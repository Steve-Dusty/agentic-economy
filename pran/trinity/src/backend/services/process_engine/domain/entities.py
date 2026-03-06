"""
Process Engine Domain Entities

Entities are objects with identity that exist within aggregates.

Reference: IT3 Section 4.2 (Entities)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _utcnow() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)

from .enums import StepType, StepStatus, OnErrorAction, ApprovalStatus, AgentRole
from .value_objects import StepId, Duration, Money, TokenUsage, RetryPolicy, ErrorPolicy
from .step_configs import (
    StepConfig,
    AgentTaskConfig,
    HumanApprovalConfig,
    GatewayConfig,
    NotificationConfig,
    CompensationConfig,
    SubProcessConfig,
    parse_step_config,
)


@dataclass
class StepRoles:
    """
    EMI role assignments for a process step.

    Reference: IT1 Section - EMI Pattern (Executor/Monitor/Informed)

    - Executor: The agent that performs the work (exactly one per step)
    - Monitor: Agents that own the outcome and can intervene
    - Informed: Agents that receive events for learning/awareness
    """
    executor: str  # Required - agent name that performs the work
    monitors: list[str] = field(default_factory=list)  # Agents that can intervene
    informed: list[str] = field(default_factory=list)  # Agents that receive notifications

    @classmethod
    def from_dict(cls, data: dict) -> "StepRoles":
        """Create from dictionary (YAML parsing)."""
        return cls(
            executor=data.get("executor", ""),
            monitors=data.get("monitors", []),
            informed=data.get("informed", []),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {"executor": self.executor}
        if self.monitors:
            result["monitors"] = self.monitors
        if self.informed:
            result["informed"] = self.informed
        return result

    def all_agents(self) -> list[str]:
        """Return all agents involved in this step (executor + monitors + informed)."""
        agents = [self.executor] if self.executor else []
        agents.extend(self.monitors)
        agents.extend(self.informed)
        return agents


@dataclass
class StepDefinition:
    """
    Entity within ProcessDefinition aggregate.

    Defines a single step in a process - what it does,
    what it depends on, and how it's configured.

    Compensation:
        Optional rollback action executed when process fails
        after this step has completed. Compensations run in
        reverse order of step completion.
    """
    id: StepId
    name: str
    type: StepType
    config: StepConfig
    dependencies: list[StepId] = field(default_factory=list)
    condition: Optional[str] = None  # Expression like "{{steps.review.decision}} == 'approved'"
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy.default)
    error_policy: ErrorPolicy = field(default_factory=ErrorPolicy.default)
    compensation: Optional[CompensationConfig] = None  # Compensation action (rollback)
    roles: Optional[StepRoles] = None  # EMI role assignments (executor/monitor/informed)

    @classmethod
    def from_dict(cls, data: dict) -> StepDefinition:
        """
        Create StepDefinition from dictionary (YAML parsing).

        Example YAML:
        ```yaml
        - id: research
          name: Research Topic
          type: agent_task
          agent: research-agent
          message: Research the following topic: {{input.topic}}
          timeout: 5m
          retry:
            max_attempts: 5
            initial_delay: 10s
          on_error: skip_step
        ```
        """
        step_id = StepId(data["id"])
        step_type = StepType(data["type"])

        # Parse config based on step type
        # For agent_task, the config is inlined in the step definition
        if step_type == StepType.AGENT_TASK:
            config_data = {
                "agent": data["agent"],
                "message": data["message"],
                "timeout": data.get("timeout", "5m"),
                "model": data.get("model"),
                "temperature": data.get("temperature"),
            }
        elif step_type == StepType.HUMAN_APPROVAL:
            config_data = {
                "title": data.get("title", data.get("name", "Approval Required")),
                "description": data.get("description", ""),
                "assignees": data.get("assignees", []),
                "timeout": data.get("timeout", "24h"),
            }
        elif step_type == StepType.GATEWAY:
            config_data = {
                "gateway_type": data.get("gateway_type", "exclusive"),
                "routes": data.get("routes", []),
                "default_route": data.get("default_route"),
            }
        elif step_type == StepType.NOTIFICATION:
            config_data = {
                "channel": data.get("channel", "slack"),
                "message": data.get("message", ""),
                "webhook_url": data.get("webhook_url"),
                "recipients": data.get("recipients", []),
                "subject": data.get("subject", ""),
                "url": data.get("url"),
            }
        elif step_type == StepType.SUB_PROCESS:
            config_data = {
                "process_name": data["process_name"],
                "version": data.get("version"),
                "input_mapping": data.get("input_mapping", {}),
                "output_key": data.get("output_key", "result"),
                "wait_for_completion": data.get("wait_for_completion", True),
                "timeout": data.get("timeout", "1h"),
            }
        else:
            # Generic config extraction
            config_data = data.get("config", {})

        config = parse_step_config(step_type.value, config_data)

        # Parse dependencies
        depends_on = data.get("depends_on", [])
        if isinstance(depends_on, str):
            depends_on = [depends_on]
        dependencies = [StepId(dep) for dep in depends_on]

        # Parse policies
        retry_policy = RetryPolicy.from_dict(data.get("retry", {}))
        error_policy = ErrorPolicy.from_dict(data.get("on_error", {}))

        # Parse compensation (optional rollback action)
        compensation = None
        if data.get("compensation"):
            compensation = CompensationConfig.from_dict(data["compensation"])

        # Parse roles (EMI pattern)
        roles = None
        if data.get("roles"):
            roles = StepRoles.from_dict(data["roles"])

        return cls(
            id=step_id,
            name=data.get("name", data["id"]),
            type=step_type,
            config=config,
            dependencies=dependencies,
            condition=data.get("condition"),
            retry_policy=retry_policy,
            error_policy=error_policy,
            compensation=compensation,
            roles=roles,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "id": str(self.id),
            "name": self.name,
            "type": self.type.value,
        }

        # Inline config for known step types
        if self.type == StepType.AGENT_TASK and isinstance(self.config, AgentTaskConfig):
            result["agent"] = self.config.agent
            result["message"] = self.config.message
            result["timeout"] = str(self.config.timeout)
            if self.config.model:
                result["model"] = self.config.model
            if self.config.temperature is not None:
                result["temperature"] = self.config.temperature
        elif self.type == StepType.HUMAN_APPROVAL and isinstance(self.config, HumanApprovalConfig):
            result["title"] = self.config.title
            result["description"] = self.config.description
            result["assignees"] = self.config.assignees
            result["timeout"] = str(self.config.timeout)
        elif self.type == StepType.GATEWAY and isinstance(self.config, GatewayConfig):
            result["gateway_type"] = self.config.gateway_type
            result["routes"] = self.config.routes
            if self.config.default_route:
                result["default_route"] = self.config.default_route
        elif self.type == StepType.NOTIFICATION and isinstance(self.config, NotificationConfig):
            result["channel"] = self.config.channel
            result["message"] = self.config.message
            if self.config.webhook_url:
                result["webhook_url"] = self.config.webhook_url
            if self.config.recipients:
                result["recipients"] = self.config.recipients
            if self.config.subject:
                result["subject"] = self.config.subject
            if self.config.url:
                result["url"] = self.config.url
        elif self.type == StepType.SUB_PROCESS and isinstance(self.config, SubProcessConfig):
            result["process_name"] = self.config.process_name
            if self.config.version:
                result["version"] = self.config.version
            if self.config.input_mapping:
                result["input_mapping"] = self.config.input_mapping
            result["output_key"] = self.config.output_key
            result["wait_for_completion"] = self.config.wait_for_completion
            result["timeout"] = str(self.config.timeout)
        else:
            result["config"] = self.config.to_dict()

        if self.dependencies:
            result["depends_on"] = [str(dep) for dep in self.dependencies]

        if self.condition:
            result["condition"] = self.condition

        result["retry"] = self.retry_policy.to_dict()
        result["on_error"] = self.error_policy.to_dict()

        if self.compensation:
            result["compensation"] = self.compensation.to_dict()

        if self.roles:
            result["roles"] = self.roles.to_dict()

        return result


@dataclass
class StepExecution:
    """
    Entity within ProcessExecution aggregate.

    Tracks the runtime state of a single step execution.
    """
    step_id: StepId
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input: Optional[dict[str, Any]] = None
    output: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None
    cost: Optional["Money"] = None  # Cost incurred by this step
    token_usage: Optional["TokenUsage"] = None  # Token usage from LLM calls
    retry_count: int = 0

    @property
    def duration(self) -> Optional[Duration]:
        """Calculate execution duration if completed."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return Duration(seconds=int(delta.total_seconds()))
        return None

    def start(self) -> None:
        """Mark step as running."""
        self.status = StepStatus.RUNNING
        self.started_at = _utcnow()

    def complete(self, output: dict[str, Any]) -> None:
        """Mark step as completed with output."""
        self.status = StepStatus.COMPLETED
        self.completed_at = _utcnow()
        self.output = output

    def fail(self, error_message: str, error_code: Optional[str] = None) -> None:
        """Mark step as failed with error (final failure)."""
        self.status = StepStatus.FAILED
        self.completed_at = _utcnow()
        self.error = {
            "message": error_message,
            "code": error_code,
        }
        # retry_count is already incremented by record_attempt_failure

    def record_attempt_failure(self, error_message: str, error_code: Optional[str] = None) -> None:
        """Record a single failed attempt but keep status as RUNNING."""
        self.retry_count += 1
        self.error = {
            "message": error_message,
            "code": error_code,
            "attempt": self.retry_count,
            "failed_at": _utcnow().isoformat(),
        }

    def skip(self, reason: str = "Condition not met") -> None:
        """Mark step as skipped."""
        self.status = StepStatus.SKIPPED
        self.completed_at = _utcnow()
        self.output = {"skipped_reason": reason}

    def wait_for_approval(self) -> None:
        """Mark step as waiting for human approval."""
        self.status = StepStatus.WAITING_APPROVAL

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "step_id": str(self.step_id),
            "status": self.status.value,
            "retry_count": self.retry_count,
        }

        if self.started_at:
            result["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            result["completed_at"] = self.completed_at.isoformat()
        if self.input:
            result["input"] = self.input
        if self.output:
            result["output"] = self.output
        if self.error:
            result["error"] = self.error
        if self.cost:
            result["cost"] = str(self.cost)
        if self.token_usage:
            result["token_usage"] = self.token_usage.to_dict()
        if self.duration:
            result["duration_seconds"] = self.duration.seconds

        return result

    @classmethod
    def from_dict(cls, data: dict) -> StepExecution:
        """Create from dictionary (deserialization)."""
        # Parse cost if present
        cost = None
        if data.get("cost"):
            cost = Money.from_string(data["cost"])

        # Parse token_usage if present
        token_usage = None
        if data.get("token_usage"):
            token_usage = TokenUsage.from_dict(data["token_usage"])

        execution = cls(
            step_id=StepId(data["step_id"]),
            status=StepStatus(data["status"]),
            retry_count=data.get("retry_count", 0),
            input=data.get("input"),
            output=data.get("output"),
            error=data.get("error"),
            cost=cost,
            token_usage=token_usage,
        )

        if data.get("started_at"):
            execution.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            execution.completed_at = datetime.fromisoformat(data["completed_at"])

        return execution


@dataclass
class OutputConfig:
    """
    Configuration for process outputs.

    Defines what data should be captured as process output
    and where it should be stored.
    """
    name: str
    source: str  # Expression like "{{steps.final.response}}"
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> OutputConfig:
        """Create from dictionary (YAML parsing)."""
        if isinstance(data, str):
            # Simple format: just the source expression
            return cls(name="output", source=data)
        return cls(
            name=data.get("name", "output"),
            source=data["source"],
            description=data.get("description", ""),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "source": self.source,
            "description": self.description,
        }


@dataclass
class ApprovalRequest:
    """
    Entity for tracking human approval requests.

    Created when a human_approval step starts, tracks who can approve
    and the decision made.
    """
    id: str  # UUID
    execution_id: str  # ExecutionId as string
    step_id: str  # StepId as string
    title: str
    description: str
    assignees: list[str]  # Users who can approve
    status: ApprovalStatus = ApprovalStatus.PENDING
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    decision_comment: Optional[str] = None

    @classmethod
    def create(
        cls,
        execution_id: str,
        step_id: str,
        title: str,
        description: str,
        assignees: list[str],
        deadline: Optional[datetime] = None,
    ) -> "ApprovalRequest":
        """Create a new approval request."""
        import uuid
        return cls(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            step_id=step_id,
            title=title,
            description=description,
            assignees=assignees,
            deadline=deadline,
        )

    def approve(self, decided_by: str, comment: Optional[str] = None) -> None:
        """Mark this request as approved."""
        self.status = ApprovalStatus.APPROVED
        self.decided_at = _utcnow()
        self.decided_by = decided_by
        self.decision_comment = comment

    def reject(self, decided_by: str, comment: str) -> None:
        """Mark this request as rejected."""
        self.status = ApprovalStatus.REJECTED
        self.decided_at = _utcnow()
        self.decided_by = decided_by
        self.decision_comment = comment

    def expire(self) -> None:
        """Mark this request as expired."""
        self.status = ApprovalStatus.EXPIRED
        self.decided_at = _utcnow()

    def is_pending(self) -> bool:
        """Check if this request is still pending."""
        return self.status == ApprovalStatus.PENDING

    def can_be_decided_by(self, user: str) -> bool:
        """Check if the given user can decide on this request."""
        # If no assignees specified, anyone can approve
        if not self.assignees:
            return True
        return user in self.assignees

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "execution_id": self.execution_id,
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "assignees": self.assignees,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }
        if self.deadline:
            result["deadline"] = self.deadline.isoformat()
        if self.decided_at:
            result["decided_at"] = self.decided_at.isoformat()
        if self.decided_by:
            result["decided_by"] = self.decided_by
        if self.decision_comment:
            result["decision_comment"] = self.decision_comment
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ApprovalRequest":
        """Create from dictionary (deserialization)."""
        request = cls(
            id=data["id"],
            execution_id=data["execution_id"],
            step_id=data["step_id"],
            title=data["title"],
            description=data["description"],
            assignees=data.get("assignees", []),
            status=ApprovalStatus(data.get("status", "pending")),
        )
        if data.get("deadline"):
            request.deadline = datetime.fromisoformat(data["deadline"])
        if data.get("created_at"):
            request.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("decided_at"):
            request.decided_at = datetime.fromisoformat(data["decided_at"])
        request.decided_by = data.get("decided_by")
        request.decision_comment = data.get("decision_comment")
        return request
