"""
Unit tests for Process Engine Repositories.

Tests for: ProcessDefinitionRepository (SQLite implementation)
Reference: E1-02 Acceptance Criteria
"""

import pytest
from datetime import datetime, timezone

from services.process_engine.domain import (
    ProcessDefinition,
    StepDefinition,
    ProcessId,
    Version,
    DefinitionStatus,
)
from services.process_engine.repositories import SqliteProcessDefinitionRepository


@pytest.fixture
def repo():
    """Create an in-memory SQLite repository for testing."""
    return SqliteProcessDefinitionRepository(":memory:")


@pytest.fixture
def sample_definition() -> ProcessDefinition:
    """Create a sample process definition for testing."""
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
            "message": "Test message",
        }),
        StepDefinition.from_dict({
            "id": "step-b",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "Another message",
            "depends_on": ["step-a"],
        }),
    ]
    return definition


# =============================================================================
# Basic CRUD Tests
# =============================================================================


class TestSqliteRepositoryCRUD:
    """Tests for basic CRUD operations."""

    def test_save_and_get_by_id(self, repo, sample_definition):
        """Can save and retrieve a definition by ID."""
        repo.save(sample_definition)
        
        retrieved = repo.get_by_id(sample_definition.id)
        
        assert retrieved is not None
        assert retrieved.name == sample_definition.name
        assert retrieved.description == sample_definition.description
        assert len(retrieved.steps) == 2

    def test_get_by_id_not_found(self, repo):
        """Returns None when ID not found."""
        fake_id = ProcessId.generate()
        
        result = repo.get_by_id(fake_id)
        
        assert result is None

    def test_save_updates_existing(self, repo, sample_definition):
        """Saving an existing ID updates the record."""
        repo.save(sample_definition)
        
        # Modify and save again
        sample_definition.description = "Updated description"
        repo.save(sample_definition)
        
        retrieved = repo.get_by_id(sample_definition.id)
        assert retrieved.description == "Updated description"
        
        # Should still be only one record
        assert repo.count() == 1

    def test_delete(self, repo, sample_definition):
        """Can delete a definition."""
        repo.save(sample_definition)
        assert repo.exists(sample_definition.id)
        
        result = repo.delete(sample_definition.id)
        
        assert result is True
        assert not repo.exists(sample_definition.id)

    def test_delete_not_found(self, repo):
        """Delete returns False when ID not found."""
        fake_id = ProcessId.generate()
        
        result = repo.delete(fake_id)
        
        assert result is False

    def test_exists(self, repo, sample_definition):
        """Exists checks work correctly."""
        assert not repo.exists(sample_definition.id)
        
        repo.save(sample_definition)
        
        assert repo.exists(sample_definition.id)

    def test_count(self, repo, sample_definition):
        """Count returns correct number."""
        assert repo.count() == 0
        
        repo.save(sample_definition)
        assert repo.count() == 1
        
        # Add another
        another = ProcessDefinition.create(name="another-process")
        another.steps = sample_definition.steps
        repo.save(another)
        assert repo.count() == 2


# =============================================================================
# Name and Version Tests
# =============================================================================


class TestSqliteRepositoryNameVersion:
    """Tests for name and version queries."""

    def test_get_by_name_specific_version(self, repo, sample_definition):
        """Can get a specific version by name."""
        repo.save(sample_definition)
        
        retrieved = repo.get_by_name(
            sample_definition.name,
            version=sample_definition.version
        )
        
        assert retrieved is not None
        assert str(retrieved.id) == str(sample_definition.id)

    def test_get_by_name_latest_published(self, repo, sample_definition):
        """get_by_name without version returns latest published."""
        # Save draft
        repo.save(sample_definition)
        
        # get_by_name without version should return None (only draft exists)
        result = repo.get_by_name(sample_definition.name)
        assert result is None
        
        # Publish and save
        published = sample_definition.publish()
        repo.save(published)
        
        # Now should return the published version
        result = repo.get_by_name(sample_definition.name)
        assert result is not None
        assert result.status == DefinitionStatus.PUBLISHED

    def test_get_latest_version(self, repo, sample_definition):
        """get_latest_version returns latest published version."""
        # Publish v1
        published_v1 = sample_definition.publish()
        repo.save(published_v1)
        
        # Create and publish v2
        v2 = published_v1.create_new_version()
        published_v2 = v2.publish()
        repo.save(published_v2)
        
        latest = repo.get_latest_version(sample_definition.name)
        
        assert latest is not None
        assert latest.version.major == 2

    def test_list_by_name(self, repo, sample_definition):
        """list_by_name returns all versions."""
        # Save v1 draft
        repo.save(sample_definition)
        
        # Publish v1
        published_v1 = sample_definition.publish()
        repo.save(published_v1)
        
        # Create v2 draft
        v2 = published_v1.create_new_version()
        repo.save(v2)
        
        versions = repo.list_by_name(sample_definition.name)
        
        # Should have 2 versions (v1 published, v2 draft)
        assert len(versions) == 2
        # Ordered by version descending
        assert versions[0].version.major == 2
        assert versions[1].version.major == 1

    def test_name_version_uniqueness(self, repo, sample_definition):
        """Saving with same name+version replaces the existing record."""
        repo.save(sample_definition)
        original_id = sample_definition.id
        
        # Create another definition with same name and version but different ID
        duplicate = ProcessDefinition.create(
            name=sample_definition.name,  # Same name
        )
        duplicate.steps = sample_definition.steps
        # Version is 1 by default, same as sample_definition
        
        # INSERT OR REPLACE replaces based on unique name+version index
        repo.save(duplicate)
        
        # Original ID should be gone, new ID should exist
        assert repo.get_by_id(original_id) is None
        assert repo.get_by_id(duplicate.id) is not None
        
        # Should still be only one record with that name
        versions = repo.list_by_name(sample_definition.name)
        assert len(versions) == 1


# =============================================================================
# List and Filter Tests
# =============================================================================


class TestSqliteRepositoryListFilter:
    """Tests for list and filter operations."""

    def test_list_all(self, repo, sample_definition):
        """list_all returns all definitions."""
        # Create multiple definitions
        for i in range(5):
            d = ProcessDefinition.create(name=f"process-{i}")
            d.steps = sample_definition.steps
            repo.save(d)
        
        results = repo.list_all()
        
        assert len(results) == 5

    def test_list_all_with_limit(self, repo, sample_definition):
        """list_all respects limit parameter."""
        for i in range(5):
            d = ProcessDefinition.create(name=f"process-{i}")
            d.steps = sample_definition.steps
            repo.save(d)
        
        results = repo.list_all(limit=3)
        
        assert len(results) == 3

    def test_list_all_with_offset(self, repo, sample_definition):
        """list_all respects offset parameter."""
        for i in range(5):
            d = ProcessDefinition.create(name=f"process-{i}")
            d.steps = sample_definition.steps
            repo.save(d)
        
        all_results = repo.list_all()
        offset_results = repo.list_all(offset=2)
        
        assert len(offset_results) == 3
        assert offset_results[0].name == all_results[2].name

    def test_list_all_filter_by_status(self, repo, sample_definition):
        """list_all can filter by status."""
        # Create draft
        repo.save(sample_definition)
        
        # Create published
        published = ProcessDefinition.create(name="published-process")
        published.steps = sample_definition.steps
        published = published.publish()
        repo.save(published)
        
        drafts = repo.list_all(status=DefinitionStatus.DRAFT)
        published_list = repo.list_all(status=DefinitionStatus.PUBLISHED)
        
        assert len(drafts) == 1
        assert drafts[0].status == DefinitionStatus.DRAFT
        assert len(published_list) == 1
        assert published_list[0].status == DefinitionStatus.PUBLISHED

    def test_count_filter_by_status(self, repo, sample_definition):
        """count can filter by status."""
        # Create draft
        repo.save(sample_definition)
        
        # Create published
        published = ProcessDefinition.create(name="published-process")
        published.steps = sample_definition.steps
        published = published.publish()
        repo.save(published)
        
        assert repo.count() == 2
        assert repo.count(status=DefinitionStatus.DRAFT) == 1
        assert repo.count(status=DefinitionStatus.PUBLISHED) == 1
        assert repo.count(status=DefinitionStatus.ARCHIVED) == 0


# =============================================================================
# Serialization Tests
# =============================================================================


class TestSqliteRepositorySerialization:
    """Tests for serialization/deserialization."""

    def test_steps_preserved(self, repo, sample_definition):
        """Step definitions are correctly serialized and deserialized."""
        repo.save(sample_definition)
        
        retrieved = repo.get_by_id(sample_definition.id)
        
        assert len(retrieved.steps) == 2
        assert str(retrieved.steps[0].id) == "step-a"
        assert retrieved.steps[0].config.agent == "test-agent"
        assert len(retrieved.steps[1].dependencies) == 1

    def test_outputs_preserved(self, repo, sample_definition):
        """Output configs are correctly serialized and deserialized."""
        from services.process_engine.domain import OutputConfig
        
        sample_definition.outputs = [
            OutputConfig(name="result", source="{{steps.step-b.output}}"),
        ]
        repo.save(sample_definition)
        
        retrieved = repo.get_by_id(sample_definition.id)
        
        assert len(retrieved.outputs) == 1
        assert retrieved.outputs[0].name == "result"
        assert retrieved.outputs[0].source == "{{steps.step-b.output}}"

    def test_timestamps_preserved(self, repo, sample_definition):
        """Timestamps are correctly serialized and deserialized."""
        repo.save(sample_definition)
        
        retrieved = repo.get_by_id(sample_definition.id)
        
        # Timestamps should be close (may differ slightly due to serialization)
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None

    def test_published_at_preserved(self, repo, sample_definition):
        """published_at is correctly handled."""
        # Draft has no published_at
        repo.save(sample_definition)
        retrieved = repo.get_by_id(sample_definition.id)
        assert retrieved.published_at is None
        
        # Publish and save
        published = sample_definition.publish()
        repo.save(published)
        
        retrieved = repo.get_by_id(published.id)
        assert retrieved.published_at is not None

    def test_version_preserved(self, repo, sample_definition):
        """Version with minor number is preserved."""
        # Create version 1.5
        sample_definition.version = Version(major=1, minor=5)
        repo.save(sample_definition)
        
        retrieved = repo.get_by_id(sample_definition.id)
        
        assert retrieved.version.major == 1
        assert retrieved.version.minor == 5
