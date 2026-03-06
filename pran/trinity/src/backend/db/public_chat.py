"""
Database operations for public chat session persistence (Phase 12.2.5: PUB-005).

Handles:
- Public chat session management (email and anonymous)
- Message persistence
- Context building for multi-turn conversations
"""

import secrets
from datetime import datetime
from typing import Optional, List

from .connection import get_db_connection
from db_models import PublicChatSession, PublicChatMessage

# Header injected into every public chat request so agents know they're serving a public user
PUBLIC_LINK_MODE_HEADER = "### Trinity: Public Link Access Mode"


class PublicChatOperations:
    """Operations for managing public chat sessions and messages."""

    @staticmethod
    def _row_to_session(row) -> PublicChatSession:
        """Convert a database row to a PublicChatSession model."""
        return PublicChatSession(
            id=row["id"],
            link_id=row["link_id"],
            session_identifier=row["session_identifier"],
            identifier_type=row["identifier_type"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_message_at=datetime.fromisoformat(row["last_message_at"]),
            message_count=row["message_count"],
            total_cost=row["total_cost"]
        )

    @staticmethod
    def _row_to_message(row) -> PublicChatMessage:
        """Convert a database row to a PublicChatMessage model."""
        return PublicChatMessage(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            cost=row["cost"]
        )

    def get_or_create_session(
        self,
        link_id: str,
        session_identifier: str,
        identifier_type: str
    ) -> PublicChatSession:
        """
        Get existing session or create a new one for the given link and identifier.

        Args:
            link_id: The public link ID
            session_identifier: Email (lowercase) or anonymous token
            identifier_type: 'email' or 'anonymous'

        Returns:
            PublicChatSession model
        """
        # Normalize email identifiers
        normalized_identifier = session_identifier.lower() if identifier_type == 'email' else session_identifier

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Try to find existing session
            cursor.execute("""
                SELECT * FROM public_chat_sessions
                WHERE link_id = ? AND session_identifier = ?
            """, (link_id, normalized_identifier))

            row = cursor.fetchone()
            if row:
                return self._row_to_session(row)

            # Create new session
            session_id = secrets.token_urlsafe(16)
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO public_chat_sessions (
                    id, link_id, session_identifier, identifier_type,
                    created_at, last_message_at, message_count, total_cost
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, 0.0)
            """, (session_id, link_id, normalized_identifier, identifier_type, now, now))

            conn.commit()

            # Return the new session
            cursor.execute("SELECT * FROM public_chat_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return self._row_to_session(row)

    def get_session_by_identifier(
        self,
        link_id: str,
        session_identifier: str
    ) -> Optional[PublicChatSession]:
        """Look up a session by link ID and identifier."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM public_chat_sessions
                WHERE link_id = ? AND session_identifier = ?
            """, (link_id, session_identifier.lower()))

            row = cursor.fetchone()
            return self._row_to_session(row) if row else None

    def get_session(self, session_id: str) -> Optional[PublicChatSession]:
        """Get a session by ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM public_chat_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return self._row_to_session(row) if row else None

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        cost: Optional[float] = None
    ) -> PublicChatMessage:
        """
        Add a message to a session and update session stats.

        Args:
            session_id: The chat session ID
            role: 'user' or 'assistant'
            content: Message content
            cost: Optional cost for assistant messages

        Returns:
            PublicChatMessage model
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Create message
            message_id = secrets.token_urlsafe(16)
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO public_chat_messages (
                    id, session_id, role, content, timestamp, cost
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, session_id, role, content, now, cost))

            # Update session stats
            cursor.execute("""
                UPDATE public_chat_sessions
                SET last_message_at = ?,
                    message_count = message_count + 1,
                    total_cost = total_cost + COALESCE(?, 0)
                WHERE id = ?
            """, (now, cost or 0, session_id))

            conn.commit()

            # Return the created message
            cursor.execute("SELECT * FROM public_chat_messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            return self._row_to_message(row)

    def get_session_messages(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[PublicChatMessage]:
        """
        Get messages for a session, ordered oldest-first for context building.

        Args:
            session_id: The chat session ID
            limit: Maximum number of messages to return

        Returns:
            List of messages, oldest first
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM public_chat_messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (session_id, limit))

            return [self._row_to_message(row) for row in cursor.fetchall()]

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[PublicChatMessage]:
        """
        Get the most recent N messages, ordered for display (oldest first).
        Uses subquery to get the most recent, then orders ascending.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get the most recent N messages, then reverse for chronological order
            cursor.execute("""
                SELECT * FROM (
                    SELECT * FROM public_chat_messages
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ) ORDER BY timestamp ASC
            """, (session_id, limit))

            return [self._row_to_message(row) for row in cursor.fetchall()]

    def clear_session(self, session_id: str) -> bool:
        """
        Delete a session and all its messages (cascade).

        Returns:
            True if session was deleted, False if not found
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Delete messages first (FK constraint)
            cursor.execute("DELETE FROM public_chat_messages WHERE session_id = ?", (session_id,))

            # Delete session
            cursor.execute("DELETE FROM public_chat_sessions WHERE id = ?", (session_id,))
            deleted = cursor.rowcount > 0

            conn.commit()

        return deleted

    def build_context_prompt(
        self,
        session_id: str,
        new_message: str,
        max_turns: int = 10
    ) -> str:
        """
        Build a prompt with conversation history for context injection.

        Args:
            session_id: The chat session ID
            new_message: The new user message to append
            max_turns: Maximum number of previous exchanges (user+assistant pairs)

        Returns:
            Formatted prompt with history and new message, prefixed with public mode header
        """
        # Get recent messages (max_turns * 2 to get pairs)
        messages = self.get_recent_messages(session_id, limit=max_turns * 2)

        # Start with public link mode header
        parts = [PUBLIC_LINK_MODE_HEADER, ""]

        if messages:
            # Add conversation history
            parts.append("Previous conversation:")
            for msg in messages:
                role_label = "User" if msg.role == "user" else "Assistant"
                parts.append(f"{role_label}: {msg.content}")
            parts.append("")

        # Add current message
        parts.append("Current message:")
        parts.append(f"User: {new_message}")

        return "\n".join(parts)

    def delete_link_sessions(self, link_id: str) -> int:
        """
        Delete all sessions for a public link (cascade on link deletion).

        Returns:
            Number of sessions deleted
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get session IDs first
            cursor.execute("SELECT id FROM public_chat_sessions WHERE link_id = ?", (link_id,))
            session_ids = [row[0] for row in cursor.fetchall()]

            # Delete messages for all sessions
            for session_id in session_ids:
                cursor.execute("DELETE FROM public_chat_messages WHERE session_id = ?", (session_id,))

            # Delete sessions
            cursor.execute("DELETE FROM public_chat_sessions WHERE link_id = ?", (link_id,))
            deleted = cursor.rowcount

            conn.commit()

        return deleted
