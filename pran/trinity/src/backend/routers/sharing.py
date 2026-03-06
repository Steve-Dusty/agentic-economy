"""
Agent sharing routes for the Trinity backend.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Request

from models import User
from database import db, AgentShare, AgentShareRequest
from dependencies import get_current_user, OwnedAgentByName, CurrentUser
from services.docker_service import get_agent_container

router = APIRouter(prefix="/api/agents", tags=["sharing"])

# WebSocket manager will be injected from main.py
manager = None

def set_websocket_manager(ws_manager):
    """Set the WebSocket manager for broadcasting events."""
    global manager
    manager = ws_manager


@router.post("/{agent_name}/share", response_model=AgentShare)
async def share_agent_endpoint(
    agent_name: OwnedAgentByName,
    share_request: AgentShareRequest,
    request: Request,
    current_user: CurrentUser
):
    """Share an agent with another user by email."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    current_user_data = db.get_user_by_username(current_user.username)
    current_user_email = (current_user_data.get("email") or "") if current_user_data else ""
    if current_user_email and current_user_email.lower() == share_request.email.lower():
        raise HTTPException(status_code=400, detail="Cannot share an agent with yourself")

    share = db.share_agent(agent_name, current_user.username, share_request.email)
    if not share:
        raise HTTPException(status_code=409, detail=f"Agent is already shared with {share_request.email}")

    # Auto-add email to whitelist if email auth is enabled (Phase 12.4)
    from config import EMAIL_AUTH_ENABLED
    email_auth_setting = db.get_setting_value("email_auth_enabled", str(EMAIL_AUTH_ENABLED).lower())
    if email_auth_setting.lower() == "true":
        try:
            db.add_to_whitelist(
                share_request.email,
                current_user.username,
                source="agent_sharing"
            )
        except Exception:
            # Already whitelisted or error - continue anyway
            pass

    if manager:
        await manager.broadcast(json.dumps({
            "event": "agent_shared",
            "data": {"name": agent_name, "shared_with": share_request.email}
        }))

    return share


@router.delete("/{agent_name}/share/{email}")
async def unshare_agent_endpoint(
    agent_name: OwnedAgentByName,
    email: str,
    request: Request,
    current_user: CurrentUser
):
    """Remove sharing access for a user."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    success = db.unshare_agent(agent_name, current_user.username, email)
    if not success:
        raise HTTPException(status_code=404, detail=f"No sharing found for {email}")

    if manager:
        await manager.broadcast(json.dumps({
            "event": "agent_unshared",
            "data": {"name": agent_name, "removed_user": email}
        }))

    return {"message": f"Sharing removed for {email}"}


@router.get("/{agent_name}/shares", response_model=list[AgentShare])
async def get_agent_shares_endpoint(
    agent_name: OwnedAgentByName,
    request: Request
):
    """Get all users an agent is shared with."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    shares = db.get_agent_shares(agent_name)
    return shares
