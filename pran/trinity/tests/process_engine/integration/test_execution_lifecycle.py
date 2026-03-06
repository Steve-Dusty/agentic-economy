"""
Integration Tests for Execution Lifecycle

Tests basic execution flows: start, complete, fail, cancel.
Verifies state persistence to SQLite and domain event emission.

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-02
"""

import pytest

from services.process_engine.domain import (
    ExecutionStatus,
    StepStatus,
)

from .conftest import (
    create_single_step_definition,
    create_sequential_definition,
    assert_event_sequence,
    assert_all_steps_completed,
    MockAgentGateway,
)


# =============================================================================
# Test: Single Step Completes
# =============================================================================


class TestSingleStepCompletes:
    """Test that a single-step process completes successfully."""

    @pytest.mark.asyncio
    async def test_single_step_completes(self, integration_engine):
        """A single-step process should complete successfully."""
        ctx = integration_engine

        # Arrange
        definition = create_single_step_definition(
            name="simple-test",
            agent="test-agent",
            message="Hello world",
        )

        # Act
        execution = await ctx.start(definition, input_data={"topic": "test"})

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Step completed
        assert_all_steps_completed(execution)

        # Assert: Agent was called
        assert len(ctx.gateway.calls) == 1
        assert ctx.gateway.calls[0]["agent"] == "test-agent"
        assert "Hello world" in ctx.gateway.calls[0]["message"]


# =============================================================================
# Test: Execution Persisted to Database
# =============================================================================


class TestExecutionPersisted:
    """Test that execution state is persisted to the database."""

    @pytest.mark.asyncio
    async def test_execution_persisted_to_database(self, integration_engine):
        """Execution state should be saved to SQLite repository."""
        ctx = integration_engine

        # Arrange
        definition = create_single_step_definition(name="persist-test")

        # Act
        execution = await ctx.start(definition)

        # Assert: Can retrieve from repository
        persisted = ctx.repos.execution.get_by_id(execution.id)
        assert persisted is not None

        # Assert: Persisted state matches
        assert persisted.id == execution.id
        assert persisted.status == ExecutionStatus.COMPLETED
        assert persisted.process_name == "persist-test"

        # Assert: Step executions persisted
        assert "step-1" in persisted.step_executions
        assert persisted.step_executions["step-1"].status == StepStatus.COMPLETED


# =============================================================================
# Test: Failed Step Fails Execution
# =============================================================================


class TestFailedStepFailsExecution:
    """Test that a failed step causes the execution to fail."""

    @pytest.mark.asyncio
    async def test_failed_step_fails_execution(self, integration_engine):
        """When an agent fails, the execution should fail."""
        ctx = integration_engine

        # Arrange: Configure gateway to fail for this agent
        ctx.gateway.fail_agents.add("failing-agent")

        definition = create_single_step_definition(
            name="fail-test",
            agent="failing-agent",
            message="This will fail",
        )

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution failed
        assert execution.status == ExecutionStatus.FAILED

        # Assert: Step failed
        step_exec = execution.step_executions["step-1"]
        assert step_exec.status == StepStatus.FAILED
        assert step_exec.error is not None
        # Error can be a dict or string
        error_str = str(step_exec.error) if isinstance(step_exec.error, dict) else step_exec.error
        assert "unavailable" in error_str.lower() or "not available" in error_str.lower()

        # Assert: Persisted as failed
        persisted = ctx.repos.execution.get_by_id(execution.id)
        assert persisted.status == ExecutionStatus.FAILED

        # Assert: Events include failure
        event_types = ctx.event_bus.get_event_types()
        assert "StepFailed" in event_types
        assert "ProcessFailed" in event_types


# =============================================================================
# Test: Cancel Running Execution
# =============================================================================


class TestCancelExecution:
    """Test that an execution can be cancelled."""

    @pytest.mark.asyncio
    async def test_cancel_pending_execution(self, integration_engine):
        """A pending execution can be cancelled."""
        ctx = integration_engine

        # Arrange: Create execution but don't start it yet
        definition = create_single_step_definition(name="cancel-test")

        # Create the execution object directly (not through engine.start)
        from services.process_engine.domain import ProcessExecution
        execution = ProcessExecution.create(definition, triggered_by="test")
        ctx.repos.execution.save(execution)

        # Act: Cancel before it runs
        cancelled = await ctx.cancel(execution, reason="User requested cancellation")

        # Assert: Execution is cancelled
        assert cancelled.status == ExecutionStatus.CANCELLED

        # Assert: Persisted as cancelled
        persisted = ctx.repos.execution.get_by_id(execution.id)
        assert persisted.status == ExecutionStatus.CANCELLED

        # Assert: Cancel event emitted
        event_types = ctx.event_bus.get_event_types()
        assert "ProcessCancelled" in event_types
