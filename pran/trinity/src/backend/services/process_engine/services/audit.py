"""
Audit Service

Provides compliance-ready audit logging for all process operations.

Reference: IT5 Section 5.4 (Audit Trail)
Reference: BACKLOG_ACCESS_AUDIT.md - E18-01, E18-02
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any, List


logger = logging.getLogger(__name__)


# =============================================================================
# Domain Model (E18-01)
# =============================================================================


class AuditAction(str, Enum):
    """
    Standard audit actions for process engine operations.

    These are logged for compliance and debugging.
    """
    # Process operations
    PROCESS_CREATE = "process.create"
    PROCESS_READ = "process.read"
    PROCESS_UPDATE = "process.update"
    PROCESS_DELETE = "process.delete"
    PROCESS_PUBLISH = "process.publish"
    PROCESS_ARCHIVE = "process.archive"

    # Execution operations
    EXECUTION_TRIGGER = "execution.trigger"
    EXECUTION_VIEW = "execution.view"
    EXECUTION_CANCEL = "execution.cancel"
    EXECUTION_RETRY = "execution.retry"
    EXECUTION_COMPLETE = "execution.complete"
    EXECUTION_FAIL = "execution.fail"

    # Approval operations
    APPROVAL_REQUEST = "approval.request"
    APPROVAL_DECIDE = "approval.decide"
    APPROVAL_DELEGATE = "approval.delegate"
    APPROVAL_EXPIRE = "approval.expire"

    # Admin operations
    ADMIN_CONFIG_CHANGE = "admin.config_change"
    ADMIN_RECOVERY = "admin.recovery"

    # Authentication
    AUTH_FAILURE = "auth.failure"


@dataclass(frozen=True)
class AuditId:
    """Unique identifier for an audit entry."""
    value: str

    @classmethod
    def generate(cls) -> "AuditId":
        """Generate a new unique audit ID."""
        return cls(value=str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AuditEntry:
    """
    Immutable audit log entry.

    Records who did what, when, and to which resource.
    These entries are append-only - never updated or deleted.

    Reference: IT5 Section 5.4
    """
    id: AuditId
    timestamp: datetime
    actor: str  # user email or "system"
    action: str  # AuditAction value or custom string
    resource_type: str  # "process", "execution", "approval"
    resource_id: Optional[str]
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditEntry":
        """Create from dictionary."""
        return cls(
            id=AuditId(data["id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            actor=data["actor"],
            action=data["action"],
            resource_type=data["resource_type"],
            resource_id=data.get("resource_id"),
            details=data.get("details", {}),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
        )


@dataclass
class AuditFilter:
    """Filters for querying audit entries."""
    actor: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


# =============================================================================
# Audit Service (E18-02)
# =============================================================================


class AuditService:
    """
    Service for logging and querying audit entries.

    All state-changing operations should be logged through this service.
    Entries are append-only - never updated or deleted.

    Example usage:
    ```python
    audit_service = AuditService(repository)

    # Log an action
    await audit_service.log(
        actor=user.email,
        action=AuditAction.PROCESS_CREATE,
        resource_type="process",
        resource_id=process.id,
        details={"name": process.name},
        request=request,  # FastAPI request for IP/user-agent
    )

    # Query entries
    entries = await audit_service.query(
        filter=AuditFilter(actor="admin@example.com"),
        limit=100,
    )
    ```
    """

    def __init__(self, repository: "AuditRepository"):
        """
        Initialize the audit service.

        Args:
            repository: Storage backend for audit entries
        """
        self.repository = repository

    async def log(
        self,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        request: Any = None,
    ) -> AuditId:
        """
        Log an audit entry.

        Args:
            actor: Who performed the action (user email or "system")
            action: What was done (AuditAction value or custom string)
            resource_type: Type of resource affected
            resource_id: ID of the affected resource
            details: Action-specific context
            request: FastAPI Request object for IP/user-agent extraction

        Returns:
            ID of the created audit entry
        """
        # Extract request metadata if available
        ip_address = None
        user_agent = None
        if request:
            ip_address = getattr(request.client, 'host', None) if hasattr(request, 'client') else None
            user_agent = request.headers.get("user-agent") if hasattr(request, 'headers') else None

        entry = AuditEntry(
            id=AuditId.generate(),
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            action=action if isinstance(action, str) else action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.repository.append(entry)

        logger.debug(
            f"Audit: {actor} {action} {resource_type}:{resource_id or 'N/A'}"
        )

        return entry.id

    async def log_sync(
        self,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditId:
        """
        Synchronous version of log for non-async contexts.

        Useful when logging from sync code paths.
        """
        entry = AuditEntry(
            id=AuditId.generate(),
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            action=action if isinstance(action, str) else action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Use sync append if available, otherwise fall back to async
        if hasattr(self.repository, 'append_sync'):
            self.repository.append_sync(entry)
        else:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.repository.append(entry))
            else:
                loop.run_until_complete(self.repository.append(entry))

        logger.debug(
            f"Audit: {actor} {action} {resource_type}:{resource_id or 'N/A'}"
        )

        return entry.id

    async def query(
        self,
        filter: Optional[AuditFilter] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """
        Query audit entries with optional filters.

        Args:
            filter: Optional filters to apply
            limit: Maximum entries to return
            offset: Number of entries to skip

        Returns:
            List of matching audit entries
        """
        return await self.repository.list(
            filter=filter,
            limit=limit,
            offset=offset,
        )

    async def get_by_id(self, audit_id: AuditId) -> Optional[AuditEntry]:
        """
        Get a single audit entry by ID.

        Args:
            audit_id: ID of the entry to retrieve

        Returns:
            The audit entry or None if not found
        """
        return await self.repository.get_by_id(audit_id)

    async def count(self, filter: Optional[AuditFilter] = None) -> int:
        """
        Count audit entries matching a filter.

        Args:
            filter: Optional filters to apply

        Returns:
            Number of matching entries
        """
        return await self.repository.count(filter)


# =============================================================================
# Repository Interface
# =============================================================================


class AuditRepository:
    """
    Abstract repository interface for audit storage.

    Implementations must be append-only - no updates or deletes.
    """

    async def append(self, entry: AuditEntry) -> None:
        """Append an audit entry (async)."""
        raise NotImplementedError

    def append_sync(self, entry: AuditEntry) -> None:
        """Append an audit entry (sync)."""
        raise NotImplementedError

    async def get_by_id(self, audit_id: AuditId) -> Optional[AuditEntry]:
        """Get a single entry by ID."""
        raise NotImplementedError

    async def list(
        self,
        filter: Optional[AuditFilter] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """List entries with optional filters."""
        raise NotImplementedError

    async def count(self, filter: Optional[AuditFilter] = None) -> int:
        """Count entries matching a filter."""
        raise NotImplementedError
