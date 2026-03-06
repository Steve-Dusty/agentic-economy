"""
Database access layer for the scheduler service.

Provides read-only access to schedules and write access to executions.
Uses the same SQLite database as the main backend.
"""

import json
import secrets
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List

from .config import config
from .models import Schedule, ScheduleExecution, ProcessSchedule, ProcessScheduleExecution

logger = logging.getLogger(__name__)


class SchedulerDatabase:
    """
    Database access for the scheduler service.

    Thread-safe SQLite access with connection pooling.
    """

    def __init__(self, database_path: str = None):
        """Initialize database with path."""
        self.database_path = database_path or config.database_path
        logger.info(f"Scheduler database initialized: {self.database_path}")

    @contextmanager
    def get_connection(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique ID."""
        return secrets.token_urlsafe(16)

    @staticmethod
    def _row_to_schedule(row: sqlite3.Row) -> Schedule:
        """Convert a database row to a Schedule model."""
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
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
            next_run_at=datetime.fromisoformat(row["next_run_at"]) if row["next_run_at"] else None,
            timeout_seconds=row["timeout_seconds"] if "timeout_seconds" in row_keys and row["timeout_seconds"] else 900,
            allowed_tools=allowed_tools,
            model=row["model"] if "model" in row_keys else None
        )

    @staticmethod
    def _row_to_execution(row: sqlite3.Row) -> ScheduleExecution:
        """Convert a database row to a ScheduleExecution model."""
        row_keys = row.keys()
        return ScheduleExecution(
            id=row["id"],
            schedule_id=row["schedule_id"],
            agent_name=row["agent_name"],
            status=row["status"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
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
            source_mcp_key_name=row["source_mcp_key_name"] if "source_mcp_key_name" in row_keys else None
        )

    # =========================================================================
    # Schedule Read Operations
    # =========================================================================

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_schedules WHERE id = ?", (schedule_id,))
            row = cursor.fetchone()
            return self._row_to_schedule(row) if row else None

    def list_all_enabled_schedules(self) -> List[Schedule]:
        """List all enabled schedules."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_schedules WHERE enabled = 1
                ORDER BY agent_name, name
            """)
            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def list_all_schedules(self) -> List[Schedule]:
        """List all schedules (enabled and disabled) for sync detection."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_schedules
                ORDER BY agent_name, name
            """)
            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def list_agent_schedules(self, agent_name: str) -> List[Schedule]:
        """List all schedules for a specific agent."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_schedules WHERE agent_name = ?
                ORDER BY name
            """, (agent_name,))
            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def get_autonomy_enabled(self, agent_name: str) -> bool:
        """Check if autonomy is enabled for an agent."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT autonomy_enabled FROM agent_ownership WHERE agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            return bool(row["autonomy_enabled"]) if row else False

    # =========================================================================
    # Schedule Update Operations
    # =========================================================================

    def update_schedule_run_times(
        self,
        schedule_id: str,
        last_run_at: datetime = None,
        next_run_at: datetime = None
    ) -> bool:
        """Update schedule run timestamps."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = ["updated_at = ?"]
            params = [datetime.utcnow().isoformat()]

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

    # =========================================================================
    # Execution Operations
    # =========================================================================

    def create_execution(
        self,
        schedule_id: str,
        agent_name: str,
        message: str,
        triggered_by: str = "schedule",
        model_used: str = None
    ) -> Optional[ScheduleExecution]:
        """Create a new execution record."""
        execution_id = self._generate_id()
        now = datetime.utcnow().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule_executions (
                    id, schedule_id, agent_name, status, started_at, message, triggered_by,
                    model_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                schedule_id,
                agent_name,
                "running",
                now,
                message,
                triggered_by,
                model_used
            ))
            conn.commit()

            return ScheduleExecution(
                id=execution_id,
                schedule_id=schedule_id,
                agent_name=agent_name,
                status="running",
                started_at=datetime.fromisoformat(now),
                message=message,
                triggered_by=triggered_by
            )

    def create_skipped_execution(
        self,
        schedule_id: str,
        agent_name: str,
        message: str,
        triggered_by: str = "schedule",
        skip_reason: str = None
    ) -> Optional[ScheduleExecution]:
        """
        Create an execution record for a skipped scheduled task.

        This is called when APScheduler fires EVENT_JOB_MAX_INSTANCES,
        indicating that a scheduled job was dropped because the previous
        execution is still running.

        Args:
            schedule_id: ID of the schedule that was skipped
            agent_name: Name of the agent
            message: The scheduled message that would have been sent
            triggered_by: Source of the trigger (always "schedule" for skipped)
            skip_reason: Human-readable reason for the skip

        Returns:
            ScheduleExecution with status='skipped', or None on failure
        """
        execution_id = self._generate_id()
        now = datetime.utcnow().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule_executions (
                    id, schedule_id, agent_name, status, started_at, completed_at,
                    duration_ms, message, triggered_by, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                schedule_id,
                agent_name,
                "skipped",
                now,
                now,  # completed_at = started_at for skipped
                0,    # duration_ms = 0 for skipped
                message,
                triggered_by,
                skip_reason
            ))
            conn.commit()

            return ScheduleExecution(
                id=execution_id,
                schedule_id=schedule_id,
                agent_name=agent_name,
                status="skipped",
                started_at=datetime.fromisoformat(now),
                completed_at=datetime.fromisoformat(now),
                duration_ms=0,
                message=message,
                triggered_by=triggered_by,
                error=skip_reason
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
        claude_session_id: str = None  # Claude Code session ID for --resume (EXEC-023)
    ) -> bool:
        """Update execution status when completed.

        Args:
            claude_session_id: Claude Code session ID for --resume support (EXEC-023)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get started_at for duration calculation
            cursor.execute("SELECT started_at FROM schedule_executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            if not row:
                return False

            started_at = datetime.fromisoformat(row["started_at"])
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            cursor.execute("""
                UPDATE schedule_executions
                SET status = ?, completed_at = ?, duration_ms = ?, response = ?, error = ?,
                    context_used = ?, context_max = ?, cost = ?, tool_calls = ?, execution_log = ?,
                    claude_session_id = ?
                WHERE id = ?
            """, (
                status,
                completed_at.isoformat(),
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

    def get_execution(self, execution_id: str) -> Optional[ScheduleExecution]:
        """Get an execution by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedule_executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            return self._row_to_execution(row) if row else None

    def get_recent_executions(self, limit: int = 50) -> List[ScheduleExecution]:
        """Get recent executions across all schedules."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM schedule_executions
                ORDER BY started_at DESC
                LIMIT ?
            """, (limit,))
            return [self._row_to_execution(row) for row in cursor.fetchall()]

    # =========================================================================
    # Process Schedule Operations
    # =========================================================================

    def ensure_process_schedules_table(self) -> None:
        """Create process_schedules table if it doesn't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS process_schedule_executions (
                    id TEXT PRIMARY KEY,
                    schedule_id TEXT NOT NULL,
                    process_id TEXT NOT NULL,
                    process_name TEXT NOT NULL,
                    execution_id TEXT,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_ms INTEGER,
                    triggered_by TEXT NOT NULL,
                    error TEXT,
                    FOREIGN KEY (schedule_id) REFERENCES process_schedules(id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_process_schedules_process
                ON process_schedules(process_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_process_schedules_enabled
                ON process_schedules(enabled)
            """)
            conn.commit()
            logger.info("Process schedules tables ensured")

    @staticmethod
    def _row_to_process_schedule(row: sqlite3.Row) -> ProcessSchedule:
        """Convert a database row to a ProcessSchedule model."""
        return ProcessSchedule(
            id=row["id"],
            process_id=row["process_id"],
            process_name=row["process_name"],
            trigger_id=row["trigger_id"],
            cron_expression=row["cron_expression"],
            enabled=bool(row["enabled"]),
            timezone=row["timezone"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
            next_run_at=datetime.fromisoformat(row["next_run_at"]) if row["next_run_at"] else None
        )

    @staticmethod
    def _row_to_process_schedule_execution(row: sqlite3.Row) -> ProcessScheduleExecution:
        """Convert a database row to a ProcessScheduleExecution model."""
        return ProcessScheduleExecution(
            id=row["id"],
            schedule_id=row["schedule_id"],
            process_id=row["process_id"],
            process_name=row["process_name"],
            execution_id=row["execution_id"],
            status=row["status"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            duration_ms=row["duration_ms"],
            triggered_by=row["triggered_by"],
            error=row["error"]
        )

    def get_process_schedule(self, schedule_id: str) -> Optional[ProcessSchedule]:
        """Get a process schedule by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM process_schedules WHERE id = ?", (schedule_id,))
            row = cursor.fetchone()
            return self._row_to_process_schedule(row) if row else None

    def get_process_schedule_by_trigger(self, process_id: str, trigger_id: str) -> Optional[ProcessSchedule]:
        """Get a process schedule by process ID and trigger ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM process_schedules WHERE process_id = ? AND trigger_id = ?",
                (process_id, trigger_id)
            )
            row = cursor.fetchone()
            return self._row_to_process_schedule(row) if row else None

    def list_all_enabled_process_schedules(self) -> List[ProcessSchedule]:
        """List all enabled process schedules."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM process_schedules WHERE enabled = 1
                ORDER BY process_name, trigger_id
            """)
            return [self._row_to_process_schedule(row) for row in cursor.fetchall()]

    def list_all_process_schedules(self) -> List[ProcessSchedule]:
        """List all process schedules (enabled and disabled) for sync detection."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM process_schedules
                ORDER BY process_name, trigger_id
            """)
            return [self._row_to_process_schedule(row) for row in cursor.fetchall()]

    def list_process_schedules(self, process_id: str) -> List[ProcessSchedule]:
        """List all schedules for a specific process."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM process_schedules WHERE process_id = ?
                ORDER BY trigger_id
            """, (process_id,))
            return [self._row_to_process_schedule(row) for row in cursor.fetchall()]

    def create_process_schedule(
        self,
        process_id: str,
        process_name: str,
        trigger_id: str,
        cron_expression: str,
        timezone: str = "UTC",
        description: str = "",
        enabled: bool = True
    ) -> Optional[ProcessSchedule]:
        """Create a new process schedule."""
        schedule_id = self._generate_id()
        now = datetime.utcnow().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO process_schedules (
                        id, process_id, process_name, trigger_id, cron_expression,
                        enabled, timezone, description, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    schedule_id,
                    process_id,
                    process_name,
                    trigger_id,
                    cron_expression,
                    1 if enabled else 0,
                    timezone,
                    description,
                    now,
                    now
                ))
                conn.commit()

                return ProcessSchedule(
                    id=schedule_id,
                    process_id=process_id,
                    process_name=process_name,
                    trigger_id=trigger_id,
                    cron_expression=cron_expression,
                    enabled=enabled,
                    timezone=timezone,
                    description=description,
                    created_at=datetime.fromisoformat(now),
                    updated_at=datetime.fromisoformat(now)
                )
            except sqlite3.IntegrityError:
                logger.warning(f"Process schedule already exists: {process_id}/{trigger_id}")
                return None

    def update_process_schedule_run_times(
        self,
        schedule_id: str,
        last_run_at: datetime = None,
        next_run_at: datetime = None
    ) -> bool:
        """Update process schedule run timestamps."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = ["updated_at = ?"]
            params = [datetime.utcnow().isoformat()]

            if last_run_at:
                updates.append("last_run_at = ?")
                params.append(last_run_at.isoformat())
            if next_run_at:
                updates.append("next_run_at = ?")
                params.append(next_run_at.isoformat())

            params.append(schedule_id)
            cursor.execute(f"""
                UPDATE process_schedules SET {", ".join(updates)} WHERE id = ?
            """, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_process_schedule(self, schedule_id: str) -> bool:
        """Delete a process schedule."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM process_schedules WHERE id = ?", (schedule_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_process_schedules_for_process(self, process_id: str) -> int:
        """Delete all schedules for a process. Returns count deleted."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM process_schedules WHERE process_id = ?", (process_id,))
            conn.commit()
            return cursor.rowcount

    def create_process_schedule_execution(
        self,
        schedule_id: str,
        process_id: str,
        process_name: str,
        triggered_by: str = "schedule"
    ) -> Optional[ProcessScheduleExecution]:
        """Create a new process schedule execution record."""
        execution_id = self._generate_id()
        now = datetime.utcnow().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO process_schedule_executions (
                    id, schedule_id, process_id, process_name, status, started_at, triggered_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                schedule_id,
                process_id,
                process_name,
                "running",
                now,
                triggered_by
            ))
            conn.commit()

            return ProcessScheduleExecution(
                id=execution_id,
                schedule_id=schedule_id,
                process_id=process_id,
                process_name=process_name,
                execution_id=None,
                status="running",
                started_at=datetime.fromisoformat(now),
                triggered_by=triggered_by
            )

    def create_skipped_process_schedule_execution(
        self,
        schedule_id: str,
        process_id: str,
        process_name: str,
        triggered_by: str = "schedule",
        skip_reason: str = None
    ) -> Optional[ProcessScheduleExecution]:
        """
        Create an execution record for a skipped process schedule.

        This is called when APScheduler fires EVENT_JOB_MAX_INSTANCES,
        indicating that a scheduled process was dropped because the previous
        execution is still running.

        Args:
            schedule_id: ID of the process schedule that was skipped
            process_id: ID of the process definition
            process_name: Name of the process
            triggered_by: Source of the trigger (always "schedule" for skipped)
            skip_reason: Human-readable reason for the skip

        Returns:
            ProcessScheduleExecution with status='skipped', or None on failure
        """
        execution_id = self._generate_id()
        now = datetime.utcnow().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO process_schedule_executions (
                    id, schedule_id, process_id, process_name, status,
                    started_at, completed_at, duration_ms, triggered_by, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                schedule_id,
                process_id,
                process_name,
                "skipped",
                now,
                now,  # completed_at = started_at for skipped
                0,    # duration_ms = 0 for skipped
                triggered_by,
                skip_reason
            ))
            conn.commit()

            return ProcessScheduleExecution(
                id=execution_id,
                schedule_id=schedule_id,
                process_id=process_id,
                process_name=process_name,
                execution_id=None,
                status="skipped",
                started_at=datetime.fromisoformat(now),
                completed_at=datetime.fromisoformat(now),
                duration_ms=0,
                triggered_by=triggered_by,
                error=skip_reason
            )

    def update_process_schedule_execution(
        self,
        execution_id: str,
        status: str,
        process_execution_id: str = None,
        error: str = None
    ) -> bool:
        """Update process schedule execution status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get started_at for duration calculation
            cursor.execute(
                "SELECT started_at FROM process_schedule_executions WHERE id = ?",
                (execution_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False

            started_at = datetime.fromisoformat(row["started_at"])
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            cursor.execute("""
                UPDATE process_schedule_executions
                SET status = ?, completed_at = ?, duration_ms = ?, execution_id = ?, error = ?
                WHERE id = ?
            """, (
                status,
                completed_at.isoformat(),
                duration_ms,
                process_execution_id,
                error,
                execution_id
            ))
            conn.commit()
            return cursor.rowcount > 0
