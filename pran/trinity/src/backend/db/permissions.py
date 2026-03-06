"""
Agent-to-agent permissions database operations.

Phase 9.10: Centralized permission system controlling which agents
can communicate with other agents.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List

from .connection import get_db_connection
from db_models import AgentPermission


class PermissionOperations:
    """Agent-to-agent permission database operations."""

    def __init__(self, user_ops, agent_ops):
        """Initialize with references to user and agent operations."""
        self._user_ops = user_ops
        self._agent_ops = agent_ops

    @staticmethod
    def _row_to_permission(row) -> AgentPermission:
        """Convert a permission row to an AgentPermission model."""
        return AgentPermission(
            id=row["id"],
            source_agent=row["source_agent"],
            target_agent=row["target_agent"],
            created_at=datetime.fromisoformat(row["created_at"]),
            created_by=row["created_by"]
        )

    # =========================================================================
    # Permission CRUD Operations
    # =========================================================================

    def get_permitted_agents(self, source_agent: str) -> List[str]:
        """
        Get list of agent names that source_agent is permitted to call.

        Returns list of target agent names.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT target_agent FROM agent_permissions
                WHERE source_agent = ?
                ORDER BY target_agent
            """, (source_agent,))
            return [row["target_agent"] for row in cursor.fetchall()]

    def get_permission_details(self, source_agent: str) -> List[AgentPermission]:
        """
        Get full permission details for an agent.

        Returns list of AgentPermission objects.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, source_agent, target_agent, created_at, created_by
                FROM agent_permissions
                WHERE source_agent = ?
                ORDER BY target_agent
            """, (source_agent,))
            return [self._row_to_permission(row) for row in cursor.fetchall()]

    def is_permitted(self, source_agent: str, target_agent: str) -> bool:
        """
        Check if source_agent is permitted to call target_agent.

        Returns True if permission exists.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM agent_permissions
                WHERE source_agent = ? AND target_agent = ?
            """, (source_agent, target_agent))
            return cursor.fetchone() is not None

    def add_permission(self, source_agent: str, target_agent: str, created_by: str) -> Optional[AgentPermission]:
        """
        Add permission for source_agent to call target_agent.

        Returns the created permission or None if it already exists.
        """
        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO agent_permissions (source_agent, target_agent, created_at, created_by)
                    VALUES (?, ?, ?, ?)
                """, (source_agent, target_agent, now, created_by))
                conn.commit()

                return AgentPermission(
                    id=cursor.lastrowid,
                    source_agent=source_agent,
                    target_agent=target_agent,
                    created_at=datetime.fromisoformat(now),
                    created_by=created_by
                )
            except sqlite3.IntegrityError:
                # Permission already exists
                return None

    def remove_permission(self, source_agent: str, target_agent: str) -> bool:
        """
        Remove permission for source_agent to call target_agent.

        Returns True if a permission was removed.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM agent_permissions
                WHERE source_agent = ? AND target_agent = ?
            """, (source_agent, target_agent))
            conn.commit()
            return cursor.rowcount > 0

    def set_permissions(self, source_agent: str, target_agents: List[str], created_by: str) -> int:
        """
        Set permissions for source_agent (full replacement).

        Removes all existing permissions and adds new ones.
        Returns the number of permissions set.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()

            # Remove all existing permissions for this source
            cursor.execute("""
                DELETE FROM agent_permissions WHERE source_agent = ?
            """, (source_agent,))

            # Add new permissions
            for target in target_agents:
                if target != source_agent:  # Can't permit self
                    try:
                        cursor.execute("""
                            INSERT INTO agent_permissions (source_agent, target_agent, created_at, created_by)
                            VALUES (?, ?, ?, ?)
                        """, (source_agent, target, now, created_by))
                    except sqlite3.IntegrityError:
                        pass  # Skip duplicates

            conn.commit()
            return len(target_agents)

    def delete_agent_permissions(self, agent_name: str) -> int:
        """
        Delete all permissions involving an agent (when agent is deleted).

        Removes permissions where agent is source OR target.
        Returns total number of permissions deleted.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Delete where agent is source
            cursor.execute("""
                DELETE FROM agent_permissions WHERE source_agent = ?
            """, (agent_name,))
            source_count = cursor.rowcount

            # Delete where agent is target
            cursor.execute("""
                DELETE FROM agent_permissions WHERE target_agent = ?
            """, (agent_name,))
            target_count = cursor.rowcount

            conn.commit()
            return source_count + target_count

    def grant_default_permissions(self, agent_name: str, owner_username: str) -> int:
        """
        Grant default permissions for a new agent.

        RESTRICTIVE DEFAULT (2026-02-19): New agents start with NO permissions.
        Owners must explicitly grant permissions via the Permissions tab.

        This is a no-op function that returns 0 permissions granted.
        The method is kept for API compatibility and potential future use.

        Previously (Option B): Granted bidirectional permissions with all
        same-owner agents automatically. Changed to restrictive default for
        better security - agents should explicitly opt-in to collaboration.

        Returns number of permissions created (always 0 with restrictive default).
        """
        # Restrictive default: no automatic permissions
        # Owners must explicitly configure permissions in the UI
        return 0
