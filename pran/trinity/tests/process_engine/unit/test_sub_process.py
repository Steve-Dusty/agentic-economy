"""
Unit Tests for Sub-Process Feature (E10-01)

Tests SubProcessConfig, SubProcessHandler, and parent/child relationships.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.process_engine.domain import (
    StepType,
    Duration,
    Version,
    ProcessId,
    ExecutionId,
    StepId,
    ExecutionStatus,
    StepStatus,
    DefinitionStatus,
)
from services.process_engine.domain.step_configs import SubProcessConfig
from services.process_engine.domain.aggregates import ProcessDefinition, ProcessExecution
from services.process_engine.domain.entities import StepDefinition, StepExecution


class TestSubProcessConfig:
    """Tests for SubProcessConfig dataclass."""

    def test_create_basic(self):
        """Test creating a basic SubProcessConfig."""
        config = SubProcessConfig(process_name="child-process")

        assert config.process_name == "child-process"
        assert config.version is None
        assert config.input_mapping == {}
        assert config.output_key == "result"
        assert config.wait_for_completion is True
        assert config.timeout.seconds == 3600  # 1 hour default

    def test_create_with_all_options(self):
        """Test creating SubProcessConfig with all options."""
        config = SubProcessConfig(
            process_name="child-process",
            version="2.0",
            input_mapping={"child_topic": "{{input.topic}}"},
            output_key="child_result",
            wait_for_completion=True,
            timeout=Duration.from_minutes(30),
        )

        assert config.process_name == "child-process"
        assert config.version == "2.0"
        assert config.input_mapping == {"child_topic": "{{input.topic}}"}
        assert config.output_key == "child_result"
        assert config.timeout.seconds == 1800

    def test_from_dict(self):
        """Test creating SubProcessConfig from dictionary."""
        data = {
            "process_name": "research-subprocess",
            "version": "1.5",
            "input_mapping": {"query": "{{input.search_term}}"},
            "output_key": "research_result",
            "timeout": "45m",
        }

        config = SubProcessConfig.from_dict(data)

        assert config.process_name == "research-subprocess"
        assert config.version == "1.5"
        assert config.input_mapping == {"query": "{{input.search_term}}"}
        assert config.output_key == "research_result"
        assert config.timeout.seconds == 2700

    def test_from_dict_minimal(self):
        """Test creating SubProcessConfig with minimal data."""
        data = {"process_name": "simple-child"}

        config = SubProcessConfig.from_dict(data)

        assert config.process_name == "simple-child"
        assert config.version is None
        assert config.output_key == "result"

    def test_to_dict(self):
        """Test serializing SubProcessConfig to dictionary."""
        config = SubProcessConfig(
            process_name="child-process",
            version="1.0",
            input_mapping={"key": "value"},
            output_key="output",
            timeout=Duration.from_hours(2),
        )

        result = config.to_dict()

        assert result["process_name"] == "child-process"
        assert result["version"] == "1.0"
        assert result["input_mapping"] == {"key": "value"}
        assert result["output_key"] == "output"
        assert result["timeout"] == "2h"

    def test_immutability(self):
        """Test that SubProcessConfig is immutable (frozen)."""
        config = SubProcessConfig(process_name="test")

        with pytest.raises(AttributeError):
            config.process_name = "changed"


class TestStepDefinitionSubProcess:
    """Tests for StepDefinition with sub_process type."""

    def test_from_dict_sub_process(self):
        """Test parsing sub_process step from dictionary."""
        data = {
            "id": "call-child",
            "name": "Call Child Process",
            "type": "sub_process",
            "process_name": "data-enrichment",
            "version": "2.0",
            "input_mapping": {"data": "{{input.raw_data}}"},
            "output_key": "enriched_data",
            "timeout": "30m",
        }

        step = StepDefinition.from_dict(data)

        assert step.id == StepId("call-child")
        assert step.name == "Call Child Process"
        assert step.type == StepType.SUB_PROCESS
        assert isinstance(step.config, SubProcessConfig)
        assert step.config.process_name == "data-enrichment"
        assert step.config.version == "2.0"
        assert step.config.input_mapping == {"data": "{{input.raw_data}}"}

    def test_to_dict_sub_process(self):
        """Test serializing sub_process step to dictionary."""
        step = StepDefinition(
            id=StepId("call-child"),
            name="Call Child",
            type=StepType.SUB_PROCESS,
            config=SubProcessConfig(
                process_name="child",
                version="1.0",
                input_mapping={"x": "y"},
            ),
        )

        result = step.to_dict()

        assert result["id"] == "call-child"
        assert result["type"] == "sub_process"
        assert result["process_name"] == "child"
        assert result["version"] == "1.0"
        assert result["input_mapping"] == {"x": "y"}


class TestProcessExecutionParentChild:
    """Tests for ProcessExecution parent/child relationships."""

    def _create_mock_definition(self, name: str = "test-process") -> ProcessDefinition:
        """Create a mock ProcessDefinition for testing."""
        return ProcessDefinition(
            id=ProcessId.generate(),
            name=name,
            version=Version.initial(),
            status=DefinitionStatus.PUBLISHED,
            description="Test process",
            steps=[
                StepDefinition(
                    id=StepId("step-one"),
                    name="Step One",
                    type=StepType.AGENT_TASK,
                    config=MagicMock(),
                ),
            ],
        )

    def test_create_without_parent(self):
        """Test creating execution without parent (normal case)."""
        definition = self._create_mock_definition()

        execution = ProcessExecution.create(
            definition=definition,
            input_data={"key": "value"},
            triggered_by="manual",
        )

        assert execution.parent_execution_id is None
        assert execution.parent_step_id is None
        assert execution.child_execution_ids == []

    def test_create_with_parent(self):
        """Test creating sub-process execution with parent."""
        definition = self._create_mock_definition()
        parent_id = ExecutionId.generate()
        parent_step = StepId("call-subprocess")

        execution = ProcessExecution.create(
            definition=definition,
            input_data={"key": "value"},
            triggered_by="sub_process",
            parent_execution_id=parent_id,
            parent_step_id=parent_step,
        )

        assert execution.parent_execution_id == parent_id
        assert execution.parent_step_id == parent_step
        assert execution.triggered_by == "sub_process"

    def test_is_sub_process(self):
        """Test is_sub_process() method."""
        definition = self._create_mock_definition()

        # Normal execution
        normal_exec = ProcessExecution.create(definition=definition)
        assert normal_exec.is_sub_process() is False

        # Sub-process execution
        sub_exec = ProcessExecution.create(
            definition=definition,
            parent_execution_id=ExecutionId.generate(),
        )
        assert sub_exec.is_sub_process() is True

    def test_add_child_execution(self):
        """Test adding child execution IDs."""
        definition = self._create_mock_definition()
        execution = ProcessExecution.create(definition=definition)

        child1 = ExecutionId.generate()
        child2 = ExecutionId.generate()

        execution.add_child_execution(child1)
        execution.add_child_execution(child2)

        assert len(execution.child_execution_ids) == 2
        assert child1 in execution.child_execution_ids
        assert child2 in execution.child_execution_ids

    def test_add_child_execution_no_duplicates(self):
        """Test that duplicate child IDs are not added."""
        definition = self._create_mock_definition()
        execution = ProcessExecution.create(definition=definition)

        child_id = ExecutionId.generate()
        execution.add_child_execution(child_id)
        execution.add_child_execution(child_id)  # Add again

        assert len(execution.child_execution_ids) == 1

    def test_has_children(self):
        """Test has_children() method."""
        definition = self._create_mock_definition()
        execution = ProcessExecution.create(definition=definition)

        assert execution.has_children() is False

        execution.add_child_execution(ExecutionId.generate())
        assert execution.has_children() is True

    def test_to_dict_includes_parent_child(self):
        """Test that to_dict includes parent/child relationships."""
        definition = self._create_mock_definition()
        parent_id = ExecutionId.generate()
        parent_step = StepId("parent-step")
        child_id = ExecutionId.generate()

        execution = ProcessExecution.create(
            definition=definition,
            parent_execution_id=parent_id,
            parent_step_id=parent_step,
        )
        execution.add_child_execution(child_id)

        result = execution.to_dict()

        assert result["parent_execution_id"] == str(parent_id)
        assert result["parent_step_id"] == str(parent_step)
        assert result["child_execution_ids"] == [str(child_id)]

    def test_from_dict_restores_parent_child(self):
        """Test that from_dict restores parent/child relationships."""
        parent_id = ExecutionId.generate()
        child_id = ExecutionId.generate()

        data = {
            "id": str(ExecutionId.generate()),
            "process_id": str(ProcessId.generate()),
            "process_version": "1.0",
            "process_name": "test",
            "status": "completed",
            "parent_execution_id": str(parent_id),
            "parent_step_id": "parent-step",
            "child_execution_ids": [str(child_id)],
        }

        execution = ProcessExecution.from_dict(data)

        assert execution.parent_execution_id is not None
        assert str(execution.parent_execution_id) == str(parent_id)
        assert execution.parent_step_id == StepId("parent-step")
        assert len(execution.child_execution_ids) == 1


class TestSubProcessHandler:
    """Tests for SubProcessHandler execution logic."""

    @pytest.fixture
    def mock_definition_repo(self):
        """Create a mock definition repository."""
        repo = MagicMock()
        return repo

    @pytest.fixture
    def mock_engine(self):
        """Create a mock execution engine."""
        engine = MagicMock()
        engine.start = AsyncMock()
        return engine

    @pytest.fixture
    def mock_context(self):
        """Create a mock step context."""
        execution = MagicMock()
        execution.id = ExecutionId.generate()
        execution.process_name = "parent-process"

        step_def = MagicMock()
        step_def.id = StepId("call-child")

        context = MagicMock()
        context.execution = execution
        context.step_definition = step_def
        context.input_data = {"topic": "AI research"}
        context.step_outputs = {}

        return context

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_definition_repo, mock_engine, mock_context):
        """Test successful sub-process execution."""
        from services.process_engine.engine.handlers.sub_process import SubProcessHandler
        from services.process_engine.domain import Money

        # Set up mock child definition
        child_definition = MagicMock()
        child_definition.id = ProcessId.generate()
        child_definition.name = "child-process"
        child_definition.version = Version.initial()
        child_definition.status = DefinitionStatus.PUBLISHED

        mock_definition_repo.get_latest_version.return_value = child_definition

        # Set up mock child execution result
        child_execution = MagicMock()
        child_execution.id = ExecutionId.generate()
        child_execution.status = MagicMock()
        child_execution.status.value = "completed"
        child_execution.output_data = {"result": "processed data"}
        child_execution.duration = Duration.from_seconds(30)
        child_execution.total_cost = Money.from_float(0.05)

        mock_engine.start.return_value = child_execution

        # Create handler and execute
        handler = SubProcessHandler(
            definition_repo=mock_definition_repo,
            engine_factory=lambda: mock_engine,
        )

        config = SubProcessConfig(process_name="child-process")
        result = await handler.execute(mock_context, config)

        # Verify success
        assert result.success is True
        assert result.output["child_process_name"] == "child-process"
        assert result.output["result"] == {"result": "processed data"}
        assert "child_execution_id" in result.output

    @pytest.mark.asyncio
    async def test_execute_process_not_found(self, mock_definition_repo, mock_engine, mock_context):
        """Test sub-process execution when child process not found."""
        from services.process_engine.engine.handlers.sub_process import SubProcessHandler

        mock_definition_repo.get_latest_version.return_value = None

        handler = SubProcessHandler(
            definition_repo=mock_definition_repo,
            engine_factory=lambda: mock_engine,
        )

        config = SubProcessConfig(process_name="nonexistent-process")
        result = await handler.execute(mock_context, config)

        assert result.success is False
        assert "not found" in result.error.lower()
        assert result.error_code == "PROCESS_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_execute_child_failed(self, mock_definition_repo, mock_engine, mock_context):
        """Test sub-process execution when child process fails."""
        from services.process_engine.engine.handlers.sub_process import SubProcessHandler

        # Set up mock child definition
        child_definition = MagicMock()
        child_definition.id = ProcessId.generate()
        child_definition.name = "child-process"
        child_definition.status = DefinitionStatus.PUBLISHED

        mock_definition_repo.get_latest_version.return_value = child_definition

        # Set up mock failed child execution
        child_execution = MagicMock()
        child_execution.status = MagicMock()
        child_execution.status.value = "failed"
        child_execution.output_data = {"error": "Child process error"}

        mock_engine.start.return_value = child_execution

        handler = SubProcessHandler(
            definition_repo=mock_definition_repo,
            engine_factory=lambda: mock_engine,
        )

        config = SubProcessConfig(process_name="child-process")
        result = await handler.execute(mock_context, config)

        assert result.success is False
        assert result.error_code == "SUB_PROCESS_FAILED"

    @pytest.mark.asyncio
    async def test_execute_missing_repo(self, mock_context):
        """Test execution fails gracefully when repo not configured."""
        from services.process_engine.engine.handlers.sub_process import SubProcessHandler

        handler = SubProcessHandler()  # No repo configured

        config = SubProcessConfig(process_name="child")
        result = await handler.execute(mock_context, config)

        assert result.success is False
        assert result.error_code == "CONFIGURATION_ERROR"

    def test_step_type(self):
        """Test that handler reports correct step type."""
        from services.process_engine.engine.handlers.sub_process import SubProcessHandler

        handler = SubProcessHandler()
        assert handler.step_type == StepType.SUB_PROCESS
