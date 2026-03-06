"""
Execution Limit Service

Provides concurrency limits for process executions.

Reference: IT5 Section 1.4 (Execution Limits)
Reference: BACKLOG_ACCESS_AUDIT.md - E19-01
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..domain import ProcessId, ExecutionStatus
from ..repositories import ProcessExecutionRepository

logger = logging.getLogger(__name__)


@dataclass
class LimitConfig:
    """
    Configuration for execution limits.

    Attributes:
        max_concurrent_executions: Maximum concurrent executions globally
        max_instances_per_process: Maximum concurrent executions per process
    """
    max_concurrent_executions: int = 50
    max_instances_per_process: int = 3


@dataclass
class LimitResult:
    """
    Result of a limit check.

    Attributes:
        allowed: Whether the execution can proceed
        reason: Explanation if not allowed
        current_count: Current count that was checked
        limit: The limit that was checked against
    """
    allowed: bool
    reason: str = ""
    current_count: int = 0
    limit: int = 0

    @classmethod
    def allow(cls, current_count: int = 0, limit: int = 0) -> "LimitResult":
        """Create an allowed result."""
        return cls(
            allowed=True,
            reason="Within limits",
            current_count=current_count,
            limit=limit,
        )

    @classmethod
    def deny(cls, reason: str, current_count: int, limit: int) -> "LimitResult":
        """Create a denied result."""
        return cls(
            allowed=False,
            reason=reason,
            current_count=current_count,
            limit=limit,
        )

    def __bool__(self) -> bool:
        """Allow using LimitResult in boolean context."""
        return self.allowed


class ExecutionLimitService:
    """
    Service for checking and enforcing execution limits.

    Prevents runaway processes from exhausting resources by limiting:
    - Total concurrent executions globally
    - Concurrent executions per process

    Example usage:
    ```python
    limit_service = ExecutionLimitService(execution_repo)

    result = limit_service.check_can_start(process_id)
    if not result:
        raise HTTPException(429, detail=result.reason)
    ```

    Reference: IT5 Section 1.4
    """

    def __init__(
        self,
        execution_repo: ProcessExecutionRepository,
        config: Optional[LimitConfig] = None,
    ):
        """
        Initialize the limit service.

        Args:
            execution_repo: Repository for querying executions
            config: Limit configuration (uses defaults if not provided)
        """
        self.execution_repo = execution_repo
        self.config = config or LimitConfig()

        # Per-process limit overrides (process_id -> max_instances)
        self._process_overrides: dict[str, int] = {}

    def check_can_start(
        self,
        process_id: ProcessId,
        process_max_instances: Optional[int] = None,
    ) -> LimitResult:
        """
        Check if a new execution can be started for a process.

        Checks both global and per-process limits.

        Args:
            process_id: The process to start an execution for
            process_max_instances: Optional per-process limit override

        Returns:
            LimitResult indicating if execution can proceed
        """
        # Check global limit
        global_count = self.get_global_running_count()
        if global_count >= self.config.max_concurrent_executions:
            return LimitResult.deny(
                reason=f"Global execution limit reached ({global_count}/{self.config.max_concurrent_executions})",
                current_count=global_count,
                limit=self.config.max_concurrent_executions,
            )

        # Determine per-process limit
        process_limit = self._get_process_limit(process_id, process_max_instances)

        # Check per-process limit
        process_count = self.get_running_count(process_id)
        if process_count >= process_limit:
            return LimitResult.deny(
                reason=f"Process execution limit reached ({process_count}/{process_limit})",
                current_count=process_count,
                limit=process_limit,
            )

        return LimitResult.allow(
            current_count=process_count,
            limit=process_limit,
        )

    def get_running_count(self, process_id: ProcessId) -> int:
        """
        Get the number of running executions for a process.

        Args:
            process_id: The process to check

        Returns:
            Number of running executions
        """
        # Get all running/pending executions for this process
        executions = self.execution_repo.list_by_process(
            process_id,
            limit=1000,  # Should be enough for any practical scenario
            offset=0,
        )

        active_statuses = {
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.PAUSED,
        }

        return sum(1 for e in executions if e.status in active_statuses)

    def get_global_running_count(self) -> int:
        """
        Get the total number of running executions globally.

        Returns:
            Total number of active executions
        """
        # Count executions in active states
        count = 0
        for status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING, ExecutionStatus.PAUSED]:
            count += self.execution_repo.count(status=status)
        return count

    def set_process_limit(self, process_id: ProcessId, max_instances: int) -> None:
        """
        Set a custom limit for a specific process.

        Args:
            process_id: The process to set limit for
            max_instances: Maximum concurrent executions
        """
        self._process_overrides[str(process_id)] = max_instances
        logger.info(f"Set execution limit for {process_id}: {max_instances}")

    def remove_process_limit(self, process_id: ProcessId) -> None:
        """
        Remove a custom limit for a process (revert to default).

        Args:
            process_id: The process to remove limit for
        """
        if str(process_id) in self._process_overrides:
            del self._process_overrides[str(process_id)]
            logger.info(f"Removed custom execution limit for {process_id}")

    def get_limits_status(self) -> dict:
        """
        Get current limits status for monitoring.

        Returns:
            Dict with current usage and limits
        """
        return {
            "global": {
                "current": self.get_global_running_count(),
                "limit": self.config.max_concurrent_executions,
            },
            "per_process_default": self.config.max_instances_per_process,
            "process_overrides": dict(self._process_overrides),
        }

    def _get_process_limit(
        self,
        process_id: ProcessId,
        override: Optional[int],
    ) -> int:
        """Get the effective limit for a process."""
        # Priority: explicit override > stored override > default
        if override is not None:
            return override

        if str(process_id) in self._process_overrides:
            return self._process_overrides[str(process_id)]

        return self.config.max_instances_per_process
