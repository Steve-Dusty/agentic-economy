"""
Process Templates API Router

Provides REST API endpoints for managing process templates.
Reference: BACKLOG_ADVANCED.md - E12-01, E12-02

Part of the Process-Driven Platform feature.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from dependencies import get_current_user, CurrentUser
from services.process_engine.services.templates import ProcessTemplateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/process-templates", tags=["process-templates"])


# =============================================================================
# Pydantic Models
# =============================================================================


class TemplateInfoResponse(BaseModel):
    """Template summary info."""
    id: str
    name: str
    display_name: str
    description: str
    category: str
    complexity: str
    version: str
    author: str
    tags: List[str]
    step_types_used: List[str]
    source: str


class TemplateDetailResponse(BaseModel):
    """Full template with definition."""
    id: str
    name: str
    display_name: str
    description: str
    category: str
    complexity: str
    version: str
    author: str
    tags: List[str]
    step_types_used: List[str]
    source: str
    definition_yaml: str
    use_cases: List[str]
    created_at: Optional[str]
    created_by: Optional[str]


class TemplateListResponse(BaseModel):
    """Response for listing templates."""
    templates: List[TemplateInfoResponse]
    total: int


class CreateTemplateRequest(BaseModel):
    """Request body for creating a template."""
    name: str = Field(..., min_length=1, max_length=100, description="Template name (slug)")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field(default="general", description="Category")
    complexity: str = Field(default="simple", description="Complexity level")
    tags: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    definition_yaml: str = Field(..., description="Process definition YAML")


class UseTemplateRequest(BaseModel):
    """Request body for creating a process from template."""
    name: str = Field(..., min_length=1, description="New process name")


# =============================================================================
# Service Instance
# =============================================================================


_template_service: Optional[ProcessTemplateService] = None


def get_template_service() -> ProcessTemplateService:
    """Get or create the template service."""
    global _template_service
    if _template_service is None:
        _template_service = ProcessTemplateService()
    return _template_service


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    current_user: CurrentUser,
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source (bundled, user)"),
):
    """
    List all available process templates.

    Templates can be filtered by category (business, devops, analytics, etc.)
    and source (bundled, user, community).
    """
    service = get_template_service()
    templates = service.list_templates(category=category, source=source)

    return TemplateListResponse(
        templates=[TemplateInfoResponse(**t.to_dict()) for t in templates],
        total=len(templates),
    )


# NOTE: /categories must be defined BEFORE /{template_id:path} to avoid route conflict
@router.get("/categories")
async def list_categories(
    current_user: CurrentUser,
):
    """
    Get list of available template categories.
    """
    return {
        "categories": [
            {"id": "general", "name": "General", "description": "General-purpose workflows"},
            {"id": "business", "name": "Business", "description": "Business process automation"},
            {"id": "devops", "name": "DevOps", "description": "Development and operations"},
            {"id": "analytics", "name": "Analytics", "description": "Data analysis workflows"},
            {"id": "support", "name": "Support", "description": "Customer support workflows"},
            {"id": "content", "name": "Content", "description": "Content creation pipelines"},
        ]
    }


# NOTE: Routes with /preview and /use MUST be defined BEFORE /{template_id:path}
# because :path matches everything including /preview
@router.get("/{template_id:path}/preview")
async def get_template_preview(
    template_id: str,
    current_user: CurrentUser,
):
    """
    Get template definition YAML for preview.

    Returns just the YAML content for display in the editor.
    """
    service = get_template_service()
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "template_id": template_id,
        "name": template.info.display_name,
        "yaml_content": template.definition_yaml,
    }


@router.post("/{template_id:path}/use")
async def use_template(
    template_id: str,
    request: UseTemplateRequest,
    current_user: CurrentUser,
):
    """
    Create a new process from a template.

    Creates a draft process definition with the template's YAML,
    customized with the provided name.
    """
    from .processes import get_repository, get_validator, publish_event
    from services.process_engine.domain import ProcessCreated
    import re

    service = get_template_service()
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Customize the YAML with the new process name
    yaml_content = template.definition_yaml

    # Replace template placeholders if any
    yaml_content = yaml_content.replace("{{name}}", request.name)
    yaml_content = yaml_content.replace("{{process_name}}", request.name)

    # Also replace the name field directly if it exists
    yaml_content = re.sub(
        r'^name:\s*.+$',
        f'name: {request.name}',
        yaml_content,
        flags=re.MULTILINE,
    )

    # Validate and create the process
    validator = get_validator()
    result = validator.validate_yaml(yaml_content, created_by=current_user.email)

    if not result.is_valid:
        error_messages = [e.message for e in result.errors]
        raise HTTPException(
            status_code=422,
            detail={"message": "Template validation failed", "errors": error_messages}
        )

    definition = result.definition
    if definition is None:
        raise HTTPException(status_code=500, detail="Validation passed but no definition created")

    # Save to repository
    repo = get_repository()
    repo.save(definition)

    logger.info(f"Process '{definition.name}' created from template '{template_id}' by {current_user.email}")

    # Emit domain event
    await publish_event(ProcessCreated(
        process_id=definition.id,
        process_name=definition.name,
        version=definition.version.major,
        created_by=current_user.email,
    ))

    return {
        "message": "Process created from template",
        "process_id": str(definition.id),
        "process_name": definition.name,
        "template_id": template_id,
    }


@router.post("", response_model=TemplateDetailResponse)
async def create_template(
    request: CreateTemplateRequest,
    current_user: CurrentUser,
):
    """
    Create a new user template.

    Creates a template from the provided process definition YAML.
    """
    service = get_template_service()

    try:
        template = service.create_template(
            name=request.name,
            definition_yaml=request.definition_yaml,
            display_name=request.display_name,
            description=request.description,
            category=request.category,
            complexity=request.complexity,
            tags=request.tags,
            use_cases=request.use_cases,
            created_by=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TemplateDetailResponse(**template.to_dict())


# NOTE: This catch-all route MUST be defined LAST - after /preview, /use, and other specific routes
@router.get("/{template_id:path}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: str,
    current_user: CurrentUser,
):
    """
    Get a template by ID.

    Template IDs are formatted as "process:name" for bundled templates
    or "user:name" for user-created templates.
    """
    service = get_template_service()
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateDetailResponse(**template.to_dict())


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user: CurrentUser,
):
    """
    Delete a user-created template.

    Only user templates can be deleted. Bundled templates cannot be deleted.
    """
    if template_id.startswith("process:"):
        raise HTTPException(status_code=400, detail="Cannot delete bundled templates")

    # Extract name from ID
    name = template_id
    if template_id.startswith("user:"):
        name = template_id[5:]

    service = get_template_service()
    success = service.delete_template(name)

    if not success:
        raise HTTPException(status_code=404, detail="Template not found")

    logger.info(f"Template '{name}' deleted by {current_user.email}")

    return {"message": "Template deleted", "template_id": template_id}
