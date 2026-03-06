"""
Process Engine Domain Layer

Contains:
- Value Objects (value_objects.py)
- Aggregates (aggregates.py)
- Entities (entities.py)
- Step Configs (step_configs.py)
- Enums (enums.py)
- Domain Events (events.py)
- Domain Exceptions (exceptions.py)
"""

from .value_objects import (
    ProcessId,
    ExecutionId,
    StepId,
    Version,
    Duration,
    Money,
    TokenUsage,
    RetryPolicy,
    ErrorPolicy,
)

from .enums import (
    DefinitionStatus,
    StepType,
    ExecutionStatus,
    StepStatus,
    OnErrorAction,
    ApprovalStatus,
    AgentRole,
    # Access Control Enums (IT5 P1)
    ProcessPermission,
    ProcessRole,
    ROLE_PERMISSIONS,
    role_has_permission,
    get_role_permissions,
)

from .entities import (
    StepDefinition,
    StepExecution,
    OutputConfig,
    ApprovalRequest,
    StepRoles,
)

from .step_configs import (
    StepConfig,
    AgentTaskConfig,
    HumanApprovalConfig,
    GatewayConfig,
    TimerConfig,
    NotificationConfig,
    CompensationConfig,
    SubProcessConfig,
    parse_step_config,
    # Trigger configs
    TriggerConfig,
    ManualTriggerConfig,
    WebhookTriggerConfig,
    ScheduleTriggerConfig,
    parse_trigger_config,
    # Cron presets
    CRON_PRESETS,
    expand_cron_preset,
)

from .aggregates import (
    ProcessDefinition,
    ProcessExecution,
)

from .exceptions import (
    ProcessEngineError,
    ProcessDefinitionError,
    ProcessExecutionError,
    ProcessNotFoundError,
    ProcessValidationError,
    CircularDependencyError,
    InvalidStepReferenceError,
    DuplicateStepIdError,
    ExecutionNotFoundError,
    InvalidExecutionStateError,
)

from .events import (
    DomainEvent,
    ProcessStarted,
    ProcessCompleted,
    ProcessFailed,
    ProcessCancelled,
    StepStarted,
    StepCompleted,
    StepFailed,
    StepRetrying,
    StepSkipped,
    StepWaitingApproval,
    ApprovalRequested,
    ApprovalDecided,
    # Compensation Events
    CompensationStarted,
    CompensationCompleted,
    CompensationFailed,
    # Process Definition Events
    ProcessCreated,
    ProcessUpdated,
    ProcessPublished,
    ProcessArchived,
    # Informed Agent Events (EMI Pattern)
    InformedNotification,
    # Recovery Events
    ExecutionRecoveryStarted,
    ExecutionRecovered,
    ExecutionRecoveryFailed,
    ExecutionRecoveryCompleted,
)

__all__ = [
    # Value Objects
    "ProcessId",
    "ExecutionId",
    "StepId",
    "Version",
    "Duration",
    "Money",
    "TokenUsage",
    "RetryPolicy",
    "ErrorPolicy",
    # Enums
    "DefinitionStatus",
    "StepType",
    "ExecutionStatus",
    "StepStatus",
    "OnErrorAction",
    "ApprovalStatus",
    "AgentRole",
    # Access Control Enums (IT5 P1)
    "ProcessPermission",
    "ProcessRole",
    "ROLE_PERMISSIONS",
    "role_has_permission",
    "get_role_permissions",
    # Entities
    "StepDefinition",
    "StepExecution",
    "OutputConfig",
    "ApprovalRequest",
    "StepRoles",
    # Step Configs
    "StepConfig",
    "AgentTaskConfig",
    "HumanApprovalConfig",
    "GatewayConfig",
    "TimerConfig",
    "NotificationConfig",
    "CompensationConfig",
    "SubProcessConfig",
    "parse_step_config",
    # Trigger Configs
    "TriggerConfig",
    "WebhookTriggerConfig",
    "ScheduleTriggerConfig",
    "parse_trigger_config",
    # Cron presets
    "CRON_PRESETS",
    "expand_cron_preset",
    # Aggregates
    "ProcessDefinition",
    "ProcessExecution",
    # Exceptions
    "ProcessEngineError",
    "ProcessDefinitionError",
    "ProcessExecutionError",
    "ProcessNotFoundError",
    "ProcessValidationError",
    "CircularDependencyError",
    "InvalidStepReferenceError",
    "DuplicateStepIdError",
    "ExecutionNotFoundError",
    "InvalidExecutionStateError",
    # Domain Events
    "DomainEvent",
    "ProcessStarted",
    "ProcessCompleted",
    "ProcessFailed",
    "ProcessCancelled",
    "StepStarted",
    "StepCompleted",
    "StepFailed",
    "StepRetrying",
    "StepSkipped",
    "StepWaitingApproval",
    "ApprovalRequested",
    "ApprovalDecided",
    # Compensation Events
    "CompensationStarted",
    "CompensationCompleted",
    "CompensationFailed",
    # Process Definition Events
    "ProcessCreated",
    "ProcessUpdated",
    "ProcessPublished",
    "ProcessArchived",
    # Informed Agent Events (EMI Pattern)
    "InformedNotification",
    # Recovery Events
    "ExecutionRecoveryStarted",
    "ExecutionRecovered",
    "ExecutionRecoveryFailed",
    "ExecutionRecoveryCompleted",
]
