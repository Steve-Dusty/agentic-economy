"""
Audit API Router

Provides REST API endpoints for querying audit logs.

Reference: BACKLOG_ACCESS_AUDIT.md - E18-03
"""

import logging
import os
from datetime import datetime
from typing import Optional, List, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dependencies import get_current_user, CurrentUser
from services.process_engine.services import (
    AuditService,
    AuditEntry,
    AuditId,
    AuditFilter,
    ProcessAuthorizationService,
)
from services.process_engine.repositories import SqliteAuditRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])


# =============================================================================
# Pydantic Models for API
# =============================================================================


class AuditEntryResponse(BaseModel):
    """Response model for a single audit entry."""
    id: str
    timestamp: str
    actor: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditListResponse(BaseModel):
    """Response for listing audit entries."""
    entries: List[AuditEntryResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# Dependencies
# =============================================================================


# Database path configuration
DB_PATH = os.getenv("TRINITY_DB_PATH", str(Path.home() / "trinity-data" / "trinity.db"))

_audit_service: Optional[AuditService] = None
_auth_service: Optional[ProcessAuthorizationService] = None


def get_audit_service() -> AuditService:
    """Get the audit service."""
    global _audit_service
    if _audit_service is None:
        audit_db_path = DB_PATH.replace(".db", "_audit.db")
        os.makedirs(os.path.dirname(audit_db_path), exist_ok=True)
        repository = SqliteAuditRepository(audit_db_path)
        _audit_service = AuditService(repository)
    return _audit_service


def get_auth_service() -> ProcessAuthorizationService:
    """Get the authorization service."""
    global _auth_service
    if _auth_service is None:
        _auth_service = ProcessAuthorizationService()
    return _auth_service


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=AuditListResponse)
async def list_audit_entries(
    current_user: CurrentUser,
    actor: Optional[str] = Query(None, description="Filter by actor (user email)"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    from_date: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
):
    """
    List audit entries with optional filters.

    Requires: ADMIN role

    This endpoint provides access to the audit trail for compliance
    and debugging purposes. Only administrators can access audit logs.
    """
    # Authorization check - admin only
    auth = get_auth_service()
    if not auth.is_admin(current_user):
        auth.log_authorization_failure(
            current_user, "audit.list", "audit", None, "Admin access required"
        )
        raise HTTPException(status_code=403, detail="Admin access required")

    # Build filter
    audit_filter = AuditFilter(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    # Parse dates if provided
    if from_date:
        try:
            audit_filter.from_date = datetime.fromisoformat(from_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format")

    if to_date:
        try:
            audit_filter.to_date = datetime.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format")

    # Query entries
    audit_service = get_audit_service()
    entries = await audit_service.query(
        filter=audit_filter,
        limit=limit,
        offset=offset,
    )
    total = await audit_service.count(filter=audit_filter)

    return AuditListResponse(
        entries=[_to_response(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{audit_id}", response_model=AuditEntryResponse)
async def get_audit_entry(
    audit_id: str,
    current_user: CurrentUser,
):
    """
    Get a single audit entry by ID.

    Requires: ADMIN role
    """
    # Authorization check - admin only
    auth = get_auth_service()
    if not auth.is_admin(current_user):
        auth.log_authorization_failure(
            current_user, "audit.read", "audit", audit_id, "Admin access required"
        )
        raise HTTPException(status_code=403, detail="Admin access required")

    audit_service = get_audit_service()

    try:
        aid = AuditId(audit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audit ID format")

    entry = await audit_service.get_by_id(aid)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")

    return _to_response(entry)


# =============================================================================
# Helper Functions
# =============================================================================


def _to_response(entry: AuditEntry) -> AuditEntryResponse:
    """Convert AuditEntry to response model."""
    return AuditEntryResponse(
        id=str(entry.id),
        timestamp=entry.timestamp.isoformat(),
        actor=entry.actor,
        action=entry.action,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        details=entry.details,
        ip_address=entry.ip_address,
        user_agent=entry.user_agent,
    )
