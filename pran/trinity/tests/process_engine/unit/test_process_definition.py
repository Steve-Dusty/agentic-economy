"""
Unit tests for ProcessDefinition aggregate and related entities.

Tests for: ProcessDefinition, StepDefinition, OutputConfig
Reference: E1-01 Acceptance Criteria
"""

import pytest
from datetime import datetime

from services.process_engine.domain import (
    ProcessDefinition,
    StepDefinition,
    OutputConfig,
    ProcessId,
    StepId,
    Version,
    Duration,
    DefinitionStatus,
    StepType,
    AgentTaskConfig,
    HumanApprovalConfig,
    ProcessValidationError,
    CircularDependencyError,
)


# =============================================================================
# StepDefinition Tests
# =============================================================================


class TestStepDefinition:
    """Tests for StepDefinition entity."""

    def test_from_dict_agent_task(self):
        """StepDefinition parses agent_task step correctly."""
        data = {
            "id": "research",
            "name": "Research Topic",
            "type": "agent_task",
            "agent": "research-agent",
            "message": "Research {{input.topic}}",
            "timeout": "10m",
        }
        
        step = StepDefinition.from_dict(data)
        
        assert str(step.id) == "research"
        assert step.name == "Research Topic"
        assert step.type == StepType.AGENT_TASK
        assert isinstance(step.config, AgentTaskConfig)
        assert step.config.agent == "research-agent"
        assert step.config.message == "Research {{input.topic}}"
        assert step.config.timeout.seconds == 600  # 10 minutes

    def test_from_dict_with_dependencies(self):
        """StepDefinition parses depends_on correctly."""
        data = {
            "id": "write",
            "type": "agent_task",
            "agent": "writer-agent",
            "message": "Write based on {{steps.research.output}}",
            "depends_on": ["research"],
        }
        
        step = StepDefinition.from_dict(data)
        
        assert len(step.dependencies) == 1
        assert str(step.dependencies[0]) == "research"

    def test_from_dict_string_dependency(self):
        """StepDefinition handles single string depends_on."""
        data = {
            "id": "step-b",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "Test",
            "depends_on": "step-a",
        }
        
        step = StepDefinition.from_dict(data)
        
        assert len(step.dependencies) == 1
        assert str(step.dependencies[0]) == "step-a"

    def test_from_dict_with_condition(self):
        """StepDefinition parses condition correctly."""
        data = {
            "id": "finalize",
            "type": "agent_task",
            "agent": "agent",
            "message": "Finalize",
            "condition": "{{steps.review.decision}} == 'approved'",
        }
        
        step = StepDefinition.from_dict(data)
        
        assert step.condition == "{{steps.review.decision}} == 'approved'"

    def test_from_dict_human_approval(self):
        """StepDefinition parses human_approval step correctly."""
        data = {
            "id": "review",
            "name": "Manager Review",
            "type": "human_approval",
            "title": "Review Required",
            "description": "Please review the draft",
            "assignees": ["manager@example.com"],
            "timeout": "48h",
        }
        
        step = StepDefinition.from_dict(data)
        
        assert step.type == StepType.HUMAN_APPROVAL
        assert isinstance(step.config, HumanApprovalConfig)
        assert step.config.title == "Review Required"
        assert step.config.timeout.seconds == 48 * 3600

    def test_to_dict_roundtrip(self):
        """StepDefinition can be serialized and deserialized."""
        original = {
            "id": "research",
            "name": "Research Topic",
            "type": "agent_task",
            "agent": "research-agent",
            "message": "Research topic",
            "timeout": "5m",
            "depends_on": ["prev-step"],
        }
        
        step = StepDefinition.from_dict(original)
        serialized = step.to_dict()
        
        assert serialized["id"] == "research"
        assert serialized["agent"] == "research-agent"
        assert serialized["depends_on"] == ["prev-step"]


# =============================================================================
# OutputConfig Tests
# =============================================================================


class TestOutputConfig:
    """Tests for OutputConfig entity."""

    def test_from_dict_full(self):
        """OutputConfig parses full config correctly."""
        data = {
            "name": "article",
            "source": "{{steps.edit.output}}",
            "description": "The final article",
        }
        
        output = OutputConfig.from_dict(data)
        
        assert output.name == "article"
        assert output.source == "{{steps.edit.output}}"
        assert output.description == "The final article"

    def test_from_dict_string(self):
        """OutputConfig handles simple string format."""
        output = OutputConfig.from_dict("{{steps.final.output}}")
        
        assert output.name == "output"
        assert output.source == "{{steps.final.output}}"


# =============================================================================
# ProcessDefinition Tests
# =============================================================================


class TestProcessDefinition:
    """Tests for ProcessDefinition aggregate."""

    def test_create_draft(self):
        """ProcessDefinition.create() creates draft definition."""
        definition = ProcessDefinition.create(
            name="test-process",
            description="A test process",
        )
        
        assert definition.name == "test-process"
        assert definition.description == "A test process"
        assert definition.status == DefinitionStatus.DRAFT
        assert definition.version.major == 1
        assert definition.version.minor == 0
        assert isinstance(definition.id, ProcessId)

    def test_from_yaml_dict(self):
        """ProcessDefinition parses YAML dict correctly."""
        yaml_data = {
            "name": "content-pipeline",
            "version": 1,
            "description": "Generate content",
            "steps": [
                {
                    "id": "research",
                    "type": "agent_task",
                    "agent": "research-agent",
                    "message": "Research topic",
                },
                {
                    "id": "write",
                    "type": "agent_task",
                    "agent": "writer-agent",
                    "message": "Write article",
                    "depends_on": ["research"],
                },
            ],
            "outputs": [
                {
                    "name": "article",
                    "source": "{{steps.write.output}}",
                },
            ],
        }
        
        definition = ProcessDefinition.from_yaml_dict(yaml_data)
        
        assert definition.name == "content-pipeline"
        assert len(definition.steps) == 2
        assert len(definition.outputs) == 1
        assert definition.status == DefinitionStatus.DRAFT

    def test_validate_valid_definition(self):
        """validate() returns empty list for valid definition."""
        definition = ProcessDefinition.create(name="valid-process")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
            }),
            StepDefinition.from_dict({
                "id": "step-b",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["step-a"],
            }),
        ]
        
        errors = definition.validate()
        
        assert errors == []

    def test_validate_duplicate_step_ids(self):
        """validate() catches duplicate step IDs."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "same-id",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test 1",
            }),
            StepDefinition.from_dict({
                "id": "same-id",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test 2",
            }),
        ]
        
        errors = definition.validate()
        
        assert any("Duplicate step ID" in err for err in errors)

    def test_validate_invalid_dependency_reference(self):
        """validate() catches references to non-existent steps."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["non-existent"],
            }),
        ]
        
        errors = definition.validate()
        
        assert any("non-existent" in err for err in errors)

    def test_validate_circular_dependency(self):
        """validate() catches circular dependencies."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["step-b"],
            }),
            StepDefinition.from_dict({
                "id": "step-b",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["step-a"],
            }),
        ]
        
        errors = definition.validate()
        
        assert any("Circular dependency" in err for err in errors)

    def test_validate_empty_name(self):
        """validate() catches empty process name."""
        definition = ProcessDefinition.create(name="")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
            }),
        ]
        
        errors = definition.validate()
        
        assert any("name cannot be empty" in err for err in errors)

    def test_validate_no_steps(self):
        """validate() catches process with no steps."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = []
        
        errors = definition.validate()
        
        assert any("at least one step" in err for err in errors)

    def test_publish_valid_definition(self):
        """publish() returns published definition if valid."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
            }),
        ]
        
        published = definition.publish()
        
        assert published.status == DefinitionStatus.PUBLISHED
        assert published.published_at is not None
        # Original is unchanged
        assert definition.status == DefinitionStatus.DRAFT

    def test_publish_invalid_definition_raises(self):
        """publish() raises ProcessValidationError if invalid."""
        definition = ProcessDefinition.create(name="")
        
        with pytest.raises(ProcessValidationError) as exc_info:
            definition.publish()
        
        assert "name cannot be empty" in str(exc_info.value)

    def test_archive(self):
        """archive() returns archived definition."""
        definition = ProcessDefinition.create(name="test")
        
        archived = definition.archive()
        
        assert archived.status == DefinitionStatus.ARCHIVED

    def test_create_new_version(self):
        """create_new_version() increments version and resets status."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
            }),
        ]
        published = definition.publish()
        
        new_version = published.create_new_version()
        
        assert new_version.version.major == 2
        assert new_version.status == DefinitionStatus.DRAFT
        assert new_version.id != published.id

    def test_get_entry_steps(self):
        """get_entry_steps() returns steps with no dependencies."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "entry-1",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
            }),
            StepDefinition.from_dict({
                "id": "entry-2",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
            }),
            StepDefinition.from_dict({
                "id": "dependent",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["entry-1"],
            }),
        ]
        
        entry_steps = definition.get_entry_steps()
        
        assert len(entry_steps) == 2
        entry_ids = [str(s) for s in entry_steps]
        assert "entry-1" in entry_ids
        assert "entry-2" in entry_ids
        assert "dependent" not in entry_ids

    def test_get_dependent_steps(self):
        """get_dependent_steps() returns steps depending on given step."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "parent",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
            }),
            StepDefinition.from_dict({
                "id": "child-1",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["parent"],
            }),
            StepDefinition.from_dict({
                "id": "child-2",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["parent"],
            }),
        ]
        
        parent_id = definition.steps[0].id
        dependents = definition.get_dependent_steps(parent_id)
        
        assert len(dependents) == 2
        dep_ids = [str(s) for s in dependents]
        assert "child-1" in dep_ids
        assert "child-2" in dep_ids

    def test_to_yaml_dict(self):
        """to_yaml_dict() produces valid YAML structure."""
        definition = ProcessDefinition.create(
            name="test-process",
            description="Test description",
        )
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "type": "agent_task",
                "agent": "test-agent",
                "message": "Test message",
            }),
        ]
        definition.outputs = [
            OutputConfig(name="result", source="{{steps.step-a.output}}"),
        ]
        
        yaml_dict = definition.to_yaml_dict()
        
        assert yaml_dict["name"] == "test-process"
        assert yaml_dict["description"] == "Test description"
        assert len(yaml_dict["steps"]) == 1
        assert yaml_dict["steps"][0]["agent"] == "test-agent"
        assert len(yaml_dict["outputs"]) == 1

    def test_to_dict_full(self):
        """to_dict() includes all metadata."""
        definition = ProcessDefinition.create(
            name="test",
            created_by="user@example.com",
        )
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
            }),
        ]
        
        data = definition.to_dict()
        
        assert "id" in data
        assert data["name"] == "test"
        assert data["status"] == "draft"
        assert data["created_by"] == "user@example.com"
        assert "created_at" in data


# =============================================================================
# Complex Validation Scenarios
# =============================================================================


class TestProcessDefinitionComplexValidation:
    """Tests for complex validation scenarios."""

    def test_three_step_circular_dependency(self):
        """Detect circular dependencies spanning multiple steps."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["step-c"],
            }),
            StepDefinition.from_dict({
                "id": "step-b",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["step-a"],
            }),
            StepDefinition.from_dict({
                "id": "step-c",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["step-b"],
            }),
        ]
        
        errors = definition.validate()
        
        assert any("Circular dependency" in err for err in errors)

    def test_diamond_dependency_valid(self):
        """Diamond dependency pattern should be valid."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "start",
                "type": "agent_task",
                "agent": "agent",
                "message": "Start",
            }),
            StepDefinition.from_dict({
                "id": "path-a",
                "type": "agent_task",
                "agent": "agent",
                "message": "Path A",
                "depends_on": ["start"],
            }),
            StepDefinition.from_dict({
                "id": "path-b",
                "type": "agent_task",
                "agent": "agent",
                "message": "Path B",
                "depends_on": ["start"],
            }),
            StepDefinition.from_dict({
                "id": "end",
                "type": "agent_task",
                "agent": "agent",
                "message": "End",
                "depends_on": ["path-a", "path-b"],
            }),
        ]
        
        errors = definition.validate()
        
        assert errors == []

    def test_self_reference_invalid(self):
        """Step depending on itself should be invalid."""
        definition = ProcessDefinition.create(name="test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-a",
                "type": "agent_task",
                "agent": "agent",
                "message": "Test",
                "depends_on": ["step-a"],  # Self-reference
            }),
        ]
        
        errors = definition.validate()
        
        # Should catch either as invalid reference or circular
        assert len(errors) > 0
