"""
Approvals API Router

Provides endpoints for managing human approval requests.

Reference: BACKLOG_CORE.md - E6-03
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from services.process_engine.engine import get_approval_store
from services.process_engine.domain import ApprovalRequest, ApprovalStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


# =============================================================================
# Schemas
# =============================================================================


class ApprovalSummary(BaseModel):
    """Summary of an approval request."""
    id: str
    execution_id: str
    step_id: str
    title: str
    description: str
    status: str
    assignees: list[str]
    created_at: str
    deadline: Optional[str] = None


class ApprovalDetail(ApprovalSummary):
    """Detailed approval request."""
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    decision_comment: Optional[str] = None


class ApproveRequest(BaseModel):
    """Request body for approving."""
    comment: Optional[str] = None


class RejectRequest(BaseModel):
    """Request body for rejecting."""
    comment: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=list[ApprovalSummary])
async def list_approvals(
    status: Optional[str] = None,
    user: Optional[str] = None,
):
    """
    List approval requests.
    
    Args:
        status: Filter by status (pending, approved, rejected, expired)
        user: Filter by assignee
    """
    store = get_approval_store()
    
    if status == "pending":
        if user:
            requests = store.get_pending_for_user(user)
        else:
            requests = store.get_all_pending()
    else:
        # Get all and filter
        requests = list(store._requests.values())
        if status:
            requests = [r for r in requests if r.status.value == status]
        if user:
            requests = [r for r in requests if r.can_be_decided_by(user)]
    
    return [_to_summary(r) for r in requests]


@router.get("/{approval_id}", response_model=ApprovalDetail)
async def get_approval(approval_id: str):
    """Get approval request details."""
    store = get_approval_store()
    request = store.get(approval_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    return _to_detail(request)


@router.get("/execution/{execution_id}/step/{step_id}", response_model=ApprovalDetail)
async def get_approval_by_step(execution_id: str, step_id: str):
    """Get approval request for a specific execution step."""
    store = get_approval_store()
    request = store.get_by_execution_step(execution_id, step_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Approval not found for this step")
    
    return _to_detail(request)


@router.post("/{approval_id}/approve", response_model=ApprovalDetail)
async def approve(approval_id: str, body: ApproveRequest):
    """
    Approve a request.
    
    This will mark the approval as approved and resume
    the paused execution.
    """
    from routers.executions import get_execution_engine, get_execution_repo
    from routers.processes import get_repository as get_process_repo
    
    store = get_approval_store()
    request = store.get(approval_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if not request.is_pending():
        raise HTTPException(
            status_code=400, 
            detail=f"Approval already decided: {request.status.value}"
        )
    
    # TODO: Get actual user from auth context
    decided_by = "admin"
    
    request.approve(decided_by=decided_by, comment=body.comment)
    store.save(request)
    
    logger.info(f"Approval {approval_id} approved by {decided_by}")
    
    # Resume the execution
    try:
        from services.process_engine.domain import ExecutionId, ProcessId
        execution_repo = get_execution_repo()
        process_repo = get_process_repo()
        
        execution = execution_repo.get_by_id(ExecutionId(request.execution_id))
        if execution:
            definition = process_repo.get_by_id(ProcessId(str(execution.process_id)))
            if definition:
                engine = get_execution_engine()
                # Run resume in background task
                import asyncio
                asyncio.create_task(engine.resume(execution, definition))
                logger.info(f"Resuming execution {request.execution_id} after approval")
    except Exception as e:
        logger.error(f"Failed to resume execution: {e}")
    
    return _to_detail(request)


@router.post("/{approval_id}/reject", response_model=ApprovalDetail)
async def reject(approval_id: str, body: RejectRequest):
    """
    Reject a request.
    
    This will mark the approval as rejected and resume
    the execution (which will fail the step).
    """
    from routers.executions import get_execution_engine, get_execution_repo
    from routers.processes import get_repository as get_process_repo
    
    store = get_approval_store()
    request = store.get(approval_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if not request.is_pending():
        raise HTTPException(
            status_code=400, 
            detail=f"Approval already decided: {request.status.value}"
        )
    
    # TODO: Get actual user from auth context
    decided_by = "admin"
    
    request.reject(decided_by=decided_by, comment=body.comment)
    store.save(request)
    
    logger.info(f"Approval {approval_id} rejected by {decided_by}")
    
    # Resume the execution (it will fail the step when re-executed)
    try:
        from services.process_engine.domain import ExecutionId, ProcessId
        execution_repo = get_execution_repo()
        process_repo = get_process_repo()
        
        execution = execution_repo.get_by_id(ExecutionId(request.execution_id))
        if execution:
            definition = process_repo.get_by_id(ProcessId(str(execution.process_id)))
            if definition:
                engine = get_execution_engine()
                # Run resume in background task
                import asyncio
                asyncio.create_task(engine.resume(execution, definition))
                logger.info(f"Resuming execution {request.execution_id} after rejection")
    except Exception as e:
        logger.error(f"Failed to resume execution: {e}")
    
    return _to_detail(request)


# =============================================================================
# Helpers
# =============================================================================


def _to_summary(request: ApprovalRequest) -> ApprovalSummary:
    """Convert to summary."""
    return ApprovalSummary(
        id=request.id,
        execution_id=request.execution_id,
        step_id=request.step_id,
        title=request.title,
        description=request.description,
        status=request.status.value,
        assignees=request.assignees,
        created_at=request.created_at.isoformat(),
        deadline=request.deadline.isoformat() if request.deadline else None,
    )


def _to_detail(request: ApprovalRequest) -> ApprovalDetail:
    """Convert to detail."""
    return ApprovalDetail(
        id=request.id,
        execution_id=request.execution_id,
        step_id=request.step_id,
        title=request.title,
        description=request.description,
        status=request.status.value,
        assignees=request.assignees,
        created_at=request.created_at.isoformat(),
        deadline=request.deadline.isoformat() if request.deadline else None,
        decided_at=request.decided_at.isoformat() if request.decided_at else None,
        decided_by=request.decided_by,
        decision_comment=request.decision_comment,
    )
