"""
Agent Service Stats - Container and context statistics.

Handles fetching context window and container stats.
"""
import asyncio
import logging
from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException

from models import User
from database import db
from services.docker_service import get_agent_container
from services.docker_utils import container_reload, container_stats
from .helpers import get_accessible_agents

logger = logging.getLogger(__name__)


async def _fetch_single_agent_context(agent: dict, client: httpx.AsyncClient) -> dict:
    """Fetch context stats for a single agent (used for concurrent fetching)."""
    agent_name = agent["name"]
    status = agent["status"]

    # Initialize default stats
    stats = {
        "name": agent_name,
        "status": status,
        "activityState": "offline",
        "contextPercent": 0,
        "contextUsed": 0,
        "contextMax": 200000,
        "lastActivityTime": None
    }

    # Only fetch context stats for running agents
    if status != "running":
        return stats

    # Fetch context stats from agent's internal API
    try:
        container = get_agent_container(agent_name)
        if container:
            agent_url = f"http://{container.name}:8000/api/chat/session"
            response = await client.get(agent_url)
            if response.status_code == 200:
                session_data = response.json()
                stats["contextPercent"] = session_data.get("context_percent", 0)
                stats["contextUsed"] = session_data.get("context_tokens", 0)
                stats["contextMax"] = session_data.get("context_window", 200000)
    except Exception as e:
        logger.debug(f"Error fetching context stats for {agent_name}: {e}")

    # Determine active/idle state based on recent activity
    try:
        cutoff_time = (datetime.utcnow() - timedelta(seconds=60)).isoformat()
        recent_activities = db.get_agent_activities(
            agent_name=agent_name,
            limit=1
        )

        if recent_activities and len(recent_activities) > 0:
            last_activity = recent_activities[0]
            activity_time = last_activity.get("created_at")
            stats["lastActivityTime"] = activity_time

            if activity_time and activity_time > cutoff_time:
                if last_activity.get("activity_state") == "started":
                    stats["activityState"] = "active"
                else:
                    stats["activityState"] = "idle"
            else:
                stats["activityState"] = "idle"
        else:
            stats["activityState"] = "idle"
    except Exception as e:
        logger.debug(f"Error determining activity state for {agent_name}: {e}")
        stats["activityState"] = "idle"

    return stats


async def get_agents_context_stats_logic(
    current_user: User
) -> dict:
    """
    Get context window stats and activity state for all accessible agents.

    Fetches all agent stats CONCURRENTLY for better performance.

    Returns: List of agent stats with context usage and active/idle/offline state
    """
    accessible_agents = get_accessible_agents(current_user)

    # Fetch all agent stats concurrently using a shared client
    async with httpx.AsyncClient(timeout=2.0) as client:
        tasks = [_fetch_single_agent_context(agent, client) for agent in accessible_agents]
        agent_stats = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out any exceptions and keep successful results
    valid_stats = []
    for i, result in enumerate(agent_stats):
        if isinstance(result, Exception):
            logger.debug(f"Error fetching stats for agent: {result}")
            # Return default stats for failed agents
            agent = accessible_agents[i]
            valid_stats.append({
                "name": agent["name"],
                "status": agent["status"],
                "activityState": "offline" if agent["status"] != "running" else "idle",
                "contextPercent": 0,
                "contextUsed": 0,
                "contextMax": 200000,
                "lastActivityTime": None
            })
        else:
            valid_stats.append(result)

    return {"agents": valid_stats}


async def get_agent_stats_logic(
    agent_name: str,
    current_user: User
) -> dict:
    """
    Get live container stats (CPU, memory, network) for an agent.
    """
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    await container_reload(container)
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent is not running")

    try:
        stats = await container_stats(container, stream=False)

        cpu_percent = 0.0
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})

        cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - \
                    precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        system_delta = cpu_stats.get("system_cpu_usage", 0) - \
                       precpu_stats.get("system_cpu_usage", 0)

        if system_delta > 0 and cpu_delta > 0:
            num_cpus = len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", [])) or 1
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        memory_stats = stats.get("memory_stats", {})
        memory_used = memory_stats.get("usage", 0)
        memory_limit = memory_stats.get("limit", 0)
        cache = memory_stats.get("stats", {}).get("cache", 0)
        memory_used_actual = max(0, memory_used - cache)

        networks = stats.get("networks", {})
        network_rx = sum(net.get("rx_bytes", 0) for net in networks.values())
        network_tx = sum(net.get("tx_bytes", 0) for net in networks.values())

        started_at = container.attrs.get("State", {}).get("StartedAt", "")
        uptime_seconds = 0
        if started_at:
            try:
                start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00").split(".")[0])
                uptime_seconds = int((datetime.now(start_time.tzinfo) - start_time).total_seconds())
            except Exception:
                pass

        return {
            "cpu_percent": round(cpu_percent, 1),
            "memory_used_bytes": memory_used_actual,
            "memory_limit_bytes": memory_limit,
            "memory_percent": round((memory_used_actual / memory_limit * 100) if memory_limit > 0 else 0, 1),
            "network_rx_bytes": network_rx,
            "network_tx_bytes": network_tx,
            "uptime_seconds": uptime_seconds,
            "status": container.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
