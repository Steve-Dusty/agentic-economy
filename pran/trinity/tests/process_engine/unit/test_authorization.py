"""
Unit Tests for Process Authorization Service

Tests role-based access control for process operations.

Reference: BACKLOG_ACCESS_AUDIT.md - E17-03
"""

import pytest
from dataclasses import dataclass
from typing import Optional

import sys
import types
from pathlib import Path

# Add src/backend to path for direct imports
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_backend_path = str(_project_root / 'src' / 'backend')
_src_path = str(_project_root / 'src')

if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Prevent services/__init__.py from being loaded (it has heavy dependencies)
if 'services' not in sys.modules:
    sys.modules['services'] = types.ModuleType('services')
    sys.modules['services'].__path__ = [str(Path(_backend_path) / 'services')]

from services.process_engine.domain import (
    ProcessPermission,
    ProcessRole,
    ROLE_PERMISSIONS,
    role_has_permission,
    get_role_permissions,
)
from services.process_engine.services.authorization import (
    ProcessAuthorizationService,
    AuthResult,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@dataclass
class MockUser:
    """Mock user for testing."""
    id: int = 1
    username: str = "testuser"
    role: str = "user"
    email: Optional[str] = "test@example.com"


@pytest.fixture
def auth_service():
    """Create an authorization service for testing."""
    return ProcessAuthorizationService()


@pytest.fixture
def admin_user():
    """Admin user fixture."""
    return MockUser(id=1, username="admin", role="admin")


@pytest.fixture
def designer_user():
    """Designer user fixture."""
    return MockUser(id=2, username="designer", role="process_designer")


@pytest.fixture
def operator_user():
    """Operator user fixture."""
    return MockUser(id=3, username="operator", role="process_operator")


@pytest.fixture
def viewer_user():
    """Viewer user fixture."""
    return MockUser(id=4, username="viewer", role="process_viewer")


@pytest.fixture
def approver_user():
    """Approver user fixture."""
    return MockUser(id=5, username="approver", role="process_approver")


@pytest.fixture
def default_user():
    """Default user fixture (maps to operator)."""
    return MockUser(id=6, username="default", role="user")


# =============================================================================
# Tests: Permission Enum
# =============================================================================


class TestProcessPermission:
    """Tests for ProcessPermission enum."""

    def test_all_permissions_defined(self):
        """All expected permissions are defined."""
        expected = [
            "process:create", "process:read", "process:update",
            "process:delete", "process:publish",
            "execution:trigger", "execution:view",
            "execution:cancel", "execution:retry",
            "approval:decide", "approval:delegate",
            "admin:view_all", "admin:manage_limits",
        ]

        actual = [p.value for p in ProcessPermission]
        for perm in expected:
            assert perm in actual, f"Missing permission: {perm}"

    def test_permission_is_string(self):
        """Permissions are string enums."""
        assert ProcessPermission.PROCESS_CREATE.value == "process:create"
        assert ProcessPermission.PROCESS_READ.value == "process:read"


# =============================================================================
# Tests: Role Definitions
# =============================================================================


class TestProcessRole:
    """Tests for ProcessRole enum and role mappings."""

    def test_all_roles_defined(self):
        """All expected roles are defined."""
        roles = [r.value for r in ProcessRole]
        assert "process_designer" in roles
        assert "process_operator" in roles
        assert "process_viewer" in roles
        assert "process_approver" in roles
        assert "process_admin" in roles

    def test_designer_permissions(self):
        """Designer has correct permissions."""
        perms = ROLE_PERMISSIONS[ProcessRole.DESIGNER]

        assert ProcessPermission.PROCESS_CREATE in perms
        assert ProcessPermission.PROCESS_READ in perms
        assert ProcessPermission.PROCESS_UPDATE in perms
        assert ProcessPermission.PROCESS_DELETE in perms
        assert ProcessPermission.PROCESS_PUBLISH in perms
        assert ProcessPermission.EXECUTION_VIEW in perms

        # Should NOT have execution trigger
        assert ProcessPermission.EXECUTION_TRIGGER not in perms

    def test_operator_permissions(self):
        """Operator has correct permissions."""
        perms = ROLE_PERMISSIONS[ProcessRole.OPERATOR]

        assert ProcessPermission.PROCESS_READ in perms
        assert ProcessPermission.EXECUTION_TRIGGER in perms
        assert ProcessPermission.EXECUTION_VIEW in perms
        assert ProcessPermission.EXECUTION_CANCEL in perms
        assert ProcessPermission.EXECUTION_RETRY in perms

        # Should NOT have create/update/delete
        assert ProcessPermission.PROCESS_CREATE not in perms
        assert ProcessPermission.PROCESS_UPDATE not in perms
        assert ProcessPermission.PROCESS_DELETE not in perms

    def test_viewer_permissions(self):
        """Viewer has correct permissions."""
        perms = ROLE_PERMISSIONS[ProcessRole.VIEWER]

        assert ProcessPermission.PROCESS_READ in perms
        assert ProcessPermission.EXECUTION_VIEW in perms

        # Very limited - no trigger, cancel, etc.
        assert ProcessPermission.EXECUTION_TRIGGER not in perms
        assert ProcessPermission.EXECUTION_CANCEL not in perms

    def test_approver_permissions(self):
        """Approver has correct permissions."""
        perms = ROLE_PERMISSIONS[ProcessRole.APPROVER]

        assert ProcessPermission.PROCESS_READ in perms
        assert ProcessPermission.EXECUTION_VIEW in perms
        assert ProcessPermission.APPROVAL_DECIDE in perms

        # Should NOT have execution control
        assert ProcessPermission.EXECUTION_TRIGGER not in perms
        assert ProcessPermission.EXECUTION_CANCEL not in perms

    def test_admin_has_all_permissions(self):
        """Admin has all permissions."""
        admin_perms = ROLE_PERMISSIONS[ProcessRole.ADMIN]
        all_perms = set(ProcessPermission)

        assert admin_perms == all_perms

    def test_role_has_permission_helper(self):
        """role_has_permission helper works correctly."""
        assert role_has_permission(ProcessRole.ADMIN, ProcessPermission.PROCESS_CREATE) is True
        assert role_has_permission(ProcessRole.VIEWER, ProcessPermission.PROCESS_CREATE) is False
        assert role_has_permission(ProcessRole.OPERATOR, ProcessPermission.EXECUTION_TRIGGER) is True

    def test_get_role_permissions_returns_copy(self):
        """get_role_permissions returns a copy, not the original."""
        perms1 = get_role_permissions(ProcessRole.ADMIN)
        perms2 = get_role_permissions(ProcessRole.ADMIN)

        # Should be equal but not the same object
        assert perms1 == perms2
        assert perms1 is not perms2


# =============================================================================
# Tests: Authorization Service - Process Operations
# =============================================================================


class TestProcessAuthorizationService:
    """Tests for ProcessAuthorizationService."""

    def test_can_create_process_admin(self, auth_service, admin_user):
        """Admin can create processes."""
        result = auth_service.can_create_process(admin_user)
        assert result.allowed is True

    def test_can_create_process_designer(self, auth_service, designer_user):
        """Designer can create processes."""
        result = auth_service.can_create_process(designer_user)
        assert result.allowed is True

    def test_cannot_create_process_viewer(self, auth_service, viewer_user):
        """Viewer cannot create processes."""
        result = auth_service.can_create_process(viewer_user)
        assert result.allowed is False
        assert "permission" in result.reason.lower()

    def test_cannot_create_process_operator(self, auth_service, operator_user):
        """Operator cannot create processes."""
        result = auth_service.can_create_process(operator_user)
        assert result.allowed is False

    def test_can_read_process_all_roles(
        self, auth_service, admin_user, designer_user,
        operator_user, viewer_user, approver_user
    ):
        """All roles can read processes."""
        for user in [admin_user, designer_user, operator_user, viewer_user, approver_user]:
            result = auth_service.can_read_process(user)
            assert result.allowed is True, f"User {user.role} should be able to read"

    def test_can_update_process_designer(self, auth_service, designer_user):
        """Designer can update processes."""
        result = auth_service.can_update_process(designer_user)
        assert result.allowed is True

    def test_cannot_update_process_viewer(self, auth_service, viewer_user):
        """Viewer cannot update processes."""
        result = auth_service.can_update_process(viewer_user)
        assert result.allowed is False

    def test_can_delete_process_designer(self, auth_service, designer_user):
        """Designer can delete processes."""
        result = auth_service.can_delete_process(designer_user)
        assert result.allowed is True

    def test_cannot_delete_process_operator(self, auth_service, operator_user):
        """Operator cannot delete processes."""
        result = auth_service.can_delete_process(operator_user)
        assert result.allowed is False


# =============================================================================
# Tests: Authorization Service - Execution Operations
# =============================================================================


class TestExecutionAuthorization:
    """Tests for execution authorization."""

    def test_can_trigger_execution_operator(self, auth_service, operator_user):
        """Operator can trigger executions."""
        result = auth_service.can_trigger_execution(operator_user)
        assert result.allowed is True

    def test_can_trigger_execution_admin(self, auth_service, admin_user):
        """Admin can trigger executions."""
        result = auth_service.can_trigger_execution(admin_user)
        assert result.allowed is True

    def test_cannot_trigger_execution_viewer(self, auth_service, viewer_user):
        """Viewer cannot trigger executions."""
        result = auth_service.can_trigger_execution(viewer_user)
        assert result.allowed is False

    def test_cannot_trigger_execution_designer(self, auth_service, designer_user):
        """Designer cannot trigger executions (just design)."""
        result = auth_service.can_trigger_execution(designer_user)
        assert result.allowed is False

    def test_can_cancel_execution_operator(self, auth_service, operator_user):
        """Operator can cancel executions."""
        result = auth_service.can_cancel_execution(operator_user)
        assert result.allowed is True

    def test_cannot_cancel_execution_viewer(self, auth_service, viewer_user):
        """Viewer cannot cancel executions."""
        result = auth_service.can_cancel_execution(viewer_user)
        assert result.allowed is False

    def test_default_user_maps_to_operator(self, auth_service, default_user):
        """Default 'user' role maps to operator permissions."""
        result = auth_service.can_trigger_execution(default_user)
        assert result.allowed is True


# =============================================================================
# Tests: Authorization Service - Approval Operations
# =============================================================================


class TestApprovalAuthorization:
    """Tests for approval authorization."""

    def test_can_decide_approval_approver(self, auth_service, approver_user):
        """Approver can decide approvals."""
        result = auth_service.can_decide_approval(approver_user)
        assert result.allowed is True

    def test_can_decide_approval_admin(self, auth_service, admin_user):
        """Admin can decide approvals."""
        result = auth_service.can_decide_approval(admin_user)
        assert result.allowed is True

    def test_cannot_decide_approval_viewer(self, auth_service, viewer_user):
        """Viewer cannot decide approvals."""
        result = auth_service.can_decide_approval(viewer_user)
        assert result.allowed is False

    def test_cannot_decide_approval_operator(self, auth_service, operator_user):
        """Operator cannot decide approvals (unless also approver)."""
        result = auth_service.can_decide_approval(operator_user)
        assert result.allowed is False


# =============================================================================
# Tests: Authorization Service - Admin Operations
# =============================================================================


class TestAdminAuthorization:
    """Tests for admin authorization."""

    def test_can_view_all_admin(self, auth_service, admin_user):
        """Admin can view all executions."""
        result = auth_service.can_view_all_executions(admin_user)
        assert result.allowed is True

    def test_cannot_view_all_operator(self, auth_service, operator_user):
        """Operator cannot view all executions."""
        result = auth_service.can_view_all_executions(operator_user)
        assert result.allowed is False

    def test_can_manage_limits_admin(self, auth_service, admin_user):
        """Admin can manage limits."""
        result = auth_service.can_manage_limits(admin_user)
        assert result.allowed is True

    def test_is_admin_true(self, auth_service, admin_user):
        """is_admin returns True for admin."""
        assert auth_service.is_admin(admin_user) is True

    def test_is_admin_false(self, auth_service, operator_user):
        """is_admin returns False for non-admin."""
        assert auth_service.is_admin(operator_user) is False


# =============================================================================
# Tests: AuthResult
# =============================================================================


class TestAuthResult:
    """Tests for AuthResult dataclass."""

    def test_allow_creates_allowed_result(self):
        """AuthResult.allow creates allowed result."""
        result = AuthResult.allow("Test reason")
        assert result.allowed is True
        assert result.reason == "Test reason"

    def test_deny_creates_denied_result(self):
        """AuthResult.deny creates denied result."""
        result = AuthResult.deny("Access denied")
        assert result.allowed is False
        assert result.reason == "Access denied"

    def test_bool_conversion(self):
        """AuthResult can be used in boolean context."""
        allowed = AuthResult.allow()
        denied = AuthResult.deny("No")

        assert bool(allowed) is True
        assert bool(denied) is False

        # Can use in if statements
        if allowed:
            pass  # This should execute
        else:
            pytest.fail("Should be truthy")

        if denied:
            pytest.fail("Should be falsy")

    def test_scope_attribute(self):
        """AuthResult can have scope."""
        result = AuthResult.allow("Test", scope="own_only")
        assert result.scope == "own_only"


# =============================================================================
# Tests: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_none_user(self, auth_service):
        """None user is denied."""
        result = auth_service.can_create_process(None)
        assert result.allowed is False
        assert "not authenticated" in result.reason.lower()

    def test_unknown_role_defaults_to_viewer(self, auth_service):
        """Unknown role defaults to viewer permissions."""
        user = MockUser(role="unknown_role")

        # Viewer can read
        result = auth_service.can_read_process(user)
        assert result.allowed is True

        # But cannot create
        result = auth_service.can_create_process(user)
        assert result.allowed is False

    def test_role_mapping_variations(self, auth_service):
        """Various role string mappings work."""
        # Short form
        user1 = MockUser(role="admin")
        assert auth_service.is_admin(user1) is True

        # Long form
        user2 = MockUser(role="process_admin")
        assert auth_service.is_admin(user2) is True

        # Designer variations
        user3 = MockUser(role="designer")
        assert auth_service.can_create_process(user3).allowed is True
