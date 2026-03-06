"""
Subscription Management Tests (test_subscriptions.py)

Tests for SUB-001: Claude Max/Pro subscription credential management.
Subscriptions are registered once and can be assigned to multiple agents.
Credentials are encrypted using AES-256-GCM.

Test tiers:
- SMOKE: Subscription CRUD, validation (no agent required)
- AGENT: Assignment, injection, auth status (requires running agent)
"""

import pytest
import uuid
import json
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
)


# =============================================================================
# Test Data
# =============================================================================

VALID_CREDENTIALS = json.dumps({
    "claudeAiOauth": {
        "accessToken": "sk-ant-oat01-test-access-token-12345",
        "refreshToken": "sk-ant-ort01-test-refresh-token-67890",
        "expiresAt": 1893456000000,  # 2030-01-01
        "subscriptionType": "max",
        "rateLimitTier": "default_claude_max_20x",
        "scopes": ["user:inference", "user:profile"]
    }
})

INVALID_CREDENTIALS = "not valid json {"


# =============================================================================
# Subscription CRUD Tests (SMOKE)
# =============================================================================

class TestSubscriptionCRUD:
    """SUB-001: Subscription CRUD endpoint tests."""

    @pytest.mark.smoke
    def test_list_subscriptions_empty(self, api_client: TrinityApiClient):
        """GET /api/subscriptions returns list (may be empty)."""
        response = api_client.get("/api/subscriptions")
        assert_status(response, 200)
        data = assert_json_response(response)
        assert isinstance(data, list)

    @pytest.mark.smoke
    def test_register_subscription(self, api_client: TrinityApiClient):
        """POST /api/subscriptions creates new subscription."""
        name = f"test-sub-{uuid.uuid4().hex[:8]}"

        response = api_client.post(
            "/api/subscriptions",
            json={
                "name": name,
                "credentials_json": VALID_CREDENTIALS,
                "subscription_type": "max",
                "rate_limit_tier": "default_claude_max_20x"
            }
        )

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, ["id", "name", "subscription_type", "owner_id", "created_at"])
        assert data["name"] == name
        assert data["subscription_type"] == "max"

        # Cleanup
        api_client.delete(f"/api/subscriptions/{data['id']}")

    @pytest.mark.smoke
    def test_register_subscription_upsert(self, api_client: TrinityApiClient):
        """POST /api/subscriptions with same name updates existing."""
        name = f"test-sub-upsert-{uuid.uuid4().hex[:8]}"

        # Create first
        response1 = api_client.post(
            "/api/subscriptions",
            json={"name": name, "credentials_json": VALID_CREDENTIALS, "subscription_type": "max"}
        )
        assert_status(response1, 200)
        id1 = response1.json()["id"]

        # Update with same name
        response2 = api_client.post(
            "/api/subscriptions",
            json={"name": name, "credentials_json": VALID_CREDENTIALS, "subscription_type": "pro"}
        )
        assert_status(response2, 200)
        data2 = response2.json()

        # Same ID, updated type
        assert data2["id"] == id1
        assert data2["subscription_type"] == "pro"

        # Cleanup
        api_client.delete(f"/api/subscriptions/{id1}")

    @pytest.mark.smoke
    def test_register_subscription_invalid_json(self, api_client: TrinityApiClient):
        """POST /api/subscriptions with invalid JSON returns 400."""
        response = api_client.post(
            "/api/subscriptions",
            json={"name": "test-invalid", "credentials_json": INVALID_CREDENTIALS}
        )
        assert_status(response, 400)

    @pytest.mark.smoke
    def test_register_subscription_missing_name(self, api_client: TrinityApiClient):
        """POST /api/subscriptions without name returns 422."""
        response = api_client.post(
            "/api/subscriptions",
            json={"credentials_json": VALID_CREDENTIALS}
        )
        assert_status(response, 422)

    @pytest.mark.smoke
    def test_list_subscriptions_with_agents(self, api_client: TrinityApiClient):
        """GET /api/subscriptions returns agent counts and names."""
        # Create subscription
        name = f"test-sub-list-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            "/api/subscriptions",
            json={"name": name, "credentials_json": VALID_CREDENTIALS}
        )
        assert_status(response, 200)
        sub_id = response.json()["id"]

        # List and verify structure
        response = api_client.get("/api/subscriptions")
        assert_status(response, 200)
        data = assert_json_response(response)

        # Find our subscription
        our_sub = next((s for s in data if s["id"] == sub_id), None)
        assert our_sub is not None
        assert "agent_count" in our_sub
        assert "agents" in our_sub
        assert isinstance(our_sub["agents"], list)

        # Cleanup
        api_client.delete(f"/api/subscriptions/{sub_id}")

    @pytest.mark.smoke
    def test_delete_subscription(self, api_client: TrinityApiClient):
        """DELETE /api/subscriptions/{id} removes subscription."""
        # Create
        name = f"test-sub-del-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            "/api/subscriptions",
            json={"name": name, "credentials_json": VALID_CREDENTIALS}
        )
        sub_id = response.json()["id"]

        # Delete
        response = api_client.delete(f"/api/subscriptions/{sub_id}")
        assert_status(response, 200)

        # Verify gone from list
        response = api_client.get("/api/subscriptions")
        data = response.json()
        assert not any(s["id"] == sub_id for s in data)

    @pytest.mark.smoke
    def test_delete_subscription_nonexistent(self, api_client: TrinityApiClient):
        """DELETE /api/subscriptions/{id} for nonexistent returns 404."""
        response = api_client.delete(f"/api/subscriptions/{uuid.uuid4()}")
        assert_status(response, 404)


# =============================================================================
# Subscription Assignment Tests (Requires Agent)
# =============================================================================

class TestSubscriptionAssignment:
    """SUB-001: Subscription assignment to agents."""

    def test_assign_subscription_to_agent(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """PUT /api/subscriptions/agents/{name} assigns subscription."""
        # Create subscription
        sub_name = f"test-sub-assign-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            "/api/subscriptions",
            json={"name": sub_name, "credentials_json": VALID_CREDENTIALS}
        )
        assert_status(response, 200)
        sub_id = response.json()["id"]

        try:
            # Assign to agent
            response = api_client.put(
                f"/api/subscriptions/agents/{created_agent['name']}",
                params={"subscription_name": sub_name}
            )
            assert_status(response, 200)
            data = assert_json_response(response)
            assert data["success"] is True
            assert data["subscription_name"] == sub_name

            # Verify agent appears in subscription's agent list
            response = api_client.get("/api/subscriptions")
            subs = response.json()
            our_sub = next((s for s in subs if s["id"] == sub_id), None)
            assert created_agent["name"] in our_sub["agents"]

        finally:
            # Cleanup
            api_client.delete(f"/api/subscriptions/agents/{created_agent['name']}")
            api_client.delete(f"/api/subscriptions/{sub_id}")

    def test_assign_subscription_nonexistent(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """PUT /api/subscriptions/agents/{name} with nonexistent subscription returns 404."""
        response = api_client.put(
            f"/api/subscriptions/agents/{created_agent['name']}",
            params={"subscription_name": "nonexistent-sub-xyz"}
        )
        assert_status(response, 404)

    def test_assign_subscription_nonexistent_agent(
        self,
        api_client: TrinityApiClient
    ):
        """PUT /api/subscriptions/agents/{name} for nonexistent agent returns 400."""
        # Create subscription first
        sub_name = f"test-sub-noagent-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            "/api/subscriptions",
            json={"name": sub_name, "credentials_json": VALID_CREDENTIALS}
        )
        sub_id = response.json()["id"]

        try:
            response = api_client.put(
                "/api/subscriptions/agents/nonexistent-agent-xyz",
                params={"subscription_name": sub_name}
            )
            # Returns 400 because agent not in ownership table
            assert_status(response, 400)
            assert "not found" in response.json()["detail"].lower()
        finally:
            api_client.delete(f"/api/subscriptions/{sub_id}")

    def test_clear_agent_subscription(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """DELETE /api/subscriptions/agents/{name} clears assignment."""
        # Create and assign
        sub_name = f"test-sub-clear-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            "/api/subscriptions",
            json={"name": sub_name, "credentials_json": VALID_CREDENTIALS}
        )
        sub_id = response.json()["id"]

        api_client.put(
            f"/api/subscriptions/agents/{created_agent['name']}",
            params={"subscription_name": sub_name}
        )

        try:
            # Clear assignment
            response = api_client.delete(
                f"/api/subscriptions/agents/{created_agent['name']}"
            )
            assert_status(response, 200)

            # Verify cleared
            response = api_client.get(
                f"/api/subscriptions/agents/{created_agent['name']}/auth"
            )
            data = response.json()
            assert data["auth_mode"] != "subscription" or data["subscription_name"] is None

        finally:
            api_client.delete(f"/api/subscriptions/{sub_id}")


# =============================================================================
# Auth Status Tests
# =============================================================================

class TestAuthStatus:
    """SUB-001: Agent auth status detection."""

    def test_get_auth_status_no_subscription(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/subscriptions/agents/{name}/auth returns status without subscription."""
        # First clear any existing subscription
        api_client.delete(f"/api/subscriptions/agents/{created_agent['name']}")

        response = api_client.get(
            f"/api/subscriptions/agents/{created_agent['name']}/auth"
        )
        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, ["agent_name", "auth_mode", "has_api_key"])
        assert data["agent_name"] == created_agent["name"]
        # Without subscription, should be api_key or not_configured
        assert data["auth_mode"] in ["api_key", "not_configured"]

    def test_get_auth_status_with_subscription(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/subscriptions/agents/{name}/auth shows subscription when assigned."""
        # Create and assign subscription
        sub_name = f"test-sub-auth-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            "/api/subscriptions",
            json={"name": sub_name, "credentials_json": VALID_CREDENTIALS, "subscription_type": "max"}
        )
        sub_id = response.json()["id"]

        api_client.put(
            f"/api/subscriptions/agents/{created_agent['name']}",
            params={"subscription_name": sub_name}
        )

        try:
            response = api_client.get(
                f"/api/subscriptions/agents/{created_agent['name']}/auth"
            )
            assert_status(response, 200)
            data = assert_json_response(response)

            assert data["auth_mode"] == "subscription"
            assert data["subscription_name"] == sub_name
            assert data["subscription_id"] == sub_id

        finally:
            api_client.delete(f"/api/subscriptions/agents/{created_agent['name']}")
            api_client.delete(f"/api/subscriptions/{sub_id}")

    def test_get_auth_status_nonexistent_agent(
        self,
        api_client: TrinityApiClient
    ):
        """GET /api/subscriptions/agents/{name}/auth for nonexistent agent returns default status.

        Note: Currently returns 200 with api_key mode even for nonexistent agents.
        This could be improved to return 404.
        """
        response = api_client.get(
            "/api/subscriptions/agents/nonexistent-agent-xyz/auth"
        )
        # API returns 200 with default status for unknown agents
        # (could be improved to validate agent exists first)
        assert_status_in(response, [200, 404])
        if response.status_code == 200:
            data = response.json()
            assert data["auth_mode"] in ["api_key", "not_configured"]


# =============================================================================
# Auth Report Tests (SMOKE)
# =============================================================================

class TestAuthReport:
    """SUB-001: Fleet auth report endpoint."""

    @pytest.mark.smoke
    def test_get_auth_report(self, api_client: TrinityApiClient):
        """GET /api/ops/auth-report returns fleet auth status."""
        response = api_client.get("/api/ops/auth-report")
        assert_status(response, 200)
        data = assert_json_response(response)

        assert_has_fields(data, ["timestamp", "summary", "by_auth_mode", "subscriptions"])
        assert_has_fields(data["summary"], [
            "total_agents", "using_subscription", "using_api_key",
            "not_configured", "subscription_count"
        ])
        assert_has_fields(data["by_auth_mode"], ["subscription", "api_key", "not_configured"])

        # Counts should be non-negative
        assert data["summary"]["total_agents"] >= 0
        assert data["summary"]["using_subscription"] >= 0
        assert data["summary"]["using_api_key"] >= 0


# =============================================================================
# Credential Injection Tests
# =============================================================================

class TestCredentialInjection:
    """SUB-001: Subscription credential injection to running agents."""

    def test_injection_on_assignment(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Assigning subscription to running agent triggers injection."""
        # Create subscription
        sub_name = f"test-sub-inject-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            "/api/subscriptions",
            json={"name": sub_name, "credentials_json": VALID_CREDENTIALS}
        )
        sub_id = response.json()["id"]

        try:
            # Assign - should include injection result
            response = api_client.put(
                f"/api/subscriptions/agents/{created_agent['name']}",
                params={"subscription_name": sub_name}
            )
            assert_status(response, 200)
            data = assert_json_response(response)

            # Check injection result
            assert "injection_result" in data
            # For running agent, should succeed
            if data["injection_result"]:
                assert data["injection_result"]["status"] in ["success", "agent_not_running"]

        finally:
            api_client.delete(f"/api/subscriptions/agents/{created_agent['name']}")
            api_client.delete(f"/api/subscriptions/{sub_id}")


# =============================================================================
# Cascade Delete Tests
# =============================================================================

class TestSubscriptionCascade:
    """SUB-001: Subscription deletion cascades to agent assignments."""

    def test_delete_subscription_clears_agents(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Deleting subscription clears all agent assignments."""
        # Create and assign
        sub_name = f"test-sub-cascade-{uuid.uuid4().hex[:8]}"
        response = api_client.post(
            "/api/subscriptions",
            json={"name": sub_name, "credentials_json": VALID_CREDENTIALS}
        )
        sub_id = response.json()["id"]

        api_client.put(
            f"/api/subscriptions/agents/{created_agent['name']}",
            params={"subscription_name": sub_name}
        )

        # Verify assigned
        response = api_client.get(
            f"/api/subscriptions/agents/{created_agent['name']}/auth"
        )
        assert response.json()["auth_mode"] == "subscription"

        # Delete subscription
        api_client.delete(f"/api/subscriptions/{sub_id}")

        # Verify agent no longer has subscription
        response = api_client.get(
            f"/api/subscriptions/agents/{created_agent['name']}/auth"
        )
        data = response.json()
        assert data["auth_mode"] != "subscription" or data["subscription_id"] is None
