"""
Session activity endpoints for real-time monitoring.
"""
from fastapi import APIRouter, HTTPException

from ..state import agent_state

router = APIRouter()


@router.get("/api/activity")
async def get_session_activity():
    """
    Get session activity summary for real-time monitoring.

    Returns the current session activity including:
    - status: "running" or "idle"
    - active_tool: currently executing tool (if any)
    - tool_counts: count of each tool used
    - timeline: list of tool executions (newest first)
    - totals: aggregate statistics
    """
    return agent_state.session_activity


@router.get("/api/activity/{tool_id}")
async def get_tool_call_detail(tool_id: str):
    """
    Get full details for a specific tool call.

    Returns the complete input and output for drill-down inspection.
    """
    # Find the timeline entry
    for entry in agent_state.session_activity["timeline"]:
        if entry["id"] == tool_id:
            # Get full output from tool_outputs if available
            full_output = agent_state.tool_outputs.get(tool_id, entry.get("output_summary", ""))

            return {
                "id": entry["id"],
                "tool": entry["tool"],
                "input": entry["input"],
                "output": full_output,
                "duration_ms": entry["duration_ms"],
                "started_at": entry["started_at"],
                "ended_at": entry["ended_at"],
                "success": entry["success"]
            }

    raise HTTPException(status_code=404, detail=f"Tool call {tool_id} not found")


@router.delete("/api/activity")
async def clear_session_activity():
    """
    Clear session activity (called when starting a new session).

    This only clears the activity tracking, not the conversation history.
    Use DELETE /api/chat/history to clear everything.
    """
    agent_state.session_activity = agent_state._create_empty_activity()
    agent_state.tool_outputs = {}
    return {
        "status": "cleared",
        "message": "Session activity cleared"
    }
