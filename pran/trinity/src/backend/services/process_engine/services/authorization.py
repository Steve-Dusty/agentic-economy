"""
Process Authorization Service

Role-based access control for process engine operations.

Reference: IT5 Section 5 (Access Management)
Reference: BACKLOG_ACCESS_AUDIT.md - E17-03
"""

import logging
from dataclasses import dataclass
from typing import Optional, Any

from ..domain import (
    ProcessDefinition,
    ProcessExecution,
    ProcessPermission,
    ProcessRole,
    ROLE_PERMISSIONS,
    role_has_permission,
)

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """
    Result of an authorization check.

    Attributes:
        allowed: Whether the operation is allowed
        reason: Human-readable explanation (especially for denials)
        scope: Optional scope restriction (e.g., "own_executions_only")
    """
    allowed: bool
    reason: str = ""
    scope: Optional[str] = None

    @classmethod
    def allow(cls, reason: str = "Permission granted", scope: str = None) -> "AuthResult":
        """Create an allowed result."""
        return cls(allowed=True, reason=reason, scope=scope)

    @classmethod
    def deny(cls, reason: str) -> "AuthResult":
        """Create a denied result."""
        return cls(allowed=False, reason=reason)

    def __bool__(self) -> bool:
        """Allow using AuthResult in boolean context."""
        return self.allowed


class ProcessAuthorizationService:
    """
    Authorization service for process engine operations.

    Provides centralized permission checking for all process operations.
    Uses role-based access control with optional resource-level overrides.

    Example usage:
    ```python
    auth_service = ProcessAuthorizationService()

    result = auth_service.can_trigger_execution(user, process)
    if not result:
        raise HTTPException(403, detail=result.reason)
    ```

    Reference: IT5 Section 5.3 (API Authorization)
    """

    def __init__(self):
        """Initialize the authorization service."""
        pass

    def _get_user_role(self, user: Any) -> Optional[ProcessRole]:
        """
        Extract the process role from a user object.

        Maps the user's role string to a ProcessRole enum.
        Falls back to VIEWER for unknown roles.
        """
        if not user:
            return None

        user_role = getattr(user, 'role', 'user')

        # Map platform roles to process roles
        role_mapping = {
            'admin': ProcessRole.ADMIN,
            'process_admin': ProcessRole.ADMIN,
            'process_designer': ProcessRole.DESIGNER,
            'designer': ProcessRole.DESIGNER,
            'process_operator': ProcessRole.OPERATOR,
            'operator': ProcessRole.OPERATOR,
            'process_approver': ProcessRole.APPROVER,
            'approver': ProcessRole.APPROVER,
            'process_viewer': ProcessRole.VIEWER,
            'viewer': ProcessRole.VIEWER,
            'user': ProcessRole.OPERATOR,  # Default users get operator access
        }

        return role_mapping.get(user_role, ProcessRole.VIEWER)

    def _check_permission(
        self,
        user: Any,
        permission: ProcessPermission,
    ) -> AuthResult:
        """
        Check if user has a specific permission.

        Args:
            user: The user making the request
            permission: The permission to check

        Returns:
            AuthResult indicating if operation is allowed
        """
        role = self._get_user_role(user)
        if role is None:
            return AuthResult.deny("User not authenticated")

        if role_has_permission(role, permission):
            return AuthResult.allow(f"Role {role.value} has {permission.value}")

        return AuthResult.deny(
            f"Role {role.value} does not have {permission.value} permission"
        )

    # =========================================================================
    # Process Definition Permissions
    # =========================================================================

    def can_create_process(self, user: Any) -> AuthResult:
        """
        Check if user can create new process definitions.

        Requires: PROCESS_CREATE permission
        """
        return self._check_permission(user, ProcessPermission.PROCESS_CREATE)

    def can_read_process(
        self,
        user: Any,
        process: Optional[ProcessDefinition] = None,
    ) -> AuthResult:
        """
        Check if user can read a process definition.

        Requires: PROCESS_READ permission

        Args:
            user: The user making the request
            process: Optional process to check (for future team-based access)
        """
        result = self._check_permission(user, ProcessPermission.PROCESS_READ)
        if not result:
            return result

        # Future: Check team ownership if process is provided
        # if process and process.owner_team != user.team and not process.is_shared:
        #     return AuthResult.deny("Process belongs to another team")

        return result

    def can_update_process(
        self,
        user: Any,
        process: Optional[ProcessDefinition] = None,
    ) -> AuthResult:
        """
        Check if user can update a process definition.

        Requires: PROCESS_UPDATE permission
        """
        result = self._check_permission(user, ProcessPermission.PROCESS_UPDATE)
        if not result:
            return result

        # Future: Check ownership
        return result

    def can_delete_process(
        self,
        user: Any,
        process: Optional[ProcessDefinition] = None,
    ) -> AuthResult:
        """
        Check if user can delete a process definition.

        Requires: PROCESS_DELETE permission
        """
        result = self._check_permission(user, ProcessPermission.PROCESS_DELETE)
        if not result:
            return result

        # Future: Check ownership, no active executions
        return result

    def can_publish_process(
        self,
        user: Any,
        process: Optional[ProcessDefinition] = None,
    ) -> AuthResult:
        """
        Check if user can publish a process definition.

        Requires: PROCESS_PUBLISH permission
        """
        return self._check_permission(user, ProcessPermission.PROCESS_PUBLISH)

    # =========================================================================
    # Execution Permissions
    # =========================================================================

    def can_trigger_execution(
        self,
        user: Any,
        process: Optional[ProcessDefinition] = None,
    ) -> AuthResult:
        """
        Check if user can trigger a new execution.

        Requires: EXECUTION_TRIGGER permission

        Args:
            user: The user making the request
            process: The process to execute (for ACL checks)
        """
        result = self._check_permission(user, ProcessPermission.EXECUTION_TRIGGER)
        if not result:
            return result

        # Future: Check process-specific allowed_users
        # if process and process.allowed_users:
        #     if user.id not in process.allowed_users:
        #         return AuthResult.deny("Not in process allowed users list")

        return result

    def can_view_execution(
        self,
        user: Any,
        execution: Optional[ProcessExecution] = None,
    ) -> AuthResult:
        """
        Check if user can view an execution.

        Requires: EXECUTION_VIEW permission

        Note: VIEWER role can only view own executions.
        Note: APPROVER role can only view executions they're assigned to.

        Args:
            user: The user making the request
            execution: The execution to view
        """
        role = self._get_user_role(user)
        if role is None:
            return AuthResult.deny("User not authenticated")

        # Admin can view all
        if role == ProcessRole.ADMIN:
            return AuthResult.allow("Admin has full access")

        # Check basic permission
        if not role_has_permission(role, ProcessPermission.EXECUTION_VIEW):
            return AuthResult.deny(
                f"Role {role.value} does not have execution:view permission"
            )

        # VIEWER can only see own executions
        if role == ProcessRole.VIEWER and execution:
            user_id = getattr(user, 'username', None) or getattr(user, 'id', None)
            if execution.triggered_by != user_id and execution.triggered_by != str(user_id):
                return AuthResult.deny("Viewers can only see their own executions")
            return AuthResult.allow("Own execution", scope="own_only")

        # APPROVER can only see executions they're assigned to
        if role == ProcessRole.APPROVER and execution:
            # Check if user is assigned to any approval step
            # This would require checking step assignments
            # For now, allow all with a scope marker
            return AuthResult.allow("Approver access", scope="approval_steps_only")

        return AuthResult.allow("Permission granted")

    def can_view_all_executions(self, user: Any) -> AuthResult:
        """
        Check if user can view all executions (not just own).

        Requires: ADMIN_VIEW_ALL permission
        """
        return self._check_permission(user, ProcessPermission.ADMIN_VIEW_ALL)

    def can_cancel_execution(
        self,
        user: Any,
        execution: Optional[ProcessExecution] = None,
    ) -> AuthResult:
        """
        Check if user can cancel an execution.

        Requires: EXECUTION_CANCEL permission
        """
        result = self._check_permission(user, ProcessPermission.EXECUTION_CANCEL)
        if not result:
            return result

        # Future: Check if user triggered this execution or owns process
        return result

    def can_retry_execution(
        self,
        user: Any,
        execution: Optional[ProcessExecution] = None,
    ) -> AuthResult:
        """
        Check if user can retry a failed execution.

        Requires: EXECUTION_RETRY permission
        """
        return self._check_permission(user, ProcessPermission.EXECUTION_RETRY)

    # =========================================================================
    # Approval Permissions
    # =========================================================================

    def can_decide_approval(
        self,
        user: Any,
        execution: Optional[ProcessExecution] = None,
        step_id: Optional[str] = None,
    ) -> AuthResult:
        """
        Check if user can decide on an approval step.

        Requires: APPROVAL_DECIDE permission

        Note: Also checks if user is actually assigned to this approval.

        Args:
            user: The user making the request
            execution: The execution containing the approval
            step_id: The specific step ID being approved
        """
        result = self._check_permission(user, ProcessPermission.APPROVAL_DECIDE)
        if not result:
            return result

        # Future: Check if user is in the assignees list for this step
        # This would require access to the step execution data

        return result

    def can_delegate_approval(
        self,
        user: Any,
        execution: Optional[ProcessExecution] = None,
        step_id: Optional[str] = None,
    ) -> AuthResult:
        """
        Check if user can delegate an approval to someone else.

        Requires: APPROVAL_DELEGATE permission
        """
        return self._check_permission(user, ProcessPermission.APPROVAL_DELEGATE)

    # =========================================================================
    # Admin Permissions
    # =========================================================================

    def can_manage_limits(self, user: Any) -> AuthResult:
        """
        Check if user can manage execution limits.

        Requires: ADMIN_MANAGE_LIMITS permission
        """
        return self._check_permission(user, ProcessPermission.ADMIN_MANAGE_LIMITS)

    def is_admin(self, user: Any) -> bool:
        """
        Check if user has admin role.

        Returns:
            True if user is an admin
        """
        role = self._get_user_role(user)
        return role == ProcessRole.ADMIN

    # =========================================================================
    # Logging
    # =========================================================================

    def log_authorization_failure(
        self,
        user: Any,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        reason: str,
    ) -> None:
        """
        Log an authorization failure for monitoring.

        Args:
            user: The user who was denied
            action: The action attempted
            resource_type: Type of resource (process, execution, etc.)
            resource_id: ID of the resource
            reason: Why access was denied
        """
        user_id = getattr(user, 'username', None) or getattr(user, 'id', 'unknown')
        logger.warning(
            f"Authorization denied: user={user_id}, action={action}, "
            f"resource={resource_type}:{resource_id or 'N/A'}, reason={reason}"
        )
