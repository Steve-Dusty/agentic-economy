"""
Unit tests for Process Engine error handling.

Tests for: 
- E13-01 Retry Policy
- E13-02 Error Boundary Step
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
    RetryPolicy,
    ErrorPolicy,
    OnErrorAction,
    Duration,
)
from services.process_engine.repositories import SqliteProcessExecutionRepository
from services.process_engine.engine import (
    ExecutionEngine,
    StepHandler,
    StepHandlerRegistry,
)
from services.process_engine.engine.step_handler import StepResult, StepContext, StepConfig


# =============================================================================
# Mock Step Handler with failure tracking
# =============================================================================


class MockFailingHandler(StepHandler):
    """Mock handler that fails N times per step before succeeding."""
    
    def __init__(self, fail_count: int, error_message: str = "Temporary failure"):
        self.fail_count = fail_count
        self.attempts_per_step: dict[str, int] = {}  # Track attempts per step
        self.total_attempts = 0  # Also track total for compatibility
        self.error_message = error_message
    
    @property
    def step_type(self) -> StepType:
        return StepType.AGENT_TASK
    
    @property
    def attempts(self) -> int:
        """For compatibility with existing tests."""
        return self.total_attempts
    
    async def execute(self, context: StepContext, config: StepConfig) -> StepResult:
        step_id = str(context.step_definition.id)
        
        # Track attempts per step
        if step_id not in self.attempts_per_step:
            self.attempts_per_step[step_id] = 0
        self.attempts_per_step[step_id] += 1
        self.total_attempts += 1
        
        step_attempts = self.attempts_per_step[step_id]
        if step_attempts <= self.fail_count:
            return StepResult.fail(self.error_message, error_code="TEMP_ERROR")
        return StepResult.ok({"result": "success", "attempts": step_attempts})


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def execution_repo():
    return SqliteProcessExecutionRepository(":memory:")


@pytest.fixture
def retry_definition():
    """Definition with a step that has a retry policy."""
    definition = ProcessDefinition.create(name="retry-process")
    definition.steps = [
        StepDefinition.from_dict({
            "id": "retry-step",
            "type": "agent_task",
            "agent": "test",
            "message": "Hello",
            "retry": {
                "max_attempts": 3,
                "initial_delay": "100ms",  # Fast for tests
                "backoff_multiplier": 1.0,
            }
        }),
    ]
    return definition.publish()


@pytest.fixture
def skip_on_error_definition():
    """Definition with a step that should be skipped on error."""
    definition = ProcessDefinition.create(name="skip-on-error-process")
    definition.steps = [
        StepDefinition.from_dict({
            "id": "failing-step",
            "type": "agent_task",
            "agent": "test",
            "message": "Fail me",
            "on_error": "skip_step",
            "retry": {
                "max_attempts": 1,  # Fail quickly
                "initial_delay": "100ms",
            }
        }),
        StepDefinition.from_dict({
            "id": "next-step",
            "type": "agent_task",
            "agent": "test",
            "message": "I should run",
            "depends_on": ["failing-step"],
            "retry": {
                "max_attempts": 3,  # Allow retries to succeed
                "initial_delay": "100ms",
            }
        }),
    ]
    return definition.publish()


# =============================================================================
# Tests
# =============================================================================


class TestRetryPolicy:
    """Tests for E13-01 Retry Policy."""

    @pytest.mark.asyncio
    async def test_successful_retry(self, execution_repo, retry_definition):
        """Step succeeds after 2 retries."""
        # Fail twice, succeed on 3rd attempt
        handler = MockFailingHandler(fail_count=2)
        registry = StepHandlerRegistry()
        registry.register(handler)
        
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=registry,
        )
        
        execution = await engine.start(retry_definition)
        
        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.step_executions["retry-step"].status == StepStatus.COMPLETED
        assert execution.step_executions["retry-step"].retry_count == 2
        assert handler.attempts == 3

    @pytest.mark.asyncio
    async def test_failed_after_max_retries(self, execution_repo, retry_definition):
        """Step fails after exceeding max attempts."""
        # Fail 5 times (max is 3)
        handler = MockFailingHandler(fail_count=5)
        registry = StepHandlerRegistry()
        registry.register(handler)
        
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=registry,
        )
        
        execution = await engine.start(retry_definition)
        
        assert execution.status == ExecutionStatus.FAILED
        assert execution.step_executions["retry-step"].status == StepStatus.FAILED
        assert execution.step_executions["retry-step"].retry_count == 3
        assert handler.attempts == 3


class TestErrorPolicy:
    """Tests for E13-02 Error Boundary Step."""

    @pytest.mark.asyncio
    async def test_skip_step_on_error(self, execution_repo, skip_on_error_definition):
        """Process continues if step is marked skip_step on error."""
        # fail_count=1: each step's first attempt fails, second succeeds
        # failing-step: max_attempts=1, so it fails and gets skipped
        # next-step: max_attempts=3, so attempt 1 fails, attempt 2 succeeds
        handler = MockFailingHandler(fail_count=1)
        registry = StepHandlerRegistry()
        registry.register(handler)
        
        engine = ExecutionEngine(
            execution_repo=execution_repo,
            handler_registry=registry,
        )
        
        execution = await engine.start(skip_on_error_definition)
        
        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.step_executions["failing-step"].status == StepStatus.SKIPPED
        assert execution.step_executions["next-step"].status == StepStatus.COMPLETED
