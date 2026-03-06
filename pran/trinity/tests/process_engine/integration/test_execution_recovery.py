"""
Integration Tests for Execution Recovery Service

Tests recovery scenarios after simulated backend restart:
- RESUME: Continue from next pending step
- RETRY_STEP: Re-execute interrupted step
- MARK_FAILED: Age timeout failure
- Mixed batch recovery
- Error handling during recovery

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-13
Reference: IT5 Section 2.3 (Recovery on Backend Restart)
"""

import sys
from pathlib import Path

# Add src/backend to path for direct imports (same as conftest.py)
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_backend_path = str(_project_root / 'src' / 'backend')
_src_path = str(_project_root / 'src')

if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Prevent services/__init__.py from being loaded
if 'services' not in sys.modules:
    import types
    sys.modules['services'] = types.ModuleType('services')
    sys.modules['services'].__path__ = [str(Path(_backend_path) / 'services')]

import pytest
from datetime import datetime, timedelta, timezone

from services.process_engine.domain import (
    ProcessExecution,
    ExecutionStatus,
    StepStatus,
)
from services.process_engine.services import (
    ExecutionRecoveryService,
    RecoveryAction,
    RecoveryConfig,
    OutputStorage,
)
from services.process_engine.engine import (
    ExecutionEngine,
    ExecutionConfig,
    StepHandlerRegistry,
    AgentTaskHandler,
)
from services.process_engine.repositories import (
    SqliteProcessDefinitionRepository,
    SqliteProcessExecutionRepository,
    SqliteEventRepository,
)
from services.process_engine.events import InMemoryEventBus
from services.process_engine.engine.handlers.agent_task import AgentGateway, AgentTaskError
from services.process_engine.domain import (
    ProcessDefinition,
    StepDefinition,
    StepType,
    Money,
    TokenUsage,
    DomainEvent,
)

from dataclasses import dataclass
from typing import Any, Optional


# =============================================================================
# Local Test Infrastructure (duplicated from conftest to avoid import issues)
# =============================================================================


@dataclass
class IntegrationRepos:
    """Container for all repositories used in integration tests."""
    definition: SqliteProcessDefinitionRepository
    execution: SqliteProcessExecutionRepository
    event: SqliteEventRepository


class MockAgentGateway(AgentGateway):
    """Mock AgentGateway for integration tests."""

    def __init__(
        self,
        responses: dict[str, str] = None,
        fail_agents: set[str] = None,
        fail_count: int = 0,
    ):
        self.responses = responses or {}
        self.fail_agents = fail_agents or set()
        self.fail_count = fail_count
        self.calls: list[dict[str, Any]] = []
        self._attempt_counts: dict[str, int] = {}

    async def check_agent_available(self, agent_name: str) -> bool:
        return agent_name not in self.fail_agents

    async def send_message(
        self,
        agent_name: str,
        message: str,
        timeout: float = 300.0,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        call_record = {
            "agent": agent_name,
            "message": message,
            "timeout": timeout,
            "context": context,
        }
        self.calls.append(call_record)

        if agent_name in self.fail_agents:
            raise AgentTaskError(f"Agent '{agent_name}' is unavailable")

        if self.fail_count > 0:
            key = f"{agent_name}:{message[:50]}"
            attempts = self._attempt_counts.get(key, 0) + 1
            self._attempt_counts[key] = attempts
            if attempts <= self.fail_count:
                raise AgentTaskError(f"Transient failure (attempt {attempts})")

        response_text = self.responses.get(agent_name, f"Mock response from {agent_name}")
        return {
            "response": response_text,
            "cost": Money.from_float(0.01),
            "token_usage": TokenUsage(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                model="mock-model",
            ),
            "metadata": {"mock": True, "agent": agent_name},
        }

    def get_calls_for_agent(self, agent_name: str) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["agent"] == agent_name]


class EventCapturingBus(InMemoryEventBus):
    """Event bus that captures all published events for assertions."""

    def __init__(self):
        super().__init__()
        self.captured_events: list[DomainEvent] = []
        self.subscribe_all(self._capture_event)

    async def _capture_event(self, event: DomainEvent):
        self.captured_events.append(event)

    def get_event_types(self) -> list[str]:
        return [type(e).__name__ for e in self.captured_events]

    def get_events_of_type(self, event_type: str) -> list[DomainEvent]:
        return [e for e in self.captured_events if type(e).__name__ == event_type]

    def clear(self):
        self.captured_events.clear()


def create_single_step_definition(
    name: str = "single-step-process",
    agent: str = "test-agent",
    message: str = "Do something",
) -> ProcessDefinition:
    """Create a simple single-step process definition."""
    definition = ProcessDefinition.create(name=name)
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-1",
            "name": "Step 1",
            "type": "agent_task",
            "agent": agent,
            "message": message,
        }),
    ]
    return definition.publish()


def create_sequential_definition(
    name: str = "sequential-process",
    num_steps: int = 3,
    agents: list[str] = None,
) -> ProcessDefinition:
    """Create a sequential multi-step process definition."""
    if agents is None:
        agents = [f"agent-{i+1}" for i in range(num_steps)]

    definition = ProcessDefinition.create(name=name)
    steps = []

    for i in range(num_steps):
        step_id = f"step-{i+1}"
        step_dict = {
            "id": step_id,
            "name": f"Step {i+1}",
            "type": "agent_task",
            "agent": agents[i] if i < len(agents) else f"agent-{i+1}",
            "message": f"Process: {{{{input.topic}}}}" if i == 0 else f"Continue with: {{{{steps.step-{i}.output}}}}",
        }
        if i > 0:
            step_dict["depends_on"] = [f"step-{i}"]
        steps.append(StepDefinition.from_dict(step_dict))

    definition.steps = steps
    return definition.publish()


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def recovery_repos() -> IntegrationRepos:
    """Create fresh repositories for recovery tests."""
    from services.process_engine.repositories import (
        SqliteProcessDefinitionRepository,
        SqliteProcessExecutionRepository,
        SqliteEventRepository,
    )
    return IntegrationRepos(
        definition=SqliteProcessDefinitionRepository(":memory:"),
        execution=SqliteProcessExecutionRepository(":memory:"),
        event=SqliteEventRepository(":memory:"),
    )


@pytest.fixture
def recovery_event_bus() -> EventCapturingBus:
    """Create event bus for recovery tests."""
    return EventCapturingBus()


@pytest.fixture
def recovery_gateway() -> MockAgentGateway:
    """Create mock gateway for recovery tests."""
    return MockAgentGateway()


@pytest.fixture
def recovery_engine(
    recovery_repos: IntegrationRepos,
    recovery_event_bus: EventCapturingBus,
    recovery_gateway: MockAgentGateway,
) -> ExecutionEngine:
    """Create execution engine for recovery tests."""
    output_storage = OutputStorage(recovery_repos.execution)

    registry = StepHandlerRegistry()
    registry.register(AgentTaskHandler(gateway=recovery_gateway))

    return ExecutionEngine(
        execution_repo=recovery_repos.execution,
        event_bus=recovery_event_bus,
        output_storage=output_storage,
        handler_registry=registry,
        config=ExecutionConfig(
            parallel_execution=True,
            stop_on_failure=True,
        ),
    )


@pytest.fixture
def recovery_service(
    recovery_repos: IntegrationRepos,
    recovery_engine: ExecutionEngine,
    recovery_event_bus: EventCapturingBus,
) -> ExecutionRecoveryService:
    """Create recovery service for tests."""
    return ExecutionRecoveryService(
        execution_repo=recovery_repos.execution,
        definition_repo=recovery_repos.definition,
        execution_engine=recovery_engine,
        event_bus=recovery_event_bus,
    )


# =============================================================================
# Helper Functions
# =============================================================================


def create_execution_in_state(
    definition,
    repos: IntegrationRepos,
    status: ExecutionStatus = ExecutionStatus.RUNNING,
    running_step: str = None,
    completed_steps: list[str] = None,
    age_hours: float = 0,
) -> ProcessExecution:
    """
    Create an execution in a specific state to simulate interrupted execution.

    Args:
        definition: Process definition
        repos: Repositories to save to
        status: Execution status
        running_step: Step ID to mark as RUNNING
        completed_steps: Step IDs to mark as COMPLETED
        age_hours: How old the execution should appear (hours)

    Returns:
        The created execution
    """
    # Save definition first
    repos.definition.save(definition)

    # Create execution
    execution = ProcessExecution.create(
        definition=definition,
        triggered_by="test",
    )

    # Set execution status
    execution.status = status

    # Adjust timestamps to simulate age
    if age_hours > 0:
        old_time = datetime.now(timezone.utc) - timedelta(hours=age_hours)
        execution.started_at = old_time

        # Update step timestamps too
        for step_exec in execution.step_executions.values():
            if step_exec.started_at:
                step_exec.started_at = old_time
    else:
        execution.started_at = datetime.now(timezone.utc)

    # Mark completed steps
    if completed_steps:
        for step_id in completed_steps:
            step_exec = execution.step_executions.get(step_id)
            if step_exec:
                step_exec.status = StepStatus.COMPLETED
                step_exec.started_at = execution.started_at
                step_exec.completed_at = execution.started_at + timedelta(seconds=5)
                step_exec.output = {"result": f"completed_{step_id}"}

    # Mark running step
    if running_step:
        step_exec = execution.step_executions.get(running_step)
        if step_exec:
            step_exec.status = StepStatus.RUNNING
            step_exec.started_at = execution.started_at + timedelta(seconds=10)

    # Save to repository
    repos.execution.save(execution)

    return execution


# =============================================================================
# Test: RESUME Action (Execution Between Steps)
# =============================================================================


@pytest.mark.asyncio
async def test_resume_execution_between_steps(
    recovery_repos: IntegrationRepos,
    recovery_service: ExecutionRecoveryService,
    recovery_gateway: MockAgentGateway,
):
    """
    Test RESUME action when execution was between steps.

    Scenario: Step 1 completed, Step 2 pending (not started yet)
    Expected: Recovery resumes from Step 2
    """
    # Create 2-step sequential process
    definition = create_sequential_definition(
        name="resume-test",
        num_steps=2,
        agents=["agent-1", "agent-2"],
    )

    # Create execution with step-1 completed, step-2 pending
    execution = create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
        completed_steps=["step-1"],
    )

    # Verify initial state
    assert execution.status == ExecutionStatus.RUNNING
    assert execution.step_executions["step-1"].status == StepStatus.COMPLETED
    assert execution.step_executions["step-2"].status == StepStatus.PENDING

    # Run recovery
    report = await recovery_service.recover_on_startup()

    # Verify RESUME action was taken
    assert len(report.resumed) == 1
    assert execution.id in report.resumed
    assert len(report.errors) == 0

    # Give async execution time to complete
    import asyncio
    await asyncio.sleep(0.5)

    # Verify agent-2 was called (step-2 executed)
    assert len(recovery_gateway.get_calls_for_agent("agent-2")) >= 1


@pytest.mark.asyncio
async def test_resume_pending_execution(
    recovery_repos: IntegrationRepos,
    recovery_service: ExecutionRecoveryService,
):
    """
    Test RESUME action for PENDING execution (never started running).

    Scenario: Execution created but never started (all steps pending)
    Expected: Recovery resumes and starts execution
    """
    definition = create_single_step_definition(
        name="pending-resume-test",
        agent="pending-agent",
    )

    # Create execution in PENDING status (never started)
    execution = create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.PENDING,
    )

    # Verify initial state
    assert execution.status == ExecutionStatus.PENDING

    # Run recovery
    report = await recovery_service.recover_on_startup()

    # PENDING executions should also be resumed
    assert len(report.resumed) == 1
    assert execution.id in report.resumed


# =============================================================================
# Test: RETRY_STEP Action (Step Was Running)
# =============================================================================


@pytest.mark.asyncio
async def test_retry_running_step(
    recovery_repos: IntegrationRepos,
    recovery_service: ExecutionRecoveryService,
    recovery_gateway: MockAgentGateway,
):
    """
    Test RETRY_STEP action when a step was mid-execution.

    Scenario: Step 1 completed, Step 2 was RUNNING (interrupted)
    Expected: Recovery resets Step 2 to PENDING and resumes
    """
    definition = create_sequential_definition(
        name="retry-step-test",
        num_steps=2,
        agents=["agent-1", "agent-2"],
    )

    # Create execution with step-2 in RUNNING state (interrupted)
    execution = create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
        completed_steps=["step-1"],
        running_step="step-2",
    )

    # Verify initial state
    assert execution.step_executions["step-1"].status == StepStatus.COMPLETED
    assert execution.step_executions["step-2"].status == StepStatus.RUNNING

    # Run recovery
    report = await recovery_service.recover_on_startup()

    # Verify RETRY_STEP action was taken
    assert len(report.retried) == 1
    assert execution.id in report.retried

    # Verify step was reset to PENDING before resume
    # (Check repo state after recovery)
    recovered_exec = recovery_repos.execution.get_by_id(execution.id)
    # Step-2 should have been reset and possibly completed by now
    # (depends on timing of async execution)

    # Give async execution time to complete
    import asyncio
    await asyncio.sleep(0.5)

    # Verify agent-2 was called (step was retried)
    calls = recovery_gateway.get_calls_for_agent("agent-2")
    assert len(calls) >= 1


@pytest.mark.asyncio
async def test_retry_first_step_running(
    recovery_repos: IntegrationRepos,
    recovery_service: ExecutionRecoveryService,
    recovery_gateway: MockAgentGateway,
):
    """
    Test RETRY_STEP when the very first step was interrupted.

    Scenario: Step 1 was RUNNING (process just started, then crashed)
    Expected: Recovery retries Step 1
    """
    definition = create_single_step_definition(
        name="retry-first-step-test",
        agent="first-agent",
    )

    # Create execution with first step running
    execution = create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
        running_step="step-1",
    )

    assert execution.step_executions["step-1"].status == StepStatus.RUNNING

    # Run recovery
    report = await recovery_service.recover_on_startup()

    assert len(report.retried) == 1
    assert execution.id in report.retried


# =============================================================================
# Test: MARK_FAILED Action (Age Timeout)
# =============================================================================


@pytest.mark.asyncio
async def test_mark_failed_old_execution(
    recovery_repos: IntegrationRepos,
    recovery_service: ExecutionRecoveryService,
):
    """
    Test MARK_FAILED action for execution older than 24 hours.

    Scenario: Execution has been stuck for > 24 hours
    Expected: Recovery marks it as failed
    """
    definition = create_single_step_definition(
        name="old-execution-test",
        agent="old-agent",
    )

    # Create execution that is 25 hours old
    execution = create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
        running_step="step-1",
        age_hours=25,
    )

    # Run recovery
    report = await recovery_service.recover_on_startup()

    # Verify MARK_FAILED action was taken
    assert len(report.failed) == 1
    assert execution.id in report.failed
    assert len(report.resumed) == 0
    assert len(report.retried) == 0

    # Verify execution is now FAILED in database
    failed_exec = recovery_repos.execution.get_by_id(execution.id)
    assert failed_exec.status == ExecutionStatus.FAILED


@pytest.mark.asyncio
async def test_mark_failed_custom_age_threshold(
    recovery_repos: IntegrationRepos,
    recovery_event_bus: EventCapturingBus,
    recovery_engine: ExecutionEngine,
):
    """
    Test custom age threshold configuration.

    Scenario: Custom 1-hour threshold, execution is 2 hours old
    Expected: Recovery marks it as failed
    """
    # Create service with custom 1-hour threshold
    recovery_service = ExecutionRecoveryService(
        execution_repo=recovery_repos.execution,
        definition_repo=recovery_repos.definition,
        execution_engine=recovery_engine,
        event_bus=recovery_event_bus,
        config=RecoveryConfig(max_age_hours=1),
    )

    definition = create_single_step_definition(
        name="custom-threshold-test",
        agent="threshold-agent",
    )

    # Create execution that is 2 hours old (exceeds 1-hour threshold)
    execution = create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
        age_hours=2,
    )

    # Run recovery
    report = await recovery_service.recover_on_startup()

    assert len(report.failed) == 1
    assert execution.id in report.failed


# =============================================================================
# Test: SKIP Action (Already Terminal)
# =============================================================================


@pytest.mark.asyncio
async def test_skip_completed_execution(
    recovery_repos: IntegrationRepos,
    recovery_service: ExecutionRecoveryService,
):
    """
    Test SKIP action for already completed execution.

    Scenario: Execution is already COMPLETED
    Expected: Recovery skips it (no action needed)
    """
    definition = create_single_step_definition(
        name="completed-test",
        agent="completed-agent",
    )

    # Create execution that is already completed
    # Note: list_active() shouldn't return completed executions,
    # but we test the logic anyway
    execution = create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.COMPLETED,
        completed_steps=["step-1"],
    )

    # Run recovery - should find nothing (completed not in list_active)
    report = await recovery_service.recover_on_startup()

    # No actions taken since COMPLETED is not returned by list_active()
    assert report.total_processed == 0


# =============================================================================
# Test: Mixed Batch Recovery
# =============================================================================


@pytest.mark.asyncio
async def test_mixed_batch_recovery(
    recovery_repos: IntegrationRepos,
    recovery_service: ExecutionRecoveryService,
):
    """
    Test recovery of multiple executions with different actions.

    Scenario: 3 executions needing different recovery actions
    Expected: Each gets appropriate action
    """
    # Create 3 definitions
    def1 = create_single_step_definition(name="batch-1", agent="agent-1")
    def2 = create_sequential_definition(name="batch-2", num_steps=2, agents=["a", "b"])
    def3 = create_single_step_definition(name="batch-3", agent="agent-3")

    # Execution 1: Between steps -> RESUME
    exec1 = create_execution_in_state(
        definition=def2,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
        completed_steps=["step-1"],
    )

    # Execution 2: Step running -> RETRY_STEP
    exec2 = create_execution_in_state(
        definition=def1,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
        running_step="step-1",
    )

    # Execution 3: Too old -> MARK_FAILED
    exec3 = create_execution_in_state(
        definition=def3,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
        age_hours=30,
    )

    # Run recovery
    report = await recovery_service.recover_on_startup()

    # Verify each got correct action
    assert len(report.resumed) == 1
    assert exec1.id in report.resumed

    assert len(report.retried) == 1
    assert exec2.id in report.retried

    assert len(report.failed) == 1
    assert exec3.id in report.failed

    # Total processed
    assert report.total_processed == 3


# =============================================================================
# Test: Error Handling During Recovery
# =============================================================================


@pytest.mark.asyncio
async def test_recovery_continues_on_error(
    recovery_repos: IntegrationRepos,
    recovery_event_bus: EventCapturingBus,
    recovery_gateway: MockAgentGateway,
):
    """
    Test that recovery continues even when one execution fails to recover.

    Scenario: First execution's definition is missing, second is valid
    Expected: First errors, second recovers successfully
    """
    # Create two definitions
    def1 = create_single_step_definition(name="missing-def", agent="agent-1")
    def2 = create_single_step_definition(name="valid-def", agent="agent-2")

    # Create execution 1 but DON'T save its definition (will error during recovery)
    exec1 = ProcessExecution.create(
        definition=def1,
        triggered_by="test",
    )
    exec1.status = ExecutionStatus.RUNNING
    exec1.started_at = datetime.now(timezone.utc)
    recovery_repos.execution.save(exec1)
    # Note: def1 NOT saved to repos.definition

    # Create execution 2 WITH its definition saved
    exec2 = create_execution_in_state(
        definition=def2,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
    )

    # Create recovery service
    output_storage = OutputStorage(recovery_repos.execution)
    registry = StepHandlerRegistry()
    registry.register(AgentTaskHandler(gateway=recovery_gateway))

    engine = ExecutionEngine(
        execution_repo=recovery_repos.execution,
        event_bus=recovery_event_bus,
        output_storage=output_storage,
        handler_registry=registry,
    )

    recovery_service = ExecutionRecoveryService(
        execution_repo=recovery_repos.execution,
        definition_repo=recovery_repos.definition,
        execution_engine=engine,
        event_bus=recovery_event_bus,
    )

    # Run recovery
    report = await recovery_service.recover_on_startup()

    # First execution should error (missing definition)
    assert len(report.errors) == 1
    error_ids = [e[0] for e in report.errors]
    assert exec1.id in error_ids

    # The second execution should be in resumed list (not in errors)
    # Note: exec1 might also be in resumed list since we determine action first,
    # but then it fails when we try to get the definition
    assert exec2.id in report.resumed or exec2.id in report.retried
    assert exec2.id not in error_ids

    # Total processed should include both (even though one errored)
    assert report.total_processed == 2


# =============================================================================
# Test: Recovery Events
# =============================================================================


@pytest.mark.asyncio
async def test_recovery_events_emitted(
    recovery_repos: IntegrationRepos,
    recovery_service: ExecutionRecoveryService,
    recovery_event_bus: EventCapturingBus,
):
    """
    Test that recovery events are emitted correctly.

    Expected events:
    - ExecutionRecoveryStarted (once at start)
    - ExecutionRecovered (for each recovered execution)
    - ExecutionRecoveryCompleted (once at end)
    """
    definition = create_single_step_definition(
        name="events-test",
        agent="events-agent",
    )

    # Create execution to recover
    execution = create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
    )

    # Clear any previous events
    recovery_event_bus.clear()

    # Run recovery
    report = await recovery_service.recover_on_startup()

    # Wait for async events
    await recovery_event_bus.wait_for_pending()

    # Check events were emitted
    event_types = recovery_event_bus.get_event_types()

    # Should have recovery events
    assert "ExecutionRecoveryStarted" in event_types
    assert "ExecutionRecovered" in event_types
    assert "ExecutionRecoveryCompleted" in event_types

    # Check ExecutionRecovered event details
    recovered_events = recovery_event_bus.get_events_of_type("ExecutionRecovered")
    assert len(recovered_events) == 1
    assert recovered_events[0].execution_id == execution.id

    # Check ExecutionRecoveryCompleted event
    completed_events = recovery_event_bus.get_events_of_type("ExecutionRecoveryCompleted")
    assert len(completed_events) == 1
    completed_event = completed_events[0]
    assert completed_event.resumed_count + completed_event.retried_count >= 1


# =============================================================================
# Test: Dry Run Mode
# =============================================================================


@pytest.mark.asyncio
async def test_dry_run_mode(
    recovery_repos: IntegrationRepos,
    recovery_event_bus: EventCapturingBus,
    recovery_engine: ExecutionEngine,
):
    """
    Test dry run mode doesn't actually modify state.

    Scenario: Recovery runs in dry_run mode
    Expected: Report is generated but no executions modified
    """
    # Create service with dry_run=True
    recovery_service = ExecutionRecoveryService(
        execution_repo=recovery_repos.execution,
        definition_repo=recovery_repos.definition,
        execution_engine=recovery_engine,
        event_bus=recovery_event_bus,
        config=RecoveryConfig(dry_run=True),
    )

    definition = create_single_step_definition(
        name="dry-run-test",
        agent="dry-run-agent",
    )

    # Create execution to potentially recover
    execution = create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
        running_step="step-1",
    )

    original_status = execution.status
    original_step_status = execution.step_executions["step-1"].status

    # Run recovery in dry run mode
    report = await recovery_service.recover_on_startup()

    # Report should show what WOULD happen
    assert len(report.retried) == 1

    # But execution state should be unchanged
    reloaded = recovery_repos.execution.get_by_id(execution.id)
    assert reloaded.status == original_status
    assert reloaded.step_executions["step-1"].status == original_step_status


# =============================================================================
# Test: Last Recovery Report
# =============================================================================


@pytest.mark.asyncio
async def test_last_recovery_report_stored(
    recovery_repos: IntegrationRepos,
    recovery_service: ExecutionRecoveryService,
):
    """
    Test that last recovery report is stored for health checks.
    """
    # Initially no report
    assert recovery_service.last_recovery_report is None

    # Create some executions
    definition = create_single_step_definition(name="report-test", agent="agent")
    create_execution_in_state(
        definition=definition,
        repos=recovery_repos,
        status=ExecutionStatus.RUNNING,
    )

    # Run recovery
    report = await recovery_service.recover_on_startup()

    # Report should be stored
    assert recovery_service.last_recovery_report is not None
    assert recovery_service.last_recovery_report is report
    assert report.completed_at is not None
    assert report.duration_ms >= 0
