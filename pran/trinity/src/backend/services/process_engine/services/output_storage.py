"""
Step Output Storage Service

Manages storage and retrieval of step execution outputs.
Provides a path-based API for accessing outputs.

Reference: BACKLOG_MVP.md - E2-06
"""

import json
import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from ..domain import ExecutionId, StepId

logger = logging.getLogger(__name__)


@dataclass
class OutputPath:
    """
    Represents a path to a step output.
    
    Pattern: /executions/{execution_id}/steps/{step_id}/output
    """
    execution_id: ExecutionId
    step_id: StepId
    
    def __str__(self) -> str:
        return f"/executions/{self.execution_id}/steps/{self.step_id}/output"
    
    @classmethod
    def from_string(cls, path: str) -> "OutputPath":
        """
        Parse an output path string.
        
        Example: /executions/abc-123/steps/step-a/output
        """
        parts = path.strip("/").split("/")
        if len(parts) != 5 or parts[0] != "executions" or parts[2] != "steps" or parts[4] != "output":
            raise ValueError(f"Invalid output path: {path}")
        
        return cls(
            execution_id=ExecutionId(parts[1]),
            step_id=StepId(parts[3]),
        )


class OutputStorage:
    """
    Service for managing step execution outputs.
    
    Outputs can be stored:
    - Small outputs (< threshold): In SQLite via ExecutionRepository
    - Large outputs (>= threshold): In filesystem (future)
    
    This service provides a unified interface regardless of storage backend.
    """
    
    # Threshold for small vs large outputs (64KB)
    SMALL_OUTPUT_THRESHOLD = 65536
    
    def __init__(
        self,
        execution_repo: "ProcessExecutionRepository",
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize output storage.
        
        Args:
            execution_repo: Repository for accessing executions
            storage_path: Base path for large file storage (optional, for future use)
        """
        self.execution_repo = execution_repo
        self.storage_path = storage_path or Path.home() / "trinity-data" / "outputs"
    
    def store(
        self,
        execution_id: ExecutionId,
        step_id: StepId,
        output: Any,
    ) -> OutputPath:
        """
        Store output for a step.
        
        The output is stored in the step's execution record.
        
        Args:
            execution_id: ID of the process execution
            step_id: ID of the step
            output: Output data (will be serialized to JSON)
            
        Returns:
            OutputPath pointing to the stored output
        """
        execution = self.execution_repo.get_by_id(execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")
        
        step_exec = execution.step_executions.get(str(step_id))
        if step_exec is None:
            raise ValueError(f"Step not found: {step_id}")
        
        # Check size for future large output handling
        output_json = json.dumps(output)
        if len(output_json) >= self.SMALL_OUTPUT_THRESHOLD:
            logger.warning(
                f"Large output ({len(output_json)} bytes) for step {step_id}. "
                "Consider file storage for large outputs in production."
            )
        
        # Store in the step execution
        step_exec.output = output
        self.execution_repo.save(execution)
        
        logger.debug(f"Stored output for {execution_id}/{step_id}")
        
        return OutputPath(execution_id=execution_id, step_id=step_id)
    
    def retrieve(
        self,
        execution_id: ExecutionId,
        step_id: StepId,
    ) -> Optional[Any]:
        """
        Retrieve output for a step.
        
        Args:
            execution_id: ID of the process execution
            step_id: ID of the step
            
        Returns:
            The stored output, or None if not found/empty
        """
        execution = self.execution_repo.get_by_id(execution_id)
        if execution is None:
            return None
        
        step_exec = execution.step_executions.get(str(step_id))
        if step_exec is None:
            return None
        
        # Treat empty dict as no output
        if step_exec.output is None or step_exec.output == {}:
            return None
        
        return step_exec.output
    
    def retrieve_by_path(self, path: Union[str, OutputPath]) -> Optional[Any]:
        """
        Retrieve output by path.
        
        Args:
            path: Output path string or OutputPath object
            
        Returns:
            The stored output, or None if not found
        """
        if isinstance(path, str):
            path = OutputPath.from_string(path)
        
        return self.retrieve(path.execution_id, path.step_id)
    
    def get_all_outputs(self, execution_id: ExecutionId) -> dict[str, Any]:
        """
        Get all step outputs for an execution.
        
        Returns:
            Dictionary mapping step_id → output (only non-empty outputs)
        """
        execution = self.execution_repo.get_by_id(execution_id)
        if execution is None:
            return {}
        
        outputs = {}
        for step_id, step_exec in execution.step_executions.items():
            # Only include non-empty outputs
            if step_exec.output is not None and step_exec.output != {}:
                outputs[step_id] = step_exec.output
        
        return outputs
    
    def exists(
        self,
        execution_id: ExecutionId,
        step_id: StepId,
    ) -> bool:
        """
        Check if output exists for a step.
        """
        output = self.retrieve(execution_id, step_id)
        return output is not None
    
    def delete(
        self,
        execution_id: ExecutionId,
        step_id: StepId,
    ) -> bool:
        """
        Delete output for a step.
        
        Returns:
            True if output was deleted, False if not found/empty
        """
        execution = self.execution_repo.get_by_id(execution_id)
        if execution is None:
            return False
        
        step_exec = execution.step_executions.get(str(step_id))
        if step_exec is None:
            return False
        
        # Check if there's actually an output to delete
        if step_exec.output is None or step_exec.output == {}:
            return False
        
        step_exec.output = None
        self.execution_repo.save(execution)
        
        logger.debug(f"Deleted output for {execution_id}/{step_id}")
        return True
    
    def clear_execution_outputs(self, execution_id: ExecutionId) -> int:
        """
        Clear all outputs for an execution.
        
        Returns:
            Number of outputs cleared
        """
        execution = self.execution_repo.get_by_id(execution_id)
        if execution is None:
            return 0
        
        count = 0
        for step_exec in execution.step_executions.values():
            if step_exec.output is not None and step_exec.output != {}:
                step_exec.output = None
                count += 1
        
        if count > 0:
            self.execution_repo.save(execution)
            logger.debug(f"Cleared {count} outputs for execution {execution_id}")
        
        return count


# Type hint for circular import avoidance
from ..repositories import ProcessExecutionRepository
