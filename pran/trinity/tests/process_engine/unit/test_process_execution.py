"""
Unit tests for ProcessExecution aggregate.

Tests for: ProcessExecution, StepExecution state transitions
Reference: Sprint 1 Review - gap identified
"""

import pytest
from datetime import datetime, timezone

from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    StepDefinition,
    StepExecution,
    ProcessId,
    ExecutionId,
    StepId,
    Version,
    Money,
    Duration,
    ExecutionStatus,
    StepStatus,
    InvalidExecutionStateError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_definition():
    """Create a sample process definition."""
    definition = ProcessDefinition.create(name="test-process")
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-a",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "First step",
        }),
        StepDefinition.from_dict({
            "id": "step-b",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "Second step",
            "depends_on": ["step-a"],
        }),
    ]
    return definition


# =============================================================================
# ProcessExecution Creation Tests
# =============================================================================


class TestProcessExecutionCreation:
    """Tests for ProcessExecution creation."""

    def test_create_from_definition(self, sample_definition):
        """ProcessExecution.create() initializes correctly."""
        execution = ProcessExecution.create(sample_definition)
        
        assert execution.process_id == sample_definition.id
        assert execution.process_name == sample_definition.name
        assert execution.status == ExecutionStatus.PENDING
        assert len(execution.step_executions) == 2

    def test_create_with_input_data(self, sample_definition):
        """ProcessExecution stores input data."""
        execution = ProcessExecution.create(
            sample_definition,
            input_data={"topic": "AI", "length": 1000},
        )
        
        assert execution.input_data == {"topic": "AI", "length": 1000}

    def test_create_with_triggered_by(self, sample_definition):
        """ProcessExecution tracks trigger source."""
        execution = ProcessExecution.create(
            sample_definition,
            triggered_by="schedule",
        )
        
        assert execution.triggered_by == "schedule"

    def test_create_initializes_step_executions(self, sample_definition):
        """All steps get StepExecution entries."""
        execution = ProcessExecution.create(sample_definition)
        
        assert "step-a" in execution.step_executions
        assert "step-b" in execution.step_executions
        assert execution.step_executions["step-a"].status == StepStatus.PENDING
        assert execution.step_executions["step-b"].status == StepStatus.PENDING


# =============================================================================
# ProcessExecution State Transitions
# =============================================================================


class TestProcessExecutionStateTransitions:
    """Tests for ProcessExecution state transitions."""

    def test_start_from_pending(self, sample_definition):
        """Can start execution from PENDING."""
        execution = ProcessExecution.create(sample_definition)
        
        execution.start()
        
        assert execution.status == ExecutionStatus.RUNNING
        assert execution.started_at is not None

    def test_start_from_running_raises(self, sample_definition):
        """Cannot start already running execution."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        
        with pytest.raises(InvalidExecutionStateError):
            execution.start()

    def test_complete_from_running(self, sample_definition):
        """Can complete execution from RUNNING."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        
        execution.complete(output_data={"result": "success"})
        
        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.completed_at is not None
        assert execution.output_data["result"] == "success"

    def test_complete_from_pending_raises(self, sample_definition):
        """Cannot complete execution from PENDING."""
        execution = ProcessExecution.create(sample_definition)
        
        with pytest.raises(InvalidExecutionStateError):
            execution.complete()

    def test_fail_from_running(self, sample_definition):
        """Can fail execution from RUNNING."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        
        execution.fail("Step timeout exceeded")
        
        assert execution.status == ExecutionStatus.FAILED
        assert execution.output_data["error"] == "Step timeout exceeded"

    def test_cancel_from_running(self, sample_definition):
        """Can cancel execution from RUNNING."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        
        execution.cancel("No longer needed")
        
        assert execution.status == ExecutionStatus.CANCELLED
        assert "cancelled_reason" in execution.output_data

    def test_cancel_from_pending(self, sample_definition):
        """Can cancel execution from PENDING."""
        execution = ProcessExecution.create(sample_definition)
        
        execution.cancel("Changed requirements")
        
        assert execution.status == ExecutionStatus.CANCELLED

    def test_cancel_from_completed_raises(self, sample_definition):
        """Cannot cancel completed execution."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        execution.complete()
        
        with pytest.raises(InvalidExecutionStateError):
            execution.cancel()

    def test_pause_from_running(self, sample_definition):
        """Can pause execution from RUNNING."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        
        execution.pause()
        
        assert execution.status == ExecutionStatus.PAUSED

    def test_resume_from_paused(self, sample_definition):
        """Can resume execution from PAUSED."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        execution.pause()
        
        execution.resume()
        
        assert execution.status == ExecutionStatus.RUNNING


# =============================================================================
# Step Operations
# =============================================================================


class TestStepOperations:
    """Tests for step-level operations on ProcessExecution."""

    def test_start_step(self, sample_definition):
        """Can start a step."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        
        execution.start_step(StepId("step-a"))
        
        step_exec = execution.step_executions["step-a"]
        assert step_exec.status == StepStatus.RUNNING
        assert step_exec.started_at is not None

    def test_complete_step(self, sample_definition):
        """Can complete a step with output."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        execution.start_step(StepId("step-a"))
        
        execution.complete_step(StepId("step-a"), {"summary": "Done"})
        
        step_exec = execution.step_executions["step-a"]
        assert step_exec.status == StepStatus.COMPLETED
        assert step_exec.output == {"summary": "Done"}

    def test_fail_step(self, sample_definition):
        """Can fail a step."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        execution.start_step(StepId("step-a"))
        
        execution.fail_step(StepId("step-a"), "Timeout")
        
        step_exec = execution.step_executions["step-a"]
        assert step_exec.status == StepStatus.FAILED
        assert step_exec.error["message"] == "Timeout"

    def test_add_cost(self, sample_definition):
        """Can accumulate costs."""
        execution = ProcessExecution.create(sample_definition)
        
        execution.add_cost(Money.from_float(0.05))
        execution.add_cost(Money.from_float(0.10))
        
        assert execution.total_cost.amount == Money.from_float(0.15).amount


# =============================================================================
# Query Methods
# =============================================================================


class TestQueryMethods:
    """Tests for ProcessExecution query methods."""

    def test_get_completed_step_ids(self, sample_definition):
        """get_completed_step_ids returns correct IDs."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        execution.start_step(StepId("step-a"))
        execution.complete_step(StepId("step-a"), {})
        
        completed = execution.get_completed_step_ids()
        
        assert "step-a" in completed
        assert "step-b" not in completed

    def test_get_pending_step_ids(self, sample_definition):
        """get_pending_step_ids returns correct IDs."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        execution.start_step(StepId("step-a"))
        
        pending = execution.get_pending_step_ids()
        
        assert "step-a" not in pending  # Running, not pending
        assert "step-b" in pending

    def test_all_steps_completed_false(self, sample_definition):
        """all_steps_completed returns False when steps remain."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        execution.start_step(StepId("step-a"))
        execution.complete_step(StepId("step-a"), {})
        
        assert not execution.all_steps_completed()

    def test_all_steps_completed_true(self, sample_definition):
        """all_steps_completed returns True when all done."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        
        execution.start_step(StepId("step-a"))
        execution.complete_step(StepId("step-a"), {})
        execution.start_step(StepId("step-b"))
        execution.complete_step(StepId("step-b"), {})
        
        assert execution.all_steps_completed()

    def test_duration(self, sample_definition):
        """duration calculates correctly when completed."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        execution.complete()
        
        # Duration should be set (very small in test)
        assert execution.duration is not None
        assert execution.duration.seconds >= 0


# =============================================================================
# Serialization
# =============================================================================


class TestSerialization:
    """Tests for ProcessExecution serialization."""

    def test_to_dict(self, sample_definition):
        """to_dict produces correct structure."""
        execution = ProcessExecution.create(
            sample_definition,
            input_data={"topic": "AI"},
        )
        execution.start()
        
        d = execution.to_dict()
        
        assert d["process_name"] == "test-process"
        assert d["status"] == "running"
        assert d["input_data"] == {"topic": "AI"}
        assert "step-a" in d["step_executions"]
        assert d["started_at"] is not None

    def test_from_dict_roundtrip(self, sample_definition):
        """Can serialize and deserialize."""
        original = ProcessExecution.create(sample_definition)
        original.start()
        original.start_step(StepId("step-a"))
        original.complete_step(StepId("step-a"), {"result": "done"})
        
        d = original.to_dict()
        restored = ProcessExecution.from_dict(d)
        
        assert restored.id == original.id
        assert restored.status == original.status
        assert restored.step_executions["step-a"].status == StepStatus.COMPLETED


# =============================================================================
# StepExecution Tests
# =============================================================================


class TestStepExecution:
    """Tests for StepExecution entity."""

    def test_start(self):
        """StepExecution.start() sets status and timestamp."""
        step = StepExecution(step_id=StepId("test"))
        
        step.start()
        
        assert step.status == StepStatus.RUNNING
        assert step.started_at is not None

    def test_complete(self):
        """StepExecution.complete() sets output."""
        step = StepExecution(step_id=StepId("test"))
        step.start()
        
        step.complete({"answer": 42})
        
        assert step.status == StepStatus.COMPLETED
        assert step.output == {"answer": 42}
        assert step.completed_at is not None

    def test_record_attempt_failure_increments_retry(self):
        """StepExecution.record_attempt_failure() increments retry count."""
        step = StepExecution(step_id=StepId("test"))
        step.start()

        # Record retry attempts (step stays RUNNING)
        step.record_attempt_failure("Error 1")
        assert step.retry_count == 1
        assert step.status == StepStatus.RUNNING  # Still running, not failed

        step.record_attempt_failure("Error 2")
        assert step.retry_count == 2

        # Final failure (all retries exhausted)
        step.fail("Final error")
        assert step.status == StepStatus.FAILED
        assert step.retry_count == 2  # Not incremented by fail()

    def test_skip(self):
        """StepExecution.skip() sets status and reason."""
        step = StepExecution(step_id=StepId("test"))
        
        step.skip("condition_not_met")
        
        assert step.status == StepStatus.SKIPPED
        assert step.output["skipped_reason"] == "condition_not_met"

    def test_duration(self):
        """StepExecution.duration calculates correctly."""
        step = StepExecution(step_id=StepId("test"))
        step.start()
        step.complete({})
        
        assert step.duration is not None
        assert step.duration.seconds >= 0

    def test_to_dict(self):
        """StepExecution.to_dict() works correctly."""
        step = StepExecution(step_id=StepId("test"))
        step.start()
        step.complete({"result": "success"})
        
        d = step.to_dict()
        
        assert d["step_id"] == "test"
        assert d["status"] == "completed"
        assert d["output"] == {"result": "success"}
