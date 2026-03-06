"""
Tags API Router (ORG-001: Agent Systems & Tags).

Lightweight organizational layer for grouping agents into logical systems using tags.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from database import db
from dependencies import get_current_user, AuthorizedAgent, OwnedAgent
from db_models import User, AgentTagList, AgentTagsUpdate, AllTagsResponse, TagWithCount


router = APIRouter(prefix="/api", tags=["tags"])


# ============================================================================
# Global Tags Endpoints
# ============================================================================

@router.get("/tags", response_model=AllTagsResponse)
async def list_all_tags(current_user: User = Depends(get_current_user)):
    """
    List all unique tags with agent counts.

    Returns tags sorted by count (descending), then alphabetically.
    """
    tags = db.list_all_tags()
    return AllTagsResponse(tags=tags)


# ============================================================================
# Agent Tag Endpoints
# ============================================================================

@router.get("/agents/{name}/tags", response_model=AgentTagList)
async def get_agent_tags(name: AuthorizedAgent):
    """
    Get all tags for an agent.

    Returns tags sorted alphabetically.
    """
    tags = db.get_agent_tags(name)
    return AgentTagList(agent_name=name, tags=tags)


@router.put("/agents/{name}/tags", response_model=AgentTagList)
async def set_agent_tags(
    name: OwnedAgent,
    request: AgentTagsUpdate
):
    """
    Replace all tags for an agent.

    Only the agent owner or admin can modify tags.
    Tags are normalized (lowercase, trimmed) and deduplicated.
    """
    tags = db.set_agent_tags(name, request.tags)
    return AgentTagList(agent_name=name, tags=tags)


@router.post("/agents/{name}/tags/{tag}", response_model=AgentTagList)
async def add_agent_tag(
    name: OwnedAgent,
    tag: str
):
    """
    Add a single tag to an agent.

    Only the agent owner or admin can modify tags.
    Tag is normalized (lowercase, trimmed).
    """
    # Validate tag format
    normalized = tag.lower().strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Tag cannot be empty")
    if len(normalized) > 50:
        raise HTTPException(status_code=400, detail="Tag too long (max 50 characters)")
    if not all(c.isalnum() or c == '-' for c in normalized):
        raise HTTPException(status_code=400, detail="Tags can only contain letters, numbers, and hyphens")

    tags = db.add_agent_tag(name, tag)
    return AgentTagList(agent_name=name, tags=tags)


@router.delete("/agents/{name}/tags/{tag}", response_model=AgentTagList)
async def remove_agent_tag(
    name: OwnedAgent,
    tag: str
):
    """
    Remove a single tag from an agent.

    Only the agent owner or admin can modify tags.
    """
    tags = db.remove_agent_tag(name, tag)
    return AgentTagList(agent_name=name, tags=tags)
