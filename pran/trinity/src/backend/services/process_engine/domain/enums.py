"""
Process Engine Enumerations

Defines the status and type enums used throughout the process engine.
"""

from enum import Enum


class DefinitionStatus(str, Enum):
    """Status of a process definition."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StepType(str, Enum):
    """Types of steps in a process."""
    AGENT_TASK = "agent_task"
    HUMAN_APPROVAL = "human_approval"  # Stub for Core phase
    GATEWAY = "gateway"  # Stub for Core phase
    TIMER = "timer"  # Stub for Advanced phase
    NOTIFICATION = "notification"  # Stub for Advanced phase
    SUB_PROCESS = "sub_process"  # Advanced phase - call other processes


class ExecutionStatus(str, Enum):
    """Status of a process execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Status of a step execution."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class OnErrorAction(str, Enum):
    """Action to take when a step fails after all retries."""
    FAIL_PROCESS = "fail_process"
    SKIP_STEP = "skip_step"
    GOTO_STEP = "goto_step"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AgentRole(str, Enum):
    """
    Role that an agent plays in a process step.

    EMI Pattern from IT1:
    - Executor: The agent that performs the work (exactly one per step)
    - Monitor: Agent that owns the outcome and can intervene (zero or more)
    - Informed: Agent that receives events for learning/awareness (zero or more)
    """
    EXECUTOR = "executor"
    MONITOR = "monitor"
    INFORMED = "informed"


# =============================================================================
# Access Control Enums (IT5 P1)
# =============================================================================


class ProcessPermission(str, Enum):
    """
    Permissions for process engine operations.

    Reference: IT5 Section 5.1 (Permission Model)
    Reference: BACKLOG_ACCESS_AUDIT.md - E17-01
    """
    # Definition permissions
    PROCESS_CREATE = "process:create"
    PROCESS_READ = "process:read"
    PROCESS_UPDATE = "process:update"
    PROCESS_DELETE = "process:delete"
    PROCESS_PUBLISH = "process:publish"

    # Execution permissions
    EXECUTION_TRIGGER = "execution:trigger"
    EXECUTION_VIEW = "execution:view"
    EXECUTION_CANCEL = "execution:cancel"
    EXECUTION_RETRY = "execution:retry"

    # Approval permissions
    APPROVAL_DECIDE = "approval:decide"
    APPROVAL_DELEGATE = "approval:delegate"

    # Admin permissions
    ADMIN_VIEW_ALL = "admin:view_all"
    ADMIN_MANAGE_LIMITS = "admin:manage_limits"


class ProcessRole(str, Enum):
    """
    Predefined roles for process engine access control.

    Each role has a set of associated permissions.

    Reference: IT5 Section 5.2 (Role Definitions)
    Reference: BACKLOG_ACCESS_AUDIT.md - E17-02

    Role descriptions:
    - DESIGNER: Can create, edit, and publish process definitions
    - OPERATOR: Can trigger and manage executions
    - VIEWER: Can view processes and own executions (read-only)
    - APPROVER: Can decide on approval steps
    - ADMIN: Full access to all operations
    """
    DESIGNER = "process_designer"
    OPERATOR = "process_operator"
    VIEWER = "process_viewer"
    APPROVER = "process_approver"
    ADMIN = "process_admin"


# Role to permission mappings
ROLE_PERMISSIONS: dict[ProcessRole, set[ProcessPermission]] = {
    ProcessRole.DESIGNER: {
        ProcessPermission.PROCESS_CREATE,
        ProcessPermission.PROCESS_READ,
        ProcessPermission.PROCESS_UPDATE,
        ProcessPermission.PROCESS_DELETE,
        ProcessPermission.PROCESS_PUBLISH,
        ProcessPermission.EXECUTION_VIEW,  # Can view executions of own processes
    },
    ProcessRole.OPERATOR: {
        ProcessPermission.PROCESS_READ,
        ProcessPermission.EXECUTION_TRIGGER,
        ProcessPermission.EXECUTION_VIEW,
        ProcessPermission.EXECUTION_CANCEL,
        ProcessPermission.EXECUTION_RETRY,
    },
    ProcessRole.VIEWER: {
        ProcessPermission.PROCESS_READ,
        ProcessPermission.EXECUTION_VIEW,  # Note: scoped to own executions
    },
    ProcessRole.APPROVER: {
        ProcessPermission.PROCESS_READ,
        ProcessPermission.EXECUTION_VIEW,  # Note: scoped to relevant steps
        ProcessPermission.APPROVAL_DECIDE,
    },
    ProcessRole.ADMIN: set(ProcessPermission),  # All permissions
}


def role_has_permission(role: ProcessRole, permission: ProcessPermission) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        role: The process role to check
        permission: The permission to check for

    Returns:
        True if the role has the permission, False otherwise
    """
    role_perms = ROLE_PERMISSIONS.get(role, set())
    return permission in role_perms


def get_role_permissions(role: ProcessRole) -> set[ProcessPermission]:
    """
    Get all permissions for a role.

    Args:
        role: The process role

    Returns:
        Set of permissions for the role
    """
    return ROLE_PERMISSIONS.get(role, set()).copy()
