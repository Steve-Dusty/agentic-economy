"""
SQLite Repository for Domain Events

Implements the EventRepository interface using SQLite for persistence.
Stores execution events for audit logging and debugging.

Reference: BACKLOG_MVP.md - E15-04
"""

import json
import sqlite3
import inspect
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Type, get_type_hints

from ..domain import (
    DomainEvent,
    ExecutionId,
    StepId,
    ProcessId,
    Money,
    Duration,
    Version,
)
from ..domain import events as domain_events
from ..domain.enums import StepType
from .interfaces import EventRepository


def _utcnow() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


class SqliteEventRepository(EventRepository):
    """
    SQLite implementation of EventRepository.
    
    Schema:
    - execution_events: Stores all domain events
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
        self._event_types = self._build_event_type_map()
        self._init_schema()
    
    def _build_event_type_map(self) -> dict[str, Type[DomainEvent]]:
        """Build a map of event type names to event classes."""
        event_map = {}
        # Iterate over all members of domain_events module
        for name, obj in inspect.getmembers(domain_events):
            if (inspect.isclass(obj) and 
                issubclass(obj, DomainEvent) and 
                obj is not DomainEvent):
                event_map[name] = obj
        return event_map
    
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
                CREATE TABLE IF NOT EXISTS execution_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    step_id TEXT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_execution_id 
                    ON execution_events(execution_id);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                    ON execution_events(timestamp);
            """)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()
    
    def save(self, event: DomainEvent) -> None:
        """Save a domain event."""
        conn = self._get_connection()
        try:
            # Extract execution_id and step_id if present
            execution_id = getattr(event, "execution_id", None)
            step_id = getattr(event, "step_id", None)
            
            # For process events that don't have execution_id (like ProcessCreated),
            # we might want to store them differently or just skip execution_id.
            # But the requirement is primarily for Execution Event Log.
            # If execution_id is missing, we can store "global" or similar, 
            # but ProcessStarted/Completed etc have execution_id.
            
            exec_id_str = str(execution_id) if execution_id else "global"
            step_id_str = str(step_id) if step_id else None
            
            now = _utcnow().isoformat()
            
            conn.execute("""
                INSERT INTO execution_events (
                    execution_id, step_id, event_type, payload, timestamp, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                exec_id_str,
                step_id_str,
                event.event_type,
                json.dumps(event.to_dict()),
                event.timestamp.isoformat(),
                now
            ))
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()
    
    def get_by_execution_id(
        self,
        execution_id: ExecutionId,
        limit: int = 100,
        offset: int = 0
    ) -> list[DomainEvent]:
        """Get events for a specific execution."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM execution_events 
                WHERE execution_id = ?
                ORDER BY timestamp ASC
                LIMIT ? OFFSET ?
            """, (str(execution_id), limit, offset))
            
            events = []
            for row in cursor.fetchall():
                event = self._deserialize(row)
                if event:
                    events.append(event)
            
            return events
        finally:
            if not self._is_memory:
                conn.close()
                
    def _deserialize(self, row: sqlite3.Row) -> Optional[DomainEvent]:
        """Deserialize event from database row."""
        event_type = row["event_type"]
        event_cls = self._event_types.get(event_type)
        
        if not event_cls:
            # Fallback or log warning?
            # For now, return None if unknown type
            return None
            
        try:
            payload = json.loads(row["payload"])
            
            # Reconstruct value objects based on annotations
            # This is a bit complex generic reconstruction.
            # Or we can just manual mapping, but that's tedious.
            # Let's try to be smart with kwargs.
            
            kwargs = {}
            type_hints = get_type_hints(event_cls)
            
            for field_name, field_type in type_hints.items():
                if field_name not in payload:
                    continue
                    
                value = payload[field_name]
                
                # Handle specific value objects
                if field_type == ExecutionId and value:
                    kwargs[field_name] = ExecutionId(value)
                elif field_type == ProcessId and value:
                    kwargs[field_name] = ProcessId(value)
                elif field_type == StepId and value:
                    kwargs[field_name] = StepId(value)
                elif field_type == Money and value:
                    if isinstance(value, str):
                        kwargs[field_name] = Money.from_string(value)
                        print(f"DEBUG: Parsed Money {value} -> {kwargs[field_name]}")
                    else:
                        print(f"DEBUG: Money value is not string: {value} type={type(value)}")
                elif field_type == Duration and value:
                    # Saved as seconds in to_dict: "duration_seconds"
                    # Wait, ProcessCompleted.to_dict saves: "total_duration_seconds": self.total_duration.seconds
                    # But the field name is "total_duration".
                    # The payload key might be different from field name.
                    pass 
                elif field_type == datetime and value:
                    kwargs[field_name] = datetime.fromisoformat(value)
                elif field_type == StepType and value:
                    kwargs[field_name] = StepType(value)
                else:
                    kwargs[field_name] = value
            
            # Handle special cases where to_dict keys differ from field names
            # e.g. ProcessCompleted: total_duration vs total_duration_seconds
            if "total_duration" in type_hints:
                secs = payload.get("total_duration_seconds")
                if secs is not None:
                    kwargs["total_duration"] = Duration(int(secs))
                    
            if "duration" in type_hints:
                secs = payload.get("duration_seconds")
                if secs is not None:
                    kwargs["duration"] = Duration(int(secs))

            # Remove keys that aren't fields (like event_type)
            valid_keys = set(type_hints.keys())
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}
            
            # Add timestamp if it's missing (it's in the row)
            if "timestamp" not in filtered_kwargs and "timestamp" in type_hints:
                 filtered_kwargs["timestamp"] = datetime.fromisoformat(row["timestamp"])

            return event_cls(**filtered_kwargs)
            
        except Exception as e:
            print(f"Failed to deserialize event {event_type}: {e}")
            return None
