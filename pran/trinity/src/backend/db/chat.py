"""
Chat session and message persistence database operations.

Handles chat session management, message storage, and history retrieval.
"""

import secrets
from datetime import datetime
from typing import Optional, List

from .connection import get_db_connection
from db_models import ChatSession, ChatMessage


class ChatOperations:
    """Chat session and message database operations."""

    @staticmethod
    def _row_to_chat_session(row) -> ChatSession:
        """Convert a chat_sessions row to a ChatSession model."""
        return ChatSession(
            id=row["id"],
            agent_name=row["agent_name"],
            user_id=row["user_id"],
            user_email=row["user_email"],
            started_at=datetime.fromisoformat(row["started_at"]),
            last_message_at=datetime.fromisoformat(row["last_message_at"]),
            message_count=row["message_count"],
            total_cost=row["total_cost"],
            total_context_used=row["total_context_used"],
            total_context_max=row["total_context_max"],
            status=row["status"]
        )

    @staticmethod
    def _row_to_chat_message(row) -> ChatMessage:
        """Convert a chat_messages row to a ChatMessage model."""
        return ChatMessage(
            id=row["id"],
            session_id=row["session_id"],
            agent_name=row["agent_name"],
            user_id=row["user_id"],
            user_email=row["user_email"],
            role=row["role"],
            content=row["content"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            cost=row["cost"],
            context_used=row["context_used"],
            context_max=row["context_max"],
            tool_calls=row["tool_calls"],
            execution_time_ms=row["execution_time_ms"]
        )

    def get_or_create_chat_session(self, agent_name: str, user_id: int, user_email: str) -> ChatSession:
        """
        Get the active chat session for a user+agent, or create a new one.
        Returns the most recent active session if it exists.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Try to find an active session for this user+agent
            cursor.execute("""
                SELECT * FROM chat_sessions
                WHERE agent_name = ? AND user_id = ? AND status = 'active'
                ORDER BY last_message_at DESC
                LIMIT 1
            """, (agent_name, user_id))

            row = cursor.fetchone()
            if row:
                return self._row_to_chat_session(row)

            # Create a new session
            session_id = secrets.token_urlsafe(16)
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO chat_sessions (
                    id, agent_name, user_id, user_email, started_at, last_message_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, agent_name, user_id, user_email, now, now))

            conn.commit()

            # Return the newly created session
            cursor.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return self._row_to_chat_session(row)

    def add_chat_message(
        self,
        session_id: str,
        agent_name: str,
        user_id: int,
        user_email: str,
        role: str,
        content: str,
        cost: Optional[float] = None,
        context_used: Optional[int] = None,
        context_max: Optional[int] = None,
        tool_calls: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> ChatMessage:
        """Add a message to a chat session and update session stats."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Create message
            message_id = secrets.token_urlsafe(16)
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO chat_messages (
                    id, session_id, agent_name, user_id, user_email,
                    role, content, timestamp,
                    cost, context_used, context_max, tool_calls, execution_time_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message_id, session_id, agent_name, user_id, user_email,
                role, content, now,
                cost, context_used, context_max, tool_calls, execution_time_ms
            ))

            # Update session stats
            cursor.execute("""
                UPDATE chat_sessions
                SET last_message_at = ?,
                    message_count = message_count + 1,
                    total_cost = total_cost + COALESCE(?, 0),
                    total_context_used = COALESCE(?, total_context_used),
                    total_context_max = COALESCE(?, total_context_max)
                WHERE id = ?
            """, (now, cost or 0, context_used, context_max, session_id))

            conn.commit()

            # Return the created message
            cursor.execute("SELECT * FROM chat_messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            return self._row_to_chat_message(row)

    def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a specific chat session by ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return self._row_to_chat_session(row) if row else None

    def get_chat_messages(self, session_id: str, limit: int = 100) -> List[ChatMessage]:
        """Get messages for a chat session (newest first)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            return [self._row_to_chat_message(row) for row in cursor.fetchall()]

    def get_agent_chat_history(
        self,
        agent_name: str,
        user_id: Optional[int] = None,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get chat history for an agent.
        If user_id is provided, filter to that user's messages.
        Returns messages across all sessions, newest first.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT * FROM chat_messages
                    WHERE agent_name = ? AND user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (agent_name, user_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM chat_messages
                    WHERE agent_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (agent_name, limit))
            return [self._row_to_chat_message(row) for row in cursor.fetchall()]

    def get_agent_chat_sessions(
        self,
        agent_name: str,
        user_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ChatSession]:
        """
        Get all chat sessions for an agent.
        Optionally filter by user_id and/or status.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM chat_sessions WHERE agent_name = ?"
            params = [agent_name]

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY last_message_at DESC"

            cursor.execute(query, params)
            return [self._row_to_chat_session(row) for row in cursor.fetchall()]

    def close_chat_session(self, session_id: str) -> bool:
        """Mark a chat session as closed."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE chat_sessions SET status = 'closed' WHERE id = ?
            """, (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    def create_new_chat_session(self, agent_name: str, user_id: int, user_email: str) -> ChatSession:
        """
        Create a new chat session, closing any existing active sessions for this user+agent.
        Use this when user explicitly wants a new conversation (e.g., "New Chat" button).
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Close any existing active sessions for this user+agent
            cursor.execute("""
                UPDATE chat_sessions SET status = 'closed'
                WHERE agent_name = ? AND user_id = ? AND status = 'active'
            """, (agent_name, user_id))

            # Create a new session
            session_id = secrets.token_urlsafe(16)
            now = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO chat_sessions (
                    id, agent_name, user_id, user_email, started_at, last_message_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, agent_name, user_id, user_email, now, now))

            conn.commit()

            # Return the newly created session
            cursor.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return self._row_to_chat_session(row)

    def delete_chat_session(self, session_id: str) -> bool:
        """Delete a chat session and all its messages."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Delete messages first (foreign key constraint)
            cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))

            # Delete session
            cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))

            conn.commit()
            return cursor.rowcount > 0
