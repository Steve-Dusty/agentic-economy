"""
Timer Step Handler

Handles timer steps by pausing execution for a specified duration.
Used for adding delays within a process flow.

Reference: BACKLOG_ADVANCED.md - E9-03
"""

import asyncio
import logging

from ...domain import StepType, TimerConfig
from ..step_handler import StepHandler, StepResult, StepContext, StepConfig


logger = logging.getLogger(__name__)


class TimerHandler(StepHandler):
    """
    Handler for timer step type.

    Pauses execution for a specified duration.

    Example YAML:
    ```yaml
    steps:
      - id: wait
        name: Wait 5 minutes
        type: timer
        delay: 5m
    ```
    """

    @property
    def step_type(self) -> StepType:
        return StepType.TIMER

    async def execute(
        self,
        context: StepContext,
        config: StepConfig,
    ) -> StepResult:
        """
        Execute a timer step.

        Pauses execution for the configured delay duration.
        """
        if not isinstance(config, TimerConfig):
            return StepResult.fail(
                f"Invalid config type: {type(config).__name__}",
                error_code="INVALID_CONFIG",
            )

        delay_seconds = config.delay.seconds

        logger.info(
            f"Timer step starting: waiting {delay_seconds}s "
            f"(execution={context.execution.id}, step={context.step_definition.id})"
        )

        # Wait for the specified duration
        await asyncio.sleep(delay_seconds)

        logger.info(
            f"Timer step completed: waited {delay_seconds}s "
            f"(execution={context.execution.id}, step={context.step_definition.id})"
        )

        return StepResult.ok({
            "waited_seconds": delay_seconds,
            "delay_formatted": str(config.delay),
        })
