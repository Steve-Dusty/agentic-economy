"""
Process Validator Service

Validates process definitions at multiple levels:
1. YAML syntax validation
2. Schema validation (required fields, types)
3. Semantic validation (dependencies, references)
4. Agent existence checking (warnings)

Reference: IT3 Section 6 (Domain Services)
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from ..domain import (
    ProcessDefinition,
    StepType,
    ProcessValidationError,
    ScheduleTriggerConfig,
    CRON_PRESETS,
    expand_cron_preset,
)

# Try to import croniter for cron validation
try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


class ErrorLevel(str, Enum):
    """Severity level for validation errors."""
    ERROR = "error"  # Must fix before saving
    WARNING = "warning"  # Can proceed, but may cause issues


@dataclass
class ValidationError:
    """
    A single validation error or warning.

    Attributes:
        message: Human-readable error description
        level: ERROR or WARNING
        path: JSON path to error location (e.g., "steps[0].depends_on")
        line: Line number in YAML source (if available)
        suggestion: Optional fix suggestion
    """
    message: str
    level: ErrorLevel = ErrorLevel.ERROR
    path: Optional[str] = None
    line: Optional[int] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        result = {
            "message": self.message,
            "level": self.level.value,
        }
        if self.path:
            result["path"] = self.path
        if self.line:
            result["line"] = self.line
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


@dataclass
class ValidationResult:
    """
    Result of process validation.

    Contains lists of errors and warnings, and indicates if the
    definition is valid for saving/publishing.
    """
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    definition: Optional[ProcessDefinition] = None

    @property
    def is_valid(self) -> bool:
        """True if no errors (warnings are allowed)."""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """True if there are warnings."""
        return len(self.warnings) > 0

    def add_error(
        self,
        message: str,
        path: Optional[str] = None,
        line: Optional[int] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add an error to the result."""
        self.errors.append(ValidationError(
            message=message,
            level=ErrorLevel.ERROR,
            path=path,
            line=line,
            suggestion=suggestion,
        ))

    def add_warning(
        self,
        message: str,
        path: Optional[str] = None,
        line: Optional[int] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add a warning to the result."""
        self.warnings.append(ValidationError(
            message=message,
            level=ErrorLevel.WARNING,
            path=path,
            line=line,
            suggestion=suggestion,
        ))

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "is_valid": self.is_valid,
            "has_warnings": self.has_warnings,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


# Type for agent checker function
AgentChecker = Callable[[str], tuple[bool, bool]]  # Returns (exists, is_running)

# Type for process checker function (for sub_process validation)
ProcessChecker = Callable[[str, Optional[str]], bool]  # (process_name, version) -> exists_and_published


class ProcessValidator:
    """
    Validates process definitions.

    Performs multiple levels of validation:
    1. YAML parsing
    2. Schema validation
    3. Semantic validation
    4. Agent existence checking

    Usage:
        validator = ProcessValidator(agent_checker=check_agent_func)
        result = validator.validate_yaml(yaml_content)
        if result.is_valid:
            definition = result.definition
    """

    def __init__(
        self,
        agent_checker: Optional[AgentChecker] = None,
        process_checker: Optional[ProcessChecker] = None,
    ):
        """
        Initialize validator.

        Args:
            agent_checker: Optional function to check if agent exists/is running.
                          Signature: (agent_name: str) -> (exists: bool, is_running: bool)
            process_checker: Optional function to check if process exists and is published.
                            Signature: (process_name: str, version: str|None) -> bool
        """
        self.agent_checker = agent_checker
        self.process_checker = process_checker

    def validate_yaml(
        self,
        yaml_content: str,
        created_by: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate YAML content and return validation result.

        Args:
            yaml_content: Raw YAML string
            created_by: Optional user identifier

        Returns:
            ValidationResult with errors, warnings, and parsed definition
        """
        result = ValidationResult()

        # Step 1: Parse YAML
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            result.add_error(
                message=f"Invalid YAML syntax: {e}",
                line=getattr(e, 'problem_mark', None) and e.problem_mark.line + 1,
            )
            return result

        if not isinstance(data, dict):
            result.add_error(
                message="Process definition must be a YAML object/mapping",
                suggestion="Start with 'name: my-process'",
            )
            return result

        # Step 2: Schema validation (required fields)
        self._validate_schema(data, result)
        if not result.is_valid:
            return result

        # Step 3: Parse into ProcessDefinition
        try:
            definition = ProcessDefinition.from_yaml_dict(data, created_by=created_by)
            result.definition = definition
        except Exception as e:
            result.add_error(
                message=f"Failed to parse process definition: {e}",
            )
            return result

        # Step 4: Semantic validation (from domain)
        domain_errors = definition.validate()
        for error in domain_errors:
            result.add_error(message=error)

        # Step 5: Agent existence checking (warnings)
        if self.agent_checker and result.is_valid:
            self._check_agents(definition, result)

        # Step 6: Sub-process existence checking (warnings)
        if self.process_checker and result.is_valid:
            self._check_sub_processes(definition, result)

        # Step 7: Recursive sub-process detection
        if result.is_valid:
            self._check_recursive_sub_processes(definition, result)

        return result

    def validate_definition(
        self,
        definition: ProcessDefinition,
    ) -> ValidationResult:
        """
        Validate an existing ProcessDefinition object.

        Args:
            definition: ProcessDefinition to validate

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        result.definition = definition

        # Domain validation
        domain_errors = definition.validate()
        for error in domain_errors:
            result.add_error(message=error)

        # Agent checking
        if self.agent_checker and result.is_valid:
            self._check_agents(definition, result)

        # Sub-process existence checking
        if self.process_checker and result.is_valid:
            self._check_sub_processes(definition, result)

        # Recursive sub-process detection
        if result.is_valid:
            self._check_recursive_sub_processes(definition, result)

        return result

    def _validate_schema(self, data: dict, result: ValidationResult) -> None:
        """Validate schema (required fields and types)."""

        # Required: name
        if "name" not in data:
            result.add_error(
                message="Missing required field: 'name'",
                path="name",
                suggestion="Add 'name: my-process-name'",
            )
        elif not isinstance(data["name"], str):
            result.add_error(
                message="Field 'name' must be a string",
                path="name",
            )
        elif not data["name"].strip():
            result.add_error(
                message="Field 'name' cannot be empty",
                path="name",
            )

        # Required: steps
        if "steps" not in data:
            result.add_error(
                message="Missing required field: 'steps'",
                path="steps",
                suggestion="Add 'steps:' section with at least one step",
            )
        elif not isinstance(data["steps"], list):
            result.add_error(
                message="Field 'steps' must be a list",
                path="steps",
            )
        elif len(data["steps"]) == 0:
            result.add_error(
                message="Process must have at least one step",
                path="steps",
            )
        else:
            # Validate each step
            for i, step in enumerate(data["steps"]):
                self._validate_step_schema(step, i, result)

        # Optional: version
        if "version" in data:
            version = data["version"]
            if not isinstance(version, (int, str)):
                result.add_error(
                    message="Field 'version' must be a number or string",
                    path="version",
                )

        # Optional: outputs
        if "outputs" in data:
            if not isinstance(data["outputs"], list):
                result.add_error(
                    message="Field 'outputs' must be a list",
                    path="outputs",
                )

        # Optional: triggers
        if "triggers" in data:
            if not isinstance(data["triggers"], list):
                result.add_error(
                    message="Field 'triggers' must be a list",
                    path="triggers",
                )
            else:
                for i, trigger in enumerate(data["triggers"]):
                    self._validate_trigger_schema(trigger, i, result)

    def _validate_step_schema(
        self,
        step: Any,
        index: int,
        result: ValidationResult,
    ) -> None:
        """Validate individual step schema."""
        path_prefix = f"steps[{index}]"

        if not isinstance(step, dict):
            result.add_error(
                message=f"Step at index {index} must be an object",
                path=path_prefix,
            )
            return

        # Required: id
        if "id" not in step:
            result.add_error(
                message=f"Step at index {index} missing required field: 'id'",
                path=f"{path_prefix}.id",
            )

        # Required: type
        if "type" not in step:
            result.add_error(
                message=f"Step at index {index} missing required field: 'type'",
                path=f"{path_prefix}.type",
                suggestion="Add 'type: agent_task' or other valid type",
            )
        else:
            step_type = step["type"]
            valid_types = [t.value for t in StepType]
            if step_type not in valid_types:
                result.add_error(
                    message=f"Invalid step type '{step_type}'",
                    path=f"{path_prefix}.type",
                    suggestion=f"Valid types: {', '.join(valid_types)}",
                )

            # Type-specific validation
            if step_type == "agent_task":
                if "agent" not in step:
                    result.add_error(
                        message=f"agent_task step missing required field: 'agent'",
                        path=f"{path_prefix}.agent",
                    )
                if "message" not in step:
                    result.add_error(
                        message=f"agent_task step missing required field: 'message'",
                        path=f"{path_prefix}.message",
                    )
            elif step_type == "sub_process":
                if "process_name" not in step:
                    result.add_error(
                        message=f"sub_process step missing required field: 'process_name'",
                        path=f"{path_prefix}.process_name",
                        suggestion="Add 'process_name: my-child-process'",
                    )
                # Validate input_mapping if provided
                input_mapping = step.get("input_mapping")
                if input_mapping is not None and not isinstance(input_mapping, dict):
                    result.add_error(
                        message=f"sub_process 'input_mapping' must be an object",
                        path=f"{path_prefix}.input_mapping",
                    )

            # Validate roles if present (EMI pattern) - applies to all step types
            if "roles" in step:
                self._validate_step_roles(step, index, step_type, result)

    def _validate_step_roles(
        self,
        step: dict,
        index: int,
        step_type: str,
        result: ValidationResult,
    ) -> None:
        """Validate EMI roles for a step."""
        path_prefix = f"steps[{index}].roles"
        roles = step.get("roles", {})

        if not isinstance(roles, dict):
            result.add_error(
                message=f"Field 'roles' must be an object",
                path=path_prefix,
            )
            return

        # Executor is required if roles are specified
        executor = roles.get("executor")
        if not executor:
            result.add_error(
                message=f"Roles must include an 'executor' agent",
                path=f"{path_prefix}.executor",
                suggestion="Add 'executor: agent-name' to specify which agent executes this step",
            )
        elif not isinstance(executor, str):
            result.add_error(
                message=f"Field 'executor' must be a string (agent name)",
                path=f"{path_prefix}.executor",
            )
        else:
            # For agent_task, executor should match the step's agent field
            if step_type == "agent_task":
                step_agent = step.get("agent")
                if step_agent and executor != step_agent:
                    result.add_warning(
                        message=f"Role executor '{executor}' differs from step agent '{step_agent}'",
                        path=f"{path_prefix}.executor",
                        suggestion="For consistency, executor should match the step's agent field",
                    )

        # Validate monitors list
        monitors = roles.get("monitors", [])
        if not isinstance(monitors, list):
            result.add_error(
                message=f"Field 'monitors' must be a list of agent names",
                path=f"{path_prefix}.monitors",
            )
        else:
            for i, monitor in enumerate(monitors):
                if not isinstance(monitor, str):
                    result.add_error(
                        message=f"Monitor at index {i} must be a string (agent name)",
                        path=f"{path_prefix}.monitors[{i}]",
                    )
                elif executor and monitor == executor:
                    result.add_warning(
                        message=f"Agent '{monitor}' is both executor and monitor (redundant)",
                        path=f"{path_prefix}.monitors[{i}]",
                    )

        # Validate informed list
        informed = roles.get("informed", [])
        if not isinstance(informed, list):
            result.add_error(
                message=f"Field 'informed' must be a list of agent names",
                path=f"{path_prefix}.informed",
            )
        else:
            for i, agent in enumerate(informed):
                if not isinstance(agent, str):
                    result.add_error(
                        message=f"Informed agent at index {i} must be a string (agent name)",
                        path=f"{path_prefix}.informed[{i}]",
                    )
                elif executor and agent == executor:
                    result.add_warning(
                        message=f"Agent '{agent}' is both executor and informed (redundant)",
                        path=f"{path_prefix}.informed[{i}]",
                    )
                elif isinstance(monitors, list) and agent in monitors:
                    result.add_warning(
                        message=f"Agent '{agent}' is in both monitors and informed lists",
                        path=f"{path_prefix}.informed[{i}]",
                    )

    def _validate_trigger_schema(
        self,
        trigger: Any,
        index: int,
        result: ValidationResult,
    ) -> None:
        """Validate individual trigger schema."""
        path_prefix = f"triggers[{index}]"

        if not isinstance(trigger, dict):
            result.add_error(
                message=f"Trigger at index {index} must be an object",
                path=path_prefix,
            )
            return

        # Required: id
        if "id" not in trigger:
            result.add_error(
                message=f"Trigger at index {index} missing required field: 'id'",
                path=f"{path_prefix}.id",
            )

        # Required: type
        trigger_type = trigger.get("type", "webhook")
        valid_types = ["manual", "webhook", "schedule"]
        if trigger_type not in valid_types:
            result.add_error(
                message=f"Invalid trigger type '{trigger_type}'",
                path=f"{path_prefix}.type",
                suggestion=f"Valid types: {', '.join(valid_types)}",
            )

        # Schedule-specific validation
        if trigger_type == "schedule":
            self._validate_schedule_trigger(trigger, index, result)

    def _validate_schedule_trigger(
        self,
        trigger: dict,
        index: int,
        result: ValidationResult,
    ) -> None:
        """Validate schedule trigger configuration."""
        path_prefix = f"triggers[{index}]"

        # Required: cron
        cron = trigger.get("cron", "")
        if not cron:
            result.add_error(
                message=f"Schedule trigger missing required field: 'cron'",
                path=f"{path_prefix}.cron",
                suggestion=f"Add 'cron: daily' or a cron expression like '0 9 * * *'",
            )
            return

        # Validate cron expression
        cron_error = self._validate_cron_expression(cron)
        if cron_error:
            # Show available presets in suggestion
            presets = ", ".join(CRON_PRESETS.keys())
            result.add_error(
                message=cron_error,
                path=f"{path_prefix}.cron",
                suggestion=f"Use a preset ({presets}) or 5-field cron: 'minute hour day month day_of_week'",
            )

        # Validate timezone if provided
        timezone = trigger.get("timezone", "UTC")
        if timezone:
            try:
                import pytz
                pytz.timezone(timezone)
            except Exception:
                result.add_warning(
                    message=f"Unknown timezone '{timezone}', will use UTC",
                    path=f"{path_prefix}.timezone",
                )

    def _validate_cron_expression(self, cron: str) -> Optional[str]:
        """
        Validate a cron expression or preset.

        Args:
            cron: Cron expression or preset name

        Returns:
            Error message if invalid, None if valid
        """
        # Check if it's a valid preset
        if cron in CRON_PRESETS:
            return None

        # Expand preset and validate
        cron_expr = expand_cron_preset(cron)

        # Basic format check (5 fields)
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return f"Invalid cron expression '{cron}': expected 5 fields (minute hour day month day_of_week)"

        # Use croniter for detailed validation if available
        if CRONITER_AVAILABLE:
            try:
                from datetime import datetime
                croniter(cron_expr, datetime.now())
            except (ValueError, KeyError) as e:
                return f"Invalid cron expression '{cron}': {str(e)}"

        return None

    def _check_agents(
        self,
        definition: ProcessDefinition,
        result: ValidationResult,
    ) -> None:
        """Check if referenced agents exist and are running."""
        if not self.agent_checker:
            return

        for i, step in enumerate(definition.steps):
            # Check step's primary agent (for agent_task)
            if step.type == StepType.AGENT_TASK:
                agent_name = step.config.agent
                self._check_single_agent(agent_name, f"steps[{i}].agent", result)

            # Check agents in roles (EMI pattern)
            if step.roles:
                # Check executor
                if step.roles.executor:
                    self._check_single_agent(
                        step.roles.executor,
                        f"steps[{i}].roles.executor",
                        result,
                    )

                # Check monitors
                for j, monitor in enumerate(step.roles.monitors):
                    self._check_single_agent(
                        monitor,
                        f"steps[{i}].roles.monitors[{j}]",
                        result,
                    )

                # Check informed agents
                for j, informed in enumerate(step.roles.informed):
                    self._check_single_agent(
                        informed,
                        f"steps[{i}].roles.informed[{j}]",
                        result,
                    )

    def _check_single_agent(
        self,
        agent_name: str,
        path: str,
        result: ValidationResult,
    ) -> None:
        """Check if a single agent exists and is running."""
        if not self.agent_checker:
            return

        try:
            exists, is_running = self.agent_checker(agent_name)

            if not exists:
                result.add_warning(
                    message=f"Agent '{agent_name}' does not exist",
                    path=path,
                    suggestion=f"Create agent '{agent_name}' before running this process",
                )
            elif not is_running:
                result.add_warning(
                    message=f"Agent '{agent_name}' exists but is not running",
                    path=path,
                    suggestion=f"Start agent '{agent_name}' before running this process",
                )
        except Exception:
            # Don't fail validation if agent check fails
            result.add_warning(
                message=f"Could not verify agent '{agent_name}'",
                path=path,
            )

    def _check_sub_processes(
        self,
        definition: ProcessDefinition,
        result: ValidationResult,
    ) -> None:
        """Check if referenced sub-processes exist and are published."""
        if not self.process_checker:
            return

        for i, step in enumerate(definition.steps):
            if step.type == StepType.SUB_PROCESS:
                from ..domain import SubProcessConfig
                if isinstance(step.config, SubProcessConfig):
                    process_name = step.config.process_name
                    version = step.config.version
                    try:
                        exists = self.process_checker(process_name, version)
                        if not exists:
                            version_info = f" (version: {version})" if version else ""
                            result.add_warning(
                                message=f"Sub-process '{process_name}'{version_info} not found or not published",
                                path=f"steps[{i}].process_name",
                                suggestion=f"Ensure process '{process_name}' exists and is published",
                            )
                    except Exception:
                        result.add_warning(
                            message=f"Could not verify sub-process '{process_name}'",
                            path=f"steps[{i}].process_name",
                        )

    def _check_recursive_sub_processes(
        self,
        definition: ProcessDefinition,
        result: ValidationResult,
    ) -> None:
        """
        Check for direct self-referencing sub-processes.

        Note: This only detects direct self-recursion where a process calls itself.
        Detecting indirect recursion (A calls B which calls A) requires access to
        all process definitions and is deferred to runtime.
        """
        for i, step in enumerate(definition.steps):
            if step.type == StepType.SUB_PROCESS:
                from ..domain import SubProcessConfig
                if isinstance(step.config, SubProcessConfig):
                    process_name = step.config.process_name
                    # Check for direct self-recursion
                    if process_name == definition.name:
                        result.add_error(
                            message=f"Sub-process step references itself (recursive call to '{process_name}')",
                            path=f"steps[{i}].process_name",
                            suggestion="Sub-processes cannot call their parent process directly",
                        )
