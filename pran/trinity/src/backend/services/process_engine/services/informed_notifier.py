"""
Informed Agent Notifier Service

Delivers step events to agents marked as "informed" in the EMI pattern.

Delivery mechanisms:
1. MCP message to agent (if running)
2. Agent memory file (always, for persistence)

Reference: IT1 Section - EMI Pattern (Executor/Monitor/Informed)
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

from ..domain import (
    StepDefinition,
    StepCompleted,
    StepFailed,
    ExecutionId,
    InformedNotification,
)


logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


class MCPClient(Protocol):
    """Protocol for MCP client interface."""

    async def send_message(self, agent_name: str, message: dict) -> bool:
        """Send a message to an agent via MCP. Returns True if successful."""
        ...


@dataclass
class NotificationResult:
    """Result of attempting to notify an agent."""
    agent_name: str
    mcp_delivered: bool = False
    memory_written: bool = False
    error: Optional[str] = None


class InformedAgentNotifier:
    """
    Delivers step events to informed agents.

    The notifier supports two delivery mechanisms:
    1. MCP message delivery (for running agents) - real-time notification
    2. Agent memory file (for persistence) - agent can read on next activation

    Usage:
        notifier = InformedAgentNotifier(
            mcp_client=mcp_client,
            agent_data_path=Path("~/trinity-data/agents"),
        )
        await notifier.notify_step_completed(step, event, context)
    """

    def __init__(
        self,
        mcp_client: Optional[MCPClient] = None,
        agent_data_path: Optional[Path] = None,
        agent_checker: Optional[Callable[[str], tuple[bool, bool]]] = None,
    ):
        """
        Initialize the notifier.

        Args:
            mcp_client: Optional MCP client for sending real-time messages
            agent_data_path: Path to agent data directory for memory persistence
            agent_checker: Function to check if agent exists and is running
        """
        self._mcp_client = mcp_client
        self._agent_data_path = agent_data_path
        self._agent_checker = agent_checker

    async def notify_step_completed(
        self,
        step: StepDefinition,
        event: StepCompleted,
        execution_context: dict,
    ) -> list[NotificationResult]:
        """
        Notify all informed agents about step completion.

        Args:
            step: The step definition that completed
            event: The StepCompleted event
            execution_context: Additional context about the execution

        Returns:
            List of NotificationResult for each informed agent
        """
        if not step.roles or not step.roles.informed:
            return []

        notification = InformedNotification(
            event_type_name="step_completed",
            process_name=execution_context.get("process_name", "unknown"),
            execution_id=event.execution_id,
            step_id=event.step_id,
            step_name=event.step_name,
            output_summary=self._summarize_output(event.output),
            metadata={
                "cost": str(event.cost),
                "duration_seconds": event.duration.seconds if event.duration else 0,
            },
        )

        results = await self._notify_agents(step.roles.informed, notification)
        return results

    async def notify_step_failed(
        self,
        step: StepDefinition,
        event: StepFailed,
        execution_context: dict,
    ) -> list[NotificationResult]:
        """
        Notify all informed agents about step failure.

        Args:
            step: The step definition that failed
            event: The StepFailed event
            execution_context: Additional context about the execution

        Returns:
            List of NotificationResult for each informed agent
        """
        if not step.roles or not step.roles.informed:
            return []

        notification = InformedNotification(
            event_type_name="step_failed",
            process_name=execution_context.get("process_name", "unknown"),
            execution_id=event.execution_id,
            step_id=event.step_id,
            step_name=event.step_name,
            output_summary=event.error_message[:500],  # Truncate error message
            metadata={
                "error_code": event.error_code,
                "retry_count": event.retry_count,
                "will_retry": event.will_retry,
            },
        )

        results = await self._notify_agents(step.roles.informed, notification)
        return results

    async def _notify_agents(
        self,
        agent_names: list[str],
        notification: InformedNotification,
    ) -> list[NotificationResult]:
        """
        Send notification to multiple agents.

        Runs notifications concurrently for better performance.
        """
        tasks = [
            self._notify_single_agent(agent_name, notification)
            for agent_name in agent_names
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to NotificationResult
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(NotificationResult(
                    agent_name=agent_names[i],
                    error=str(result),
                ))
            else:
                final_results.append(result)

        return final_results

    async def _notify_single_agent(
        self,
        agent_name: str,
        notification: InformedNotification,
    ) -> NotificationResult:
        """
        Send notification to a single agent.

        Attempts both MCP delivery (if agent is running) and memory persistence.
        """
        result = NotificationResult(agent_name=agent_name)

        # Check if agent exists and is running
        is_running = False
        if self._agent_checker:
            try:
                exists, is_running = self._agent_checker(agent_name)
                if not exists:
                    logger.warning(f"Informed agent '{agent_name}' does not exist")
            except Exception as e:
                logger.warning(f"Could not check agent '{agent_name}': {e}")

        # Try MCP delivery if agent is running
        if is_running and self._mcp_client:
            try:
                result.mcp_delivered = await self._deliver_via_mcp(
                    agent_name,
                    notification,
                )
            except Exception as e:
                logger.warning(f"MCP delivery to '{agent_name}' failed: {e}")
                result.error = f"MCP delivery failed: {e}"

        # Always try memory persistence
        if self._agent_data_path:
            try:
                result.memory_written = await self._write_to_memory(
                    agent_name,
                    notification,
                )
            except Exception as e:
                logger.warning(f"Memory write for '{agent_name}' failed: {e}")
                if result.error:
                    result.error += f"; Memory write failed: {e}"
                else:
                    result.error = f"Memory write failed: {e}"

        return result

    async def _deliver_via_mcp(
        self,
        agent_name: str,
        notification: InformedNotification,
    ) -> bool:
        """
        Deliver notification via MCP message.

        Non-blocking - does not wait for agent response.
        """
        if not self._mcp_client:
            return False

        message = {
            "type": "informed_notification",
            "payload": notification.to_dict(),
        }

        try:
            success = await self._mcp_client.send_message(agent_name, message)
            if success:
                logger.info(f"MCP notification sent to '{agent_name}'")
            return success
        except Exception as e:
            logger.error(f"Failed to send MCP message to '{agent_name}': {e}")
            return False

    async def _write_to_memory(
        self,
        agent_name: str,
        notification: InformedNotification,
    ) -> bool:
        """
        Write notification to agent's memory file.

        Uses NDJSON format (newline-delimited JSON) for easy parsing.
        Agent can read these on next activation.
        """
        if not self._agent_data_path:
            return False

        # Create events directory for agent
        events_dir = self._agent_data_path / agent_name / ".trinity" / "events"

        # Run file I/O in executor to avoid blocking
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._write_to_memory_sync,
            events_dir,
            notification,
        )

    def _write_to_memory_sync(
        self,
        events_dir: Path,
        notification: InformedNotification,
    ) -> bool:
        """Synchronous memory write operation."""
        try:
            events_dir.mkdir(parents=True, exist_ok=True)

            # Use date-based file naming for organization
            today = _utcnow().strftime("%Y-%m-%d")
            events_file = events_dir / f"notifications_{today}.ndjson"

            # Append to NDJSON file
            with open(events_file, "a") as f:
                f.write(json.dumps(notification.to_dict()) + "\n")

            logger.debug(f"Wrote notification to '{events_file}'")
            return True
        except Exception as e:
            logger.error(f"Failed to write notification to memory: {e}")
            return False

    def _summarize_output(self, output: dict, max_length: int = 500) -> str:
        """
        Create a summary of step output for notification.

        Truncates long outputs to avoid overwhelming informed agents.
        """
        if not output:
            return ""

        try:
            output_str = json.dumps(output)
            if len(output_str) <= max_length:
                return output_str
            return output_str[:max_length - 3] + "..."
        except Exception:
            return str(output)[:max_length]
