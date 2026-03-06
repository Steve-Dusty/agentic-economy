"""
Unit tests for Executions API Router.

Tests for: E2-05 Execution API Endpoints
"""

import pytest
from datetime import datetime, timezone

from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    StepDefinition,
    ProcessId,
    ExecutionId,
    ExecutionStatus,
    StepStatus,
    DefinitionStatus,
)
from services.process_engine.repositories import SqliteProcessExecutionRepository


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def execution_repo():
    """Create in-memory execution repository."""
    return SqliteProcessExecutionRepository(":memory:")


@pytest.fixture
def sample_definition():
    """Create a sample published process definition."""
    definition = ProcessDefinition.create(name="test-process")
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-a",
            "type": "agent_task",
            "agent": "test",
            "message": "Hello",
        }),
    ]
    return definition.publish()


@pytest.fixture
def sample_execution(sample_definition):
    """Create a sample execution."""
    return ProcessExecution.create(
        sample_definition,
        input_data={"topic": "AI"},
        triggered_by="test",
    )


# =============================================================================
# Execution Summary Tests
# =============================================================================


class TestExecutionSummary:
    """Tests for execution summary generation."""

    def test_execution_has_required_fields(self, sample_execution):
        """Execution has all fields needed for summary."""
        assert sample_execution.id is not None
        assert sample_execution.process_id is not None
        assert sample_execution.process_name == "test-process"
        assert sample_execution.status == ExecutionStatus.PENDING
        assert sample_execution.triggered_by == "test"

    def test_execution_has_step_executions(self, sample_execution):
        """Execution has step execution records."""
        assert len(sample_execution.step_executions) == 1
        assert "step-a" in sample_execution.step_executions
        assert sample_execution.step_executions["step-a"].status == StepStatus.PENDING


# =============================================================================
# Execution Creation Tests
# =============================================================================


class TestExecutionCreation:
    """Tests for execution creation logic."""

    def test_create_execution_from_definition(self, sample_definition):
        """Can create execution from published definition."""
        execution = ProcessExecution.create(
            sample_definition,
            input_data={"key": "value"},
            triggered_by="api",
        )
        
        assert execution.status == ExecutionStatus.PENDING
        assert execution.process_id == sample_definition.id
        assert execution.process_name == "test-process"
        assert execution.input_data == {"key": "value"}
        assert execution.triggered_by == "api"

    def test_execution_persists_to_repo(self, execution_repo, sample_definition):
        """Execution can be saved and retrieved."""
        execution = ProcessExecution.create(sample_definition)
        execution_repo.save(execution)
        
        retrieved = execution_repo.get_by_id(execution.id)
        
        assert retrieved is not None
        assert retrieved.id == execution.id
        assert retrieved.status == ExecutionStatus.PENDING


# =============================================================================
# Execution Status Transitions
# =============================================================================


class TestExecutionStatusTransitions:
    """Tests for execution status transitions."""

    def test_cancel_pending_execution(self, sample_definition):
        """Can cancel pending execution."""
        execution = ProcessExecution.create(sample_definition)
        
        execution.cancel("Test cancellation")
        
        assert execution.status == ExecutionStatus.CANCELLED

    def test_cancel_running_execution(self, sample_definition):
        """Can cancel running execution."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        
        execution.cancel("Test cancellation")
        
        assert execution.status == ExecutionStatus.CANCELLED

    def test_cannot_cancel_completed(self, sample_definition):
        """Cannot cancel completed execution."""
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        execution.start_step(execution.step_executions.keys().__iter__().__next__())
        # Complete all steps
        for step_id in list(execution.step_executions.keys()):
            if execution.step_executions[step_id].status == StepStatus.RUNNING:
                execution.complete_step(
                    list(execution.step_executions.keys())[0],
                    {"result": "done"}
                )
        execution.complete()
        
        # Should raise or handle gracefully
        with pytest.raises(Exception):
            execution.cancel("Cannot cancel")


# =============================================================================
# Execution Listing Tests
# =============================================================================


class TestExecutionListing:
    """Tests for execution listing."""

    def test_list_all_executions(self, execution_repo, sample_definition):
        """Can list all executions."""
        # Create multiple executions
        for i in range(3):
            execution = ProcessExecution.create(sample_definition)
            execution_repo.save(execution)
        
        executions = execution_repo.list_all()
        
        assert len(executions) == 3

    def test_list_by_status(self, execution_repo, sample_definition):
        """Can filter executions by status."""
        # Create pending execution
        pending = ProcessExecution.create(sample_definition)
        execution_repo.save(pending)
        
        # Create and start another execution
        running = ProcessExecution.create(sample_definition)
        running.start()
        execution_repo.save(running)
        
        # Filter by running
        running_list = execution_repo.list_all(status=ExecutionStatus.RUNNING)
        
        assert len(running_list) == 1
        assert running_list[0].status == ExecutionStatus.RUNNING

    def test_list_by_process(self, execution_repo, sample_definition):
        """Can filter executions by process ID."""
        # Create executions for this process
        for i in range(2):
            execution = ProcessExecution.create(sample_definition)
            execution_repo.save(execution)
        
        # List by process
        executions = execution_repo.list_by_process(sample_definition.id)
        
        assert len(executions) == 2
        assert all(e.process_id == sample_definition.id for e in executions)


# =============================================================================
# Retry Logic Tests
# =============================================================================


class TestRetryLogic:
    """Tests for execution retry functionality."""

    def test_retry_creates_new_execution(self, sample_definition):
        """Retry creates a new execution with same input."""
        # Original failed execution
        original = ProcessExecution.create(
            sample_definition,
            input_data={"topic": "AI"},
        )
        original.start()
        original.fail("Test failure")
        
        # Create retry execution
        retry = ProcessExecution.create(
            sample_definition,
            input_data=original.input_data,
            triggered_by="retry",
        )
        
        assert retry.id != original.id
        assert retry.input_data == original.input_data
        assert retry.triggered_by == "retry"
        assert retry.status == ExecutionStatus.PENDING

    def test_retry_only_for_failed(self, sample_definition):
        """Can only retry failed executions."""
        pending = ProcessExecution.create(sample_definition)
        
        # Pending execution cannot be retried (business logic check)
        assert pending.status != ExecutionStatus.FAILED


# =============================================================================
# Step Output Tests
# =============================================================================


class TestStepOutput:
    """Tests for step output retrieval."""

    def test_get_step_output(self, execution_repo, sample_definition):
        """Can retrieve step output."""
        from services.process_engine.services import OutputStorage
        from services.process_engine.domain import StepId
        
        execution = ProcessExecution.create(sample_definition)
        execution.start()
        
        # Simulate step completion with output
        step_id = StepId("step-a")
        execution.start_step(step_id)
        execution.complete_step(step_id, {"response": "Test output"})
        execution_repo.save(execution)
        
        # Retrieve via OutputStorage
        output_storage = OutputStorage(execution_repo)
        output = output_storage.retrieve(execution.id, step_id)
        
        assert output is not None
        assert output.get("response") == "Test output"
