"""
Process Engine Repository Interfaces

Abstract base classes defining the repository contracts.

Reference: IT3 Section 7 (Repositories)
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..domain import (
    ProcessDefinition,
    ProcessExecution,
    ProcessId,
    ExecutionId,
    Version,
    DefinitionStatus,
    ExecutionStatus,
    DomainEvent,
)


class ProcessDefinitionRepository(ABC):
    """
    Repository interface for process definitions.
    
    Stores and retrieves process definitions. Definitions are identified
    by both their unique ID and by name+version combination.
    """

    @abstractmethod
    def save(self, definition: ProcessDefinition) -> None:
        """
        Save or update a process definition.
        
        If a definition with the same ID exists, it will be updated.
        Otherwise, a new definition is created.
        """
        ...

    @abstractmethod
    def get_by_id(self, id: ProcessId) -> Optional[ProcessDefinition]:
        """
        Get definition by its unique ID.
        
        Returns None if not found.
        """
        ...

    @abstractmethod
    def get_by_name(
        self,
        name: str,
        version: Optional[Version] = None
    ) -> Optional[ProcessDefinition]:
        """
        Get definition by name, optionally for a specific version.
        
        If version is not specified, returns the latest published version.
        Returns None if not found.
        """
        ...

    @abstractmethod
    def get_latest_version(self, name: str) -> Optional[ProcessDefinition]:
        """
        Get the latest published version of a process by name.
        
        Returns None if no published version exists.
        """
        ...

    @abstractmethod
    def list_all(
        self,
        status: Optional[DefinitionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProcessDefinition]:
        """
        List all definitions, optionally filtered by status.
        
        Results are ordered by updated_at descending.
        """
        ...

    @abstractmethod
    def list_by_name(self, name: str) -> list[ProcessDefinition]:
        """
        List all versions of a process by name.
        
        Returns all versions (draft, published, archived) ordered by version.
        """
        ...

    @abstractmethod
    def delete(self, id: ProcessId) -> bool:
        """
        Delete a process definition by ID.
        
        Returns True if deleted, False if not found.
        """
        ...

    @abstractmethod
    def exists(self, id: ProcessId) -> bool:
        """
        Check if a definition exists by ID.
        """
        ...

    @abstractmethod
    def count(self, status: Optional[DefinitionStatus] = None) -> int:
        """
        Count definitions, optionally filtered by status.
        """
        ...


class ProcessExecutionRepository(ABC):
    """
    Repository interface for process executions.
    
    Stores and retrieves execution state. Executions track the runtime
    state of a process instance.
    """

    @abstractmethod
    def save(self, execution: ProcessExecution) -> None:
        """
        Save or update execution state.
        
        Called after each state change (step start, step complete, etc.)
        """
        ...

    @abstractmethod
    def get_by_id(self, id: ExecutionId) -> Optional[ProcessExecution]:
        """
        Get execution by ID.
        
        Returns None if not found.
        """
        ...

    @abstractmethod
    def update(self, execution: ProcessExecution) -> None:
        """
        Update an existing execution.
        
        Same as save - uses upsert pattern.
        """
        ...

    @abstractmethod
    def delete(self, id: ExecutionId) -> bool:
        """
        Delete an execution by ID.
        
        Returns True if deleted, False if not found.
        """
        ...

    @abstractmethod
    def list_by_process(
        self,
        process_id: ProcessId,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProcessExecution]:
        """
        List executions for a specific process.
        
        Returns recent executions ordered by created_at descending.
        """
        ...

    @abstractmethod
    def list_active(self) -> list[ProcessExecution]:
        """
        List all active (running/pending/paused) executions.
        """
        ...

    @abstractmethod
    def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[ExecutionStatus] = None,
    ) -> list[ProcessExecution]:
        """
        List all executions with optional filtering.
        """
        ...

    @abstractmethod
    def count(self, status: Optional[ExecutionStatus] = None) -> int:
        """
        Count executions with optional status filter.
        """
        ...

    @abstractmethod
    def exists(self, id: ExecutionId) -> bool:
        """
        Check if an execution exists.
        """
        ...


class EventRepository(ABC):
    """
    Repository interface for domain events.
    
    Stores and retrieves domain events for audit logging and debugging.
    """
    
    @abstractmethod
    def save(self, event: DomainEvent) -> None:
        """
        Save a domain event.
        """
        ...
        
    @abstractmethod
    def get_by_execution_id(
        self,
        execution_id: ExecutionId,
        limit: int = 100,
        offset: int = 0
    ) -> list[DomainEvent]:
        """
        Get events for a specific execution.
        """
        ...
