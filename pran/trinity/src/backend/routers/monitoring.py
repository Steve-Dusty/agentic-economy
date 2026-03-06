"""
Monitoring API Router (MON-001).

Provides endpoints for agent health monitoring:
- Fleet-wide health status
- Individual agent health details
- Health history and trends
- Configuration management
- Manual health check triggers
"""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from database import db
from dependencies import get_current_user, require_admin, AuthorizedAgentByName
from db_models import (
    User,
    MonitoringConfig,
    FleetHealthStatus,
    FleetHealthSummary,
    AgentHealthDetail,
    AgentHealthSummary,
    HealthCheckRecord,
)
from services.monitoring_service import (
    perform_health_check,
    perform_fleet_health_check,
    get_monitoring_service,
    start_monitoring_service,
    stop_monitoring_service,
    DEFAULT_CONFIG,
)
from services.agent_service import get_accessible_agents


router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# WebSocket manager for broadcasting health events
_websocket_manager = None
_filtered_websocket_manager = None


def set_websocket_manager(manager):
    """Set the WebSocket manager for broadcasting health events."""
    global _websocket_manager
    _websocket_manager = manager


def set_filtered_websocket_manager(manager):
    """Set the filtered WebSocket manager for Trinity Connect."""
    global _filtered_websocket_manager
    _filtered_websocket_manager = manager


async def _broadcast_health_change(
    agent_name: str,
    previous_status: str,
    current_status: str,
    issues: List[str]
):
    """Broadcast a health status change event via WebSocket."""
    from utils.helpers import utc_now_iso

    event = {
        "type": "agent_health_changed",
        "agent_name": agent_name,
        "previous_status": previous_status,
        "current_status": current_status,
        "issues": issues,
        "timestamp": utc_now_iso()
    }
    event_json = json.dumps(event)

    if _websocket_manager:
        await _websocket_manager.broadcast(event_json)

    if _filtered_websocket_manager:
        await _filtered_websocket_manager.broadcast_filtered(event)


# ============================================================================
# Fleet Status Endpoints
# ============================================================================

@router.get("/status", response_model=FleetHealthStatus)
async def get_fleet_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get fleet-wide health summary.

    Returns health status for all agents the user can access.
    Admins see all agents; regular users see owned and shared agents.
    """
    # Get accessible agents
    from services.docker_service import list_all_agents_fast

    all_agents = list_all_agents_fast()
    all_agent_names = [a.name for a in all_agents]

    # Filter to accessible agents (unless admin)
    if current_user.role != "admin":
        accessible = get_accessible_agents(current_user.email, all_agent_names)
        accessible_names = {a["name"] for a in accessible}
        agent_names = [n for n in all_agent_names if n in accessible_names]
    else:
        agent_names = all_agent_names

    if not agent_names:
        return FleetHealthStatus(
            enabled=get_monitoring_service().is_running,
            last_check_at=None,
            summary=FleetHealthSummary(total_agents=0),
            agents=[]
        )

    # Get latest health checks from database
    latest_checks = db.get_all_latest_health_checks(agent_names, "aggregate")
    summary = db.get_health_summary(agent_names)

    # Build agent summaries
    agents = []
    for name in agent_names:
        check = latest_checks.get(name)
        if check:
            agents.append(AgentHealthSummary(
                name=name,
                status=check.get("status", "unknown"),
                docker_status=check.get("container_status"),
                network_reachable=check.get("reachable"),
                runtime_available=check.get("runtime_available"),
                last_check_at=check.get("checked_at"),
                issues=check.get("error_message", "").split("; ") if check.get("error_message") else []
            ))
        else:
            agents.append(AgentHealthSummary(
                name=name,
                status="unknown",
                issues=["No health check data"]
            ))

    # Sort by status severity (critical first)
    status_order = {"critical": 0, "unhealthy": 1, "degraded": 2, "unknown": 3, "healthy": 4}
    agents.sort(key=lambda a: status_order.get(a.status, 3))

    return FleetHealthStatus(
        enabled=get_monitoring_service().is_running,
        last_check_at=agents[0].last_check_at if agents else None,
        summary=FleetHealthSummary(
            total_agents=len(agent_names),
            healthy=summary.get("healthy", 0),
            degraded=summary.get("degraded", 0),
            unhealthy=summary.get("unhealthy", 0),
            critical=summary.get("critical", 0),
            unknown=summary.get("unknown", 0)
        ),
        agents=agents
    )


# ============================================================================
# Agent Health Endpoints
# ============================================================================

@router.get("/agents/{agent_name}", response_model=AgentHealthDetail)
async def get_agent_health(
    agent_name: AuthorizedAgentByName
):
    """
    Get detailed health information for a specific agent.

    Returns all layer health checks and historical metrics.
    """

    # Get latest checks for each layer
    docker_check = db.get_latest_health_check(agent_name, "docker")
    network_check = db.get_latest_health_check(agent_name, "network")
    business_check = db.get_latest_health_check(agent_name, "business")
    aggregate_check = db.get_latest_health_check(agent_name, "aggregate")

    if not aggregate_check:
        # No health data - trigger a check
        return await perform_health_check(agent_name, DEFAULT_CONFIG, store_results=True)

    # Build detailed response
    from db_models import DockerHealthCheck, NetworkHealthCheck, BusinessHealthCheck
    from utils.helpers import utc_now_iso

    docker = None
    if docker_check:
        docker = DockerHealthCheck(
            agent_name=agent_name,
            container_status=docker_check.get("container_status"),
            restart_count=docker_check.get("restart_count", 0),
            oom_killed=docker_check.get("oom_killed", False),
            cpu_percent=docker_check.get("cpu_percent"),
            memory_percent=docker_check.get("memory_percent"),
            memory_mb=docker_check.get("memory_mb"),
            checked_at=docker_check.get("checked_at", utc_now_iso())
        )

    network = None
    if network_check:
        network = NetworkHealthCheck(
            agent_name=agent_name,
            reachable=network_check.get("reachable", False),
            latency_ms=network_check.get("latency_ms"),
            error=network_check.get("error_message"),
            checked_at=network_check.get("checked_at", utc_now_iso())
        )

    business = None
    if business_check:
        business = BusinessHealthCheck(
            agent_name=agent_name,
            status=business_check.get("status", "unknown"),
            runtime_available=business_check.get("runtime_available"),
            claude_available=business_check.get("claude_available"),
            context_percent=business_check.get("context_percent"),
            active_execution_count=business_check.get("active_executions", 0),
            stuck_execution_count=0,  # Not stored directly
            recent_error_rate=business_check.get("error_rate", 0.0),
            checked_at=business_check.get("checked_at", utc_now_iso())
        )

    # Get historical metrics
    uptime = db.calculate_uptime_percent(agent_name, hours=24)
    avg_latency = db.calculate_avg_latency(agent_name, hours=24)

    # Parse issues from error_message
    issues = []
    if aggregate_check.get("error_message"):
        issues = aggregate_check["error_message"].split("; ")

    return AgentHealthDetail(
        agent_name=agent_name,
        aggregate_status=aggregate_check.get("status", "unknown"),
        last_check_at=aggregate_check.get("checked_at"),
        docker=docker,
        network=network,
        business=business,
        issues=issues,
        recent_alerts=[],  # TODO: Fetch from notifications
        uptime_percent_24h=round(uptime, 2) if uptime else None,
        avg_latency_24h_ms=round(avg_latency, 2) if avg_latency else None
    )


@router.get("/agents/{agent_name}/history")
async def get_agent_health_history(
    agent_name: AuthorizedAgentByName,
    hours: int = Query(24, ge=1, le=168),  # Max 7 days
    check_type: str = Query("aggregate", regex="^(docker|network|business|aggregate)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get health check history for an agent.

    Returns historical health checks for trend analysis.
    """
    history = db.get_agent_health_history(agent_name, check_type, hours, limit)

    return {
        "agent_name": agent_name,
        "check_type": check_type,
        "hours": hours,
        "count": len(history),
        "checks": history
    }


@router.post("/agents/{agent_name}/check", response_model=AgentHealthDetail)
async def trigger_health_check(
    agent_name: AuthorizedAgentByName,
    current_user: User = Depends(require_admin)
):
    """
    Trigger an immediate health check for an agent.

    Admin only. Forces a fresh health check regardless of schedule.
    """

    # Perform health check
    result = await perform_health_check(agent_name, DEFAULT_CONFIG, store_results=True)

    # Broadcast status if changed
    previous_check = db.get_agent_health_history(agent_name, "aggregate", hours=1, limit=2)
    if len(previous_check) > 1:
        previous_status = previous_check[1].get("status", "unknown")
        if previous_status != result.aggregate_status:
            await _broadcast_health_change(
                agent_name,
                previous_status,
                result.aggregate_status,
                result.issues
            )

    return result


# ============================================================================
# Alerts Endpoint
# ============================================================================

@router.get("/alerts")
async def get_active_alerts(
    current_user: User = Depends(require_admin),
    status: str = Query("pending", regex="^(pending|acknowledged|all)$"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Get active monitoring alerts.

    Admin only. Returns notifications with category='health'.
    """
    # Query notifications with health category
    notifications = db.list_notifications(
        status=None if status == "all" else status,
        category="health",
        limit=limit
    )

    return {
        "count": len(notifications),
        "alerts": notifications
    }


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.get("/config", response_model=MonitoringConfig)
async def get_monitoring_config(
    current_user: User = Depends(require_admin)
):
    """
    Get current monitoring configuration.

    Admin only.
    """
    # Try to get from settings
    setting = db.get_setting("monitoring_config")
    if setting and setting.value:
        try:
            import json
            config_dict = json.loads(setting.value)
            return MonitoringConfig(**config_dict)
        except Exception:
            pass

    return DEFAULT_CONFIG


@router.put("/config", response_model=MonitoringConfig)
async def update_monitoring_config(
    config: MonitoringConfig,
    current_user: User = Depends(require_admin)
):
    """
    Update monitoring configuration.

    Admin only. Changes take effect on next check cycle.
    """
    import json

    # Save to settings
    config_json = json.dumps(config.model_dump())
    db.set_setting("monitoring_config", config_json)

    # Update running service
    service = get_monitoring_service()
    service.config = config

    return config


@router.post("/enable")
async def enable_monitoring(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Enable the monitoring service.

    Admin only. Starts background health check tasks.
    """
    service = get_monitoring_service()
    if service.is_running:
        return {"status": "already_running", "message": "Monitoring service is already running"}

    # Start in background to avoid blocking
    background_tasks.add_task(start_monitoring_service)

    return {"status": "starting", "message": "Monitoring service is starting"}


@router.post("/disable")
async def disable_monitoring(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Disable the monitoring service.

    Admin only. Stops background health check tasks.
    """
    service = get_monitoring_service()
    if not service.is_running:
        return {"status": "already_stopped", "message": "Monitoring service is not running"}

    # Stop in background
    background_tasks.add_task(stop_monitoring_service)

    return {"status": "stopping", "message": "Monitoring service is stopping"}


# ============================================================================
# Batch Operations
# ============================================================================

@router.post("/check-all")
async def trigger_fleet_health_check(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Trigger health checks for all running agents.

    Admin only. Runs checks in background.
    """
    from services.docker_service import list_all_agents_fast

    agents = list_all_agents_fast()
    running_agents = [a.name for a in agents if a.status == "running"]

    if not running_agents:
        return {"status": "no_agents", "message": "No running agents to check"}

    # Run in background
    async def run_checks():
        await perform_fleet_health_check(running_agents, DEFAULT_CONFIG, store_results=True)

    background_tasks.add_task(run_checks)

    return {
        "status": "started",
        "message": f"Health checks started for {len(running_agents)} agents",
        "agents": running_agents
    }


@router.delete("/history")
async def cleanup_health_history(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(require_admin)
):
    """
    Delete old health check records.

    Admin only. Deletes records older than specified days.
    """
    deleted = db.cleanup_old_health_records(days)
    return {
        "status": "success",
        "deleted_records": deleted,
        "retention_days": days
    }
