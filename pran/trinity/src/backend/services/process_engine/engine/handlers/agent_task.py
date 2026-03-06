"""
Agent Task Step Handler

Executes agent_task steps by sending messages to Trinity agents.
Uses AgentGateway as an Anti-Corruption Layer to the existing agent system.

Reference: BACKLOG_MVP.md - E2-04
Reference: IT3 Section 8 (Anti-Corruption Layers - AgentGateway)
"""

import logging
from typing import Any, Optional

from ...domain import StepType, AgentTaskConfig, Money, TokenUsage
from ...services import ExpressionEvaluator, EvaluationContext
from ..step_handler import StepHandler, StepResult, StepContext, StepConfig


logger = logging.getLogger(__name__)


class AgentGateway:
    """
    Anti-Corruption Layer for agent communication.

    Wraps the existing Trinity agent client to provide a clean interface
    for the process engine. Handles:
    - Agent discovery and availability checking
    - Message formatting and context injection
    - Response parsing and cost extraction
    - Error handling and timeout management
    """

    def __init__(self, agent_client_factory=None):
        """
        Initialize the gateway.

        Args:
            agent_client_factory: Factory for creating AgentClient instances.
                                 If None, uses the default factory.
        """
        self._client_factory = agent_client_factory or self._default_client_factory

    @staticmethod
    def _default_client_factory(agent_name: str):
        """Default factory using Trinity's AgentClient."""
        # Import here to avoid circular dependencies
        from services.agent_client import AgentClient
        return AgentClient(agent_name)

    async def send_message(
        self,
        agent_name: str,
        message: str,
        timeout: float = 300.0,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Send a message to an agent and get the response.

        Args:
            agent_name: Name of the target agent
            message: Message to send
            timeout: Timeout in seconds
            context: Optional context data to include

        Returns:
            Dictionary containing:
            - response: The agent's text response
            - cost: Cost of the operation (Money object, if available)
            - token_usage: TokenUsage object with input/output/total tokens (if available)
            - metadata: Additional response metadata
        """
        try:
            client = self._client_factory(agent_name)
            response = await client.chat(message, timeout=timeout)

            # Extract cost if available
            cost = None
            if response.metrics and response.metrics.cost_usd:
                cost = Money.from_float(response.metrics.cost_usd)

            # Extract token usage if available
            token_usage = None
            if response.metrics:
                metrics = response.metrics
                # Check for token fields (different LLMs may report differently)
                input_tokens = getattr(metrics, 'input_tokens', 0) or getattr(metrics, 'prompt_tokens', 0) or 0
                output_tokens = getattr(metrics, 'output_tokens', 0) or getattr(metrics, 'completion_tokens', 0) or 0
                total_tokens = getattr(metrics, 'total_tokens', 0) or (input_tokens + output_tokens)

                if total_tokens > 0:
                    token_usage = TokenUsage(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                        model=getattr(metrics, 'model', None),
                    )

            return {
                "response": response.response_text,
                "cost": cost,
                "token_usage": token_usage,
                "metadata": {
                    "context_used": response.metrics.context_used if response.metrics else None,
                    "context_max": response.metrics.context_max if response.metrics else None,
                },
            }
        except Exception as e:
            logger.error(f"AgentGateway error for {agent_name}: {e}")
            raise AgentTaskError(f"Failed to communicate with agent '{agent_name}': {e}") from e

    async def check_agent_available(self, agent_name: str) -> bool:
        """
        Check if an agent is available.

        Args:
            agent_name: Name of the agent to check

        Returns:
            True if agent is running and reachable
        """
        try:
            # Try to get the agent container
            from services.docker_service import get_agent_container
            container = get_agent_container(agent_name)
            return container is not None and container.status == "running"
        except Exception:
            return False


class AgentTaskError(Exception):
    """Error during agent task execution."""
    pass


class AgentTaskHandler(StepHandler):
    """
    Handler for agent_task step type.

    Sends messages to Trinity agents and captures their responses
    as step output.
    """

    def __init__(
        self,
        gateway: Optional[AgentGateway] = None,
        expression_evaluator: Optional[ExpressionEvaluator] = None,
    ):
        """
        Initialize handler.

        Args:
            gateway: Optional AgentGateway instance. If None, creates default.
            expression_evaluator: Optional expression evaluator. If None, creates default.
        """
        self.gateway = gateway or AgentGateway()
        self.expression_evaluator = expression_evaluator or ExpressionEvaluator()

    @property
    def step_type(self) -> StepType:
        return StepType.AGENT_TASK

    async def execute(
        self,
        context: StepContext,
        config: StepConfig,
    ) -> StepResult:
        """
        Execute an agent task.

        Sends the configured message to the specified agent and
        captures the response as step output.
        """
        if not isinstance(config, AgentTaskConfig):
            return StepResult.fail(
                f"Invalid config type: {type(config).__name__}",
                error_code="INVALID_CONFIG",
            )

        agent_name = config.agent
        message = config.message

        # Substitute variables in message using ExpressionEvaluator
        message = self._substitute_variables(message, context)

        # Also substitute agent name if it's a variable
        agent_name = self._substitute_variables(agent_name, context)

        # Get timeout
        timeout = config.timeout.seconds if config.timeout else 300

        logger.info(f"Executing agent task: agent={agent_name}, timeout={timeout}s")

        try:
            # Check agent availability first
            if not await self.gateway.check_agent_available(agent_name):
                return StepResult.fail(
                    f"Agent '{agent_name}' is not available",
                    error_code="AGENT_UNAVAILABLE",
                )

            # Send message
            result = await self.gateway.send_message(
                agent_name=agent_name,
                message=message,
                timeout=timeout,
                context={
                    "execution_id": str(context.execution.id),
                    "step_id": str(context.step_definition.id),
                    "process_name": context.execution.process_name,
                },
            )

            # Build output
            output = {
                "response": result["response"],
                "agent": agent_name,
            }

            # Include cost if available
            if result.get("cost"):
                output["cost"] = str(result["cost"])

            # Include token usage if available
            if result.get("token_usage"):
                output["token_usage"] = result["token_usage"].to_dict()

            return StepResult.ok(output)

        except AgentTaskError as e:
            return StepResult.fail(str(e), error_code="AGENT_ERROR")
        except Exception as e:
            logger.exception(f"Unexpected error in agent task")
            return StepResult.fail(str(e), error_code="UNEXPECTED_ERROR")

    def _substitute_variables(self, template: str, context: StepContext) -> str:
        """
        Substitute variables in the template using ExpressionEvaluator.

        Supports:
        - {{input.X}} - Process input data
        - {{input.X.Y}} - Nested input data
        - {{steps.X.output}} - Full step output
        - {{steps.X.output.Y}} - Nested field in step output
        - {{execution.id}} - Execution ID
        - {{process.name}} - Process name
        """
        eval_context = EvaluationContext(
            input_data=context.input_data,
            step_outputs=context.step_outputs,
            execution_id=str(context.execution.id),
            process_name=context.execution.process_name,
        )

        return self.expression_evaluator.evaluate(template, eval_context)
