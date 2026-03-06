"""
Sub-Process Step Handler

Executes sub_process steps by calling another process as a child execution.
This enables composable, reusable workflows.

Reference: BACKLOG_ADVANCED.md - E10-01
Reference: IT2 Section 6.6 (Phase 6 - Sub-processes)
"""

import logging
from typing import Any, Callable, Optional, TYPE_CHECKING

from ...domain import (
    StepType,
    SubProcessConfig,
    ProcessDefinition,
    ProcessExecution,
    ExecutionId,
    Version,
    DefinitionStatus,
)
from ...repositories import ProcessDefinitionRepository
from ...services import ExpressionEvaluator, EvaluationContext
from ..step_handler import StepHandler, StepResult, StepContext, StepConfig

if TYPE_CHECKING:
    from ..execution_engine import ExecutionEngine


logger = logging.getLogger(__name__)


class SubProcessError(Exception):
    """Error during sub-process execution."""
    pass


class SubProcessHandler(StepHandler):
    """
    Handler for sub_process step type.

    Enables calling another process as a step within a parent process.
    The parent waits for the child to complete and receives its output.

    Key features:
    - Load child ProcessDefinition by name/version
    - Create child ProcessExecution with mapped inputs
    - Execute via ExecutionEngine (handles recursive execution)
    - Link parent/child executions for navigation
    - Return child output to parent
    - Aggregate child costs into parent total
    """

    def __init__(
        self,
        definition_repo: Optional[ProcessDefinitionRepository] = None,
        engine_factory: Optional[Callable[[], "ExecutionEngine"]] = None,
        expression_evaluator: Optional[ExpressionEvaluator] = None,
    ):
        """
        Initialize handler.

        Args:
            definition_repo: Repository for loading child process definitions
            engine_factory: Factory to get/create ExecutionEngine for child execution
            expression_evaluator: Optional expression evaluator for input mapping
        """
        self._definition_repo = definition_repo
        self._engine_factory = engine_factory
        self.expression_evaluator = expression_evaluator or ExpressionEvaluator()

    @property
    def step_type(self) -> StepType:
        return StepType.SUB_PROCESS

    def set_definition_repo(self, repo: ProcessDefinitionRepository) -> None:
        """Set the definition repository (for late binding)."""
        self._definition_repo = repo

    def set_engine_factory(self, factory: Callable[[], "ExecutionEngine"]) -> None:
        """Set the engine factory (for late binding to avoid circular deps)."""
        self._engine_factory = factory

    async def execute(
        self,
        context: StepContext,
        config: StepConfig,
    ) -> StepResult:
        """
        Execute a sub-process step.

        1. Load the child process definition
        2. Map input data from parent context
        3. Create and execute child execution
        4. Return child output to parent
        """
        if not isinstance(config, SubProcessConfig):
            return StepResult.fail(
                f"Invalid config type: {type(config).__name__}",
                error_code="INVALID_CONFIG",
            )

        if not self._definition_repo:
            return StepResult.fail(
                "SubProcessHandler not properly configured: missing definition repository",
                error_code="CONFIGURATION_ERROR",
            )

        if not self._engine_factory:
            return StepResult.fail(
                "SubProcessHandler not properly configured: missing engine factory",
                error_code="CONFIGURATION_ERROR",
            )

        process_name = config.process_name
        version_str = config.version

        logger.info(
            f"Executing sub-process step: process={process_name}, "
            f"version={version_str or 'latest'}, "
            f"parent_execution={context.execution.id}"
        )

        try:
            # 1. Load child process definition
            child_definition = self._load_child_definition(process_name, version_str)
            if not child_definition:
                return StepResult.fail(
                    f"Sub-process '{process_name}' not found or not published",
                    error_code="PROCESS_NOT_FOUND",
                )

            # 2. Map input data from parent context to child input
            child_input = self._map_input_data(config.input_mapping, context)

            logger.info(
                f"Sub-process '{process_name}' found (id={child_definition.id}), "
                f"mapped {len(child_input)} input fields"
            )

            # 3. Execute child process
            engine = self._engine_factory()

            # Create child execution with parent reference
            child_execution = await engine.start(
                definition=child_definition,
                input_data=child_input,
                triggered_by="sub_process",
                parent_execution_id=context.execution.id,
                parent_step_id=context.step_definition.id,
            )

            # 4. Check child execution result
            if child_execution.status.value == "completed":
                output = {
                    config.output_key: child_execution.output_data,
                    "child_execution_id": str(child_execution.id),
                    "child_process_name": child_definition.name,
                    "child_process_version": str(child_definition.version),
                    "child_duration_seconds": child_execution.duration.seconds if child_execution.duration else 0,
                    "child_cost": str(child_execution.total_cost),
                }

                logger.info(
                    f"Sub-process '{process_name}' completed successfully "
                    f"(child_execution={child_execution.id})"
                )

                return StepResult.ok(output)

            elif child_execution.status.value == "failed":
                error_msg = child_execution.output_data.get("error", "Unknown error")
                return StepResult.fail(
                    f"Sub-process '{process_name}' failed: {error_msg}",
                    error_code="SUB_PROCESS_FAILED",
                )

            elif child_execution.status.value == "paused":
                # Child is waiting for approval - propagate waiting state
                return StepResult.wait({
                    "child_execution_id": str(child_execution.id),
                    "child_process_name": child_definition.name,
                    "waiting_reason": "Child process waiting for approval",
                })

            else:
                return StepResult.fail(
                    f"Sub-process '{process_name}' ended in unexpected state: {child_execution.status.value}",
                    error_code="UNEXPECTED_STATE",
                )

        except SubProcessError as e:
            return StepResult.fail(str(e), error_code="SUB_PROCESS_ERROR")
        except Exception as e:
            logger.exception(f"Unexpected error executing sub-process '{process_name}'")
            return StepResult.fail(str(e), error_code="UNEXPECTED_ERROR")

    def _load_child_definition(
        self,
        process_name: str,
        version_str: Optional[str],
    ) -> Optional[ProcessDefinition]:
        """
        Load the child process definition.

        Args:
            process_name: Name of the process to load
            version_str: Optional version string (None = latest published)

        Returns:
            ProcessDefinition if found and published, None otherwise
        """
        if version_str:
            # Load specific version
            try:
                version = Version.from_string(version_str)
                definition = self._definition_repo.get_by_name(process_name, version)
            except ValueError:
                logger.warning(f"Invalid version string: {version_str}")
                return None
        else:
            # Load latest published version
            definition = self._definition_repo.get_latest_version(process_name)

        # Verify definition is published
        if definition and definition.status != DefinitionStatus.PUBLISHED:
            logger.warning(
                f"Process '{process_name}' found but not published "
                f"(status={definition.status.value})"
            )
            return None

        return definition

    def _map_input_data(
        self,
        input_mapping: dict[str, str],
        context: StepContext,
    ) -> dict[str, Any]:
        """
        Map parent context data to child input.

        Input mapping uses expressions like:
        - "{{input.topic}}" - Map from parent input
        - "{{steps.research.output.summary}}" - Map from previous step output

        Args:
            input_mapping: Dict of {child_key: expression}
            context: Parent step context

        Returns:
            Dictionary of mapped input data for child process
        """
        if not input_mapping:
            # If no mapping specified, pass parent input as-is
            return context.input_data.copy()

        child_input = {}
        eval_context = EvaluationContext(
            input_data=context.input_data,
            step_outputs=context.step_outputs,
            execution_id=str(context.execution.id),
            process_name=context.execution.process_name,
        )

        for child_key, expression in input_mapping.items():
            if isinstance(expression, str) and "{{" in expression:
                # Evaluate expression
                try:
                    value = self.expression_evaluator.evaluate(expression, eval_context)
                    child_input[child_key] = value
                except Exception as e:
                    logger.warning(
                        f"Failed to evaluate input mapping '{child_key}': {e}, "
                        f"using raw expression"
                    )
                    child_input[child_key] = expression
            else:
                # Literal value
                child_input[child_key] = expression

        return child_input
