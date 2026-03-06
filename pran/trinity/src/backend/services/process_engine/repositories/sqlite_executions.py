"""
SQLite Repository for Process Executions

Implements the ProcessExecutionRepository interface using SQLite
for persistence. Stores both the main execution record and 
individual step execution states.

Reference: BACKLOG_MVP.md - E2-02
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..domain import (
    ProcessExecution,
    ProcessId,
    ExecutionId,
    ExecutionStatus,
    StepExecution,
    StepId,
    StepStatus,
    Version,
    Money,
)
from .interfaces import ProcessExecutionRepository


def _utcnow() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


class SqliteProcessExecutionRepository(ProcessExecutionRepository):
    """
    SQLite implementation of ProcessExecutionRepository.
    
    Schema:
    - process_executions: Main execution record
    - step_executions: Per-step state (could be denormalized in main record,
                       but keeping separate for query flexibility)
    """
    
    def __init__(self, db_path: str | Path):
        """
        Initialize repository with database path.
        
        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory DB
        """
        self.db_path = str(db_path)
        self._is_memory = self.db_path == ":memory:"
        self._memory_conn: Optional[sqlite3.Connection] = None
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._is_memory:
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
    
    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS process_executions (
                    id TEXT PRIMARY KEY,
                    process_id TEXT NOT NULL,
                    process_version TEXT NOT NULL,
                    process_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    triggered_by TEXT DEFAULT 'manual',
                    input_data TEXT DEFAULT '{}',
                    output_data TEXT DEFAULT '{}',
                    total_cost_amount INTEGER DEFAULT 0,
                    total_cost_currency TEXT DEFAULT 'USD',
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_exec_process_id 
                    ON process_executions(process_id);
                CREATE INDEX IF NOT EXISTS idx_exec_status 
                    ON process_executions(status);
                CREATE INDEX IF NOT EXISTS idx_exec_started_at 
                    ON process_executions(started_at);
                    
                CREATE TABLE IF NOT EXISTS step_executions (
                    execution_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_data TEXT DEFAULT '{}',
                    output_data TEXT DEFAULT '{}',
                    error_data TEXT DEFAULT '{}',
                    cost_amount INTEGER DEFAULT 0,
                    cost_currency TEXT DEFAULT 'USD',
                    started_at TEXT,
                    completed_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    PRIMARY KEY (execution_id, step_id),
                    FOREIGN KEY (execution_id) REFERENCES process_executions(id)
                        ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_step_exec_status 
                    ON step_executions(status);
            """)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()
    
    # =========================================================================
    # Repository Interface Implementation
    # =========================================================================
    
    def save(self, execution: ProcessExecution) -> None:
        """Save or update an execution."""
        conn = self._get_connection()
        try:
            now = _utcnow().isoformat()
            
            # Upsert main execution record
            # Store amount as cents (multiply by 100)
            cost_cents = int(execution.total_cost.amount * 100)
            
            conn.execute("""
                INSERT OR REPLACE INTO process_executions (
                    id, process_id, process_version, process_name,
                    status, triggered_by, input_data, output_data,
                    total_cost_amount, total_cost_currency,
                    started_at, completed_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM process_executions WHERE id = ?), ?),
                    ?)
            """, (
                str(execution.id),
                str(execution.process_id),
                str(execution.process_version),
                execution.process_name,
                execution.status.value,
                execution.triggered_by,
                json.dumps(execution.input_data),
                json.dumps(execution.output_data),
                cost_cents,  # Store as cents
                execution.total_cost.currency,
                execution.started_at.isoformat() if execution.started_at else None,
                execution.completed_at.isoformat() if execution.completed_at else None,
                str(execution.id),  # For COALESCE
                now,  # created_at if new
                now,  # updated_at
            ))
            
            # Save step executions
            for step_id, step_exec in execution.step_executions.items():
                self._save_step_execution(conn, str(execution.id), step_exec)
            
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()
    
    def _save_step_execution(
        self,
        conn: sqlite3.Connection,
        execution_id: str,
        step_exec: StepExecution,
    ) -> None:
        """Save a single step execution."""
        # Store cost as cents
        cost_cents = int(step_exec.cost.amount * 100) if step_exec.cost else 0
        
        conn.execute("""
            INSERT OR REPLACE INTO step_executions (
                execution_id, step_id, status,
                input_data, output_data, error_data,
                cost_amount, cost_currency,
                started_at, completed_at, retry_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution_id,
            str(step_exec.step_id),
            step_exec.status.value,
            json.dumps(step_exec.input or {}),
            json.dumps(step_exec.output or {}),
            json.dumps(step_exec.error or {}),
            cost_cents,  # Store as cents
            step_exec.cost.currency if step_exec.cost else "USD",
            step_exec.started_at.isoformat() if step_exec.started_at else None,
            step_exec.completed_at.isoformat() if step_exec.completed_at else None,
            step_exec.retry_count,
        ))
    
    def get_by_id(self, id: ExecutionId) -> Optional[ProcessExecution]:
        """Get execution by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM process_executions WHERE id = ?",
                (str(id),)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            
            # Get step executions
            step_cursor = conn.execute(
                "SELECT * FROM step_executions WHERE execution_id = ?",
                (str(id),)
            )
            step_rows = step_cursor.fetchall()
            
            return self._deserialize(row, step_rows)
        finally:
            if not self._is_memory:
                conn.close()
    
    def update(self, execution: ProcessExecution) -> None:
        """Update an existing execution."""
        # Same as save - upsert pattern
        self.save(execution)
    
    def delete(self, id: ExecutionId) -> bool:
        """Delete an execution."""
        conn = self._get_connection()
        try:
            # Delete step executions first (cascade should handle this, but be explicit)
            conn.execute(
                "DELETE FROM step_executions WHERE execution_id = ?",
                (str(id),)
            )
            cursor = conn.execute(
                "DELETE FROM process_executions WHERE id = ?",
                (str(id),)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if not self._is_memory:
                conn.close()
    
    def list_by_process(
        self,
        process_id: ProcessId,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProcessExecution]:
        """List executions for a specific process."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM process_executions 
                WHERE process_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (str(process_id), limit, offset))
            
            results = []
            for row in cursor.fetchall():
                step_cursor = conn.execute(
                    "SELECT * FROM step_executions WHERE execution_id = ?",
                    (row["id"],)
                )
                results.append(self._deserialize(row, step_cursor.fetchall()))
            
            return results
        finally:
            if not self._is_memory:
                conn.close()
    
    def list_active(self) -> list[ProcessExecution]:
        """List all active (running/pending/paused) executions."""
        conn = self._get_connection()
        try:
            active_statuses = (
                ExecutionStatus.PENDING.value,
                ExecutionStatus.RUNNING.value,
                ExecutionStatus.PAUSED.value,
            )
            cursor = conn.execute("""
                SELECT * FROM process_executions 
                WHERE status IN (?, ?, ?)
                ORDER BY started_at ASC
            """, active_statuses)
            
            results = []
            for row in cursor.fetchall():
                step_cursor = conn.execute(
                    "SELECT * FROM step_executions WHERE execution_id = ?",
                    (row["id"],)
                )
                results.append(self._deserialize(row, step_cursor.fetchall()))
            
            return results
        finally:
            if not self._is_memory:
                conn.close()
    
    def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[ExecutionStatus] = None,
    ) -> list[ProcessExecution]:
        """List all executions with optional filtering."""
        conn = self._get_connection()
        try:
            if status:
                cursor = conn.execute("""
                    SELECT * FROM process_executions 
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (status.value, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT * FROM process_executions 
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            results = []
            for row in cursor.fetchall():
                step_cursor = conn.execute(
                    "SELECT * FROM step_executions WHERE execution_id = ?",
                    (row["id"],)
                )
                results.append(self._deserialize(row, step_cursor.fetchall()))
            
            return results
        finally:
            if not self._is_memory:
                conn.close()
    
    def count(self, status: Optional[ExecutionStatus] = None) -> int:
        """Count executions with optional status filter."""
        conn = self._get_connection()
        try:
            if status:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM process_executions WHERE status = ?",
                    (status.value,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM process_executions")
            return cursor.fetchone()[0]
        finally:
            if not self._is_memory:
                conn.close()
    
    def exists(self, id: ExecutionId) -> bool:
        """Check if an execution exists."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM process_executions WHERE id = ?",
                (str(id),)
            )
            return cursor.fetchone() is not None
        finally:
            if not self._is_memory:
                conn.close()
    
    # =========================================================================
    # Serialization / Deserialization
    # =========================================================================
    
    def _deserialize(
        self,
        row: sqlite3.Row,
        step_rows: list[sqlite3.Row],
    ) -> ProcessExecution:
        """Deserialize from database rows."""
        from decimal import Decimal
        
        # Parse step executions
        step_executions = {}
        for step_row in step_rows:
            # Convert cents back to dollars
            step_cost = None
            if step_row["cost_amount"]:
                step_cost = Money(
                    amount=Decimal(step_row["cost_amount"]) / 100,
                    currency=step_row["cost_currency"]
                )
            
            step_exec = StepExecution(
                step_id=StepId(step_row["step_id"]),
                status=StepStatus(step_row["status"]),
                input=json.loads(step_row["input_data"]) if step_row["input_data"] else None,
                output=json.loads(step_row["output_data"]) if step_row["output_data"] else None,
                error=json.loads(step_row["error_data"]) if step_row["error_data"] else None,
                cost=step_cost,
                started_at=datetime.fromisoformat(step_row["started_at"]) if step_row["started_at"] else None,
                completed_at=datetime.fromisoformat(step_row["completed_at"]) if step_row["completed_at"] else None,
                retry_count=step_row["retry_count"],
            )
            step_executions[step_row["step_id"]] = step_exec
        
        # Convert cents back to dollars for total cost
        total_cost = Money(
            amount=Decimal(row["total_cost_amount"]) / 100,
            currency=row["total_cost_currency"]
        )
        
        execution = ProcessExecution(
            id=ExecutionId(row["id"]),
            process_id=ProcessId(row["process_id"]),
            process_version=Version.from_string(row["process_version"]),
            process_name=row["process_name"],
            status=ExecutionStatus(row["status"]),
            step_executions=step_executions,
            input_data=json.loads(row["input_data"]) if row["input_data"] else {},
            output_data=json.loads(row["output_data"]) if row["output_data"] else {},
            triggered_by=row["triggered_by"],
            total_cost=total_cost,
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )
        
        return execution
