"""
Agent skills database operations.

Manages skill assignments to agents. Skills themselves are stored in
a GitHub repository; this module only tracks which skills are assigned
to which agents.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional

from .connection import get_db_connection
from db_models import AgentSkill


class SkillsOperations:
    """Agent skills database operations."""

    @staticmethod
    def _row_to_skill(row) -> AgentSkill:
        """Convert a database row to an AgentSkill model."""
        return AgentSkill(
            id=row["id"],
            agent_name=row["agent_name"],
            skill_name=row["skill_name"],
            assigned_by=row["assigned_by"],
            assigned_at=datetime.fromisoformat(row["assigned_at"])
        )

    # =========================================================================
    # Skill Assignment Operations
    # =========================================================================

    def get_agent_skills(self, agent_name: str) -> List[AgentSkill]:
        """
        Get all skills assigned to an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            List of AgentSkill objects
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, agent_name, skill_name, assigned_by, assigned_at
                FROM agent_skills
                WHERE agent_name = ?
                ORDER BY skill_name
            """, (agent_name,))
            return [self._row_to_skill(row) for row in cursor.fetchall()]

    def get_agent_skill_names(self, agent_name: str) -> List[str]:
        """
        Get skill names assigned to an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            List of skill names
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT skill_name
                FROM agent_skills
                WHERE agent_name = ?
                ORDER BY skill_name
            """, (agent_name,))
            return [row["skill_name"] for row in cursor.fetchall()]

    def assign_skill(
        self,
        agent_name: str,
        skill_name: str,
        assigned_by: str
    ) -> Optional[AgentSkill]:
        """
        Assign a skill to an agent.

        Args:
            agent_name: Name of the agent
            skill_name: Name of the skill
            assigned_by: Username of who is assigning

        Returns:
            AgentSkill object if created, None if already exists
        """
        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO agent_skills (agent_name, skill_name, assigned_by, assigned_at)
                    VALUES (?, ?, ?, ?)
                """, (agent_name, skill_name, assigned_by, now))
                conn.commit()

                return AgentSkill(
                    id=cursor.lastrowid,
                    agent_name=agent_name,
                    skill_name=skill_name,
                    assigned_by=assigned_by,
                    assigned_at=datetime.fromisoformat(now)
                )
            except sqlite3.IntegrityError:
                # Skill already assigned
                return None

    def unassign_skill(self, agent_name: str, skill_name: str) -> bool:
        """
        Remove a skill assignment from an agent.

        Args:
            agent_name: Name of the agent
            skill_name: Name of the skill to remove

        Returns:
            True if a skill was removed
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM agent_skills
                WHERE agent_name = ? AND skill_name = ?
            """, (agent_name, skill_name))
            conn.commit()
            return cursor.rowcount > 0

    def set_agent_skills(
        self,
        agent_name: str,
        skill_names: List[str],
        assigned_by: str
    ) -> int:
        """
        Set skills for an agent (full replacement).

        Removes all existing skills and assigns the new list.

        Args:
            agent_name: Name of the agent
            skill_names: List of skill names to assign
            assigned_by: Username of who is assigning

        Returns:
            Number of skills assigned
        """
        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Remove all existing skills for this agent
            cursor.execute("""
                DELETE FROM agent_skills WHERE agent_name = ?
            """, (agent_name,))

            # Add new skills
            for skill_name in skill_names:
                try:
                    cursor.execute("""
                        INSERT INTO agent_skills (agent_name, skill_name, assigned_by, assigned_at)
                        VALUES (?, ?, ?, ?)
                    """, (agent_name, skill_name, assigned_by, now))
                except sqlite3.IntegrityError:
                    pass  # Skip duplicates

            conn.commit()
            return len(skill_names)

    def delete_agent_skills(self, agent_name: str) -> int:
        """
        Delete all skill assignments for an agent (cleanup on agent delete).

        Args:
            agent_name: Name of the agent

        Returns:
            Number of skills deleted
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM agent_skills WHERE agent_name = ?
            """, (agent_name,))
            conn.commit()
            return cursor.rowcount

    def is_skill_assigned(self, agent_name: str, skill_name: str) -> bool:
        """
        Check if a skill is assigned to an agent.

        Args:
            agent_name: Name of the agent
            skill_name: Name of the skill

        Returns:
            True if the skill is assigned
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM agent_skills
                WHERE agent_name = ? AND skill_name = ?
            """, (agent_name, skill_name))
            return cursor.fetchone() is not None

    def get_agents_with_skill(self, skill_name: str) -> List[str]:
        """
        Get all agents that have a specific skill assigned.

        Args:
            skill_name: Name of the skill

        Returns:
            List of agent names
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name
                FROM agent_skills
                WHERE skill_name = ?
                ORDER BY agent_name
            """, (skill_name,))
            return [row["agent_name"] for row in cursor.fetchall()]
