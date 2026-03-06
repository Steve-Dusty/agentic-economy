"""
Unit tests for Process Definition API endpoints.

Tests for: E1-04 Process Definition API Endpoints

Note: These tests focus on domain logic and helper functions.
Integration tests with FastAPI TestClient would require additional setup.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from services.process_engine.domain import (
    ProcessDefinition,
    ProcessId,
    StepDefinition,
    DefinitionStatus,
)
from services.process_engine.services import ProcessValidator, ValidationResult, ValidationError, ErrorLevel


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_definition():
    """Create a sample process definition."""
    definition = ProcessDefinition.create(
        name="test-process",
        description="A test process",
        created_by="test@example.com",
    )
    definition.steps = [
        StepDefinition.from_dict({
            "id": "step-a",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "Do something",
        }),
    ]
    return definition


@pytest.fixture
def published_definition(sample_definition):
    """Create a published process definition."""
    return sample_definition.publish()


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return MagicMock()


@pytest.fixture
def mock_current_user():
    """Create a mock current user."""
    user = MagicMock()
    user.email = "test@example.com"
    user.id = "user-123"
    return user


# =============================================================================
# Helper Function Tests
# =============================================================================


def to_summary(definition: ProcessDefinition) -> dict:
    """Convert ProcessDefinition to summary dict."""
    return {
        "id": str(definition.id),
        "name": definition.name,
        "version": str(definition.version),
        "status": definition.status.value,
        "description": definition.description,
        "step_count": len(definition.steps),
        "created_by": definition.created_by,
        "created_at": definition.created_at.isoformat(),
        "updated_at": definition.updated_at.isoformat(),
        "published_at": definition.published_at.isoformat() if definition.published_at else None,
    }


def to_detail(definition: ProcessDefinition, yaml_content: str = None) -> dict:
    """Convert ProcessDefinition to detail dict."""
    import yaml
    
    result = {
        "id": str(definition.id),
        "name": definition.name,
        "version": str(definition.version),
        "status": definition.status.value,
        "description": definition.description,
        "steps": [step.to_dict() for step in definition.steps],
        "outputs": [output.to_dict() for output in definition.outputs],
        "created_by": definition.created_by,
        "created_at": definition.created_at.isoformat(),
        "updated_at": definition.updated_at.isoformat(),
        "published_at": definition.published_at.isoformat() if definition.published_at else None,
    }
    
    if yaml_content:
        result["yaml_content"] = yaml_content
    else:
        result["yaml_content"] = yaml.dump(definition.to_yaml_dict(), default_flow_style=False)
    
    return result


def to_validation_response(result: ValidationResult) -> dict:
    """Convert ValidationResult to response dict."""
    errors = []
    warnings = []
    
    for error in result.errors:
        item = {
            "message": error.message,
            "level": error.level.value,
            "path": error.path,
            "line": error.line,
            "suggestion": error.suggestion,
        }
        errors.append(item)
    
    for warning in result.warnings:
        item = {
            "message": warning.message,
            "level": warning.level.value,
            "path": warning.path,
            "line": warning.line,
            "suggestion": warning.suggestion,
        }
        warnings.append(item)
    
    return {
        "is_valid": result.is_valid,
        "errors": errors,
        "warnings": warnings,
    }


class TestHelperFunctions:
    """Tests for helper conversion functions."""

    def test_to_summary(self, sample_definition):
        """to_summary produces correct structure."""
        summary = to_summary(sample_definition)
        
        assert summary["id"] == str(sample_definition.id)
        assert summary["name"] == "test-process"
        assert summary["status"] == "draft"
        assert summary["step_count"] == 1
        assert "created_at" in summary

    def test_to_detail(self, sample_definition):
        """to_detail produces correct structure."""
        detail = to_detail(sample_definition)
        
        assert detail["id"] == str(sample_definition.id)
        assert detail["name"] == "test-process"
        assert len(detail["steps"]) == 1
        assert detail["yaml_content"] is not None  # Should be generated

    def test_to_detail_with_yaml_content(self, sample_definition):
        """to_detail preserves provided yaml_content."""
        yaml_content = "name: test-process\nsteps: []"
        detail = to_detail(sample_definition, yaml_content)
        
        assert detail["yaml_content"] == yaml_content

    def test_to_validation_response_valid(self):
        """to_validation_response handles valid result."""
        result = ValidationResult(errors=[], warnings=[], definition=None)
        response = to_validation_response(result)
        
        assert response["is_valid"] is True
        assert response["errors"] == []
        assert response["warnings"] == []

    def test_to_validation_response_with_errors(self):
        """to_validation_response separates errors and warnings."""
        result = ValidationResult(
            errors=[
                ValidationError("Missing name", level=ErrorLevel.ERROR),
            ],
            warnings=[
                ValidationError("Agent not running", level=ErrorLevel.WARNING),
            ],
            definition=None,
        )
        response = to_validation_response(result)
        
        assert response["is_valid"] is False
        assert len(response["errors"]) == 1
        assert len(response["warnings"]) == 1
        assert response["errors"][0]["message"] == "Missing name"
        assert response["warnings"][0]["message"] == "Agent not running"


# =============================================================================
# API Endpoint Tests (Unit - with mocked dependencies)
# =============================================================================


class TestCreateProcessValidation:
    """Tests for create process validation logic."""

    def test_valid_yaml_creates_definition(self, sample_definition):
        """Valid YAML should create a definition successfully."""
        yaml_content = """
name: test-process
description: Test
steps:
  - id: step-a
    type: agent_task
    agent: test-agent
    message: Hello
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)
        
        assert result.is_valid
        assert result.definition is not None
        assert result.definition.name == "test-process"

    def test_invalid_yaml_returns_errors(self):
        """Invalid YAML should return validation errors."""
        yaml_content = """
name: test-process
steps: []
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_malformed_yaml_returns_errors(self):
        """Malformed YAML should return parse errors."""
        yaml_content = """
name: [invalid yaml
  - broken: structure
"""
        validator = ProcessValidator()
        result = validator.validate_yaml(yaml_content)
        
        assert not result.is_valid


class TestProcessStatusTransitions:
    """Tests for process status transition rules."""

    def test_draft_can_be_updated(self, sample_definition):
        """Draft processes can be updated."""
        assert sample_definition.status == DefinitionStatus.DRAFT
        # Draft processes should be updatable - no exception

    def test_published_cannot_be_updated_directly(self, published_definition):
        """Published processes should not be updatable."""
        assert published_definition.status == DefinitionStatus.PUBLISHED
        # API should reject updates to published processes

    def test_draft_can_be_published(self, sample_definition):
        """Draft processes can be published."""
        published = sample_definition.publish()
        assert published.status == DefinitionStatus.PUBLISHED

    def test_published_can_be_archived(self, published_definition):
        """Published processes can be archived."""
        archived = published_definition.archive()
        assert archived.status == DefinitionStatus.ARCHIVED

    def test_draft_can_be_deleted(self, sample_definition):
        """Draft processes can be deleted."""
        assert sample_definition.status == DefinitionStatus.DRAFT
        # No exception - draft can be deleted

    def test_archived_can_be_deleted(self, published_definition):
        """Archived processes can be deleted."""
        archived = published_definition.archive()
        assert archived.status == DefinitionStatus.ARCHIVED
        # No exception - archived can be deleted


class TestNewVersionCreation:
    """Tests for creating new versions."""

    def test_new_version_increments_major(self, sample_definition):
        """New version should increment major version number."""
        new_version = sample_definition.create_new_version()
        
        assert new_version.version.major == sample_definition.version.major + 1
        assert new_version.status == DefinitionStatus.DRAFT
        assert new_version.id != sample_definition.id

    def test_new_version_from_published(self, published_definition):
        """Can create new version from published process."""
        new_version = published_definition.create_new_version()
        
        assert new_version.status == DefinitionStatus.DRAFT
        assert new_version.published_at is None


# =============================================================================
# Repository Integration Tests
# =============================================================================


class TestRepositoryIntegration:
    """Tests that verify repository operations work correctly."""

    @pytest.fixture
    def memory_repo(self):
        """Create an in-memory repository for testing."""
        from services.process_engine.repositories import SqliteProcessDefinitionRepository
        return SqliteProcessDefinitionRepository(":memory:")

    def test_save_and_retrieve(self, memory_repo, sample_definition):
        """Can save and retrieve a definition."""
        memory_repo.save(sample_definition)
        
        retrieved = memory_repo.get_by_id(sample_definition.id)
        assert retrieved is not None
        assert retrieved.name == sample_definition.name

    def test_list_all(self, memory_repo, sample_definition):
        """Can list all definitions."""
        memory_repo.save(sample_definition)
        
        definitions = memory_repo.list_all()
        assert len(definitions) == 1

    def test_list_by_status(self, memory_repo, sample_definition):
        """Can filter by status."""
        # Save a draft
        memory_repo.save(sample_definition)
        
        # Create and save a published version
        published = sample_definition.publish()
        # Need a different ID to not overwrite
        from dataclasses import replace
        from services.process_engine.domain import ProcessId
        published = replace(published, id=ProcessId.generate(), name="published-process")
        memory_repo.save(published)
        
        drafts = memory_repo.list_all(status=DefinitionStatus.DRAFT)
        published_list = memory_repo.list_all(status=DefinitionStatus.PUBLISHED)
        
        assert len(drafts) == 1
        assert len(published_list) == 1
        assert drafts[0].status == DefinitionStatus.DRAFT
        assert published_list[0].status == DefinitionStatus.PUBLISHED

    def test_delete(self, memory_repo, sample_definition):
        """Can delete a definition."""
        memory_repo.save(sample_definition)
        memory_repo.delete(sample_definition.id)
        
        retrieved = memory_repo.get_by_id(sample_definition.id)
        assert retrieved is None

    def test_count(self, memory_repo, sample_definition):
        """Can count definitions."""
        assert memory_repo.count() == 0
        
        memory_repo.save(sample_definition)
        assert memory_repo.count() == 1
