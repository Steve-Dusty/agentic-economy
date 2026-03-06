"""
Unit tests for Process Validator Service.

Tests for: ProcessValidator, ValidationResult
Reference: E1-03 Acceptance Criteria
"""

import pytest
from textwrap import dedent

from services.process_engine.services import (
    ProcessValidator,
    ValidationResult,
    ValidationError,
)
from services.process_engine.domain import ProcessDefinition, StepDefinition


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def validator():
    """Create a validator without agent checking."""
    return ProcessValidator()


@pytest.fixture
def validator_with_agent_check():
    """Create a validator with mock agent checker."""
    def check_agent(name: str) -> tuple[bool, bool]:
        if name == "existing-running":
            return (True, True)
        elif name == "existing-stopped":
            return (True, False)
        else:
            return (False, False)
    
    return ProcessValidator(agent_checker=check_agent)


@pytest.fixture
def valid_yaml():
    """Valid minimal process YAML."""
    return dedent("""
        name: test-process
        version: 1
        description: A test process
        
        steps:
          - id: step-a
            type: agent_task
            agent: test-agent
            message: Do something
    """).strip()


# =============================================================================
# YAML Parsing Tests
# =============================================================================


class TestYamlParsing:
    """Tests for YAML syntax validation."""

    def test_valid_yaml_parses(self, validator, valid_yaml):
        """Valid YAML is parsed successfully."""
        result = validator.validate_yaml(valid_yaml)
        
        assert result.is_valid
        assert result.definition is not None

    def test_invalid_yaml_syntax(self, validator):
        """Invalid YAML syntax produces error."""
        invalid_yaml = dedent("""
            name: test
            steps:
              - id: step-a
                invalid: yaml: here
        """).strip()
        
        result = validator.validate_yaml(invalid_yaml)
        
        assert not result.is_valid
        assert any("YAML syntax" in e.message for e in result.errors)

    def test_yaml_not_object(self, validator):
        """YAML that's not an object produces error."""
        result = validator.validate_yaml("- just\n- a\n- list")
        
        assert not result.is_valid
        assert any("object/mapping" in e.message for e in result.errors)


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestSchemaValidation:
    """Tests for schema validation (required fields, types)."""

    def test_missing_name(self, validator):
        """Missing 'name' field produces error."""
        yaml_content = dedent("""
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("name" in e.message and "Missing" in e.message for e in result.errors)

    def test_empty_name(self, validator):
        """Empty 'name' field produces error."""
        yaml_content = dedent("""
            name: ""
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("empty" in e.message.lower() for e in result.errors)

    def test_missing_steps(self, validator):
        """Missing 'steps' field produces error."""
        yaml_content = dedent("""
            name: test-process
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("steps" in e.message and "Missing" in e.message for e in result.errors)

    def test_empty_steps(self, validator):
        """Empty 'steps' list produces error."""
        yaml_content = dedent("""
            name: test-process
            steps: []
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("at least one step" in e.message for e in result.errors)

    def test_step_missing_id(self, validator):
        """Step without 'id' produces error."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - type: agent_task
                agent: test-agent
                message: Test
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("id" in e.message for e in result.errors)

    def test_step_missing_type(self, validator):
        """Step without 'type' produces error."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                agent: test-agent
                message: Test
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("type" in e.message for e in result.errors)

    def test_invalid_step_type(self, validator):
        """Invalid step type produces error with suggestion."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: invalid_type
                agent: test-agent
                message: Test
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        error = next(e for e in result.errors if "invalid_type" in e.message.lower())
        assert error.suggestion is not None
        assert "agent_task" in error.suggestion

    def test_agent_task_missing_agent(self, validator):
        """agent_task without 'agent' produces error."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                message: Test
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("agent" in e.message for e in result.errors)

    def test_agent_task_missing_message(self, validator):
        """agent_task without 'message' produces error."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("message" in e.message for e in result.errors)


# =============================================================================
# Semantic Validation Tests
# =============================================================================


class TestSemanticValidation:
    """Tests for semantic validation (dependencies, references)."""

    def test_duplicate_step_ids(self, validator):
        """Duplicate step IDs produce error."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: First
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Second
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("Duplicate" in e.message for e in result.errors)

    def test_invalid_dependency_reference(self, validator):
        """Reference to non-existent step produces error."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: Test
                depends_on: [non-existent]
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("non-existent" in e.message for e in result.errors)

    def test_circular_dependency(self, validator):
        """Circular dependencies produce error."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: A
                depends_on: [step-b]
              - id: step-b
                type: agent_task
                agent: test-agent
                message: B
                depends_on: [step-a]
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert any("Circular" in e.message for e in result.errors)

    def test_valid_dependency_chain(self, validator):
        """Valid dependency chain passes validation."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: test-agent
                message: First
              - id: step-b
                type: agent_task
                agent: test-agent
                message: Second
                depends_on: [step-a]
              - id: step-c
                type: agent_task
                agent: test-agent
                message: Third
                depends_on: [step-b]
        """).strip()
        
        result = validator.validate_yaml(yaml_content)
        
        assert result.is_valid


# =============================================================================
# Agent Checking Tests
# =============================================================================


class TestAgentChecking:
    """Tests for agent existence checking."""

    def test_existing_running_agent_no_warning(self, validator_with_agent_check):
        """Existing and running agent produces no warning."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: existing-running
                message: Test
        """).strip()
        
        result = validator_with_agent_check.validate_yaml(yaml_content)
        
        assert result.is_valid
        assert not result.has_warnings

    def test_existing_stopped_agent_warning(self, validator_with_agent_check):
        """Existing but stopped agent produces warning."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: existing-stopped
                message: Test
        """).strip()
        
        result = validator_with_agent_check.validate_yaml(yaml_content)
        
        assert result.is_valid  # Still valid
        assert result.has_warnings
        assert any("not running" in w.message for w in result.warnings)

    def test_nonexistent_agent_warning(self, validator_with_agent_check):
        """Non-existent agent produces warning."""
        yaml_content = dedent("""
            name: test-process
            steps:
              - id: step-a
                type: agent_task
                agent: does-not-exist
                message: Test
        """).strip()
        
        result = validator_with_agent_check.validate_yaml(yaml_content)
        
        assert result.is_valid  # Still valid
        assert result.has_warnings
        assert any("does not exist" in w.message for w in result.warnings)

    def test_no_agent_check_skips_warnings(self, validator, valid_yaml):
        """Validator without agent checker doesn't produce warnings."""
        result = validator.validate_yaml(valid_yaml)
        
        assert result.is_valid
        assert not result.has_warnings


# =============================================================================
# ValidationResult Tests
# =============================================================================


class TestValidationResult:
    """Tests for ValidationResult data structure."""

    def test_empty_result_is_valid(self):
        """Empty result is valid."""
        result = ValidationResult()
        assert result.is_valid
        assert not result.has_warnings

    def test_result_with_error_not_valid(self):
        """Result with error is not valid."""
        result = ValidationResult()
        result.add_error("Test error")
        
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_result_with_warning_still_valid(self):
        """Result with only warning is still valid."""
        result = ValidationResult()
        result.add_warning("Test warning")
        
        assert result.is_valid
        assert result.has_warnings
        assert len(result.warnings) == 1

    def test_to_dict(self):
        """to_dict produces correct structure."""
        result = ValidationResult()
        result.add_error("Error message", path="steps[0].id")
        result.add_warning("Warning message")
        
        d = result.to_dict()
        
        assert d["is_valid"] is False
        assert d["has_warnings"] is True
        assert len(d["errors"]) == 1
        assert d["errors"][0]["message"] == "Error message"
        assert d["errors"][0]["path"] == "steps[0].id"


# =============================================================================
# Definition Validation Tests
# =============================================================================


class TestDefinitionValidation:
    """Tests for validating ProcessDefinition objects directly."""

    def test_validate_valid_definition(self, validator):
        """Valid definition passes validation."""
        definition = ProcessDefinition.create(name="test-process")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "type": "agent_task",
                "agent": "test-agent",
                "message": "Test",
            }),
        ]
        
        result = validator.validate_definition(definition)
        
        assert result.is_valid
        assert result.definition is definition

    def test_validate_invalid_definition(self, validator):
        """Invalid definition fails validation."""
        definition = ProcessDefinition.create(name="")
        definition.steps = []  # No steps
        
        result = validator.validate_definition(definition)
        
        assert not result.is_valid
