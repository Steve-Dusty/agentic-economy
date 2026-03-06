"""
System Views operations for agent organization (ORG-001 Phase 2).

System Views are saved filters that group agents by tags.
Views can be private (owned) or shared (visible to all users).
"""

import json
import secrets
from typing import List, Optional
from datetime import datetime

from db.connection import get_db_connection
from db_models import SystemView, SystemViewCreate, SystemViewUpdate


class SystemViewOperations:
    """Database operations for system views."""

    def create_view(self, owner_id: str, data: SystemViewCreate) -> SystemView:
        """
        Create a new system view.

        Args:
            owner_id: The user ID creating the view
            data: View creation data

        Returns:
            The created SystemView
        """
        view_id = f"sv_{secrets.token_urlsafe(12)}"
        now = datetime.utcnow().isoformat() + "Z"

        # Normalize and validate tags
        filter_tags = sorted(set(t.lower().strip() for t in data.filter_tags if t.strip()))

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_views (
                    id, name, description, icon, color, filter_tags,
                    owner_id, is_shared, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                view_id,
                data.name.strip(),
                data.description.strip() if data.description else None,
                data.icon,
                data.color,
                json.dumps(filter_tags),
                owner_id,
                1 if data.is_shared else 0,
                now,
                now
            ))
            conn.commit()

            return self.get_view(view_id)

    def get_view(self, view_id: str) -> Optional[SystemView]:
        """Get a system view by ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sv.id, sv.name, sv.description, sv.icon, sv.color,
                       sv.filter_tags, sv.owner_id, sv.is_shared,
                       sv.created_at, sv.updated_at,
                       u.email as owner_email
                FROM system_views sv
                LEFT JOIN users u ON sv.owner_id = u.id
                WHERE sv.id = ?
            """, (view_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_view(row, cursor)

    def list_user_views(self, user_id: str) -> List[SystemView]:
        """
        List all views accessible to a user (owned + shared).

        Args:
            user_id: The user ID

        Returns:
            List of SystemView objects sorted by name
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sv.id, sv.name, sv.description, sv.icon, sv.color,
                       sv.filter_tags, sv.owner_id, sv.is_shared,
                       sv.created_at, sv.updated_at,
                       u.email as owner_email
                FROM system_views sv
                LEFT JOIN users u ON sv.owner_id = u.id
                WHERE sv.owner_id = ? OR sv.is_shared = 1
                ORDER BY sv.name ASC
            """, (user_id,))

            views = []
            for row in cursor.fetchall():
                views.append(self._row_to_view(row, cursor))

            return views

    def list_all_views(self) -> List[SystemView]:
        """List all system views (admin use)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sv.id, sv.name, sv.description, sv.icon, sv.color,
                       sv.filter_tags, sv.owner_id, sv.is_shared,
                       sv.created_at, sv.updated_at,
                       u.email as owner_email
                FROM system_views sv
                LEFT JOIN users u ON sv.owner_id = u.id
                ORDER BY sv.name ASC
            """)

            views = []
            for row in cursor.fetchall():
                views.append(self._row_to_view(row, cursor))

            return views

    def update_view(self, view_id: str, data: SystemViewUpdate) -> Optional[SystemView]:
        """
        Update a system view.

        Args:
            view_id: The view ID
            data: Update data (only provided fields are updated)

        Returns:
            The updated SystemView or None if not found
        """
        updates = []
        params = []

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name.strip())

        if data.description is not None:
            updates.append("description = ?")
            params.append(data.description.strip() if data.description else None)

        if data.icon is not None:
            updates.append("icon = ?")
            params.append(data.icon)

        if data.color is not None:
            updates.append("color = ?")
            params.append(data.color)

        if data.filter_tags is not None:
            filter_tags = sorted(set(t.lower().strip() for t in data.filter_tags if t.strip()))
            updates.append("filter_tags = ?")
            params.append(json.dumps(filter_tags))

        if data.is_shared is not None:
            updates.append("is_shared = ?")
            params.append(1 if data.is_shared else 0)

        if not updates:
            return self.get_view(view_id)

        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat() + "Z")
        params.append(view_id)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE system_views
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            conn.commit()

            if cursor.rowcount == 0:
                return None

            return self.get_view(view_id)

    def delete_view(self, view_id: str) -> bool:
        """
        Delete a system view.

        Args:
            view_id: The view ID

        Returns:
            True if deleted, False if not found
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_views WHERE id = ?", (view_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_view_owner(self, view_id: str) -> Optional[str]:
        """Get the owner_id of a view."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT owner_id FROM system_views WHERE id = ?", (view_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def can_user_edit_view(self, user_id: str, view_id: str, is_admin: bool = False) -> bool:
        """Check if a user can edit a view (owner or admin)."""
        if is_admin:
            return True
        owner_id = self.get_view_owner(view_id)
        return owner_id == user_id

    def can_user_view(self, user_id: str, view_id: str) -> bool:
        """Check if a user can view a system view (owner or shared)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM system_views
                WHERE id = ? AND (owner_id = ? OR is_shared = 1)
            """, (view_id, user_id))
            return cursor.fetchone() is not None

    def _row_to_view(self, row, cursor) -> SystemView:
        """Convert a database row to a SystemView object with agent count."""
        filter_tags = json.loads(row[5]) if row[5] else []

        # Count agents matching any of the filter tags
        agent_count = 0
        if filter_tags:
            placeholders = ",".join("?" * len(filter_tags))
            cursor.execute(f"""
                SELECT COUNT(DISTINCT agent_name)
                FROM agent_tags
                WHERE tag IN ({placeholders})
            """, filter_tags)
            result = cursor.fetchone()
            agent_count = result[0] if result else 0

        return SystemView(
            id=row[0],
            name=row[1],
            description=row[2],
            icon=row[3],
            color=row[4],
            filter_tags=filter_tags,
            owner_id=row[6],
            owner_email=row[10],
            is_shared=bool(row[7]),
            agent_count=agent_count,
            created_at=row[8],
            updated_at=row[9]
        )
