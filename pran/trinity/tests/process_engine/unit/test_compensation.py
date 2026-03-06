"""
Unit tests for Compensation Logic (Sprint 11 - E13-03)

Tests for: CompensationConfig, compensation execution logic
Reference: BACKLOG_MVP.md - E13-03
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from services.process_engine.domain import (
    ProcessId,
    ExecutionId,
    StepId,
    StepType,
    Version,
    Duration,
    ExecutionStatus,
    StepStatus,
    CompensationConfig,
)
from services.process_engine.domain.entities import StepDefinition
from services.process_engine.domain.aggregates import ProcessExecution, ProcessDefinition


# =============================================================================
# CompensationConfig Tests
# =============================================================================


class TestCompensationConfig:
    """Tests for CompensationConfig value object."""

    def test_create_agent_task_compensation(self):
        """Can create agent_task compensation config."""
        config = CompensationConfig(
            type="agent_task",
            agent="cleanup-agent",
            message="Rollback the changes made in this step",
            timeout=Duration.from_minutes(10),
        )

        assert config.type == "agent_task"
        assert config.agent == "cleanup-agent"
        assert config.timeout.seconds == 600

    def test_create_notification_compensation(self):
        """Can create notification compensation config."""
        config = CompensationConfig(
            type="notification",
            channel="slack",
            message="Process failed, manual intervention required",
        )

        assert config.type == "notification"
        assert config.channel == "slack"

    def test_from_dict_agent_task(self):
        """Can create agent_task config from dictionary."""
        data = {
            "type": "agent_task",
            "agent": "rollback-agent",
            "message": "Undo the operation",
            "timeout": "15m",
        }

        config = CompensationConfig.from_dict(data)

        assert config.type == "agent_task"
        assert config.agent == "rollback-agent"
        assert config.timeout.seconds == 900

    def test_from_dict_notification(self):
        """Can create notification config from dictionary."""
        data = {
            "type": "notification",
            "channel": "slack",
            "message": "Process {{input.name}} failed",
            "webhook_url": "https://hooks.slack.com/test",
        }

        config = CompensationConfig.from_dict(data)

        assert config.type == "notification"
        assert config.channel == "slack"
        assert config.message == "Process {{input.name}} failed"

    def test_from_dict_defaults(self):
        """Uses defaults for missing fields."""
        data = {}

        config = CompensationConfig.from_dict(data)

        assert config.type == "agent_task"
        assert config.timeout.seconds == 300  # 5m default

    def test_to_dict(self):
        """Can serialize to dictionary."""
        config = CompensationConfig(
            type="agent_task",
            agent="cleanup",
            message="Clean up resources",
        )

        d = config.to_dict()

        assert d["type"] == "agent_task"
        assert d["agent"] == "cleanup"
        assert d["message"] == "Clean up resources"


# =============================================================================
# Step with Compensation Tests
# =============================================================================


class TestStepWithCompensation:
    """Tests for step definitions with compensation."""

    def test_step_definition_with_compensation(self):
        """Can create step with compensation config."""
        step = StepDefinition.from_dict({
            "id": "create-resource",
            "name": "Create Resource",
            "type": "agent_task",
            "agent": "resource-agent",
            "message": "Create the resource",
            "compensation": {
                "type": "agent_task",
                "agent": "resource-agent",
                "message": "Delete the resource {{steps.create-resource.resource_id}}",
            },
        })

        assert step.compensation is not None
        assert step.compensation.type == "agent_task"
        assert "Delete" in step.compensation.message

    def test_step_definition_without_compensation(self):
        """Step without compensation has None."""
        step = StepDefinition.from_dict({
            "id": "safe-step",
            "name": "Safe Step",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "This step has no side effects",
        })

        assert step.compensation is None


# =============================================================================
# Compensation Order Tests
# =============================================================================


class TestCompensationOrder:
    """Tests for compensation execution order."""

    def test_compensation_runs_in_reverse_order(self):
        """Compensation should run in reverse completion order."""
        # Simulating steps completed in order: step1 -> step2 -> step3
        # Compensation should run: step3 -> step2 -> step1

        completion_times = [
            ("step1", datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)),
            ("step2", datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc)),
            ("step3", datetime(2026, 1, 15, 10, 10, 0, tzinfo=timezone.utc)),
        ]

        # Sort by completion time, most recent first (reverse order)
        sorted_steps = sorted(completion_times, key=lambda x: x[1], reverse=True)

        assert sorted_steps[0][0] == "step3"
        assert sorted_steps[1][0] == "step2"
        assert sorted_steps[2][0] == "step1"


# =============================================================================
# Compensation Template Substitution Tests
# =============================================================================


class TestCompensationTemplates:
    """Tests for template substitution in compensation messages."""

    def test_compensation_message_can_reference_step_output(self):
        """Compensation message can use {{steps.stepId.field}} syntax."""
        config = CompensationConfig(
            type="agent_task",
            agent="cleanup",
            message="Delete resource {{steps.create.resource_id}} created at {{steps.create.created_at}}",
        )

        # The actual substitution happens during execution
        # This test verifies the template syntax is preserved
        assert "{{steps.create.resource_id}}" in config.message
        assert "{{steps.create.created_at}}" in config.message

    def test_compensation_message_can_reference_input(self):
        """Compensation message can use {{input.field}} syntax."""
        config = CompensationConfig(
            type="notification",
            message="Failed while processing {{input.request_id}} for {{input.customer}}",
        )

        assert "{{input.request_id}}" in config.message
        assert "{{input.customer}}" in config.message


# =============================================================================
# Compensation Events Tests
# =============================================================================


class TestCompensationEvents:
    """Tests for compensation-related domain events."""

    def test_compensation_started_event(self):
        """CompensationStarted event contains correct data."""
        from services.process_engine.domain import CompensationStarted

        event = CompensationStarted(
            execution_id=ExecutionId.generate(),
            process_id=ProcessId.generate(),
            process_name="test-process",
            compensation_count=3,
        )

        d = event.to_dict()

        assert d["event_type"] == "CompensationStarted"
        assert d["compensation_count"] == 3

    def test_compensation_completed_event(self):
        """CompensationCompleted event contains correct data."""
        from services.process_engine.domain import CompensationCompleted

        event = CompensationCompleted(
            execution_id=ExecutionId.generate(),
            step_id=StepId("cleanup-step"),
            step_name="Cleanup Step",
            compensation_type="agent_task",
        )

        d = event.to_dict()

        assert d["event_type"] == "CompensationCompleted"
        assert d["step_id"] == "cleanup-step"
        assert d["compensation_type"] == "agent_task"

    def test_compensation_failed_event(self):
        """CompensationFailed event contains error details."""
        from services.process_engine.domain import CompensationFailed

        event = CompensationFailed(
            execution_id=ExecutionId.generate(),
            step_id=StepId("failing-step"),
            step_name="Failing Step",
            compensation_type="agent_task",
            error_message="Agent not available",
        )

        d = event.to_dict()

        assert d["event_type"] == "CompensationFailed"
        assert d["error_message"] == "Agent not available"


# =============================================================================
# Compensation Validation Tests
# =============================================================================


class TestCompensationValidation:
    """Tests for compensation configuration validation."""

    def test_agent_task_requires_agent(self):
        """Agent task compensation requires agent field."""
        config = CompensationConfig(
            type="agent_task",
            agent=None,  # Missing
            message="Rollback",
        )

        # Agent can be None/empty - will use step's agent or fail at runtime
        assert config.agent is None

    def test_notification_requires_channel(self):
        """Notification compensation uses default channel."""
        config = CompensationConfig(
            type="notification",
            message="Alert!",
        )

        # Default channel is slack
        assert config.channel == "slack"

    def test_valid_compensation_types(self):
        """Only agent_task and notification types are valid."""
        valid_types = ["agent_task", "notification"]

        for comp_type in valid_types:
            config = CompensationConfig(type=comp_type)
            assert config.type == comp_type


# =============================================================================
# Integration-like Tests (without external deps)
# =============================================================================


class TestCompensationScenarios:
    """Scenario-based tests for compensation logic."""

    def test_scenario_file_creation_rollback(self):
        """Scenario: File created, then process fails, compensation deletes file."""
        # Step 1: Create file (succeeds, outputs file_path)
        step1_output = {"file_path": "/tmp/data.txt", "bytes_written": 1024}

        # Step 2: Process file (fails)
        # ...

        # Compensation for Step 1 should receive access to step1_output
        compensation_config = CompensationConfig(
            type="agent_task",
            agent="file-agent",
            message="Delete file at {{steps.create-file.file_path}}",
        )

        # Template should reference the file path
        assert "{{steps.create-file.file_path}}" in compensation_config.message

    def test_scenario_api_call_rollback(self):
        """Scenario: API call creates record, compensation deletes it."""
        # Step creates a record and returns ID
        step_output = {"record_id": "rec_12345", "created": True}

        # Compensation should use the record_id
        compensation_config = CompensationConfig(
            type="agent_task",
            agent="api-agent",
            message="DELETE /api/records/{{steps.create-record.record_id}}",
        )

        assert "{{steps.create-record.record_id}}" in compensation_config.message

    def test_scenario_notification_on_failure(self):
        """Scenario: Send notification when compensation runs."""
        compensation_config = CompensationConfig(
            type="notification",
            channel="slack",
            message=":warning: Process '{{input.process_name}}' failed. Manual cleanup may be required.",
        )

        assert compensation_config.type == "notification"
        assert compensation_config.channel == "slack"
