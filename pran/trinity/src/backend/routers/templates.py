"""
Template routes for the Trinity backend.
"""
from fastapi import APIRouter, Depends, HTTPException

from models import User
from dependencies import get_current_user
from services.template_service import (
    get_all_templates,
    get_github_template,
)

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def list_templates(current_user: User = Depends(get_current_user)):
    """List available agent templates (GitHub-based, metadata from repo)."""
    templates = get_all_templates()
    templates.sort(key=lambda t: (t.get("priority", 100), t.get("display_name", "")))
    return templates


@router.get("/{template_id:path}")
async def get_template(template_id: str, current_user: User = Depends(get_current_user)):
    """Get template details.

    Note: Uses {template_id:path} to capture full path including slashes,
    which is needed for GitHub template IDs like 'github:org/repo'.
    """
    if template_id.startswith("github:"):
        gh_template = get_github_template(template_id)
        if gh_template:
            return gh_template

    raise HTTPException(status_code=404, detail="Template not found")
