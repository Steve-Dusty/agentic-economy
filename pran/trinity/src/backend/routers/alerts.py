"""
Cost Alerts API Router

Provides REST API endpoints for managing cost thresholds and alerts.
Reference: BACKLOG_ADVANCED.md - E11-03

Part of the Process-Driven Platform feature.
"""

import logging
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dependencies import get_current_user, CurrentUser
from services.process_engine.services.alerts import (
    CostAlertService,
    ThresholdType,
    AlertStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ThresholdRequest(BaseModel):
    """Request body for setting a threshold."""
    threshold_type: str = Field(..., description="Type: per_execution, daily, weekly")
    amount: float = Field(..., gt=0, description="Threshold amount in USD")
    enabled: bool = Field(default=True)


class ThresholdResponse(BaseModel):
    """Response for a single threshold."""
    id: str
    process_id: str
    threshold_type: str
    threshold_amount: float
    currency: str
    enabled: bool
    created_at: str
    updated_at: str


class ThresholdSettingsResponse(BaseModel):
    """Response for all thresholds of a process."""
    process_id: str
    thresholds: List[ThresholdResponse]


class AlertResponse(BaseModel):
    """Response for a single alert."""
    id: str
    process_id: str
    process_name: str
    execution_id: Optional[str]
    threshold_type: str
    threshold_amount: float
    actual_amount: float
    currency: str
    severity: str
    status: str
    message: str
    created_at: str
    dismissed_at: Optional[str]
    dismissed_by: Optional[str]


class AlertListResponse(BaseModel):
    """Response for listing alerts."""
    alerts: List[AlertResponse]
    total: int
    active_count: int


# =============================================================================
# Service Instance
# =============================================================================


_alert_service: Optional[CostAlertService] = None


def get_alert_service() -> CostAlertService:
    """Get or create the alert service."""
    global _alert_service
    if _alert_service is None:
        _alert_service = CostAlertService()
    return _alert_service


# =============================================================================
# Alert Endpoints
# =============================================================================


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="Filter by status (active, dismissed)"),
    process_id: Optional[str] = Query(None, description="Filter by process ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List cost alerts.

    Returns alerts sorted by creation date (newest first).
    """
    service = get_alert_service()

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = AlertStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    alerts = service.get_alerts(
        status=status_filter,
        process_id=process_id,
        limit=limit,
        offset=offset,
    )
    active_count = service.get_active_alerts_count()

    return AlertListResponse(
        alerts=[AlertResponse(**a.to_dict()) for a in alerts],
        total=len(alerts),
        active_count=active_count,
    )


# NOTE: Static routes (/count, /thresholds) must be defined BEFORE /{alert_id} to avoid route conflict
@router.get("/count")
async def get_alerts_count(
    current_user: CurrentUser,
):
    """
    Get count of active alerts.

    Useful for notification badges.
    """
    service = get_alert_service()
    count = service.get_active_alerts_count()
    return {"active_count": count}


@router.get("/thresholds/{process_id}", response_model=ThresholdSettingsResponse)
async def get_process_thresholds(
    process_id: str,
    current_user: CurrentUser,
):
    """
    Get all cost thresholds for a process.
    """
    service = get_alert_service()
    thresholds = service.get_thresholds(process_id)

    return ThresholdSettingsResponse(
        process_id=process_id,
        thresholds=[
            ThresholdResponse(**t.to_dict())
            for t in thresholds
        ],
    )


@router.put("/thresholds/{process_id}")
async def set_process_threshold(
    process_id: str,
    request: ThresholdRequest,
    current_user: CurrentUser,
):
    """
    Set or update a threshold for a process.
    """
    service = get_alert_service()

    try:
        threshold_type = ThresholdType(request.threshold_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid threshold type: {request.threshold_type}. Valid: per_execution, daily, weekly"
        )

    threshold = service.set_threshold(
        process_id=process_id,
        threshold_type=threshold_type,
        amount=Decimal(str(request.amount)),
        enabled=request.enabled,
    )

    logger.info(f"Threshold set for process {process_id}: {threshold_type.value} = ${request.amount}")

    return {
        "message": "Threshold updated",
        "threshold": ThresholdResponse(**threshold.to_dict()),
    }


@router.delete("/thresholds/{process_id}/{threshold_type}")
async def delete_process_threshold(
    process_id: str,
    threshold_type: str,
    current_user: CurrentUser,
):
    """
    Delete a threshold for a process.
    """
    service = get_alert_service()

    try:
        tt = ThresholdType(threshold_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid threshold type: {threshold_type}"
        )

    success = service.delete_threshold(process_id, tt)

    if not success:
        raise HTTPException(status_code=404, detail="Threshold not found")

    logger.info(f"Threshold deleted for process {process_id}: {threshold_type}")
    return {"message": "Threshold deleted"}


# Dynamic route - must come AFTER static routes
@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user: CurrentUser,
):
    """
    Get a single alert by ID.
    """
    service = get_alert_service()
    alert = service.get_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertResponse(**alert.to_dict())


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    current_user: CurrentUser,
):
    """
    Dismiss an alert.
    """
    service = get_alert_service()

    alert = service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == AlertStatus.DISMISSED:
        raise HTTPException(status_code=400, detail="Alert already dismissed")

    success = service.dismiss_alert(alert_id, dismissed_by=current_user.email)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to dismiss alert")

    logger.info(f"Alert {alert_id} dismissed by {current_user.email}")
    return {"message": "Alert dismissed", "alert_id": alert_id}
