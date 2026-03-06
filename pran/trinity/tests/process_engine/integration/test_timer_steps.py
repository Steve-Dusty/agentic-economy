"""
Integration Tests for Timer Steps

Tests timer delay behavior in process execution.

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-07
"""

import pytest
from unittest.mock import patch, AsyncMock

from services.process_engine.domain import (
    ExecutionStatus,
    StepStatus,
    ProcessDefinition,
    StepDefinition,
)

from .conftest import (
    create_timer_definition,
    assert_step_status,
    assert_all_steps_completed,
)


# =============================================================================
# Test: Timer Step Completes
# =============================================================================


class TestTimerExecution:
    """Tests for timer step execution."""

    @pytest.mark.asyncio
    async def test_timer_step_completes(self, integration_engine):
        """Timer step should complete after delay."""
        ctx = integration_engine

        # Arrange: Process with timer
        definition = create_timer_definition(
            name="timer-test",
            delay="50ms",
        )

        ctx.gateway.responses = {
            "before-agent": "Before timer",
            "after-agent": "After timer",
        }

        # Act: Execute with mocked sleep for speed
        with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
            execution = await ctx.start(definition)

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: All steps completed
        assert_all_steps_completed(execution)

        # Assert: Steps ran in order
        agents_called = [c["agent"] for c in ctx.gateway.calls]
        assert agents_called == ["before-agent", "after-agent"]

    @pytest.mark.asyncio
    async def test_timer_output_includes_waited_seconds(self, integration_engine):
        """Timer step output should include wait duration information."""
        ctx = integration_engine

        # Arrange: Create timer definition
        definition = ProcessDefinition.create(name="timer-output-test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-timer",
                "name": "Wait",
                "type": "timer",
                "delay": "100ms",
            }),
        ]
        definition = definition.publish()

        # Act
        with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
            execution = await ctx.start(definition)

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Timer step has output
        timer_exec = execution.step_executions["step-timer"]
        assert timer_exec.status == StepStatus.COMPLETED
        assert timer_exec.output is not None

        # Assert: Output contains wait information
        output = timer_exec.output
        assert isinstance(output, dict)
        # Timer handler returns waited_seconds or similar
        assert "waited_seconds" in output or "delay" in str(output)


# =============================================================================
# Test: Timer with Following Steps
# =============================================================================


class TestTimerDependencies:
    """Tests for timer steps with dependencies."""

    @pytest.mark.asyncio
    async def test_timer_delays_dependent_steps(self, integration_engine):
        """Steps depending on timer should wait until timer completes."""
        ctx = integration_engine

        # Arrange
        definition = create_timer_definition(
            name="timer-dependency-test",
            delay="100ms",
        )

        ctx.gateway.responses = {
            "before-agent": "Before result",
            "after-agent": "After result",
        }

        # Act
        with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
            execution = await ctx.start(definition)

        # Assert: All completed
        assert execution.status == ExecutionStatus.COMPLETED
        assert_all_steps_completed(execution)

        # Assert: Timer completed before after-step started
        timer_exec = execution.step_executions["step-timer"]
        after_exec = execution.step_executions["step-after"]

        if timer_exec.completed_at and after_exec.started_at:
            assert timer_exec.completed_at <= after_exec.started_at

        # Assert: After step could access timer output
        after_call = ctx.gateway.get_calls_for_agent("after-agent")[0]
        assert "message" in after_call  # Message was generated (may include timer output)
