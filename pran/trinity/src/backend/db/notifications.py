"""
Notification operations for agent notifications (NOTIF-001).

Enables agents to send structured notifications to the Trinity platform.
Notifications are persisted and broadcast via WebSocket.
"""

import json
import secrets
from typing import List, Optional
from datetime import datetime

from db.connection import get_db_connection
from db_models import Notification, NotificationCreate


class NotificationOperations:
    """Database operations for agent notifications."""

    def create_notification(
        self,
        agent_name: str,
        data: NotificationCreate
    ) -> Notification:
        """
        Create a new notification.

        Args:
            agent_name: The agent sending the notification
            data: Notification data

        Returns:
            The created notification
        """
        notification_id = f"notif_{secrets.token_urlsafe(12)}"
        now = datetime.utcnow().isoformat() + "Z"

        # Serialize metadata to JSON if provided
        metadata_json = json.dumps(data.metadata) if data.metadata else None

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_notifications (
                    id, agent_name, notification_type, title, message,
                    priority, category, metadata, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notification_id,
                agent_name,
                data.notification_type,
                data.title[:200],  # Enforce max length
                data.message,
                data.priority,
                data.category,
                metadata_json,
                "pending",
                now
            ))
            conn.commit()

        return Notification(
            id=notification_id,
            agent_name=agent_name,
            notification_type=data.notification_type,
            title=data.title[:200],
            message=data.message,
            priority=data.priority,
            category=data.category,
            metadata=data.metadata,
            status="pending",
            created_at=now,
            acknowledged_at=None,
            acknowledged_by=None
        )

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """
        Get a notification by ID.

        Args:
            notification_id: The notification ID

        Returns:
            The notification or None if not found
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, agent_name, notification_type, title, message,
                       priority, category, metadata, status, created_at,
                       acknowledged_at, acknowledged_by
                FROM agent_notifications
                WHERE id = ?
            """, (notification_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_notification(row)

    def list_notifications(
        self,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[List[str]] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Notification]:
        """
        List notifications with optional filters.

        Args:
            agent_name: Filter by agent name
            status: Filter by status (pending, acknowledged, dismissed)
            priority: Filter by priority levels
            category: Filter by category (e.g., 'health' for monitoring alerts)
            limit: Maximum number of results

        Returns:
            List of notifications
        """
        query = """
            SELECT id, agent_name, notification_type, title, message,
                   priority, category, metadata, status, created_at,
                   acknowledged_at, acknowledged_by
            FROM agent_notifications
            WHERE 1=1
        """
        params = []

        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)

        if status:
            query += " AND status = ?"
            params.append(status)

        if priority:
            placeholders = ",".join("?" * len(priority))
            query += f" AND priority IN ({placeholders})"
            params.extend(priority)

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [self._row_to_notification(row) for row in rows]

    def list_agent_notifications(
        self,
        agent_name: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Notification]:
        """
        List notifications for a specific agent.

        Args:
            agent_name: The agent name
            status: Optional status filter
            limit: Maximum number of results

        Returns:
            List of notifications
        """
        return self.list_notifications(
            agent_name=agent_name,
            status=status,
            limit=limit
        )

    def acknowledge_notification(
        self,
        notification_id: str,
        acknowledged_by: str
    ) -> Optional[Notification]:
        """
        Acknowledge a notification.

        Args:
            notification_id: The notification ID
            acknowledged_by: User ID who acknowledged

        Returns:
            The updated notification or None if not found
        """
        now = datetime.utcnow().isoformat() + "Z"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_notifications
                SET status = 'acknowledged',
                    acknowledged_at = ?,
                    acknowledged_by = ?
                WHERE id = ? AND status = 'pending'
            """, (now, acknowledged_by, notification_id))
            conn.commit()

            if cursor.rowcount == 0:
                # Check if notification exists
                cursor.execute(
                    "SELECT id FROM agent_notifications WHERE id = ?",
                    (notification_id,)
                )
                if not cursor.fetchone():
                    return None

        return self.get_notification(notification_id)

    def dismiss_notification(
        self,
        notification_id: str,
        dismissed_by: str
    ) -> Optional[Notification]:
        """
        Dismiss a notification.

        Args:
            notification_id: The notification ID
            dismissed_by: User ID who dismissed

        Returns:
            The updated notification or None if not found
        """
        now = datetime.utcnow().isoformat() + "Z"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_notifications
                SET status = 'dismissed',
                    acknowledged_at = ?,
                    acknowledged_by = ?
                WHERE id = ?
            """, (now, dismissed_by, notification_id))
            conn.commit()

            if cursor.rowcount == 0:
                return None

        return self.get_notification(notification_id)

    def delete_agent_notifications(self, agent_name: str) -> int:
        """
        Delete all notifications for an agent.

        Args:
            agent_name: The agent name

        Returns:
            Number of notifications deleted
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM agent_notifications WHERE agent_name = ?",
                (agent_name,)
            )
            conn.commit()
            return cursor.rowcount

    def count_pending_notifications(
        self,
        agent_name: Optional[str] = None
    ) -> int:
        """
        Count pending notifications.

        Args:
            agent_name: Optional filter by agent

        Returns:
            Count of pending notifications
        """
        query = "SELECT COUNT(*) FROM agent_notifications WHERE status = 'pending'"
        params = []

        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def _row_to_notification(self, row: tuple) -> Notification:
        """Convert a database row to a Notification model."""
        metadata = None
        if row[7]:  # metadata column
            try:
                metadata = json.loads(row[7])
            except json.JSONDecodeError:
                pass

        return Notification(
            id=row[0],
            agent_name=row[1],
            notification_type=row[2],
            title=row[3],
            message=row[4],
            priority=row[5],
            category=row[6],
            metadata=metadata,
            status=row[8],
            created_at=row[9],
            acknowledged_at=row[10],
            acknowledged_by=row[11]
        )
