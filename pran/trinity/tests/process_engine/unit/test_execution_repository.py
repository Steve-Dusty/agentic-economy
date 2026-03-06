"""
Unit tests for ProcessExecution Repository.

Tests for: E2-02 Execution Repository
"""

import pytest
from datetime import datetime, timezone

from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    ProcessId,
    ExecutionId,
    ExecutionStatus,
    StepDefinition,
    StepId,
    StepStatus,
    Money,
)
from services.process_engine.repositories import SqliteProcessExecutionRepository


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def repository():
    """Create an in-memory repository for testing."""
    return SqliteProcessExecutionRepository(":memory:")


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


@pytest.fixture
def sample_execution(sample_definition):
    """Create a sample execution."""
    return ProcessExecution.create(
        sample_definition,
        input_data={"topic": "AI"},
        triggered_by="test",
    )


# =============================================================================
# CRUD Tests
# =============================================================================


class TestCrudOperations:
    """Tests for basic CRUD operations."""

    def test_save_and_get_by_id(self, repository, sample_execution):
        """Can save and retrieve an execution."""
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_execution.id
        assert retrieved.process_name == sample_execution.process_name
        assert retrieved.status == sample_execution.status

    def test_get_by_id_not_found(self, repository):
        """Returns None for non-existent execution."""
        non_existent = ExecutionId.generate()
        
        retrieved = repository.get_by_id(non_existent)
        
        assert retrieved is None

    def test_save_updates_existing(self, repository, sample_execution):
        """Save updates existing execution."""
        repository.save(sample_execution)
        
        # Modify execution
        sample_execution.start()
        sample_execution.start_step(StepId("step-a"))
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        assert retrieved.status == ExecutionStatus.RUNNING
        assert retrieved.step_executions["step-a"].status == StepStatus.RUNNING

    def test_delete(self, repository, sample_execution):
        """Can delete an execution."""
        repository.save(sample_execution)
        
        result = repository.delete(sample_execution.id)
        
        assert result is True
        assert repository.get_by_id(sample_execution.id) is None

    def test_delete_not_found(self, repository):
        """Delete returns False for non-existent."""
        non_existent = ExecutionId.generate()
        
        result = repository.delete(non_existent)
        
        assert result is False

    def test_exists(self, repository, sample_execution):
        """Can check if execution exists."""
        assert not repository.exists(sample_execution.id)
        
        repository.save(sample_execution)
        
        assert repository.exists(sample_execution.id)

    def test_count(self, repository, sample_execution):
        """Can count executions."""
        assert repository.count() == 0
        
        repository.save(sample_execution)
        
        assert repository.count() == 1


# =============================================================================
# Query Tests
# =============================================================================


class TestQueryOperations:
    """Tests for query operations."""

    def test_list_all(self, repository, sample_definition):
        """Can list all executions."""
        # Create multiple executions
        exec1 = ProcessExecution.create(sample_definition)
        exec2 = ProcessExecution.create(sample_definition)
        repository.save(exec1)
        repository.save(exec2)
        
        results = repository.list_all()
        
        assert len(results) == 2

    def test_list_all_with_limit(self, repository, sample_definition):
        """List respects limit."""
        for _ in range(5):
            repository.save(ProcessExecution.create(sample_definition))
        
        results = repository.list_all(limit=3)
        
        assert len(results) == 3

    def test_list_all_with_offset(self, repository, sample_definition):
        """List respects offset."""
        for _ in range(5):
            repository.save(ProcessExecution.create(sample_definition))
        
        results = repository.list_all(limit=10, offset=2)
        
        assert len(results) == 3

    def test_list_all_filter_by_status(self, repository, sample_definition):
        """Can filter by status."""
        pending = ProcessExecution.create(sample_definition)
        
        running = ProcessExecution.create(sample_definition)
        running.start()
        
        completed = ProcessExecution.create(sample_definition)
        completed.start()
        completed.complete()
        
        repository.save(pending)
        repository.save(running)
        repository.save(completed)
        
        pending_list = repository.list_all(status=ExecutionStatus.PENDING)
        running_list = repository.list_all(status=ExecutionStatus.RUNNING)
        completed_list = repository.list_all(status=ExecutionStatus.COMPLETED)
        
        assert len(pending_list) == 1
        assert len(running_list) == 1
        assert len(completed_list) == 1

    def test_list_by_process(self, repository, sample_definition):
        """Can list executions for a specific process."""
        # Create executions for our process
        exec1 = ProcessExecution.create(sample_definition)
        exec2 = ProcessExecution.create(sample_definition)
        repository.save(exec1)
        repository.save(exec2)
        
        # Create execution for different process
        other_def = ProcessDefinition.create(name="other-process")
        other_def.steps = [StepDefinition.from_dict({
            "id": "other-step", "type": "agent_task", "agent": "test", "message": "test"
        })]
        other_exec = ProcessExecution.create(other_def)
        repository.save(other_exec)
        
        results = repository.list_by_process(sample_definition.id)
        
        assert len(results) == 2
        for r in results:
            assert r.process_id == sample_definition.id

    def test_list_active(self, repository, sample_definition):
        """Can list active executions."""
        # Create different status executions
        pending = ProcessExecution.create(sample_definition)
        
        running = ProcessExecution.create(sample_definition)
        running.start()
        
        paused = ProcessExecution.create(sample_definition)
        paused.start()
        paused.pause()
        
        completed = ProcessExecution.create(sample_definition)
        completed.start()
        completed.complete()
        
        repository.save(pending)
        repository.save(running)
        repository.save(paused)
        repository.save(completed)
        
        active = repository.list_active()
        
        # Active means pending, running, or paused
        assert len(active) == 3
        statuses = {e.status for e in active}
        assert ExecutionStatus.COMPLETED not in statuses


# =============================================================================
# Serialization Tests
# =============================================================================


class TestSerialization:
    """Tests for serialization/deserialization."""

    def test_input_data_preserved(self, repository, sample_execution):
        """Input data is preserved through save/load."""
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        
        assert retrieved.input_data == {"topic": "AI"}

    def test_output_data_preserved(self, repository, sample_execution):
        """Output data is preserved through save/load."""
        sample_execution.start()
        sample_execution.complete(output_data={"result": "success", "count": 42})
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        
        assert retrieved.output_data["result"] == "success"
        assert retrieved.output_data["count"] == 42

    def test_step_executions_preserved(self, repository, sample_execution):
        """Step execution states are preserved."""
        sample_execution.start()
        sample_execution.start_step(StepId("step-a"))
        sample_execution.complete_step(StepId("step-a"), {"output": "done"})
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        
        step_a = retrieved.step_executions.get("step-a")
        assert step_a is not None
        assert step_a.status == StepStatus.COMPLETED
        assert step_a.output == {"output": "done"}

    def test_timestamps_preserved(self, repository, sample_execution):
        """Timestamps are preserved through save/load."""
        sample_execution.start()
        sample_execution.complete()
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        
        assert retrieved.started_at is not None
        assert retrieved.completed_at is not None

    def test_total_cost_preserved(self, repository, sample_execution):
        """Total cost is preserved through save/load."""
        sample_execution.add_cost(Money.from_float(0.05))
        sample_execution.add_cost(Money.from_float(0.10))
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        
        assert retrieved.total_cost.amount == Money.from_float(0.15).amount

    def test_triggered_by_preserved(self, repository, sample_execution):
        """Triggered_by field is preserved."""
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        
        assert retrieved.triggered_by == "test"

    def test_process_version_preserved(self, repository, sample_execution):
        """Process version is preserved."""
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        
        assert str(retrieved.process_version) == str(sample_execution.process_version)


# =============================================================================
# Concurrency Tests
# =============================================================================


class TestConcurrency:
    """Tests for concurrent access patterns."""

    def test_multiple_updates(self, repository, sample_execution):
        """Multiple updates work correctly."""
        repository.save(sample_execution)
        
        sample_execution.start()
        repository.save(sample_execution)
        
        sample_execution.start_step(StepId("step-a"))
        repository.save(sample_execution)
        
        sample_execution.complete_step(StepId("step-a"), {"done": True})
        repository.save(sample_execution)
        
        sample_execution.start_step(StepId("step-b"))
        repository.save(sample_execution)
        
        sample_execution.complete_step(StepId("step-b"), {"also_done": True})
        repository.save(sample_execution)
        
        sample_execution.complete()
        repository.save(sample_execution)
        
        retrieved = repository.get_by_id(sample_execution.id)
        
        assert retrieved.status == ExecutionStatus.COMPLETED
        assert retrieved.step_executions["step-a"].status == StepStatus.COMPLETED
        assert retrieved.step_executions["step-b"].status == StepStatus.COMPLETED
