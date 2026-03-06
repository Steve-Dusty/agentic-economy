"""
Agent state management for the agent server.
"""
import os
import subprocess
import logging
from typing import List, Dict, Optional
from datetime import datetime

from .models import ChatMessage

logger = logging.getLogger(__name__)


class AgentState:
    """
    Manages the state of the agent including conversation history,
    session tracking, and real-time activity monitoring.
    """

    def __init__(self):
        self.conversation_history: List[ChatMessage] = []
        self.agent_name = os.getenv("AGENT_NAME", "unknown")
        self.agent_runtime = os.getenv("AGENT_RUNTIME", "claude-code")
        # Check if the configured runtime is available
        self.runtime_available = self._check_runtime_available()
        # Backward compatibility alias
        self.claude_code_available = self.runtime_available if self.agent_runtime == "claude-code" else self._check_claude_code()
        self.session_started = False  # Track if we've started a conversation
        # Session-level token tracking
        self.session_total_cost: float = 0.0
        self.session_total_output_tokens: int = 0
        self.session_context_tokens: int = 0  # Latest context size
        self.session_context_window: int = self._get_default_context_window()
        # Model selection (persists across session)
        self.current_model: Optional[str] = os.getenv("AGENT_RUNTIME_MODEL", None) or os.getenv("CLAUDE_MODEL", None)
        # Session activity tracking (for real-time monitoring)
        self.session_activity = self._create_empty_activity()
        # Store full tool outputs for drill-down (separate from timeline summaries)
        self.tool_outputs: Dict[str, str] = {}

    def _get_default_context_window(self) -> int:
        """Get default context window based on runtime"""
        if self.agent_runtime == "gemini-cli" or self.agent_runtime == "gemini":
            return 1000000  # 1M tokens for Gemini
        return 200000  # 200K for Claude Code

    def _check_runtime_available(self) -> bool:
        """Check if the configured runtime CLI is available"""
        if self.agent_runtime == "gemini-cli" or self.agent_runtime == "gemini":
            return self._check_gemini_cli()
        return self._check_claude_code()

    def _check_gemini_cli(self) -> bool:
        """Check if Gemini CLI is available"""
        try:
            result = subprocess.run(
                ["gemini", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Gemini CLI check failed: {e}")
            return False

    def _create_empty_activity(self) -> Dict:
        """Create empty session activity structure"""
        return {
            "status": "idle",
            "active_tool": None,
            "tool_counts": {},
            "timeline": [],
            "totals": {
                "calls": 0,
                "duration_ms": 0,
                "started_at": None
            }
        }

    def _check_claude_code(self) -> bool:
        """Check if Claude Code CLI is available"""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Claude Code check failed: {e}")
            return False

    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append(
            ChatMessage(
                role=role,
                content=content,
                timestamp=datetime.now()
            )
        )

    def reset_session(self):
        """Reset conversation state and token tracking"""
        self.conversation_history = []
        self.session_started = False
        self.session_total_cost = 0.0
        self.session_total_output_tokens = 0
        self.session_context_tokens = 0
        # Note: current_model is NOT reset - it persists until explicitly changed
        # Reset session activity tracking
        self.session_activity = self._create_empty_activity()
        self.tool_outputs = {}


# Global agent state instance
agent_state = AgentState()
