"""
Unit tests for Gateway Handler (Sprint 10 - E7)

Tests for: GatewayHandler, GatewayConfig, conditional routing
Reference: BACKLOG_CORE.md - E7-01, E7-02
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from services.process_engine.domain import (
    ProcessId,
    ExecutionId,
    StepType,
    Version,
    ExecutionStatus,
    GatewayConfig,
)
from services.process_engine.domain.entities import StepDefinition
from services.process_engine.domain.aggregates import ProcessExecution
from services.process_engine.engine.handlers.gateway import GatewayHandler
from services.process_engine.engine.step_handler import StepContext, StepConfig


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def gateway_handler():
    """Create a GatewayHandler instance."""
    return GatewayHandler()


@pytest.fixture
def exclusive_gateway_config():
    """Create an exclusive gateway config with multiple routes."""
    return GatewayConfig(
        gateway_type="exclusive",
        routes=[
            {"condition": "input.score >= 90", "target": "high-priority"},
            {"condition": "input.score >= 70", "target": "medium-priority"},
            {"condition": "input.score >= 50", "target": "low-priority"},
        ],
        default_route="review",
    )


@pytest.fixture
def parallel_gateway_config():
    """Create a parallel gateway config."""
    return GatewayConfig(
        gateway_type="parallel",
        routes=[
            {"condition": "input.notify_email", "target": "send-email"},
            {"condition": "input.notify_slack", "target": "send-slack"},
            {"condition": "input.notify_sms", "target": "send-sms"},
        ],
        default_route=None,
    )


@pytest.fixture
def step_definition():
    """Create a gateway step definition."""
    return StepDefinition.from_dict({
        "id": "route-decision",
        "name": "Route Decision",
        "type": "gateway",
        "gateway_type": "exclusive",
    })


@pytest.fixture
def process_execution():
    """Create a mock process execution."""
    return ProcessExecution(
        id=ExecutionId.generate(),
        process_id=ProcessId.generate(),
        process_name="gateway-test-process",
        process_version=Version.initial(),
        status=ExecutionStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        triggered_by="test",
        input_data={"score": 85},
    )


@pytest.fixture
def step_context(step_definition, process_execution):
    """Create a step context for testing."""
    return StepContext(
        step_definition=step_definition,
        execution=process_execution,
        step_outputs={},
        input_data=process_execution.input_data,
    )


# =============================================================================
# GatewayHandler Tests - Exclusive Gateway
# =============================================================================


class TestExclusiveGateway:
    """Tests for exclusive (XOR) gateway behavior."""

    def test_step_type(self, gateway_handler):
        """Handler returns correct step type."""
        assert gateway_handler.step_type == StepType.GATEWAY

    @pytest.mark.asyncio
    async def test_first_matching_route_wins(self, gateway_handler, step_context, exclusive_gateway_config):
        """Exclusive gateway takes first matching route."""
        # score=85 matches "input.score >= 70" (medium-priority)
        # but also would match >= 50, first match wins
        result = await gateway_handler.execute(step_context, exclusive_gateway_config)

        assert result.success is True
        assert result.output["route"] == "medium-priority"
        assert result.output["gateway_type"] == "exclusive"

    @pytest.mark.asyncio
    async def test_high_score_route(self, gateway_handler, step_definition):
        """Routes to high-priority for high scores."""
        execution = ProcessExecution(
            id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test",
            process_version=Version.initial(),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            triggered_by="test",
            input_data={"score": 95},
        )
        context = StepContext(
            step_definition=step_definition,
            execution=execution,
            step_outputs={},
            input_data=execution.input_data,
        )

        config = GatewayConfig(
            gateway_type="exclusive",
            routes=[
                {"condition": "input.score >= 90", "target": "high-priority"},
                {"condition": "input.score >= 70", "target": "medium-priority"},
            ],
            default_route="low-priority",
        )

        handler = GatewayHandler()
        result = await handler.execute(context, config)

        assert result.output["route"] == "high-priority"

    @pytest.mark.asyncio
    async def test_default_route_when_no_match(self, gateway_handler, step_definition):
        """Uses default route when no conditions match."""
        execution = ProcessExecution(
            id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test",
            process_version=Version.initial(),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            triggered_by="test",
            input_data={"score": 30},
        )
        context = StepContext(
            step_definition=step_definition,
            execution=execution,
            step_outputs={},
            input_data=execution.input_data,
        )

        config = GatewayConfig(
            gateway_type="exclusive",
            routes=[
                {"condition": "input.score >= 90", "target": "high"},
                {"condition": "input.score >= 50", "target": "medium"},
            ],
            default_route="fallback",
        )

        handler = GatewayHandler()
        result = await handler.execute(context, config)

        assert result.output["route"] == "fallback"
        assert result.output["is_default"] is True

    @pytest.mark.asyncio
    async def test_error_no_match_no_default(self, gateway_handler, step_definition):
        """Fails when no conditions match and no default."""
        execution = ProcessExecution(
            id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test",
            process_version=Version.initial(),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            triggered_by="test",
            input_data={"score": 10},
        )
        context = StepContext(
            step_definition=step_definition,
            execution=execution,
            step_outputs={},
            input_data=execution.input_data,
        )

        config = GatewayConfig(
            gateway_type="exclusive",
            routes=[
                {"condition": "input.score >= 50", "target": "pass"},
            ],
            default_route=None,  # No default
        )

        handler = GatewayHandler()
        result = await handler.execute(context, config)

        assert result.success is False
        assert result.error_code == "NO_MATCHING_ROUTE"


# =============================================================================
# GatewayHandler Tests - Parallel Gateway
# =============================================================================


class TestParallelGateway:
    """Tests for parallel gateway behavior."""

    @pytest.mark.asyncio
    async def test_all_matching_routes(self, gateway_handler, step_definition):
        """Parallel gateway returns all matching routes."""
        execution = ProcessExecution(
            id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test",
            process_version=Version.initial(),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            triggered_by="test",
            input_data={
                "notify_email": True,
                "notify_slack": True,
                "notify_sms": False,
            },
        )
        context = StepContext(
            step_definition=step_definition,
            execution=execution,
            step_outputs={},
            input_data=execution.input_data,
        )

        config = GatewayConfig(
            gateway_type="parallel",
            routes=[
                {"condition": "input.notify_email", "target": "send-email"},
                {"condition": "input.notify_slack", "target": "send-slack"},
                {"condition": "input.notify_sms", "target": "send-sms"},
            ],
            default_route=None,
        )

        handler = GatewayHandler()
        result = await handler.execute(context, config)

        assert result.success is True
        assert result.output["gateway_type"] == "parallel"
        assert set(result.output["routes"]) == {"send-email", "send-slack"}

    @pytest.mark.asyncio
    async def test_parallel_uses_default_when_no_matches(self, gateway_handler, step_definition):
        """Parallel gateway uses default when no conditions match."""
        execution = ProcessExecution(
            id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test",
            process_version=Version.initial(),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            triggered_by="test",
            input_data={
                "notify_email": False,
                "notify_slack": False,
            },
        )
        context = StepContext(
            step_definition=step_definition,
            execution=execution,
            step_outputs={},
            input_data=execution.input_data,
        )

        config = GatewayConfig(
            gateway_type="parallel",
            routes=[
                {"condition": "input.notify_email", "target": "send-email"},
                {"condition": "input.notify_slack", "target": "send-slack"},
            ],
            default_route="no-notification",
        )

        handler = GatewayHandler()
        result = await handler.execute(context, config)

        assert result.output["routes"] == ["no-notification"]
        assert result.output["is_default"] is True


# =============================================================================
# GatewayHandler Tests - Step Outputs
# =============================================================================


class TestGatewayWithStepOutputs:
    """Tests for gateway routing based on step outputs."""

    @pytest.mark.asyncio
    async def test_route_based_on_previous_step_output(self, gateway_handler, step_definition):
        """Can route based on output from previous steps."""
        execution = ProcessExecution(
            id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test",
            process_version=Version.initial(),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            triggered_by="test",
            input_data={},
        )
        # Use underscore in step ID (hyphen may not work in all expression contexts)
        # Note: path format is steps.{step_id}.output.{field}
        context = StepContext(
            step_definition=step_definition,
            execution=execution,
            step_outputs={
                "analyze_step": {"sentiment": "positive", "confidence": 0.92},
            },
            input_data=execution.input_data,
        )

        config = GatewayConfig(
            gateway_type="exclusive",
            routes=[
                {"condition": "steps.analyze_step.output.sentiment == 'positive'", "target": "celebrate"},
                {"condition": "steps.analyze_step.output.sentiment == 'negative'", "target": "investigate"},
            ],
            default_route="neutral-path",
        )

        handler = GatewayHandler()
        result = await handler.execute(context, config)

        assert result.output["route"] == "celebrate"


# =============================================================================
# GatewayHandler Tests - Invalid Configurations
# =============================================================================


class TestGatewayInvalidConfig:
    """Tests for gateway handler error handling."""

    @pytest.mark.asyncio
    async def test_invalid_config_type(self, gateway_handler, step_context):
        """Returns error for invalid config type."""
        invalid_config = MagicMock(spec=StepConfig)

        result = await gateway_handler.execute(step_context, invalid_config)

        assert result.success is False
        assert result.error_code == "INVALID_CONFIG"

    @pytest.mark.asyncio
    async def test_unknown_gateway_type(self, gateway_handler, step_context):
        """Returns error for unknown gateway type."""
        config = GatewayConfig(
            gateway_type="unknown_type",
            routes=[{"condition": "true", "target": "somewhere"}],
        )

        result = await gateway_handler.execute(step_context, config)

        assert result.success is False
        assert result.error_code == "INVALID_GATEWAY_TYPE"

    @pytest.mark.asyncio
    async def test_route_without_target_is_skipped(self, gateway_handler, step_context):
        """Routes without target are skipped."""
        config = GatewayConfig(
            gateway_type="exclusive",
            routes=[
                {"condition": "true"},  # Missing target
                {"condition": "true", "target": "valid-target"},
            ],
            default_route=None,
        )

        result = await gateway_handler.execute(step_context, config)

        assert result.success is True
        assert result.output["route"] == "valid-target"


# =============================================================================
# GatewayConfig Tests
# =============================================================================


class TestGatewayConfig:
    """Tests for GatewayConfig value object."""

    def test_create_config(self):
        """Can create gateway config."""
        config = GatewayConfig(
            gateway_type="exclusive",
            routes=[{"condition": "true", "target": "next"}],
            default_route="fallback",
        )

        assert config.gateway_type == "exclusive"
        assert len(config.routes) == 1

    def test_from_dict(self):
        """Can create from dictionary."""
        data = {
            "gateway_type": "parallel",
            "routes": [
                {"condition": "a", "target": "x"},
                {"condition": "b", "target": "y"},
            ],
            "default_route": "z",
        }

        config = GatewayConfig.from_dict(data)

        assert config.gateway_type == "parallel"
        assert len(config.routes) == 2
        assert config.default_route == "z"

    def test_from_dict_defaults(self):
        """Uses defaults for missing fields."""
        data = {}

        config = GatewayConfig.from_dict(data)

        assert config.gateway_type == "exclusive"
        assert config.routes == []
        assert config.default_route is None

    def test_to_dict(self):
        """Can serialize to dictionary."""
        config = GatewayConfig(
            gateway_type="inclusive",
            routes=[{"condition": "test", "target": "target"}],
            default_route="default",
        )

        d = config.to_dict()

        assert d["gateway_type"] == "inclusive"
        assert len(d["routes"]) == 1
