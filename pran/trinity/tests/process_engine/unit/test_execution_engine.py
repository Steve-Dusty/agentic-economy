"""
Unit tests for Execution Engine.

Tests for: E2-03 Sequential Step Executor
"""

import pytest
import asyncio
from typing import Any

from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    StepDefinition,
    StepId,
    StepType,
    ExecutionStatus,
    StepStatus,
)
from services.process_engine.repositories import SqliteProcessExecutionRepository
from services.process_engine.services import OutputStorage
from services.process_engine.events import InMemoryEventBus
from services.process_engine.engine import (
    ExecutionEngine,
    DependencyResolver,
    StepHandler,
    StepHandlerRegistry,
)
from services.process_engine.engine.step_handler import StepResult, StepContext, StepConfig


# =============================================================================
# Mock Step Handler
# =============================================================================


class MockAgentHandler(StepHandler):
    """Mock handler for testing."""
    
    def __init__(self, results: dict[str, StepResult] = None):
        self.results = results or {}
        self.executed_steps = []
    
    @property
    def step_type(self) -> StepType:
        return StepType.AGENT_TASK
    
    async def execute(self, context: StepContext, config: StepConfig) -> StepResult:
        step_id = str(context.step_definition.id)
        self.executed_steps.append(step_id)
        
        if step_id in self.results:
            return self.results[step_id]
        
        # Default success
        return StepResult.ok({"step_id": step_id, "result": "done"})


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def execution_repo():
    """Create in-memory execution repository."""
    return SqliteProcessExecutionRepository(":memory:")


@pytest.fixture
def event_bus():
    """Create in-memory event bus."""
    return InMemoryEventBus()


@pytest.fixture
def output_storage(execution_repo):
    """Create output storage with in-memory repo."""
    return OutputStorage(execution_repo)


@pytest.fixture
def mock_handler():
    """Create mock step handler."""
    return MockAgentHandler()


@pytest.fixture
def handler_registry(mock_handler):
    """Create handler registry with mock handler."""
    registry = StepHandlerRegistry()
    registry.register(mock_handler)
    return registry


@pytest.fixture
def simple_definition():
    """Create a simple single-step process."""
    definition = ProcessDefinition.create(name="simple-process")
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
def sequential_definition():
    """Create a sequential two-step process."""
    definition = ProcessDefinition.create(name="sequential-process")
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-a",
            "type": "agent_task",
            "agent": "test",
            "message": "First",
        }),
        StepDefinition.from_dict({
            "id": "step-b",
            "type": "agent_task",
            "agent": "test",
            "message": "Second",
            "depends_on": ["step-a"],
        }),
    ]
    return definition.publish()


@pytest.fixture
def parallel_definition():
    """Create a process with parallel steps then join."""
    definition = ProcessDefinition.create(name="parallel-process")
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-a",
            "type": "agent_task",
            "agent": "test",
            "message": "Branch A",
        }),
        StepDefinition.from_dict({
            "id": "step-b",
            "type": "agent_task",
            "agent": "test",
            "message": "Branch B",
        }),
        StepDefinition.from_dict({
            "id": "step-c",
            "type": "agent_task",
            "agent": "test",
            "message": "Join",
            "depends_on": ["step-a", "step-b"],
        }),
    ]
    return definition.publish()


# =============================================================================
# DependencyResolver Tests
# =============================================================================


class TestDependencyResolver:
    """Tests for DependencyResolver."""

    def test_get_ready_steps_no_deps(self, simple_definition):
        """Steps without dependencies are ready immediately."""
        execution = ProcessExecution.create(simple_definition)
        resolver = DependencyResolver(simple_definition)
        
        ready = resolver.get_ready_steps(execution)
        
        assert len(ready) == 1
        assert str(ready[0]) == "step-a"

    def test_get_ready_steps_with_deps(self, sequential_definition):
        """Steps with unmet dependencies are not ready."""
        execution = ProcessExecution.create(sequential_definition)
        resolver = DependencyResolver(sequential_definition)
        
        ready = resolver.get_ready_steps(execution)
        
        # Only step-a should be ready (step-b depends on step-a)
        assert len(ready) == 1
        assert str(ready[0]) == "step-a"

    def test_get_ready_steps_after_completion(self, sequential_definition):
        """Steps become ready when dependencies complete."""
        execution = ProcessExecution.create(sequential_definition)
        execution.start()
        execution.start_step(StepId("step-a"))
        execution.complete_step(StepId("step-a"), {"done": True})
        
        resolver = DependencyResolver(sequential_definition)
        ready = resolver.get_ready_steps(execution)
        
        # Now step-b should be ready
        assert len(ready) == 1
        assert str(ready[0]) == "step-b"

    def test_get_ready_steps_parallel(self, parallel_definition):
        """Multiple steps without deps are all ready."""
        execution = ProcessExecution.create(parallel_definition)
        resolver = DependencyResolver(parallel_definition)
        
        ready = resolver.get_ready_steps(execution)
        
        # step-a and step-b are both ready (step-c depends on both)
        assert len(ready) == 2
        step_ids = {str(s) for s in ready}
        assert step_ids == {"step-a", "step-b"}

    def test_get_execution_order(self, sequential_definition):
        """Execution order respects dependencies."""
        resolver = DependencyResolver(sequential_definition)
        
        order = resolver.get_execution_order()
        
        # step-a must come before step-b
        order_str = [str(s) for s in order]
        assert order_str.index("step-a") < order_str.index("step-b")

    def test_is_complete_false(self, simple_definition):
        """is_complete returns False when steps remain."""
        execution = ProcessExecution.create(simple_definition)
        resolver = DependencyResolver(simple_definition)
        
        assert resolver.is_complete(execution) is False

    def test_is_complete_true(self, simple_definition):
        """is_complete returns True when all steps done."""
        execution = ProcessExecution.create(simple_definition)
        execution.start()
        execution.start_step(StepId("step-a"))
        execution.complete_step(StepId("step-a"), {})
        
        resolver = DependencyResolver(simple_definition)
        
        assert resolver.is_complete(execution) is True


# =============================================================================
# ExecutionEngine Tests
# =============================================================================


class TestExecutionEngineStart:
    """Tests for starting executions."""

    @pytest.mark.asyncio
    async def test_start_simple_process(
        self, execution_repo, handler_registry, simple_definition
    ):
        """Can start and complete a simple process."""
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=handler_registry,
        )
        
        execution = await engine.start(simple_definition)
        
        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.step_executions["step-a"].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_start_sequential_process(
        self, execution_repo, handler_registry, sequential_definition
    ):
        """Executes steps in dependency order."""
        handler = handler_registry.get(StepType.AGENT_TASK)
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=handler_registry,
        )
        
        execution = await engine.start(sequential_definition)
        
        assert execution.status == ExecutionStatus.COMPLETED
        # Verify execution order
        assert handler.executed_steps == ["step-a", "step-b"]

    @pytest.mark.asyncio
    async def test_start_with_input_data(
        self, execution_repo, handler_registry, simple_definition
    ):
        """Input data is passed to execution."""
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=handler_registry,
        )
        
        execution = await engine.start(
            simple_definition,
            input_data={"topic": "AI"},
        )
        
        assert execution.input_data == {"topic": "AI"}

    @pytest.mark.asyncio
    async def test_start_emits_events(
        self, execution_repo, handler_registry, event_bus, simple_definition
    ):
        """Events are emitted during execution."""
        events = []
        event_bus.subscribe_all(lambda e: events.append(e))
        
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=handler_registry,
            event_bus=event_bus,
        )
        
        await engine.start(simple_definition)
        await event_bus.wait_for_pending()
        
        event_types = [type(e).__name__ for e in events]
        assert "ProcessStarted" in event_types
        assert "StepStarted" in event_types
        assert "StepCompleted" in event_types
        assert "ProcessCompleted" in event_types


class TestExecutionEngineFailure:
    """Tests for failure handling."""

    @pytest.mark.asyncio
    async def test_step_failure_fails_execution(
        self, execution_repo, simple_definition
    ):
        """Failed step causes execution to fail."""
        handler = MockAgentHandler(results={
            "step-a": StepResult.fail("Something went wrong"),
        })
        registry = StepHandlerRegistry()
        registry.register(handler)
        
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=registry,
        )
        
        execution = await engine.start(simple_definition)
        
        assert execution.status == ExecutionStatus.FAILED
        assert execution.step_executions["step-a"].status == StepStatus.FAILED

    @pytest.mark.asyncio
    async def test_failure_stops_execution(
        self, execution_repo, sequential_definition
    ):
        """Failure in step-a prevents step-b from running."""
        handler = MockAgentHandler(results={
            "step-a": StepResult.fail("Error in step A"),
        })
        registry = StepHandlerRegistry()
        registry.register(handler)

        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=registry,
        )

        execution = await engine.start(sequential_definition)

        assert execution.status == ExecutionStatus.FAILED
        # step-b should still be pending
        assert execution.step_executions["step-b"].status == StepStatus.PENDING
        # Only step-a was attempted (may have retry attempts), step-b never ran
        assert all(step == "step-a" for step in handler.executed_steps)
        assert "step-b" not in handler.executed_steps


class TestExecutionEngineCancel:
    """Tests for cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_execution(
        self, execution_repo, simple_definition
    ):
        """Can cancel a pending execution."""
        execution = ProcessExecution.create(simple_definition)
        execution_repo.save(execution)
        
        engine = ExecutionEngine(execution_repo=execution_repo)
        
        cancelled = await engine.cancel(execution, "No longer needed")
        
        assert cancelled.status == ExecutionStatus.CANCELLED
        assert "No longer needed" in cancelled.output_data.get("cancelled_reason", "")


class TestExecutionEngineResume:
    """Tests for resuming executions."""

    @pytest.mark.asyncio
    async def test_resume_paused_execution(
        self, execution_repo, handler_registry, sequential_definition
    ):
        """Can resume a paused execution."""
        # Start execution and pause after first step
        execution = ProcessExecution.create(sequential_definition)
        execution.start()
        execution.start_step(StepId("step-a"))
        execution.complete_step(StepId("step-a"), {"result": "done"})
        execution.pause()
        execution_repo.save(execution)
        
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=handler_registry,
        )
        
        resumed = await engine.resume(execution, sequential_definition)
        
        assert resumed.status == ExecutionStatus.COMPLETED
        assert resumed.step_executions["step-b"].status == StepStatus.COMPLETED


class TestOutputStorage:
    """Tests for output storage integration."""

    @pytest.mark.asyncio
    async def test_outputs_stored(
        self, execution_repo, handler_registry, output_storage, simple_definition
    ):
        """Step outputs are stored via OutputStorage."""
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=handler_registry,
            output_storage=output_storage,
        )
        
        execution = await engine.start(simple_definition)
        
        # Check output was stored
        output = output_storage.retrieve(execution.id, StepId("step-a"))
        assert output is not None
        assert "step_id" in output


class TestParallelExecution:
    """Tests for E5-01, E5-02: Parallel step detection and execution."""

    @pytest.fixture
    def parallel_definition(self):
        """
        Create a process with parallel steps:
        
        step-a (level 0)
               |
           +---+---+
           |       |
        step-b  step-c (both level 1, can run in parallel)
           |       |
           +---+---+
               |
            step-d (level 2, depends on both)
        """
        definition = ProcessDefinition.create(name="parallel-process")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "name": "First Step",
                "type": "agent_task",
                "agent": "test-agent",
                "message": "Do step A",
            }),
            StepDefinition.from_dict({
                "id": "step-b",
                "name": "Branch B",
                "type": "agent_task",
                "agent": "test-agent",
                "message": "Do step B",
                "depends_on": ["step-a"],
            }),
            StepDefinition.from_dict({
                "id": "step-c",
                "name": "Branch C",
                "type": "agent_task",
                "agent": "test-agent",
                "message": "Do step C",
                "depends_on": ["step-a"],
            }),
            StepDefinition.from_dict({
                "id": "step-d",
                "name": "Final Step",
                "type": "agent_task",
                "agent": "test-agent",
                "message": "Do step D",
                "depends_on": ["step-b", "step-c"],
            }),
        ]
        return definition

    def test_parallel_structure_detection(self, parallel_definition):
        """Test that DependencyResolver correctly identifies parallel groups."""
        resolver = DependencyResolver(parallel_definition)
        structure = resolver.get_parallel_structure()
        
        # Should have 3 levels: 0, 1, 2
        assert len(structure.groups) == 3
        
        # Level 0: step-a only
        assert structure.groups[0].level == 0
        assert len(structure.groups[0].step_ids) == 1
        assert not structure.groups[0].is_parallel
        
        # Level 1: step-b and step-c (parallel)
        assert structure.groups[1].level == 1
        assert len(structure.groups[1].step_ids) == 2
        assert structure.groups[1].is_parallel
        
        # Level 2: step-d only
        assert structure.groups[2].level == 2
        assert len(structure.groups[2].step_ids) == 1
        assert not structure.groups[2].is_parallel
        
        # Overall structure has parallel execution
        assert structure.has_parallel_execution()

    def test_step_levels(self, parallel_definition):
        """Test that step levels are correctly assigned."""
        resolver = DependencyResolver(parallel_definition)
        structure = resolver.get_parallel_structure()
        
        assert structure.get_step_level("step-a") == 0
        assert structure.get_step_level("step-b") == 1
        assert structure.get_step_level("step-c") == 1
        assert structure.get_step_level("step-d") == 2

    def test_get_ready_steps_parallel(self, parallel_definition):
        """Test that multiple steps are ready when they can run in parallel."""
        resolver = DependencyResolver(parallel_definition)
        execution = ProcessExecution.create(parallel_definition)
        
        # Initially only step-a is ready
        ready = resolver.get_ready_steps(execution)
        assert len(ready) == 1
        assert str(ready[0]) == "step-a"
        
        # Complete step-a
        execution.start_step(StepId("step-a"))
        execution.complete_step(StepId("step-a"), {})
        
        # Now both step-b and step-c should be ready
        ready = resolver.get_ready_steps(execution)
        assert len(ready) == 2
        ready_ids = {str(r) for r in ready}
        assert ready_ids == {"step-b", "step-c"}

    @pytest.mark.asyncio
    async def test_parallel_execution(
        self, execution_repo, handler_registry, parallel_definition
    ):
        """Test that parallel steps are executed and process completes."""
        from services.process_engine.engine.execution_engine import ExecutionConfig
        
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=handler_registry,
            config=ExecutionConfig(parallel_execution=True),
        )
        
        execution = await engine.start(parallel_definition)
        
        # All steps should be completed
        assert execution.status == ExecutionStatus.COMPLETED
        for step_id in ["step-a", "step-b", "step-c", "step-d"]:
            assert execution.step_executions[step_id].status == StepStatus.COMPLETED
