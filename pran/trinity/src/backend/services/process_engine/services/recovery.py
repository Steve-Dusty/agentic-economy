"""
Execution Recovery Service

Recovers in-progress executions after platform restart.

Reference: IT5 Section 2.3 (Recovery on Backend Restart)
Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-10
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from ..domain import (
    ProcessExecution,
    ExecutionId,
    ExecutionStatus,
    StepStatus,
)
from ..repositories import ProcessExecutionRepository, ProcessDefinitionRepository
from ..events import EventBus

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class RecoveryAction(Enum):
    """
    Actions the recovery service can take for an execution.
    """
    RESUME = "resume"           # Continue from next pending step
    RETRY_STEP = "retry_step"   # Re-execute the interrupted step
    MARK_FAILED = "mark_failed" # Fail due to age timeout
    SKIP = "skip"               # No action needed (already terminal)


@dataclass
class RecoveryResult:
    """
    Result of recovering a single execution.
    """
    execution_id: ExecutionId
    action: RecoveryAction
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "execution_id": str(self.execution_id),
            "action": self.action.value,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class RecoveryReport:
    """
    Summary of recovery operations performed on startup.
    """
    started_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None

    # Counts by action
    resumed: list[ExecutionId] = field(default_factory=list)
    retried: list[ExecutionId] = field(default_factory=list)
    failed: list[ExecutionId] = field(default_factory=list)
    skipped: list[ExecutionId] = field(default_factory=list)

    # Errors during recovery
    errors: list[tuple[ExecutionId, str]] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return len(self.resumed) + len(self.retried) + len(self.failed) + len(self.skipped)

    @property
    def total_errors(self) -> int:
        return len(self.errors)

    @property
    def duration_ms(self) -> int:
        if self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return 0

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "counts": {
                "resumed": len(self.resumed),
                "retried": len(self.retried),
                "failed": len(self.failed),
                "skipped": len(self.skipped),
                "errors": len(self.errors),
            },
            "resumed_ids": [str(e) for e in self.resumed],
            "retried_ids": [str(e) for e in self.retried],
            "failed_ids": [str(e) for e in self.failed],
            "skipped_ids": [str(e) for e in self.skipped],
            "errors": [(str(e), msg) for e, msg in self.errors],
        }


@dataclass
class RecoveryConfig:
    """
    Configuration for the recovery service.
    """
    # Max age before marking execution as failed (hours)
    max_age_hours: int = 24

    # Whether to actually resume/retry executions or just report
    dry_run: bool = False


class ExecutionRecoveryService:
    """
    Recovers in-progress executions after platform restart.

    Called during backend initialization to detect and recover
    executions that were interrupted by restart.

    Recovery strategies:
    - RESUME: Execution was between steps, continue from next pending
    - RETRY_STEP: Step was mid-execution, re-execute it
    - MARK_FAILED: Execution too old (> 24h), fail it
    - SKIP: Execution already in terminal state

    Example usage:
    ```python
    recovery_service = ExecutionRecoveryService(
        execution_repo=execution_repo,
        definition_repo=definition_repo,
        execution_engine=engine,
        event_bus=event_bus,
    )

    # Call on startup
    report = await recovery_service.recover_on_startup()
    logger.info(f"Recovery: {report.total_processed} processed, {report.total_errors} errors")
    ```
    """

    def __init__(
        self,
        execution_repo: ProcessExecutionRepository,
        definition_repo: ProcessDefinitionRepository,
        execution_engine,  # Type hint omitted to avoid circular import
        event_bus: Optional[EventBus] = None,
        config: Optional[RecoveryConfig] = None,
    ):
        """
        Initialize the recovery service.

        Args:
            execution_repo: Repository for execution state
            definition_repo: Repository for process definitions
            execution_engine: Engine to resume/retry executions
            event_bus: Optional event bus for publishing recovery events
            config: Optional recovery configuration
        """
        self.execution_repo = execution_repo
        self.definition_repo = definition_repo
        self.execution_engine = execution_engine
        self.event_bus = event_bus
        self.config = config or RecoveryConfig()

        # Store last recovery report for health checks
        self._last_report: Optional[RecoveryReport] = None

    @property
    def last_recovery_report(self) -> Optional[RecoveryReport]:
        """Get the most recent recovery report."""
        return self._last_report

    async def recover_on_startup(self) -> RecoveryReport:
        """
        Scan for and recover interrupted executions.

        Called during backend initialization.

        Returns:
            RecoveryReport with details of all recovery operations
        """
        report = RecoveryReport()

        logger.info("Starting execution recovery scan...")

        # Publish recovery started event
        await self._publish_recovery_started()

        # Find all active executions
        try:
            active_executions = self.execution_repo.list_active()
        except Exception as e:
            logger.error(f"Failed to list active executions: {e}")
            report.errors.append((ExecutionId.generate(), f"Failed to list active executions: {e}"))
            report.completed_at = _utcnow()
            self._last_report = report
            await self._publish_recovery_completed(report)
            return report

        logger.info(f"Found {len(active_executions)} active executions to check")

        for execution in active_executions:
            try:
                result = await self._recover_execution(execution)

                # Record result
                if result.action == RecoveryAction.RESUME:
                    report.resumed.append(execution.id)
                elif result.action == RecoveryAction.RETRY_STEP:
                    report.retried.append(execution.id)
                elif result.action == RecoveryAction.MARK_FAILED:
                    report.failed.append(execution.id)
                elif result.action == RecoveryAction.SKIP:
                    report.skipped.append(execution.id)

                if not result.success:
                    report.errors.append((execution.id, result.error or "Unknown error"))

            except Exception as e:
                logger.exception(f"Recovery failed for execution {execution.id}")
                report.errors.append((execution.id, str(e)))

        report.completed_at = _utcnow()
        self._last_report = report

        # Log summary
        logger.info(
            f"Recovery complete: "
            f"resumed={len(report.resumed)}, "
            f"retried={len(report.retried)}, "
            f"failed={len(report.failed)}, "
            f"skipped={len(report.skipped)}, "
            f"errors={len(report.errors)}, "
            f"duration={report.duration_ms}ms"
        )

        # Publish recovery completed event
        await self._publish_recovery_completed(report)

        return report

    async def _recover_execution(
        self,
        execution: ProcessExecution,
    ) -> RecoveryResult:
        """
        Attempt to recover a single execution.

        Args:
            execution: The execution to recover

        Returns:
            RecoveryResult with action taken and success status
        """
        action = self._determine_recovery_action(execution)

        logger.info(
            f"Recovering execution {execution.id} "
            f"(process={execution.process_name}, status={execution.status.value}, action={action.value})"
        )

        if action == RecoveryAction.SKIP:
            return RecoveryResult(
                execution_id=execution.id,
                action=action,
                success=True,
            )

        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would {action.value} execution {execution.id}")
            return RecoveryResult(
                execution_id=execution.id,
                action=action,
                success=True,
            )

        # Get process definition
        definition = self.definition_repo.get_by_id(execution.process_id)
        if not definition:
            error_msg = f"Process definition not found: {execution.process_id}"
            logger.error(error_msg)
            return RecoveryResult(
                execution_id=execution.id,
                action=action,
                success=False,
                error=error_msg,
            )

        try:
            if action == RecoveryAction.MARK_FAILED:
                # Too old - fail the execution
                execution.fail("Recovery timeout exceeded (execution older than 24 hours)")
                self.execution_repo.save(execution)

                # Publish event
                await self._publish_execution_recovered(execution, action)

                return RecoveryResult(
                    execution_id=execution.id,
                    action=action,
                    success=True,
                )

            elif action == RecoveryAction.RETRY_STEP:
                # Step was interrupted - reset it and resume
                running_step = self._get_running_step(execution)
                if running_step:
                    # Reset the running step to pending
                    step_exec = execution.step_executions.get(running_step)
                    if step_exec:
                        step_exec.status = StepStatus.PENDING
                        step_exec.started_at = None
                        logger.info(f"Reset step '{running_step}' to PENDING for retry")

                self.execution_repo.save(execution)

                # Publish event before resuming
                await self._publish_execution_recovered(execution, action)

                # Resume execution (engine will re-execute the reset step)
                # Note: We don't await the full execution - just kick it off
                # The execution engine handles its own lifecycle
                import asyncio
                asyncio.create_task(
                    self.execution_engine.resume(execution, definition)
                )

                return RecoveryResult(
                    execution_id=execution.id,
                    action=action,
                    success=True,
                )

            elif action == RecoveryAction.RESUME:
                # Between steps - just resume
                # Publish event before resuming
                await self._publish_execution_recovered(execution, action)

                # Resume execution
                import asyncio
                asyncio.create_task(
                    self.execution_engine.resume(execution, definition)
                )

                return RecoveryResult(
                    execution_id=execution.id,
                    action=action,
                    success=True,
                )

            else:
                return RecoveryResult(
                    execution_id=execution.id,
                    action=action,
                    success=False,
                    error=f"Unknown recovery action: {action}",
                )

        except Exception as e:
            logger.exception(f"Failed to execute recovery action {action.value}")
            return RecoveryResult(
                execution_id=execution.id,
                action=action,
                success=False,
                error=str(e),
            )

    def _determine_recovery_action(
        self,
        execution: ProcessExecution,
    ) -> RecoveryAction:
        """
        Determine the appropriate recovery action for an execution.

        Rules:
        1. If execution is in terminal state → SKIP
        2. If execution is too old (> 24h) → MARK_FAILED
        3. If a step is currently RUNNING → RETRY_STEP
        4. Otherwise → RESUME
        """
        # Check if already in terminal state
        if execution.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        ):
            return RecoveryAction.SKIP

        # Check age
        age = self._get_execution_age(execution)
        max_age = timedelta(hours=self.config.max_age_hours)

        if age > max_age:
            logger.info(
                f"Execution {execution.id} is {age.total_seconds() / 3600:.1f}h old, "
                f"marking as failed (max={self.config.max_age_hours}h)"
            )
            return RecoveryAction.MARK_FAILED

        # Check if any step was in RUNNING state (interrupted)
        running_step = self._get_running_step(execution)
        if running_step:
            logger.info(f"Execution {execution.id} has running step '{running_step}', will retry")
            return RecoveryAction.RETRY_STEP

        # Otherwise, resume from where we left off
        return RecoveryAction.RESUME

    def _get_execution_age(self, execution: ProcessExecution) -> timedelta:
        """
        Get the age of an execution based on last activity.
        """
        # Use the most recent timestamp we have
        last_activity = execution.started_at

        # Check step timestamps
        for step_exec in execution.step_executions.values():
            if step_exec.started_at and (not last_activity or step_exec.started_at > last_activity):
                last_activity = step_exec.started_at
            if step_exec.completed_at and (not last_activity or step_exec.completed_at > last_activity):
                last_activity = step_exec.completed_at

        if last_activity:
            return _utcnow() - last_activity

        # Default to a large age if no timestamp found
        return timedelta(hours=self.config.max_age_hours + 1)

    def _get_running_step(self, execution: ProcessExecution) -> Optional[str]:
        """
        Get the ID of any step that was in RUNNING state.
        """
        for step_id, step_exec in execution.step_executions.items():
            if step_exec.status == StepStatus.RUNNING:
                return step_id
        return None

    async def _publish_recovery_started(self) -> None:
        """Publish event that recovery scan has started."""
        if self.event_bus:
            from ..domain.events import ExecutionRecoveryStarted
            await self.event_bus.publish(ExecutionRecoveryStarted())

    async def _publish_execution_recovered(
        self,
        execution: ProcessExecution,
        action: RecoveryAction,
    ) -> None:
        """Publish event that an execution was recovered."""
        if self.event_bus:
            from ..domain.events import ExecutionRecovered
            await self.event_bus.publish(ExecutionRecovered(
                execution_id=execution.id,
                process_id=execution.process_id,
                process_name=execution.process_name,
                action=action.value,
            ))

    async def _publish_recovery_completed(self, report: RecoveryReport) -> None:
        """Publish event that recovery scan has completed."""
        if self.event_bus:
            from ..domain.events import ExecutionRecoveryCompleted
            await self.event_bus.publish(ExecutionRecoveryCompleted(
                resumed_count=len(report.resumed),
                retried_count=len(report.retried),
                failed_count=len(report.failed),
                skipped_count=len(report.skipped),
                error_count=len(report.errors),
                duration_ms=report.duration_ms,
            ))
