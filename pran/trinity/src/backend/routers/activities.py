"""
Activities Router

Cross-agent activity timeline and queries.
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from database import db
from dependencies import get_current_user
from models import User

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("/timeline")
async def get_activity_timeline(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    activity_types: Optional[str] = Query(None, description="Comma-separated list of activity types"),
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    Get cross-agent activity timeline with access control.

    Only returns activities for agents the user can access.
    """
    # Parse activity types
    types_list = None
    if activity_types:
        types_list = [t.strip() for t in activity_types.split(',')]

    # Get all activities
    all_activities = db.get_activities_in_range(
        start_time=start_time,
        end_time=end_time,
        activity_types=types_list,
        limit=limit * 2  # Get more than needed for filtering
    )

    # Get accessible agents for this user
    from routers.agents import get_accessible_agents
    accessible_agents = get_accessible_agents(current_user)
    accessible_agent_names = {agent['name'] for agent in accessible_agents}

    # Filter activities to only include accessible agents
    filtered_activities = [
        activity for activity in all_activities
        if activity['agent_name'] in accessible_agent_names
    ][:limit]

    return {
        "count": len(filtered_activities),
        "activities": filtered_activities
    }
