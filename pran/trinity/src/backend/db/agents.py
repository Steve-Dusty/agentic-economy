"""
Agent ownership and sharing database operations.

Handles agent ownership registration, access control, and sharing.
Includes system agent protection (Phase 11.1).
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

from .connection import get_db_connection
from db_models import AgentShare

# System agent name constant
SYSTEM_AGENT_NAME = "trinity-system"


class AgentOperations:
    """Agent ownership and sharing database operations."""

    def __init__(self, user_ops):
        """Initialize with reference to user operations for lookups."""
        self._user_ops = user_ops

    @staticmethod
    def _row_to_agent_share(row) -> AgentShare:
        """Convert an agent_sharing row to an AgentShare model."""
        return AgentShare(
            id=row["id"],
            agent_name=row["agent_name"],
            shared_with_email=row["shared_with_email"],
            shared_by_id=row["shared_by_id"],
            shared_by_email=row["shared_by_email"] or "unknown",
            created_at=datetime.fromisoformat(row["created_at"])
        )

    # =========================================================================
    # Agent Ownership Management
    # =========================================================================

    def register_agent_owner(self, agent_name: str, owner_username: str, is_system: bool = False) -> bool:
        """Register the owner of an agent.

        Args:
            agent_name: Name of the agent
            owner_username: Username of the owner
            is_system: True for system agents (deletion-protected)
        """
        user = self._user_ops.get_user_by_username(owner_username)
        if not user:
            return False

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO agent_ownership (agent_name, owner_id, created_at, is_system)
                    VALUES (?, ?, ?, ?)
                """, (agent_name, user["id"], datetime.utcnow().isoformat(), 1 if is_system else 0))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Agent already registered - update is_system flag if needed
                if is_system:
                    cursor.execute("""
                        UPDATE agent_ownership SET is_system = 1 WHERE agent_name = ?
                    """, (agent_name,))
                    conn.commit()
                return False

    def get_agent_owner(self, agent_name: str) -> Optional[Dict]:
        """Get the owner of an agent, including is_system flag."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ao.id, ao.agent_name, ao.owner_id, u.username as owner_username,
                       ao.created_at, COALESCE(ao.is_system, 0) as is_system
                FROM agent_ownership ao
                JOIN users u ON ao.owner_id = u.id
                WHERE ao.agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result["is_system"] = bool(result.get("is_system", 0))
                return result
            return None

    def get_agents_by_owner(self, owner_username: str) -> List[str]:
        """Get all agent names owned by a user."""
        user = self._user_ops.get_user_by_username(owner_username)
        if not user:
            return []

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name FROM agent_ownership WHERE owner_id = ?
            """, (user["id"],))
            return [row["agent_name"] for row in cursor.fetchall()]

    def delete_agent_ownership(self, agent_name: str) -> bool:
        """Remove agent ownership record and all sharing records (when agent is deleted)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Delete sharing records first (cascade)
            cursor.execute("DELETE FROM agent_sharing WHERE agent_name = ?", (agent_name,))
            # Delete ownership record
            cursor.execute("DELETE FROM agent_ownership WHERE agent_name = ?", (agent_name,))
            conn.commit()
            return cursor.rowcount > 0

    def can_user_access_agent(self, username: str, agent_name: str) -> bool:
        """Check if a user can access an agent (owner, shared, or admin)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        # Admins can access all agents
        if user["role"] == "admin":
            return True

        # Check if user is the owner
        owner = self.get_agent_owner(agent_name)
        if owner and owner["owner_username"] == username:
            return True

        # Check if agent is shared with user
        if self.is_agent_shared_with_user(agent_name, username):
            return True

        return False

    def can_user_delete_agent(self, username: str, agent_name: str) -> bool:
        """Check if a user can delete an agent (owner or admin, but NOT system agents)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        # Check if this is a system agent - NO ONE can delete system agents
        owner = self.get_agent_owner(agent_name)
        if owner and owner.get("is_system", False):
            return False

        # Admins can delete any non-system agent
        if user["role"] == "admin":
            return True

        # Owners can delete their own non-system agents
        if owner and owner["owner_username"] == username:
            return True

        return False

    def is_system_agent(self, agent_name: str) -> bool:
        """Check if an agent is a system agent (deletion-protected)."""
        # Quick check by name
        if agent_name == SYSTEM_AGENT_NAME:
            return True
        # Check database flag
        owner = self.get_agent_owner(agent_name)
        return owner.get("is_system", False) if owner else False

    # =========================================================================
    # Agent Sharing Management
    # =========================================================================

    def share_agent(self, agent_name: str, owner_username: str, share_with_email: str) -> Optional[AgentShare]:
        """
        Share an agent with another user by email.
        - Validates owner has permission to share
        - Creates sharing record with email (user doesn't need to exist yet)
        - Returns share details or None if failed
        """
        # Get owner and validate permission
        owner = self._user_ops.get_user_by_username(owner_username)
        if not owner:
            return None

        # Check if user can share (owner or admin)
        if not self.can_user_share_agent(owner_username, agent_name):
            return None

        # Prevent self-sharing (check if owner's email matches target email)
        owner_email = owner.get("email") or ""
        if owner_email and owner_email.lower() == share_with_email.lower():
            return None

        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO agent_sharing (agent_name, shared_with_email, shared_by_id, created_at)
                    VALUES (?, ?, ?, ?)
                """, (agent_name, share_with_email.lower(), owner["id"], now))
                conn.commit()
                share_id = cursor.lastrowid

                return AgentShare(
                    id=share_id,
                    agent_name=agent_name,
                    shared_with_email=share_with_email.lower(),
                    shared_by_id=owner["id"],
                    shared_by_email=owner.get("email") or owner.get("username") or "unknown",
                    created_at=datetime.fromisoformat(now)
                )
            except sqlite3.IntegrityError:
                # Already shared with this email
                return None

    def unshare_agent(self, agent_name: str, owner_username: str, share_with_email: str) -> bool:
        """Remove sharing access for an email."""
        # Validate permission
        if not self.can_user_share_agent(owner_username, agent_name):
            return False

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM agent_sharing
                WHERE agent_name = ? AND shared_with_email = ?
            """, (agent_name, share_with_email.lower()))
            conn.commit()
            return cursor.rowcount > 0

    def get_agent_shares(self, agent_name: str) -> List[AgentShare]:
        """Get all emails an agent is shared with."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.agent_name, s.shared_with_email, s.shared_by_id, s.created_at,
                       COALESCE(sb.email, sb.username) as shared_by_email
                FROM agent_sharing s
                JOIN users sb ON s.shared_by_id = sb.id
                WHERE s.agent_name = ?
                ORDER BY s.created_at DESC
            """, (agent_name,))
            return [self._row_to_agent_share(row) for row in cursor.fetchall()]

    def get_shared_agents(self, username: str) -> List[str]:
        """Get all agent names shared with a user (by their email)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return []

        user_email = user.get("email")
        if not user_email:
            return []

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name FROM agent_sharing WHERE shared_with_email = ?
            """, (user_email.lower(),))
            return [row["agent_name"] for row in cursor.fetchall()]

    def is_agent_shared_with_user(self, agent_name: str, username: str) -> bool:
        """Check if an agent is shared with a specific user (by their email)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        user_email = user.get("email")
        if not user_email:
            return False

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM agent_sharing
                WHERE agent_name = ? AND shared_with_email = ?
            """, (agent_name, user_email.lower()))
            return cursor.fetchone() is not None

    def can_user_share_agent(self, username: str, agent_name: str) -> bool:
        """Check if a user can share an agent (only owner or admin)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        if user["role"] == "admin":
            return True

        owner = self.get_agent_owner(agent_name)
        return owner and owner["owner_username"] == username

    def delete_agent_shares(self, agent_name: str) -> int:
        """Delete all sharing records for an agent (when agent is deleted)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM agent_sharing WHERE agent_name = ?", (agent_name,))
            conn.commit()
            return cursor.rowcount

    # =========================================================================
    # Agent API Key Settings
    # =========================================================================

    def get_use_platform_api_key(self, agent_name: str) -> bool:
        """Check if agent should use platform API key (default: True)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(use_platform_api_key, 1) as use_platform_api_key
                FROM agent_ownership WHERE agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            if row:
                return bool(row["use_platform_api_key"])
            return True  # Default to using platform key

    def set_use_platform_api_key(self, agent_name: str, use_platform_key: bool) -> bool:
        """Set whether agent should use platform API key."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_ownership SET use_platform_api_key = ?
                WHERE agent_name = ?
            """, (1 if use_platform_key else 0, agent_name))
            conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # Autonomy Mode
    # =========================================================================

    def get_autonomy_enabled(self, agent_name: str) -> bool:
        """Check if autonomy mode is enabled for agent (scheduled tasks run automatically)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(autonomy_enabled, 0) as autonomy_enabled
                FROM agent_ownership WHERE agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            if row:
                return bool(row["autonomy_enabled"])
            return False  # Default to disabled

    def set_autonomy_enabled(self, agent_name: str, enabled: bool) -> bool:
        """Set whether autonomy mode is enabled for agent."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_ownership SET autonomy_enabled = ?
                WHERE agent_name = ?
            """, (1 if enabled else 0, agent_name))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_agents_autonomy_status(self) -> Dict[str, bool]:
        """Get autonomy status for all agents (for dashboard display)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name, COALESCE(autonomy_enabled, 0) as autonomy_enabled
                FROM agent_ownership
            """)
            return {row["agent_name"]: bool(row["autonomy_enabled"]) for row in cursor.fetchall()}

    # =========================================================================
    # Resource Limits
    # =========================================================================

    def get_resource_limits(self, agent_name: str) -> Optional[Dict[str, str]]:
        """
        Get per-agent resource limits (memory and CPU).

        Returns None if no custom limits are set, otherwise returns dict with:
        - memory: Memory limit (e.g., "8g", "16g")
        - cpu: CPU limit (e.g., "4", "8")
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT memory_limit, cpu_limit
                FROM agent_ownership WHERE agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            if row:
                memory = row["memory_limit"]
                cpu = row["cpu_limit"]
                # Return None if no custom limits set
                if memory is None and cpu is None:
                    return None
                return {
                    "memory": memory,
                    "cpu": cpu
                }
            return None

    def set_resource_limits(self, agent_name: str, memory: Optional[str] = None, cpu: Optional[str] = None) -> bool:
        """
        Set per-agent resource limits.

        Args:
            agent_name: Name of the agent
            memory: Memory limit (e.g., "4g", "8g", "16g") or None to clear
            cpu: CPU limit (e.g., "2", "4", "8") or None to clear

        Returns:
            True if update succeeded, False otherwise
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_ownership SET memory_limit = ?, cpu_limit = ?
                WHERE agent_name = ?
            """, (memory, cpu, agent_name))
            conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # Full Capabilities (Container Security)
    # =========================================================================

    def get_full_capabilities(self, agent_name: str) -> bool:
        """
        Get full_capabilities setting for an agent.
        When True, container runs with Docker default capabilities (apt-get works).
        When False (default), container runs with restricted capabilities (secure).

        Args:
            agent_name: Name of the agent

        Returns:
            True if full capabilities enabled, False otherwise
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT full_capabilities FROM agent_ownership WHERE agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            if row and row[0] is not None:
                return bool(row[0])
            return False

    def set_full_capabilities(self, agent_name: str, enabled: bool) -> bool:
        """
        Set full_capabilities setting for an agent.
        Requires container restart to take effect.

        Args:
            agent_name: Name of the agent
            enabled: True for Docker default capabilities, False for restricted

        Returns:
            True if update succeeded, False otherwise
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_ownership SET full_capabilities = ?
                WHERE agent_name = ?
            """, (1 if enabled else 0, agent_name))
            conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # Read-Only Mode
    # =========================================================================

    def get_read_only_mode(self, agent_name: str) -> dict:
        """
        Get read-only mode status and configuration for an agent.

        Returns:
            dict with 'enabled' (bool) and 'config' (dict or None)
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(read_only_mode, 0) as read_only_mode, read_only_config
                FROM agent_ownership WHERE agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            if row:
                import json
                config = None
                if row["read_only_config"]:
                    try:
                        config = json.loads(row["read_only_config"])
                    except json.JSONDecodeError:
                        config = None
                return {
                    "enabled": bool(row["read_only_mode"]),
                    "config": config
                }
            return {"enabled": False, "config": None}

    def set_read_only_mode(self, agent_name: str, enabled: bool, config: Optional[dict] = None) -> bool:
        """
        Set read-only mode status and configuration for an agent.

        Args:
            agent_name: Name of the agent
            enabled: True to enable read-only mode
            config: Optional dict with 'blocked_patterns' and 'allowed_patterns' lists

        Returns:
            True if update succeeded
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            import json
            config_json = json.dumps(config) if config else None
            cursor.execute("""
                UPDATE agent_ownership SET read_only_mode = ?, read_only_config = ?
                WHERE agent_name = ?
            """, (1 if enabled else 0, config_json, agent_name))
            conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # Parallel Capacity (CAPACITY-001)
    # =========================================================================

    def get_max_parallel_tasks(self, agent_name: str) -> int:
        """
        Get max_parallel_tasks for an agent (default: 3).

        Args:
            agent_name: Name of the agent

        Returns:
            Maximum number of parallel tasks allowed (1-10, default 3)
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(max_parallel_tasks, 3) as max_parallel_tasks
                FROM agent_ownership WHERE agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            if row:
                return row["max_parallel_tasks"]
            return 3  # Default

    def set_max_parallel_tasks(self, agent_name: str, max_tasks: int) -> bool:
        """
        Set max_parallel_tasks for an agent.

        Args:
            agent_name: Name of the agent
            max_tasks: Maximum parallel tasks (must be 1-10)

        Returns:
            True if update succeeded
        """
        # Validate range
        if max_tasks < 1 or max_tasks > 10:
            return False

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_ownership SET max_parallel_tasks = ?
                WHERE agent_name = ?
            """, (max_tasks, agent_name))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_agents_parallel_capacity(self) -> Dict[str, int]:
        """
        Get max_parallel_tasks for all agents.

        Returns:
            Dict mapping agent_name to max_parallel_tasks
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name, COALESCE(max_parallel_tasks, 3) as max_parallel_tasks
                FROM agent_ownership
            """)
            return {row["agent_name"]: row["max_parallel_tasks"] for row in cursor.fetchall()}

    # =========================================================================
    # Batch Metadata Query (N+1 Fix)
    # =========================================================================

    def get_accessible_agent_names(self, user_email: str, is_admin: bool = False) -> List[str]:
        """
        Get list of agent names the user can access.

        Used by /ws/events endpoint to filter events to user's accessible agents.

        Args:
            user_email: User's email address
            is_admin: True if user is admin (sees all agents)

        Returns:
            List of agent names the user can access (owned + shared, or all if admin)
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if is_admin:
                # Admin sees all agents
                cursor.execute("SELECT agent_name FROM agent_ownership")
                return [row["agent_name"] for row in cursor.fetchall()]

            # Get owned + shared agents
            cursor.execute("""
                SELECT DISTINCT agent_name FROM (
                    SELECT ao.agent_name FROM agent_ownership ao
                    JOIN users u ON ao.owner_id = u.id
                    WHERE LOWER(u.email) = LOWER(?)
                    UNION
                    SELECT agent_name FROM agent_sharing
                    WHERE LOWER(shared_with_email) = LOWER(?)
                )
            """, (user_email, user_email))
            return [row["agent_name"] for row in cursor.fetchall()]

    # =========================================================================
    # Agent Rename (RENAME-001)
    # =========================================================================

    def rename_agent(self, old_name: str, new_name: str) -> bool:
        """
        Rename an agent by updating all database references.

        This updates agent_name in all tables that reference it:
        - agent_ownership (primary)
        - agent_sharing
        - agent_schedules
        - schedule_executions
        - chat_sessions
        - chat_messages
        - agent_activities
        - agent_permissions (source and target)
        - agent_shared_folder_config
        - agent_git_config
        - agent_skills
        - agent_tags
        - agent_public_links
        - mcp_api_keys
        - agent_health_checks
        - agent_dashboard_values
        - monitoring_alert_cooldowns

        Args:
            old_name: Current agent name
            new_name: New agent name (must be unique)

        Returns:
            True if rename succeeded, False if failed
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                # Check if old agent exists
                cursor.execute("SELECT 1 FROM agent_ownership WHERE agent_name = ?", (old_name,))
                if not cursor.fetchone():
                    return False

                # Check if new name is already taken
                cursor.execute("SELECT 1 FROM agent_ownership WHERE agent_name = ?", (new_name,))
                if cursor.fetchone():
                    return False

                # Update all tables in order
                # Primary table
                cursor.execute(
                    "UPDATE agent_ownership SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Sharing
                cursor.execute(
                    "UPDATE agent_sharing SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Schedules
                cursor.execute(
                    "UPDATE agent_schedules SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Executions
                cursor.execute(
                    "UPDATE schedule_executions SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Chat sessions
                cursor.execute(
                    "UPDATE chat_sessions SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Chat messages
                cursor.execute(
                    "UPDATE chat_messages SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Activities
                cursor.execute(
                    "UPDATE agent_activities SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Permissions (both source and target)
                cursor.execute(
                    "UPDATE agent_permissions SET source_agent = ? WHERE source_agent = ?",
                    (new_name, old_name)
                )
                cursor.execute(
                    "UPDATE agent_permissions SET target_agent = ? WHERE target_agent = ?",
                    (new_name, old_name)
                )

                # Shared folder config
                cursor.execute(
                    "UPDATE agent_shared_folder_config SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Git config
                cursor.execute(
                    "UPDATE agent_git_config SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Skills
                cursor.execute(
                    "UPDATE agent_skills SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Tags
                cursor.execute(
                    "UPDATE agent_tags SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Public links
                cursor.execute(
                    "UPDATE agent_public_links SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # MCP API keys
                cursor.execute(
                    "UPDATE mcp_api_keys SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Health checks
                cursor.execute(
                    "UPDATE agent_health_checks SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Dashboard values
                cursor.execute(
                    "UPDATE agent_dashboard_values SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                # Monitoring cooldowns
                cursor.execute(
                    "UPDATE monitoring_alert_cooldowns SET agent_name = ? WHERE agent_name = ?",
                    (new_name, old_name)
                )

                conn.commit()
                return True

            except sqlite3.IntegrityError:
                conn.rollback()
                return False

    def can_user_rename_agent(self, username: str, agent_name: str) -> bool:
        """Check if a user can rename an agent (only owner or admin, NOT system agents)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        # Check if this is a system agent - NO ONE can rename system agents
        owner = self.get_agent_owner(agent_name)
        if owner and owner.get("is_system", False):
            return False

        # Admins can rename any non-system agent
        if user["role"] == "admin":
            return True

        # Only owners can rename their agents
        if owner and owner["owner_username"] == username:
            return True

        return False

    def get_all_agent_metadata(self, user_email: str = None) -> Dict[str, Dict]:
        """
        Fetch all agent metadata in a SINGLE query.

        This eliminates the N+1 query problem by joining all related tables
        and returning a dict keyed by agent_name.

        Args:
            user_email: Current user's email for checking share access

        Returns:
            Dict mapping agent_name to metadata dict containing:
            - owner_id, owner_username, owner_email
            - is_system, autonomy_enabled, use_platform_api_key
            - memory_limit, cpu_limit
            - github_repo, github_branch
            - is_shared_with_user (bool)
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Single query that joins all needed tables
            cursor.execute("""
                SELECT
                    ao.agent_name,
                    ao.owner_id,
                    u.username as owner_username,
                    u.email as owner_email,
                    COALESCE(ao.is_system, 0) as is_system,
                    COALESCE(ao.autonomy_enabled, 0) as autonomy_enabled,
                    COALESCE(ao.read_only_mode, 0) as read_only_enabled,
                    COALESCE(ao.use_platform_api_key, 1) as use_platform_api_key,
                    ao.memory_limit,
                    ao.cpu_limit,
                    gc.github_repo,
                    gc.working_branch as github_branch,
                    CASE
                        WHEN s.id IS NOT NULL THEN 1
                        ELSE 0
                    END as is_shared_with_user
                FROM agent_ownership ao
                LEFT JOIN users u ON ao.owner_id = u.id
                LEFT JOIN agent_git_config gc ON gc.agent_name = ao.agent_name
                LEFT JOIN agent_sharing s ON s.agent_name = ao.agent_name
                    AND LOWER(s.shared_with_email) = LOWER(?)
            """, (user_email or '',))

            result = {}
            for row in cursor.fetchall():
                result[row["agent_name"]] = {
                    "owner_id": row["owner_id"],
                    "owner_username": row["owner_username"],
                    "owner_email": row["owner_email"],
                    "is_system": bool(row["is_system"]),
                    "autonomy_enabled": bool(row["autonomy_enabled"]),
                    "read_only_enabled": bool(row["read_only_enabled"]),
                    "use_platform_api_key": bool(row["use_platform_api_key"]),
                    "memory_limit": row["memory_limit"],
                    "cpu_limit": row["cpu_limit"],
                    "github_repo": row["github_repo"],
                    "github_branch": row["github_branch"],
                    "is_shared_with_user": bool(row["is_shared_with_user"]),
                }

            return result
