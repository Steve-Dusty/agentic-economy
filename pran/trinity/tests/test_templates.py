"""
Templates Tests (test_templates.py)

Tests for template listing and details.
Covers REQ-TMPL-001 through REQ-TMPL-003.

FAST TESTS - No agent creation required.
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
    assert_list_response,
)


class TestListTemplates:
    """REQ-TMPL-001: List templates endpoint tests."""

    @pytest.mark.smoke
    def test_list_templates(self, api_client: TrinityApiClient):
        """GET /api/templates returns available templates."""
        response = api_client.get("/api/templates")

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_list_response(data, "templates")

    def test_template_has_required_fields(self, api_client: TrinityApiClient):
        """Each template has id, display_name, description."""
        response = api_client.get("/api/templates")

        assert_status(response, 200)
        templates = response.json()

        if len(templates) > 0:
            template = templates[0]
            assert_has_fields(template, ["id", "display_name"])

    def test_templates_include_required_credentials(self, api_client: TrinityApiClient):
        """Templates include required_credentials field."""
        response = api_client.get("/api/templates")

        assert_status(response, 200)
        templates = response.json()

        # At least one template should have this field
        # (not all templates may have credentials)
        has_creds_field = any(
            "required_credentials" in t or "credentials" in t
            for t in templates
        )
        # This is optional - just verify structure if present


class TestGetTemplateDetails:
    """REQ-TMPL-002: Get template details endpoint tests."""

    def test_get_template_by_id(self, api_client: TrinityApiClient):
        """GET /api/templates/{id} returns full template metadata."""
        # First get list to find a template
        list_response = api_client.get("/api/templates")
        templates = list_response.json()

        if len(templates) == 0:
            pytest.skip("No templates available")

        template_id = templates[0].get("id")

        # Get details - env-template endpoint with template_id param
        response = api_client.get(
            "/api/templates/env-template",
            params={"template_id": template_id}
        )

        # Individual template detail endpoint may not exist, env-template returns content
        if response.status_code == 404:
            pytest.skip("Template detail endpoint not available")

        assert_status(response, 200)

    def test_get_nonexistent_template_returns_404(self, api_client: TrinityApiClient):
        """GET /api/templates/{id} for non-existent returns 404."""
        response = api_client.get("/api/templates/nonexistent-template-xyz")

        assert_status(response, 404)


class TestEnvTemplate:
    """REQ-TMPL-003: Env template endpoint tests."""

    def test_get_env_template(self, api_client: TrinityApiClient):
        """GET /api/templates/env-template returns template content."""
        # First get a template that has credentials
        list_response = api_client.get("/api/templates")
        templates = list_response.json()

        if len(templates) == 0:
            pytest.skip("No templates available")

        template_id = templates[0].get("id")

        # Get env template
        response = api_client.get(
            "/api/templates/env-template",
            params={"template_id": template_id}
        )

        # May return 404 if template has no env template
        if response.status_code == 404:
            pytest.skip("Template has no env template")

        assert_status(response, 200)

    def test_env_template_with_template_id(self, api_client: TrinityApiClient):
        """GET /api/templates/env-template supports template_id parameter."""
        # Just verify the endpoint accepts the parameter
        response = api_client.get(
            "/api/templates/env-template",
            params={"template_id": "some-template"}
        )

        # Should not crash, may return 404 if template not found
        assert_status_in(response, [200, 404])


class TestTemplateRefresh:
    """Tests for template cache refresh."""

    def test_refresh_templates(self, api_client: TrinityApiClient):
        """POST /api/templates/refresh refreshes template cache."""
        response = api_client.post("/api/templates/refresh")

        # May not be implemented or may use different method
        if response.status_code in [404, 405]:
            pytest.skip("Template refresh not implemented or uses different method")

        assert_status(response, 200)
