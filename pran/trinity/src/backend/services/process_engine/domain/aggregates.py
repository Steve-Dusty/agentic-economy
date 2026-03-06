"""
Process Engine Domain Aggregates

Aggregates are clusters of entities and value objects that form
consistency boundaries. They are the main entry points for domain operations.

Reference: IT3 Section 4.1 (Aggregates)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Optional


def _utcnow() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)

from .enums import DefinitionStatus, ExecutionStatus, StepStatus
from .value_objects import ProcessId, ExecutionId, StepId, Version, Money, Duration
from .entities import StepDefinition, StepExecution, OutputConfig
from .step_configs import TriggerConfig, parse_trigger_config
from .exceptions import (
    CircularDependencyError,
    InvalidStepReferenceError,
    DuplicateStepIdError,
    InvalidExecutionStateError,
)


@dataclass
class ProcessDefinition:
    """
    Aggregate root for process definitions.

    A process definition describes a workflow - its steps, their order,
    and what output to produce. Once published, definitions are immutable;
    changes require creating a new version.

    Example YAML:
    ```yaml
    name: content-pipeline
    version: 1
    description: Generate and review content

    steps:
      - id: research
        name: Research Topic
        type: agent_task
        agent: research-agent
        message: Research the topic: {{input.topic}}

      - id: write
        name: Write Draft
        type: agent_task
        agent: writer-agent
        message: Write an article based on: {{steps.research.output}}
        depends_on: [research]

    outputs:
      - name: article
        source: "{{steps.write.output}}"
    ```
    """
    id: ProcessId
    name: str
    description: str
    version: Version
    status: DefinitionStatus

    # Composition
    steps: list[StepDefinition]
    outputs: list[OutputConfig] = field(default_factory=list)
    triggers: list[TriggerConfig] = field(default_factory=list)

    # Metadata
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        steps: Optional[list[StepDefinition]] = None,
        outputs: Optional[list[OutputConfig]] = None,
        triggers: Optional[list[TriggerConfig]] = None,
        created_by: Optional[str] = None,
    ) -> ProcessDefinition:
        """
        Factory method to create a new draft process definition.
        """
        return cls(
            id=ProcessId.generate(),
            name=name,
            description=description,
            version=Version.initial(),
            status=DefinitionStatus.DRAFT,
            steps=steps or [],
            outputs=outputs or [],
            triggers=triggers or [],
            created_by=created_by,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

    @classmethod
    def from_yaml_dict(cls, data: dict, created_by: Optional[str] = None) -> ProcessDefinition:
        """
        Create ProcessDefinition from parsed YAML dictionary.

        Args:
            data: Dictionary from YAML parsing
            created_by: User who created this definition

        Returns:
            New ProcessDefinition in draft status
        """
        # Parse steps
        steps = []
        for step_data in data.get("steps", []):
            steps.append(StepDefinition.from_dict(step_data))

        # Parse outputs
        outputs = []
        for output_data in data.get("outputs", []):
            outputs.append(OutputConfig.from_dict(output_data))

        # Parse triggers
        triggers = []
        for trigger_data in data.get("triggers", []):
            triggers.append(parse_trigger_config(trigger_data))

        # Parse version
        version_data = data.get("version", 1)
        if isinstance(version_data, int):
            version = Version(major=version_data)
        elif isinstance(version_data, str):
            version = Version.from_string(version_data)
        else:
            version = Version.initial()

        return cls(
            id=ProcessId.generate(),
            name=data["name"],
            description=data.get("description", ""),
            version=version,
            status=DefinitionStatus.DRAFT,
            steps=steps,
            outputs=outputs,
            triggers=triggers,
            created_by=created_by,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

    def to_yaml_dict(self) -> dict:
        """
        Convert to dictionary suitable for YAML serialization.
        """
        result = {
            "name": self.name,
            "version": str(self.version),
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
        }

        if self.outputs:
            result["outputs"] = [output.to_dict() for output in self.outputs]

        if self.triggers:
            result["triggers"] = [trigger.to_dict() for trigger in self.triggers]

        return result

    def to_dict(self) -> dict:
        """
        Convert to full dictionary for API/storage.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "version": str(self.version),
            "status": self.status.value,
            "steps": [step.to_dict() for step in self.steps],
            "outputs": [output.to_dict() for output in self.outputs],
            "triggers": [trigger.to_dict() for trigger in self.triggers],
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }

    # =========================================================================
    # Invariant Enforcement
    # =========================================================================

    def validate(self) -> list[str]:
        """
        Validate the process definition and return list of errors.
        Returns empty list if valid.
        """
        errors = []

        # Check for duplicate step IDs
        step_ids = set()
        for step in self.steps:
            if str(step.id) in step_ids:
                errors.append(f"Duplicate step ID: {step.id}")
            step_ids.add(str(step.id))

        # Check that all dependencies reference existing steps
        for step in self.steps:
            for dep in step.dependencies:
                if str(dep) not in step_ids:
                    errors.append(
                        f"Step '{step.id}' references non-existent step '{dep}'"
                    )

        # Check for circular dependencies
        try:
            self._detect_circular_dependencies()
        except CircularDependencyError as e:
            errors.append(str(e))

        # Check name is valid
        if not self.name or not self.name.strip():
            errors.append("Process name cannot be empty")

        # Check at least one step exists
        if not self.steps:
            errors.append("Process must have at least one step")

        return errors

    def _detect_circular_dependencies(self) -> None:
        """
        Detect circular dependencies in step graph.
        Raises CircularDependencyError if found.
        """
        # Build adjacency list
        graph: dict[str, list[str]] = {}
        for step in self.steps:
            graph[str(step.id)] = [str(dep) for dep in step.dependencies]

        # DFS-based cycle detection
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle - extract it
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    raise CircularDependencyError(cycle)

            path.pop()
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                dfs(node)

    def publish(self) -> ProcessDefinition:
        """
        Validate and publish the definition.
        Returns new instance with PUBLISHED status.

        Raises ProcessValidationError if validation fails.
        """
        from .exceptions import ProcessValidationError

        errors = self.validate()
        if errors:
            raise ProcessValidationError(errors)

        return replace(
            self,
            status=DefinitionStatus.PUBLISHED,
            published_at=_utcnow(),
            updated_at=_utcnow(),
        )

    def archive(self) -> ProcessDefinition:
        """
        Archive the definition.
        Returns new instance with ARCHIVED status.
        """
        return replace(
            self,
            status=DefinitionStatus.ARCHIVED,
            updated_at=_utcnow(),
        )

    def create_new_version(self) -> ProcessDefinition:
        """
        Create a new draft version based on this definition.
        Increments the major version number.
        """
        return replace(
            self,
            id=ProcessId.generate(),
            version=self.version.increment_major(),
            status=DefinitionStatus.DRAFT,
            published_at=None,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_entry_steps(self) -> list[StepId]:
        """
        Get steps with no dependencies - where execution starts.
        """
        return [step.id for step in self.steps if not step.dependencies]

    def get_dependent_steps(self, step_id: StepId) -> list[StepId]:
        """
        Get steps that depend on the given step.
        """
        return [
            step.id
            for step in self.steps
            if step_id in step.dependencies
        ]

    def get_step(self, step_id: StepId) -> Optional[StepDefinition]:
        """
        Get step by ID.
        """
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_step_by_id_str(self, step_id_str: str) -> Optional[StepDefinition]:
        """
        Get step by ID string.
        """
        for step in self.steps:
            if str(step.id) == step_id_str:
                return step
        return None


@dataclass
class ProcessExecution:
    """
    Aggregate root for process execution state.

    Tracks all runtime state for a single execution of a process.
    """
    id: ExecutionId
    process_id: ProcessId
    process_version: Version
    process_name: str  # Denormalized for display

    # State
    status: ExecutionStatus = ExecutionStatus.PENDING
    step_executions: dict[str, StepExecution] = field(default_factory=dict)

    # Context
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)

    # Tracking
    triggered_by: str = "manual"  # manual, schedule, api, event, retry, sub_process
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_of: Optional[ExecutionId] = None  # Original execution if this is a retry

    # Sub-process tracking (parent/child relationships)
    parent_execution_id: Optional[ExecutionId] = None  # Parent execution if this is a child
    parent_step_id: Optional[StepId] = None  # Step in parent that spawned this
    child_execution_ids: list[ExecutionId] = field(default_factory=list)  # Child executions

    # Observability
    total_cost: Money = field(default_factory=lambda: Money.zero())

    @classmethod
    def create(
        cls,
        definition: ProcessDefinition,
        triggered_by: str = "manual",
        input_data: Optional[dict[str, Any]] = None,
        retry_of: Optional[ExecutionId] = None,
        parent_execution_id: Optional[ExecutionId] = None,
        parent_step_id: Optional[StepId] = None,
    ) -> ProcessExecution:
        """
        Create a new execution for a process definition.

        Args:
            definition: The process definition to execute
            triggered_by: What triggered this execution (manual, schedule, api, retry, sub_process)
            input_data: Input data for the execution
            retry_of: If this is a retry, the ID of the original failed execution
            parent_execution_id: If this is a sub-process, the parent execution ID
            parent_step_id: If this is a sub-process, the parent step that spawned this
        """
        # Initialize step executions for all steps
        step_executions = {}
        for step in definition.steps:
            step_executions[str(step.id)] = StepExecution(step_id=step.id)

        return cls(
            id=ExecutionId.generate(),
            process_id=definition.id,
            process_version=definition.version,
            process_name=definition.name,
            status=ExecutionStatus.PENDING,
            step_executions=step_executions,
            input_data=input_data or {},
            triggered_by=triggered_by,
            retry_of=retry_of,
            parent_execution_id=parent_execution_id,
            parent_step_id=parent_step_id,
            child_execution_ids=[],
        )

    @property
    def duration(self) -> Optional[Duration]:
        """Calculate total execution duration if completed."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return Duration(seconds=int(delta.total_seconds()))
        return None

    # =========================================================================
    # State Transitions
    # =========================================================================

    def start(self) -> None:
        """Start the execution."""
        if self.status != ExecutionStatus.PENDING:
            raise InvalidExecutionStateError(self.status.value, "start")
        self.status = ExecutionStatus.RUNNING
        self.started_at = _utcnow()

    def complete(self, output_data: Optional[dict[str, Any]] = None) -> None:
        """Mark execution as completed."""
        if self.status != ExecutionStatus.RUNNING:
            raise InvalidExecutionStateError(self.status.value, "complete")
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = _utcnow()
        if output_data:
            self.output_data = output_data

    def fail(self, error_message: str) -> None:
        """Mark execution as failed."""
        if self.status not in (ExecutionStatus.RUNNING, ExecutionStatus.PENDING):
            raise InvalidExecutionStateError(self.status.value, "fail")
        self.status = ExecutionStatus.FAILED
        self.completed_at = _utcnow()
        self.output_data["error"] = error_message

    def cancel(self, reason: str = "Cancelled by user") -> None:
        """Cancel the execution."""
        if self.status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
            raise InvalidExecutionStateError(self.status.value, "cancel")
        self.status = ExecutionStatus.CANCELLED
        self.completed_at = _utcnow()
        self.output_data["cancelled_reason"] = reason

    def pause(self) -> None:
        """Pause the execution (e.g., waiting for approval)."""
        if self.status != ExecutionStatus.RUNNING:
            raise InvalidExecutionStateError(self.status.value, "pause")
        self.status = ExecutionStatus.PAUSED

    def resume(self) -> None:
        """Resume a paused execution."""
        if self.status != ExecutionStatus.PAUSED:
            raise InvalidExecutionStateError(self.status.value, "resume")
        self.status = ExecutionStatus.RUNNING

    # =========================================================================
    # Step Operations
    # =========================================================================

    def get_step_execution(self, step_id: StepId) -> Optional[StepExecution]:
        """Get execution state for a step."""
        return self.step_executions.get(str(step_id))

    def start_step(self, step_id: StepId) -> None:
        """Mark a step as started."""
        step_exec = self.step_executions.get(str(step_id))
        if step_exec:
            step_exec.start()

    def complete_step(self, step_id: StepId, output: dict[str, Any]) -> None:
        """Mark a step as completed with output."""
        step_exec = self.step_executions.get(str(step_id))
        if step_exec:
            step_exec.complete(output)

    def fail_step(self, step_id: StepId, error_message: str, error_code: Optional[str] = None) -> None:
        """Mark a step as failed (final)."""
        step_exec = self.step_executions.get(str(step_id))
        if step_exec:
            step_exec.fail(error_message, error_code)

    def record_step_attempt(self, step_id: StepId, error_message: str, error_code: Optional[str] = None) -> None:
        """Record a failed attempt for a step."""
        step_exec = self.step_executions.get(str(step_id))
        if step_exec:
            step_exec.record_attempt_failure(error_message, error_code)

    def add_cost(self, cost: Money) -> None:
        """Add cost from a step execution."""
        self.total_cost = self.total_cost + cost

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_completed_step_ids(self) -> list[str]:
        """Get IDs of completed steps."""
        return [
            step_id
            for step_id, step_exec in self.step_executions.items()
            if step_exec.status == StepStatus.COMPLETED
        ]

    def get_failed_step_ids(self) -> list[str]:
        """Get IDs of failed steps."""
        return [
            step_id
            for step_id, step_exec in self.step_executions.items()
            if step_exec.status == StepStatus.FAILED
        ]

    def get_pending_step_ids(self) -> list[str]:
        """Get IDs of pending steps."""
        return [
            step_id
            for step_id, step_exec in self.step_executions.items()
            if step_exec.status == StepStatus.PENDING
        ]

    def get_skipped_step_ids(self) -> list[str]:
        """Get IDs of skipped steps."""
        return [
            step_id
            for step_id, step_exec in self.step_executions.items()
            if step_exec.status == StepStatus.SKIPPED
        ]

    def all_steps_completed(self) -> bool:
        """Check if all steps are completed or skipped."""
        for step_exec in self.step_executions.values():
            if step_exec.status not in (StepStatus.COMPLETED, StepStatus.SKIPPED):
                return False
        return True

    def add_child_execution(self, child_id: ExecutionId) -> None:
        """Add a child execution ID to track sub-process calls."""
        if child_id not in self.child_execution_ids:
            self.child_execution_ids.append(child_id)

    def is_sub_process(self) -> bool:
        """Check if this execution is a sub-process (has a parent)."""
        return self.parent_execution_id is not None

    def has_children(self) -> bool:
        """Check if this execution has spawned child processes."""
        return len(self.child_execution_ids) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "id": str(self.id),
            "process_id": str(self.process_id),
            "process_version": str(self.process_version),
            "process_name": self.process_name,
            "status": self.status.value,
            "step_executions": {
                step_id: step_exec.to_dict()
                for step_id, step_exec in self.step_executions.items()
            },
            "input_data": self.input_data,
            "output_data": self.output_data,
            "triggered_by": self.triggered_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_cost": str(self.total_cost),
            "duration_seconds": self.duration.seconds if self.duration else None,
            "retry_of": str(self.retry_of) if self.retry_of else None,
        }

        # Sub-process tracking
        if self.parent_execution_id:
            result["parent_execution_id"] = str(self.parent_execution_id)
        if self.parent_step_id:
            result["parent_step_id"] = str(self.parent_step_id)
        if self.child_execution_ids:
            result["child_execution_ids"] = [str(cid) for cid in self.child_execution_ids]

        return result

    @classmethod
    def from_dict(cls, data: dict) -> ProcessExecution:
        """Create from dictionary (deserialization)."""
        # Parse parent/child relationships
        parent_execution_id = None
        if data.get("parent_execution_id"):
            parent_execution_id = ExecutionId(data["parent_execution_id"])

        parent_step_id = None
        if data.get("parent_step_id"):
            parent_step_id = StepId(data["parent_step_id"])

        child_execution_ids = []
        if data.get("child_execution_ids"):
            child_execution_ids = [ExecutionId(cid) for cid in data["child_execution_ids"]]

        execution = cls(
            id=ExecutionId(data["id"]),
            process_id=ProcessId(data["process_id"]),
            process_version=Version.from_string(data["process_version"]),
            process_name=data["process_name"],
            status=ExecutionStatus(data["status"]),
            input_data=data.get("input_data", {}),
            output_data=data.get("output_data", {}),
            triggered_by=data.get("triggered_by", "manual"),
            total_cost=Money.from_string(data.get("total_cost", "$0.00")),
            retry_of=ExecutionId(data["retry_of"]) if data.get("retry_of") else None,
            parent_execution_id=parent_execution_id,
            parent_step_id=parent_step_id,
            child_execution_ids=child_execution_ids,
        )

        # Parse step executions
        for step_id, step_data in data.get("step_executions", {}).items():
            execution.step_executions[step_id] = StepExecution.from_dict(step_data)

        # Parse timestamps
        if data.get("started_at"):
            execution.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            execution.completed_at = datetime.fromisoformat(data["completed_at"])

        return execution
