"""
Skills Router - API endpoints for skills management.

Endpoints:
- GET /api/skills/library - List available skills
- GET /api/skills/library/{name} - Get skill content
- POST /api/skills/library/sync - Sync library from GitHub
- GET /api/skills/library/status - Get library status
- GET /api/agents/{name}/skills - List assigned skills
- PUT /api/agents/{name}/skills - Bulk update assignments
- POST /api/agents/{name}/skills/inject - Push skills to running agent
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException

from models import User
from dependencies import get_current_user, require_admin
from database import db
from db_models import AgentSkill, SkillInfo, AgentSkillsUpdate
from services.skill_service import skill_service

router = APIRouter(prefix="/api", tags=["skills"])


# ============================================================================
# Skills Library Endpoints
# ============================================================================

@router.get("/skills/library", response_model=List[SkillInfo])
async def list_skills(current_user: User = Depends(get_current_user)):
    """
    List all available skills from the skills library.

    Returns skills with name, description, and path.
    Content is not included for performance.
    """
    skills = skill_service.list_skills()
    return [
        SkillInfo(
            name=s["name"],
            description=s.get("description"),
            path=s["path"]
        )
        for s in skills
    ]


@router.get("/skills/library/status")
async def get_library_status(current_user: User = Depends(get_current_user)):
    """
    Get the current status of the skills library.

    Returns configuration status, sync info, and skill count.
    """
    return skill_service.get_library_status()


@router.get("/skills/library/{skill_name}")
async def get_skill(
    skill_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get details for a specific skill including full content.
    """
    skill = skill_service.get_skill(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    return skill


@router.post("/skills/library/sync")
async def sync_library(admin_user: User = Depends(require_admin)):
    """
    Sync the skills library from GitHub.

    Admin-only. Clones or pulls the configured repository.
    """
    result = skill_service.sync_library()
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Sync failed")
        )
    return result


# ============================================================================
# Agent Skills Assignment Endpoints
# ============================================================================

@router.get("/agents/{agent_name}/skills", response_model=List[AgentSkill])
async def get_agent_skills(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get skills assigned to an agent.

    Returns list of AgentSkill objects with assignment metadata.
    """
    # TODO: Add access control for shared agents
    return db.get_agent_skills(agent_name)


@router.put("/agents/{agent_name}/skills")
async def update_agent_skills(
    agent_name: str,
    update: AgentSkillsUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Bulk update skills assigned to an agent.

    Replaces all existing skill assignments with the provided list.
    """
    # TODO: Add access control (owner only)
    count = db.set_agent_skills(
        agent_name=agent_name,
        skill_names=update.skills,
        assigned_by=current_user.username
    )
    return {
        "success": True,
        "agent_name": agent_name,
        "skills_assigned": count,
        "skills": update.skills
    }


# NOTE: inject endpoint MUST be defined BEFORE {skill_name} routes
# to prevent FastAPI from matching "inject" as a skill_name parameter
@router.post("/agents/{agent_name}/skills/inject")
async def inject_skills(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Inject assigned skills into a running agent.

    Copies all assigned skills to the agent's .claude/skills/ directory.
    Agent must be running.
    """
    result = await skill_service.inject_skills(agent_name)
    if not result.get("success") and result.get("skills_failed", 0) > 0:
        # Partial success or full failure
        return result

    return result


@router.post("/agents/{agent_name}/skills/{skill_name}")
async def assign_skill(
    agent_name: str,
    skill_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Assign a single skill to an agent.
    """
    # Verify skill exists in library
    skill = skill_service.get_skill(skill_name)
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Skill '{skill_name}' not found in library"
        )

    result = db.assign_skill(agent_name, skill_name, current_user.username)
    if result is None:
        return {
            "success": True,
            "message": "Skill already assigned",
            "skill_name": skill_name
        }

    return {
        "success": True,
        "message": "Skill assigned",
        "skill": result
    }


@router.delete("/agents/{agent_name}/skills/{skill_name}")
async def unassign_skill(
    agent_name: str,
    skill_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Remove a skill assignment from an agent.
    """
    removed = db.unassign_skill(agent_name, skill_name)
    return {
        "success": True,
        "removed": removed,
        "skill_name": skill_name
    }
