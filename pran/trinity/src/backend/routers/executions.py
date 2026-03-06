"""
Process Execution API Router

Provides REST API endpoints for managing process executions.
Part of the Process-Driven Platform feature.

Reference: BACKLOG_MVP.md - E2-05
Reference: BACKLOG_ACCESS_AUDIT.md - E17-04 (Authorization)
"""

import asyncio
import logging
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from pydantic import BaseModel, Field

from dependencies import get_current_user, CurrentUser
from services.process_engine.services import ProcessAuthorizationService, ExecutionLimitService
from services.process_engine.domain import (
    ProcessDefinition,
    ProcessExecution,
    ProcessId,
    ExecutionId,
    ExecutionStatus,
    StepStatus,
    DefinitionStatus,
)
from services.process_engine.repositories import (
    SqliteProcessDefinitionRepository,
    SqliteProcessExecutionRepository,
    SqliteEventRepository,
)
from services.process_engine.services import OutputStorage, EventLogger
from services.process_engine.events import InMemoryEventBus, get_websocket_publisher, get_webhook_publisher
from services.process_engine.engine import (
    ExecutionEngine,
    StepHandlerRegistry,
    AgentTaskHandler,
    HumanApprovalHandler,
    GatewayHandler,
    NotificationHandler,
    TimerHandler,
    SubProcessHandler,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/executions", tags=["executions"])


# =============================================================================
# Pydantic Models for API
# =============================================================================


class ExecutionStartRequest(BaseModel):
    """Request body for starting a new execution."""
    input_data: dict[str, Any] = Field(default_factory=dict, description="Input data for the process")
    triggered_by: str = Field(default="api", description="What triggered this execution")


class StepError(BaseModel):
    """Error details for a failed step."""
    message: str
    code: Optional[str] = None
    attempt: Optional[int] = None
    failed_at: Optional[str] = None


class StepExecutionSummary(BaseModel):
    """Summary of a step execution."""
    step_id: str
    status: str
    step_type: Optional[str] = None  # Type of step (agent_task, gateway, sub_process, etc.)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[StepError] = None
    retry_count: int = 0
    parallel_level: int = 0  # Execution level for parallel visualization
    cost: Optional[str] = None  # Cost for this step


class ExecutionSummary(BaseModel):
    """Summary view of an execution."""
    id: str
    process_id: str
    process_name: str
    status: str
    triggered_by: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    retry_of: Optional[str] = None  # ID of original execution if this is a retry


class ExecutionDetail(BaseModel):
    """Detailed view of an execution."""
    id: str
    process_id: str
    process_version: str
    process_name: str
    status: str
    triggered_by: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    total_cost: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    steps: List[StepExecutionSummary]
    has_parallel_steps: bool = False  # True if process has parallel execution
    retry_of: Optional[str] = None  # ID of original execution if this is a retry
    # Sub-process relationships
    parent_execution_id: Optional[str] = None  # Parent execution if this is a sub-process
    parent_step_id: Optional[str] = None  # Step that spawned this sub-process
    child_execution_ids: List[str] = Field(default_factory=list)  # Child executions


class ExecutionListResponse(BaseModel):
    """Response for listing executions."""
    executions: List[ExecutionSummary]
    total: int
    limit: int
    offset: int


# =============================================================================
# Dependencies
# =============================================================================


# Singleton instances for the process engine components
_definition_repo: Optional[SqliteProcessDefinitionRepository] = None
_execution_repo: Optional[SqliteProcessExecutionRepository] = None
_event_repo: Optional[SqliteEventRepository] = None
_event_bus: Optional[InMemoryEventBus] = None
_handler_registry: Optional[StepHandlerRegistry] = None
_event_logger: Optional[EventLogger] = None

# Database path configuration
import os
from pathlib import Path
DB_PATH = os.getenv("TRINITY_DB_PATH", str(Path.home() / "trinity-data" / "trinity.db"))


def get_definition_repo() -> SqliteProcessDefinitionRepository:
    """Get the process definition repository."""
    global _definition_repo
    if _definition_repo is None:
        process_db_path = DB_PATH.replace(".db", "_processes.db")
        os.makedirs(os.path.dirname(process_db_path), exist_ok=True)
        _definition_repo = SqliteProcessDefinitionRepository(process_db_path)
    return _definition_repo


def get_execution_repo() -> SqliteProcessExecutionRepository:
    """Get the process execution repository."""
    global _execution_repo
    if _execution_repo is None:
        exec_db_path = DB_PATH.replace(".db", "_executions.db")
        os.makedirs(os.path.dirname(exec_db_path), exist_ok=True)
        _execution_repo = SqliteProcessExecutionRepository(exec_db_path)
    return _execution_repo


def get_event_repo() -> SqliteEventRepository:
    """Get the event repository."""
    global _event_repo
    if _event_repo is None:
        event_db_path = DB_PATH.replace(".db", "_events.db")
        os.makedirs(os.path.dirname(event_db_path), exist_ok=True)
        _event_repo = SqliteEventRepository(event_db_path)
    return _event_repo


def get_event_bus() -> InMemoryEventBus:
    """Get the event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = InMemoryEventBus()
        # Register WebSocket publisher to broadcast events
        websocket_publisher = get_websocket_publisher()
        websocket_publisher.register_with_event_bus(_event_bus)
        # Register Webhook publisher for external integrations
        webhook_publisher = get_webhook_publisher()
        webhook_publisher.register_with_event_bus(_event_bus)
    return _event_bus


def get_handler_registry() -> StepHandlerRegistry:
    """Get the step handler registry."""
    global _handler_registry
    if _handler_registry is None:
        _handler_registry = StepHandlerRegistry()
        # Register default handlers
        _handler_registry.register(AgentTaskHandler())
        _handler_registry.register(HumanApprovalHandler())
        _handler_registry.register(GatewayHandler())
        _handler_registry.register(NotificationHandler())
        _handler_registry.register(TimerHandler())

        # Register SubProcessHandler with required dependencies
        sub_process_handler = SubProcessHandler(
            definition_repo=get_definition_repo(),
            engine_factory=get_execution_engine,
        )
        _handler_registry.register(sub_process_handler)
    return _handler_registry


def get_event_logger() -> EventLogger:
    """Get and start the event logger."""
    global _event_logger
    if _event_logger is None:
        repo = get_event_repo()
        bus = get_event_bus()
        _event_logger = EventLogger(repo, bus)
        _event_logger.start()
    return _event_logger


def get_execution_engine() -> ExecutionEngine:
    """Get the execution engine."""
    execution_repo = get_execution_repo()
    output_storage = OutputStorage(execution_repo)

    # Ensure event logger is running
    get_event_logger()

    return ExecutionEngine(
        execution_repo=execution_repo,
        event_bus=get_event_bus(),
        output_storage=output_storage,
        handler_registry=get_handler_registry(),
    )


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


# =============================================================================
# Execution Limit Service (IT5 P1 - E19-01)
# =============================================================================

_limit_service: Optional[ExecutionLimitService] = None


def get_limit_service() -> ExecutionLimitService:
    """Get the execution limit service."""
    global _limit_service
    if _limit_service is None:
        _limit_service = ExecutionLimitService(get_execution_repo())
    return _limit_service


# =============================================================================
# Recovery Service
# =============================================================================

from services.process_engine.services import ExecutionRecoveryService, RecoveryReport

_recovery_service: Optional[ExecutionRecoveryService] = None
_last_recovery_report: Optional[RecoveryReport] = None


def get_recovery_service() -> ExecutionRecoveryService:
    """Get the execution recovery service."""
    global _recovery_service
    if _recovery_service is None:
        _recovery_service = ExecutionRecoveryService(
            execution_repo=get_execution_repo(),
            definition_repo=get_definition_repo(),
            execution_engine=get_execution_engine(),
            event_bus=get_event_bus(),
        )
    return _recovery_service


async def run_execution_recovery() -> RecoveryReport:
    """
    Run execution recovery on startup.

    Called from main.py lifespan handler to recover any executions
    that were interrupted by a previous restart.

    Reference: IT5 Section 2.3 (Recovery on Backend Restart)
    Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-12
    """
    global _last_recovery_report

    recovery_service = get_recovery_service()
    report = await recovery_service.recover_on_startup()
    _last_recovery_report = report

    return report


def get_last_recovery_report() -> Optional[RecoveryReport]:
    """Get the last recovery report for health checks."""
    return _last_recovery_report


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/processes/{process_id}/execute", response_model=ExecutionDetail, status_code=201)
async def start_execution(
    process_id: str,
    current_user: CurrentUser,
    request: ExecutionStartRequest = Body(default_factory=ExecutionStartRequest),
    background_tasks: BackgroundTasks = None,
):
    """
    Start a new execution of a process.

    The execution runs asynchronously in the background.
    Returns the initial execution state immediately.

    Requires: EXECUTION_TRIGGER permission
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_trigger_execution(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "execution.trigger", "process", process_id, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    definition_repo = get_definition_repo()

    # Get the process definition
    try:
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    definition = definition_repo.get_by_id(pid)
    if not definition:
        raise HTTPException(status_code=404, detail="Process definition not found")

    # Only published processes can be executed
    if definition.status != DefinitionStatus.PUBLISHED:
        raise HTTPException(
            status_code=400,
            detail=f"Process is not published (status: {definition.status.value})"
        )

    # Check execution limits (IT5 P1 - E19-01)
    limit_service = get_limit_service()
    limit_result = limit_service.check_can_start(pid)
    if not limit_result:
        logger.warning(f"Execution limit exceeded for {process_id}: {limit_result.reason}")
        raise HTTPException(
            status_code=429,  # Too Many Requests
            detail=limit_result.reason,
        )

    # Create the execution
    execution_repo = get_execution_repo()
    execution = ProcessExecution.create(
        definition=definition,
        input_data=request.input_data,
        triggered_by=request.triggered_by,
    )
    execution_repo.save(execution)

    logger.info(f"Created execution {execution.id} for process '{definition.name}' by user {current_user.username}")

    # Run execution in background
    if background_tasks:
        background_tasks.add_task(_run_execution, str(execution.id), str(definition.id))

    return _to_detail(execution, definition)


async def _run_execution(execution_id: str, process_id: str):
    """Background task to run an execution."""
    try:
        definition_repo = get_definition_repo()
        execution_repo = get_execution_repo()
        engine = get_execution_engine()

        definition = definition_repo.get_by_id(ProcessId(process_id))
        execution = execution_repo.get_by_id(ExecutionId(execution_id))

        if definition and execution:
            await engine.resume(execution, definition)

    except Exception as e:
        logger.exception(f"Error running execution {execution_id}")
        # Update execution to failed state
        try:
            execution_repo = get_execution_repo()
            execution = execution_repo.get_by_id(ExecutionId(execution_id))
            if execution and execution.status not in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                execution.fail(str(e))
                execution_repo.save(execution)
        except Exception:
            pass


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="Filter by status"),
    process_id: Optional[str] = Query(None, description="Filter by process ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all executions with optional filters.

    Requires: EXECUTION_VIEW permission
    Note: VIEWER role can only see own executions
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_view_execution(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "execution.list", "execution", None, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    execution_repo = get_execution_repo()

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = ExecutionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Filter by process if specified
    if process_id:
        try:
            pid = ProcessId(process_id)
            executions = execution_repo.list_by_process(pid, limit=limit, offset=offset)
            total = len(executions)  # Simplified count
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid process ID format")
    else:
        executions = execution_repo.list_all(limit=limit, offset=offset, status=status_filter)
        total = execution_repo.count(status=status_filter)

    return ExecutionListResponse(
        executions=[_to_summary(e) for e in executions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{execution_id}", response_model=ExecutionDetail)
async def get_execution(
    execution_id: str,
    current_user: CurrentUser,
):
    """
    Get detailed information about a specific execution.

    Requires: EXECUTION_VIEW permission
    Note: VIEWER role can only see own executions
    """
    execution_repo = get_execution_repo()
    definition_repo = get_definition_repo()

    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")

    execution = execution_repo.get_by_id(eid)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Authorization check with execution context (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_view_execution(current_user, execution)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "execution.view", "execution", execution_id, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    # Get definition for parallel structure info
    definition = definition_repo.get_by_id(execution.process_id)

    return _to_detail(execution, definition)


@router.post("/{execution_id}/cancel", response_model=ExecutionDetail)
async def cancel_execution(
    execution_id: str,
    current_user: CurrentUser,
):
    """
    Cancel a running execution.

    Requires: EXECUTION_CANCEL permission
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_cancel_execution(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "execution.cancel", "execution", execution_id, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    execution_repo = get_execution_repo()
    definition_repo = get_definition_repo()

    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")

    execution = execution_repo.get_by_id(eid)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING, ExecutionStatus.PAUSED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel execution in status: {execution.status.value}"
        )

    execution.cancel(f"Cancelled by {current_user.username}")
    execution_repo.save(execution)

    logger.info(f"Execution {execution_id} cancelled by {current_user.username}")

    definition = definition_repo.get_by_id(execution.process_id)
    return _to_detail(execution, definition)


@router.post("/{execution_id}/retry", response_model=ExecutionDetail, status_code=201)
async def retry_execution(
    execution_id: str,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks = None,
):
    """
    Retry a failed execution.

    Creates a new execution with the same input data.

    Requires: EXECUTION_RETRY permission
    """
    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_retry_execution(current_user)
    if not auth_result:
        auth.log_authorization_failure(
            current_user, "execution.retry", "execution", execution_id, auth_result.reason
        )
        raise HTTPException(status_code=403, detail=auth_result.reason)

    execution_repo = get_execution_repo()
    definition_repo = get_definition_repo()

    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")

    execution = execution_repo.get_by_id(eid)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.status != ExecutionStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed executions (status: {execution.status.value})"
        )

    # Get the process definition
    definition = definition_repo.get_by_id(execution.process_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Process definition not found")

    # Create new execution with same input, linking to original
    new_execution = ProcessExecution.create(
        definition=definition,
        input_data=execution.input_data,
        triggered_by="retry",
        retry_of=execution.id,  # Link to original failed execution
    )
    execution_repo.save(new_execution)

    logger.info(f"Created retry execution {new_execution.id} for failed execution {execution_id}")

    # Run in background
    if background_tasks:
        background_tasks.add_task(_run_execution, str(new_execution.id), str(definition.id))

    return _to_detail(new_execution, definition)


@router.get("/{execution_id}/events")
async def get_execution_events(
    execution_id: str,
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Get audit log of events for an execution.
    """
    event_repo = get_event_repo()

    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")

    events = event_repo.get_by_execution_id(eid, limit=limit, offset=offset)
    return [e.to_dict() for e in events]


@router.get("/{execution_id}/steps/{step_id}/output")
async def get_step_output(
    execution_id: str,
    step_id: str,
    current_user: CurrentUser,
):
    """
    Get the output of a specific step.
    """
    execution_repo = get_execution_repo()
    output_storage = OutputStorage(execution_repo)

    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")

    from services.process_engine.domain import StepId
    try:
        sid = StepId(step_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid step ID format")

    output = output_storage.retrieve(eid, sid)
    if output is None:
        raise HTTPException(status_code=404, detail="Step output not found")

    return {"output": output}


@router.get("/{execution_id}/costs")
async def get_execution_costs(
    execution_id: str,
    current_user: CurrentUser,
):
    """
    Get cost breakdown for an execution.

    Returns per-step costs and total execution cost.
    Reference: BACKLOG_ADVANCED.md - E11-01
    """
    execution_repo = get_execution_repo()

    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")

    execution = execution_repo.get_by_id(eid)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Build cost breakdown per step
    step_costs = []
    for step_id, step_exec in execution.step_executions.items():
        step_info = {
            "step_id": step_id,
            "status": step_exec.status.value,
            "cost": str(step_exec.cost) if step_exec.cost else None,
        }
        # Include token usage if available
        if step_exec.token_usage:
            step_info["token_usage"] = step_exec.token_usage.to_dict()
        step_costs.append(step_info)

    return {
        "execution_id": str(execution.id),
        "process_name": execution.process_name,
        "status": execution.status.value,
        "total_cost": str(execution.total_cost),
        "steps": step_costs,
    }


# =============================================================================
# Analytics Endpoints (E11-02)
# =============================================================================


@router.get("/analytics/steps")
async def get_step_analytics(
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    limit: int = Query(10, ge=1, le=50, description="Number of steps to return per category"),
):
    """
    Get step-level performance analytics.

    Returns slowest and most expensive steps across all processes.
    Reference: BACKLOG_ADVANCED.md - E11-02
    """
    from services.process_engine.services.analytics import ProcessAnalytics

    definition_repo = get_definition_repo()
    execution_repo = get_execution_repo()

    analytics = ProcessAnalytics(definition_repo, execution_repo)
    step_performance = analytics.get_step_performance(days=days, limit=limit)

    return step_performance.to_dict()


# =============================================================================
# Helper Functions
# =============================================================================


def _to_summary(execution: ProcessExecution) -> ExecutionSummary:
    """Convert execution to summary response."""
    return ExecutionSummary(
        id=str(execution.id),
        process_id=str(execution.process_id),
        process_name=execution.process_name,
        status=execution.status.value,
        triggered_by=execution.triggered_by,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        created_at=execution.started_at.isoformat() if execution.started_at else "",
        retry_of=str(execution.retry_of) if execution.retry_of else None,
    )


def _to_detail(
    execution: ProcessExecution,
    definition: Optional[ProcessDefinition] = None,
) -> ExecutionDetail:
    """Convert execution to detail response."""
    from services.process_engine.engine import DependencyResolver

    # Calculate parallel structure if definition available
    parallel_levels: dict[str, int] = {}
    has_parallel = False
    if definition:
        resolver = DependencyResolver(definition)
        parallel_structure = resolver.get_parallel_structure()
        parallel_levels = parallel_structure.step_levels
        has_parallel = parallel_structure.has_parallel_execution()

    # Build step type lookup from definition
    step_types: dict[str, str] = {}
    if definition:
        for step_def in definition.steps:
            step_types[str(step_def.id)] = step_def.type.value

    steps = []
    for step_id, step_exec in execution.step_executions.items():
        step_error = None
        if step_exec.error:
            if isinstance(step_exec.error, dict):
                step_error = StepError(
                    message=step_exec.error.get("message", "Unknown error"),
                    code=step_exec.error.get("code"),
                    attempt=step_exec.error.get("attempt"),
                    failed_at=step_exec.error.get("failed_at"),
                )
            else:
                step_error = StepError(message=str(step_exec.error))

        steps.append(StepExecutionSummary(
            step_id=step_id,
            status=step_exec.status.value,
            step_type=step_types.get(step_id),
            started_at=step_exec.started_at.isoformat() if step_exec.started_at else None,
            completed_at=step_exec.completed_at.isoformat() if step_exec.completed_at else None,
            error=step_error,
            retry_count=step_exec.retry_count,
            parallel_level=parallel_levels.get(step_id, 0),
            cost=str(step_exec.cost) if step_exec.cost else None,
        ))

    duration = None
    if execution.duration:
        duration = execution.duration.seconds

    return ExecutionDetail(
        id=str(execution.id),
        process_id=str(execution.process_id),
        process_version=str(execution.process_version),
        process_name=execution.process_name,
        status=execution.status.value,
        triggered_by=execution.triggered_by,
        input_data=execution.input_data,
        output_data=execution.output_data,
        total_cost=str(execution.total_cost) if execution.total_cost else None,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        duration_seconds=duration,
        steps=steps,
        has_parallel_steps=has_parallel,
        retry_of=str(execution.retry_of) if execution.retry_of else None,
        # Sub-process relationships
        parent_execution_id=str(execution.parent_execution_id) if execution.parent_execution_id else None,
        parent_step_id=str(execution.parent_step_id) if execution.parent_step_id else None,
        child_execution_ids=[str(cid) for cid in (execution.child_execution_ids or [])],
    )


# =============================================================================
# Recovery Status Endpoint
# =============================================================================


@router.get("/recovery/status")
async def get_recovery_status(current_user: CurrentUser):
    """
    Get the status of the last execution recovery scan.

    Useful for health checks and monitoring to verify recovery
    ran successfully after backend startup.

    Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-12
    """
    report = get_last_recovery_report()

    if report is None:
        return {
            "status": "not_run",
            "message": "Recovery has not run yet (backend may have just started)",
        }

    return {
        "status": "completed",
        "started_at": report.started_at.isoformat(),
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
        "duration_ms": report.duration_ms,
        "counts": {
            "resumed": len(report.resumed),
            "retried": len(report.retried),
            "failed": len(report.failed),
            "skipped": len(report.skipped),
            "errors": len(report.errors),
            "total": report.total_processed,
        },
        "has_errors": len(report.errors) > 0,
    }


# =============================================================================
# Execution Limits Endpoint (IT5 P1 - E19-01)
# =============================================================================


@router.get("/limits/status")
async def get_limits_status(current_user: CurrentUser):
    """
    Get current execution limits status.

    Returns global and per-process limits with current usage.
    Useful for monitoring capacity and troubleshooting 429 errors.

    Requires: ADMIN_VIEW_ALL permission
    """
    auth = get_auth_service()
    if not auth.is_admin(current_user):
        auth.log_authorization_failure(
            current_user, "limits.view", "limits", None, "Admin access required"
        )
        raise HTTPException(status_code=403, detail="Admin access required")

    limit_service = get_limit_service()
    return limit_service.get_limits_status()
