"""
Unit tests for Process Template Service

Tests the template management functionality.
Reference: BACKLOG_ADVANCED.md - E12-01, E12-02
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone

from services.process_engine.services.templates import (
    ProcessTemplateService,
    ProcessTemplate,
    ProcessTemplateInfo,
)


class TestProcessTemplateInfo:
    """Tests for ProcessTemplateInfo dataclass."""

    def test_create_template_info(self):
        """Test creating template info."""
        info = ProcessTemplateInfo(
            id="process:content-review",
            name="content-review",
            display_name="Content Review Pipeline",
            description="Multi-step content review workflow",
            category="content",
            complexity="intermediate",
            version="1.0.0",
            author="Trinity Examples",
            tags=["content", "review", "approval"],
            step_types_used=["agent_task", "user_task", "condition"],
            source="bundled",
        )

        assert info.id == "process:content-review"
        assert info.name == "content-review"
        assert info.category == "content"
        assert "content" in info.tags
        assert "agent_task" in info.step_types_used

    def test_template_info_to_dict(self):
        """Test conversion to dictionary."""
        info = ProcessTemplateInfo(
            id="process:test",
            name="test",
            display_name="Test Template",
            description="A test template",
            category="general",
            complexity="simple",
            version="1.0.0",
            author="Test",
            tags=["test"],
            step_types_used=["agent_task"],
            source="bundled",
        )

        result = info.to_dict()

        assert result["id"] == "process:test"
        assert result["name"] == "test"
        assert result["display_name"] == "Test Template"
        assert result["source"] == "bundled"
        assert result["tags"] == ["test"]


class TestProcessTemplate:
    """Tests for ProcessTemplate dataclass."""

    def test_create_template(self):
        """Test creating a full template."""
        info = ProcessTemplateInfo(
            id="user:my-template",
            name="my-template",
            display_name="My Template",
            description="Custom template",
            category="business",
            complexity="simple",
            version="1.0.0",
            author="User",
            source="user",
        )

        template = ProcessTemplate(
            info=info,
            definition_yaml="name: my-template\nsteps: []",
            use_cases=["Example use case"],
            created_at=datetime.now(timezone.utc),
            created_by="test-user",
        )

        assert template.info.name == "my-template"
        assert "name: my-template" in template.definition_yaml
        assert len(template.use_cases) == 1

    def test_template_to_dict(self):
        """Test conversion to dictionary."""
        info = ProcessTemplateInfo(
            id="user:test",
            name="test",
            display_name="Test",
            description="Test",
            category="general",
            complexity="simple",
            version="1.0.0",
            author="Test",
            source="user",
        )

        template = ProcessTemplate(
            info=info,
            definition_yaml="name: test",
            use_cases=["Testing"],
            created_by="user@test.com",
        )

        result = template.to_dict()

        assert result["id"] == "user:test"
        assert result["definition_yaml"] == "name: test"
        assert result["use_cases"] == ["Testing"]
        assert result["created_by"] == "user@test.com"


class TestProcessTemplateService:
    """Tests for ProcessTemplateService."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        # Clean up
        os.unlink(f.name)

    @pytest.fixture
    def temp_templates_dir(self):
        """Create a temporary templates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def template_service(self, temp_db_path, temp_templates_dir):
        """Create a template service with temporary storage."""
        return ProcessTemplateService(
            templates_dir=temp_templates_dir,
            db_path=temp_db_path,
        )

    def test_service_initialization(self, template_service):
        """Test that service initializes correctly."""
        assert template_service is not None

    def test_list_templates_empty(self, template_service):
        """Test listing templates when none exist."""
        templates = template_service.list_templates()
        assert isinstance(templates, list)
        assert len(templates) == 0

    def test_create_user_template(self, template_service):
        """Test creating a user template."""
        definition = """
name: test-workflow
version: "1.0.0"
description: A test workflow

steps:
  - id: step-1
    name: First Step
    type: agent_task
    agent: test-agent
    message: Hello

outputs:
  - name: result
    value: "{{steps.step-1.output}}"
"""

        template = template_service.create_template(
            name="test-workflow",
            definition_yaml=definition,
            display_name="Test Workflow",
            description="A workflow for testing",
            category="general",
            tags=["test", "example"],
            created_by="test@example.com",
        )

        assert template is not None
        assert template.info.name == "test-workflow"
        assert template.info.display_name == "Test Workflow"
        assert template.info.source == "user"
        assert "test" in template.info.tags
        assert template.created_by == "test@example.com"

    def test_create_duplicate_template_raises(self, template_service):
        """Test that creating a duplicate template raises an error."""
        template_service.create_template(
            name="unique-template",
            definition_yaml="name: unique-template",
            created_by="user@test.com",
        )

        with pytest.raises(ValueError, match="already exists"):
            template_service.create_template(
                name="unique-template",
                definition_yaml="name: unique-template",
                created_by="user@test.com",
            )

    def test_get_user_template(self, template_service):
        """Test retrieving a user template."""
        # Create template
        template_service.create_template(
            name="my-template",
            definition_yaml="name: my-template\nsteps: []",
            display_name="My Template",
            description="Description",
            category="business",
        )

        # Retrieve it
        template = template_service.get_template("user:my-template")

        assert template is not None
        assert template.info.name == "my-template"
        assert template.info.category == "business"

    def test_get_nonexistent_template(self, template_service):
        """Test retrieving a template that doesn't exist."""
        template = template_service.get_template("user:nonexistent")
        assert template is None

    def test_list_user_templates(self, template_service):
        """Test listing user-created templates."""
        # Create multiple templates
        template_service.create_template(
            name="template-1",
            definition_yaml="name: template-1",
            category="business",
        )
        template_service.create_template(
            name="template-2",
            definition_yaml="name: template-2",
            category="devops",
        )

        templates = template_service.list_templates(source="user")

        assert len(templates) == 2

    def test_list_templates_by_category(self, template_service):
        """Test filtering templates by category."""
        # Create templates in different categories
        template_service.create_template(
            name="biz-template",
            definition_yaml="name: biz-template",
            category="business",
        )
        template_service.create_template(
            name="ops-template",
            definition_yaml="name: ops-template",
            category="devops",
        )

        # Filter by category
        business_templates = template_service.list_templates(category="business")

        assert len(business_templates) == 1
        assert business_templates[0].category == "business"

    def test_delete_user_template(self, template_service):
        """Test deleting a user template."""
        # Create template
        template_service.create_template(
            name="to-delete",
            definition_yaml="name: to-delete",
        )

        # Verify it exists
        assert template_service.get_template("user:to-delete") is not None

        # Delete it
        result = template_service.delete_template("to-delete")
        assert result is True

        # Verify it's gone
        assert template_service.get_template("user:to-delete") is None

    def test_delete_nonexistent_template(self, template_service):
        """Test deleting a template that doesn't exist."""
        result = template_service.delete_template("nonexistent")
        assert result is False

    def test_template_extracts_step_types(self, template_service):
        """Test that template creation extracts step types from definition."""
        definition = """
name: multi-step
steps:
  - id: step-1
    type: agent_task
  - id: step-2
    type: condition
  - id: step-3
    type: user_task
"""

        template = template_service.create_template(
            name="multi-step",
            definition_yaml=definition,
        )

        # Step types should be extracted
        assert "agent_task" in template.info.step_types_used
        assert "condition" in template.info.step_types_used
        assert "user_task" in template.info.step_types_used


class TestBundledTemplates:
    """Tests for bundled template loading."""

    @pytest.fixture
    def temp_templates_dir(self):
        """Create a temporary templates directory with bundled templates."""
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a sample bundled template
            template_dir = os.path.join(tmpdir, "sample-template")
            os.makedirs(template_dir)

            # Write template.yaml
            template_meta = {
                "name": "sample-template",
                "display_name": "Sample Template",
                "description": "A sample bundled template",
                "category": "general",
                "complexity": "simple",
                "version": "1.0.0",
                "author": "Test",
                "tags": ["sample"],
                "step_types_used": ["agent_task"],
            }
            with open(os.path.join(template_dir, "template.yaml"), "w") as f:
                yaml.dump(template_meta, f)

            # Write definition.yaml
            with open(os.path.join(template_dir, "definition.yaml"), "w") as f:
                f.write("name: sample-template\nsteps: []")

            yield tmpdir

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        os.unlink(f.name)

    def test_load_bundled_templates(self, temp_templates_dir, temp_db_path):
        """Test loading templates from the templates directory."""
        service = ProcessTemplateService(
            templates_dir=temp_templates_dir,
            db_path=temp_db_path,
        )

        templates = service.list_templates(source="bundled")

        assert len(templates) == 1
        assert templates[0].name == "sample-template"
        assert templates[0].source == "bundled"

    def test_get_bundled_template(self, temp_templates_dir, temp_db_path):
        """Test retrieving a bundled template."""
        service = ProcessTemplateService(
            templates_dir=temp_templates_dir,
            db_path=temp_db_path,
        )

        template = service.get_template("process:sample-template")

        assert template is not None
        assert template.info.name == "sample-template"
        assert template.definition_yaml == "name: sample-template\nsteps: []"


class TestTemplateIdFormats:
    """Tests for template ID format handling."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def template_service(self, temp_db_path):
        """Create a template service."""
        with tempfile.TemporaryDirectory() as tmpdir:
            return ProcessTemplateService(
                templates_dir=tmpdir,
                db_path=temp_db_path,
            )

    def test_user_template_id_format(self, template_service):
        """Test that user templates get correct ID format."""
        template_service.create_template(
            name="my-template",
            definition_yaml="name: my-template",
        )

        templates = template_service.list_templates()

        assert any(t.id == "user:my-template" for t in templates)

    def test_get_template_with_prefix(self, template_service):
        """Test getting template with user: prefix."""
        template_service.create_template(
            name="prefixed",
            definition_yaml="name: prefixed",
        )

        template = template_service.get_template("user:prefixed")
        assert template is not None
        assert template.info.name == "prefixed"

    def test_get_template_without_prefix(self, template_service):
        """Test getting template without prefix (falls back to user)."""
        template_service.create_template(
            name="no-prefix",
            definition_yaml="name: no-prefix",
        )

        template = template_service.get_template("no-prefix")
        assert template is not None
        assert template.info.name == "no-prefix"
