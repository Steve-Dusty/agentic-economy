"""
Integration Tests for Sequential Execution

Tests multi-step sequential processes and output passing between steps.

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-03
"""

import pytest

from services.process_engine.domain import (
    ExecutionStatus,
    StepStatus,
)

from .conftest import (
    create_sequential_definition,
    assert_event_sequence,
    assert_all_steps_completed,
)


# =============================================================================
# Test: Three Step Sequential Completes
# =============================================================================


class TestSequentialExecution:
    """Tests for sequential multi-step process execution."""

    @pytest.mark.asyncio
    async def test_three_step_sequential_completes(self, integration_engine):
        """A 3-step sequential process should complete all steps in order."""
        ctx = integration_engine

        # Arrange
        definition = create_sequential_definition(
            name="sequential-test",
            num_steps=3,
            agents=["researcher", "writer", "editor"],
        )

        # Configure specific responses
        ctx.gateway.responses = {
            "researcher": "Research findings about AI",
            "writer": "Draft article based on research",
            "editor": "Polished final article",
        }

        # Act
        execution = await ctx.start(definition, input_data={"topic": "AI"})

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: All steps completed
        assert_all_steps_completed(execution)

        # Assert: Steps executed in order
        agent_calls = [c["agent"] for c in ctx.gateway.calls]
        assert agent_calls == ["researcher", "writer", "editor"]

        # Assert: Events in correct sequence
        expected_events = [
            "ProcessStarted",
            "StepStarted", "StepCompleted",  # step-1
            "StepStarted", "StepCompleted",  # step-2
            "StepStarted", "StepCompleted",  # step-3
            "ProcessCompleted",
        ]
        assert_event_sequence(ctx.event_bus, expected_events)

    @pytest.mark.asyncio
    async def test_output_passed_between_steps(self, integration_engine):
        """Step outputs should be available to subsequent steps via {{steps.X.output}}."""
        ctx = integration_engine

        # Arrange
        definition = create_sequential_definition(
            name="output-passing-test",
            num_steps=2,
            agents=["first-agent", "second-agent"],
        )

        # Configure first agent to return specific output
        ctx.gateway.responses = {
            "first-agent": "First step output data",
            "second-agent": "Processed the first output",
        }

        # Act
        execution = await ctx.start(definition, input_data={"topic": "test"})

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Second step received first step's output in its message
        # The sequential_definition uses "Continue with: {{steps.step-1.output}}"
        second_call = ctx.gateway.get_calls_for_agent("second-agent")[0]
        # The message should contain the first agent's response
        assert "First step output data" in second_call["message"]

    @pytest.mark.asyncio
    async def test_input_data_available_in_first_step(self, integration_engine):
        """Input data should be available via {{input.X}} in step messages."""
        ctx = integration_engine

        # Arrange
        definition = create_sequential_definition(
            name="input-test",
            num_steps=1,
            agents=["processor"],
        )

        # Act
        execution = await ctx.start(
            definition,
            input_data={"topic": "Machine Learning"},
        )

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: First step received input data
        # The sequential_definition uses "Process: {{input.topic}}" for first step
        first_call = ctx.gateway.calls[0]
        assert "Machine Learning" in first_call["message"]


# =============================================================================
# Test: Step Failure Stops Chain
# =============================================================================


class TestSequentialFailure:
    """Tests for failure handling in sequential execution."""

    @pytest.mark.asyncio
    async def test_middle_step_failure_stops_execution(self, integration_engine):
        """If a middle step fails, subsequent steps should not run."""
        ctx = integration_engine

        # Arrange: Configure second agent to fail
        ctx.gateway.fail_agents.add("failing-writer")

        definition = create_sequential_definition(
            name="middle-fail-test",
            num_steps=3,
            agents=["researcher", "failing-writer", "editor"],
        )

        # Act
        execution = await ctx.start(definition, input_data={"topic": "test"})

        # Assert: Execution failed
        assert execution.status == ExecutionStatus.FAILED

        # Assert: First step completed, second failed, third never ran
        assert execution.step_executions["step-1"].status == StepStatus.COMPLETED
        assert execution.step_executions["step-2"].status == StepStatus.FAILED
        assert execution.step_executions["step-3"].status == StepStatus.PENDING

        # Assert: Only first agent was called (second failed on availability check)
        agents_called = [c["agent"] for c in ctx.gateway.calls]
        assert "researcher" in agents_called
        # Note: failing-writer may or may not be in calls depending on when it fails
        assert "editor" not in agents_called
