"""
Session activity tracking for real-time monitoring.
"""
from datetime import datetime
from typing import Dict, Any

from ..state import agent_state
from ..utils.helpers import get_tool_name, get_input_summary, truncate_output


def start_tool_execution(tool_id: str, tool: str, input_data: Dict[str, Any]):
    """Record start of a tool execution"""
    now = datetime.now()
    display_name = get_tool_name(tool, input_data)
    input_summary = get_input_summary(tool, input_data)

    # Set session as running
    agent_state.session_activity["status"] = "running"
    agent_state.session_activity["active_tool"] = {
        "name": display_name,
        "input_summary": input_summary,
        "started_at": now.isoformat()
    }

    # Initialize totals.started_at if this is the first call
    if agent_state.session_activity["totals"]["started_at"] is None:
        agent_state.session_activity["totals"]["started_at"] = now.isoformat()

    # Add to timeline (newest first)
    timeline_entry = {
        "id": tool_id,
        "tool": display_name,
        "input": input_data,
        "input_summary": input_summary,
        "output_summary": None,
        "duration_ms": None,
        "started_at": now.isoformat(),
        "ended_at": None,
        "success": None,
        "status": "running"
    }
    # Insert at beginning (newest first)
    agent_state.session_activity["timeline"].insert(0, timeline_entry)

    # Update tool counts
    if display_name not in agent_state.session_activity["tool_counts"]:
        agent_state.session_activity["tool_counts"][display_name] = 0
    agent_state.session_activity["tool_counts"][display_name] += 1

    # Update totals
    agent_state.session_activity["totals"]["calls"] += 1


def complete_tool_execution(tool_id: str, success: bool, output: str = None):
    """Record completion of a tool execution"""
    now = datetime.now()

    # Find the timeline entry
    for entry in agent_state.session_activity["timeline"]:
        if entry["id"] == tool_id and entry["status"] == "running":
            started_at = datetime.fromisoformat(entry["started_at"])
            duration_ms = int((now - started_at).total_seconds() * 1000)

            entry["ended_at"] = now.isoformat()
            entry["duration_ms"] = duration_ms
            entry["success"] = success
            entry["status"] = "completed"
            entry["output_summary"] = truncate_output(output) if output else None

            # Update total duration
            agent_state.session_activity["totals"]["duration_ms"] += duration_ms
            break

    # Store full output for drill-down
    if output:
        agent_state.tool_outputs[tool_id] = output

    # Clear active tool
    agent_state.session_activity["active_tool"] = None

    # Check if there are any other running tools
    has_running = any(e["status"] == "running" for e in agent_state.session_activity["timeline"])
    if not has_running:
        agent_state.session_activity["status"] = "idle"
