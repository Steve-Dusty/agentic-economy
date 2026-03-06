"""
Unit tests for Schedule Triggers (Sprint 12 - E9-01, E9-02)

Tests for: CRON_PRESETS, ScheduleTriggerConfig, schedule trigger validation
Reference: BACKLOG_ADVANCED.md - E9-01, E9-02
"""

import pytest
from textwrap import dedent

from services.process_engine.domain import (
    ScheduleTriggerConfig,
    CRON_PRESETS,
    expand_cron_preset,
)
from services.process_engine.services import ProcessValidator


# =============================================================================
# Cron Preset Tests
# =============================================================================


class TestCronPresets:
    """Tests for CRON_PRESETS and expand_cron_preset()."""

    def test_hourly_preset(self):
        """Hourly preset expands to every hour at :00."""
        assert CRON_PRESETS["hourly"] == "0 * * * *"
        assert expand_cron_preset("hourly") == "0 * * * *"

    def test_daily_preset(self):
        """Daily preset expands to 9:00 AM every day."""
        assert CRON_PRESETS["daily"] == "0 9 * * *"
        assert expand_cron_preset("daily") == "0 9 * * *"

    def test_weekly_preset(self):
        """Weekly preset expands to Monday 9:00 AM."""
        assert CRON_PRESETS["weekly"] == "0 9 * * 1"
        assert expand_cron_preset("weekly") == "0 9 * * 1"

    def test_monthly_preset(self):
        """Monthly preset expands to 1st of month at 9:00 AM."""
        assert CRON_PRESETS["monthly"] == "0 9 1 * *"
        assert expand_cron_preset("monthly") == "0 9 1 * *"

    def test_weekdays_preset(self):
        """Weekdays preset expands to Mon-Fri at 9:00 AM."""
        assert CRON_PRESETS["weekdays"] == "0 9 * * 1-5"
        assert expand_cron_preset("weekdays") == "0 9 * * 1-5"

    def test_expand_cron_non_preset(self):
        """Non-preset cron expression passes through unchanged."""
        cron = "*/15 * * * *"
        assert expand_cron_preset(cron) == cron

    def test_expand_cron_custom_expression(self):
        """Custom cron expression passes through unchanged."""
        cron = "30 14 * * 2,4"  # 2:30 PM on Tuesday and Thursday
        assert expand_cron_preset(cron) == cron


# =============================================================================
# ScheduleTriggerConfig Tests
# =============================================================================


class TestScheduleTriggerConfig:
    """Tests for ScheduleTriggerConfig value object."""

    def test_create_with_cron_expression(self):
        """Create config with explicit cron expression."""
        config = ScheduleTriggerConfig(
            id="daily-report",
            cron="0 9 * * 1-5",
            timezone="America/New_York",
        )

        assert config.id == "daily-report"
        assert config.cron == "0 9 * * 1-5"
        assert config.cron_expression == "0 9 * * 1-5"
        assert config.timezone == "America/New_York"
        assert config.enabled is True

    def test_create_with_preset(self):
        """Create config with preset name."""
        config = ScheduleTriggerConfig(
            id="hourly-check",
            cron="hourly",
        )

        assert config.cron == "hourly"
        assert config.cron_expression == "0 * * * *"  # Expanded
        assert config.is_preset is True

    def test_is_preset_false_for_expression(self):
        """is_preset returns False for explicit cron expressions."""
        config = ScheduleTriggerConfig(
            id="custom",
            cron="0 12 * * *",
        )

        assert config.is_preset is False

    def test_from_dict(self):
        """from_dict parses dictionary correctly."""
        data = {
            "id": "test-trigger",
            "cron": "daily",
            "enabled": False,
            "timezone": "Europe/London",
            "description": "Test trigger",
        }

        config = ScheduleTriggerConfig.from_dict(data)

        assert config.id == "test-trigger"
        assert config.cron == "daily"
        assert config.enabled is False
        assert config.timezone == "Europe/London"
        assert config.description == "Test trigger"

    def test_from_dict_defaults(self):
        """from_dict uses defaults for missing fields."""
        data = {"id": "minimal"}

        config = ScheduleTriggerConfig.from_dict(data)

        assert config.cron == ""
        assert config.enabled is True
        assert config.timezone == "UTC"
        assert config.description == ""

    def test_to_dict(self):
        """to_dict serializes correctly."""
        config = ScheduleTriggerConfig(
            id="test",
            cron="weekly",
            enabled=True,
            timezone="UTC",
            description="Weekly job",
        )

        d = config.to_dict()

        assert d["type"] == "schedule"
        assert d["id"] == "test"
        assert d["cron"] == "weekly"
        assert d["cron_expression"] == "0 9 * * 1"  # Expanded in output
        assert d["enabled"] is True

    def test_immutable(self):
        """ScheduleTriggerConfig is immutable (frozen)."""
        config = ScheduleTriggerConfig(id="test", cron="daily")

        with pytest.raises(AttributeError):
            config.cron = "weekly"


# =============================================================================
# Schedule Trigger Validation Tests
# =============================================================================


class TestScheduleTriggerValidation:
    """Tests for schedule trigger validation in ProcessValidator."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return ProcessValidator()

    def test_valid_schedule_trigger_with_preset(self, validator):
        """Schedule trigger with valid preset passes validation."""
        yaml_content = dedent("""
            name: scheduled-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: daily-trigger
                type: schedule
                cron: daily
        """).strip()

        result = validator.validate_yaml(yaml_content)
        assert result.is_valid

    def test_valid_schedule_trigger_with_expression(self, validator):
        """Schedule trigger with valid cron expression passes validation."""
        yaml_content = dedent("""
            name: scheduled-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: custom-trigger
                type: schedule
                cron: "0 9 * * 1-5"
                timezone: America/New_York
        """).strip()

        result = validator.validate_yaml(yaml_content)
        assert result.is_valid

    def test_schedule_trigger_missing_cron(self, validator):
        """Schedule trigger without cron produces error."""
        yaml_content = dedent("""
            name: scheduled-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: no-cron
                type: schedule
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("cron" in e.message.lower() for e in result.errors)

    def test_schedule_trigger_invalid_cron(self, validator):
        """Schedule trigger with invalid cron expression produces error."""
        yaml_content = dedent("""
            name: scheduled-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: bad-cron
                type: schedule
                cron: "invalid cron expression"
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("cron" in e.message.lower() for e in result.errors)

    def test_schedule_trigger_too_few_fields(self, validator):
        """Schedule trigger with incomplete cron expression produces error."""
        yaml_content = dedent("""
            name: scheduled-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: incomplete
                type: schedule
                cron: "0 9 * *"
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("5 fields" in e.message for e in result.errors)

    def test_schedule_trigger_invalid_timezone_warning(self, validator):
        """Schedule trigger with invalid timezone produces warning."""
        yaml_content = dedent("""
            name: scheduled-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: bad-tz
                type: schedule
                cron: daily
                timezone: Invalid/Timezone
        """).strip()

        result = validator.validate_yaml(yaml_content)

        # Should still be valid but with warning
        assert result.is_valid
        assert result.has_warnings
        assert any("timezone" in w.message.lower() for w in result.warnings)

    def test_trigger_missing_id(self, validator):
        """Trigger without id produces error."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - type: schedule
                cron: daily
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("id" in e.message.lower() for e in result.errors)

    def test_invalid_trigger_type(self, validator):
        """Trigger with invalid type produces error."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: bad-type
                type: invalid_type
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("invalid_type" in e.message.lower() or "trigger type" in e.message.lower() for e in result.errors)

    def test_multiple_triggers(self, validator):
        """Process with multiple triggers validates correctly."""
        yaml_content = dedent("""
            name: multi-trigger
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
            triggers:
              - id: webhook-trigger
                type: webhook
              - id: schedule-trigger
                type: schedule
                cron: daily
        """).strip()

        result = validator.validate_yaml(yaml_content)
        assert result.is_valid
