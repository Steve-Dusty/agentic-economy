"""
Unit tests for Human Approval Handler (Sprint 9 - E6)

Tests for: HumanApprovalHandler, ApprovalStore, ApprovalRequest
Reference: BACKLOG_CORE.md - E6-01, E6-02
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from services.process_engine.domain import (
    ProcessId,
    ExecutionId,
    StepId,
    StepType,
    Duration,
    Version,
    ExecutionStatus,
    ApprovalStatus,
    HumanApprovalConfig,
)
from services.process_engine.domain.entities import StepDefinition, ApprovalRequest
from services.process_engine.domain.aggregates import ProcessExecution
from services.process_engine.engine.handlers.human_approval import (
    HumanApprovalHandler,
    ApprovalStore,
)
from services.process_engine.engine.step_handler import StepContext, StepConfig


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fresh_approval_store():
    """Create a fresh approval store for each test."""
    store = ApprovalStore.__new__(ApprovalStore)
    store._requests = {}
    return store


@pytest.fixture
def approval_handler(fresh_approval_store):
    """Create a HumanApprovalHandler with fresh store."""
    return HumanApprovalHandler(approval_store=fresh_approval_store)


@pytest.fixture
def approval_config():
    """Create a basic approval config."""
    return HumanApprovalConfig(
        title="Review Document",
        description="Please review and approve the document",
        assignees=["manager@example.com"],
    )


@pytest.fixture
def approval_config_with_timeout():
    """Create an approval config with timeout."""
    return HumanApprovalConfig(
        title="Urgent Review",
        description="Needs approval within 1 hour",
        assignees=["admin@example.com"],
        timeout=Duration.from_hours(1),
    )


@pytest.fixture
def step_definition():
    """Create an approval step definition."""
    return StepDefinition.from_dict({
        "id": "approval-step",
        "name": "Manager Approval",
        "type": "human_approval",
        "title": "Review Required",
        "description": "Please approve",
    })


@pytest.fixture
def process_execution():
    """Create a mock process execution."""
    return ProcessExecution(
        id=ExecutionId.generate(),
        process_id=ProcessId.generate(),
        process_name="approval-test-process",
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
# ApprovalStore Tests
# =============================================================================


class TestApprovalStore:
    """Tests for ApprovalStore."""

    def test_save_and_get(self, fresh_approval_store):
        """Can save and retrieve approval request."""
        request = ApprovalRequest.create(
            execution_id="exec-123",
            step_id="step-1",
            title="Test Approval",
            description="Test description",
            assignees=["user@example.com"],
        )

        fresh_approval_store.save(request)
        retrieved = fresh_approval_store.get(request.id)

        assert retrieved is not None
        assert retrieved.id == request.id
        assert retrieved.title == "Test Approval"

    def test_get_nonexistent(self, fresh_approval_store):
        """Returns None for non-existent request."""
        result = fresh_approval_store.get("nonexistent-id")
        assert result is None

    def test_get_by_execution_step(self, fresh_approval_store):
        """Can retrieve by execution and step ID."""
        request = ApprovalRequest.create(
            execution_id="exec-456",
            step_id="step-2",
            title="Another Approval",
            description="Description",
            assignees=[],
        )

        fresh_approval_store.save(request)
        retrieved = fresh_approval_store.get_by_execution_step("exec-456", "step-2")

        assert retrieved is not None
        assert retrieved.id == request.id

    def test_get_by_execution_step_not_found(self, fresh_approval_store):
        """Returns None when execution/step combo not found."""
        result = fresh_approval_store.get_by_execution_step("wrong-exec", "wrong-step")
        assert result is None

    def test_get_all_pending(self, fresh_approval_store):
        """Returns all pending approval requests."""
        req1 = ApprovalRequest.create(
            execution_id="exec-1",
            step_id="step-1",
            title="Pending 1",
            description="",
            assignees=[],
        )
        req2 = ApprovalRequest.create(
            execution_id="exec-2",
            step_id="step-2",
            title="Pending 2",
            description="",
            assignees=[],
        )

        fresh_approval_store.save(req1)
        fresh_approval_store.save(req2)

        pending = fresh_approval_store.get_all_pending()

        assert len(pending) == 2

    def test_get_pending_for_user(self, fresh_approval_store):
        """Returns pending approvals for specific user."""
        req1 = ApprovalRequest.create(
            execution_id="exec-1",
            step_id="step-1",
            title="For User A",
            description="",
            assignees=["user-a@example.com"],
        )
        req2 = ApprovalRequest.create(
            execution_id="exec-2",
            step_id="step-2",
            title="For User B",
            description="",
            assignees=["user-b@example.com"],
        )

        fresh_approval_store.save(req1)
        fresh_approval_store.save(req2)

        user_a_pending = fresh_approval_store.get_pending_for_user("user-a@example.com")

        assert len(user_a_pending) == 1
        assert user_a_pending[0].title == "For User A"


# =============================================================================
# ApprovalRequest Tests
# =============================================================================


class TestApprovalRequest:
    """Tests for ApprovalRequest entity."""

    def test_create(self):
        """Can create approval request."""
        request = ApprovalRequest.create(
            execution_id="exec-123",
            step_id="step-1",
            title="Test",
            description="Description",
            assignees=["user@example.com"],
        )

        assert request.id is not None
        assert request.status == ApprovalStatus.PENDING
        assert request.is_pending() is True

    def test_create_with_deadline(self):
        """Can create approval with deadline."""
        deadline = datetime.now(timezone.utc) + timedelta(hours=24)
        request = ApprovalRequest.create(
            execution_id="exec-123",
            step_id="step-1",
            title="Test",
            description="",
            assignees=[],
            deadline=deadline,
        )

        assert request.deadline == deadline

    def test_approve(self):
        """Can approve request."""
        request = ApprovalRequest.create(
            execution_id="exec-123",
            step_id="step-1",
            title="Test",
            description="",
            assignees=["user@example.com"],
        )

        request.approve(
            decided_by="manager@example.com",
            comment="Looks good!",
        )

        assert request.status == ApprovalStatus.APPROVED
        assert request.decided_by == "manager@example.com"
        assert request.decision_comment == "Looks good!"
        assert request.decided_at is not None

    def test_reject(self):
        """Can reject request."""
        request = ApprovalRequest.create(
            execution_id="exec-123",
            step_id="step-1",
            title="Test",
            description="",
            assignees=[],
        )

        request.reject(
            decided_by="admin@example.com",
            comment="Needs more work",
        )

        assert request.status == ApprovalStatus.REJECTED
        assert request.decided_by == "admin@example.com"

    def test_can_be_decided_by_assignee(self):
        """Assignee can decide on request."""
        request = ApprovalRequest.create(
            execution_id="exec-123",
            step_id="step-1",
            title="Test",
            description="",
            assignees=["user@example.com", "admin@example.com"],
        )

        assert request.can_be_decided_by("user@example.com") is True
        assert request.can_be_decided_by("admin@example.com") is True
        assert request.can_be_decided_by("other@example.com") is False

    def test_can_be_decided_by_any_when_no_assignees(self):
        """Anyone can decide when no assignees specified."""
        request = ApprovalRequest.create(
            execution_id="exec-123",
            step_id="step-1",
            title="Test",
            description="",
            assignees=[],  # No specific assignees
        )

        assert request.can_be_decided_by("anyone@example.com") is True


# =============================================================================
# HumanApprovalHandler Tests
# =============================================================================


class TestHumanApprovalHandler:
    """Tests for HumanApprovalHandler."""

    def test_step_type(self, approval_handler):
        """Handler returns correct step type."""
        assert approval_handler.step_type == StepType.HUMAN_APPROVAL

    @pytest.mark.asyncio
    async def test_execute_creates_approval_request(
        self, approval_handler, step_context, approval_config, fresh_approval_store
    ):
        """Executing creates approval request and returns wait result."""
        result = await approval_handler.execute(step_context, approval_config)

        assert result.waiting is True
        assert "approval_id" in result.output

        # Verify request was stored
        approval_id = result.output["approval_id"]
        stored = fresh_approval_store.get(approval_id)
        assert stored is not None
        assert stored.title == "Review Document"

    @pytest.mark.asyncio
    async def test_execute_returns_existing_pending(
        self, approval_handler, step_context, approval_config, fresh_approval_store
    ):
        """Returns existing pending request if already exists."""
        # First execution
        result1 = await approval_handler.execute(step_context, approval_config)
        approval_id = result1.output["approval_id"]

        # Second execution (same step)
        result2 = await approval_handler.execute(step_context, approval_config)

        assert result2.waiting is True
        assert result2.output["approval_id"] == approval_id

    @pytest.mark.asyncio
    async def test_execute_completes_if_approved(
        self, approval_handler, step_context, approval_config, fresh_approval_store
    ):
        """Returns success if request was already approved."""
        # Create and approve request
        request = ApprovalRequest.create(
            execution_id=str(step_context.execution.id),
            step_id=str(step_context.step_definition.id),
            title="Test",
            description="",
            assignees=[],
        )
        request.approve(decided_by="manager@example.com", comment="OK")
        fresh_approval_store.save(request)

        # Execute handler
        result = await approval_handler.execute(step_context, approval_config)

        assert result.success is True
        assert result.output["decision"] == "approved"

    @pytest.mark.asyncio
    async def test_execute_fails_if_rejected(
        self, approval_handler, step_context, approval_config, fresh_approval_store
    ):
        """Returns failure if request was rejected."""
        # Create and reject request
        request = ApprovalRequest.create(
            execution_id=str(step_context.execution.id),
            step_id=str(step_context.step_definition.id),
            title="Test",
            description="",
            assignees=[],
        )
        request.reject(decided_by="admin@example.com", comment="Rejected")
        fresh_approval_store.save(request)

        # Execute handler
        result = await approval_handler.execute(step_context, approval_config)

        assert result.success is False
        assert result.error_code == "APPROVAL_REJECTED"

    @pytest.mark.asyncio
    async def test_execute_invalid_config(self, approval_handler, step_context):
        """Returns error for invalid config type."""
        invalid_config = MagicMock(spec=StepConfig)

        result = await approval_handler.execute(step_context, invalid_config)

        assert result.success is False
        assert result.error_code == "INVALID_CONFIG"

    @pytest.mark.asyncio
    async def test_execute_sets_deadline(
        self, approval_handler, step_context, approval_config_with_timeout, fresh_approval_store
    ):
        """Sets deadline when timeout is configured."""
        result = await approval_handler.execute(step_context, approval_config_with_timeout)

        approval_id = result.output["approval_id"]
        stored = fresh_approval_store.get(approval_id)

        assert stored.deadline is not None
        # Deadline should be roughly 1 hour from now
        expected_deadline = datetime.now(timezone.utc) + timedelta(hours=1)
        assert abs((stored.deadline - expected_deadline).total_seconds()) < 5


# =============================================================================
# HumanApprovalConfig Tests
# =============================================================================


class TestHumanApprovalConfig:
    """Tests for HumanApprovalConfig value object."""

    def test_create_config(self):
        """Can create approval config."""
        config = HumanApprovalConfig(
            title="Review",
            description="Please review",
            assignees=["user@example.com"],
        )

        assert config.title == "Review"
        assert len(config.assignees) == 1

    def test_from_dict(self):
        """Can create from dictionary."""
        data = {
            "title": "Approval Title",
            "description": "Description text",
            "assignees": ["a@test.com", "b@test.com"],
            "timeout": "12h",
        }

        config = HumanApprovalConfig.from_dict(data)

        assert config.title == "Approval Title"
        assert len(config.assignees) == 2
        assert config.timeout.seconds == 12 * 3600

    def test_from_dict_defaults(self):
        """Uses defaults for missing fields."""
        data = {
            "title": "Minimal",
            "description": "Test",
        }

        config = HumanApprovalConfig.from_dict(data)

        assert config.assignees == []
        assert config.timeout.seconds == 24 * 3600  # Default 24h

    def test_to_dict(self):
        """Can serialize to dictionary."""
        config = HumanApprovalConfig(
            title="Test",
            description="Description",
            assignees=["user@test.com"],
        )

        d = config.to_dict()

        assert d["title"] == "Test"
        assert d["description"] == "Description"


# =============================================================================
# Template Variable Substitution Tests (Bug Fix: 2026-01-23)
# =============================================================================


class TestHumanApprovalTemplateSubstitution:
    """Tests for template variable substitution in HumanApprovalHandler."""

    @pytest.fixture
    def step_context_with_data(self, step_definition, process_execution):
        """Create a step context with input data and step outputs."""
        return StepContext(
            step_definition=step_definition,
            execution=process_execution,
            step_outputs={
                "intake": {"response": "Intake complete", "score": 85}
            },
            input_data={
                "company_name": "TestCo AI",
                "deal_type": "Series A"
            },
        )

    @pytest.fixture
    def approval_config_with_templates(self):
        """Create an approval config with template variables."""
        return HumanApprovalConfig(
            title="Approve {{input.company_name}} for {{input.deal_type}}?",
            description="Based on intake: {{steps.intake.output.response}}",
            assignees=["manager@example.com"],
        )

    @pytest.mark.asyncio
    async def test_execute_substitutes_title_variables(
        self, approval_handler, step_context_with_data, approval_config_with_templates, fresh_approval_store
    ):
        """Template variables in title are substituted."""
        result = await approval_handler.execute(step_context_with_data, approval_config_with_templates)

        assert result.waiting is True
        approval_id = result.output["approval_id"]
        stored = fresh_approval_store.get(approval_id)

        # Title should have substituted values
        assert stored.title == "Approve TestCo AI for Series A?"
        assert "{{input" not in stored.title

    @pytest.mark.asyncio
    async def test_execute_substitutes_description_variables(
        self, approval_handler, step_context_with_data, approval_config_with_templates, fresh_approval_store
    ):
        """Template variables in description are substituted."""
        result = await approval_handler.execute(step_context_with_data, approval_config_with_templates)

        approval_id = result.output["approval_id"]
        stored = fresh_approval_store.get(approval_id)

        # Description should have substituted step output
        assert stored.description == "Based on intake: Intake complete"
        assert "{{steps" not in stored.description

    @pytest.mark.asyncio
    async def test_execute_returns_evaluated_title_in_output(
        self, approval_handler, step_context_with_data, approval_config_with_templates
    ):
        """The wait result output contains the evaluated title."""
        result = await approval_handler.execute(step_context_with_data, approval_config_with_templates)

        # The output title should be substituted, not raw template
        assert result.output["title"] == "Approve TestCo AI for Series A?"

    @pytest.mark.asyncio
    async def test_execute_handles_missing_variables_gracefully(
        self, approval_handler, step_context, fresh_approval_store
    ):
        """Missing template variables are left as-is."""
        config = HumanApprovalConfig(
            title="Review {{input.nonexistent_field}}",
            description="Check {{steps.missing_step.output}}",
            assignees=[],
        )

        result = await approval_handler.execute(step_context, config)

        approval_id = result.output["approval_id"]
        stored = fresh_approval_store.get(approval_id)

        # Missing variables should remain as template placeholders
        assert "{{input.nonexistent_field}}" in stored.title
        assert "{{steps.missing_step.output}}" in stored.description
