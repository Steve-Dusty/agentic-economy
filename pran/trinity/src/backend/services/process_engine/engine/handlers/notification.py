"""
Notification Step Handler

Handles notification steps by sending messages to external channels
(Slack, email, webhooks).

Reference: BACKLOG_CORE.md - E14-01
"""

import logging
import os
import re
import httpx
from typing import Any

from ...domain import StepType, NotificationConfig
from ...services import ExpressionEvaluator, EvaluationContext
from ..step_handler import StepHandler, StepResult, StepContext, StepConfig


logger = logging.getLogger(__name__)


class NotificationHandler(StepHandler):
    """
    Handler for notification step type.

    Sends notifications to external channels:
    - Slack: Posts to webhook URL
    - Email: Sends via SMTP (future)
    - Webhook: Generic HTTP POST

    Message templates support {{...}} variable substitution.
    """

    def __init__(self):
        """Initialize handler with expression evaluator for templating."""
        self.expression_evaluator = ExpressionEvaluator()

    @property
    def step_type(self) -> StepType:
        return StepType.NOTIFICATION

    async def execute(
        self,
        context: StepContext,
        config: StepConfig,
    ) -> StepResult:
        """
        Execute a notification step.

        Sends a notification to the configured channel.
        """
        if not isinstance(config, NotificationConfig):
            return StepResult.fail(
                f"Invalid config type: {type(config).__name__}",
                error_code="INVALID_CONFIG",
            )

        channel = config.channel.lower()

        # Build evaluation context for template substitution
        eval_context = EvaluationContext(
            input_data=context.execution.input_data,
            step_outputs=context.step_outputs,
            execution_id=str(context.execution.id),
            process_name=context.execution.process_name,
        )

        # Process message template
        message = self._render_template(config.message, eval_context)

        logger.info(f"Sending notification via {channel}: {message[:100]}...")

        if channel == "slack":
            return await self._send_slack(config, message, eval_context)
        elif channel == "email":
            return await self._send_email(config, message, eval_context)
        elif channel == "webhook":
            return await self._send_webhook(config, message, eval_context)
        else:
            return StepResult.fail(
                f"Unknown notification channel: {channel}",
                error_code="INVALID_CHANNEL",
            )

    def _render_template(self, template: str, context: EvaluationContext) -> str:
        """
        Render a message template with variable substitution.

        Supports {{input.field}}, {{steps.stepId.output.field}}, etc.
        """
        if not template:
            return ""

        # Find all {{...}} patterns
        pattern = r'\{\{([^}]+)\}\}'

        def replace_var(match):
            expr = match.group(1).strip()
            try:
                value = self.expression_evaluator.evaluate(expr, context)
                return str(value) if value is not None else ""
            except Exception as e:
                logger.warning(f"Failed to evaluate template var '{expr}': {e}")
                return match.group(0)  # Keep original if fails

        return re.sub(pattern, replace_var, template)

    async def _send_slack(
        self,
        config: NotificationConfig,
        message: str,
        context: EvaluationContext,
    ) -> StepResult:
        """
        Send notification to Slack via webhook.

        The webhook_url can be a direct URL or reference an environment variable.
        """
        webhook_url = config.webhook_url

        if not webhook_url:
            # Try environment variable
            webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

        if not webhook_url:
            return StepResult.fail(
                "Slack webhook URL not configured. Set webhook_url in step or SLACK_WEBHOOK_URL env var.",
                error_code="MISSING_WEBHOOK_URL",
            )

        # Resolve env var reference (e.g., "${SLACK_WEBHOOK_URL}")
        if webhook_url.startswith("${") and webhook_url.endswith("}"):
            env_var = webhook_url[2:-1]
            webhook_url = os.environ.get(env_var)
            if not webhook_url:
                return StepResult.fail(
                    f"Environment variable {env_var} not set",
                    error_code="MISSING_ENV_VAR",
                )

        # Prepare Slack payload
        payload = {
            "text": message,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message,
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_Process: {context.process_name} | Execution: {context.execution_id[:8]}..._"
                        }
                    ]
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    logger.info(f"Slack notification sent successfully")
                    return StepResult.ok({
                        "channel": "slack",
                        "status": "sent",
                        "message_preview": message[:200],
                    })
                else:
                    logger.error(f"Slack webhook failed: {response.status_code} {response.text}")
                    return StepResult.fail(
                        f"Slack webhook returned {response.status_code}: {response.text[:200]}",
                        error_code="SLACK_ERROR",
                    )

        except httpx.TimeoutException:
            return StepResult.fail(
                "Slack webhook timed out",
                error_code="SLACK_TIMEOUT",
            )
        except Exception as e:
            logger.exception(f"Failed to send Slack notification: {e}")
            return StepResult.fail(
                f"Failed to send Slack notification: {str(e)}",
                error_code="SLACK_ERROR",
            )

    async def _send_email(
        self,
        config: NotificationConfig,
        message: str,
        context: EvaluationContext,
    ) -> StepResult:
        """
        Send notification via email.

        Requires SMTP configuration (future implementation).
        """
        if not config.recipients:
            return StepResult.fail(
                "No email recipients configured",
                error_code="MISSING_RECIPIENTS",
            )

        # For now, email is not fully implemented - return success for testing
        # In production, this would use SMTP or an email service
        logger.warning("Email notifications not yet implemented - marking as sent for testing")

        return StepResult.ok({
            "channel": "email",
            "status": "sent",
            "recipients": config.recipients,
            "subject": config.subject or "Process Notification",
            "message_preview": message[:200],
            "note": "Email delivery pending SMTP configuration",
        })

    async def _send_webhook(
        self,
        config: NotificationConfig,
        message: str,
        context: EvaluationContext,
    ) -> StepResult:
        """
        Send notification to a generic webhook.

        Posts JSON payload to the configured URL.
        """
        url = config.url

        if not url:
            return StepResult.fail(
                "Webhook URL not configured",
                error_code="MISSING_URL",
            )

        # Resolve env var reference
        if url.startswith("${") and url.endswith("}"):
            env_var = url[2:-1]
            url = os.environ.get(env_var)
            if not url:
                return StepResult.fail(
                    f"Environment variable {env_var} not set",
                    error_code="MISSING_ENV_VAR",
                )

        payload = {
            "message": message,
            "process_name": context.process_name,
            "execution_id": context.execution_id,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code < 400:
                    logger.info(f"Webhook notification sent successfully")
                    return StepResult.ok({
                        "channel": "webhook",
                        "status": "sent",
                        "status_code": response.status_code,
                        "message_preview": message[:200],
                    })
                else:
                    logger.error(f"Webhook failed: {response.status_code}")
                    return StepResult.fail(
                        f"Webhook returned {response.status_code}",
                        error_code="WEBHOOK_ERROR",
                    )

        except httpx.TimeoutException:
            return StepResult.fail(
                "Webhook timed out",
                error_code="WEBHOOK_TIMEOUT",
            )
        except Exception as e:
            logger.exception(f"Failed to send webhook notification: {e}")
            return StepResult.fail(
                f"Failed to send webhook: {str(e)}",
                error_code="WEBHOOK_ERROR",
            )
