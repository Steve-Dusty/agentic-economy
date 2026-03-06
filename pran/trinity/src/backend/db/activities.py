"""
Activity stream database operations.

Handles activity logging for real-time state monitoring and tool-level observability.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict

from .connection import get_db_connection
from utils.helpers import utc_now_iso, to_utc_iso, parse_iso_timestamp


class ActivityOperations:
    """Activity stream database operations."""

    @staticmethod
    def _row_to_activity(row) -> Dict:
        """Convert database row to activity dict."""
        return {
            "id": row[0],
            "agent_name": row[1],
            "activity_type": row[2],
            "activity_state": row[3],
            "parent_activity_id": row[4],
            "started_at": row[5],
            "completed_at": row[6],
            "duration_ms": row[7],
            "user_id": row[8],
            "triggered_by": row[9],
            "related_chat_message_id": row[10],
            "related_execution_id": row[11],
            "details": json.loads(row[12]) if row[12] else None,
            "error": row[13],
            "created_at": row[14]
        }

    def create_activity(self, activity: 'ActivityCreate') -> str:
        """Create a new activity record. Returns activity_id."""
        from models import ActivityType, ActivityState

        activity_id = str(uuid.uuid4())
        now = utc_now_iso()  # Use UTC with 'Z' suffix for frontend compatibility

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_activities (
                    id, agent_name, activity_type, activity_state, parent_activity_id,
                    started_at, user_id, triggered_by, related_chat_message_id,
                    related_execution_id, details, error, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                activity_id,
                activity.agent_name,
                activity.activity_type.value if isinstance(activity.activity_type, ActivityType) else activity.activity_type,
                activity.activity_state.value if isinstance(activity.activity_state, ActivityState) else activity.activity_state,
                activity.parent_activity_id,
                now,
                activity.user_id,
                activity.triggered_by,
                activity.related_chat_message_id,
                activity.related_execution_id,
                json.dumps(activity.details) if activity.details else None,
                activity.error,
                now
            ))
            conn.commit()

        return activity_id

    def complete_activity(self, activity_id: str, status: str = "completed",
                         details: Optional[Dict] = None, error: Optional[str] = None) -> bool:
        """
        Complete an activity by updating its state, completion time, and duration.
        Returns True if activity was found and updated.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get start time to calculate duration
            cursor.execute("SELECT started_at, details FROM agent_activities WHERE id = ?", (activity_id,))
            row = cursor.fetchone()
            if not row:
                return False

            # Use parse_iso_timestamp to handle both 'Z' and non-'Z' timestamps
            started_at = parse_iso_timestamp(row[0])
            completed_at = parse_iso_timestamp(utc_now_iso())
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            # Merge existing details with new details
            existing_details = json.loads(row[1]) if row[1] else {}
            if details:
                existing_details.update(details)

            cursor.execute("""
                UPDATE agent_activities
                SET activity_state = ?,
                    completed_at = ?,
                    duration_ms = ?,
                    details = ?,
                    error = ?
                WHERE id = ?
            """, (
                status,
                to_utc_iso(completed_at),  # Use UTC with 'Z' suffix
                duration_ms,
                json.dumps(existing_details) if existing_details else None,
                error,
                activity_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def get_activity(self, activity_id: str) -> Optional[Dict]:
        """Get a single activity by ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_activities WHERE id = ?", (activity_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_activity(row)

    def get_agent_activities(self, agent_name: str, activity_type: Optional[str] = None,
                            activity_state: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Get activities for a specific agent.
        Optionally filter by activity_type and/or activity_state.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM agent_activities WHERE agent_name = ?"
            params = [agent_name]

            if activity_type:
                query += " AND activity_type = ?"
                params.append(activity_type)

            if activity_state:
                query += " AND activity_state = ?"
                params.append(activity_state)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [self._row_to_activity(row) for row in cursor.fetchall()]

    def get_activities_in_range(self, start_time: Optional[str] = None,
                                end_time: Optional[str] = None,
                                activity_types: Optional[List[str]] = None,
                                limit: int = 100) -> List[Dict]:
        """
        Get activities across all agents in a time range.
        Optionally filter by activity types.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM agent_activities WHERE 1=1"
            params = []

            if start_time:
                query += " AND created_at >= ?"
                params.append(start_time)

            if end_time:
                query += " AND created_at <= ?"
                params.append(end_time)

            if activity_types:
                placeholders = ",".join("?" * len(activity_types))
                query += f" AND activity_type IN ({placeholders})"
                params.extend(activity_types)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [self._row_to_activity(row) for row in cursor.fetchall()]

    def get_current_activities(self, agent_name: str) -> List[Dict]:
        """Get all in-progress (started) activities for an agent."""
        return self.get_agent_activities(
            agent_name=agent_name,
            activity_state="started",
            limit=50
        )
