"""
Unit tests for Agent Task Handler.

Tests for: E2-04 Agent Task Step Handler
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    StepDefinition,
    StepType,
    StepId,
    AgentTaskConfig,
    Money,
    Duration,
)
from services.process_engine.engine import StepResult, StepContext
from services.process_engine.engine.handlers.agent_task import (
    AgentTaskHandler,
    AgentGateway,
    AgentTaskError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_gateway():
    """Create a mock AgentGateway."""
    gateway = MagicMock(spec=AgentGateway)
    gateway.check_agent_available = AsyncMock(return_value=True)
    gateway.send_message = AsyncMock(return_value={
        "response": "Agent response text",
        "cost": Money.from_float(0.05),
        "metadata": {"context_used": 1000},
    })
    return gateway


@pytest.fixture
def handler(mock_gateway):
    """Create handler with mock gateway."""
    return AgentTaskHandler(gateway=mock_gateway)


@pytest.fixture
def sample_definition():
    """Create a sample process definition."""
    definition = ProcessDefinition.create(name="test-process")
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-a",
            "type": "agent_task",
            "agent": "research-agent",
            "message": "Research the topic: {{input.topic}}",
            "timeout": "5m",
        }),
    ]
    return definition


@pytest.fixture
def sample_execution(sample_definition):
    """Create a sample execution."""
    return ProcessExecution.create(
        sample_definition,
        input_data={"topic": "Artificial Intelligence"},
    )


@pytest.fixture
def sample_context(sample_execution, sample_definition):
    """Create a sample step context."""
    step = sample_definition.steps[0]
    return StepContext(
        execution=sample_execution,
        step_definition=step,
        step_outputs={},
        input_data=sample_execution.input_data,
    )


# =============================================================================
# Handler Basic Tests
# =============================================================================


class TestAgentTaskHandler:
    """Tests for AgentTaskHandler."""

    def test_step_type(self, handler):
        """Handler reports correct step type."""
        assert handler.step_type == StepType.AGENT_TASK

    @pytest.mark.asyncio
    async def test_execute_success(self, handler, sample_context):
        """Successful execution returns output."""
        config = sample_context.step_definition.config

        result = await handler.execute(sample_context, config)

        assert result.success is True
        assert result.output is not None
        assert "response" in result.output
        assert result.output["agent"] == "research-agent"

    @pytest.mark.asyncio
    async def test_execute_substitutes_input(self, handler, mock_gateway, sample_context):
        """Input variables are substituted in message."""
        config = sample_context.step_definition.config

        await handler.execute(sample_context, config)

        # Check that the message was substituted
        call_args = mock_gateway.send_message.call_args
        sent_message = call_args.kwargs.get("message") or call_args[1].get("message")
        # The message should have "Artificial Intelligence" instead of "{{input.topic}}"
        assert "Artificial Intelligence" in sent_message
        assert "{{input.topic}}" not in sent_message

    @pytest.mark.asyncio
    async def test_execute_agent_unavailable(self, handler, mock_gateway, sample_context):
        """Returns failure when agent is unavailable."""
        mock_gateway.check_agent_available.return_value = False
        config = sample_context.step_definition.config

        result = await handler.execute(sample_context, config)

        assert result.success is False
        assert result.error_code == "AGENT_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_execute_agent_error(self, handler, mock_gateway, sample_context):
        """Returns failure when agent returns error."""
        mock_gateway.send_message.side_effect = AgentTaskError("Connection failed")
        config = sample_context.step_definition.config

        result = await handler.execute(sample_context, config)

        assert result.success is False
        assert result.error_code == "AGENT_ERROR"
        assert "Connection failed" in result.error


# =============================================================================
# Variable Substitution Tests
# =============================================================================


class TestVariableSubstitution:
    """Tests for variable substitution in messages."""

    @pytest.mark.asyncio
    async def test_substitute_multiple_inputs(self, handler, mock_gateway):
        """Multiple input variables are substituted."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "type": "agent_task",
                "agent": "test",
                "message": "Research {{input.topic}} in {{input.language}}",
            }),
        ]

        execution = ProcessExecution.create(definition, input_data={
            "topic": "AI",
            "language": "English",
        })

        context = StepContext(
            execution=execution,
            step_definition=definition.steps[0],
            step_outputs={},
            input_data=execution.input_data,
        )

        await handler.execute(context, definition.steps[0].config)

        call_args = mock_gateway.send_message.call_args
        sent_message = call_args.kwargs.get("message") or call_args[1].get("message")
        assert "AI" in sent_message
        assert "English" in sent_message

    @pytest.mark.asyncio
    async def test_substitute_step_output(self, handler, mock_gateway):
        """Step outputs are substituted."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-b",
                "type": "agent_task",
                "agent": "test",
                "message": "Continue with: {{steps.step-a.output}}",
            }),
        ]

        execution = ProcessExecution.create(definition, input_data={})

        context = StepContext(
            execution=execution,
            step_definition=definition.steps[0],
            step_outputs={
                "step-a": {"response": "Research findings about AI"},
            },
            input_data={},
        )

        await handler.execute(context, definition.steps[0].config)

        call_args = mock_gateway.send_message.call_args
        sent_message = call_args.kwargs.get("message") or call_args[1].get("message")
        assert "Research findings about AI" in sent_message


# =============================================================================
# AgentGateway Tests
# =============================================================================


class TestAgentGateway:
    """Tests for AgentGateway."""

    @pytest.mark.asyncio
    async def test_send_message_with_mock_client(self):
        """Gateway correctly wraps agent client."""
        # Create mock client factory
        mock_response = MagicMock()
        mock_response.response_text = "Hello from agent"
        mock_response.metrics = MagicMock()
        mock_response.metrics.cost_usd = 0.01
        mock_response.metrics.context_used = 500
        mock_response.metrics.context_max = 8000
        # Token usage attributes for E11-01 cost tracking
        mock_response.metrics.input_tokens = 100
        mock_response.metrics.output_tokens = 50
        mock_response.metrics.total_tokens = 150
        mock_response.metrics.model = "gpt-4"

        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value=mock_response)

        def mock_factory(agent_name):
            return mock_client

        gateway = AgentGateway(agent_client_factory=mock_factory)

        result = await gateway.send_message(
            agent_name="test-agent",
            message="Hello",
            timeout=60.0,
        )

        assert result["response"] == "Hello from agent"
        assert result["cost"] is not None
        assert result["token_usage"] is not None
        assert result["token_usage"].total_tokens == 150
        mock_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_error_handling(self):
        """Gateway handles client errors."""
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(side_effect=Exception("Network error"))

        def mock_factory(agent_name):
            return mock_client

        gateway = AgentGateway(agent_client_factory=mock_factory)

        with pytest.raises(AgentTaskError) as exc_info:
            await gateway.send_message(
                agent_name="test-agent",
                message="Hello",
            )

        assert "Network error" in str(exc_info.value)


# =============================================================================
# Integration with Registry
# =============================================================================


class TestHandlerRegistration:
    """Tests for handler registration."""

    def test_register_with_registry(self):
        """Handler can be registered with registry."""
        from services.process_engine.engine import StepHandlerRegistry

        registry = StepHandlerRegistry()
        handler = AgentTaskHandler(gateway=MagicMock())

        registry.register(handler)

        assert registry.has_handler(StepType.AGENT_TASK)
        assert registry.get(StepType.AGENT_TASK) is handler
