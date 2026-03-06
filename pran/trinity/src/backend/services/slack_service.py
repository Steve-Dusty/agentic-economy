"""
Slack integration service (SLACK-001).

Provides:
- Slack request signature verification
- Slack API interactions (chat.postMessage, users.info)
- OAuth token exchange
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Optional, Tuple
from urllib.parse import urlencode

import httpx

from config import (
    PUBLIC_CHAT_URL,
    FRONTEND_URL,
    SECRET_KEY
)
from services.settings_service import (
    get_slack_signing_secret,
    get_slack_client_id,
    get_slack_client_secret,
)

logger = logging.getLogger(__name__)


class SlackService:
    """Service for Slack API interactions."""

    SLACK_API_BASE = "https://slack.com/api"
    SLACK_OAUTH_URL = "https://slack.com/oauth/v2/authorize"

    def __init__(self):
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialize async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    # =========================================================================
    # Request Verification
    # =========================================================================

    def verify_slack_signature(
        self,
        timestamp: str,
        body: bytes,
        signature: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify that a request came from Slack using the signing secret.

        Returns (is_valid, error_reason).
        """
        signing_secret = get_slack_signing_secret()
        if not signing_secret:
            return False, "Slack Signing Secret not configured"

        # Reject requests older than 5 minutes (prevent replay attacks)
        try:
            request_timestamp = int(timestamp)
            if abs(time.time() - request_timestamp) > 60 * 5:
                return False, "Request timestamp too old"
        except (ValueError, TypeError):
            return False, "Invalid timestamp"

        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected_signature = 'v0=' + hmac.new(
            signing_secret.encode('utf-8'),
            sig_basestring.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison
        if not hmac.compare_digest(expected_signature, signature):
            return False, "Invalid signature"

        return True, None

    # =========================================================================
    # OAuth Flow
    # =========================================================================

    def get_oauth_url(self, state: str) -> str:
        """Generate Slack OAuth URL for workspace installation."""
        if not PUBLIC_CHAT_URL:
            raise ValueError("PUBLIC_CHAT_URL not configured")

        redirect_uri = f"{PUBLIC_CHAT_URL}/api/public/slack/oauth/callback"

        params = {
            "client_id": get_slack_client_id(),
            "scope": "im:history,chat:write,users:read.email",
            "redirect_uri": redirect_uri,
            "state": state
        }

        return f"{self.SLACK_OAUTH_URL}?{urlencode(params)}"

    async def exchange_oauth_code(self, code: str) -> Tuple[bool, dict]:
        """
        Exchange OAuth authorization code for access token.

        Returns (success, result_dict).
        result_dict contains either the token info or error info.
        """
        if not PUBLIC_CHAT_URL:
            return False, {"error": "PUBLIC_CHAT_URL not configured"}

        redirect_uri = f"{PUBLIC_CHAT_URL}/api/public/slack/oauth/callback"

        try:
            response = await self.client.post(
                f"{self.SLACK_API_BASE}/oauth.v2.access",
                data={
                    "client_id": get_slack_client_id(),
                    "client_secret": get_slack_client_secret(),
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            data = response.json()

            if not data.get("ok"):
                logger.error(f"Slack OAuth error: {data.get('error')}")
                return False, {"error": data.get("error", "unknown_error")}

            return True, {
                "access_token": data.get("access_token"),
                "team_id": data.get("team", {}).get("id"),
                "team_name": data.get("team", {}).get("name"),
                "bot_user_id": data.get("bot_user_id"),
                "scope": data.get("scope")
            }

        except Exception as e:
            logger.error(f"Slack OAuth exchange failed: {e}")
            return False, {"error": str(e)}

    def encode_oauth_state(self, link_id: str, agent_name: str, user_id: str) -> str:
        """Encode OAuth state as a signed token."""
        import base64
        import json

        state_data = {
            "link_id": link_id,
            "agent_name": agent_name,
            "user_id": user_id,
            "timestamp": int(time.time())
        }
        state_json = json.dumps(state_data, separators=(',', ':'))

        # Sign the state
        signature = hmac.new(
            SECRET_KEY.encode(),
            state_json.encode(),
            hashlib.sha256
        ).hexdigest()[:16]

        # Combine and base64 encode
        combined = f"{state_json}:{signature}"
        return base64.urlsafe_b64encode(combined.encode()).decode()

    def decode_oauth_state(self, state: str) -> Tuple[bool, Optional[dict]]:
        """Decode and verify OAuth state token."""
        import base64

        try:
            decoded = base64.urlsafe_b64decode(state.encode()).decode()
            state_json, signature = decoded.rsplit(':', 1)

            # Verify signature
            expected_signature = hmac.new(
                SECRET_KEY.encode(),
                state_json.encode(),
                hashlib.sha256
            ).hexdigest()[:16]

            if not hmac.compare_digest(expected_signature, signature):
                return False, None

            state_data = json.loads(state_json)

            # Check timestamp (15 minute expiry)
            if time.time() - state_data.get("timestamp", 0) > 15 * 60:
                return False, None

            return True, state_data

        except Exception as e:
            logger.error(f"Failed to decode OAuth state: {e}")
            return False, None

    # =========================================================================
    # Slack API Interactions
    # =========================================================================

    async def send_message(
        self,
        bot_token: str,
        channel: str,
        text: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Send a message to a Slack channel/DM.

        Returns (success, error_message).
        """
        try:
            response = await self.client.post(
                f"{self.SLACK_API_BASE}/chat.postMessage",
                headers={"Authorization": f"Bearer {bot_token}"},
                json={
                    "channel": channel,
                    "text": text
                }
            )
            data = response.json()

            if not data.get("ok"):
                error = data.get("error", "unknown_error")
                logger.error(f"Slack chat.postMessage failed: {error}")
                return False, error

            return True, None

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False, str(e)

    async def get_user_email(
        self,
        bot_token: str,
        user_id: str
    ) -> Optional[str]:
        """
        Get a user's email from their Slack profile.

        Requires users:read.email scope.
        Returns None if not available.
        """
        try:
            response = await self.client.get(
                f"{self.SLACK_API_BASE}/users.info",
                headers={"Authorization": f"Bearer {bot_token}"},
                params={"user": user_id}
            )
            data = response.json()

            if not data.get("ok"):
                logger.warning(f"Failed to get Slack user info: {data.get('error')}")
                return None

            user = data.get("user", {})
            profile = user.get("profile", {})
            return profile.get("email")

        except Exception as e:
            logger.error(f"Failed to get Slack user email: {e}")
            return None

    async def open_dm_channel(
        self,
        bot_token: str,
        user_id: str
    ) -> Optional[str]:
        """
        Open a DM channel with a user.

        Returns the channel ID.
        """
        try:
            response = await self.client.post(
                f"{self.SLACK_API_BASE}/conversations.open",
                headers={"Authorization": f"Bearer {bot_token}"},
                json={"users": user_id}
            )
            data = response.json()

            if not data.get("ok"):
                logger.error(f"Failed to open DM channel: {data.get('error')}")
                return None

            return data.get("channel", {}).get("id")

        except Exception as e:
            logger.error(f"Failed to open Slack DM channel: {e}")
            return None

    def get_oauth_callback_redirect(
        self,
        agent_name: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        """Get the redirect URL after OAuth completion."""
        base_url = FRONTEND_URL or "http://localhost"
        if success:
            return f"{base_url}/agents/{agent_name}?tab=sharing&slack=connected"
        else:
            return f"{base_url}/agents/{agent_name}?tab=sharing&slack=error&reason={error or 'unknown'}"


# Singleton instance
slack_service = SlackService()
