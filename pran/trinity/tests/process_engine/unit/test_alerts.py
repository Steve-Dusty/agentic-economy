"""
Unit tests for Cost Alert Service

Tests the cost threshold management and alert generation.
Reference: BACKLOG_ADVANCED.md - E11-03
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

from services.process_engine.services.alerts import (
    CostAlertService,
    CostThreshold,
    CostAlert,
    ThresholdType,
    AlertSeverity,
    AlertStatus,
)


class TestThresholdType:
    """Tests for ThresholdType enum."""

    def test_threshold_types_exist(self):
        """Test that all expected threshold types exist."""
        assert ThresholdType.PER_EXECUTION.value == "per_execution"
        assert ThresholdType.DAILY.value == "daily"
        assert ThresholdType.WEEKLY.value == "weekly"


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_severity_levels_exist(self):
        """Test that all expected severity levels exist."""
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertStatus:
    """Tests for AlertStatus enum."""

    def test_status_values_exist(self):
        """Test that all expected status values exist."""
        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.DISMISSED.value == "dismissed"


class TestCostThreshold:
    """Tests for CostThreshold dataclass."""

    def test_create_threshold(self):
        """Test creating a cost threshold."""
        threshold = CostThreshold(
            id="test-id",
            process_id="process-123",
            threshold_type=ThresholdType.PER_EXECUTION,
            threshold_amount=Decimal("5.00"),
            currency="USD",
            enabled=True,
        )

        assert threshold.id == "test-id"
        assert threshold.process_id == "process-123"
        assert threshold.threshold_type == ThresholdType.PER_EXECUTION
        assert threshold.threshold_amount == Decimal("5.00")
        assert threshold.enabled is True

    def test_threshold_to_dict(self):
        """Test conversion to dictionary."""
        threshold = CostThreshold(
            id="test-id",
            process_id="process-123",
            threshold_type=ThresholdType.DAILY,
            threshold_amount=Decimal("100.00"),
        )

        result = threshold.to_dict()

        assert result["id"] == "test-id"
        assert result["process_id"] == "process-123"
        assert result["threshold_type"] == "daily"
        assert result["threshold_amount"] == 100.00

    def test_threshold_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "id": "test-id",
            "process_id": "process-123",
            "threshold_type": "weekly",
            "threshold_amount": 500.0,
            "enabled": True,
            "created_at": "2026-01-15T00:00:00+00:00",
            "updated_at": "2026-01-15T00:00:00+00:00",
        }

        threshold = CostThreshold.from_dict(data)

        assert threshold.id == "test-id"
        assert threshold.threshold_type == ThresholdType.WEEKLY
        assert threshold.threshold_amount == Decimal("500.0")


class TestCostAlert:
    """Tests for CostAlert dataclass."""

    def test_create_alert(self):
        """Test creating a cost alert."""
        alert = CostAlert(
            id="alert-1",
            process_id="process-123",
            process_name="test-process",
            execution_id="exec-456",
            threshold_type=ThresholdType.PER_EXECUTION,
            threshold_amount=Decimal("5.00"),
            actual_amount=Decimal("7.50"),
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            message="Execution cost exceeded threshold",
        )

        assert alert.id == "alert-1"
        assert alert.process_name == "test-process"
        assert alert.actual_amount == Decimal("7.50")
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.ACTIVE

    def test_alert_to_dict(self):
        """Test conversion to dictionary."""
        alert = CostAlert(
            id="alert-1",
            process_id="process-123",
            process_name="test-process",
            execution_id=None,
            threshold_type=ThresholdType.DAILY,
            threshold_amount=Decimal("100.00"),
            actual_amount=Decimal("150.00"),
            severity=AlertSeverity.CRITICAL,
            message="Daily limit exceeded",
        )

        result = alert.to_dict()

        assert result["id"] == "alert-1"
        assert result["threshold_type"] == "daily"
        assert result["severity"] == "critical"
        assert result["actual_amount"] == 150.00


class TestCostAlertService:
    """Tests for CostAlertService."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        # Clean up
        os.unlink(f.name)

    @pytest.fixture
    def alert_service(self, temp_db_path):
        """Create an alert service with a temporary database."""
        return CostAlertService(db_path=temp_db_path)

    def test_service_initialization(self, alert_service):
        """Test that service initializes correctly."""
        assert alert_service is not None

    def test_set_and_get_threshold(self, alert_service):
        """Test setting and retrieving a threshold."""
        process_id = "process-123"

        # Set a threshold
        threshold = alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
            enabled=True,
        )

        assert threshold.process_id == process_id
        assert threshold.threshold_amount == Decimal("5.00")

        # Retrieve thresholds
        thresholds = alert_service.get_thresholds(process_id)
        assert len(thresholds) == 1
        assert thresholds[0].threshold_type == ThresholdType.PER_EXECUTION

    def test_update_existing_threshold(self, alert_service):
        """Test updating an existing threshold."""
        process_id = "process-123"

        # Set initial threshold
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
        )

        # Update threshold
        updated = alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("10.00"),
        )

        assert updated.threshold_amount == Decimal("10.00")

        # Verify only one threshold exists
        thresholds = alert_service.get_thresholds(process_id)
        assert len(thresholds) == 1

    def test_delete_threshold(self, alert_service):
        """Test deleting a threshold."""
        process_id = "process-123"

        # Set a threshold
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.DAILY,
            amount=Decimal("100.00"),
        )

        # Delete it
        result = alert_service.delete_threshold(process_id, ThresholdType.DAILY)
        assert result is True

        # Verify it's gone
        thresholds = alert_service.get_thresholds(process_id)
        assert len(thresholds) == 0

    def test_delete_nonexistent_threshold(self, alert_service):
        """Test deleting a threshold that doesn't exist."""
        result = alert_service.delete_threshold("fake-process", ThresholdType.DAILY)
        assert result is False

    def test_check_execution_cost_no_threshold(self, alert_service):
        """Test checking execution cost when no threshold is set."""
        alert = alert_service.check_execution_cost(
            process_id="process-123",
            process_name="test-process",
            execution_id="exec-456",
            cost=Decimal("10.00"),
        )

        assert alert is None

    def test_check_execution_cost_below_threshold(self, alert_service):
        """Test checking execution cost that is below threshold."""
        process_id = "process-123"

        # Set threshold
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("10.00"),
        )

        # Check cost that is below threshold
        alert = alert_service.check_execution_cost(
            process_id=process_id,
            process_name="test-process",
            execution_id="exec-456",
            cost=Decimal("5.00"),
        )

        assert alert is None

    def test_check_execution_cost_above_threshold(self, alert_service):
        """Test checking execution cost that exceeds threshold."""
        process_id = "process-123"

        # Set threshold
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
        )

        # Check cost that exceeds threshold
        alert = alert_service.check_execution_cost(
            process_id=process_id,
            process_name="test-process",
            execution_id="exec-456",
            cost=Decimal("7.50"),
        )

        assert alert is not None
        assert alert.process_id == process_id
        assert alert.actual_amount == Decimal("7.50")
        assert alert.threshold_amount == Decimal("5.00")
        assert alert.severity == AlertSeverity.WARNING

    def test_check_execution_cost_critical_severity(self, alert_service):
        """Test that severe cost overages get critical severity."""
        process_id = "process-123"

        # Set threshold
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
        )

        # Check cost that is more than 2x threshold
        alert = alert_service.check_execution_cost(
            process_id=process_id,
            process_name="test-process",
            execution_id="exec-456",
            cost=Decimal("15.00"),  # 3x threshold
        )

        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL

    def test_disabled_threshold_ignored(self, alert_service):
        """Test that disabled thresholds don't trigger alerts."""
        process_id = "process-123"

        # Set disabled threshold
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
            enabled=False,
        )

        # Check cost that would exceed threshold
        alert = alert_service.check_execution_cost(
            process_id=process_id,
            process_name="test-process",
            execution_id="exec-456",
            cost=Decimal("10.00"),
        )

        assert alert is None

    def test_get_alerts(self, alert_service):
        """Test retrieving alerts."""
        process_id = "process-123"

        # Set threshold and trigger alert
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
        )

        alert_service.check_execution_cost(
            process_id=process_id,
            process_name="test-process",
            execution_id="exec-456",
            cost=Decimal("10.00"),
        )

        # Get alerts
        alerts = alert_service.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].status == AlertStatus.ACTIVE

    def test_get_active_alerts_count(self, alert_service):
        """Test getting count of active alerts."""
        process_id = "process-123"

        # Set threshold
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
        )

        # Trigger multiple alerts
        for i in range(3):
            alert_service.check_execution_cost(
                process_id=process_id,
                process_name="test-process",
                execution_id=f"exec-{i}",
                cost=Decimal("10.00"),
            )

        count = alert_service.get_active_alerts_count()
        assert count == 3

    def test_dismiss_alert(self, alert_service):
        """Test dismissing an alert."""
        process_id = "process-123"

        # Set threshold and trigger alert
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
        )

        alert = alert_service.check_execution_cost(
            process_id=process_id,
            process_name="test-process",
            execution_id="exec-456",
            cost=Decimal("10.00"),
        )

        # Dismiss it
        result = alert_service.dismiss_alert(alert.id, dismissed_by="test-user")
        assert result is True

        # Verify it's dismissed
        updated_alert = alert_service.get_alert(alert.id)
        assert updated_alert.status == AlertStatus.DISMISSED
        assert updated_alert.dismissed_by == "test-user"

    def test_get_alert_by_id(self, alert_service):
        """Test getting a single alert by ID."""
        process_id = "process-123"

        # Set threshold and trigger alert
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
        )

        created_alert = alert_service.check_execution_cost(
            process_id=process_id,
            process_name="test-process",
            execution_id="exec-456",
            cost=Decimal("10.00"),
        )

        # Get by ID
        fetched_alert = alert_service.get_alert(created_alert.id)
        assert fetched_alert is not None
        assert fetched_alert.id == created_alert.id

    def test_get_nonexistent_alert(self, alert_service):
        """Test getting an alert that doesn't exist."""
        alert = alert_service.get_alert("nonexistent-id")
        assert alert is None


# =============================================================================
# ExecutionEngine Integration Tests (E11-03)
# =============================================================================


class TestCostAlertEngineIntegration:
    """Tests for cost alert integration with ExecutionEngine."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def temp_exec_db_path(self):
        """Create a temporary database path for executions."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def alert_service(self, temp_db_path):
        """Create an alert service with a temporary database."""
        return CostAlertService(db_path=temp_db_path)

    def test_execution_engine_accepts_cost_alert_service(self, alert_service, temp_exec_db_path):
        """Test that ExecutionEngine can be initialized with CostAlertService."""
        from services.process_engine.repositories import SqliteProcessExecutionRepository
        from services.process_engine.engine import ExecutionEngine

        repo = SqliteProcessExecutionRepository(temp_exec_db_path)
        engine = ExecutionEngine(
            execution_repo=repo,
            cost_alert_service=alert_service,
        )

        assert engine.cost_alert_service is alert_service

    def test_execution_engine_without_cost_alert_service(self, temp_exec_db_path):
        """Test that ExecutionEngine works without CostAlertService."""
        from services.process_engine.repositories import SqliteProcessExecutionRepository
        from services.process_engine.engine import ExecutionEngine

        repo = SqliteProcessExecutionRepository(temp_exec_db_path)
        engine = ExecutionEngine(execution_repo=repo)

        assert engine.cost_alert_service is None

    @pytest.mark.asyncio
    async def test_check_cost_thresholds_no_alert_service(self, temp_exec_db_path):
        """Test that _check_cost_thresholds handles missing service gracefully."""
        from services.process_engine.repositories import SqliteProcessExecutionRepository
        from services.process_engine.engine import ExecutionEngine
        from services.process_engine.domain import ProcessExecution, ProcessId, ExecutionId, Money, Version

        repo = SqliteProcessExecutionRepository(temp_exec_db_path)
        engine = ExecutionEngine(execution_repo=repo)

        # Create a mock execution with cost
        import uuid
        execution = ProcessExecution(
            id=ExecutionId(str(uuid.uuid4())),
            process_id=ProcessId(str(uuid.uuid4())),
            process_version=Version.initial(),
            process_name="test-process",
            input_data={},
            triggered_by="test",
            total_cost=Money.from_float(10.0),
        )

        # Should not raise
        await engine._check_cost_thresholds(execution)

    @pytest.mark.asyncio
    async def test_check_cost_thresholds_no_cost(self, alert_service, temp_exec_db_path):
        """Test that _check_cost_thresholds handles zero cost gracefully."""
        from services.process_engine.repositories import SqliteProcessExecutionRepository
        from services.process_engine.engine import ExecutionEngine
        from services.process_engine.domain import ProcessExecution, ProcessId, ExecutionId, Version

        repo = SqliteProcessExecutionRepository(temp_exec_db_path)
        engine = ExecutionEngine(
            execution_repo=repo,
            cost_alert_service=alert_service,
        )

        # Create a mock execution without cost
        import uuid
        execution = ProcessExecution(
            id=ExecutionId(str(uuid.uuid4())),
            process_id=ProcessId(str(uuid.uuid4())),
            process_version=Version.initial(),
            process_name="test-process",
            input_data={},
            triggered_by="test",
        )

        # Should not raise or create alert
        await engine._check_cost_thresholds(execution)

        # No alerts should exist
        alerts = alert_service.get_alerts()
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_check_cost_thresholds_triggers_alert(self, alert_service, temp_exec_db_path):
        """Test that _check_cost_thresholds triggers alert when threshold exceeded."""
        from services.process_engine.repositories import SqliteProcessExecutionRepository
        from services.process_engine.engine import ExecutionEngine
        from services.process_engine.domain import ProcessExecution, ProcessId, ExecutionId, Money, Version

        repo = SqliteProcessExecutionRepository(temp_exec_db_path)
        engine = ExecutionEngine(
            execution_repo=repo,
            cost_alert_service=alert_service,
        )

        import uuid
        process_id = str(uuid.uuid4())

        # Set threshold
        alert_service.set_threshold(
            process_id=process_id,
            threshold_type=ThresholdType.PER_EXECUTION,
            amount=Decimal("5.00"),
        )

        # Create execution with cost exceeding threshold
        execution = ProcessExecution(
            id=ExecutionId(str(uuid.uuid4())),
            process_id=ProcessId(process_id),
            process_version=Version.initial(),
            process_name="test-process",
            input_data={},
            triggered_by="test",
            total_cost=Money.from_float(10.0),
        )

        # Check thresholds
        await engine._check_cost_thresholds(execution)

        # Alert should be created
        alerts = alert_service.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].process_name == "test-process"
        assert alerts[0].actual_amount == Decimal("10.0")
