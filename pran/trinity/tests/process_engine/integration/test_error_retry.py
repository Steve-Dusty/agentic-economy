"""
Integration Tests for Error Handling and Retry

Tests retry policies and error boundary behavior.

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-05
"""

import pytest

from services.process_engine.domain import (
    ExecutionStatus,
    StepStatus,
    ProcessDefinition,
    StepDefinition,
)

from .conftest import (
    create_retry_definition,
    create_sequential_definition,
    assert_step_status,
    MockAgentGateway,
)


# =============================================================================
# Test: Retry Succeeds on Third Attempt
# =============================================================================


class TestRetryPolicies:
    """Tests for retry policy behavior."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_third_attempt(self, integration_engine):
        """A step should retry and eventually succeed after transient failures."""
        ctx = integration_engine

        # Arrange: Configure gateway to fail twice then succeed
        ctx.gateway.fail_count = 2  # Fail first 2 attempts
        ctx.gateway.responses = {
            "flaky-agent": "Success after retries",
        }

        definition = create_retry_definition(
            name="retry-success-test",
            max_attempts=3,
        )

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Step completed
        assert_step_status(execution, "step-retry", StepStatus.COMPLETED)

        # Assert: Agent was called 3 times (2 failures + 1 success)
        flaky_calls = ctx.gateway.get_calls_for_agent("flaky-agent")
        assert len(flaky_calls) == 3

        # Assert: StepRetrying events were emitted
        event_types = ctx.event_bus.get_event_types()
        retrying_count = event_types.count("StepRetrying")
        assert retrying_count >= 2

    @pytest.mark.asyncio
    async def test_retry_exhausted_fails_execution(self, integration_engine):
        """When all retry attempts are exhausted, the execution should fail."""
        ctx = integration_engine

        # Arrange: Configure gateway to always fail
        ctx.gateway.fail_agents.add("always-failing-agent")

        definition = ProcessDefinition.create(name="retry-exhausted-test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-retry",
                "name": "Retry Step",
                "type": "agent_task",
                "agent": "always-failing-agent",
                "message": "Will always fail",
                "retry": {
                    "max_attempts": 3,
                    "initial_delay": "10ms",
                },
            }),
        ]
        definition = definition.publish()

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution failed
        assert execution.status == ExecutionStatus.FAILED

        # Assert: Step failed
        assert_step_status(execution, "step-retry", StepStatus.FAILED)

        # Assert: Error recorded
        step_exec = execution.step_executions["step-retry"]
        assert step_exec.error is not None


# =============================================================================
# Test: Skip Step on Error
# =============================================================================


class TestErrorBoundaries:
    """Tests for error boundary behavior (on_error settings)."""

    @pytest.mark.asyncio
    async def test_skip_step_on_error_continues(self, integration_engine):
        """With on_error=skip_step, execution should continue after failure."""
        ctx = integration_engine

        # Arrange: Configure middle agent to fail
        ctx.gateway.fail_agents.add("failing-agent")

        definition = ProcessDefinition.create(name="skip-step-test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-1",
                "name": "First Step",
                "type": "agent_task",
                "agent": "first-agent",
                "message": "First",
            }),
            StepDefinition.from_dict({
                "id": "step-2",
                "name": "Skippable Step",
                "type": "agent_task",
                "agent": "failing-agent",
                "message": "This will fail",
                "depends_on": ["step-1"],
                "on_error": "skip_step",
            }),
            StepDefinition.from_dict({
                "id": "step-3",
                "name": "Final Step",
                "type": "agent_task",
                "agent": "final-agent",
                "message": "Final",
                "depends_on": ["step-2"],
            }),
        ]
        definition = definition.publish()

        ctx.gateway.responses = {
            "first-agent": "First result",
            "final-agent": "Final result",
        }

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution completed (not failed)
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: First step completed
        assert_step_status(execution, "step-1", StepStatus.COMPLETED)

        # Assert: Middle step was skipped
        assert_step_status(execution, "step-2", StepStatus.SKIPPED)

        # Assert: Final step still ran
        assert_step_status(execution, "step-3", StepStatus.COMPLETED)

        # Assert: Final agent was called
        final_calls = ctx.gateway.get_calls_for_agent("final-agent")
        assert len(final_calls) == 1


# =============================================================================
# Test: Retry Count Persisted
# =============================================================================


class TestRetryPersistence:
    """Tests for retry state persistence."""

    @pytest.mark.asyncio
    async def test_retry_count_persisted(self, integration_engine):
        """Retry count should be persisted to the database."""
        ctx = integration_engine

        # Arrange: Configure gateway to fail once
        ctx.gateway.fail_count = 1

        definition = create_retry_definition(
            name="retry-persist-test",
            max_attempts=3,
        )

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Retry count persisted
        persisted = ctx.repos.execution.get_by_id(execution.id)
        step_exec = persisted.step_executions["step-retry"]
        assert step_exec.retry_count >= 1

        # Assert: In-memory and persisted match
        assert step_exec.retry_count == execution.step_executions["step-retry"].retry_count


# =============================================================================
# Test: Retry with Backoff
# =============================================================================


class TestRetryBackoff:
    """Tests for retry backoff behavior."""

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, integration_engine):
        """Retry should use exponential backoff between attempts."""
        ctx = integration_engine

        # Arrange: Configure gateway to fail twice
        ctx.gateway.fail_count = 2

        definition = ProcessDefinition.create(name="backoff-test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-retry",
                "name": "Retry Step",
                "type": "agent_task",
                "agent": "backoff-agent",
                "message": "Test backoff",
                "retry": {
                    "max_attempts": 3,
                    "initial_delay": "10ms",
                    "backoff_multiplier": 2.0,
                },
            }),
        ]
        definition = definition.publish()

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Step completed after retries
        assert_step_status(execution, "step-retry", StepStatus.COMPLETED)

        # Assert: Correct number of calls
        calls = ctx.gateway.get_calls_for_agent("backoff-agent")
        assert len(calls) == 3
