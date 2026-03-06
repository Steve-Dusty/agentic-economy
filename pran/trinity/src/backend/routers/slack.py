"""
Slack integration router (SLACK-001).

Provides:
- Public endpoints for Slack events and OAuth callback
- Authenticated endpoints for connection management

Public Endpoints (no auth):
- POST /api/public/slack/events - Receive Slack events
- GET /api/public/slack/oauth/callback - OAuth completion redirect

Authenticated Endpoints:
- GET /api/agents/{name}/public-links/{link_id}/slack - Connection status
- POST /api/agents/{name}/public-links/{link_id}/slack/connect - Start OAuth
- DELETE /api/agents/{name}/public-links/{link_id}/slack - Disconnect
"""

import logging
import random
import string
import httpx
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from database import db
from dependencies import get_current_user
from models import User
from services.slack_service import slack_service
from services.email_service import email_service
from services.docker_service import get_agent_container
from db_models import SlackConnectionStatus, SlackOAuthInitResponse
from config import SLACK_SIGNING_SECRET, SLACK_AUTO_VERIFY_EMAIL


logger = logging.getLogger(__name__)


# =========================================================================
# Public Router (no authentication required)
# =========================================================================

public_router = APIRouter(prefix="/api/public/slack", tags=["slack-public"])


class SlackEventResponse(BaseModel):
    """Response to Slack events (always return 200)."""
    ok: bool = True
    challenge: Optional[str] = None


@public_router.post("/events", response_model=SlackEventResponse)
async def handle_slack_event(request: Request):
    """
    Handle incoming Slack events.

    Slack requires:
    1. URL verification challenge (one-time setup)
    2. Event callbacks (DM messages)

    Always returns 200 to prevent Slack retries.
    Errors are logged internally.
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    is_valid, error = slack_service.verify_slack_signature(timestamp, body, signature)
    if not is_valid:
        logger.warning(f"Slack signature verification failed: {error}")
        # Still return 200 to prevent retries, but log the error
        return SlackEventResponse(ok=False)

    # Parse event
    try:
        event_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse Slack event: {e}")
        return SlackEventResponse(ok=False)

    event_type = event_data.get("type")

    # Handle URL verification challenge
    if event_type == "url_verification":
        challenge = event_data.get("challenge")
        logger.info("Slack URL verification challenge received")
        return SlackEventResponse(ok=True, challenge=challenge)

    # Handle event callback
    if event_type == "event_callback":
        team_id = event_data.get("team_id")
        event = event_data.get("event", {})

        # Process DM message
        if event.get("type") == "message" and event.get("channel_type") == "im":
            await _handle_slack_dm(team_id, event)

        return SlackEventResponse(ok=True)

    logger.info(f"Unhandled Slack event type: {event_type}")
    return SlackEventResponse(ok=True)


async def _handle_slack_dm(team_id: str, event: dict):
    """
    Handle a DM message to the bot.

    Flow:
    1. Look up connection by team_id
    2. Check if user is verified (if required)
    3. Get/create session
    4. Forward to agent
    5. Send response back to Slack
    """
    user_id = event.get("user")
    text = event.get("text", "").strip()
    channel = event.get("channel")

    # Ignore bot messages
    if event.get("bot_id"):
        return

    # Ignore empty messages
    if not text:
        return

    # Look up connection
    connection = db.get_slack_connection_by_team(team_id)
    if not connection:
        logger.warning(f"No Slack connection found for team {team_id}")
        return

    link_id = connection["link_id"]
    agent_name = connection["agent_name"]
    require_email = connection["require_email"]
    bot_token = connection["slack_bot_token"]

    # Check agent availability
    container = get_agent_container(agent_name)
    if not container or container.status != "running":
        await slack_service.send_message(
            bot_token, channel,
            "Sorry, I'm not available right now. Please try again later."
        )
        return

    # Handle verification flow if required
    if require_email:
        verified = await _handle_slack_verification(
            link_id, user_id, team_id, channel, text, bot_token
        )
        if not verified:
            return  # Verification flow will send its own messages

    # Forward message to agent
    try:
        response_text = await _forward_to_agent(
            agent_name, link_id, user_id, team_id, text
        )

        # Send response back to Slack
        await slack_service.send_message(bot_token, channel, response_text)

    except Exception as e:
        logger.error(f"Error processing Slack message: {e}")
        await slack_service.send_message(
            bot_token, channel,
            "Sorry, I encountered an error processing your message. Please try again."
        )


async def _handle_slack_verification(
    link_id: str,
    user_id: str,
    team_id: str,
    channel: str,
    text: str,
    bot_token: str
) -> bool:
    """
    Handle Slack user verification flow.

    Returns True if user is verified and message should proceed.
    Returns False if verification flow is in progress.
    """
    # Check if already verified
    verification = db.get_slack_user_verification(link_id, user_id, team_id)
    if verification:
        return True

    # Check for pending verification
    pending = db.get_slack_pending_verification(user_id, team_id)

    # No pending verification - try auto-verify or start flow
    if not pending:
        # Try auto-verify via Slack profile email
        if SLACK_AUTO_VERIFY_EMAIL:
            email = await slack_service.get_user_email(bot_token, user_id)
            if email:
                db.create_slack_user_verification(
                    link_id, user_id, team_id, email, "slack_profile"
                )
                return True

        # Start verification flow
        db.create_slack_pending_verification(link_id, user_id, team_id)
        await slack_service.send_message(
            bot_token, channel,
            "Hi! Before we chat, I need to verify your email address.\n\n"
            "Please reply with your email address to continue."
        )
        return False

    # Handle verification states
    state = pending.get("state")

    if state == "awaiting_email":
        # User should be providing email
        email = _extract_email(text)
        if not email:
            await slack_service.send_message(
                bot_token, channel,
                "That doesn't look like a valid email address. "
                "Please reply with your email to continue."
            )
            return False

        # Generate and send verification code
        code = _generate_verification_code()
        db.update_slack_pending_verification(user_id, team_id, email=email, code=code, state="awaiting_code")

        # Send email
        try:
            await email_service.send_verification_code(email, code)
            await slack_service.send_message(
                bot_token, channel,
                f"I've sent a 6-digit verification code to {email}.\n\n"
                "Reply with the code to complete verification. The code expires in 10 minutes."
            )
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            await slack_service.send_message(
                bot_token, channel,
                "Sorry, I couldn't send the verification email. Please try again."
            )
            db.delete_slack_pending_verification(user_id, team_id)

        return False

    if state == "awaiting_code":
        # User should be providing code
        code = _extract_code(text)
        expected_code = pending.get("code")
        email = pending.get("email")

        if not code or code != expected_code:
            await slack_service.send_message(
                bot_token, channel,
                "That code doesn't match. Please enter the 6-digit code from your email."
            )
            return False

        # Verification successful!
        db.create_slack_user_verification(
            link_id, user_id, team_id, email, "email_code"
        )
        db.delete_slack_pending_verification(user_id, team_id)

        await slack_service.send_message(
            bot_token, channel,
            "Verified! You can now chat with me.\n\n"
            "What would you like to know?"
        )
        return False  # Don't process the code message as a chat

    return False


async def _forward_to_agent(
    agent_name: str,
    link_id: str,
    user_id: str,
    team_id: str,
    message: str
) -> str:
    """
    Forward a Slack message to the agent and get response.

    Uses the public chat session infrastructure with Slack identifier.
    """
    # Build session identifier for Slack: team:user
    session_identifier = f"{team_id}:{user_id}"

    # Get or create session
    session = db.get_or_create_public_chat_session(link_id, session_identifier, "slack")

    # Build context prompt with chat history
    context_prompt = db.build_public_chat_context(session["id"], message)

    # Call agent via /api/task endpoint
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"http://agent-{agent_name}:8000/api/task",
                json={"prompt": context_prompt}
            )

            if response.status_code != 200:
                logger.error(f"Agent task failed: {response.status_code}")
                return "Sorry, I couldn't process your request."

            data = response.json()
            response_text = data.get("response", "")

            # Update session
            db.add_public_chat_message(session["id"], "user", message)
            db.add_public_chat_message(session["id"], "assistant", response_text, cost=data.get("cost"))

            return response_text

    except Exception as e:
        logger.error(f"Error calling agent: {e}")
        return "Sorry, I encountered an error. Please try again."


def _extract_email(text: str) -> Optional[str]:
    """Extract email address from text."""
    import re
    match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    return match.group(0) if match else None


def _extract_code(text: str) -> Optional[str]:
    """Extract 6-digit code from text."""
    import re
    match = re.search(r'\b(\d{6})\b', text)
    return match.group(1) if match else None


def _generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))


@public_router.get("/oauth/callback")
async def slack_oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    Handle Slack OAuth callback.

    Exchanges code for token and creates connection.
    Redirects to frontend with success/error status.
    """
    # Handle OAuth errors
    if error:
        logger.error(f"Slack OAuth error: {error}")
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect("unknown", success=False, error=error)
        )

    if not code or not state:
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect("unknown", success=False, error="missing_params")
        )

    # Decode and verify state
    valid, state_data = slack_service.decode_oauth_state(state)
    if not valid or not state_data:
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect("unknown", success=False, error="invalid_state")
        )

    link_id = state_data["link_id"]
    agent_name = state_data["agent_name"]
    user_id = state_data["user_id"]

    # Exchange code for token
    success, result = await slack_service.exchange_oauth_code(code)
    if not success:
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect(agent_name, success=False, error=result.get("error"))
        )

    # Create connection
    try:
        db.create_slack_connection(
            link_id=link_id,
            slack_team_id=result["team_id"],
            slack_team_name=result.get("team_name"),
            slack_bot_token=result["access_token"],
            connected_by=user_id
        )

        logger.info(f"Slack connection created for link {link_id} to workspace {result.get('team_name')}")

        return RedirectResponse(
            slack_service.get_oauth_callback_redirect(agent_name, success=True)
        )

    except Exception as e:
        logger.error(f"Failed to create Slack connection: {e}")
        return RedirectResponse(
            slack_service.get_oauth_callback_redirect(agent_name, success=False, error="database_error")
        )


# =========================================================================
# Authenticated Router (requires login)
# =========================================================================

auth_router = APIRouter(tags=["slack"])


@auth_router.get("/api/agents/{name}/public-links/{link_id}/slack", response_model=SlackConnectionStatus)
async def get_slack_connection_status(
    name: str,
    link_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get Slack connection status for a public link."""
    # Verify user has access to the agent
    if not db.can_user_access_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Access denied")

    # Verify link belongs to agent
    link = db.get_public_link(link_id)
    if not link or link["agent_name"] != name:
        raise HTTPException(status_code=404, detail="Public link not found")

    # Get connection
    connection = db.get_slack_connection_by_link(link_id)
    if not connection:
        return SlackConnectionStatus(connected=False)

    # Get user who connected
    connected_by_user = db.get_user_by_id(int(connection["connected_by"]))
    connected_by_email = connected_by_user.get("email", "unknown") if connected_by_user else "unknown"

    return SlackConnectionStatus(
        connected=True,
        team_id=connection["slack_team_id"],
        team_name=connection["slack_team_name"],
        connected_at=connection["connected_at"],
        connected_by=connected_by_email,
        enabled=connection["enabled"]
    )


@auth_router.post("/api/agents/{name}/public-links/{link_id}/slack/connect", response_model=SlackOAuthInitResponse)
async def initiate_slack_oauth(
    name: str,
    link_id: str,
    current_user: User = Depends(get_current_user)
):
    """Initiate Slack OAuth flow to connect a workspace."""
    # Verify user is owner (can_user_share_agent returns True for owners and admins)
    if not db.can_user_share_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Only owners can connect Slack")

    # Verify link belongs to agent
    link = db.get_public_link(link_id)
    if not link or link["agent_name"] != name:
        raise HTTPException(status_code=404, detail="Public link not found")

    # Check if already connected
    existing = db.get_slack_connection_by_link(link_id)
    if existing:
        raise HTTPException(status_code=400, detail="Slack already connected. Disconnect first.")

    if not SLACK_SIGNING_SECRET:
        raise HTTPException(status_code=400, detail="Slack integration not configured")

    # Generate OAuth state
    state = slack_service.encode_oauth_state(link_id, name, str(current_user.id))

    # Get OAuth URL
    try:
        oauth_url = slack_service.get_oauth_url(state)
        return SlackOAuthInitResponse(oauth_url=oauth_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.delete("/api/agents/{name}/public-links/{link_id}/slack")
async def disconnect_slack(
    name: str,
    link_id: str,
    current_user: User = Depends(get_current_user)
):
    """Disconnect Slack workspace from public link."""
    # Verify user is owner (can_user_share_agent returns True for owners and admins)
    if not db.can_user_share_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Only owners can disconnect Slack")

    # Verify link belongs to agent
    link = db.get_public_link(link_id)
    if not link or link["agent_name"] != name:
        raise HTTPException(status_code=404, detail="Public link not found")

    # Delete connection
    deleted = db.delete_slack_connection_by_link(link_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="No Slack connection found")

    logger.info(f"Slack disconnected from link {link_id} by user {current_user.id}")

    return {"disconnected": True}


@auth_router.put("/api/agents/{name}/public-links/{link_id}/slack")
async def update_slack_connection(
    name: str,
    link_id: str,
    enabled: bool = None,
    current_user: User = Depends(get_current_user)
):
    """Update Slack connection settings (enable/disable)."""
    # Verify user is owner (can_user_share_agent returns True for owners and admins)
    if not db.can_user_share_agent(current_user.username, name):
        raise HTTPException(status_code=403, detail="Only owners can modify Slack settings")

    # Verify link belongs to agent
    link = db.get_public_link(link_id)
    if not link or link["agent_name"] != name:
        raise HTTPException(status_code=404, detail="Public link not found")

    # Get connection
    connection = db.get_slack_connection_by_link(link_id)
    if not connection:
        raise HTTPException(status_code=404, detail="No Slack connection found")

    # Update
    db.update_slack_connection(connection["id"], enabled=enabled)

    return {"updated": True, "enabled": enabled}
