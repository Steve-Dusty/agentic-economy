"""
Unit tests for Informed Agent Notifier Service.

Tests for: InformedAgentNotifier, NotificationResult
Reference: Sprint 15 - E16-02
"""

import pytest
import asyncio
import tempfile
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from services.process_engine.services import InformedAgentNotifier, NotificationResult
from services.process_engine.domain import (
    StepDefinition,
    StepRoles,
    StepCompleted,
    StepFailed,
    ExecutionId,
    StepId,
    Money,
    Duration,
    InformedNotification,
)


# Helper to generate valid IDs
def make_execution_id():
    return ExecutionId(str(uuid.uuid4()))

def make_step_id(name: str = "step"):
    # StepId must start with lowercase letter, contain only lowercase letters, numbers, hyphens, underscores
    return StepId(f"{name}-{uuid.uuid4().hex[:8]}")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def agent_data_path(tmp_path):
    """Create temporary agent data directory."""
    return tmp_path / "agents"


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    client = AsyncMock()
    client.send_message = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_agent_checker():
    """Create mock agent checker."""
    def checker(name: str) -> tuple[bool, bool]:
        if name == "running-agent":
            return (True, True)
        elif name == "stopped-agent":
            return (True, False)
        else:
            return (False, False)
    return checker


@pytest.fixture
def step_with_informed():
    """Create a step definition with informed agents."""
    data = {
        "id": "test-step",
        "type": "agent_task",
        "agent": "executor-agent",
        "message": "Test message",
        "roles": {
            "executor": "executor-agent",
            "monitors": ["supervisor"],
            "informed": ["dashboard-agent", "reporting-agent"],
        },
    }
    return StepDefinition.from_dict(data)


@pytest.fixture
def step_without_informed():
    """Create a step definition without informed agents."""
    data = {
        "id": "test-step",
        "type": "agent_task",
        "agent": "executor-agent",
        "message": "Test message",
        "roles": {
            "executor": "executor-agent",
        },
    }
    return StepDefinition.from_dict(data)


@pytest.fixture
def test_execution_id():
    """Generate a valid execution ID for tests."""
    return make_execution_id()


@pytest.fixture
def test_step_id():
    """Generate a valid step ID for tests."""
    return make_step_id()


@pytest.fixture
def step_completed_event(test_execution_id, test_step_id):
    """Create a StepCompleted event."""
    return StepCompleted(
        execution_id=test_execution_id,
        step_id=test_step_id,
        step_name="Test Step",
        output={"result": "success", "data": {"key": "value"}},
        cost=Money.from_string("$0.05"),
        duration=Duration(seconds=10),
    )


@pytest.fixture
def step_failed_event(test_execution_id, test_step_id):
    """Create a StepFailed event."""
    return StepFailed(
        execution_id=test_execution_id,
        step_id=test_step_id,
        step_name="Test Step",
        error_message="Something went wrong",
        error_code="TEST_ERROR",
        retry_count=2,
        will_retry=False,
    )


@pytest.fixture
def execution_context(test_execution_id):
    """Create execution context."""
    return {
        "process_name": "test-process",
        "execution_id": str(test_execution_id),
        "triggered_by": "manual",
    }


# =============================================================================
# NotificationResult Tests
# =============================================================================


class TestNotificationResult:
    """Tests for NotificationResult dataclass."""

    def test_create_default(self):
        """NotificationResult has correct defaults."""
        result = NotificationResult(agent_name="test-agent")

        assert result.agent_name == "test-agent"
        assert result.mcp_delivered is False
        assert result.memory_written is False
        assert result.error is None

    def test_create_with_values(self):
        """NotificationResult can be created with values."""
        result = NotificationResult(
            agent_name="test-agent",
            mcp_delivered=True,
            memory_written=True,
            error=None,
        )

        assert result.mcp_delivered is True
        assert result.memory_written is True


# =============================================================================
# InformedAgentNotifier Basic Tests
# =============================================================================


class TestInformedAgentNotifierBasic:
    """Basic tests for InformedAgentNotifier."""

    def test_create_without_dependencies(self):
        """Notifier can be created without dependencies."""
        notifier = InformedAgentNotifier()

        assert notifier._mcp_client is None
        assert notifier._agent_data_path is None
        assert notifier._agent_checker is None

    def test_create_with_dependencies(self, mock_mcp_client, agent_data_path, mock_agent_checker):
        """Notifier can be created with all dependencies."""
        notifier = InformedAgentNotifier(
            mcp_client=mock_mcp_client,
            agent_data_path=agent_data_path,
            agent_checker=mock_agent_checker,
        )

        assert notifier._mcp_client is mock_mcp_client
        assert notifier._agent_data_path == agent_data_path
        assert notifier._agent_checker is mock_agent_checker


# =============================================================================
# Step Completed Notification Tests
# =============================================================================


class TestNotifyStepCompleted:
    """Tests for notify_step_completed method."""

    @pytest.mark.asyncio
    async def test_no_informed_agents_returns_empty(
        self, step_without_informed, step_completed_event, execution_context
    ):
        """Notification with no informed agents returns empty list."""
        # Step without informed (but has roles)
        step = step_without_informed

        notifier = InformedAgentNotifier()
        results = await notifier.notify_step_completed(step, step_completed_event, execution_context)

        assert results == []

    @pytest.mark.asyncio
    async def test_no_roles_returns_empty(self, step_completed_event, execution_context):
        """Step without roles returns empty list."""
        data = {
            "id": "test-step",
            "type": "agent_task",
            "agent": "executor-agent",
            "message": "Test message",
        }
        step = StepDefinition.from_dict(data)

        notifier = InformedAgentNotifier()
        results = await notifier.notify_step_completed(step, step_completed_event, execution_context)

        assert results == []

    @pytest.mark.asyncio
    async def test_memory_persistence_only(
        self, step_with_informed, step_completed_event, execution_context, agent_data_path
    ):
        """Notifications are written to agent memory."""
        notifier = InformedAgentNotifier(agent_data_path=agent_data_path)

        results = await notifier.notify_step_completed(
            step_with_informed, step_completed_event, execution_context
        )

        # Should have results for each informed agent
        assert len(results) == 2
        assert all(r.memory_written for r in results)
        assert all(not r.mcp_delivered for r in results)

        # Check files were created
        for agent_name in ["dashboard-agent", "reporting-agent"]:
            events_dir = agent_data_path / agent_name / ".trinity" / "events"
            assert events_dir.exists()

            # Check NDJSON file
            files = list(events_dir.glob("notifications_*.ndjson"))
            assert len(files) == 1

            # Read and verify content
            with open(files[0]) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["event_type_name"] == "step_completed"
                assert data["step_name"] == "Test Step"

    @pytest.mark.asyncio
    async def test_mcp_delivery_for_running_agent(
        self, step_with_informed, step_completed_event, execution_context, mock_mcp_client
    ):
        """MCP delivery is attempted for running agents."""
        # Custom checker that marks dashboard-agent as running
        def checker(name: str) -> tuple[bool, bool]:
            if name == "dashboard-agent":
                return (True, True)
            return (True, False)

        notifier = InformedAgentNotifier(
            mcp_client=mock_mcp_client,
            agent_checker=checker,
        )

        results = await notifier.notify_step_completed(
            step_with_informed, step_completed_event, execution_context
        )

        assert len(results) == 2

        # Find result for dashboard-agent
        dashboard_result = next(r for r in results if r.agent_name == "dashboard-agent")
        assert dashboard_result.mcp_delivered is True

        # MCP client should have been called for running agent
        mock_mcp_client.send_message.assert_called()


# =============================================================================
# Step Failed Notification Tests
# =============================================================================


class TestNotifyStepFailed:
    """Tests for notify_step_failed method."""

    @pytest.mark.asyncio
    async def test_failure_notification_includes_error(
        self, step_with_informed, step_failed_event, execution_context, agent_data_path
    ):
        """Failure notifications include error information."""
        notifier = InformedAgentNotifier(agent_data_path=agent_data_path)

        results = await notifier.notify_step_failed(
            step_with_informed, step_failed_event, execution_context
        )

        # Should have results for each informed agent
        assert len(results) == 2
        assert all(r.memory_written for r in results)

        # Check file content includes error info
        for agent_name in ["dashboard-agent", "reporting-agent"]:
            events_dir = agent_data_path / agent_name / ".trinity" / "events"
            files = list(events_dir.glob("notifications_*.ndjson"))

            with open(files[0]) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["event_type_name"] == "step_failed"
                assert data["output_summary"] == "Something went wrong"
                assert data["metadata"]["error_code"] == "TEST_ERROR"
                assert data["metadata"]["retry_count"] == 2
                assert data["metadata"]["will_retry"] is False


# =============================================================================
# Output Summary Tests
# =============================================================================


class TestOutputSummary:
    """Tests for output summarization."""

    @pytest.mark.asyncio
    async def test_large_output_is_truncated(
        self, step_with_informed, execution_context, agent_data_path, test_execution_id, test_step_id
    ):
        """Large outputs are truncated in notifications."""
        # Create event with large output
        large_output = {"data": "x" * 1000}
        event = StepCompleted(
            execution_id=test_execution_id,
            step_id=test_step_id,
            step_name="Test Step",
            output=large_output,
            cost=Money.zero(),
            duration=Duration(seconds=1),
        )

        notifier = InformedAgentNotifier(agent_data_path=agent_data_path)

        await notifier.notify_step_completed(
            step_with_informed, event, execution_context
        )

        # Check summary was truncated
        events_dir = agent_data_path / "dashboard-agent" / ".trinity" / "events"
        files = list(events_dir.glob("notifications_*.ndjson"))

        with open(files[0]) as f:
            line = f.readline()
            data = json.loads(line)
            # Summary should be truncated (500 chars + "...")
            assert len(data["output_summary"]) <= 503


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in notifications."""

    @pytest.mark.asyncio
    async def test_mcp_failure_doesnt_block(
        self, step_with_informed, step_completed_event, execution_context, agent_data_path
    ):
        """MCP failure doesn't prevent memory write."""
        # Create MCP client that fails
        failing_client = AsyncMock()
        failing_client.send_message = AsyncMock(return_value=False)

        def checker(name: str) -> tuple[bool, bool]:
            return (True, True)  # All agents running

        notifier = InformedAgentNotifier(
            mcp_client=failing_client,
            agent_data_path=agent_data_path,
            agent_checker=checker,
        )

        results = await notifier.notify_step_completed(
            step_with_informed, step_completed_event, execution_context
        )

        # Memory should still be written even if MCP failed
        assert len(results) == 2
        assert all(r.memory_written for r in results)
        assert all(not r.mcp_delivered for r in results)

    @pytest.mark.asyncio
    async def test_agent_checker_exception_handled(
        self, step_with_informed, step_completed_event, execution_context, agent_data_path
    ):
        """Agent checker exception is handled gracefully."""
        def failing_checker(name: str) -> tuple[bool, bool]:
            raise Exception("Checker failed")

        notifier = InformedAgentNotifier(
            agent_data_path=agent_data_path,
            agent_checker=failing_checker,
        )

        # Should not raise
        results = await notifier.notify_step_completed(
            step_with_informed, step_completed_event, execution_context
        )

        # Should still have results (memory write should succeed)
        assert len(results) == 2


# =============================================================================
# InformedNotification Event Tests
# =============================================================================


class TestInformedNotification:
    """Tests for InformedNotification event type."""

    def test_create_notification(self, test_execution_id, test_step_id):
        """InformedNotification can be created."""
        notification = InformedNotification(
            event_type_name="step_completed",
            process_name="test-process",
            execution_id=test_execution_id,
            step_id=test_step_id,
            step_name="Test Step",
            output_summary='{"result": "ok"}',
            metadata={"cost": "$0.05"},
        )

        assert notification.event_type_name == "step_completed"
        assert notification.process_name == "test-process"
        assert notification.step_name == "Test Step"
        assert notification.metadata["cost"] == "$0.05"

    def test_notification_to_dict(self, test_execution_id, test_step_id):
        """InformedNotification.to_dict() returns correct structure."""
        notification = InformedNotification(
            event_type_name="step_failed",
            process_name="test-process",
            execution_id=test_execution_id,
            step_id=test_step_id,
            step_name="Test Step",
            output_summary="Error occurred",
            metadata={"error_code": "ERR_001"},
        )

        result = notification.to_dict()

        assert result["event_type_name"] == "step_failed"
        assert result["process_name"] == "test-process"
        assert result["execution_id"] == str(test_execution_id)
        assert result["step_id"] == str(test_step_id)
        assert result["step_name"] == "Test Step"
        assert result["output_summary"] == "Error occurred"
        assert result["metadata"]["error_code"] == "ERR_001"
        assert "timestamp" in result
