"""
Unit tests for Process Analytics Service

Tests the analytics calculations for process executions.
Reference: BACKLOG_ADVANCED.md - E11-02
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from services.process_engine.services.analytics import (
    ProcessAnalytics,
    ProcessMetrics,
    TrendData,
    DailyTrend,
    StepPerformance,
    StepPerformanceEntry,
)
from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    ProcessId,
    ExecutionId,
    ExecutionStatus,
    StepExecution,
    StepStatus,
    Money,
    Duration,
)


class TestProcessMetrics:
    """Tests for ProcessMetrics dataclass."""

    def test_create_empty_metrics(self):
        """Test creating metrics with default values."""
        metrics = ProcessMetrics(
            process_id="test-id",
            process_name="test-process",
        )

        assert metrics.process_id == "test-id"
        assert metrics.process_name == "test-process"
        assert metrics.execution_count == 0
        assert metrics.completed_count == 0
        assert metrics.failed_count == 0
        assert metrics.success_rate == 0.0
        assert metrics.total_cost == Decimal("0")

    def test_metrics_to_dict(self):
        """Test conversion to dictionary."""
        metrics = ProcessMetrics(
            process_id="test-id",
            process_name="test-process",
            execution_count=10,
            completed_count=8,
            failed_count=2,
            success_rate=80.0,
            average_duration_seconds=45.5,
            average_cost=Decimal("1.50"),
            total_cost=Decimal("15.00"),
        )

        result = metrics.to_dict()

        assert result["process_id"] == "test-id"
        assert result["process_name"] == "test-process"
        assert result["execution_count"] == 10
        assert result["success_rate"] == 80.0
        assert result["average_duration_seconds"] == 45.5
        assert result["average_cost"] == "$1.50"
        assert result["total_cost"] == "$15.00"


class TestDailyTrend:
    """Tests for DailyTrend dataclass."""

    def test_create_daily_trend(self):
        """Test creating a daily trend entry."""
        trend = DailyTrend(
            date="2026-01-15",
            execution_count=5,
            completed_count=4,
            failed_count=1,
            total_cost=Decimal("10.50"),
            success_rate=80.0,
        )

        assert trend.date == "2026-01-15"
        assert trend.execution_count == 5
        assert trend.success_rate == 80.0

    def test_daily_trend_to_dict(self):
        """Test conversion to dictionary."""
        trend = DailyTrend(
            date="2026-01-15",
            execution_count=5,
            completed_count=4,
            failed_count=1,
            total_cost=Decimal("10.50"),
            success_rate=80.0,
        )

        result = trend.to_dict()

        assert result["date"] == "2026-01-15"
        assert result["execution_count"] == 5
        assert result["total_cost"] == 10.50
        assert result["success_rate"] == 80.0


class TestTrendData:
    """Tests for TrendData dataclass."""

    def test_create_trend_data(self):
        """Test creating trend data."""
        trends = TrendData(
            days=7,
            total_executions=25,
            total_completed=20,
            total_failed=5,
            overall_success_rate=80.0,
            total_cost=Decimal("100.00"),
        )

        assert trends.days == 7
        assert trends.total_executions == 25
        assert trends.overall_success_rate == 80.0

    def test_trend_data_to_dict(self):
        """Test conversion to dictionary."""
        trends = TrendData(
            days=7,
            daily_trends=[
                DailyTrend(date="2026-01-15", execution_count=5),
            ],
            total_executions=5,
            total_cost=Decimal("50.00"),
        )

        result = trends.to_dict()

        assert result["days"] == 7
        assert len(result["daily_trends"]) == 1
        assert result["total_cost"] == "$50.00"


class TestStepPerformanceEntry:
    """Tests for StepPerformanceEntry dataclass."""

    def test_create_step_performance_entry(self):
        """Test creating a step performance entry."""
        entry = StepPerformanceEntry(
            step_id="analyze-data",
            step_name="Analyze Data",
            process_name="data-pipeline",
            execution_count=100,
            average_duration_seconds=30.5,
            total_cost=Decimal("25.00"),
            average_cost=Decimal("0.25"),
            failure_rate=5.0,
        )

        assert entry.step_id == "analyze-data"
        assert entry.average_duration_seconds == 30.5
        assert entry.failure_rate == 5.0

    def test_step_performance_entry_to_dict(self):
        """Test conversion to dictionary."""
        entry = StepPerformanceEntry(
            step_id="analyze-data",
            step_name="Analyze Data",
            process_name="data-pipeline",
            execution_count=100,
            average_duration_seconds=30.5,
            total_cost=Decimal("25.00"),
        )

        result = entry.to_dict()

        assert result["step_id"] == "analyze-data"
        assert result["average_duration_seconds"] == 30.5
        assert result["total_cost"] == "$25.00"


class TestProcessAnalytics:
    """Tests for ProcessAnalytics service."""

    @pytest.fixture
    def mock_definition_repo(self):
        """Create a mock definition repository."""
        return Mock()

    @pytest.fixture
    def mock_execution_repo(self):
        """Create a mock execution repository."""
        return Mock()

    @pytest.fixture
    def analytics_service(self, mock_definition_repo, mock_execution_repo):
        """Create an analytics service with mocked repositories."""
        return ProcessAnalytics(mock_definition_repo, mock_execution_repo)

    def test_calculate_metrics_empty_executions(self, analytics_service):
        """Test metrics calculation with no executions."""
        metrics = analytics_service._calculate_metrics(
            process_id="test-id",
            process_name="test-process",
            executions=[],
        )

        assert metrics.execution_count == 0
        assert metrics.success_rate == 0.0
        assert metrics.total_cost == Decimal("0")

    def test_calculate_metrics_with_executions(self, analytics_service):
        """Test metrics calculation with sample executions."""
        # Create mock executions
        executions = []
        for i in range(10):
            exec_mock = Mock()
            exec_mock.status = ExecutionStatus.COMPLETED if i < 8 else ExecutionStatus.FAILED
            exec_mock.duration = Duration.from_seconds(60) if i < 8 else None
            exec_mock.total_cost = Money(Decimal("1.00"), "USD") if i < 8 else None
            executions.append(exec_mock)

        metrics = analytics_service._calculate_metrics(
            process_id="test-id",
            process_name="test-process",
            executions=executions,
        )

        assert metrics.execution_count == 10
        assert metrics.completed_count == 8
        assert metrics.failed_count == 2
        assert metrics.success_rate == 80.0
        assert metrics.total_cost == Decimal("8.00")

    def test_get_process_metrics_not_found(
        self, analytics_service, mock_definition_repo, mock_execution_repo
    ):
        """Test getting metrics for a non-existent process."""
        mock_definition_repo.get_by_id.return_value = None

        metrics = analytics_service.get_process_metrics(ProcessId.generate())

        assert metrics.process_name == "Unknown"
        assert metrics.execution_count == 0

    def test_get_trend_data_structure(
        self, analytics_service, mock_execution_repo
    ):
        """Test that trend data has correct structure."""
        mock_execution_repo.list_all.return_value = []

        trends = analytics_service.get_trend_data(days=7)

        assert trends.days == 7
        assert isinstance(trends.daily_trends, list)
        assert trends.total_executions == 0

    def test_get_step_performance_structure(
        self, analytics_service, mock_execution_repo
    ):
        """Test that step performance has correct structure."""
        mock_execution_repo.list_all.return_value = []

        performance = analytics_service.get_step_performance(days=30, limit=10)

        assert isinstance(performance.slowest_steps, list)
        assert isinstance(performance.most_expensive_steps, list)


class TestSuccessRateCalculation:
    """Tests specifically for success rate calculation."""

    def test_success_rate_all_completed(self):
        """Test success rate when all executions completed."""
        metrics = ProcessMetrics(
            process_id="test",
            process_name="test",
            completed_count=10,
            failed_count=0,
            success_rate=100.0,
        )
        assert metrics.success_rate == 100.0

    def test_success_rate_all_failed(self):
        """Test success rate when all executions failed."""
        metrics = ProcessMetrics(
            process_id="test",
            process_name="test",
            completed_count=0,
            failed_count=10,
            success_rate=0.0,
        )
        assert metrics.success_rate == 0.0

    def test_success_rate_mixed(self):
        """Test success rate with mixed results."""
        metrics = ProcessMetrics(
            process_id="test",
            process_name="test",
            completed_count=7,
            failed_count=3,
            success_rate=70.0,
        )
        assert metrics.success_rate == 70.0
