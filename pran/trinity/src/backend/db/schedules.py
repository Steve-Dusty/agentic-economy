"""
Schedule and execution management database operations.

Handles schedule CRUD, execution tracking, and Git configuration.
"""

import json
import logging
import secrets
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

import pytz
from croniter import croniter

from .connection import get_db_connection
from db_models import Schedule, ScheduleCreate, ScheduleExecution, AgentGitConfig
from utils.helpers import utc_now_iso, to_utc_iso, parse_iso_timestamp

logger = logging.getLogger(__name__)


class ScheduleOperations:
    """Schedule and execution database operations."""

    def __init__(self, user_ops, agent_ops):
        """Initialize with references to user and agent operations."""
        self._user_ops = user_ops
        self._agent_ops = agent_ops

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique ID."""
        return secrets.token_urlsafe(16)

    @staticmethod
    def _calculate_next_run_at(cron_expression: str, timezone: str = "UTC") -> Optional[datetime]:
        """Calculate the next run time for a cron expression.

        This is calculated in the database layer to ensure next_run_at is always
        set when schedules are created or updated, independent of the scheduler service.

        Args:
            cron_expression: Cron expression (5-field format)
            timezone: Timezone for schedule (default: UTC)

        Returns:
            Next run time as datetime, or None if calculation fails
        """
        try:
            tz = pytz.timezone(timezone) if timezone else pytz.UTC
            now = datetime.now(tz)
            cron = croniter(cron_expression, now)
            next_time = cron.get_next(datetime)
            return next_time
        except Exception as e:
            logger.warning(f"Failed to calculate next_run_at for cron '{cron_expression}': {e}")
            return None

    @staticmethod
    def _row_to_schedule(row) -> Schedule:
        """Convert a schedule row to a Schedule model."""
        row_keys = row.keys() if hasattr(row, 'keys') else []

        # Parse allowed_tools from JSON if present
        allowed_tools = None
        if "allowed_tools" in row_keys and row["allowed_tools"]:
            try:
                allowed_tools = json.loads(row["allowed_tools"])
            except (json.JSONDecodeError, TypeError):
                allowed_tools = None

        return Schedule(
            id=row["id"],
            agent_name=row["agent_name"],
            name=row["name"],
            cron_expression=row["cron_expression"],
            message=row["message"],
            enabled=bool(row["enabled"]),
            timezone=row["timezone"],
            description=row["description"],
            owner_id=row["owner_id"],
            # Use parse_iso_timestamp to handle both 'Z' and non-'Z' timestamps
            created_at=parse_iso_timestamp(row["created_at"]),
            updated_at=parse_iso_timestamp(row["updated_at"]),
            last_run_at=parse_iso_timestamp(row["last_run_at"]) if row["last_run_at"] else None,
            next_run_at=parse_iso_timestamp(row["next_run_at"]) if row["next_run_at"] else None,
            timeout_seconds=row["timeout_seconds"] if "timeout_seconds" in row_keys and row["timeout_seconds"] else 900,
            allowed_tools=allowed_tools,
            model=row["model"] if "model" in row_keys else None
        )

    @staticmethod
    def _row_to_schedule_execution(row) -> ScheduleExecution:
        """Convert a schedule_executions row to a ScheduleExecution model."""
        row_keys = row.keys()
        return ScheduleExecution(
            id=row["id"],
            schedule_id=row["schedule_id"],
            agent_name=row["agent_name"],
            status=row["status"],
            # Use parse_iso_timestamp to handle both 'Z' and non-'Z' timestamps
            started_at=parse_iso_timestamp(row["started_at"]),
            completed_at=parse_iso_timestamp(row["completed_at"]) if row["completed_at"] else None,
            duration_ms=row["duration_ms"],
            message=row["message"],
            response=row["response"],
            error=row["error"],
            triggered_by=row["triggered_by"],
            context_used=row["context_used"] if "context_used" in row_keys else None,
            context_max=row["context_max"] if "context_max" in row_keys else None,
            cost=row["cost"] if "cost" in row_keys else None,
            tool_calls=row["tool_calls"] if "tool_calls" in row_keys else None,
            execution_log=row["execution_log"] if "execution_log" in row_keys else None,
            # Origin tracking fields (AUDIT-001)
            source_user_id=row["source_user_id"] if "source_user_id" in row_keys else None,
            source_user_email=row["source_user_email"] if "source_user_email" in row_keys else None,
            source_agent_name=row["source_agent_name"] if "source_agent_name" in row_keys else None,
            source_mcp_key_id=row["source_mcp_key_id"] if "source_mcp_key_id" in row_keys else None,
            source_mcp_key_name=row["source_mcp_key_name"] if "source_mcp_key_name" in row_keys else None,
            # Session resume support (EXEC-023)
            claude_session_id=row["claude_session_id"] if "claude_session_id" in row_keys else None,
            # Model selection (MODEL-001)
            model_used=row["model_used"] if "model_used" in row_keys else None,
        )

    @staticmethod
    def _row_to_git_config(row) -> AgentGitConfig:
        """Convert an agent_git_config row to an AgentGitConfig model."""
        row_keys = row.keys() if hasattr(row, 'keys') else []
        return AgentGitConfig(
            id=row["id"],
            agent_name=row["agent_name"],
            github_repo=row["github_repo"],
            working_branch=row["working_branch"],
            instance_id=row["instance_id"],
            source_branch=row["source_branch"] if "source_branch" in row_keys else "main",
            source_mode=bool(row["source_mode"]) if "source_mode" in row_keys else False,
            # Use parse_iso_timestamp to handle both 'Z' and non-'Z' timestamps
            created_at=parse_iso_timestamp(row["created_at"]),
            last_sync_at=parse_iso_timestamp(row["last_sync_at"]) if row["last_sync_at"] else None,
            last_commit_sha=row["last_commit_sha"],
            sync_enabled=bool(row["sync_enabled"]),
            sync_paths=row["sync_paths"]
        )

    # =========================================================================
    # Schedule Management
    # =========================================================================

    def create_schedule(self, agent_name: str, username: str, schedule_data: ScheduleCreate) -> Optional[Schedule]:
        """Create a new schedule for an agent."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return None

        # Check user has access to this agent
        if not self._agent_ops.can_user_access_agent(username, agent_name):
            return None

        schedule_id = self._generate_id()
        now = utc_now_iso()

        # Calculate next_run_at if schedule is enabled
        next_run_at = None
        next_run_at_iso = None
        if schedule_data.enabled:
            next_run_at = self._calculate_next_run_at(
                schedule_data.cron_expression,
                schedule_data.timezone or "UTC"
            )
            if next_run_at:
                next_run_at_iso = next_run_at.isoformat()

        # Serialize allowed_tools to JSON if provided
        allowed_tools_json = None
        if schedule_data.allowed_tools is not None:
            allowed_tools_json = json.dumps(schedule_data.allowed_tools)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO agent_schedules (
                        id, agent_name, name, cron_expression, message, enabled,
                        timezone, description, owner_id, created_at, updated_at, next_run_at,
                        timeout_seconds, allowed_tools, model
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    schedule_id,
                    agent_name,
                    schedule_data.name,
                    schedule_data.cron_expression,
                    schedule_data.message,
                    1 if schedule_data.enabled else 0,
                    schedule_data.timezone,
                    schedule_data.description,
                    user["id"],
                    now,
                    now,
                    next_run_at_iso,
                    schedule_data.timeout_seconds,
                    allowed_tools_json,
                    schedule_data.model
                ))
                conn.commit()

                return Schedule(
                    id=schedule_id,
                    agent_name=agent_name,
                    name=schedule_data.name,
                    cron_expression=schedule_data.cron_expression,
                    message=schedule_data.message,
                    enabled=schedule_data.enabled,
                    timezone=schedule_data.timezone,
                    description=schedule_data.description,
                    owner_id=user["id"],
                    created_at=datetime.fromisoformat(now),
                    updated_at=datetime.fromisoformat(now),
                    next_run_at=next_run_at,
                    timeout_seconds=schedule_data.timeout_seconds,
                    allowed_tools=schedule_data.allowed_tools,
                    model=schedule_data.model
                )
            except sqlite3.IntegrityError:
                return None

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_schedules WHERE id = ?", (schedule_id,))
            row = cursor.fetchone()
            return self._row_to_schedule(row) if row else None

    def list_agent_schedules(self, agent_name: str) -> List[Schedule]:
        """List all schedules for an agent."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_schedules WHERE agent_name = ?
                ORDER BY created_at DESC
            """, (agent_name,))
            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def list_all_enabled_schedules(self) -> List[Schedule]:
        """List all enabled schedules (for scheduler initialization)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_schedules WHERE enabled = 1
                ORDER BY agent_name, name
            """)
            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def list_all_disabled_schedules(self) -> List[Schedule]:
        """List all disabled schedules (for resume operations)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_schedules WHERE enabled = 0
                ORDER BY agent_name, name
            """)
            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def list_all_schedules(self) -> List[Schedule]:
        """List all schedules across all agents (for system agent overview)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_schedules
                ORDER BY agent_name, name
            """)
            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def update_schedule(self, schedule_id: str, username: str, updates: Dict) -> Optional[Schedule]:
        """Update a schedule."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return None

        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return None

        # Check permission (owner or admin)
        if user["role"] != "admin" and schedule.owner_id != user["id"]:
            return None

        with get_db_connection() as conn:
            cursor = conn.cursor()

            set_clauses = []
            params = []
            allowed_fields = ["name", "cron_expression", "message", "enabled", "timezone", "description", "timeout_seconds", "allowed_tools", "model"]

            for key, value in updates.items():
                if key in allowed_fields:
                    if key == "enabled":
                        value = 1 if value else 0
                    elif key == "allowed_tools":
                        # Serialize allowed_tools to JSON
                        value = json.dumps(value) if value is not None else None
                    set_clauses.append(f"{key} = ?")
                    params.append(value)

            if not set_clauses:
                return schedule

            # Check if we need to recalculate next_run_at
            # Recalculate if cron_expression, timezone, or enabled status changed
            needs_next_run_recalc = (
                "cron_expression" in updates or
                "timezone" in updates or
                "enabled" in updates
            )

            if needs_next_run_recalc:
                # Determine final values after update
                new_cron = updates.get("cron_expression", schedule.cron_expression)
                new_timezone = updates.get("timezone", schedule.timezone) or "UTC"
                new_enabled = updates.get("enabled", schedule.enabled)

                if new_enabled:
                    next_run_at = self._calculate_next_run_at(new_cron, new_timezone)
                    set_clauses.append("next_run_at = ?")
                    params.append(next_run_at.isoformat() if next_run_at else None)
                else:
                    # Clear next_run_at if schedule is disabled
                    set_clauses.append("next_run_at = ?")
                    params.append(None)

            set_clauses.append("updated_at = ?")
            params.append(utc_now_iso())
            params.append(schedule_id)

            cursor.execute(f"""
                UPDATE agent_schedules SET {", ".join(set_clauses)} WHERE id = ?
            """, params)
            conn.commit()

            return self.get_schedule(schedule_id)

    def delete_schedule(self, schedule_id: str, username: str) -> bool:
        """Delete a schedule and its executions."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return False

        # Check permission (owner or admin)
        if user["role"] != "admin" and schedule.owner_id != user["id"]:
            return False

        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Delete executions first
            cursor.execute("DELETE FROM schedule_executions WHERE schedule_id = ?", (schedule_id,))
            # Delete schedule
            cursor.execute("DELETE FROM agent_schedules WHERE id = ?", (schedule_id,))
            conn.commit()
            return cursor.rowcount > 0

    def set_schedule_enabled(self, schedule_id: str, enabled: bool) -> bool:
        """Enable or disable a schedule.

        When enabling, calculates and stores next_run_at.
        When disabling, clears next_run_at.
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return False

        next_run_at_iso = None
        if enabled:
            next_run_at = self._calculate_next_run_at(
                schedule.cron_expression,
                schedule.timezone or "UTC"
            )
            if next_run_at:
                next_run_at_iso = next_run_at.isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_schedules SET enabled = ?, updated_at = ?, next_run_at = ? WHERE id = ?
            """, (1 if enabled else 0, utc_now_iso(), next_run_at_iso, schedule_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_schedule_run_times(self, schedule_id: str, last_run_at: datetime = None, next_run_at: datetime = None) -> bool:
        """Update schedule run timestamps."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            updates = ["updated_at = ?"]
            params = [utc_now_iso()]

            if last_run_at:
                updates.append("last_run_at = ?")
                params.append(last_run_at.isoformat())
            if next_run_at:
                updates.append("next_run_at = ?")
                params.append(next_run_at.isoformat())

            params.append(schedule_id)
            cursor.execute(f"""
                UPDATE agent_schedules SET {", ".join(updates)} WHERE id = ?
            """, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_agent_schedules(self, agent_name: str) -> int:
        """Delete all schedules for an agent (when agent is deleted)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get schedule IDs first
            cursor.execute("SELECT id FROM agent_schedules WHERE agent_name = ?", (agent_name,))
            schedule_ids = [row["id"] for row in cursor.fetchall()]

            # Delete executions for all schedules
            for sid in schedule_ids:
                cursor.execute("DELETE FROM schedule_executions WHERE schedule_id = ?", (sid,))

            # Delete schedules
            cursor.execute("DELETE FROM agent_schedules WHERE agent_name = ?", (agent_name,))
            conn.commit()
            return len(schedule_ids)

    # =========================================================================
    # Schedule Execution Management
    # =========================================================================

    def create_task_execution(
        self,
        agent_name: str,
        message: str,
        triggered_by: str = "manual",
        source_user_id: int = None,
        source_user_email: str = None,
        source_agent_name: str = None,
        source_mcp_key_id: str = None,
        source_mcp_key_name: str = None,
        model_used: str = None,
    ) -> Optional[ScheduleExecution]:
        """Create a new execution record for a manual/API-triggered task (no schedule).

        Args:
            agent_name: Target agent name
            message: Task message
            triggered_by: Trigger type - "manual", "mcp", "agent"
            source_user_id: User ID who triggered (for manual/mcp triggers)
            source_user_email: User email (denormalized for queries)
            source_agent_name: Calling agent name (for agent-to-agent)
            source_mcp_key_id: MCP API key ID (for mcp/agent triggers)
            source_mcp_key_name: MCP API key name (denormalized)
            model_used: Model used for this execution (MODEL-001)
        """
        execution_id = self._generate_id()
        now = utc_now_iso()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule_executions (
                    id, schedule_id, agent_name, status, started_at, message, triggered_by,
                    source_user_id, source_user_email, source_agent_name,
                    source_mcp_key_id, source_mcp_key_name, model_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                "__manual__",  # Special marker for manual/API-triggered tasks
                agent_name,
                "running",
                now,
                message,
                triggered_by,
                source_user_id,
                source_user_email,
                source_agent_name,
                source_mcp_key_id,
                source_mcp_key_name,
                model_used,
            ))
            conn.commit()

            return ScheduleExecution(
                id=execution_id,
                schedule_id="__manual__",
                agent_name=agent_name,
                status="running",
                started_at=datetime.fromisoformat(now),
                message=message,
                triggered_by=triggered_by,
                source_user_id=source_user_id,
                source_user_email=source_user_email,
                source_agent_name=source_agent_name,
                source_mcp_key_id=source_mcp_key_id,
                source_mcp_key_name=source_mcp_key_name,
                model_used=model_used,
            )

    def create_schedule_execution(
        self,
        schedule_id: str,
        agent_name: str,
        message: str,
        triggered_by: str = "schedule",
        source_user_id: int = None,
        source_user_email: str = None,
        source_agent_name: str = None,
        source_mcp_key_id: str = None,
        source_mcp_key_name: str = None,
        model_used: str = None,
    ) -> Optional[ScheduleExecution]:
        """Create a new execution record for a scheduled task.

        Note: For schedule-triggered executions, source fields are typically NULL
        since the schedule itself is the trigger (schedule owner is tracked via schedule.owner_id).
        For manual schedule triggers, source fields may be populated.
        """
        execution_id = self._generate_id()
        now = utc_now_iso()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule_executions (
                    id, schedule_id, agent_name, status, started_at, message, triggered_by,
                    source_user_id, source_user_email, source_agent_name,
                    source_mcp_key_id, source_mcp_key_name, model_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                schedule_id,
                agent_name,
                "running",
                now,
                message,
                triggered_by,
                source_user_id,
                source_user_email,
                source_agent_name,
                source_mcp_key_id,
                source_mcp_key_name,
                model_used,
            ))
            conn.commit()

            return ScheduleExecution(
                id=execution_id,
                schedule_id=schedule_id,
                agent_name=agent_name,
                status="running",
                started_at=datetime.fromisoformat(now),
                message=message,
                triggered_by=triggered_by,
                source_user_id=source_user_id,
                source_user_email=source_user_email,
                source_agent_name=source_agent_name,
                source_mcp_key_id=source_mcp_key_id,
                source_mcp_key_name=source_mcp_key_name,
                model_used=model_used,
            )

    def update_execution_status(
        self,
        execution_id: str,
        status: str,
        response: str = None,
        error: str = None,
        context_used: int = None,
        context_max: int = None,
        cost: float = None,
        tool_calls: str = None,
        execution_log: str = None,
        claude_session_id: str = None
    ) -> bool:
        """Update execution status when completed.

        Args:
            claude_session_id: Claude Code session ID for --resume support (EXEC-023)
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get started_at for duration calculation
            cursor.execute("SELECT started_at FROM schedule_executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            if not row:
                return False

            # Use parse_iso_timestamp to handle both 'Z' and non-'Z' timestamps
            started_at = parse_iso_timestamp(row["started_at"])
            completed_at = parse_iso_timestamp(utc_now_iso())
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            cursor.execute("""
                UPDATE schedule_executions
                SET status = ?, completed_at = ?, duration_ms = ?, response = ?, error = ?,
                    context_used = ?, context_max = ?, cost = ?, tool_calls = ?, execution_log = ?,
                    claude_session_id = ?
                WHERE id = ?
            """, (
                status,
                to_utc_iso(completed_at),  # Use UTC with 'Z' suffix
                duration_ms,
                response,
                error,
                context_used,
                context_max,
                cost,
                tool_calls,
                execution_log,
                claude_session_id,
                execution_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def get_schedule_executions(self, schedule_id: str, limit: int = 50) -> List[ScheduleExecution]:
        """Get execution history for a schedule."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM schedule_executions
                WHERE schedule_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (schedule_id, limit))
            return [self._row_to_schedule_execution(row) for row in cursor.fetchall()]

    def get_agent_executions(self, agent_name: str, limit: int = 50) -> List[ScheduleExecution]:
        """Get all executions for an agent across all schedules."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM schedule_executions
                WHERE agent_name = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (agent_name, limit))
            return [self._row_to_schedule_execution(row) for row in cursor.fetchall()]

    def get_agent_executions_summary(self, agent_name: str, limit: int = 50) -> List[Dict]:
        """Get execution summaries for list view - excludes large text fields.

        Returns only the columns needed for the Tasks list UI, excluding:
        - response (can be large)
        - error (can be large)
        - tool_calls (JSON array, can be large)
        - execution_log (100KB+ per execution)

        This provides 50-100x data reduction vs SELECT * for list views.
        Use get_execution() for full details on a single execution.

        PERF-001: Task List Performance Optimization
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id, schedule_id, agent_name, status, started_at, completed_at,
                    duration_ms, message, triggered_by, context_used, context_max, cost,
                    source_user_id, source_user_email, source_agent_name,
                    source_mcp_key_id, source_mcp_key_name, claude_session_id, model_used
                FROM schedule_executions
                WHERE agent_name = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (agent_name, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_execution(self, execution_id: str) -> Optional[ScheduleExecution]:
        """Get a specific execution by ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedule_executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            return self._row_to_schedule_execution(row) if row else None

    def get_agent_execution_stats(self, agent_name: str, hours: int = 24) -> Dict:
        """Get execution statistics for a single agent.

        Used for platform metrics injection in dashboard (DASH-001).

        Args:
            agent_name: Name of the agent
            hours: Time window in hours (default: 24)

        Returns:
            Dict with execution stats: task_count, success_count, failed_count,
            running_count, success_rate, total_cost, avg_duration_ms, last_execution_at
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as task_count,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_count,
                    SUM(COALESCE(cost, 0)) as total_cost,
                    AVG(duration_ms) as avg_duration_ms,
                    MAX(started_at) as last_execution_at
                FROM schedule_executions
                WHERE agent_name = ?
                AND started_at > datetime('now', ? || ' hours')
            """, (agent_name, f"-{hours}"))

            row = cursor.fetchone()
            if not row or row["task_count"] == 0:
                return {
                    "task_count": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "running_count": 0,
                    "success_rate": 0,
                    "total_cost": 0,
                    "avg_duration_ms": None,
                    "last_execution_at": None
                }

            task_count = row["task_count"]
            success_count = row["success_count"] or 0
            success_rate = round((success_count / task_count * 100), 1) if task_count > 0 else 0

            return {
                "task_count": task_count,
                "success_count": success_count,
                "failed_count": row["failed_count"] or 0,
                "running_count": row["running_count"] or 0,
                "success_rate": success_rate,
                "total_cost": round(row["total_cost"] or 0, 4),
                "avg_duration_ms": int(row["avg_duration_ms"]) if row["avg_duration_ms"] else None,
                "last_execution_at": row["last_execution_at"]
            }

    def get_all_agents_execution_stats(self, hours: int = 24) -> List[Dict]:
        """Get execution statistics for all agents.

        Returns aggregated stats per agent for the specified time window.

        Args:
            hours: Time window in hours (default: 24)

        Returns:
            List of dicts with agent execution stats
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    agent_name,
                    COUNT(*) as task_count,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_count,
                    SUM(COALESCE(cost, 0)) as total_cost,
                    MAX(started_at) as last_execution_at
                FROM schedule_executions
                WHERE started_at > datetime('now', ? || ' hours')
                GROUP BY agent_name
            """, (f"-{hours}",))

            results = []
            for row in cursor.fetchall():
                task_count = row["task_count"]
                success_count = row["success_count"]
                success_rate = round((success_count / task_count * 100), 1) if task_count > 0 else 0

                results.append({
                    "name": row["agent_name"],
                    "task_count_24h": task_count,
                    "success_count": success_count,
                    "failed_count": row["failed_count"],
                    "running_count": row["running_count"],
                    "success_rate": success_rate,
                    "total_cost": round(row["total_cost"], 4) if row["total_cost"] else 0,
                    "last_execution_at": row["last_execution_at"]
                })

            return results

    def get_all_agents_execution_stats_dual(self) -> List[Dict]:
        """Get execution statistics for all agents with both 24h and 7d windows.

        Single SQL query using CASE WHEN to compute both time windows efficiently.

        Returns:
            List of dicts with agent execution stats for both 24h and 7d windows.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    agent_name,
                    SUM(CASE WHEN started_at > datetime('now', '-24 hours') THEN 1 ELSE 0 END) as task_count_24h,
                    SUM(CASE WHEN started_at > datetime('now', '-24 hours') AND status = 'success' THEN 1 ELSE 0 END) as success_count_24h,
                    SUM(CASE WHEN started_at > datetime('now', '-24 hours') AND status = 'failed' THEN 1 ELSE 0 END) as failed_count_24h,
                    SUM(CASE WHEN started_at > datetime('now', '-24 hours') AND status = 'running' THEN 1 ELSE 0 END) as running_count_24h,
                    SUM(CASE WHEN started_at > datetime('now', '-24 hours') THEN COALESCE(cost, 0) ELSE 0 END) as total_cost_24h,
                    MAX(CASE WHEN started_at > datetime('now', '-24 hours') THEN started_at ELSE NULL END) as last_execution_at_24h,
                    COUNT(*) as task_count_7d,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count_7d,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count_7d,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_count_7d,
                    SUM(COALESCE(cost, 0)) as total_cost_7d,
                    MAX(started_at) as last_execution_at_7d
                FROM schedule_executions
                WHERE started_at > datetime('now', '-168 hours')
                GROUP BY agent_name
            """)

            results = []
            for row in cursor.fetchall():
                task_count_24h = row["task_count_24h"] or 0
                success_count_24h = row["success_count_24h"] or 0
                success_rate_24h = round((success_count_24h / task_count_24h * 100), 1) if task_count_24h > 0 else 0

                task_count_7d = row["task_count_7d"] or 0
                success_count_7d = row["success_count_7d"] or 0
                success_rate_7d = round((success_count_7d / task_count_7d * 100), 1) if task_count_7d > 0 else 0

                results.append({
                    "name": row["agent_name"],
                    "task_count_24h": task_count_24h,
                    "success_count": success_count_24h,
                    "failed_count": row["failed_count_24h"] or 0,
                    "running_count": row["running_count_24h"] or 0,
                    "success_rate": success_rate_24h,
                    "total_cost": round(row["total_cost_24h"] or 0, 4),
                    "last_execution_at": row["last_execution_at_24h"],
                    "task_count_7d": task_count_7d,
                    "success_count_7d": success_count_7d,
                    "failed_count_7d": row["failed_count_7d"] or 0,
                    "running_count_7d": row["running_count_7d"] or 0,
                    "success_rate_7d": success_rate_7d,
                    "total_cost_7d": round(row["total_cost_7d"] or 0, 4),
                    "last_execution_at_7d": row["last_execution_at_7d"]
                })

            return results

    def get_all_agents_schedule_counts(self) -> Dict[str, Dict[str, int]]:
        """Get schedule counts (total and enabled) for all agents.

        Returns:
            Dict mapping agent_name to {"total": X, "enabled": Y}
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    agent_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled
                FROM agent_schedules
                GROUP BY agent_name
            """)

            results = {}
            for row in cursor.fetchall():
                results[row["agent_name"]] = {
                    "total": row["total"],
                    "enabled": row["enabled"]
                }

            return results

    # =========================================================================
    # Git Configuration Management (Phase 7: GitHub Bidirectional Sync)
    # =========================================================================

    def create_git_config(
        self,
        agent_name: str,
        github_repo: str,
        working_branch: str,
        instance_id: str,
        sync_paths: List[str] = None,
        source_branch: str = "main",
        source_mode: bool = False
    ) -> Optional[AgentGitConfig]:
        """Create git configuration for an agent.

        Args:
            agent_name: Name of the agent
            github_repo: GitHub repository (e.g., "owner/repo")
            working_branch: Branch for Trinity to work on (legacy mode) or same as source_branch
            instance_id: Unique instance identifier
            sync_paths: Paths to sync (default: memory/, outputs/, etc.)
            source_branch: Branch to pull updates from (default: "main")
            source_mode: If True, track source_branch directly without creating a working branch
        """
        config_id = self._generate_id()
        now = utc_now_iso()
        sync_paths_json = json.dumps(sync_paths) if sync_paths else json.dumps(["memory/", "outputs/", "CLAUDE.md", ".claude/"])

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO agent_git_config (
                        id, agent_name, github_repo, working_branch, instance_id,
                        source_branch, source_mode, created_at, sync_enabled, sync_paths
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (config_id, agent_name, github_repo, working_branch, instance_id,
                      source_branch, 1 if source_mode else 0, now, sync_paths_json))
                conn.commit()

                return AgentGitConfig(
                    id=config_id,
                    agent_name=agent_name,
                    github_repo=github_repo,
                    working_branch=working_branch,
                    instance_id=instance_id,
                    source_branch=source_branch,
                    source_mode=source_mode,
                    created_at=datetime.fromisoformat(now),
                    sync_enabled=True,
                    sync_paths=sync_paths_json
                )
            except sqlite3.IntegrityError:
                # Already exists
                return None

    def get_git_config(self, agent_name: str) -> Optional[AgentGitConfig]:
        """Get git configuration for an agent."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_git_config WHERE agent_name = ?", (agent_name,))
            row = cursor.fetchone()
            return self._row_to_git_config(row) if row else None

    def update_git_sync(self, agent_name: str, commit_sha: str) -> bool:
        """Update git sync timestamp and commit SHA after successful sync."""
        now = utc_now_iso()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_git_config
                SET last_sync_at = ?, last_commit_sha = ?
                WHERE agent_name = ?
            """, (now, commit_sha, agent_name))
            conn.commit()
            return cursor.rowcount > 0

    def set_git_sync_enabled(self, agent_name: str, enabled: bool) -> bool:
        """Enable or disable git sync for an agent."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_git_config SET sync_enabled = ? WHERE agent_name = ?
            """, (1 if enabled else 0, agent_name))
            conn.commit()
            return cursor.rowcount > 0

    def delete_git_config(self, agent_name: str) -> bool:
        """Delete git configuration for an agent (when agent is deleted)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM agent_git_config WHERE agent_name = ?", (agent_name,))
            conn.commit()
            return cursor.rowcount > 0

    def list_git_enabled_agents(self) -> List[AgentGitConfig]:
        """List all agents with git sync enabled."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_git_config WHERE sync_enabled = 1
                ORDER BY agent_name
            """)
            return [self._row_to_git_config(row) for row in cursor.fetchall()]
