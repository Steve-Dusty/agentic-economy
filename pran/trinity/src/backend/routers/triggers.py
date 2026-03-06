"""
Trigger Endpoints

Handles webhook and schedule triggers for starting process executions.

Reference: BACKLOG_CORE.md - E8-02, BACKLOG_ADVANCED.md - E9-02
"""

import logging
import hmac
import sqlite3
import os
from typing import Optional, List
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

from services.process_engine.domain import (
    WebhookTriggerConfig,
    ScheduleTriggerConfig,
    ProcessDefinition,
    DefinitionStatus,
    expand_cron_preset,
)

# Reuse centralized repository and engine instances
from routers.processes import get_repository as get_process_repo
from routers.executions import get_execution_engine


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/triggers", tags=["triggers"])


# =============================================================================
# Schemas
# =============================================================================


class TriggerResponse(BaseModel):
    """Response from a trigger invocation."""
    execution_id: str
    process_name: str
    status: str
    message: str


class TriggerInfo(BaseModel):
    """Information about a trigger."""
    id: str
    type: str
    process_name: str
    process_id: str
    enabled: bool
    webhook_url: str
    description: str


class ScheduleTriggerInfo(BaseModel):
    """Information about a schedule trigger."""
    id: str
    type: str = "schedule"
    process_name: str
    process_id: str
    trigger_id: str
    cron: str
    cron_expression: str
    timezone: str
    enabled: bool
    description: str
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def _find_trigger(trigger_id: str) -> tuple[Optional[ProcessDefinition], Optional[WebhookTriggerConfig]]:
    """
    Find a webhook trigger by ID across all published processes.

    Returns:
        Tuple of (ProcessDefinition, WebhookTriggerConfig) if found, (None, None) otherwise.
    """
    repo = get_process_repo()

    # Use proper repository method to get published processes
    published_processes = repo.list_all(status=DefinitionStatus.PUBLISHED)

    for process in published_processes:
        for trigger in process.triggers:
            if isinstance(trigger, WebhookTriggerConfig) and trigger.id == trigger_id:
                return process, trigger

    return None, None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=list[TriggerInfo])
async def list_triggers(request: Request):
    """
    List all webhook triggers across all processes.

    Returns a list of all configured triggers with their webhook URLs.
    """
    repo = get_process_repo()
    triggers = []

    # Use proper repository method to get published processes
    published_processes = repo.list_all(status=DefinitionStatus.PUBLISHED)

    for process in published_processes:
        for trigger in process.triggers:
            if isinstance(trigger, WebhookTriggerConfig):
                base_url = str(request.base_url).rstrip('/')
                webhook_url = f"{base_url}/api/triggers/webhook/{trigger.id}"
                triggers.append(TriggerInfo(
                    id=trigger.id,
                    type="webhook",
                    process_name=process.name,
                    process_id=str(process.id),
                    enabled=trigger.enabled,
                    webhook_url=webhook_url,
                    description=trigger.description,
                ))

    return triggers


@router.post("/webhook/{trigger_id}", response_model=TriggerResponse)
async def invoke_webhook(
    trigger_id: str,
    request: Request,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    """
    Invoke a webhook trigger to start a process execution.

    The trigger_id must match a configured webhook trigger in a published process.
    The request body (JSON) will be available as `trigger.payload` in the process.

    Optional authentication via X-Webhook-Secret header if the trigger has a secret.
    """
    # Find the trigger and its process
    process, trigger = _find_trigger(trigger_id)

    if not process or not trigger:
        raise HTTPException(status_code=404, detail=f"Trigger not found: {trigger_id}")

    if not trigger.enabled:
        raise HTTPException(status_code=403, detail="Trigger is disabled")

    # Verify secret if configured
    if trigger.secret:
        if not x_webhook_secret:
            raise HTTPException(status_code=401, detail="Webhook secret required")

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(trigger.secret, x_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Parse request body as trigger payload
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Build input data with trigger context
    input_data = {
        "trigger": {
            "type": "webhook",
            "id": trigger_id,
            "payload": body,
        },
        **body,  # Also include body at top level for convenience
    }

    # Create and start execution using centralized engine
    engine = get_execution_engine()

    try:
        execution = await engine.start(
            definition=process,
            input_data=input_data,
            triggered_by="webhook",
        )

        logger.info(f"Webhook trigger '{trigger_id}' started execution {execution.id} for process '{process.name}'")

        return TriggerResponse(
            execution_id=str(execution.id),
            process_name=process.name,
            status=execution.status.value,
            message=f"Execution started successfully via webhook trigger",
        )

    except Exception as e:
        logger.error(f"Failed to start execution via webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.get("/webhook/{trigger_id}/info", response_model=TriggerInfo)
async def get_trigger_info(trigger_id: str, request: Request):
    """
    Get information about a specific webhook trigger.
    """
    process, trigger = _find_trigger(trigger_id)

    if not process or not trigger:
        raise HTTPException(status_code=404, detail=f"Trigger not found: {trigger_id}")

    base_url = str(request.base_url).rstrip('/')
    return TriggerInfo(
        id=trigger.id,
        type="webhook",
        process_name=process.name,
        process_id=str(process.id),
        enabled=trigger.enabled,
        webhook_url=f"{base_url}/api/triggers/webhook/{trigger.id}",
        description=trigger.description,
    )


# =============================================================================
# Schedule Trigger Endpoints
# =============================================================================


def _get_scheduler_db_path() -> str:
    """Get the path to the main Trinity database used by scheduler."""
    return os.getenv("TRINITY_DB_PATH", str(Path.home() / "trinity-data" / "trinity.db"))


def _get_schedule_triggers_from_db() -> List[dict]:
    """Get all schedule triggers from the database."""
    db_path = _get_scheduler_db_path()
    schedules = []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM process_schedules
            ORDER BY process_name, trigger_id
        """)

        for row in cursor.fetchall():
            schedules.append(dict(row))

        conn.close()
    except Exception as e:
        logger.warning(f"Failed to get schedule triggers from database: {e}")

    return schedules


@router.get("/schedules", response_model=List[ScheduleTriggerInfo])
async def list_schedule_triggers():
    """
    List all schedule triggers across all processes.

    Returns a list of all configured schedule triggers with their next run times.
    """
    repo = get_process_repo()
    triggers = []

    # Get schedule triggers from process definitions
    published_processes = repo.list_all(status=DefinitionStatus.PUBLISHED)

    # Get runtime info from database
    db_schedules = {
        f"{s['process_id']}:{s['trigger_id']}": s
        for s in _get_schedule_triggers_from_db()
    }

    for process in published_processes:
        for trigger in process.triggers:
            if isinstance(trigger, ScheduleTriggerConfig):
                # Get runtime info if available
                key = f"{process.id}:{trigger.id}"
                db_info = db_schedules.get(key, {})

                triggers.append(ScheduleTriggerInfo(
                    id=db_info.get("id", trigger.id),
                    type="schedule",
                    process_name=process.name,
                    process_id=str(process.id),
                    trigger_id=trigger.id,
                    cron=trigger.cron,
                    cron_expression=trigger.cron_expression,
                    timezone=trigger.timezone,
                    enabled=trigger.enabled,
                    description=trigger.description,
                    next_run_at=db_info.get("next_run_at"),
                    last_run_at=db_info.get("last_run_at"),
                ))

    return triggers


@router.get("/schedules/{schedule_id}", response_model=ScheduleTriggerInfo)
async def get_schedule_trigger(schedule_id: str):
    """
    Get information about a specific schedule trigger.
    """
    db_schedules = _get_schedule_triggers_from_db()

    # Find by ID
    schedule = None
    for s in db_schedules:
        if s.get("id") == schedule_id:
            schedule = s
            break

    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule trigger not found: {schedule_id}")

    # Get the trigger config from the process definition for additional info
    repo = get_process_repo()
    try:
        from services.process_engine.domain import ProcessId
        process = repo.get_by_id(ProcessId(schedule["process_id"]))

        trigger_config = None
        if process:
            for t in process.triggers:
                if isinstance(t, ScheduleTriggerConfig) and t.id == schedule["trigger_id"]:
                    trigger_config = t
                    break
    except Exception:
        process = None
        trigger_config = None

    return ScheduleTriggerInfo(
        id=schedule["id"],
        type="schedule",
        process_name=schedule["process_name"],
        process_id=schedule["process_id"],
        trigger_id=schedule["trigger_id"],
        cron=trigger_config.cron if trigger_config else schedule["cron_expression"],
        cron_expression=schedule["cron_expression"],
        timezone=schedule["timezone"],
        enabled=bool(schedule["enabled"]),
        description=schedule.get("description", ""),
        next_run_at=schedule.get("next_run_at"),
        last_run_at=schedule.get("last_run_at"),
    )


@router.get("/process/{process_id}/schedules", response_model=List[ScheduleTriggerInfo])
async def list_process_schedule_triggers(process_id: str):
    """
    List all schedule triggers for a specific process.
    """
    repo = get_process_repo()

    try:
        from services.process_engine.domain import ProcessId
        pid = ProcessId(process_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid process ID format")

    process = repo.get_by_id(pid)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    # Get runtime info from database
    db_schedules = {
        s["trigger_id"]: s
        for s in _get_schedule_triggers_from_db()
        if s.get("process_id") == process_id
    }

    triggers = []
    for trigger in process.triggers:
        if isinstance(trigger, ScheduleTriggerConfig):
            db_info = db_schedules.get(trigger.id, {})

            triggers.append(ScheduleTriggerInfo(
                id=db_info.get("id", trigger.id),
                type="schedule",
                process_name=process.name,
                process_id=str(process.id),
                trigger_id=trigger.id,
                cron=trigger.cron,
                cron_expression=trigger.cron_expression,
                timezone=trigger.timezone,
                enabled=trigger.enabled,
                description=trigger.description,
                next_run_at=db_info.get("next_run_at"),
                last_run_at=db_info.get("last_run_at"),
            ))

    return triggers
