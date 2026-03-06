"""
Dependency Resolver

Determines execution order based on step dependencies.
Implements topological sorting for dependency resolution.
Supports parallel execution by identifying independent step groups.

Reference: IT3 Section 6 (Domain Services - DependencyResolver)
"""

from dataclasses import dataclass, field
from typing import Optional

from ..domain import (
    ProcessDefinition,
    ProcessExecution,
    StepDefinition,
    StepId,
    StepStatus,
)


@dataclass
class ParallelGroup:
    """
    A group of steps that can execute in parallel.
    
    Steps in the same group have no dependencies on each other
    and all their prerequisites have been satisfied.
    """
    level: int  # Execution level (0 = entry steps, 1 = depends on level 0, etc.)
    step_ids: list[StepId] = field(default_factory=list)
    
    @property
    def is_parallel(self) -> bool:
        """True if this group has multiple steps that can run in parallel."""
        return len(self.step_ids) > 1


@dataclass
class ParallelStructure:
    """
    Complete parallel execution structure for a process.
    
    Provides information for UI visualization of fork/join points.
    """
    groups: list[ParallelGroup] = field(default_factory=list)
    step_levels: dict[str, int] = field(default_factory=dict)  # step_id -> level
    
    def get_step_level(self, step_id: str) -> int:
        """Get the execution level for a step."""
        return self.step_levels.get(step_id, 0)
    
    def has_parallel_execution(self) -> bool:
        """True if any group has parallel steps."""
        return any(g.is_parallel for g in self.groups)


class DependencyResolver:
    """
    Resolves step execution order based on dependencies.
    
    Uses the step dependencies defined in the process definition
    to determine which steps are ready to execute.
    """
    
    def __init__(self, definition: ProcessDefinition):
        """
        Initialize resolver with a process definition.
        
        Args:
            definition: The process definition to resolve
        """
        self.definition = definition
        self._step_map = {str(step.id): step for step in definition.steps}
    
    def get_ready_steps(self, execution: ProcessExecution) -> list[StepId]:
        """
        Get steps that are ready to execute.
        
        A step is ready when:
        1. It has not started yet (PENDING status)
        2. All its dependencies are COMPLETED or SKIPPED
        
        Args:
            execution: Current execution state
            
        Returns:
            List of step IDs ready to execute
        """
        ready = []
        
        # Get both completed and skipped steps as satisfied dependencies
        satisfied_steps = set(execution.get_completed_step_ids())
        satisfied_steps.update(execution.get_skipped_step_ids())
        
        for step in self.definition.steps:
            step_exec = execution.step_executions.get(str(step.id))
            
            # Skip if not pending
            if step_exec is None or step_exec.status != StepStatus.PENDING:
                continue
            
            # Check if all dependencies are completed or skipped
            deps_satisfied = all(
                str(dep) in satisfied_steps
                for dep in step.dependencies
            )
            
            if deps_satisfied:
                ready.append(step.id)
        
        return ready
    
    def get_next_step(self, execution: ProcessExecution) -> Optional[StepId]:
        """
        Get the next step to execute (for sequential execution).
        
        Returns the first ready step, or None if no steps are ready.
        
        Args:
            execution: Current execution state
            
        Returns:
            Next step ID to execute, or None
        """
        ready = self.get_ready_steps(execution)
        return ready[0] if ready else None
    
    def get_execution_order(self) -> list[StepId]:
        """
        Get the full execution order using topological sort.
        
        Returns steps in an order that respects all dependencies.
        
        Returns:
            List of step IDs in execution order
        """
        # Build in-degree map
        in_degree = {str(step.id): 0 for step in self.definition.steps}
        for step in self.definition.steps:
            for dep in step.dependencies:
                # Count how many steps depend on each step
                pass
            in_degree[str(step.id)] = len(step.dependencies)
        
        # Find steps with no dependencies (in-degree 0)
        queue = [
            step.id for step in self.definition.steps
            if in_degree[str(step.id)] == 0
        ]
        
        result = []
        while queue:
            # Take first step
            current = queue.pop(0)
            result.append(current)
            
            # Reduce in-degree for dependent steps
            for step in self.definition.steps:
                if current in step.dependencies:
                    in_degree[str(step.id)] -= 1
                    if in_degree[str(step.id)] == 0:
                        queue.append(step.id)
        
        return result
    
    def get_step_definition(self, step_id: StepId) -> Optional[StepDefinition]:
        """
        Get step definition by ID.
        
        Args:
            step_id: Step ID to look up
            
        Returns:
            StepDefinition or None if not found
        """
        return self._step_map.get(str(step_id))
    
    def is_complete(self, execution: ProcessExecution) -> bool:
        """
        Check if execution is complete.
        
        Returns True if all steps are completed or skipped.
        
        Args:
            execution: Current execution state
            
        Returns:
            True if all steps are done
        """
        return execution.all_steps_completed()
    
    def has_failed_steps(self, execution: ProcessExecution) -> bool:
        """
        Check if execution has any failed steps.
        
        Args:
            execution: Current execution state
            
        Returns:
            True if any step has failed
        """
        return len(execution.get_failed_step_ids()) > 0
    
    def get_parallel_structure(self) -> ParallelStructure:
        """
        Analyze the process definition to identify parallel execution groups.
        
        Groups steps by their "level" - steps at the same level can run
        in parallel because they don't depend on each other.
        
        Returns:
            ParallelStructure with groups and step levels
        """
        # Calculate level for each step (longest path from any entry step)
        step_levels: dict[str, int] = {}
        
        # Entry steps (no dependencies) are level 0
        for step in self.definition.steps:
            if not step.dependencies:
                step_levels[str(step.id)] = 0
        
        # Calculate levels for remaining steps
        # A step's level is max(dependency levels) + 1
        changed = True
        while changed:
            changed = False
            for step in self.definition.steps:
                step_id_str = str(step.id)
                if step_id_str in step_levels:
                    continue
                
                # Check if all dependencies have levels assigned
                dep_levels = []
                all_deps_resolved = True
                for dep in step.dependencies:
                    dep_str = str(dep)
                    if dep_str in step_levels:
                        dep_levels.append(step_levels[dep_str])
                    else:
                        all_deps_resolved = False
                        break
                
                if all_deps_resolved and dep_levels:
                    step_levels[step_id_str] = max(dep_levels) + 1
                    changed = True
        
        # Group steps by level
        level_groups: dict[int, list[StepId]] = {}
        for step in self.definition.steps:
            level = step_levels.get(str(step.id), 0)
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(step.id)
        
        # Create ParallelGroups
        groups = []
        for level in sorted(level_groups.keys()):
            groups.append(ParallelGroup(
                level=level,
                step_ids=level_groups[level],
            ))
        
        return ParallelStructure(
            groups=groups,
            step_levels=step_levels,
        )
    
    def get_running_steps(self, execution: ProcessExecution) -> list[StepId]:
        """
        Get steps that are currently running.
        
        Args:
            execution: Current execution state
            
        Returns:
            List of step IDs currently in RUNNING status
        """
        running = []
        for step in self.definition.steps:
            step_exec = execution.step_executions.get(str(step.id))
            if step_exec and step_exec.status == StepStatus.RUNNING:
                running.append(step.id)
        return running
    
    def get_waiting_steps(self, execution: ProcessExecution) -> list[StepId]:
        """
        Get steps that are waiting for approval.
        
        Args:
            execution: Current execution state
            
        Returns:
            List of step IDs currently in WAITING_APPROVAL status
        """
        waiting = []
        for step in self.definition.steps:
            step_exec = execution.step_executions.get(str(step.id))
            if step_exec and step_exec.status == StepStatus.WAITING_APPROVAL:
                waiting.append(step.id)
        return waiting
    
    def has_waiting_steps(self, execution: ProcessExecution) -> bool:
        """
        Check if execution has any steps waiting for approval.
        
        Args:
            execution: Current execution state
            
        Returns:
            True if any step is waiting for approval
        """
        return len(self.get_waiting_steps(execution)) > 0
