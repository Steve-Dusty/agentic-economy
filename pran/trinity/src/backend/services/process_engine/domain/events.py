"""
Process Engine Domain Events

Events represent something that has happened in the domain.
They are immutable facts about past occurrences.

Reference: IT3 Section 5 (Domain Events)
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .value_objects import ProcessId, ExecutionId, StepId, Duration, Money
from .enums import StepType


def _utcnow() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


# =============================================================================
# Base Event
# =============================================================================


@dataclass(frozen=True)
class DomainEvent(ABC):
    """
    Base class for all domain events.

    Events are immutable records of something that happened.
    They always have a timestamp and can be serialized.
    """
    # kw_only=True allows subclasses to have required fields before this
    timestamp: datetime = field(default_factory=_utcnow, kw_only=True)

    @property
    def event_type(self) -> str:
        """Return the event type name."""
        return self.__class__.__name__

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        # Base implementation - subclasses add their fields
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# Process Lifecycle Events
# =============================================================================


@dataclass(frozen=True)
class ProcessStarted(DomainEvent):
    """
    Emitted when a process execution begins.
    """
    execution_id: ExecutionId
    process_id: ProcessId
    process_name: str
    triggered_by: str = "manual"

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "triggered_by": self.triggered_by,
        }


@dataclass(frozen=True)
class ProcessCompleted(DomainEvent):
    """
    Emitted when a process execution completes successfully.
    """
    execution_id: ExecutionId
    process_id: ProcessId
    process_name: str
    total_cost: Money
    total_duration: Duration
    output_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "total_cost": str(self.total_cost),
            "total_duration_seconds": self.total_duration.seconds,
            "output_data": self.output_data,
        }


@dataclass(frozen=True)
class ProcessFailed(DomainEvent):
    """
    Emitted when a process execution fails.
    """
    execution_id: ExecutionId
    process_id: ProcessId
    process_name: str
    failed_step_id: StepId
    error_message: str
    error_code: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "failed_step_id": str(self.failed_step_id),
            "error_message": self.error_message,
        }
        if self.error_code:
            result["error_code"] = self.error_code
        return result


@dataclass(frozen=True)
class ProcessCancelled(DomainEvent):
    """
    Emitted when a process execution is cancelled.
    """
    execution_id: ExecutionId
    process_id: ProcessId
    process_name: str
    cancelled_by: str
    reason: str

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "cancelled_by": self.cancelled_by,
            "reason": self.reason,
        }


# =============================================================================
# Step Lifecycle Events
# =============================================================================


@dataclass(frozen=True)
class StepStarted(DomainEvent):
    """
    Emitted when a step begins execution.
    """
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    step_type: StepType

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "step_type": self.step_type.value,
        }


@dataclass(frozen=True)
class StepCompleted(DomainEvent):
    """
    Emitted when a step completes successfully.
    """
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    output: dict = field(default_factory=dict)
    cost: Money = field(default_factory=lambda: Money.zero())
    duration: Duration = field(default_factory=lambda: Duration(0))

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "output": self.output,
            "cost": str(self.cost),
            "duration_seconds": self.duration.seconds,
        }


@dataclass(frozen=True)
class StepFailed(DomainEvent):
    """
    Emitted when a step fails.
    """
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    error_message: str
    error_code: Optional[str] = None
    retry_count: int = 0
    will_retry: bool = False

    def to_dict(self) -> dict:
        result = {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "will_retry": self.will_retry,
        }
        if self.error_code:
            result["error_code"] = self.error_code
        return result


@dataclass(frozen=True)
class StepRetrying(DomainEvent):
    """
    Emitted when a step fails but will be retried.
    """
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    error_message: str
    attempt: int
    max_attempts: int
    next_retry_at: datetime

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "error_message": self.error_message,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "next_retry_at": self.next_retry_at.isoformat(),
        }


@dataclass(frozen=True)
class StepSkipped(DomainEvent):
    """
    Emitted when a step is skipped.
    """
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    reason: str  # "condition_not_met", "upstream_failed"

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class StepWaitingApproval(DomainEvent):
    """
    Emitted when a step is waiting for human approval.
    """
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    approval_id: str
    title: str
    assignees: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "approval_id": self.approval_id,
            "title": self.title,
            "assignees": self.assignees,
        }


# =============================================================================
# Approval Events
# =============================================================================


@dataclass(frozen=True)
class ApprovalRequested(DomainEvent):
    """
    Emitted when a step requires human approval.
    """
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    title: str
    description: str
    assignees: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "title": self.title,
            "description": self.description,
            "assignees": self.assignees,
        }


@dataclass(frozen=True)
class ApprovalDecided(DomainEvent):
    """
    Emitted when an approval decision is made.
    """
    execution_id: ExecutionId
    step_id: StepId
    decision: str  # "approved" | "rejected"
    decided_by: str
    comment: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "decision": self.decision,
            "decided_by": self.decided_by,
        }
        if self.comment:
            result["comment"] = self.comment
        return result


# =============================================================================
# Compensation Events
# =============================================================================


@dataclass(frozen=True)
class CompensationStarted(DomainEvent):
    """
    Emitted when compensation handlers begin execution.
    """
    execution_id: ExecutionId
    process_id: ProcessId
    process_name: str
    compensation_count: int  # Number of compensations to run

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "compensation_count": self.compensation_count,
        }


@dataclass(frozen=True)
class CompensationCompleted(DomainEvent):
    """
    Emitted when a single compensation handler completes successfully.
    """
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    compensation_type: str  # "agent_task" | "notification"

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "compensation_type": self.compensation_type,
        }


@dataclass(frozen=True)
class CompensationFailed(DomainEvent):
    """
    Emitted when a compensation handler fails.
    """
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    compensation_type: str
    error_message: str

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "compensation_type": self.compensation_type,
            "error_message": self.error_message,
        }


# =============================================================================
# Process Definition Events
# =============================================================================


@dataclass(frozen=True)
class ProcessCreated(DomainEvent):
    """
    Emitted when a new process definition is created.
    """
    process_id: ProcessId
    process_name: str
    version: int
    created_by: str

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "version": self.version,
            "created_by": self.created_by,
        }


@dataclass(frozen=True)
class ProcessUpdated(DomainEvent):
    """
    Emitted when a process definition is updated.
    """
    process_id: ProcessId
    process_name: str
    version: int
    updated_by: str

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "version": self.version,
            "updated_by": self.updated_by,
        }


@dataclass(frozen=True)
class ProcessPublished(DomainEvent):
    """
    Emitted when a process definition is published.
    """
    process_id: ProcessId
    process_name: str
    version: int
    published_by: str

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "version": self.version,
            "published_by": self.published_by,
        }


@dataclass(frozen=True)
class ProcessArchived(DomainEvent):
    """
    Emitted when a process definition is archived.
    """
    process_id: ProcessId
    process_name: str
    version: int
    archived_by: str

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "version": self.version,
            "archived_by": self.archived_by,
        }


# =============================================================================
# Informed Agent Notification Events (EMI Pattern)
# =============================================================================


@dataclass(frozen=True)
class InformedNotification(DomainEvent):
    """
    Notification sent to informed agents about step events.

    Part of the EMI (Executor/Monitor/Informed) pattern.
    Informed agents receive these notifications for awareness
    and learning but don't need to take action.
    """
    event_type_name: str  # "step_completed", "step_failed"
    process_name: str
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    output_summary: str  # Truncated output for context
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "event_type_name": self.event_type_name,
            "process_name": self.process_name,
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "output_summary": self.output_summary,
            "metadata": self.metadata,
        }


# =============================================================================
# Execution Recovery Events
# =============================================================================


@dataclass(frozen=True)
class ExecutionRecoveryStarted(DomainEvent):
    """
    Emitted when the recovery scan begins on backend startup.

    Reference: IT5 Section 2.3 (Recovery on Backend Restart)
    Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-11
    """

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
        }


@dataclass(frozen=True)
class ExecutionRecovered(DomainEvent):
    """
    Emitted when a single execution is recovered after restart.

    Contains the action taken (resume, retry_step, mark_failed).
    """
    execution_id: ExecutionId
    process_id: ProcessId
    process_name: str
    action: str  # "resume", "retry_step", "mark_failed"

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "process_id": str(self.process_id),
            "process_name": self.process_name,
            "action": self.action,
        }


@dataclass(frozen=True)
class ExecutionRecoveryFailed(DomainEvent):
    """
    Emitted when recovery of a single execution fails.
    """
    execution_id: ExecutionId
    error_message: str
    action_attempted: str  # "resume", "retry_step", "mark_failed"

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "execution_id": str(self.execution_id),
            "error_message": self.error_message,
            "action_attempted": self.action_attempted,
        }


@dataclass(frozen=True)
class ExecutionRecoveryCompleted(DomainEvent):
    """
    Emitted when the full recovery scan completes.

    Contains summary counts of all recovery operations.
    """
    resumed_count: int
    retried_count: int
    failed_count: int  # Executions marked as failed due to age
    skipped_count: int  # Already terminal, no action needed
    error_count: int  # Recovery attempts that errored
    duration_ms: int

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "resumed_count": self.resumed_count,
            "retried_count": self.retried_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "duration_ms": self.duration_ms,
            "total_processed": self.resumed_count + self.retried_count + self.failed_count + self.skipped_count,
        }
