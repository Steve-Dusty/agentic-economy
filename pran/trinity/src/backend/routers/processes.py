"""
Process Definition API Router

Provides REST API endpoints for managing process definitions.
Part of the Process-Driven Platform feature.

Reference: BACKLOG_MVP.md - E1-04
Reference: BACKLOG_ACCESS_AUDIT.md - E17-04 (Authorization)
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from dependencies import get_current_user, CurrentUser
from services.process_engine.domain import (
    ProcessDefinition,
    ProcessId,
    DefinitionStatus,
    ProcessValidationError,
    ProcessCreated,
    ProcessUpdated,
    ProcessPublished,
    ProcessArchived,
    ScheduleTriggerConfig,
    expand_cron_preset,
)
from services.process_engine.repositories import SqliteProcessDefinitionRepository
from services.process_engine.services import ProcessValidator, ValidationResult, ProcessAuthorizationService
from services.process_engine.events import InMemoryEventBus, get_websocket_publisher

# For process schedule management
import sqlite3
import secrets
from datetime import datetime
from croniter import croniter
import pytz

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/processes", tags=["processes"])


# =============================================================================
# Pydantic Models for API
# =============================================================================


class ProcessCreateRequest(BaseModel):
    """Request body for creating a new process definition."""
    yaml_content: str = Field(..., description="YAML content of the process definition")


class ProcessUpdateRequest(BaseModel):
    """Request body for updating a process definition."""
    yaml_content: str = Field(..., description="Updated YAML content")


class ProcessValidateRequest(BaseModel):
    """Request body for validating a process definition."""
    yaml_content: str = Field(..., description="YAML content to validate")


class ValidationErrorResponse(BaseModel):
    """Single validation error."""
    message: str
    level: str = "error"  # error, warning, info
    path: Optional[str] = None
    line: Optional[int] = None
    suggestion: Optional[str] = None


class ValidationResponse(BaseModel):
    """Response from validation endpoint."""
    is_valid: bool
    errors: List[ValidationErrorResponse] = []
    warnings: List[ValidationErrorResponse] = []


class ProcessSummary(BaseModel):
    """Summary view of a process definition."""
    id: str
    name: str
    version: str
    status: str
    description: str
    step_count: int
    created_by: Optional[str] = None
    created_at: str
    updated_at: str
    published_at: Optional[str] = None


class ProcessDetail(BaseModel):
    """Full process definition detail."""
    id: str
    name: str
    version: str
    status: str
    description: str
    steps: List[dict]
    outputs: List[dict]
    created_by: Optional[str] = None
    created_at: str
    updated_at: str
    published_at: Optional[str] = None
    yaml_content: Optional[str] = None


class ProcessListResponse(BaseModel):
    """Response for list endpoint."""
    processes: List[ProcessSummary]
    total: int
    limit: int
    offset: int


# =============================================================================
# Repository Instance
# =============================================================================

# Use the same database path as the main Trinity database
import os
from pathlib import Path

DB_PATH = os.getenv("TRINITY_DB_PATH", str(Path.home() / "trinity-data" / "trinity.db"))
_repository: Optional[SqliteProcessDefinitionRepository] = None


def get_repository() -> SqliteProcessDefinitionRepository:
    """Get or create the process definition repository."""
    global _repository
    if _repository is None:
        # Use a separate database file for process definitions
        process_db_path = DB_PATH.replace(".db", "_processes.db")

        # Ensure directory exists
        os.makedirs(os.path.dirname(process_db_path), exist_ok=True)

        _repository = SqliteProcessDefinitionRepository(process_db_path)
        logger.info(f"Process definition repository initialized at {process_db_path}")
    return _repository


def get_validator() -> ProcessValidator:
    """Get a process validator instance."""
    # For now, no agent checker - will add when we have agent integration
    return ProcessValidator(agent_checker=None)


# =============================================================================
# Authorization Service (IT5 P1)
# =============================================================================

_auth_service: Optional[ProcessAuthorizationService] = None


def get_auth_service() -> ProcessAuthorizationService:
    """Get the process authorization service."""
    global _auth_service
    if _auth_service is None:
        _auth_service = ProcessAuthorizationService()
    return _auth_service


def require_process_permission(permission_check):
    """
    Decorator-like function that checks authorization.

    Usage:
        auth_result = require_process_permission(lambda auth: auth.can_create_process(user))
        if not auth_result:
            raise HTTPException(403, detail=auth_result.reason)
    """
    auth = get_auth_service()
    return permission_check(auth)


# Event bus for process definition events
_event_bus: Optional[InMemoryEventBus] = None


def get_event_bus() -> InMemoryEventBus:
    """Get or create the event bus for definition events."""
    global _event_bus
    if _event_bus is None:
        _event_bus = InMemoryEventBus()
        # Register WebSocket publisher
        websocket_publisher = get_websocket_publisher()
        websocket_publisher.register_with_event_bus(_event_bus)
    return _event_bus


async def publish_event(event) -> None:
    """Publish a domain event (fire and forget)."""
    try:
        event_bus = get_event_bus()
        await event_bus.publish(event)
    except Exception as e:
        logger.warning(f"Failed to publish event {event.__class__.__name__}: {e}")


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("", response_model=ProcessDetail, status_code=201)
async def create_process(
    request: ProcessCreateRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Create a new process definition from YAML.

    The process is created in DRAFT status.

    Requires: PROCESS_CREATE permission
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_create_process(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "process.create", "process", None, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    validator = get_validator()
    result = validator.validate_yaml(request.yaml_content, created_by=current_user.email)

    if not result.is_valid:
        error_messages = [e.message for e in result.errors]
        raise HTTPException(
            status_code=422,
            detail={"message": "Validation failed", "errors": error_messages}
        )

    # Create from validated data
    definition = result.definition
    if definition is None:
        raise HTTPException(status_code=500, detail="Validation passed but no definition created")

    # Save to repository
    repo = get_repository()
    repo.save(definition)

    logger.info(f"Process '{definition.name}' created by {current_user.email}")

    # Emit domain event
    await publish_event(ProcessCreated(
        process_id=definition.id,
        process_name=definition.name,
        version=definition.version.major,
        created_by=current_user.email,
    ))

    return _to_detail(definition, request.yaml_content)


@router.get("", response_model=ProcessListResponse)
async def list_processes(
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="Filter by status (draft, published, archived)"),
    name: Optional[str] = Query(None, description="Filter by name"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> dict:
    """
    List all process definitions.

    Supports filtering by status and name, with pagination.

    Requires: PROCESS_READ permission
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_read_process(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "process.list", "process", None, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    repo = get_repository()

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = DefinitionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Get definitions
    definitions = repo.list_all(limit=limit, offset=offset, status=status_filter)
    total = repo.count(status=status_filter)

    processes = [_to_summary(d) for d in definitions]

    return {
        "processes": processes,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{process_id}", response_model=ProcessDetail)
async def get_process(
    process_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Get a single process definition by ID.

    Requires: PROCESS_READ permission
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_read_process(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "process.read", "process", process_id, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    repo = get_repository()

    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    definition = repo.get_by_id(pid)
    if definition is None:
        raise HTTPException(status_code=404, detail="Process not found")

    return _to_detail(definition)


@router.put("/{process_id}", response_model=ProcessDetail)
async def update_process(
    process_id: str,
    request: ProcessUpdateRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Update a process definition.

    Only DRAFT processes can be updated.

    Requires: PROCESS_UPDATE permission
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_update_process(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "process.update", "process", process_id, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    repo = get_repository()

    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    existing = repo.get_by_id(pid)
    if existing is None:
        raise HTTPException(status_code=404, detail="Process not found")

    if existing.status != DefinitionStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update process in '{existing.status.value}' status. Only DRAFT processes can be updated."
        )

    # Validate new content
    validator = get_validator()
    result = validator.validate_yaml(request.yaml_content, created_by=current_user.email)

    if not result.is_valid:
        error_messages = [e.message for e in result.errors]
        raise HTTPException(
            status_code=422,
            detail={"message": "Validation failed", "errors": error_messages}
        )

    # Update the definition but keep the same ID
    new_definition = result.definition
    if new_definition is None:
        raise HTTPException(status_code=500, detail="Validation passed but no definition created")

    # Preserve ID, created_at, created_by
    from dataclasses import replace
    from datetime import datetime, timezone
    updated = replace(
        new_definition,
        id=existing.id,
        created_at=existing.created_at,
        created_by=existing.created_by,
        updated_at=datetime.now(timezone.utc),
    )

    repo.save(updated)
    logger.info(f"Process '{updated.name}' updated by {current_user.email}")

    # Emit domain event
    await publish_event(ProcessUpdated(
        process_id=updated.id,
        process_name=updated.name,
        version=updated.version.major,
        updated_by=current_user.email,
    ))

    return _to_detail(updated, request.yaml_content)


@router.delete("/{process_id}", status_code=204)
async def delete_process(
    process_id: str,
    current_user: CurrentUser,
) -> None:
    """
    Delete a process definition.

    Only DRAFT and ARCHIVED processes can be deleted.

    Requires: PROCESS_DELETE permission
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_delete_process(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "process.delete", "process", process_id, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    repo = get_repository()

    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    existing = repo.get_by_id(pid)
    if existing is None:
        raise HTTPException(status_code=404, detail="Process not found")

    if existing.status == DefinitionStatus.PUBLISHED:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete PUBLISHED processes. Archive them first."
        )

    repo.delete(pid)
    logger.info(f"Process '{existing.name}' deleted by {current_user.email}")


@router.post("/{process_id}/validate", response_model=ValidationResponse)
async def validate_process(
    process_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Validate an existing process definition.

    Returns validation errors and warnings without modifying the process.
    """
    repo = get_repository()

    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    definition = repo.get_by_id(pid)
    if definition is None:
        raise HTTPException(status_code=404, detail="Process not found")

    validator = get_validator()
    result = validator.validate_definition(definition)

    return _to_validation_response(result)


@router.post("/validate", response_model=ValidationResponse)
async def validate_yaml(
    request: ProcessValidateRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Validate YAML content without saving.

    Useful for real-time validation in the editor.
    """
    validator = get_validator()
    result = validator.validate_yaml(request.yaml_content)

    return _to_validation_response(result)


@router.post("/{process_id}/publish", response_model=ProcessDetail)
async def publish_process(
    process_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Publish a draft process definition.

    Published processes are immutable and can be executed.

    Requires: PROCESS_PUBLISH permission
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_publish_process(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "process.publish", "process", process_id, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    repo = get_repository()

    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    definition = repo.get_by_id(pid)
    if definition is None:
        raise HTTPException(status_code=404, detail="Process not found")

    if definition.status != DefinitionStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish process in '{definition.status.value}' status. Only DRAFT processes can be published."
        )

    try:
        published = definition.publish()
    except ProcessValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={"message": "Validation failed", "errors": e.errors}
        )

    repo.save(published)
    logger.info(f"Process '{published.name}' published by {current_user.email}")

    # Register schedule triggers with the scheduler
    schedule_count = _register_process_schedules(published)
    if schedule_count > 0:
        logger.info(f"Registered {schedule_count} schedule trigger(s) for '{published.name}'")

    # Emit domain event
    await publish_event(ProcessPublished(
        process_id=published.id,
        process_name=published.name,
        version=published.version.major,
        published_by=current_user.email,
    ))

    return _to_detail(published)


@router.post("/{process_id}/archive", response_model=ProcessDetail)
async def archive_process(
    process_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Archive a process definition.

    Archived processes cannot be executed but are preserved for history.
    """
    repo = get_repository()

    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    definition = repo.get_by_id(pid)
    if definition is None:
        raise HTTPException(status_code=404, detail="Process not found")

    if definition.status == DefinitionStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Process is already archived")

    archived = definition.archive()
    repo.save(archived)
    logger.info(f"Process '{archived.name}' archived by {current_user.email}")

    # Unregister schedule triggers from the scheduler
    schedule_count = _unregister_process_schedules(archived.id)
    if schedule_count > 0:
        logger.info(f"Unregistered {schedule_count} schedule trigger(s) for '{archived.name}'")

    # Emit domain event
    await publish_event(ProcessArchived(
        process_id=archived.id,
        process_name=archived.name,
        version=archived.version.major,
        archived_by=current_user.email,
    ))

    return _to_detail(archived)


@router.post("/{process_id}/new-version", response_model=ProcessDetail, status_code=201)
async def create_new_version(
    process_id: str,
    current_user: CurrentUser,
) -> dict:
    """
    Create a new version from an existing process.

    Creates a new DRAFT copy with incremented version number.
    """
    repo = get_repository()

    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    definition = repo.get_by_id(pid)
    if definition is None:
        raise HTTPException(status_code=404, detail="Process not found")

    new_version = definition.create_new_version()
    new_version = replace(new_version, created_by=current_user.email)

    repo.save(new_version)
    logger.info(f"New version of '{new_version.name}' (v{new_version.version}) created by {current_user.email}")

    return _to_detail(new_version)


# =============================================================================
# Helper Functions
# =============================================================================


def _to_summary(definition: ProcessDefinition) -> dict:
    """Convert ProcessDefinition to summary dict."""
    return {
        "id": str(definition.id),
        "name": definition.name,
        "version": str(definition.version),
        "status": definition.status.value,
        "description": definition.description,
        "step_count": len(definition.steps),
        "created_by": definition.created_by,
        "created_at": definition.created_at.isoformat(),
        "updated_at": definition.updated_at.isoformat(),
        "published_at": definition.published_at.isoformat() if definition.published_at else None,
    }


def _to_detail(definition: ProcessDefinition, yaml_content: Optional[str] = None) -> dict:
    """Convert ProcessDefinition to detail dict."""
    import yaml

    result = {
        "id": str(definition.id),
        "name": definition.name,
        "version": str(definition.version),
        "status": definition.status.value,
        "description": definition.description,
        "steps": [step.to_dict() for step in definition.steps],
        "outputs": [output.to_dict() for output in definition.outputs],
        "created_by": definition.created_by,
        "created_at": definition.created_at.isoformat(),
        "updated_at": definition.updated_at.isoformat(),
        "published_at": definition.published_at.isoformat() if definition.published_at else None,
    }

    # Include YAML representation if provided or generate from definition
    if yaml_content:
        result["yaml_content"] = yaml_content
    else:
        result["yaml_content"] = yaml.dump(definition.to_yaml_dict(), default_flow_style=False)

    return result


def _to_validation_response(result: ValidationResult) -> dict:
    """Convert ValidationResult to response dict."""
    errors = []
    warnings = []

    for error in result.errors:
        item = {
            "message": error.message,
            "level": error.level.value,
            "path": error.path,
            "line": error.line,
            "suggestion": error.suggestion,
        }
        if error.level.value == "error":
            errors.append(item)
        else:
            warnings.append(item)

    return {
        "is_valid": result.is_valid,
        "errors": errors,
        "warnings": warnings,
    }


# Need this import for new_version endpoint
from dataclasses import replace


# =============================================================================
# Process Schedule Management
# =============================================================================


def _get_scheduler_db_path() -> str:
    """Get the path to the main Trinity database used by scheduler."""
    return os.getenv("TRINITY_DB_PATH", str(Path.home() / "trinity-data" / "trinity.db"))


def _register_process_schedules(definition: ProcessDefinition) -> int:
    """
    Register schedule triggers for a published process.

    Writes to the process_schedules table that the scheduler service reads.
    Returns the number of schedules registered.
    """
    # Filter for schedule triggers
    schedule_triggers = [
        t for t in definition.triggers
        if isinstance(t, ScheduleTriggerConfig)
    ]

    if not schedule_triggers:
        return 0

    db_path = _get_scheduler_db_path()
    count = 0

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_schedules (
                id TEXT PRIMARY KEY,
                process_id TEXT NOT NULL,
                process_name TEXT NOT NULL,
                trigger_id TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                timezone TEXT DEFAULT 'UTC',
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_run_at TEXT,
                next_run_at TEXT,
                UNIQUE(process_id, trigger_id)
            )
        """)

        now = datetime.utcnow().isoformat()

        for trigger in schedule_triggers:
            if not trigger.enabled:
                continue

            # Expand cron preset if needed
            cron_expr = expand_cron_preset(trigger.cron)

            # Calculate next run time
            next_run = None
            try:
                tz = pytz.timezone(trigger.timezone) if trigger.timezone else pytz.UTC
                cron = croniter(cron_expr, datetime.now(tz))
                next_run = cron.get_next(datetime).isoformat()
            except Exception as e:
                logger.warning(f"Failed to calculate next run time for {trigger.id}: {e}")

            schedule_id = secrets.token_urlsafe(16)

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO process_schedules (
                        id, process_id, process_name, trigger_id, cron_expression,
                        enabled, timezone, description, created_at, updated_at, next_run_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    schedule_id,
                    str(definition.id),
                    definition.name,
                    trigger.id,
                    cron_expr,
                    1,
                    trigger.timezone,
                    trigger.description,
                    now,
                    now,
                    next_run
                ))
                count += 1
                logger.info(f"Registered schedule trigger: {definition.name}/{trigger.id} (cron: {cron_expr})")
            except sqlite3.IntegrityError:
                logger.warning(f"Schedule already exists: {definition.name}/{trigger.id}")

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to register process schedules: {e}")

    return count


def _unregister_process_schedules(process_id: ProcessId) -> int:
    """
    Unregister all schedule triggers for a process.

    Called when a process is archived.
    Returns the number of schedules removed.
    """
    db_path = _get_scheduler_db_path()
    count = 0

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM process_schedules WHERE process_id = ?",
            (str(process_id),)
        )
        count = cursor.rowcount

        conn.commit()
        conn.close()

        if count > 0:
            logger.info(f"Unregistered {count} schedule(s) for process {process_id}")

    except Exception as e:
        logger.error(f"Failed to unregister process schedules: {e}")

    return count


# =============================================================================
# Cost Statistics
# =============================================================================


@router.get("/{process_id}/cost-stats")
async def get_process_cost_stats(
    process_id: str,
    current_user: CurrentUser,
):
    """
    Get cost statistics for a process.

    Returns average cost, total cost, and execution count.
    Reference: BACKLOG_ADVANCED.md - E11-01
    """
    definition_repo = get_definition_repo()

    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    definition = definition_repo.get_by_id(pid)
    if not definition:
        raise HTTPException(status_code=404, detail="Process definition not found")

    # Get executions for this process
    from .executions import get_execution_repo
    from decimal import Decimal

    execution_repo = get_execution_repo()
    executions = execution_repo.list_by_process(pid, limit=1000, offset=0)

    # Calculate statistics
    execution_count = len(executions)
    completed_count = 0
    total_cost = Decimal("0")
    costs = []

    for execution in executions:
        if execution.status.value == "completed":
            completed_count += 1
            if execution.total_cost and execution.total_cost.amount > 0:
                total_cost += execution.total_cost.amount
                costs.append(execution.total_cost.amount)

    # Calculate average
    avg_cost = Decimal("0")
    if costs:
        avg_cost = total_cost / len(costs)

    # Calculate min/max
    min_cost = min(costs) if costs else Decimal("0")
    max_cost = max(costs) if costs else Decimal("0")

    return {
        "process_id": str(definition.id),
        "process_name": definition.name,
        "execution_count": execution_count,
        "completed_count": completed_count,
        "total_cost": f"${total_cost:.2f}",
        "average_cost": f"${avg_cost:.2f}",
        "min_cost": f"${min_cost:.2f}",
        "max_cost": f"${max_cost:.2f}",
        "executions_with_cost": len(costs),
    }


# =============================================================================
# Analytics Endpoints (E11-02)
# =============================================================================


@router.get("/{process_id}/analytics")
async def get_process_analytics(
    process_id: str,
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
):
    """
    Get analytics metrics for a specific process.

    Returns success rate, average duration, average cost, and more.
    Reference: BACKLOG_ADVANCED.md - E11-02
    """
    from .executions import get_execution_repo
    from services.process_engine.services.analytics import ProcessAnalytics

    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    definition_repo = get_repository()
    execution_repo = get_execution_repo()

    analytics = ProcessAnalytics(definition_repo, execution_repo)
    metrics = analytics.get_process_metrics(pid, days=days)

    return metrics.to_dict()


@router.get("/analytics/trends")
async def get_process_trends(
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    process_id: Optional[str] = Query(None, description="Filter by process ID"),
):
    """
    Get execution trend data over time.

    Returns daily execution counts, success rates, and costs.
    Reference: BACKLOG_ADVANCED.md - E11-02
    """
    from .executions import get_execution_repo
    from services.process_engine.services.analytics import ProcessAnalytics

    pid = None
    if process_id:
        try:
            pid = ProcessId(process_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid process ID format")

    definition_repo = get_repository()
    execution_repo = get_execution_repo()

    analytics = ProcessAnalytics(definition_repo, execution_repo)
    trends = analytics.get_trend_data(days=days, process_id=pid)

    return trends.to_dict()


@router.get("/analytics/all")
async def get_all_process_analytics(
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
):
    """
    Get analytics metrics for all published processes.

    Returns a list of metrics per process for the dashboard.
    Reference: BACKLOG_ADVANCED.md - E11-02
    """
    from .executions import get_execution_repo
    from services.process_engine.services.analytics import ProcessAnalytics

    definition_repo = get_repository()
    execution_repo = get_execution_repo()

    analytics = ProcessAnalytics(definition_repo, execution_repo)
    all_metrics = analytics.get_all_process_metrics(days=days)

    return {
        "processes": [m.to_dict() for m in all_metrics],
        "days": days,
    }
