"""
Unit Tests for Sub-Process Validation (E10-01)

Tests ProcessValidator's sub_process validation logic.
"""

import pytest

from services.process_engine.services import ProcessValidator


class TestSubProcessSchemaValidation:
    """Tests for sub_process schema validation."""

    def test_validate_sub_process_missing_process_name(self):
        """Test validation fails when process_name is missing."""
        yaml_content = """
name: parent-process
steps:
  - id: call-child
    type: sub_process
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("process_name" in e.message for e in result.errors)

    def test_validate_sub_process_valid(self):
        """Test validation passes for valid sub_process step."""
        yaml_content = """
name: parent-process
steps:
  - id: call-child
    type: sub_process
    process_name: child-process
    input_mapping:
      topic: "{{input.topic}}"
    output_key: result
    timeout: 30m
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)

        # Should not have errors related to sub_process schema
        sub_process_errors = [
            e for e in result.errors
            if "sub_process" in e.message.lower() or "process_name" in e.message.lower()
        ]
        assert len(sub_process_errors) == 0

    def test_validate_sub_process_invalid_input_mapping(self):
        """Test validation fails when input_mapping is not a dict."""
        yaml_content = """
name: parent-process
steps:
  - id: call-child
    type: sub_process
    process_name: child-process
    input_mapping: "not a dict"
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("input_mapping" in e.message for e in result.errors)


class TestSubProcessRecursionDetection:
    """Tests for recursive sub-process detection."""

    def test_detect_direct_self_recursion(self):
        """Test that direct self-recursion is detected."""
        yaml_content = """
name: recursive-process
steps:
  - id: call-self
    type: sub_process
    process_name: recursive-process
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        recursion_errors = [
            e for e in result.errors
            if "recursive" in e.message.lower()
        ]
        assert len(recursion_errors) > 0

    def test_no_error_for_different_process(self):
        """Test that calling a different process doesn't trigger recursion error."""
        yaml_content = """
name: parent-process
steps:
  - id: call-child
    type: sub_process
    process_name: child-process
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)

        # Should not have recursion errors
        recursion_errors = [
            e for e in result.errors
            if "recursive" in e.message.lower()
        ]
        assert len(recursion_errors) == 0


class TestSubProcessExistenceCheck:
    """Tests for sub-process existence checking."""

    def test_check_sub_process_exists(self):
        """Test that process_checker is called for sub_process steps."""
        yaml_content = """
name: parent-process
steps:
  - id: call-child
    type: sub_process
    process_name: child-process
"""
        # Mock process checker that always returns False (process not found)
        def process_checker(name: str, version: str = None) -> bool:
            return False

        validator = ProcessValidator(process_checker=process_checker)
        result = validator.validate_yaml(yaml_content)

        # Should have a warning about process not found
        process_warnings = [
            w for w in result.warnings
            if "child-process" in w.message and "not found" in w.message.lower()
        ]
        assert len(process_warnings) > 0

    def test_no_warning_when_process_exists(self):
        """Test no warning when sub-process exists."""
        yaml_content = """
name: parent-process
steps:
  - id: call-child
    type: sub_process
    process_name: child-process
"""
        # Mock process checker that always returns True
        def process_checker(name: str, version: str = None) -> bool:
            return True

        validator = ProcessValidator(process_checker=process_checker)
        result = validator.validate_yaml(yaml_content)

        # Should not have warnings about process not found
        process_warnings = [
            w for w in result.warnings
            if "not found" in w.message.lower()
        ]
        assert len(process_warnings) == 0

    def test_check_versioned_sub_process(self):
        """Test that version is passed to process_checker."""
        checked_versions = []

        def process_checker(name: str, version: str = None) -> bool:
            checked_versions.append((name, version))
            return True

        yaml_content = """
name: parent-process
steps:
  - id: call-child
    type: sub_process
    process_name: child-process
    version: "2.0"
"""
        validator = ProcessValidator(process_checker=process_checker)
        validator.validate_yaml(yaml_content)

        # Verify version was passed
        assert any(
            name == "child-process" and version == "2.0"
            for name, version in checked_versions
        )


class TestSubProcessWithOtherSteps:
    """Tests for processes combining sub_process with other step types."""

    def test_mixed_step_types(self):
        """Test validation passes for process with mixed step types."""
        yaml_content = """
name: complex-process
steps:
  - id: research
    type: agent_task
    agent: research-agent
    message: Research this topic

  - id: call-enrichment
    type: sub_process
    process_name: data-enrichment
    depends_on: research
    input_mapping:
      data: "{{steps.research.output}}"

  - id: notify
    type: notification
    channel: slack
    message: Processing complete
    depends_on: call-enrichment
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)

        # Should parse without errors
        assert result.is_valid

    def test_sub_process_with_dependencies(self):
        """Test sub_process step can have dependencies."""
        yaml_content = """
name: process-with-deps
steps:
  - id: step-one
    type: agent_task
    agent: agent-one
    message: Do something

  - id: call-child
    type: sub_process
    process_name: child-process
    depends_on: step-one

  - id: step-three
    type: agent_task
    agent: agent-three
    message: Do something else
    depends_on: call-child
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)

        # Should parse successfully
        assert result.definition is not None

        # Verify dependencies are set
        call_child_step = next(
            s for s in result.definition.steps if str(s.id) == "call-child"
        )
        assert len(call_child_step.dependencies) > 0
