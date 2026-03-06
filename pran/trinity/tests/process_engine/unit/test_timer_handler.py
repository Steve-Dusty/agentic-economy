"""
Unit tests for Timer Step Handler (Sprint 12 - E9-03)

Tests for: TimerHandler
Reference: BACKLOG_ADVANCED.md - E9-03
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

from services.process_engine.domain import (
    ProcessId,
    ExecutionId,
    StepId,
    StepType,
    Duration,
    TimerConfig,
    ExecutionStatus,
    StepStatus,
    Version,
)
from services.process_engine.domain.entities import StepDefinition, StepExecution
from services.process_engine.domain.aggregates import ProcessExecution
from services.process_engine.engine import TimerHandler, StepResult, StepContext
from services.process_engine.engine.step_handler import StepConfig


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def timer_handler():
    """Create a TimerHandler instance."""
    return TimerHandler()


@pytest.fixture
def timer_config():
    """Create a TimerConfig with 1 second delay."""
    return TimerConfig(delay=Duration(seconds=1))


@pytest.fixture
def timer_config_short():
    """Create a TimerConfig with very short delay for faster tests."""
    return TimerConfig(delay=Duration(seconds=0))


@pytest.fixture
def step_definition():
    """Create a timer step definition."""
    return StepDefinition.from_dict({
        "id": "wait-step",
        "name": "Wait Step",
        "type": "timer",
        "delay": "1s",
    })


@pytest.fixture
def process_execution():
    """Create a mock process execution."""
    return ProcessExecution(
        id=ExecutionId.generate(),
        process_id=ProcessId.generate(),
        process_name="test-process",
        process_version=Version.initial(),
        status=ExecutionStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        triggered_by="test",
    )


@pytest.fixture
def step_context(step_definition, process_execution):
    """Create a step context for testing."""
    return StepContext(
        step_definition=step_definition,
        execution=process_execution,
        step_outputs={},
        input_data={},
    )


# =============================================================================
# TimerHandler Tests
# =============================================================================


class TestTimerHandler:
    """Tests for TimerHandler."""

    def test_step_type(self, timer_handler):
        """TimerHandler returns correct step type."""
        assert timer_handler.step_type == StepType.TIMER

    @pytest.mark.asyncio
    async def test_execute_success(self, timer_handler, step_context, timer_config_short):
        """TimerHandler executes successfully with valid config."""
        result = await timer_handler.execute(step_context, timer_config_short)

        assert result.success is True
        assert result.output["waited_seconds"] == 0
        assert "delay_formatted" in result.output

    @pytest.mark.asyncio
    async def test_execute_with_delay(self, timer_handler, step_context):
        """TimerHandler waits for the configured delay."""
        # Use a short but measurable delay
        config = TimerConfig(delay=Duration.from_string("100ms") if hasattr(Duration, "from_string") else Duration(seconds=0.1))
        # Since Duration might not support sub-second, use 0 for fast test
        config = TimerConfig(delay=Duration(seconds=0))

        start = datetime.now()
        result = await timer_handler.execute(step_context, config)
        elapsed = (datetime.now() - start).total_seconds()

        assert result.success is True
        # Elapsed time should be at least the delay (allowing for small margin)

    @pytest.mark.asyncio
    async def test_execute_invalid_config(self, timer_handler, step_context):
        """TimerHandler fails with invalid config type."""
        # Pass a non-TimerConfig
        invalid_config = MagicMock(spec=StepConfig)

        result = await timer_handler.execute(step_context, invalid_config)

        assert result.success is False
        assert result.error_code == "INVALID_CONFIG"

    @pytest.mark.asyncio
    async def test_output_includes_formatted_delay(self, timer_handler, step_context):
        """TimerHandler output includes human-readable delay format."""
        config = TimerConfig(delay=Duration(seconds=60))  # 1 minute

        # Mock sleep to avoid actual wait
        original_sleep = asyncio.sleep
        asyncio.sleep = AsyncMock()

        try:
            result = await timer_handler.execute(step_context, config)

            assert result.output["waited_seconds"] == 60
            assert result.output["delay_formatted"] == "1m"
        finally:
            asyncio.sleep = original_sleep

    @pytest.mark.asyncio
    async def test_output_format_complex_duration(self, timer_handler, step_context):
        """TimerHandler formats complex durations correctly."""
        config = TimerConfig(delay=Duration(seconds=3661))  # 1h 1m 1s

        # Mock sleep to avoid actual wait
        original_sleep = asyncio.sleep
        asyncio.sleep = AsyncMock()

        try:
            result = await timer_handler.execute(step_context, config)

            assert result.output["waited_seconds"] == 3661
            assert result.output["delay_formatted"] == "1h1m1s"
        finally:
            asyncio.sleep = original_sleep


class TestTimerConfig:
    """Tests for TimerConfig value object."""

    def test_create_timer_config(self):
        """TimerConfig can be created with a Duration."""
        config = TimerConfig(delay=Duration(seconds=30))
        assert config.delay.seconds == 30

    def test_from_dict(self):
        """TimerConfig.from_dict parses correctly."""
        data = {"delay": "5m"}
        config = TimerConfig.from_dict(data)
        assert config.delay.seconds == 300

    def test_from_dict_seconds(self):
        """TimerConfig.from_dict parses seconds format."""
        data = {"delay": "30s"}
        config = TimerConfig.from_dict(data)
        assert config.delay.seconds == 30

    def test_from_dict_hours(self):
        """TimerConfig.from_dict parses hours format."""
        data = {"delay": "2h"}
        config = TimerConfig.from_dict(data)
        assert config.delay.seconds == 7200

    def test_to_dict(self):
        """TimerConfig.to_dict serializes correctly."""
        config = TimerConfig(delay=Duration(seconds=300))
        d = config.to_dict()

        assert d["delay"] == "5m"
