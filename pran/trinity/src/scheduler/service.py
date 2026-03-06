"""
Core scheduler service for Trinity platform.

Manages scheduled task execution for agents using APScheduler.
Uses distributed locks to prevent duplicate executions.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Optional, List, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.events import EVENT_JOB_MAX_INSTANCES, JobExecutionEvent
from croniter import croniter
import pytz
import redis

import httpx

from .config import config
from .models import Schedule, ScheduleExecution, SchedulerStatus, ProcessSchedule
from .database import SchedulerDatabase
from .agent_client import get_agent_client, AgentNotReachableError, AgentRequestError
from .locking import get_lock_manager, LockManager

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Manages scheduled task execution for agents.

    Key features:
    - APScheduler with AsyncIO for non-blocking execution
    - Distributed locking to prevent duplicate executions
    - Event publishing for WebSocket compatibility
    - Periodic sync to detect new/updated/deleted schedules
    """

    def __init__(
        self,
        database: SchedulerDatabase = None,
        lock_manager: LockManager = None,
        redis_url: str = None
    ):
        """
        Initialize the scheduler service.

        Args:
            database: Database access instance
            lock_manager: Distributed lock manager
            redis_url: Redis URL for event publishing
        """
        self.db = database or SchedulerDatabase()
        self.lock_manager = lock_manager or get_lock_manager()
        self.redis_url = redis_url or config.redis_url

        self.scheduler: Optional[AsyncIOScheduler] = None
        self._redis: Optional[redis.Redis] = None
        self._initialized = False
        self._start_time: Optional[datetime] = None
        self._instance_id: str = f"scheduler-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Schedule state snapshots for sync detection
        # Maps schedule_id -> (enabled, updated_at_iso)
        self._schedule_snapshot: Dict[str, tuple] = {}
        self._process_schedule_snapshot: Dict[str, tuple] = {}

    @property
    def redis(self) -> redis.Redis:
        """Get or create Redis connection for events."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def initialize(self):
        """Initialize the scheduler and load all enabled schedules."""
        if self._initialized:
            logger.warning("Scheduler already initialized")
            return

        # Ensure process schedules table exists
        self.db.ensure_process_schedules_table()

        # Create scheduler with memory job store
        jobstores = {
            'default': MemoryJobStore()
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone=pytz.UTC
        )

        # Load all enabled agent schedules from database
        schedules = self.db.list_all_enabled_schedules()
        for schedule in schedules:
            self._add_job(schedule)
            # Capture snapshot for sync detection
            self._schedule_snapshot[schedule.id] = (
                schedule.enabled,
                schedule.updated_at.isoformat() if schedule.updated_at else None
            )

        # Load all enabled process schedules from database
        process_schedules = self.db.list_all_enabled_process_schedules()
        for process_schedule in process_schedules:
            self._add_process_job(process_schedule)
            # Capture snapshot for sync detection
            self._process_schedule_snapshot[process_schedule.id] = (
                process_schedule.enabled,
                process_schedule.updated_at.isoformat() if process_schedule.updated_at else None
            )

        # Add listener for skipped executions (max_instances reached)
        # This records when a scheduled job is dropped because previous execution is still running
        self.scheduler.add_listener(
            self._on_job_max_instances,
            EVENT_JOB_MAX_INSTANCES
        )

        # Start the scheduler
        self.scheduler.start()
        self._initialized = True
        self._start_time = datetime.utcnow()

        logger.info(f"Scheduler initialized with {len(schedules)} agent schedules, {len(process_schedules)} process schedules")
        logger.info(f"Instance ID: {self._instance_id}")
        logger.info(f"Schedule sync interval: {config.schedule_reload_interval}s")

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self._initialized = False
            logger.info("Scheduler shutdown")

        if self._redis:
            self._redis.close()
            self._redis = None

        self.lock_manager.close()

    async def run_forever(self):
        """Run the scheduler until interrupted."""
        self.initialize()

        sync_interval = config.schedule_reload_interval
        heartbeat_interval = 30
        last_sync = datetime.utcnow()

        try:
            # Keep the service running with periodic heartbeat and sync
            while True:
                self.lock_manager.set_heartbeat(self._instance_id)

                # Check if it's time to sync schedules
                now = datetime.utcnow()
                if (now - last_sync).total_seconds() >= sync_interval:
                    await self._sync_schedules()
                    last_sync = now

                await asyncio.sleep(heartbeat_interval)
        except asyncio.CancelledError:
            logger.info("Scheduler received cancel signal")
        finally:
            self.shutdown()

    # =========================================================================
    # Job Management
    # =========================================================================

    def _get_job_id(self, schedule_id: str) -> str:
        """Generate a unique job ID for APScheduler."""
        return f"schedule_{schedule_id}"

    def _parse_cron(self, cron_expression: str) -> Dict:
        """
        Parse a cron expression into APScheduler CronTrigger kwargs.

        Format: minute hour day month day_of_week
        Examples:
          - "0 9 * * *" = Every day at 9:00 AM
          - "*/15 * * * *" = Every 15 minutes
          - "0 0 * * 0" = Every Sunday at midnight
        """
        parts = cron_expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}. Expected 5 parts.")

        return {
            'minute': parts[0],
            'hour': parts[1],
            'day': parts[2],
            'month': parts[3],
            'day_of_week': parts[4]
        }

    def _add_job(self, schedule: Schedule):
        """Add a schedule as an APScheduler job."""
        if not self.scheduler:
            return

        job_id = self._get_job_id(schedule.id)

        try:
            # Parse cron expression
            cron_kwargs = self._parse_cron(schedule.cron_expression)

            # Create timezone-aware trigger
            timezone = pytz.timezone(schedule.timezone) if schedule.timezone else pytz.UTC
            trigger = CronTrigger(timezone=timezone, **cron_kwargs)

            # Add the job
            self.scheduler.add_job(
                self._execute_schedule,
                trigger=trigger,
                id=job_id,
                args=[schedule.id],
                replace_existing=True,
                name=f"{schedule.agent_name}:{schedule.name}"
            )

            # Calculate and store next run time
            next_run = self._get_next_run_time(schedule.cron_expression, schedule.timezone)
            if next_run:
                self.db.update_schedule_run_times(schedule.id, next_run_at=next_run)

            logger.info(f"Added schedule job: {job_id} ({schedule.name}) for agent {schedule.agent_name}")
        except Exception as e:
            logger.error(f"Failed to add schedule job {job_id}: {e}")

    def _remove_job(self, schedule_id: str):
        """Remove a schedule job from APScheduler."""
        if not self.scheduler:
            return

        job_id = self._get_job_id(schedule_id)
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed schedule job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to remove schedule job {job_id}: {e}")

    def _get_next_run_time(self, cron_expression: str, timezone: str = "UTC") -> Optional[datetime]:
        """Calculate the next run time for a cron expression."""
        try:
            tz = pytz.timezone(timezone) if timezone else pytz.UTC
            now = datetime.now(tz)
            cron = croniter(cron_expression, now)
            next_time = cron.get_next(datetime)
            return next_time
        except Exception as e:
            logger.error(f"Failed to calculate next run time: {e}")
            return None

    # =========================================================================
    # Schedule Sync (detect new/updated/deleted schedules)
    # =========================================================================

    async def _sync_schedules(self):
        """
        Sync in-memory APScheduler jobs with database schedules.

        This is called periodically to detect:
        - New schedules created since last sync
        - Deleted schedules
        - Updated schedules (cron, timezone, enabled status changed)

        This allows new schedules to work without restarting the scheduler container.
        """
        try:
            await self._sync_agent_schedules()
            await self._sync_process_schedules()
        except Exception as e:
            logger.error(f"Schedule sync failed: {e}")

    async def _sync_agent_schedules(self):
        """Sync agent schedules with database."""
        # Get all schedules from database (enabled and disabled)
        all_schedules = self.db.list_all_schedules()

        # Build current state map
        current_state: Dict[str, tuple] = {}
        schedule_map: Dict[str, Schedule] = {}
        for schedule in all_schedules:
            current_state[schedule.id] = (
                schedule.enabled,
                schedule.updated_at.isoformat() if schedule.updated_at else None
            )
            schedule_map[schedule.id] = schedule

        # Detect changes
        snapshot_ids = set(self._schedule_snapshot.keys())
        current_ids = set(current_state.keys())

        # New schedules (in database but not in snapshot)
        new_ids = current_ids - snapshot_ids
        for schedule_id in new_ids:
            schedule = schedule_map[schedule_id]
            if schedule.enabled:
                logger.info(f"Sync: Adding new schedule {schedule.name} for agent {schedule.agent_name}")
                self._add_job(schedule)
            self._schedule_snapshot[schedule_id] = current_state[schedule_id]

        # Deleted schedules (in snapshot but not in database)
        deleted_ids = snapshot_ids - current_ids
        for schedule_id in deleted_ids:
            logger.info(f"Sync: Removing deleted schedule {schedule_id}")
            self._remove_job(schedule_id)
            del self._schedule_snapshot[schedule_id]

        # Updated schedules (still exists but state changed)
        for schedule_id in (snapshot_ids & current_ids):
            old_state = self._schedule_snapshot[schedule_id]
            new_state = current_state[schedule_id]

            if old_state != new_state:
                schedule = schedule_map[schedule_id]
                old_enabled, old_updated = old_state
                new_enabled, new_updated = new_state

                if old_enabled and not new_enabled:
                    # Schedule was disabled
                    logger.info(f"Sync: Disabling schedule {schedule.name}")
                    self._remove_job(schedule_id)
                elif not old_enabled and new_enabled:
                    # Schedule was enabled
                    logger.info(f"Sync: Enabling schedule {schedule.name}")
                    self._add_job(schedule)
                elif new_enabled and old_updated != new_updated:
                    # Schedule was updated (and still enabled)
                    logger.info(f"Sync: Updating schedule {schedule.name}")
                    self._remove_job(schedule_id)
                    self._add_job(schedule)

                self._schedule_snapshot[schedule_id] = new_state

        if new_ids or deleted_ids:
            logger.info(f"Sync complete: {len(new_ids)} added, {len(deleted_ids)} removed")

    async def _sync_process_schedules(self):
        """Sync process schedules with database."""
        # Get all process schedules from database
        all_schedules = self.db.list_all_process_schedules()

        # Build current state map
        current_state: Dict[str, tuple] = {}
        schedule_map: Dict[str, ProcessSchedule] = {}
        for schedule in all_schedules:
            current_state[schedule.id] = (
                schedule.enabled,
                schedule.updated_at.isoformat() if schedule.updated_at else None
            )
            schedule_map[schedule.id] = schedule

        # Detect changes
        snapshot_ids = set(self._process_schedule_snapshot.keys())
        current_ids = set(current_state.keys())

        # New schedules
        new_ids = current_ids - snapshot_ids
        for schedule_id in new_ids:
            schedule = schedule_map[schedule_id]
            if schedule.enabled:
                logger.info(f"Sync: Adding new process schedule {schedule.process_name}/{schedule.trigger_id}")
                self._add_process_job(schedule)
            self._process_schedule_snapshot[schedule_id] = current_state[schedule_id]

        # Deleted schedules
        deleted_ids = snapshot_ids - current_ids
        for schedule_id in deleted_ids:
            logger.info(f"Sync: Removing deleted process schedule {schedule_id}")
            self._remove_process_job(schedule_id)
            del self._process_schedule_snapshot[schedule_id]

        # Updated schedules
        for schedule_id in (snapshot_ids & current_ids):
            old_state = self._process_schedule_snapshot[schedule_id]
            new_state = current_state[schedule_id]

            if old_state != new_state:
                schedule = schedule_map[schedule_id]
                old_enabled, old_updated = old_state
                new_enabled, new_updated = new_state

                if old_enabled and not new_enabled:
                    logger.info(f"Sync: Disabling process schedule {schedule.process_name}/{schedule.trigger_id}")
                    self._remove_process_job(schedule_id)
                elif not old_enabled and new_enabled:
                    logger.info(f"Sync: Enabling process schedule {schedule.process_name}/{schedule.trigger_id}")
                    self._add_process_job(schedule)
                elif new_enabled and old_updated != new_updated:
                    logger.info(f"Sync: Updating process schedule {schedule.process_name}/{schedule.trigger_id}")
                    self._remove_process_job(schedule_id)
                    self._add_process_job(schedule)

                self._process_schedule_snapshot[schedule_id] = new_state

    # =========================================================================
    # Skipped Execution Tracking (Issue #46)
    # =========================================================================

    def _on_job_max_instances(self, event: JobExecutionEvent):
        """
        Handle EVENT_JOB_MAX_INSTANCES - triggered when a job is skipped because
        the previous execution is still running (max_instances=1 reached).

        This ensures we have an audit trail for skipped scheduled executions
        instead of silently dropping them with only a log warning.

        Args:
            event: APScheduler JobExecutionEvent with job_id
        """
        job_id = event.job_id
        logger.warning(f"Job {job_id} skipped: previous execution still running (max_instances reached)")

        # Extract schedule_id from job_id (format: "schedule_{schedule_id}" or "process_schedule_{schedule_id}")
        if job_id.startswith("schedule_"):
            schedule_id = job_id[len("schedule_"):]
            self._record_skipped_agent_schedule(schedule_id)
        elif job_id.startswith("process_schedule_"):
            schedule_id = job_id[len("process_schedule_"):]
            self._record_skipped_process_schedule(schedule_id)
        else:
            logger.warning(f"Unknown job_id format for skipped job: {job_id}")

    def _record_skipped_agent_schedule(self, schedule_id: str):
        """
        Record a skipped agent schedule execution in the database.

        Creates an execution record with status='skipped' so it appears in
        the execution history and provides an audit trail.
        """
        try:
            schedule = self.db.get_schedule(schedule_id)
            if not schedule:
                logger.error(f"Cannot record skipped execution: schedule {schedule_id} not found")
                return

            # Create execution record with 'skipped' status
            execution = self.db.create_skipped_execution(
                schedule_id=schedule.id,
                agent_name=schedule.agent_name,
                message=schedule.message,
                triggered_by="schedule",
                skip_reason="Previous execution still running (max_instances reached)"
            )

            if execution:
                logger.info(f"Recorded skipped execution {execution.id} for schedule {schedule.name}")

                # Publish event for WebSocket notification
                asyncio.create_task(self._publish_event({
                    "type": "schedule_execution_skipped",
                    "agent": schedule.agent_name,
                    "schedule_id": schedule.id,
                    "execution_id": execution.id,
                    "schedule_name": schedule.name,
                    "reason": "Previous execution still running"
                }))
            else:
                logger.error(f"Failed to create skipped execution record for schedule {schedule_id}")

        except Exception as e:
            logger.error(f"Error recording skipped execution for schedule {schedule_id}: {e}")

    def _record_skipped_process_schedule(self, schedule_id: str):
        """
        Record a skipped process schedule execution in the database.

        Creates an execution record with status='skipped' so it appears in
        the execution history and provides an audit trail.
        """
        try:
            schedule = self.db.get_process_schedule(schedule_id)
            if not schedule:
                logger.error(f"Cannot record skipped execution: process schedule {schedule_id} not found")
                return

            # Create execution record with 'skipped' status
            execution = self.db.create_skipped_process_schedule_execution(
                schedule_id=schedule.id,
                process_id=schedule.process_id,
                process_name=schedule.process_name,
                triggered_by="schedule",
                skip_reason="Previous execution still running (max_instances reached)"
            )

            if execution:
                logger.info(f"Recorded skipped process execution {execution.id} for {schedule.process_name}/{schedule.trigger_id}")

                # Publish event for WebSocket notification
                asyncio.create_task(self._publish_event({
                    "type": "process_schedule_execution_skipped",
                    "process_id": schedule.process_id,
                    "process_name": schedule.process_name,
                    "schedule_id": schedule.id,
                    "trigger_id": schedule.trigger_id,
                    "execution_id": execution.id,
                    "reason": "Previous execution still running"
                }))
            else:
                logger.error(f"Failed to create skipped execution record for process schedule {schedule_id}")

        except Exception as e:
            logger.error(f"Error recording skipped execution for process schedule {schedule_id}: {e}")

    # =========================================================================
    # Schedule Execution
    # =========================================================================

    async def _execute_schedule(self, schedule_id: str):
        """
        Execute a scheduled task.

        This is called by APScheduler when a schedule is due.
        Uses distributed locking to prevent duplicate executions.
        """
        # Try to acquire lock - if failed, another instance is executing
        lock = self.lock_manager.try_acquire_schedule_lock(schedule_id)
        if not lock:
            logger.info(f"Schedule {schedule_id} already being executed by another instance")
            return

        try:
            await self._execute_schedule_with_lock(schedule_id)
        finally:
            lock.release()

    async def _execute_schedule_with_lock(self, schedule_id: str, triggered_by: str = "schedule"):
        """Execute schedule after acquiring lock.

        Args:
            schedule_id: ID of the schedule to execute
            triggered_by: Source of trigger - "schedule" (cron) or "manual"
        """
        schedule = self.db.get_schedule(schedule_id)
        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return

        if not schedule.enabled and triggered_by == "schedule":
            logger.info(f"Schedule {schedule_id} is disabled, skipping")
            return

        # Check if agent has autonomy enabled (only for cron-triggered, not manual)
        if triggered_by == "schedule" and not self.db.get_autonomy_enabled(schedule.agent_name):
            logger.info(f"Schedule {schedule_id} skipped: agent {schedule.agent_name} autonomy is disabled")
            return

        logger.info(f"Executing schedule: {schedule.name} for agent {schedule.agent_name} (triggered_by={triggered_by})")

        # Create execution record
        execution = self.db.create_execution(
            schedule_id=schedule.id,
            agent_name=schedule.agent_name,
            message=schedule.message,
            triggered_by=triggered_by,
            model_used=schedule.model
        )

        if not execution:
            logger.error(f"Failed to create execution record for schedule {schedule_id}")
            return

        # Track activity start via backend internal API
        # This creates the agent_activities record and broadcasts via WebSocket
        activity_id = await self._track_activity_start(
            agent_name=schedule.agent_name,
            schedule=schedule,
            execution_id=execution.id,
            triggered_by=triggered_by
        )

        # Broadcast execution started
        await self._publish_event({
            "type": "schedule_execution_started",
            "agent": schedule.agent_name,
            "schedule_id": schedule.id,
            "execution_id": execution.id,
            "schedule_name": schedule.name,
            "triggered_by": triggered_by
        })

        try:
            # Send task to agent with schedule-specific timeout, allowed_tools, and model
            client = get_agent_client(schedule.agent_name)
            task_response = await client.task(
                schedule.message,
                timeout=schedule.timeout_seconds,
                execution_id=execution.id,
                allowed_tools=schedule.allowed_tools,
                model=schedule.model
            )

            # Update execution status with parsed response
            self.db.update_execution_status(
                execution_id=execution.id,
                status="success",
                response=task_response.response_text,
                context_used=task_response.metrics.context_used,
                context_max=task_response.metrics.context_max,
                cost=task_response.metrics.cost_usd,
                tool_calls=task_response.metrics.tool_calls_json,
                execution_log=task_response.metrics.execution_log_json,
                claude_session_id=task_response.metrics.session_id  # EXEC-023: For --resume support
            )

            # Update schedule last run time
            now = datetime.utcnow()
            next_run = self._get_next_run_time(schedule.cron_expression, schedule.timezone)
            self.db.update_schedule_run_times(schedule.id, last_run_at=now, next_run_at=next_run)

            logger.info(f"Schedule {schedule.name} executed successfully")

            # Complete activity via backend internal API
            execution_log = task_response.raw_response.get("execution_log")
            await self._complete_activity(
                activity_id=activity_id,
                status="completed",
                details={
                    "related_execution_id": execution.id,
                    "context_used": task_response.metrics.context_used,
                    "context_max": task_response.metrics.context_max,
                    "cost_usd": task_response.metrics.cost_usd,
                    "tool_count": len(execution_log) if execution_log else 0
                }
            )

            # Broadcast execution completed
            await self._publish_event({
                "type": "schedule_execution_completed",
                "agent": schedule.agent_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "success"
            })

        except AgentNotReachableError as e:
            error_msg = f"Agent not reachable: {str(e)}"
            logger.error(f"Schedule {schedule.name} execution failed: {error_msg}")
            # Agent unreachable could indicate container credential issues
            # if subscription was expected but agent can't authenticate

            self.db.update_execution_status(
                execution_id=execution.id,
                status="failed",
                error=error_msg
            )

            # Complete activity as failed
            await self._complete_activity(
                activity_id=activity_id,
                status="failed",
                error=error_msg,
                details={"related_execution_id": execution.id}
            )

            await self._publish_event({
                "type": "schedule_execution_completed",
                "agent": schedule.agent_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "failed",
                "error": error_msg
            })

        except Exception as e:
            error_msg = str(e)

            # Detect auth-specific failures for better error surfacing
            auth_indicators = [
                "credit balance", "unauthorized", "authentication",
                "credentials", "forbidden", "401", "403",
                "oauth", "token expired", "not authenticated"
            ]
            error_lower = error_msg.lower()
            is_auth_failure = any(ind in error_lower for ind in auth_indicators)

            if is_auth_failure:
                error_msg = f"[AUTH_ERROR] {error_msg}"
                logger.error(
                    f"Schedule {schedule.name} execution failed due to authentication error: {error_msg}"
                )
            else:
                logger.error(f"Schedule {schedule.name} execution failed: {error_msg}")

            self.db.update_execution_status(
                execution_id=execution.id,
                status="failed",
                error=error_msg
            )

            # Complete activity as failed
            await self._complete_activity(
                activity_id=activity_id,
                status="failed",
                error=error_msg,
                details={
                    "related_execution_id": execution.id,
                    **({"failure_category": "auth"} if is_auth_failure else {})
                }
            )

            await self._publish_event({
                "type": "schedule_execution_completed",
                "agent": schedule.agent_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "failed",
                "error": error_msg
            })

    async def _track_activity_start(
        self,
        agent_name: str,
        schedule,
        execution_id: str,
        triggered_by: str
    ) -> Optional[str]:
        """
        Track activity start via backend internal API.

        Creates an agent_activities record and broadcasts via WebSocket.
        Returns the activity_id or None if the call fails.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{config.backend_url}/api/internal/activities/track",
                    json={
                        "agent_name": agent_name,
                        "activity_type": "schedule_start",
                        "user_id": schedule.owner_id,
                        "triggered_by": triggered_by,
                        "related_execution_id": execution_id,
                        "details": {
                            "schedule_id": schedule.id,
                            "schedule_name": schedule.name,
                            "cron_expression": schedule.cron_expression,
                            "execution_id": execution_id
                        }
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    activity_id = result.get("activity_id")
                    logger.debug(f"Activity tracked: {activity_id}")
                    return activity_id
                else:
                    logger.warning(f"Failed to track activity: {response.status_code} - {response.text[:200]}")
                    return None

        except Exception as e:
            logger.warning(f"Failed to track activity via backend API: {e}")
            # Don't fail the execution if activity tracking fails
            return None

    async def _complete_activity(
        self,
        activity_id: Optional[str],
        status: str,
        details: Optional[dict] = None,
        error: Optional[str] = None
    ):
        """
        Complete an activity via backend internal API.

        Updates the agent_activities record and broadcasts via WebSocket.
        """
        if not activity_id:
            # Activity tracking was skipped, nothing to complete
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{config.backend_url}/api/internal/activities/{activity_id}/complete",
                    json={
                        "status": status,
                        "details": details,
                        "error": error
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    logger.debug(f"Activity completed: {activity_id} ({status})")
                else:
                    logger.warning(f"Failed to complete activity: {response.status_code} - {response.text[:200]}")

        except Exception as e:
            logger.warning(f"Failed to complete activity via backend API: {e}")
            # Don't fail the execution if activity completion fails

    # =========================================================================
    # Schedule Management (for runtime updates)
    # =========================================================================

    def add_schedule(self, schedule: Schedule):
        """Add a new schedule to the scheduler."""
        if schedule.enabled:
            self._add_job(schedule)

    def remove_schedule(self, schedule_id: str):
        """Remove a schedule from the scheduler."""
        self._remove_job(schedule_id)

    def update_schedule(self, schedule: Schedule):
        """Update an existing schedule in the scheduler."""
        self._remove_job(schedule.id)
        if schedule.enabled:
            self._add_job(schedule)

    def reload_schedules(self):
        """Reload all schedules from the database."""
        if not self.scheduler:
            return

        # Remove all existing jobs
        for job in self.scheduler.get_jobs():
            if job.id.startswith("schedule_") or job.id.startswith("process_schedule_"):
                self.scheduler.remove_job(job.id)

        # Reload agent schedules from database
        schedules = self.db.list_all_enabled_schedules()
        for schedule in schedules:
            self._add_job(schedule)

        # Reload process schedules from database
        process_schedules = self.db.list_all_enabled_process_schedules()
        for process_schedule in process_schedules:
            self._add_process_job(process_schedule)

        logger.info(f"Reloaded {len(schedules)} agent schedules, {len(process_schedules)} process schedules")

    # =========================================================================
    # Process Schedule Management
    # =========================================================================

    def _get_process_job_id(self, schedule_id: str) -> str:
        """Generate a unique job ID for process schedules."""
        return f"process_schedule_{schedule_id}"

    def _add_process_job(self, schedule: ProcessSchedule):
        """Add a process schedule as an APScheduler job."""
        if not self.scheduler:
            return

        job_id = self._get_process_job_id(schedule.id)

        try:
            # Parse cron expression
            cron_kwargs = self._parse_cron(schedule.cron_expression)

            # Create timezone-aware trigger
            timezone = pytz.timezone(schedule.timezone) if schedule.timezone else pytz.UTC
            trigger = CronTrigger(timezone=timezone, **cron_kwargs)

            # Add the job
            self.scheduler.add_job(
                self._execute_process_schedule,
                trigger=trigger,
                id=job_id,
                args=[schedule.id],
                replace_existing=True,
                name=f"process:{schedule.process_name}:{schedule.trigger_id}"
            )

            # Calculate and store next run time
            next_run = self._get_next_run_time(schedule.cron_expression, schedule.timezone)
            if next_run:
                self.db.update_process_schedule_run_times(schedule.id, next_run_at=next_run)

            logger.info(f"Added process schedule job: {job_id} ({schedule.process_name}/{schedule.trigger_id})")
        except Exception as e:
            logger.error(f"Failed to add process schedule job {job_id}: {e}")

    def _remove_process_job(self, schedule_id: str):
        """Remove a process schedule job from APScheduler."""
        if not self.scheduler:
            return

        job_id = self._get_process_job_id(schedule_id)
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed process schedule job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to remove process schedule job {job_id}: {e}")

    async def _execute_process_schedule(self, schedule_id: str):
        """
        Execute a scheduled process.

        This is called by APScheduler when a process schedule is due.
        Uses distributed locking to prevent duplicate executions.
        """
        # Try to acquire lock - if failed, another instance is executing
        lock = self.lock_manager.try_acquire_schedule_lock(f"process_{schedule_id}")
        if not lock:
            logger.info(f"Process schedule {schedule_id} already being executed by another instance")
            return

        try:
            await self._execute_process_schedule_with_lock(schedule_id)
        finally:
            lock.release()

    async def _execute_process_schedule_with_lock(self, schedule_id: str):
        """Execute process schedule after acquiring lock."""
        schedule = self.db.get_process_schedule(schedule_id)
        if not schedule:
            logger.error(f"Process schedule {schedule_id} not found")
            return

        if not schedule.enabled:
            logger.info(f"Process schedule {schedule_id} is disabled, skipping")
            return

        logger.info(f"Executing process schedule: {schedule.process_name}/{schedule.trigger_id}")

        # Create execution record
        execution = self.db.create_process_schedule_execution(
            schedule_id=schedule.id,
            process_id=schedule.process_id,
            process_name=schedule.process_name,
            triggered_by="schedule"
        )

        if not execution:
            logger.error(f"Failed to create execution record for process schedule {schedule_id}")
            return

        # Broadcast execution started
        await self._publish_event({
            "type": "process_schedule_execution_started",
            "process_id": schedule.process_id,
            "process_name": schedule.process_name,
            "schedule_id": schedule.id,
            "trigger_id": schedule.trigger_id,
            "execution_id": execution.id
        })

        try:
            # Call backend API to start process execution
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{config.backend_url}/api/processes/{schedule.process_id}/execute",
                    json={
                        "triggered_by": "schedule",
                        "input_data": {
                            "trigger": {
                                "type": "schedule",
                                "id": schedule.trigger_id,
                                "schedule_id": schedule.id,
                            }
                        }
                    },
                    timeout=60.0
                )

                if response.status_code == 200 or response.status_code == 201:
                    result = response.json()
                    process_execution_id = result.get("id")

                    # Update execution status
                    self.db.update_process_schedule_execution(
                        execution_id=execution.id,
                        status="success",
                        process_execution_id=process_execution_id
                    )

                    # Update schedule last run time
                    now = datetime.utcnow()
                    next_run = self._get_next_run_time(schedule.cron_expression, schedule.timezone)
                    self.db.update_process_schedule_run_times(schedule.id, last_run_at=now, next_run_at=next_run)

                    logger.info(f"Process schedule {schedule.process_name}/{schedule.trigger_id} executed successfully, execution_id={process_execution_id}")

                    # Broadcast execution completed
                    await self._publish_event({
                        "type": "process_schedule_execution_completed",
                        "process_id": schedule.process_id,
                        "process_name": schedule.process_name,
                        "schedule_id": schedule.id,
                        "execution_id": execution.id,
                        "process_execution_id": process_execution_id,
                        "status": "success"
                    })

                else:
                    error_msg = f"Backend returned {response.status_code}: {response.text[:200]}"
                    logger.error(f"Process schedule {schedule.process_name} execution failed: {error_msg}")

                    self.db.update_process_schedule_execution(
                        execution_id=execution.id,
                        status="failed",
                        error=error_msg
                    )

                    await self._publish_event({
                        "type": "process_schedule_execution_completed",
                        "process_id": schedule.process_id,
                        "process_name": schedule.process_name,
                        "schedule_id": schedule.id,
                        "execution_id": execution.id,
                        "status": "failed",
                        "error": error_msg
                    })

        except httpx.TimeoutException:
            error_msg = "Backend request timed out"
            logger.error(f"Process schedule {schedule.process_name} execution failed: {error_msg}")

            self.db.update_process_schedule_execution(
                execution_id=execution.id,
                status="failed",
                error=error_msg
            )

            await self._publish_event({
                "type": "process_schedule_execution_completed",
                "process_id": schedule.process_id,
                "process_name": schedule.process_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "failed",
                "error": error_msg
            })

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Process schedule {schedule.process_name} execution failed: {error_msg}")

            self.db.update_process_schedule_execution(
                execution_id=execution.id,
                status="failed",
                error=error_msg
            )

            await self._publish_event({
                "type": "process_schedule_execution_completed",
                "process_id": schedule.process_id,
                "process_name": schedule.process_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "failed",
                "error": error_msg
            })

    def add_process_schedule(self, schedule: ProcessSchedule):
        """Add a new process schedule to the scheduler."""
        if schedule.enabled:
            self._add_process_job(schedule)

    def remove_process_schedule(self, schedule_id: str):
        """Remove a process schedule from the scheduler."""
        self._remove_process_job(schedule_id)

    def update_process_schedule(self, schedule: ProcessSchedule):
        """Update an existing process schedule in the scheduler."""
        self._remove_process_job(schedule.id)
        if schedule.enabled:
            self._add_process_job(schedule)

    # =========================================================================
    # Event Publishing
    # =========================================================================

    async def _publish_event(self, event: dict):
        """
        Publish an event to Redis for WebSocket compatibility.

        Events are published to a channel that the backend can subscribe to.
        """
        if not config.publish_events:
            return

        try:
            event_json = json.dumps(event)
            self.redis.publish("scheduler:events", event_json)
            logger.debug(f"Published event: {event['type']}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    # =========================================================================
    # Status & Health
    # =========================================================================

    def get_status(self) -> SchedulerStatus:
        """Get current scheduler status."""
        if not self.scheduler:
            return SchedulerStatus(
                running=False,
                jobs_count=0,
                last_check=datetime.utcnow(),
                uptime_seconds=0
            )

        jobs = self.scheduler.get_jobs()
        uptime = (datetime.utcnow() - self._start_time).total_seconds() if self._start_time else 0

        return SchedulerStatus(
            running=self.scheduler.running,
            jobs_count=len(jobs),
            last_check=datetime.utcnow(),
            uptime_seconds=uptime,
            jobs=[
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in jobs
            ]
        )

    def is_healthy(self) -> bool:
        """Check if the scheduler is healthy."""
        if not self._initialized:
            return False
        if not self.scheduler or not self.scheduler.running:
            return False
        return True
