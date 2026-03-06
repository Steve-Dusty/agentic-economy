"""
Unit tests for Webhook Triggers (Sprint 10 - E8)

Tests for: WebhookTriggerConfig
Reference: BACKLOG_CORE.md - E8-01
"""

import pytest
from textwrap import dedent

from services.process_engine.domain import WebhookTriggerConfig
from services.process_engine.services import ProcessValidator


# =============================================================================
# WebhookTriggerConfig Tests
# =============================================================================


class TestWebhookTriggerConfig:
    """Tests for WebhookTriggerConfig value object."""

    def test_create_config(self):
        """Can create webhook trigger config."""
        config = WebhookTriggerConfig(
            id="my-webhook",
            enabled=True,
            description="Test webhook trigger",
        )

        assert config.id == "my-webhook"
        assert config.enabled is True
        assert config.secret is None

    def test_create_with_secret(self):
        """Can create webhook trigger with secret."""
        config = WebhookTriggerConfig(
            id="secure-webhook",
            secret="my-secret-key",
        )

        assert config.secret == "my-secret-key"

    def test_from_dict(self):
        """Can create from dictionary."""
        data = {
            "id": "webhook-1",
            "enabled": False,
            "secret": "secret123",
            "description": "A webhook trigger",
        }

        config = WebhookTriggerConfig.from_dict(data)

        assert config.id == "webhook-1"
        assert config.enabled is False
        assert config.secret == "secret123"
        assert config.description == "A webhook trigger"

    def test_from_dict_defaults(self):
        """Uses defaults for missing fields."""
        data = {"id": "minimal"}

        config = WebhookTriggerConfig.from_dict(data)

        assert config.enabled is True
        assert config.secret is None
        assert config.description == ""

    def test_to_dict(self):
        """Can serialize to dictionary."""
        config = WebhookTriggerConfig(
            id="test-webhook",
            enabled=True,
            secret="secret",
            description="Test",
        )

        d = config.to_dict()

        assert d["type"] == "webhook"
        assert d["id"] == "test-webhook"
        assert d["enabled"] is True
        assert d["description"] == "Test"
        # Secret is intentionally NOT serialized (security)
        assert "secret" not in d

    def test_immutable(self):
        """WebhookTriggerConfig is immutable."""
        config = WebhookTriggerConfig(id="test")

        with pytest.raises(AttributeError):
            config.id = "changed"


# =============================================================================
# Webhook Trigger Validation Tests
# =============================================================================


class TestWebhookTriggerValidation:
    """Tests for webhook trigger validation in ProcessValidator."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return ProcessValidator()

    def test_valid_webhook_trigger(self, validator):
        """Valid webhook trigger passes validation."""
        yaml_content = dedent("""
            name: webhook-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: api-trigger
                type: webhook
                description: API trigger for automation
        """).strip()

        result = validator.validate_yaml(yaml_content)
        assert result.is_valid

    def test_webhook_trigger_with_secret(self, validator):
        """Webhook trigger with secret passes validation."""
        yaml_content = dedent("""
            name: secure-webhook-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: secure-trigger
                type: webhook
                secret: my-secret-123
        """).strip()

        result = validator.validate_yaml(yaml_content)
        assert result.is_valid

    def test_webhook_trigger_disabled(self, validator):
        """Disabled webhook trigger passes validation."""
        yaml_content = dedent("""
            name: disabled-webhook
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: disabled-trigger
                type: webhook
                enabled: false
        """).strip()

        result = validator.validate_yaml(yaml_content)
        assert result.is_valid

    def test_default_trigger_type_is_webhook(self, validator):
        """Trigger without explicit type defaults to webhook."""
        yaml_content = dedent("""
            name: default-type-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: implicit-webhook
                description: No type specified, defaults to webhook
        """).strip()

        result = validator.validate_yaml(yaml_content)
        assert result.is_valid

    def test_multiple_webhook_triggers(self, validator):
        """Multiple webhook triggers in same process passes validation."""
        yaml_content = dedent("""
            name: multi-webhook
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: webhook-1
                type: webhook
                description: First webhook
              - id: webhook-2
                type: webhook
                description: Second webhook
        """).strip()

        result = validator.validate_yaml(yaml_content)
        assert result.is_valid

    def test_mixed_trigger_types(self, validator):
        """Process with both webhook and schedule triggers passes validation."""
        yaml_content = dedent("""
            name: mixed-triggers
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: webhook-trigger
                type: webhook
                description: Manual trigger
              - id: schedule-trigger
                type: schedule
                cron: daily
                description: Scheduled trigger
        """).strip()

        result = validator.validate_yaml(yaml_content)
        assert result.is_valid


# =============================================================================
# Trigger URL Generation Tests
# =============================================================================


class TestWebhookTriggerURL:
    """Tests for webhook trigger URL logic."""

    def test_webhook_url_format(self):
        """Webhook trigger ID is used in URL construction."""
        config = WebhookTriggerConfig(id="my-process-trigger")

        # URL would be: /api/triggers/webhook/{id}
        expected_path = f"/api/triggers/webhook/{config.id}"

        assert expected_path == "/api/triggers/webhook/my-process-trigger"

    def test_trigger_id_uniqueness(self):
        """Different triggers have different IDs."""
        trigger1 = WebhookTriggerConfig(id="trigger-a")
        trigger2 = WebhookTriggerConfig(id="trigger-b")

        assert trigger1.id != trigger2.id
