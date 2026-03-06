"""
SQLite Audit Repository

Append-only storage for audit entries.

Reference: IT5 Section 5.4 (Audit Trail)
Reference: BACKLOG_ACCESS_AUDIT.md - E18-02
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional, List

from ..services.audit import (
    AuditRepository,
    AuditEntry,
    AuditId,
    AuditFilter,
)

logger = logging.getLogger(__name__)


class SqliteAuditRepository(AuditRepository):
    """
    SQLite implementation of the audit repository.

    Features:
    - Append-only: no update or delete operations
    - Indexed for efficient filtering
    - Thread-safe with check_same_thread=False

    Reference: IT5 Section 5.4
    """

    def __init__(self, db_path: str):
        """
        Initialize the repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Create audit_entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_entries (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_entries(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_actor
                ON audit_entries(actor)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_action
                ON audit_entries(action)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_resource
                ON audit_entries(resource_type, resource_id)
            """)

            conn.commit()
            logger.info(f"Audit repository initialized at {self.db_path}")
        finally:
            conn.close()

    async def append(self, entry: AuditEntry) -> None:
        """
        Append an audit entry (async version).

        Args:
            entry: The audit entry to store
        """
        self.append_sync(entry)

    def append_sync(self, entry: AuditEntry) -> None:
        """
        Append an audit entry (sync version).

        Args:
            entry: The audit entry to store
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_entries
                (id, timestamp, actor, action, resource_type, resource_id,
                 details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(entry.id),
                    entry.timestamp.isoformat(),
                    entry.actor,
                    entry.action,
                    entry.resource_type,
                    entry.resource_id,
                    json.dumps(entry.details) if entry.details else None,
                    entry.ip_address,
                    entry.user_agent,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    async def get_by_id(self, audit_id: AuditId) -> Optional[AuditEntry]:
        """
        Get a single entry by ID.

        Args:
            audit_id: ID of the entry to retrieve

        Returns:
            The audit entry or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM audit_entries WHERE id = ?",
                (str(audit_id),)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
            return None
        finally:
            conn.close()

    async def list(
        self,
        filter: Optional[AuditFilter] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """
        List entries with optional filters.

        Args:
            filter: Optional filters to apply
            limit: Maximum entries to return
            offset: Number of entries to skip

        Returns:
            List of matching audit entries
        """
        conn = self._get_connection()
        try:
            query = "SELECT * FROM audit_entries"
            params: list = []

            query, params = self._apply_filters(query, params, filter)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.cursor()
            cursor.execute(query, params)

            return [self._row_to_entry(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    async def count(self, filter: Optional[AuditFilter] = None) -> int:
        """
        Count entries matching a filter.

        Args:
            filter: Optional filters to apply

        Returns:
            Number of matching entries
        """
        conn = self._get_connection()
        try:
            query = "SELECT COUNT(*) FROM audit_entries"
            params: list = []

            query, params = self._apply_filters(query, params, filter)

            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def _apply_filters(
        self,
        query: str,
        params: list,
        filter: Optional[AuditFilter],
    ) -> tuple[str, list]:
        """Apply filters to a query."""
        if filter is None:
            return query, params

        conditions = []

        if filter.actor:
            conditions.append("actor = ?")
            params.append(filter.actor)

        if filter.action:
            conditions.append("action = ?")
            params.append(filter.action)

        if filter.resource_type:
            conditions.append("resource_type = ?")
            params.append(filter.resource_type)

        if filter.resource_id:
            conditions.append("resource_id = ?")
            params.append(filter.resource_id)

        if filter.from_date:
            conditions.append("timestamp >= ?")
            params.append(filter.from_date.isoformat())

        if filter.to_date:
            conditions.append("timestamp <= ?")
            params.append(filter.to_date.isoformat())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        return query, params

    def _row_to_entry(self, row: sqlite3.Row) -> AuditEntry:
        """Convert a database row to an AuditEntry."""
        details = {}
        if row["details"]:
            try:
                details = json.loads(row["details"])
            except json.JSONDecodeError:
                details = {}

        return AuditEntry(
            id=AuditId(row["id"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            actor=row["actor"],
            action=row["action"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            details=details,
            ip_address=row["ip_address"],
            user_agent=row["user_agent"],
        )
