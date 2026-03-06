"""
Step Handler Interface and Registry

Defines the interface for step execution handlers and provides
a registry for looking up handlers by step type.

Reference: IT3 Section 8 (Anti-Corruption Layers)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional, Type

from ..domain import (
    StepDefinition,
    StepExecution,
    ProcessExecution,
    StepType,
    StepConfig,
)


@dataclass
class StepResult:
    """
    Result of executing a step.
    
    Attributes:
        success: Whether the step completed successfully
        waiting: Whether the step is waiting for external input (e.g., approval)
        output: Output data from the step (if successful)
        error: Error message (if failed)
        error_code: Optional error code for categorization
    """
    success: bool
    waiting: bool = False
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    @classmethod
    def ok(cls, output: dict[str, Any]) -> "StepResult":
        """Create a successful result."""
        return cls(success=True, output=output)
    
    @classmethod
    def fail(cls, error: str, error_code: Optional[str] = None) -> "StepResult":
        """Create a failed result."""
        return cls(success=False, error=error, error_code=error_code)
    
    @classmethod
    def wait(cls, output: Optional[dict[str, Any]] = None) -> "StepResult":
        """Create a waiting result (step paused for external input)."""
        return cls(success=False, waiting=True, output=output)


@dataclass
class StepContext:
    """
    Context passed to step handlers.
    
    Provides access to execution state and previous step outputs.
    """
    execution: ProcessExecution
    step_definition: StepDefinition
    step_outputs: dict[str, Any]  # step_id → output
    input_data: dict[str, Any]  # Process input data
    
    def get_step_output(self, step_id: str) -> Optional[Any]:
        """Get output from a previous step."""
        return self.step_outputs.get(step_id)


class StepHandler(ABC):
    """
    Abstract base class for step handlers.
    
    Each step type (agent_task, human_approval, etc.) has its own
    handler implementation.
    """
    
    @property
    @abstractmethod
    def step_type(self) -> StepType:
        """The step type this handler processes."""
        ...
    
    @abstractmethod
    async def execute(
        self,
        context: StepContext,
        config: StepConfig,
    ) -> StepResult:
        """
        Execute the step.
        
        Args:
            context: Execution context with state and outputs
            config: Step-specific configuration
            
        Returns:
            StepResult indicating success/failure and output
        """
        ...
    
    def can_handle(self, step_definition: StepDefinition) -> bool:
        """Check if this handler can process the given step."""
        return step_definition.type == self.step_type


class StepHandlerRegistry:
    """
    Registry for step handlers.
    
    Allows registering handlers for different step types and
    looking them up at runtime.
    """
    
    def __init__(self):
        self._handlers: dict[StepType, StepHandler] = {}
    
    def register(self, handler: StepHandler) -> None:
        """
        Register a handler for a step type.
        
        Args:
            handler: The handler to register
        """
        self._handlers[handler.step_type] = handler
    
    def get(self, step_type: StepType) -> Optional[StepHandler]:
        """
        Get handler for a step type.
        
        Args:
            step_type: The step type to look up
            
        Returns:
            The handler, or None if not registered
        """
        return self._handlers.get(step_type)
    
    def get_for_step(self, step: StepDefinition) -> Optional[StepHandler]:
        """
        Get handler for a step definition.
        
        Args:
            step: The step definition
            
        Returns:
            The handler, or None if not registered
        """
        return self.get(step.type)
    
    def has_handler(self, step_type: StepType) -> bool:
        """Check if a handler is registered for the step type."""
        return step_type in self._handlers
    
    @property
    def registered_types(self) -> list[StepType]:
        """Get list of registered step types."""
        return list(self._handlers.keys())


# Default registry instance
_default_registry = StepHandlerRegistry()


def get_default_registry() -> StepHandlerRegistry:
    """Get the default step handler registry."""
    return _default_registry


def register_handler(handler: StepHandler) -> None:
    """Register a handler in the default registry."""
    _default_registry.register(handler)
