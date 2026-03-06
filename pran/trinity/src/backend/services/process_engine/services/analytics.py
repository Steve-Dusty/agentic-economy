"""
Process Analytics Service

Provides analytics calculations for process executions.
Reference: BACKLOG_ADVANCED.md - E11-02

Part of the Process-Driven Platform feature.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from collections import defaultdict

from ..domain import (
    ProcessDefinition,
    ProcessExecution,
    ProcessId,
    ExecutionId,
    ExecutionStatus,
)
from ..repositories import (
    ProcessDefinitionRepository,
    ProcessExecutionRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessMetrics:
    """Metrics for a single process definition."""
    process_id: str
    process_name: str
    execution_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    running_count: int = 0
    success_rate: float = 0.0
    average_duration_seconds: Optional[float] = None
    average_cost: Optional[Decimal] = None
    total_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    min_duration_seconds: Optional[float] = None
    max_duration_seconds: Optional[float] = None
    min_cost: Optional[Decimal] = None
    max_cost: Optional[Decimal] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "process_id": self.process_id,
            "process_name": self.process_name,
            "execution_count": self.execution_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "running_count": self.running_count,
            "success_rate": round(self.success_rate, 1),
            "average_duration_seconds": round(self.average_duration_seconds, 1) if self.average_duration_seconds else None,
            "average_cost": f"${self.average_cost:.2f}" if self.average_cost else None,
            "total_cost": f"${self.total_cost:.2f}",
            "min_duration_seconds": round(self.min_duration_seconds, 1) if self.min_duration_seconds else None,
            "max_duration_seconds": round(self.max_duration_seconds, 1) if self.max_duration_seconds else None,
            "min_cost": f"${self.min_cost:.2f}" if self.min_cost else None,
            "max_cost": f"${self.max_cost:.2f}" if self.max_cost else None,
        }


@dataclass
class DailyTrend:
    """Trend data for a single day."""
    date: str
    execution_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    total_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    success_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "execution_count": self.execution_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "total_cost": float(self.total_cost),
            "success_rate": round(self.success_rate, 1),
        }


@dataclass
class TrendData:
    """Aggregated trend data over a time period."""
    days: int
    daily_trends: List[DailyTrend] = field(default_factory=list)
    total_executions: int = 0
    total_completed: int = 0
    total_failed: int = 0
    overall_success_rate: float = 0.0
    total_cost: Decimal = field(default_factory=lambda: Decimal("0"))

    def to_dict(self) -> dict:
        return {
            "days": self.days,
            "daily_trends": [t.to_dict() for t in self.daily_trends],
            "total_executions": self.total_executions,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "overall_success_rate": round(self.overall_success_rate, 1),
            "total_cost": f"${self.total_cost:.2f}",
        }


@dataclass
class StepPerformanceEntry:
    """Performance data for a single step."""
    step_id: str
    step_name: str
    process_name: str
    execution_count: int = 0
    average_duration_seconds: Optional[float] = None
    total_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    average_cost: Optional[Decimal] = None
    failure_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "process_name": self.process_name,
            "execution_count": self.execution_count,
            "average_duration_seconds": round(self.average_duration_seconds, 1) if self.average_duration_seconds else None,
            "total_cost": f"${self.total_cost:.2f}",
            "average_cost": f"${self.average_cost:.2f}" if self.average_cost else None,
            "failure_rate": round(self.failure_rate, 1),
        }


@dataclass
class StepPerformance:
    """Aggregated step performance data."""
    slowest_steps: List[StepPerformanceEntry] = field(default_factory=list)
    most_expensive_steps: List[StepPerformanceEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "slowest_steps": [s.to_dict() for s in self.slowest_steps],
            "most_expensive_steps": [s.to_dict() for s in self.most_expensive_steps],
        }


class ProcessAnalytics:
    """
    Analytics service for process execution metrics.

    Provides:
    - Per-process metrics (success rate, duration, cost)
    - Trend data over time
    - Step-level performance analysis
    """

    def __init__(
        self,
        definition_repo: ProcessDefinitionRepository,
        execution_repo: ProcessExecutionRepository,
    ):
        self._definition_repo = definition_repo
        self._execution_repo = execution_repo

    def get_process_metrics(
        self,
        process_id: ProcessId,
        days: int = 30,
    ) -> ProcessMetrics:
        """
        Get metrics for a specific process.

        Args:
            process_id: The process definition ID
            days: Number of days to include in calculations

        Returns:
            ProcessMetrics with aggregated data
        """
        definition = self._definition_repo.get_by_id(process_id)
        if not definition:
            return ProcessMetrics(
                process_id=str(process_id),
                process_name="Unknown",
            )

        # Get executions for this process
        executions = self._execution_repo.list_by_process(
            process_id,
            limit=10000,
            offset=0,
        )

        # Filter by time window
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent_executions = [
            e for e in executions
            if e.started_at and e.started_at >= cutoff
        ]

        return self._calculate_metrics(
            process_id=str(process_id),
            process_name=definition.name,
            executions=recent_executions,
        )

    def get_all_process_metrics(
        self,
        days: int = 30,
    ) -> List[ProcessMetrics]:
        """
        Get metrics for all published processes.

        Args:
            days: Number of days to include in calculations

        Returns:
            List of ProcessMetrics for all processes
        """
        from ..domain import DefinitionStatus

        definitions = self._definition_repo.list_all(
            limit=1000,
            offset=0,
            status=DefinitionStatus.PUBLISHED,
        )

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        results = []

        for definition in definitions:
            executions = self._execution_repo.list_by_process(
                definition.id,
                limit=10000,
                offset=0,
            )

            recent_executions = [
                e for e in executions
                if e.started_at and e.started_at >= cutoff
            ]

            metrics = self._calculate_metrics(
                process_id=str(definition.id),
                process_name=definition.name,
                executions=recent_executions,
            )
            results.append(metrics)

        return results

    def get_trend_data(
        self,
        days: int = 30,
        process_id: Optional[ProcessId] = None,
    ) -> TrendData:
        """
        Get execution trend data over time.

        Args:
            days: Number of days to include
            process_id: Optional filter by process

        Returns:
            TrendData with daily breakdowns
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Get executions
        if process_id:
            executions = self._execution_repo.list_by_process(
                process_id,
                limit=10000,
                offset=0,
            )
        else:
            executions = self._execution_repo.list_all(
                limit=10000,
                offset=0,
            )

        # Filter by time window
        recent_executions = [
            e for e in executions
            if e.started_at and e.started_at >= cutoff
        ]

        # Group by date
        daily_data: Dict[str, DailyTrend] = {}
        for i in range(days):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_data[date] = DailyTrend(date=date)

        for execution in recent_executions:
            if not execution.started_at:
                continue

            date_key = execution.started_at.strftime("%Y-%m-%d")
            if date_key not in daily_data:
                daily_data[date_key] = DailyTrend(date=date_key)

            trend = daily_data[date_key]
            trend.execution_count += 1

            if execution.status == ExecutionStatus.COMPLETED:
                trend.completed_count += 1
            elif execution.status == ExecutionStatus.FAILED:
                trend.failed_count += 1

            if execution.total_cost:
                trend.total_cost += execution.total_cost.amount

        # Calculate success rates and sort by date
        for trend in daily_data.values():
            finished = trend.completed_count + trend.failed_count
            if finished > 0:
                trend.success_rate = (trend.completed_count / finished) * 100

        sorted_trends = sorted(daily_data.values(), key=lambda t: t.date)

        # Calculate totals
        total_executions = sum(t.execution_count for t in sorted_trends)
        total_completed = sum(t.completed_count for t in sorted_trends)
        total_failed = sum(t.failed_count for t in sorted_trends)
        total_cost = sum(t.total_cost for t in sorted_trends)

        overall_success_rate = 0.0
        if total_completed + total_failed > 0:
            overall_success_rate = (total_completed / (total_completed + total_failed)) * 100

        return TrendData(
            days=days,
            daily_trends=sorted_trends,
            total_executions=total_executions,
            total_completed=total_completed,
            total_failed=total_failed,
            overall_success_rate=overall_success_rate,
            total_cost=total_cost,
        )

    def get_step_performance(
        self,
        days: int = 30,
        limit: int = 10,
    ) -> StepPerformance:
        """
        Get step-level performance metrics.

        Identifies slowest and most expensive steps.

        Args:
            days: Number of days to include
            limit: Maximum number of steps to return per category

        Returns:
            StepPerformance with slowest and most expensive steps
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Get all recent executions
        executions = self._execution_repo.list_all(
            limit=10000,
            offset=0,
        )

        recent_executions = [
            e for e in executions
            if e.started_at and e.started_at >= cutoff
        ]

        # Aggregate step data
        step_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "durations": [],
            "costs": [],
            "failures": 0,
            "total": 0,
            "process_name": "",
            "step_name": "",
        })

        for execution in recent_executions:
            for step_id, step_exec in execution.step_executions.items():
                key = f"{execution.process_name}:{step_id}"
                data = step_data[key]
                data["process_name"] = execution.process_name
                data["step_name"] = step_id  # We don't have step name easily, use ID
                data["total"] += 1

                # Duration
                if step_exec.started_at and step_exec.completed_at:
                    duration = (step_exec.completed_at - step_exec.started_at).total_seconds()
                    data["durations"].append(duration)

                # Cost
                if step_exec.cost and step_exec.cost.amount > 0:
                    data["costs"].append(step_exec.cost.amount)

                # Failures
                if step_exec.status.value == "failed":
                    data["failures"] += 1

        # Build entries
        entries: List[StepPerformanceEntry] = []
        for key, data in step_data.items():
            entry = StepPerformanceEntry(
                step_id=key.split(":")[-1],
                step_name=data["step_name"],
                process_name=data["process_name"],
                execution_count=data["total"],
            )

            if data["durations"]:
                entry.average_duration_seconds = sum(data["durations"]) / len(data["durations"])

            if data["costs"]:
                entry.total_cost = sum(data["costs"])
                entry.average_cost = entry.total_cost / len(data["costs"])

            if data["total"] > 0:
                entry.failure_rate = (data["failures"] / data["total"]) * 100

            entries.append(entry)

        # Sort for slowest (by average duration)
        slowest = sorted(
            [e for e in entries if e.average_duration_seconds],
            key=lambda e: e.average_duration_seconds or 0,
            reverse=True,
        )[:limit]

        # Sort for most expensive (by total cost)
        most_expensive = sorted(
            [e for e in entries if e.total_cost > 0],
            key=lambda e: e.total_cost,
            reverse=True,
        )[:limit]

        return StepPerformance(
            slowest_steps=slowest,
            most_expensive_steps=most_expensive,
        )

    def _calculate_metrics(
        self,
        process_id: str,
        process_name: str,
        executions: List[ProcessExecution],
    ) -> ProcessMetrics:
        """Calculate metrics from a list of executions."""
        metrics = ProcessMetrics(
            process_id=process_id,
            process_name=process_name,
        )

        if not executions:
            return metrics

        durations = []
        costs = []

        for execution in executions:
            metrics.execution_count += 1

            if execution.status == ExecutionStatus.COMPLETED:
                metrics.completed_count += 1
            elif execution.status == ExecutionStatus.FAILED:
                metrics.failed_count += 1
            elif execution.status == ExecutionStatus.RUNNING:
                metrics.running_count += 1

            # Duration
            if execution.duration:
                durations.append(execution.duration.seconds)

            # Cost
            if execution.total_cost and execution.total_cost.amount > 0:
                costs.append(execution.total_cost.amount)
                metrics.total_cost += execution.total_cost.amount

        # Calculate rates and averages
        finished = metrics.completed_count + metrics.failed_count
        if finished > 0:
            metrics.success_rate = (metrics.completed_count / finished) * 100

        if durations:
            metrics.average_duration_seconds = sum(durations) / len(durations)
            metrics.min_duration_seconds = min(durations)
            metrics.max_duration_seconds = max(durations)

        if costs:
            metrics.average_cost = metrics.total_cost / len(costs)
            metrics.min_cost = min(costs)
            metrics.max_cost = max(costs)

        return metrics
