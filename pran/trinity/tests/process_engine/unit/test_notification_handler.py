"""
Unit tests for Notification Handler (Sprint 11 - E14)

Tests for: NotificationHandler, NotificationConfig
Reference: BACKLOG_CORE.md - E14-01
"""

import pytest
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from services.process_engine.domain import (
    ProcessId,
    ExecutionId,
    StepType,
    Version,
    ExecutionStatus,
    NotificationConfig,
)
from services.process_engine.domain.entities import StepDefinition
from services.process_engine.domain.aggregates import ProcessExecution
from services.process_engine.engine.handlers.notification import NotificationHandler
from services.process_engine.engine.step_handler import StepContext, StepConfig


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def notification_handler():
    """Create a NotificationHandler instance."""
    return NotificationHandler()


@pytest.fixture
def slack_config():
    """Create a Slack notification config."""
    return NotificationConfig(
        channel="slack",
        message="Process {{input.name}} completed successfully!",
        webhook_url="https://hooks.slack.com/test",
    )


@pytest.fixture
def email_config():
    """Create an email notification config."""
    return NotificationConfig(
        channel="email",
        message="Your process is complete.",
        recipients=["user@example.com", "admin@example.com"],
        subject="Process Complete",
    )


@pytest.fixture
def webhook_config():
    """Create a generic webhook notification config."""
    return NotificationConfig(
        channel="webhook",
        message="Custom notification payload",
        url="https://example.com/webhook",
    )


@pytest.fixture
def step_definition():
    """Create a notification step definition."""
    return StepDefinition.from_dict({
        "id": "notify-step",
        "name": "Send Notification",
        "type": "notification",
        "channel": "slack",
    })


@pytest.fixture
def process_execution():
    """Create a mock process execution."""
    return ProcessExecution(
        id=ExecutionId.generate(),
        process_id=ProcessId.generate(),
        process_name="notification-test-process",
        process_version=Version.initial(),
        status=ExecutionStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        triggered_by="test",
        input_data={"name": "Test Process", "value": 42},
    )


@pytest.fixture
def step_context(step_definition, process_execution):
    """Create a step context for testing."""
    return StepContext(
        step_definition=step_definition,
        execution=process_execution,
        step_outputs={
            "previous-step": {"result": "success", "data": {"key": "value"}},
        },
        input_data=process_execution.input_data,
    )


# =============================================================================
# NotificationHandler Tests - Basic
# =============================================================================


class TestNotificationHandler:
    """Tests for NotificationHandler basic functionality."""

    def test_step_type(self, notification_handler):
        """Handler returns correct step type."""
        assert notification_handler.step_type == StepType.NOTIFICATION

    @pytest.mark.asyncio
    async def test_invalid_config_type(self, notification_handler, step_context):
        """Returns error for invalid config type."""
        invalid_config = MagicMock(spec=StepConfig)

        result = await notification_handler.execute(step_context, invalid_config)

        assert result.success is False
        assert result.error_code == "INVALID_CONFIG"

    @pytest.mark.asyncio
    async def test_unknown_channel(self, notification_handler, step_context):
        """Returns error for unknown notification channel."""
        config = NotificationConfig(
            channel="unknown_channel",
            message="Test",
        )

        result = await notification_handler.execute(step_context, config)

        assert result.success is False
        assert result.error_code == "INVALID_CHANNEL"


# =============================================================================
# NotificationHandler Tests - Template Rendering
# =============================================================================


class TestNotificationTemplateRendering:
    """Tests for message template rendering."""

    def test_render_template_processes_patterns(self, notification_handler):
        """Template rendering processes {{...}} patterns."""
        from services.process_engine.services import EvaluationContext

        context = EvaluationContext(
            input_data={"name": "John", "count": 5},
            step_outputs={},
            execution_id="exec-123",
            process_name="test",
        )

        template = "Hello {{input.name}}, you have {{input.count}} items."
        result = notification_handler._render_template(template, context)

        # The template should be processed (not unchanged)
        assert result != template
        # The result should contain something for each variable slot
        assert "Hello " in result
        assert " items." in result

    def test_render_template_with_step_outputs(self, notification_handler):
        """Template can reference step outputs."""
        from services.process_engine.services import EvaluationContext

        context = EvaluationContext(
            input_data={},
            step_outputs={
                "analyze": {"score": 85, "label": "good"},
            },
            execution_id="exec-123",
            process_name="test",
        )

        template = "Analysis: {{steps.analyze.output.score}}"
        result = notification_handler._render_template(template, context)

        # Template should be processed
        assert "{{" not in result or result != template

    def test_render_empty_template(self, notification_handler):
        """Empty template returns empty string."""
        from services.process_engine.services import EvaluationContext

        context = EvaluationContext(
            input_data={},
            step_outputs={},
            execution_id="exec-123",
            process_name="test",
        )

        result = notification_handler._render_template("", context)

        assert result == ""

    def test_render_template_without_variables(self, notification_handler):
        """Template without variables passes through unchanged."""
        from services.process_engine.services import EvaluationContext

        context = EvaluationContext(
            input_data={},
            step_outputs={},
            execution_id="exec-123",
            process_name="test",
        )

        template = "Plain text without variables"
        result = notification_handler._render_template(template, context)

        assert result == template


# =============================================================================
# NotificationHandler Tests - Slack
# =============================================================================


class TestSlackNotification:
    """Tests for Slack notification sending."""

    @pytest.mark.asyncio
    async def test_slack_missing_webhook_url(self, notification_handler, step_context):
        """Returns error when Slack webhook URL is missing."""
        config = NotificationConfig(
            channel="slack",
            message="Test message",
            webhook_url=None,  # No URL
        )

        # Also ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            result = await notification_handler.execute(step_context, config)

        assert result.success is False
        assert result.error_code == "MISSING_WEBHOOK_URL"

    @pytest.mark.asyncio
    async def test_slack_env_var_reference(self, notification_handler, step_context):
        """Resolves environment variable reference for webhook URL."""
        config = NotificationConfig(
            channel="slack",
            message="Test",
            webhook_url="${TEST_SLACK_URL}",
        )

        # Env var not set
        with patch.dict(os.environ, {}, clear=True):
            result = await notification_handler.execute(step_context, config)

        assert result.success is False
        assert result.error_code == "MISSING_ENV_VAR"

    @pytest.mark.asyncio
    async def test_slack_success(self, notification_handler, step_context, slack_config):
        """Slack notification succeeds with valid response."""
        # Mock httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await notification_handler.execute(step_context, slack_config)

        assert result.success is True
        assert result.output["channel"] == "slack"
        assert result.output["status"] == "sent"


# =============================================================================
# NotificationHandler Tests - Email
# =============================================================================


class TestEmailNotification:
    """Tests for email notification sending."""

    @pytest.mark.asyncio
    async def test_email_missing_recipients(self, notification_handler, step_context):
        """Returns error when email recipients are missing."""
        config = NotificationConfig(
            channel="email",
            message="Test message",
            recipients=[],  # No recipients
        )

        result = await notification_handler.execute(step_context, config)

        assert result.success is False
        assert result.error_code == "MISSING_RECIPIENTS"

    @pytest.mark.asyncio
    async def test_email_success_stub(self, notification_handler, step_context, email_config):
        """Email notification returns success (stub implementation)."""
        result = await notification_handler.execute(step_context, email_config)

        # Current implementation is a stub
        assert result.success is True
        assert result.output["channel"] == "email"
        assert "recipients" in result.output


# =============================================================================
# NotificationHandler Tests - Webhook
# =============================================================================


class TestWebhookNotification:
    """Tests for generic webhook notification sending."""

    @pytest.mark.asyncio
    async def test_webhook_missing_url(self, notification_handler, step_context):
        """Returns error when webhook URL is missing."""
        config = NotificationConfig(
            channel="webhook",
            message="Test",
            url=None,
        )

        result = await notification_handler.execute(step_context, config)

        assert result.success is False
        assert result.error_code == "MISSING_URL"

    @pytest.mark.asyncio
    async def test_webhook_success(self, notification_handler, step_context, webhook_config):
        """Webhook notification succeeds with valid response."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await notification_handler.execute(step_context, webhook_config)

        assert result.success is True
        assert result.output["channel"] == "webhook"


# =============================================================================
# NotificationConfig Tests
# =============================================================================


class TestNotificationConfig:
    """Tests for NotificationConfig value object."""

    def test_create_slack_config(self):
        """Can create Slack notification config."""
        config = NotificationConfig(
            channel="slack",
            message="Hello!",
            webhook_url="https://hooks.slack.com/test",
        )

        assert config.channel == "slack"
        assert config.webhook_url is not None

    def test_create_email_config(self):
        """Can create email notification config."""
        config = NotificationConfig(
            channel="email",
            message="Your report is ready.",
            recipients=["user@test.com"],
            subject="Report Ready",
        )

        assert config.channel == "email"
        assert len(config.recipients) == 1

    def test_from_dict_slack(self):
        """Can create Slack config from dictionary."""
        data = {
            "channel": "slack",
            "message": "Process complete!",
            "webhook_url": "https://slack.example.com/hook",
        }

        config = NotificationConfig.from_dict(data)

        assert config.channel == "slack"
        assert config.message == "Process complete!"

    def test_from_dict_email(self):
        """Can create email config from dictionary."""
        data = {
            "channel": "email",
            "message": "Hello",
            "recipients": ["a@test.com", "b@test.com"],
            "subject": "Test Subject",
        }

        config = NotificationConfig.from_dict(data)

        assert config.channel == "email"
        assert len(config.recipients) == 2

    def test_from_dict_defaults(self):
        """Uses defaults for missing fields."""
        data = {}

        config = NotificationConfig.from_dict(data)

        assert config.channel == "slack"  # Default
        assert config.message == ""
        assert config.recipients == []

    def test_to_dict(self):
        """Can serialize to dictionary."""
        config = NotificationConfig(
            channel="webhook",
            message="Test message",
            url="https://example.com/hook",
        )

        d = config.to_dict()

        assert d["channel"] == "webhook"
        assert d["message"] == "Test message"
