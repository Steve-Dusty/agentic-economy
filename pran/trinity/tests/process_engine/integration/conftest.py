"""
Integration Test Configuration for Process Engine

Provides fixtures for testing ExecutionEngine with real infrastructure:
- Real SQLite repositories (in-memory)
- Real domain services (DependencyResolver, OutputStorage)
- Real event bus with event capture
- Mock only the external agent HTTP boundary (MockAgentGateway)

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-01
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional
import asyncio
import importlib.util

import pytest

# Add src/backend to path for direct imports
# Must be added FIRST before any services imports to resolve nested dependencies
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_backend_path = str(_project_root / 'src' / 'backend')
_src_path = str(_project_root / 'src')

# Insert backend path at the start - this is where models.py and utils/ live
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# Also add src path for compatibility
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Prevent services/__init__.py from being loaded (it has heavy dependencies)
# by pre-creating an empty services module
if 'services' not in sys.modules:
    import types
    sys.modules['services'] = types.ModuleType('services')
    sys.modules['services'].__path__ = [str(Path(_backend_path) / 'services')]

from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    StepDefinition,
    StepId,
    StepType,
    ExecutionStatus,
    StepStatus,
    Money,
    TokenUsage,
    DomainEvent,
)
from services.process_engine.repositories import (
    SqliteProcessDefinitionRepository,
    SqliteProcessExecutionRepository,
    SqliteEventRepository,
)
from services.process_engine.services import OutputStorage, ExpressionEvaluator
from services.process_engine.events import InMemoryEventBus
from services.process_engine.engine import (
    ExecutionEngine,
    ExecutionConfig,
    StepHandlerRegistry,
    AgentTaskHandler,
    GatewayHandler,
    TimerHandler,
)
from services.process_engine.engine.handlers.agent_task import AgentGateway, AgentTaskError


# =============================================================================
# Mock Agent Gateway
# =============================================================================


class MockAgentGateway(AgentGateway):
    """
    Mock AgentGateway for integration tests.

    Provides configurable responses and tracks all calls for assertions.
    Implements the same interface as the real AgentGateway.
    """

    def __init__(
        self,
        responses: dict[str, str] = None,
        fail_agents: set[str] = None,
        fail_count: int = 0,
    ):
        """
        Initialize the mock gateway.

        Args:
            responses: Dict mapping agent_name to response text
            fail_agents: Set of agent names that should always fail
            fail_count: Number of times to fail before succeeding (for retry tests)
        """
        # Don't call super().__init__() to avoid real client factory
        self.responses = responses or {}
        self.fail_agents = fail_agents or set()
        self.fail_count = fail_count
        self.calls: list[dict[str, Any]] = []
        self._attempt_counts: dict[str, int] = {}

    async def check_agent_available(self, agent_name: str) -> bool:
        """Check if agent is available (not in fail set)."""
        return agent_name not in self.fail_agents

    async def send_message(
        self,
        agent_name: str,
        message: str,
        timeout: float = 300.0,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Send a message and return mock response.

        Tracks calls and supports configurable failures for testing.
        """
        # Track the call
        call_record = {
            "agent": agent_name,
            "message": message,
            "timeout": timeout,
            "context": context,
        }
        self.calls.append(call_record)

        # Check for permanent failures
        if agent_name in self.fail_agents:
            raise AgentTaskError(f"Agent '{agent_name}' is unavailable")

        # Check for transient failures (for retry tests)
        if self.fail_count > 0:
            key = f"{agent_name}:{message[:50]}"
            attempts = self._attempt_counts.get(key, 0) + 1
            self._attempt_counts[key] = attempts

            if attempts <= self.fail_count:
                raise AgentTaskError(f"Transient failure (attempt {attempts})")

        # Return configured or default response
        response_text = self.responses.get(
            agent_name,
            f"Mock response from {agent_name}"
        )

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
        """Get all calls made to a specific agent."""
        return [c for c in self.calls if c["agent"] == agent_name]

    def reset(self):
        """Reset call tracking."""
        self.calls.clear()
        self._attempt_counts.clear()


# =============================================================================
# Repository Fixtures
# =============================================================================


@dataclass
class IntegrationRepos:
    """Container for all repositories used in integration tests."""
    definition: SqliteProcessDefinitionRepository
    execution: SqliteProcessExecutionRepository
    event: SqliteEventRepository


@pytest.fixture
def integration_repos() -> IntegrationRepos:
    """Create in-memory SQLite repositories for integration tests."""
    return IntegrationRepos(
        definition=SqliteProcessDefinitionRepository(":memory:"),
        execution=SqliteProcessExecutionRepository(":memory:"),
        event=SqliteEventRepository(":memory:"),
    )


# =============================================================================
# Event Bus with Capture
# =============================================================================


class EventCapturingBus(InMemoryEventBus):
    """Event bus that captures all published events for assertions."""

    def __init__(self):
        super().__init__()
        self.captured_events: list[DomainEvent] = []
        # Subscribe to capture all events
        self.subscribe_all(self._capture_event)

    async def _capture_event(self, event: DomainEvent):
        """Capture event for later assertion."""
        self.captured_events.append(event)

    def get_event_types(self) -> list[str]:
        """Get list of event type names in order."""
        return [type(e).__name__ for e in self.captured_events]

    def get_events_of_type(self, event_type: str) -> list[DomainEvent]:
        """Get all events of a specific type."""
        return [e for e in self.captured_events if type(e).__name__ == event_type]

    def clear(self):
        """Clear captured events."""
        self.captured_events.clear()


@pytest.fixture
def integration_event_bus() -> EventCapturingBus:
    """Create event bus with capture capability."""
    return EventCapturingBus()


# =============================================================================
# Mock Gateway Fixture
# =============================================================================


@pytest.fixture
def mock_gateway() -> MockAgentGateway:
    """Create a fresh MockAgentGateway for each test."""
    return MockAgentGateway()


# =============================================================================
# Integration Engine Fixture
# =============================================================================


class IntegrationTestContext:
    """Context object for integration tests with helpers."""

    def __init__(
        self,
        engine: ExecutionEngine,
        repos: IntegrationRepos,
        event_bus: EventCapturingBus,
        gateway: MockAgentGateway,
    ):
        self.engine = engine
        self.repos = repos
        self.event_bus = event_bus
        self.gateway = gateway

    async def start(self, definition: ProcessDefinition, input_data: dict = None):
        """Start execution and wait for events to be captured."""
        execution = await self.engine.start(definition, input_data=input_data)
        # Wait for async event handlers to complete
        await self.event_bus.wait_for_pending()
        return execution

    async def cancel(self, execution: ProcessExecution, reason: str = None):
        """Cancel execution and wait for events to be captured."""
        result = await self.engine.cancel(execution, reason=reason)
        await self.event_bus.wait_for_pending()
        return result


@pytest.fixture
def integration_engine(
    integration_repos: IntegrationRepos,
    integration_event_bus: EventCapturingBus,
    mock_gateway: MockAgentGateway,
) -> IntegrationTestContext:
    """
    Create a fully-wired ExecutionEngine for integration tests.

    Returns IntegrationTestContext with helpers for async event handling.
    """
    # Create output storage with real repo
    output_storage = OutputStorage(integration_repos.execution)

    # Create handler registry with real handlers but mock gateway
    registry = StepHandlerRegistry()
    registry.register(AgentTaskHandler(gateway=mock_gateway))
    registry.register(GatewayHandler())
    registry.register(TimerHandler())

    # Create engine with real infrastructure
    engine = ExecutionEngine(
        execution_repo=integration_repos.execution,
        event_bus=integration_event_bus,
        output_storage=output_storage,
        handler_registry=registry,
        config=ExecutionConfig(
            parallel_execution=True,
            stop_on_failure=True,
        ),
    )

    return IntegrationTestContext(engine, integration_repos, integration_event_bus, mock_gateway)


# =============================================================================
# Process Definition Helpers
# =============================================================================


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
    """
    Create a sequential multi-step process definition.

    Steps are chained via depends_on, each referencing previous step output.
    """
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


def create_parallel_definition(
    name: str = "parallel-process",
    parallel_count: int = 2,
) -> ProcessDefinition:
    """
    Create a process with parallel steps followed by a join step.

    Structure:
        step-start
           |
        +--+--+
        |     |
    step-a  step-b  (parallel)
        |     |
        +--+--+
           |
        step-join (depends on both)
    """
    definition = ProcessDefinition.create(name=name)

    steps = [
        StepDefinition.from_dict({
            "id": "step-start",
            "name": "Start",
            "type": "agent_task",
            "agent": "start-agent",
            "message": "Initialize: {{input.topic}}",
        }),
    ]

    # Add parallel steps
    parallel_ids = []
    for i in range(parallel_count):
        step_id = f"step-parallel-{i+1}"
        parallel_ids.append(step_id)
        steps.append(StepDefinition.from_dict({
            "id": step_id,
            "name": f"Parallel {i+1}",
            "type": "agent_task",
            "agent": f"parallel-agent-{i+1}",
            "message": f"Process branch {i+1}: {{{{steps.step-start.output}}}}",
            "depends_on": ["step-start"],
        }))

    # Add join step
    steps.append(StepDefinition.from_dict({
        "id": "step-join",
        "name": "Join",
        "type": "agent_task",
        "agent": "join-agent",
        "message": "Combine results",
        "depends_on": parallel_ids,
    }))

    definition.steps = steps
    return definition.publish()


def create_gateway_definition(
    name: str = "gateway-process",
    routes: list[dict] = None,
    default_route: str = "default-path",
) -> ProcessDefinition:
    """Create a process with a gateway step for conditional routing."""
    if routes is None:
        routes = [
            {"condition": "input.score >= 80", "target": "high-path"},
            {"condition": "input.score >= 50", "target": "medium-path"},
        ]

    definition = ProcessDefinition.create(name=name)
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-analyze",
            "name": "Analyze",
            "type": "agent_task",
            "agent": "analyzer",
            "message": "Analyze: {{input.data}}",
        }),
        StepDefinition.from_dict({
            "id": "step-gateway",
            "name": "Route Decision",
            "type": "gateway",
            "gateway_type": "exclusive",
            "depends_on": ["step-analyze"],
            "routes": routes,
            "default_route": default_route,
        }),
        StepDefinition.from_dict({
            "id": "high-path",
            "name": "High Path",
            "type": "agent_task",
            "agent": "high-handler",
            "message": "Handle high score",
            "depends_on": ["step-gateway"],
        }),
        StepDefinition.from_dict({
            "id": "medium-path",
            "name": "Medium Path",
            "type": "agent_task",
            "agent": "medium-handler",
            "message": "Handle medium score",
            "depends_on": ["step-gateway"],
        }),
        StepDefinition.from_dict({
            "id": "default-path",
            "name": "Default Path",
            "type": "agent_task",
            "agent": "default-handler",
            "message": "Handle default",
            "depends_on": ["step-gateway"],
        }),
    ]
    return definition.publish()


def create_retry_definition(
    name: str = "retry-process",
    max_attempts: int = 3,
    on_error: str = "fail_process",
) -> ProcessDefinition:
    """Create a process with retry configuration."""
    definition = ProcessDefinition.create(name=name)
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-retry",
            "name": "Retry Step",
            "type": "agent_task",
            "agent": "flaky-agent",
            "message": "Do something that might fail",
            "retry": {
                "max_attempts": max_attempts,
                "initial_delay": "10ms",
                "backoff_multiplier": 1.0,
            },
            "on_error": on_error,
        }),
    ]
    return definition.publish()


def create_timer_definition(
    name: str = "timer-process",
    delay: str = "100ms",
) -> ProcessDefinition:
    """Create a process with a timer step."""
    definition = ProcessDefinition.create(name=name)
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-before",
            "name": "Before Timer",
            "type": "agent_task",
            "agent": "before-agent",
            "message": "Before waiting",
        }),
        StepDefinition.from_dict({
            "id": "step-timer",
            "name": "Wait",
            "type": "timer",
            "delay": delay,
            "depends_on": ["step-before"],
        }),
        StepDefinition.from_dict({
            "id": "step-after",
            "name": "After Timer",
            "type": "agent_task",
            "agent": "after-agent",
            "message": "After waiting: {{steps.step-timer.output}}",
            "depends_on": ["step-timer"],
        }),
    ]
    return definition.publish()


# =============================================================================
# Assertion Helpers
# =============================================================================


def assert_event_sequence(
    event_bus: EventCapturingBus,
    expected_types: list[str],
    strict: bool = True,
):
    """
    Assert that events were published in the expected sequence.

    Args:
        event_bus: The event bus with captured events
        expected_types: List of expected event type names
        strict: If True, must match exactly. If False, expected can be subset.
    """
    actual_types = event_bus.get_event_types()

    if strict:
        assert actual_types == expected_types, (
            f"Event sequence mismatch.\n"
            f"Expected: {expected_types}\n"
            f"Actual:   {actual_types}"
        )
    else:
        # Check that expected events appear in order (but may have extras)
        actual_iter = iter(actual_types)
        for expected in expected_types:
            found = False
            for actual in actual_iter:
                if actual == expected:
                    found = True
                    break
            assert found, f"Expected event '{expected}' not found in sequence"


def assert_all_steps_completed(execution: ProcessExecution):
    """Assert that all steps in the execution are completed."""
    for step_id, step_exec in execution.step_executions.items():
        assert step_exec.status == StepStatus.COMPLETED, (
            f"Step '{step_id}' is {step_exec.status}, expected COMPLETED"
        )


def assert_step_status(
    execution: ProcessExecution,
    step_id: str,
    expected_status: StepStatus,
):
    """Assert a specific step has the expected status."""
    step_exec = execution.step_executions.get(step_id)
    assert step_exec is not None, f"Step '{step_id}' not found in execution"
    assert step_exec.status == expected_status, (
        f"Step '{step_id}' is {step_exec.status}, expected {expected_status}"
    )


# =============================================================================
# Override session fixtures from root conftest
# =============================================================================


@pytest.fixture(scope="session")
def api_config():
    """Stub fixture - integration tests don't need API."""
    return None


@pytest.fixture(scope="session")
def api_client():
    """Stub fixture - integration tests don't need API."""
    yield None


@pytest.fixture(scope="session")
def unauthenticated_client():
    """Stub fixture - integration tests don't need API."""
    yield None
