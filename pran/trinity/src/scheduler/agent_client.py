"""
Agent HTTP Client for the scheduler service.

Provides communication with agent containers for task execution.
"""

import json
import logging
from typing import Optional, Dict, Any

import httpx

from .config import config
from .models import AgentTaskMetrics, AgentTaskResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class AgentClientError(Exception):
    """Base exception for agent client errors."""
    pass


class AgentNotReachableError(AgentClientError):
    """Agent container is not responding."""
    pass


class AgentRequestError(AgentClientError):
    """Agent returned an error response."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


# ============================================================================
# Agent Client
# ============================================================================

class AgentClient:
    """
    HTTP client for agent container communication.

    Designed for scheduler use - focuses on task execution.
    """

    def __init__(self, agent_name: str, timeout: float = None):
        """
        Initialize client for a specific agent.

        Args:
            agent_name: Name of the agent (without 'agent-' prefix)
            timeout: Request timeout in seconds (default from config)
        """
        self.agent_name = agent_name
        self.base_url = f"http://agent-{agent_name}:8000"
        self.timeout = timeout or config.agent_timeout

    async def _request(
        self,
        method: str,
        path: str,
        timeout: float = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request to the agent.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (e.g., "/api/task")
            timeout: Request timeout in seconds
            **kwargs: Additional arguments for httpx request

        Returns:
            httpx.Response

        Raises:
            AgentNotReachableError: If connection fails
        """
        url = f"{self.base_url}{path}"
        timeout = timeout or self.timeout

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, **kwargs)
                return response
        except httpx.ConnectError as e:
            raise AgentNotReachableError(
                f"Cannot connect to agent {self.agent_name}: {e}"
            )
        except httpx.TimeoutException as e:
            raise AgentNotReachableError(
                f"Request to agent {self.agent_name} timed out after {timeout}s"
            )

    async def task(
        self,
        message: str,
        timeout: float = None,
        execution_id: Optional[str] = None,
        allowed_tools: Optional[list] = None,
        model: Optional[str] = None
    ) -> AgentTaskResponse:
        """
        Execute a stateless task on the agent.

        This endpoint:
        - Does NOT maintain conversation history
        - Each call is independent
        - Returns raw Claude Code execution log

        Args:
            message: Task prompt to execute
            timeout: Request timeout in seconds
            execution_id: Optional execution ID for process registry
            allowed_tools: Optional list of tool names to allow (None = all tools)
            model: Optional model override (MODEL-001)

        Returns:
            AgentTaskResponse with parsed metrics

        Raises:
            AgentNotReachableError: If agent is not reachable
            AgentRequestError: If request fails
        """
        timeout = timeout or self.timeout

        payload = {"message": message, "timeout_seconds": int(timeout)}
        if execution_id:
            payload["execution_id"] = execution_id
        if allowed_tools is not None:
            payload["allowed_tools"] = allowed_tools
        if model:
            payload["model"] = model

        response = await self._request(
            "POST",
            "/api/task",
            json=payload,
            timeout=timeout + 10  # Add buffer to agent timeout
        )

        if response.status_code >= 400:
            error_msg = self._extract_error_detail(response)
            raise AgentRequestError(error_msg, status_code=response.status_code)

        result = response.json()
        return self._parse_task_response(result)

    async def health_check(self, timeout: float = 5.0) -> bool:
        """
        Check if agent is healthy and responding.

        Returns:
            True if agent responds to health check
        """
        try:
            response = await self._request("GET", "/api/health", timeout=timeout)
            return response.status_code == 200
        except AgentClientError:
            return False

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """Extract detailed error message from agent HTTP response."""
        try:
            error_data = response.json()
            if "detail" in error_data:
                return error_data["detail"]
        except Exception:
            pass
        if response.text:
            return response.text[:500]
        return f"HTTP {response.status_code} error"

    def _parse_task_response(self, result: Dict[str, Any]) -> AgentTaskResponse:
        """
        Parse agent task response into structured data.

        Extracts:
        - Response text
        - Context usage
        - Cost
        - Execution log
        - Session ID (for --resume support, EXEC-023)
        """
        # Extract response text
        response_text = result.get("response", str(result))
        if len(response_text) > 10000:
            response_text = response_text[:10000] + "... (truncated)"

        # Extract observability data
        metadata = result.get("metadata", {})
        execution_log = result.get("execution_log")

        # Context usage
        context_used = metadata.get("input_tokens", 0)
        context_max = metadata.get("context_window", 200000)
        context_percent = round(context_used / max(context_max, 1) * 100, 1)

        # Cost
        cost = metadata.get("cost_usd")

        # Claude Code session ID for --resume support (EXEC-023)
        session_id = result.get("session_id") or metadata.get("session_id")

        # Execution log - raw Claude Code transcript
        tool_calls_json = None
        execution_log_json = None
        if execution_log is not None:
            execution_log_json = json.dumps(execution_log)
            tool_calls_json = execution_log_json

        metrics = AgentTaskMetrics(
            context_used=context_used,
            context_max=context_max,
            context_percent=context_percent,
            cost_usd=cost,
            tool_calls_json=tool_calls_json,
            execution_log_json=execution_log_json,
            session_id=session_id
        )

        return AgentTaskResponse(
            response_text=response_text,
            metrics=metrics,
            raw_response=result
        )


def get_agent_client(agent_name: str) -> AgentClient:
    """Factory function to create an AgentClient."""
    return AgentClient(agent_name)
