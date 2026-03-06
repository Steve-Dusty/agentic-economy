"""
Internal endpoints (no authentication required).

These endpoints are called by:
- Agent containers on the Docker network to communicate back to the backend
- Dedicated scheduler service (trinity-scheduler) for activity tracking

They are not exposed externally.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import logging

from models import ActivityType
from services.activity_service import activity_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
)


@router.get("/health")
async def internal_health():
    """Internal health check for agent containers."""
    return {"status": "ok"}


# =============================================================================
# Activity Tracking Endpoints (for dedicated scheduler)
# =============================================================================

class ActivityTrackRequest(BaseModel):
    """Request model for tracking activity start."""
    agent_name: str
    activity_type: str  # e.g., "schedule_start"
    user_id: Optional[int] = None
    triggered_by: str = "schedule"  # schedule, manual, user, agent, system
    related_execution_id: Optional[str] = None
    details: Optional[Dict] = None


class ActivityCompleteRequest(BaseModel):
    """Request model for completing an activity."""
    status: str = "completed"  # completed, failed
    details: Optional[Dict] = None
    error: Optional[str] = None


@router.post("/activities/track")
async def track_activity(request: ActivityTrackRequest):
    """
    Track the start of a new activity.

    Called by the dedicated scheduler when a cron-triggered execution starts.
    Creates an activity record and broadcasts via WebSocket.

    Returns:
        activity_id: UUID of the created activity
    """
    try:
        # Map string to ActivityType enum
        activity_type_map = {
            "schedule_start": ActivityType.SCHEDULE_START,
            "schedule_end": ActivityType.SCHEDULE_END,
            "chat_start": ActivityType.CHAT_START,
            "chat_end": ActivityType.CHAT_END,
            "agent_collaboration": ActivityType.AGENT_COLLABORATION,
        }

        activity_type = activity_type_map.get(request.activity_type)
        if not activity_type:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid activity_type: {request.activity_type}"
            )

        activity_id = await activity_service.track_activity(
            agent_name=request.agent_name,
            activity_type=activity_type,
            user_id=request.user_id,
            triggered_by=request.triggered_by,
            related_execution_id=request.related_execution_id,
            details=request.details
        )

        logger.info(f"Activity tracked: {activity_id} for agent {request.agent_name} ({request.activity_type})")

        return {
            "activity_id": activity_id,
            "agent_name": request.agent_name,
            "activity_type": request.activity_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activities/{activity_id}/complete")
async def complete_activity(activity_id: str, request: ActivityCompleteRequest):
    """
    Mark an activity as completed or failed.

    Called by the dedicated scheduler when an execution completes.
    Updates the activity record and broadcasts via WebSocket.
    """
    try:
        success = await activity_service.complete_activity(
            activity_id=activity_id,
            status=request.status,
            details=request.details,
            error=request.error
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Activity not found: {activity_id}"
            )

        logger.info(f"Activity completed: {activity_id} ({request.status})")

        return {
            "activity_id": activity_id,
            "status": request.status,
            "completed": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
