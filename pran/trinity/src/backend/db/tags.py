"""
Tag operations for agent organization (ORG-001).

Tags enable lightweight grouping of agents into logical systems.
Agents can have multiple tags, enabling multi-system membership.
"""

import json
from typing import List, Optional
from datetime import datetime

from db.connection import get_db_connection
from db_models import AgentTagList, TagWithCount


class TagOperations:
    """Database operations for agent tags."""

    def get_agent_tags(self, agent_name: str) -> List[str]:
        """Get all tags for an agent, sorted alphabetically."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT tag FROM agent_tags WHERE agent_name = ? ORDER BY tag",
                (agent_name,)
            )
            return [row[0] for row in cursor.fetchall()]

    def set_agent_tags(self, agent_name: str, tags: List[str]) -> List[str]:
        """
        Replace all tags for an agent.

        Args:
            agent_name: The agent name
            tags: List of tags to set (replaces existing)

        Returns:
            The normalized, sorted list of tags
        """
        # Normalize tags: lowercase, strip whitespace, remove duplicates
        normalized = sorted(set(t.lower().strip() for t in tags if t.strip()))

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Delete existing tags
            cursor.execute(
                "DELETE FROM agent_tags WHERE agent_name = ?",
                (agent_name,)
            )

            # Insert new tags
            now = datetime.utcnow().isoformat() + "Z"
            for tag in normalized:
                cursor.execute(
                    "INSERT INTO agent_tags (agent_name, tag, created_at) VALUES (?, ?, ?)",
                    (agent_name, tag, now)
                )

            conn.commit()
            return normalized

    def add_tag(self, agent_name: str, tag: str) -> List[str]:
        """
        Add a single tag to an agent.

        Args:
            agent_name: The agent name
            tag: Tag to add

        Returns:
            Updated list of all tags for the agent
        """
        normalized_tag = tag.lower().strip()
        if not normalized_tag:
            return self.get_agent_tags(agent_name)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat() + "Z"

            # Use INSERT OR IGNORE to handle duplicates
            cursor.execute(
                "INSERT OR IGNORE INTO agent_tags (agent_name, tag, created_at) VALUES (?, ?, ?)",
                (agent_name, normalized_tag, now)
            )
            conn.commit()

        return self.get_agent_tags(agent_name)

    def remove_tag(self, agent_name: str, tag: str) -> List[str]:
        """
        Remove a single tag from an agent.

        Args:
            agent_name: The agent name
            tag: Tag to remove

        Returns:
            Updated list of all tags for the agent
        """
        normalized_tag = tag.lower().strip()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM agent_tags WHERE agent_name = ? AND tag = ?",
                (agent_name, normalized_tag)
            )
            conn.commit()

        return self.get_agent_tags(agent_name)

    def list_all_tags(self) -> List[TagWithCount]:
        """
        List all unique tags with agent counts.

        Returns:
            List of tags with their usage counts, sorted by count descending
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tag, COUNT(*) as count
                FROM agent_tags
                GROUP BY tag
                ORDER BY count DESC, tag ASC
            """)
            return [
                TagWithCount(tag=row[0], count=row[1])
                for row in cursor.fetchall()
            ]

    def get_agents_by_tag(self, tag: str) -> List[str]:
        """
        Get all agent names that have a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of agent names with this tag
        """
        normalized_tag = tag.lower().strip()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT agent_name FROM agent_tags WHERE tag = ? ORDER BY agent_name",
                (normalized_tag,)
            )
            return [row[0] for row in cursor.fetchall()]

    def get_agents_by_tags(self, tags: List[str]) -> List[str]:
        """
        Get all agent names that have ANY of the specified tags (OR logic).

        Args:
            tags: List of tags to search for

        Returns:
            List of unique agent names with any of these tags
        """
        if not tags:
            return []

        normalized_tags = [t.lower().strip() for t in tags if t.strip()]
        if not normalized_tags:
            return []

        placeholders = ",".join("?" * len(normalized_tags))

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT DISTINCT agent_name FROM agent_tags WHERE tag IN ({placeholders}) ORDER BY agent_name",
                normalized_tags
            )
            return [row[0] for row in cursor.fetchall()]

    def delete_agent_tags(self, agent_name: str) -> None:
        """
        Delete all tags for an agent (called when agent is deleted).

        Args:
            agent_name: The agent name
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM agent_tags WHERE agent_name = ?",
                (agent_name,)
            )
            conn.commit()

    def get_tags_for_agents(self, agent_names: List[str]) -> dict:
        """
        Batch get tags for multiple agents.

        Args:
            agent_names: List of agent names

        Returns:
            Dict mapping agent_name -> list of tags
        """
        if not agent_names:
            return {}

        placeholders = ",".join("?" * len(agent_names))

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT agent_name, tag FROM agent_tags WHERE agent_name IN ({placeholders}) ORDER BY agent_name, tag",
                agent_names
            )

            result = {name: [] for name in agent_names}
            for row in cursor.fetchall():
                result[row[0]].append(row[1])

            return result
