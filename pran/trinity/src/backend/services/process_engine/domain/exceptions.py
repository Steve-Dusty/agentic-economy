"""
Process Engine Domain Exceptions

Custom exceptions for the process engine domain.
"""


class ProcessEngineError(Exception):
    """Base exception for process engine errors."""
    pass


class ProcessDefinitionError(ProcessEngineError):
    """Error related to process definitions."""
    pass


class ProcessExecutionError(ProcessEngineError):
    """Error related to process execution."""
    pass


class ProcessNotFoundError(ProcessDefinitionError):
    """Process definition not found."""
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Process not found: {identifier}")


class ProcessValidationError(ProcessDefinitionError):
    """Process definition validation failed."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Process validation failed: {'; '.join(errors)}")


class CircularDependencyError(ProcessDefinitionError):
    """Circular dependency detected in step definitions."""
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' -> '.join(cycle)}")


class InvalidStepReferenceError(ProcessDefinitionError):
    """Step references non-existent step."""
    def __init__(self, step_id: str, referenced_id: str):
        self.step_id = step_id
        self.referenced_id = referenced_id
        super().__init__(f"Step '{step_id}' references non-existent step '{referenced_id}'")


class DuplicateStepIdError(ProcessDefinitionError):
    """Duplicate step ID found."""
    def __init__(self, step_id: str):
        self.step_id = step_id
        super().__init__(f"Duplicate step ID: {step_id}")


class ExecutionNotFoundError(ProcessExecutionError):
    """Execution not found."""
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        super().__init__(f"Execution not found: {execution_id}")


class InvalidExecutionStateError(ProcessExecutionError):
    """Invalid state transition attempted."""
    def __init__(self, current_state: str, attempted_action: str):
        self.current_state = current_state
        self.attempted_action = attempted_action
        super().__init__(
            f"Cannot {attempted_action} execution in state '{current_state}'"
        )
