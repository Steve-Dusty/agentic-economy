"""
Unit tests for Step Output Storage Service.

Tests for: E2-06 Step Output Storage
"""

import pytest

from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    ExecutionId,
    StepId,
    StepDefinition,
)
from services.process_engine.repositories import SqliteProcessExecutionRepository
from services.process_engine.services import OutputStorage, OutputPath


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def execution_repo():
    """Create an in-memory execution repository."""
    return SqliteProcessExecutionRepository(":memory:")


@pytest.fixture
def storage(execution_repo):
    """Create output storage with in-memory repository."""
    return OutputStorage(execution_repo)


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
def sample_execution(sample_definition, execution_repo):
    """Create and save a sample execution."""
    execution = ProcessExecution.create(sample_definition)
    execution_repo.save(execution)
    return execution


# =============================================================================
# OutputPath Tests
# =============================================================================


class TestOutputPath:
    """Tests for OutputPath value object."""

    def test_str(self):
        """OutputPath converts to string correctly."""
        exec_id = ExecutionId.generate()
        path = OutputPath(
            execution_id=exec_id,
            step_id=StepId("step-a"),
        )
        
        assert f"/executions/{exec_id}/steps/step-a/output" in str(path)

    def test_from_string(self):
        """OutputPath parses from string correctly."""
        exec_id = ExecutionId.generate()
        path = OutputPath.from_string(f"/executions/{exec_id}/steps/step-a/output")
        
        assert path.execution_id == exec_id
        assert str(path.step_id) == "step-a"

    def test_from_string_without_leading_slash(self):
        """OutputPath parses without leading slash."""
        exec_id = ExecutionId.generate()
        path = OutputPath.from_string(f"executions/{exec_id}/steps/step-a/output")
        
        assert path.execution_id == exec_id
        assert str(path.step_id) == "step-a"

    def test_from_string_invalid_format(self):
        """Invalid path format raises error."""
        with pytest.raises(ValueError):
            OutputPath.from_string("/invalid/path")

    def test_from_string_wrong_structure(self):
        """Wrong path structure raises error."""
        with pytest.raises(ValueError):
            OutputPath.from_string("/steps/step-a/output")


# =============================================================================
# Store/Retrieve Tests
# =============================================================================


class TestStoreRetrieve:
    """Tests for storing and retrieving outputs."""

    def test_store_and_retrieve(self, storage, sample_execution):
        """Can store and retrieve output."""
        output = {"result": "success", "count": 42}
        
        path = storage.store(sample_execution.id, StepId("step-a"), output)
        retrieved = storage.retrieve(sample_execution.id, StepId("step-a"))
        
        assert retrieved == output
        assert str(path.step_id) == "step-a"

    def test_retrieve_nonexistent_execution(self, storage):
        """Retrieve returns None for nonexistent execution."""
        result = storage.retrieve(ExecutionId.generate(), StepId("step-a"))
        
        assert result is None

    def test_retrieve_nonexistent_step(self, storage, sample_execution):
        """Retrieve returns None for nonexistent step."""
        result = storage.retrieve(sample_execution.id, StepId("nonexistent"))
        
        assert result is None

    def test_retrieve_no_output(self, storage, sample_execution):
        """Retrieve returns None when no output stored."""
        result = storage.retrieve(sample_execution.id, StepId("step-a"))
        
        assert result is None

    def test_retrieve_by_path(self, storage, sample_execution):
        """Can retrieve by path string."""
        output = {"data": "test"}
        storage.store(sample_execution.id, StepId("step-a"), output)
        
        path_str = f"/executions/{sample_execution.id}/steps/step-a/output"
        retrieved = storage.retrieve_by_path(path_str)
        
        assert retrieved == output

    def test_store_overwrites(self, storage, sample_execution):
        """Storing again overwrites previous output."""
        storage.store(sample_execution.id, StepId("step-a"), {"first": True})
        storage.store(sample_execution.id, StepId("step-a"), {"second": True})
        
        retrieved = storage.retrieve(sample_execution.id, StepId("step-a"))
        
        assert retrieved == {"second": True}
        assert "first" not in retrieved


# =============================================================================
# Bulk Operations Tests
# =============================================================================


class TestBulkOperations:
    """Tests for bulk operations."""

    def test_get_all_outputs(self, storage, sample_execution):
        """Can get all outputs for an execution."""
        storage.store(sample_execution.id, StepId("step-a"), {"a": 1})
        storage.store(sample_execution.id, StepId("step-b"), {"b": 2})
        
        outputs = storage.get_all_outputs(sample_execution.id)
        
        assert len(outputs) == 2
        assert outputs["step-a"] == {"a": 1}
        assert outputs["step-b"] == {"b": 2}

    def test_get_all_outputs_empty(self, storage, sample_execution):
        """Get all outputs returns empty dict when none stored."""
        outputs = storage.get_all_outputs(sample_execution.id)
        
        assert outputs == {}

    def test_get_all_outputs_nonexistent_execution(self, storage):
        """Get all outputs returns empty dict for nonexistent execution."""
        outputs = storage.get_all_outputs(ExecutionId.generate())
        
        assert outputs == {}

    def test_clear_execution_outputs(self, storage, sample_execution):
        """Can clear all outputs for an execution."""
        storage.store(sample_execution.id, StepId("step-a"), {"a": 1})
        storage.store(sample_execution.id, StepId("step-b"), {"b": 2})
        
        count = storage.clear_execution_outputs(sample_execution.id)
        
        assert count == 2
        assert storage.get_all_outputs(sample_execution.id) == {}


# =============================================================================
# Existence/Deletion Tests
# =============================================================================


class TestExistenceAndDeletion:
    """Tests for exists and delete operations."""

    def test_exists_true(self, storage, sample_execution):
        """Exists returns True when output stored."""
        storage.store(sample_execution.id, StepId("step-a"), {"data": 1})
        
        assert storage.exists(sample_execution.id, StepId("step-a")) is True

    def test_exists_false(self, storage, sample_execution):
        """Exists returns False when no output stored."""
        assert storage.exists(sample_execution.id, StepId("step-a")) is False

    def test_delete_existing(self, storage, sample_execution):
        """Can delete existing output."""
        storage.store(sample_execution.id, StepId("step-a"), {"data": 1})
        
        result = storage.delete(sample_execution.id, StepId("step-a"))
        
        assert result is True
        assert storage.exists(sample_execution.id, StepId("step-a")) is False

    def test_delete_nonexistent(self, storage, sample_execution):
        """Delete returns False for nonexistent output."""
        result = storage.delete(sample_execution.id, StepId("step-a"))
        
        assert result is False


# =============================================================================
# Complex Output Tests
# =============================================================================


class TestComplexOutputs:
    """Tests for complex output data types."""

    def test_nested_dict(self, storage, sample_execution):
        """Can store nested dictionary."""
        output = {
            "level1": {
                "level2": {
                    "level3": "deep value"
                }
            }
        }
        
        storage.store(sample_execution.id, StepId("step-a"), output)
        retrieved = storage.retrieve(sample_execution.id, StepId("step-a"))
        
        assert retrieved == output

    def test_list_output(self, storage, sample_execution):
        """Can store list output."""
        output = [1, 2, 3, {"nested": True}]
        
        storage.store(sample_execution.id, StepId("step-a"), output)
        retrieved = storage.retrieve(sample_execution.id, StepId("step-a"))
        
        assert retrieved == output

    def test_mixed_types(self, storage, sample_execution):
        """Can store output with mixed types."""
        output = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
        }
        
        storage.store(sample_execution.id, StepId("step-a"), output)
        retrieved = storage.retrieve(sample_execution.id, StepId("step-a"))
        
        assert retrieved == output

    def test_string_output(self, storage, sample_execution):
        """Can store string output."""
        output = "Just a plain string output"
        
        storage.store(sample_execution.id, StepId("step-a"), output)
        retrieved = storage.retrieve(sample_execution.id, StepId("step-a"))
        
        assert retrieved == output
