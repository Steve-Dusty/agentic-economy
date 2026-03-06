"""
Integration Tests for Output Persistence

Tests OutputStorage integration and expression substitution.

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-09
"""

import pytest

from services.process_engine.domain import (
    ExecutionStatus,
    StepStatus,
    ProcessDefinition,
    StepDefinition,
)

from .conftest import (
    create_sequential_definition,
    create_single_step_definition,
    assert_all_steps_completed,
)


# =============================================================================
# Test: Step Output Stored and Retrievable
# =============================================================================


class TestOutputStorage:
    """Tests for output storage and retrieval."""

    @pytest.mark.asyncio
    async def test_step_output_stored_and_retrievable(self, integration_engine):
        """Step output should be stored in OutputStorage and retrievable."""
        ctx = integration_engine

        # Arrange
        definition = create_single_step_definition(
            name="output-storage-test",
            agent="output-agent",
        )

        ctx.gateway.responses = {
            "output-agent": "This is the agent output",
        }

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Output stored in step execution
        step_exec = execution.step_executions["step-1"]
        assert step_exec.output is not None

        # Assert: Output contains agent response
        output = step_exec.output
        if isinstance(output, dict):
            assert "response" in output
            assert "This is the agent output" in output["response"]
        else:
            assert "This is the agent output" in str(output)

        # Assert: Output persisted to database
        persisted = ctx.repos.execution.get_by_id(execution.id)
        persisted_step = persisted.step_executions["step-1"]
        assert persisted_step.output is not None


# =============================================================================
# Test: Output Available for Next Step
# =============================================================================


class TestOutputSubstitution:
    """Tests for output substitution in expressions."""

    @pytest.mark.asyncio
    async def test_output_available_for_next_step_substitution(self, integration_engine):
        """Output from one step should be available for substitution in next step."""
        ctx = integration_engine

        # Arrange: 2-step process where step 2 uses step 1 output
        definition = create_sequential_definition(
            name="substitution-test",
            num_steps=2,
            agents=["first", "second"],
        )

        # Configure first agent to return specific output
        ctx.gateway.responses = {
            "first": "SPECIFIC_OUTPUT_VALUE",
            "second": "Processed the specific output",
        }

        # Act
        execution = await ctx.start(definition, input_data={"topic": "test"})

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED
        assert_all_steps_completed(execution)

        # Assert: Second step received first step's output
        # The sequential_definition uses "Continue with: {{steps.step-1.output}}"
        second_call = ctx.gateway.get_calls_for_agent("second")[0]
        # The message should contain the first agent's response
        assert "SPECIFIC_OUTPUT_VALUE" in second_call["message"]

    @pytest.mark.asyncio
    async def test_multiple_output_references(self, integration_engine):
        """Multiple output references in same message should all be substituted."""
        ctx = integration_engine

        # Arrange: Process with multiple references
        definition = ProcessDefinition.create(name="multi-ref-test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-1",
                "name": "First",
                "type": "agent_task",
                "agent": "first",
                "message": "Do first thing",
            }),
            StepDefinition.from_dict({
                "id": "step-2",
                "name": "Second",
                "type": "agent_task",
                "agent": "second",
                "message": "Do second thing",
                "depends_on": ["step-1"],
            }),
            StepDefinition.from_dict({
                "id": "step-3",
                "name": "Third",
                "type": "agent_task",
                "agent": "third",
                # Reference both previous steps
                "message": "First said: {{steps.step-1.output}}, Second said: {{steps.step-2.output}}",
                "depends_on": ["step-2"],
            }),
        ]
        definition = definition.publish()

        ctx.gateway.responses = {
            "first": "FIRST_RESULT",
            "second": "SECOND_RESULT",
            "third": "Combined",
        }

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Third step message contains both outputs
        third_call = ctx.gateway.get_calls_for_agent("third")[0]
        assert "FIRST_RESULT" in third_call["message"]
        assert "SECOND_RESULT" in third_call["message"]
