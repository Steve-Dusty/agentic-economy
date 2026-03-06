"""
Integration Tests for Parallel Execution

Tests fork/join patterns and concurrent step execution.

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-04
"""

import pytest

from services.process_engine.domain import (
    ExecutionStatus,
    StepStatus,
    ProcessDefinition,
    StepDefinition,
)
from services.process_engine.engine import ExecutionConfig

from .conftest import (
    create_parallel_definition,
    assert_all_steps_completed,
    assert_step_status,
)


# =============================================================================
# Test: Parallel Steps Both Complete
# =============================================================================


class TestParallelExecution:
    """Tests for parallel step execution."""

    @pytest.mark.asyncio
    async def test_parallel_steps_both_complete(self, integration_engine):
        """Two parallel steps should both complete successfully."""
        ctx = integration_engine

        # Arrange: Process with 2 parallel branches
        definition = create_parallel_definition(
            name="parallel-test",
            parallel_count=2,
        )

        ctx.gateway.responses = {
            "start-agent": "Initial data",
            "parallel-agent-1": "Branch 1 result",
            "parallel-agent-2": "Branch 2 result",
            "join-agent": "Combined results",
        }

        # Act
        execution = await ctx.start(definition, input_data={"topic": "parallel"})

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: All steps completed
        assert_all_steps_completed(execution)

        # Assert: All agents were called
        agents_called = {c["agent"] for c in ctx.gateway.calls}
        assert "start-agent" in agents_called
        assert "parallel-agent-1" in agents_called
        assert "parallel-agent-2" in agents_called
        assert "join-agent" in agents_called

    @pytest.mark.asyncio
    async def test_diamond_pattern(self, integration_engine):
        """Diamond pattern (fork → parallel → join) should work correctly."""
        ctx = integration_engine

        # Arrange: Create diamond pattern manually for clarity
        definition = ProcessDefinition.create(name="diamond-test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "start",
                "name": "Start",
                "type": "agent_task",
                "agent": "coordinator",
                "message": "Initialize",
            }),
            StepDefinition.from_dict({
                "id": "branch-a",
                "name": "Branch A",
                "type": "agent_task",
                "agent": "worker-a",
                "message": "Process A: {{steps.start.output}}",
                "depends_on": ["start"],
            }),
            StepDefinition.from_dict({
                "id": "branch-b",
                "name": "Branch B",
                "type": "agent_task",
                "agent": "worker-b",
                "message": "Process B: {{steps.start.output}}",
                "depends_on": ["start"],
            }),
            StepDefinition.from_dict({
                "id": "merge",
                "name": "Merge",
                "type": "agent_task",
                "agent": "merger",
                "message": "Merge A and B",
                "depends_on": ["branch-a", "branch-b"],
            }),
        ]
        definition = definition.publish()

        ctx.gateway.responses = {
            "coordinator": "Started",
            "worker-a": "Result A",
            "worker-b": "Result B",
            "merger": "Merged",
        }

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: All steps completed
        assert_all_steps_completed(execution)

        # Assert: Start came first, merge came last
        call_order = [c["agent"] for c in ctx.gateway.calls]
        assert call_order[0] == "coordinator"  # Start first
        assert call_order[-1] == "merger"      # Merge last
        # Branch A and B can be in any order between
        assert "worker-a" in call_order[1:-1]
        assert "worker-b" in call_order[1:-1]

    @pytest.mark.asyncio
    async def test_join_waits_for_all_dependencies(self, integration_engine):
        """Join step should not start until all parallel steps complete."""
        ctx = integration_engine

        # Arrange: Use parallel definition
        definition = create_parallel_definition(
            name="join-wait-test",
            parallel_count=3,  # 3 parallel branches
        )

        # Act
        execution = await ctx.start(definition, input_data={"topic": "test"})

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Join step has all parallel steps as dependencies met
        join_exec = execution.step_executions["step-join"]
        assert join_exec.status == StepStatus.COMPLETED

        # Assert: All parallel steps completed before join
        for i in range(1, 4):
            parallel_exec = execution.step_executions[f"step-parallel-{i}"]
            assert parallel_exec.status == StepStatus.COMPLETED
            # Parallel step should have completed before join started
            if parallel_exec.completed_at and join_exec.started_at:
                assert parallel_exec.completed_at <= join_exec.started_at

    @pytest.mark.asyncio
    async def test_one_parallel_failure_behavior(self, integration_engine):
        """When one parallel branch fails, behavior depends on stop_on_failure config."""
        ctx = integration_engine

        # Arrange: One parallel agent fails
        ctx.gateway.fail_agents.add("parallel-agent-2")

        definition = create_parallel_definition(
            name="parallel-fail-test",
            parallel_count=2,
        )

        # Act: With stop_on_failure=True (default)
        execution = await ctx.start(definition, input_data={"topic": "test"})

        # Assert: Execution failed
        assert execution.status == ExecutionStatus.FAILED

        # Assert: The failing branch failed
        assert_step_status(execution, "step-parallel-2", StepStatus.FAILED)

        # Assert: Join never completed (couldn't run with failed dependency)
        join_status = execution.step_executions["step-join"].status
        assert join_status in (StepStatus.PENDING, StepStatus.FAILED)


# =============================================================================
# Test: Parallel Execution Events
# =============================================================================


class TestParallelEvents:
    """Tests for events during parallel execution."""

    @pytest.mark.asyncio
    async def test_parallel_events_sequence(self, integration_engine):
        """Events should reflect parallel execution structure."""
        ctx = integration_engine

        # Arrange
        definition = create_parallel_definition(
            name="parallel-events-test",
            parallel_count=2,
        )

        # Act
        execution = await ctx.start(definition, input_data={"topic": "test"})

        # Assert: Key events present
        event_types = ctx.event_bus.get_event_types()

        # Should have process start/complete
        assert "ProcessStarted" in event_types
        assert "ProcessCompleted" in event_types

        # Should have step events for all 4 steps (start, 2 parallel, join)
        step_started_count = event_types.count("StepStarted")
        step_completed_count = event_types.count("StepCompleted")
        assert step_started_count == 4
        assert step_completed_count == 4
