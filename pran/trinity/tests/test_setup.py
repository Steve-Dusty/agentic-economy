"""
First-Time Setup Tests (test_setup.py)

Tests for Trinity first-time setup endpoints.
Covers REQ-SETUP-001: Admin password configuration and setup status.

Feature Flow: first-time-setup.md

FAST TESTS - No agent creation required.
These tests verify the setup endpoints WITHOUT modifying actual setup state
(since setup can only be done once on a fresh install).
"""

import pytest

# Mark all tests in this module as smoke tests (fast, no agent needed)
pytestmark = pytest.mark.smoke

from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
)


class TestSetupStatus:
    """Tests for GET /api/setup/status endpoint."""

    @pytest.mark.smoke
    def test_setup_status_accessible_without_auth(self, unauthenticated_client: TrinityApiClient):
        """GET /api/setup/status should be accessible without authentication."""
        response = unauthenticated_client.get("/api/setup/status", auth=False)
        assert_status(response, 200)

    @pytest.mark.smoke
    def test_setup_status_returns_valid_response(self, unauthenticated_client: TrinityApiClient):
        """GET /api/setup/status returns setup_completed field."""
        response = unauthenticated_client.get("/api/setup/status", auth=False)

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, ["setup_completed"])

    def test_setup_status_is_boolean(self, unauthenticated_client: TrinityApiClient):
        """setup_completed should be a boolean value."""
        response = unauthenticated_client.get("/api/setup/status", auth=False)

        assert_status(response, 200)
        data = response.json()
        assert isinstance(data["setup_completed"], bool)


class TestSetupAdminPassword:
    """Tests for POST /api/setup/admin-password endpoint.

    NOTE: These tests verify validation behavior WITHOUT actually
    completing setup (which would lock out the endpoint permanently).
    """

    def test_setup_blocked_after_completion(self, unauthenticated_client: TrinityApiClient):
        """POST /api/setup/admin-password returns 403 if setup already completed."""
        # First check if setup is completed
        status_response = unauthenticated_client.get("/api/setup/status", auth=False)
        status_data = status_response.json()

        if not status_data.get("setup_completed"):
            pytest.skip("Setup not completed - cannot test blocked state")

        # Try to set password again - should be blocked
        response = unauthenticated_client.post(
            "/api/setup/admin-password",
            json={
                "password": "newpassword123",
                "confirm_password": "newpassword123"
            },
            auth=False
        )

        assert_status(response, 403)
        data = response.json()
        assert "already completed" in data.get("detail", "").lower() or "setup" in data.get("detail", "").lower()

    def test_password_validation_short_password(self, unauthenticated_client: TrinityApiClient):
        """POST /api/setup/admin-password rejects passwords shorter than 8 characters."""
        # First check if setup is completed
        status_response = unauthenticated_client.get("/api/setup/status", auth=False)
        status_data = status_response.json()

        if status_data.get("setup_completed"):
            pytest.skip("Setup already completed - cannot test validation")

        # Try to set short password
        response = unauthenticated_client.post(
            "/api/setup/admin-password",
            json={
                "password": "short",
                "confirm_password": "short"
            },
            auth=False
        )

        # Should reject with 400
        assert_status(response, 400)
        data = response.json()
        assert "8 characters" in data.get("detail", "").lower() or "too short" in data.get("detail", "").lower()

    def test_password_validation_mismatch(self, unauthenticated_client: TrinityApiClient):
        """POST /api/setup/admin-password rejects mismatched passwords."""
        # First check if setup is completed
        status_response = unauthenticated_client.get("/api/setup/status", auth=False)
        status_data = status_response.json()

        if status_data.get("setup_completed"):
            pytest.skip("Setup already completed - cannot test validation")

        # Try to set mismatched passwords
        response = unauthenticated_client.post(
            "/api/setup/admin-password",
            json={
                "password": "validpassword123",
                "confirm_password": "differentpassword123"
            },
            auth=False
        )

        # Should reject with 400
        assert_status(response, 400)
        data = response.json()
        assert "match" in data.get("detail", "").lower() or "mismatch" in data.get("detail", "").lower()

    def test_password_validation_missing_fields(self, unauthenticated_client: TrinityApiClient):
        """POST /api/setup/admin-password rejects missing required fields."""
        # First check if setup is completed
        status_response = unauthenticated_client.get("/api/setup/status", auth=False)
        status_data = status_response.json()

        if status_data.get("setup_completed"):
            pytest.skip("Setup already completed - cannot test validation")

        # Try with empty body
        response = unauthenticated_client.post(
            "/api/setup/admin-password",
            json={},
            auth=False
        )

        # Should reject with 422 (validation error)
        assert_status_in(response, [400, 422])


class TestAuthModeSetupStatus:
    """Tests for setup_completed in /api/auth/mode response."""

    def test_auth_mode_includes_setup_status(self, unauthenticated_client: TrinityApiClient):
        """GET /api/auth/mode should include setup_completed field."""
        response = unauthenticated_client.get("/api/auth/mode", auth=False)

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, ["setup_completed"])
        assert isinstance(data["setup_completed"], bool)

    def test_auth_mode_setup_status_matches_setup_endpoint(self, unauthenticated_client: TrinityApiClient):
        """setup_completed in /api/auth/mode should match /api/setup/status."""
        # Get status from setup endpoint
        setup_response = unauthenticated_client.get("/api/setup/status", auth=False)
        setup_data = setup_response.json()

        # Get status from auth mode endpoint
        auth_response = unauthenticated_client.get("/api/auth/mode", auth=False)
        auth_data = auth_response.json()

        # They should match
        assert setup_data["setup_completed"] == auth_data["setup_completed"]


class TestLoginBlockedBeforeSetup:
    """Tests for login being blocked before setup completion."""

    def test_login_returns_setup_required_before_setup(self, unauthenticated_client: TrinityApiClient):
        """POST /token returns 403 with 'setup_required' if setup not completed."""
        # First check if setup is completed
        status_response = unauthenticated_client.get("/api/setup/status", auth=False)
        status_data = status_response.json()

        if status_data.get("setup_completed"):
            pytest.skip("Setup already completed - cannot test login block")

        # Try to login
        response = unauthenticated_client._client.post(
            "/token",
            data={
                "username": "admin",
                "password": "testpassword",
            },
        )

        assert_status(response, 403)
        data = response.json()
        assert data.get("detail") == "setup_required"
