"""
SQLite Implementation of ProcessDefinitionRepository

Stores process definitions in SQLite database for durable storage.

Reference: IT3 Section 7 (Repositories)
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .interfaces import ProcessDefinitionRepository
from ..domain import (
    ProcessDefinition,
    ProcessId,
    Version,
    DefinitionStatus,
    StepDefinition,
    OutputConfig,
    parse_trigger_config,
)


def _utcnow() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


class SqliteProcessDefinitionRepository(ProcessDefinitionRepository):
    """
    SQLite implementation for process definitions.
    
    Stores definitions as JSON in SQLite for simplicity and portability.
    Uses separate columns for frequently-queried fields (name, version, status).
    """

    def __init__(self, db_path: str | Path):
        """
        Initialize repository with database path.
        
        Args:
            db_path: Path to SQLite database file. 
                     Use ":memory:" for in-memory database (testing).
        """
        self.db_path = str(db_path)
        self._is_memory = self.db_path == ":memory:"
        self._memory_conn: Optional[sqlite3.Connection] = None
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        if self._is_memory:
            # For in-memory databases, reuse the same connection
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn

    def _init_schema(self) -> None:
        """Initialize database schema if not exists."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS process_definitions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version_major INTEGER NOT NULL,
                    version_minor INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    description TEXT,
                    definition_json TEXT NOT NULL,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    published_at TEXT
                )
            """)
            
            # Index for name lookup
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_process_definitions_name 
                ON process_definitions(name)
            """)
            
            # Index for status filtering
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_process_definitions_status
                ON process_definitions(status)
            """)
            
            # Unique constraint on name + version
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_process_definitions_name_version
                ON process_definitions(name, version_major, version_minor)
            """)
            
            conn.commit()

    def _serialize(self, definition: ProcessDefinition) -> dict:
        """Serialize ProcessDefinition to database row."""
        return {
            "id": str(definition.id),
            "name": definition.name,
            "version_major": definition.version.major,
            "version_minor": definition.version.minor,
            "status": definition.status.value,
            "description": definition.description,
            "definition_json": json.dumps(definition.to_dict()),
            "created_by": definition.created_by,
            "created_at": definition.created_at.isoformat(),
            "updated_at": definition.updated_at.isoformat(),
            "published_at": definition.published_at.isoformat() if definition.published_at else None,
        }

    def _deserialize(self, row: sqlite3.Row) -> ProcessDefinition:
        """Deserialize database row to ProcessDefinition."""
        data = json.loads(row["definition_json"])
        
        # Parse steps
        steps = [StepDefinition.from_dict(s) for s in data.get("steps", [])]
        
        # Parse outputs
        outputs = [OutputConfig.from_dict(o) for o in data.get("outputs", [])]
        
        # Parse triggers
        triggers = [parse_trigger_config(t) for t in data.get("triggers", [])]
        
        # Parse timestamps
        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])
        published_at = datetime.fromisoformat(row["published_at"]) if row["published_at"] else None
        
        return ProcessDefinition(
            id=ProcessId(row["id"]),
            name=row["name"],
            description=row["description"] or "",
            version=Version(major=row["version_major"], minor=row["version_minor"]),
            status=DefinitionStatus(row["status"]),
            steps=steps,
            outputs=outputs,
            triggers=triggers,
            created_by=row["created_by"],
            created_at=created_at,
            updated_at=updated_at,
            published_at=published_at,
        )

    def save(self, definition: ProcessDefinition) -> None:
        """Save or update a process definition."""
        data = self._serialize(definition)
        
        with self._get_connection() as conn:
            # Use INSERT OR REPLACE for upsert behavior
            conn.execute("""
                INSERT OR REPLACE INTO process_definitions
                (id, name, version_major, version_minor, status, description,
                 definition_json, created_by, created_at, updated_at, published_at)
                VALUES
                (:id, :name, :version_major, :version_minor, :status, :description,
                 :definition_json, :created_by, :created_at, :updated_at, :published_at)
            """, data)
            conn.commit()

    def get_by_id(self, id: ProcessId) -> Optional[ProcessDefinition]:
        """Get definition by its unique ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM process_definitions WHERE id = ?",
                (str(id),)
            )
            row = cursor.fetchone()
            
            if row:
                return self._deserialize(row)
            return None

    def get_by_name(
        self,
        name: str,
        version: Optional[Version] = None
    ) -> Optional[ProcessDefinition]:
        """Get definition by name, optionally for a specific version."""
        with self._get_connection() as conn:
            if version:
                # Get specific version
                cursor = conn.execute(
                    """SELECT * FROM process_definitions 
                       WHERE name = ? AND version_major = ? AND version_minor = ?""",
                    (name, version.major, version.minor)
                )
            else:
                # Get latest published version
                cursor = conn.execute(
                    """SELECT * FROM process_definitions 
                       WHERE name = ? AND status = ?
                       ORDER BY version_major DESC, version_minor DESC
                       LIMIT 1""",
                    (name, DefinitionStatus.PUBLISHED.value)
                )
            
            row = cursor.fetchone()
            if row:
                return self._deserialize(row)
            return None

    def get_latest_version(self, name: str) -> Optional[ProcessDefinition]:
        """Get the latest published version of a process by name."""
        return self.get_by_name(name, version=None)

    def list_all(
        self,
        status: Optional[DefinitionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProcessDefinition]:
        """List all definitions, optionally filtered by status."""
        with self._get_connection() as conn:
            if status:
                cursor = conn.execute(
                    """SELECT * FROM process_definitions 
                       WHERE status = ?
                       ORDER BY updated_at DESC
                       LIMIT ? OFFSET ?""",
                    (status.value, limit, offset)
                )
            else:
                cursor = conn.execute(
                    """SELECT * FROM process_definitions 
                       ORDER BY updated_at DESC
                       LIMIT ? OFFSET ?""",
                    (limit, offset)
                )
            
            return [self._deserialize(row) for row in cursor.fetchall()]

    def list_by_name(self, name: str) -> list[ProcessDefinition]:
        """List all versions of a process by name."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM process_definitions 
                   WHERE name = ?
                   ORDER BY version_major DESC, version_minor DESC""",
                (name,)
            )
            return [self._deserialize(row) for row in cursor.fetchall()]

    def delete(self, id: ProcessId) -> bool:
        """Delete a process definition by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM process_definitions WHERE id = ?",
                (str(id),)
            )
            conn.commit()
            return cursor.rowcount > 0

    def exists(self, id: ProcessId) -> bool:
        """Check if a definition exists by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM process_definitions WHERE id = ?",
                (str(id),)
            )
            return cursor.fetchone() is not None

    def count(self, status: Optional[DefinitionStatus] = None) -> int:
        """Count definitions, optionally filtered by status."""
        with self._get_connection() as conn:
            if status:
                cursor = conn.execute(
                    "SELECT COUNT(*) as cnt FROM process_definitions WHERE status = ?",
                    (status.value,)
                )
            else:
                cursor = conn.execute(
                    "SELECT COUNT(*) as cnt FROM process_definitions"
                )
            return cursor.fetchone()["cnt"]
