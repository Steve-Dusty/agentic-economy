"""
Service modules for the agent server.
"""
from .activity_tracking import start_tool_execution, complete_tool_execution
from .runtime_adapter import get_runtime, AgentRuntime
from .trinity_mcp import inject_trinity_mcp_if_configured

# Backward compatibility - expose Claude-specific functions
from .claude_code import execute_claude_code, get_claude_runtime

__all__ = [
    "start_tool_execution",
    "complete_tool_execution",
    "get_runtime",
    "AgentRuntime",
    "inject_trinity_mcp_if_configured",
    # Backward compatibility
    "execute_claude_code",
    "get_claude_runtime",
]
