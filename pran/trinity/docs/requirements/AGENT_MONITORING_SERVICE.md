# Agent Monitoring Service (MON-001)

> **Status**: Draft
> **Priority**: HIGH
> **Author**: Claude
> **Created**: 2026-02-23
> **Related**: NOTIF-001 (Notifications), OBS-011/OBS-012 (Host Telemetry)

## Overview

A comprehensive monitoring service that performs health checks on agent infrastructure at multiple levels: Docker container status, network reachability, and business logic health. Issues are reported through the existing notification system and displayed on a dedicated Monitoring page.

## Problem Statement

Currently, Trinity lacks proactive monitoring of agent health:
- No automated detection of unresponsive agents
- No alerting when agents become unreachable
- No visibility into agent health trends
- Manual inspection required to discover issues
- No centralized view of fleet health status

## Goals

1. **Proactive Issue Detection**: Automatically detect and report agent health issues
2. **Multi-Layer Health Checks**: Monitor Docker, network, and application layers
3. **Integration with Notifications**: Leverage NOTIF-001 for alert delivery
4. **Historical Tracking**: Store health check results for trend analysis
5. **Configurable Thresholds**: Allow customization of check intervals and alert thresholds
6. **Fleet Overview UI**: Dedicated page showing health status across all agents

## Non-Goals

- External monitoring integration (Prometheus, Datadog) - future enhancement
- Agent auto-recovery/self-healing - separate feature
- Cost-based alerting - handled by Process Engine analytics
- Log-based anomaly detection - separate feature

---

## Architecture

### Health Check Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent Monitoring Service                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │  Layer 1: Docker │  │ Layer 2: Network │  │ Layer 3: Business│      │
│  │   (Container)    │  │  (Reachability)  │  │     (Logic)      │      │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤      │
│  │ • Running state  │  │ • HTTP /health   │  │ • API /health    │      │
│  │ • Exit codes     │  │ • TCP port 8000  │  │ • Runtime avail  │      │
│  │ • Restart count  │  │ • Response time  │  │ • Session state  │      │
│  │ • OOM kills      │  │ • Timeout detect │  │ • Context usage  │      │
│  │ • Resource usage │  │                  │  │ • Error rates    │      │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘      │
│           │                     │                     │                 │
│           └─────────────────────┴─────────────────────┘                 │
│                                 │                                        │
│                    ┌────────────▼────────────┐                          │
│                    │   Health Aggregator     │                          │
│                    │  (Compute final status) │                          │
│                    └────────────┬────────────┘                          │
│                                 │                                        │
│           ┌─────────────────────┼─────────────────────┐                 │
│           ▼                     ▼                     ▼                 │
│  ┌─────────────────┐   ┌───────────────┐   ┌──────────────────┐        │
│  │ Database Store  │   │ Notification  │   │ WebSocket        │        │
│  │ (History)       │   │ System        │   │ Broadcast        │        │
│  └─────────────────┘   └───────────────┘   └──────────────────┘        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Service Design

The monitoring service runs as a background task within the backend (similar to how host telemetry works), not as a separate container. This keeps the architecture simple while providing:

- Configurable check intervals per layer
- Parallel health checks across all agents
- Threshold-based alerting with notification integration
- Historical data storage for trend analysis

---

## Functional Requirements

### FR1: Docker Layer Health Checks

Monitor container infrastructure status via Docker API.

**Checks**:
| Check | Source | Frequency | Alert Condition |
|-------|--------|-----------|-----------------|
| Container State | `container.status` | 30s | Not "running" when expected |
| Exit Code | `container.attrs['State']['ExitCode']` | 30s | Non-zero exit code |
| Restart Count | `container.attrs['RestartCount']` | 30s | > 3 restarts in 10 min |
| OOM Killed | `container.attrs['State']['OOMKilled']` | 30s | True |
| CPU Usage | `container.stats()` | 60s | > 90% sustained 5 min |
| Memory Usage | `container.stats()` | 60s | > 95% of limit |

**Data Model**:
```python
class DockerHealthCheck:
    agent_name: str
    container_status: str  # running, stopped, paused, restarting
    exit_code: int | None
    restart_count: int
    oom_killed: bool
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    checked_at: datetime
```

### FR2: Network Layer Health Checks

Verify agents are reachable on the internal Docker network.

**Checks**:
| Check | Method | Frequency | Alert Condition |
|-------|--------|-----------|-----------------|
| HTTP Reachability | `GET /health` | 30s | No response / timeout |
| Response Time | HTTP latency | 30s | > 5s latency |
| TCP Port | Socket connect 8000 | 30s | Connection refused |

**Implementation**:
```python
async def check_network_health(agent_name: str) -> NetworkHealthCheck:
    url = f"http://agent-{agent_name}:8000/health"
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            latency_ms = (time.monotonic() - start) * 1000
            return NetworkHealthCheck(
                agent_name=agent_name,
                reachable=True,
                status_code=response.status_code,
                latency_ms=latency_ms,
                checked_at=utc_now_iso()
            )
    except Exception as e:
        return NetworkHealthCheck(
            agent_name=agent_name,
            reachable=False,
            error=str(e),
            checked_at=utc_now_iso()
        )
```

**Data Model**:
```python
class NetworkHealthCheck:
    agent_name: str
    reachable: bool
    status_code: int | None
    latency_ms: float | None
    error: str | None
    checked_at: datetime
```

### FR3: Business Logic Health Checks

Verify agent application state and runtime availability.

**Checks**:
| Check | Source | Frequency | Alert Condition |
|-------|--------|-----------|-----------------|
| Runtime Available | `/health` response | 60s | `runtime_available: false` |
| Claude Available | `/health` response | 60s | `claude_available: false` |
| Context Usage | `/api/chat/session` | 60s | > 95% context window |
| Active Execution | `/api/executions/running` | 60s | Stuck > 30 min |
| Error Rate | Activity stream | 5 min | > 50% failures in window |

**Existing Endpoint Response** (agent internal `/health`):
```json
{
  "status": "healthy",
  "agent_name": "my-agent",
  "runtime": "claude-code",
  "runtime_available": true,
  "claude_available": true,
  "message_count": 42
}
```

**Extended Business Health Model**:
```python
class BusinessHealthCheck:
    agent_name: str
    status: str  # healthy, degraded, unhealthy
    runtime_available: bool
    claude_available: bool
    context_percent: float | None
    active_execution_count: int
    stuck_execution_count: int
    recent_error_rate: float  # 0.0 - 1.0
    checked_at: datetime
```

### FR4: Health Aggregation

Combine all layers into a single health status per agent.

**Aggregation Logic**:
```python
def aggregate_health(docker: DockerHealthCheck,
                     network: NetworkHealthCheck,
                     business: BusinessHealthCheck) -> AgentHealthStatus:
    """
    Priority: Docker > Network > Business

    Status levels:
    - healthy: All checks pass
    - degraded: Minor issues (high latency, high resource usage)
    - unhealthy: Major issues (unreachable, runtime unavailable)
    - critical: Container not running or OOM killed
    """

    # Critical: Docker layer failures
    if docker.container_status != "running":
        return AgentHealthStatus.CRITICAL
    if docker.oom_killed:
        return AgentHealthStatus.CRITICAL

    # Unhealthy: Network or runtime failures
    if not network.reachable:
        return AgentHealthStatus.UNHEALTHY
    if not business.runtime_available:
        return AgentHealthStatus.UNHEALTHY

    # Degraded: Performance issues
    if docker.cpu_percent > 90 or docker.memory_percent > 95:
        return AgentHealthStatus.DEGRADED
    if network.latency_ms > 5000:
        return AgentHealthStatus.DEGRADED
    if business.context_percent > 95:
        return AgentHealthStatus.DEGRADED
    if business.recent_error_rate > 0.5:
        return AgentHealthStatus.DEGRADED

    return AgentHealthStatus.HEALTHY
```

**Health Status Enum**:
```python
class AgentHealthStatus(str, Enum):
    HEALTHY = "healthy"      # All systems operational
    DEGRADED = "degraded"    # Performance issues, still functional
    UNHEALTHY = "unhealthy"  # Major issues, may not respond
    CRITICAL = "critical"    # Container down or crashed
    UNKNOWN = "unknown"      # Unable to determine status
```

### FR5: Notification Integration

Send alerts via existing notification system (NOTIF-001).

**Alert Triggers**:
| Condition | Notification Type | Priority | Cooldown |
|-----------|-------------------|----------|----------|
| Status → CRITICAL | alert | urgent | 5 min |
| Status → UNHEALTHY | alert | high | 10 min |
| Status → DEGRADED | alert | normal | 30 min |
| Status → HEALTHY (from unhealthy) | info | normal | none |
| High restart count | alert | high | 15 min |
| OOM killed | alert | urgent | 5 min |
| Stuck execution | alert | high | 30 min |

**Notification Payload**:
```python
await send_notification(
    notification_type="alert",
    title=f"Agent {agent_name} is {status}",
    message=f"Health check failed: {failure_reason}",
    priority="high",
    category="health",
    metadata={
        "agent_name": agent_name,
        "previous_status": "healthy",
        "current_status": "unhealthy",
        "failure_layer": "network",
        "failure_detail": "HTTP timeout after 10s",
        "check_timestamp": "2026-02-23T10:30:00Z"
    }
)
```

**Cooldown Implementation**:
Store last alert timestamp per agent+condition to prevent alert storms.

### FR6: Historical Data Storage

Persist health check results for trend analysis.

**Database Schema**:
```sql
CREATE TABLE agent_health_checks (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    check_type TEXT NOT NULL,        -- docker, network, business, aggregate
    status TEXT NOT NULL,            -- healthy, degraded, unhealthy, critical

    -- Docker metrics
    container_status TEXT,
    cpu_percent REAL,
    memory_percent REAL,
    memory_mb REAL,
    restart_count INTEGER,
    oom_killed INTEGER,              -- 0 or 1

    -- Network metrics
    reachable INTEGER,               -- 0 or 1
    latency_ms REAL,

    -- Business metrics
    runtime_available INTEGER,       -- 0 or 1
    claude_available INTEGER,        -- 0 or 1
    context_percent REAL,
    active_executions INTEGER,
    error_rate REAL,

    -- Metadata
    error_message TEXT,
    checked_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_health_agent_time ON agent_health_checks(agent_name, checked_at DESC);
CREATE INDEX idx_health_status ON agent_health_checks(status);
CREATE INDEX idx_health_type ON agent_health_checks(check_type);

-- Retention: Keep detailed data for 7 days, aggregated for 90 days
-- Cleanup job runs daily at 3 AM UTC
```

**Retention Policy**:
- Raw health checks: 7 days
- Hourly aggregates: 90 days
- Daily aggregates: 1 year

### FR7: Monitoring Configuration

Allow admin configuration of monitoring parameters.

**Configuration Model**:
```python
class MonitoringConfig:
    # Enable/disable monitoring
    enabled: bool = True

    # Check intervals (seconds)
    docker_check_interval: int = 30
    network_check_interval: int = 30
    business_check_interval: int = 60

    # Timeouts
    http_timeout: float = 10.0
    tcp_timeout: float = 5.0

    # Thresholds
    cpu_warning_percent: float = 80.0
    cpu_critical_percent: float = 95.0
    memory_warning_percent: float = 85.0
    memory_critical_percent: float = 95.0
    latency_warning_ms: float = 2000.0
    latency_critical_ms: float = 5000.0
    context_warning_percent: float = 85.0
    context_critical_percent: float = 95.0
    error_rate_warning: float = 0.3
    error_rate_critical: float = 0.5

    # Alert cooldowns (seconds)
    critical_cooldown: int = 300      # 5 min
    unhealthy_cooldown: int = 600     # 10 min
    degraded_cooldown: int = 1800     # 30 min

    # Stuck execution threshold (seconds)
    stuck_execution_threshold: int = 1800  # 30 min
```

**Storage**: `platform_settings` table (existing) with key `monitoring_config`.

**API Endpoints**:
- `GET /api/monitoring/config` - Get current config (admin)
- `PUT /api/monitoring/config` - Update config (admin)

---

## REST API Endpoints

### Monitoring Status

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/monitoring/status` | Admin | Fleet-wide health summary |
| GET | `/api/monitoring/agents/{name}` | Auth | Single agent health details |
| GET | `/api/monitoring/agents/{name}/history` | Auth | Health check history |
| GET | `/api/monitoring/alerts` | Admin | Active alerts (unresolved) |
| POST | `/api/monitoring/agents/{name}/check` | Admin | Trigger immediate check |

### Configuration

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/monitoring/config` | Admin | Get monitoring configuration |
| PUT | `/api/monitoring/config` | Admin | Update configuration |
| POST | `/api/monitoring/enable` | Admin | Enable monitoring service |
| POST | `/api/monitoring/disable` | Admin | Disable monitoring service |

### Response Models

**Fleet Status Response** (`GET /api/monitoring/status`):
```json
{
  "enabled": true,
  "last_check_at": "2026-02-23T10:30:00Z",
  "summary": {
    "total_agents": 12,
    "healthy": 9,
    "degraded": 2,
    "unhealthy": 1,
    "critical": 0,
    "unknown": 0
  },
  "agents": [
    {
      "name": "research-agent",
      "status": "healthy",
      "docker_status": "running",
      "network_reachable": true,
      "runtime_available": true,
      "last_check_at": "2026-02-23T10:30:00Z",
      "issues": []
    },
    {
      "name": "writer-agent",
      "status": "degraded",
      "docker_status": "running",
      "network_reachable": true,
      "runtime_available": true,
      "last_check_at": "2026-02-23T10:30:00Z",
      "issues": ["High CPU usage (92%)"]
    },
    {
      "name": "broken-agent",
      "status": "unhealthy",
      "docker_status": "running",
      "network_reachable": false,
      "runtime_available": null,
      "last_check_at": "2026-02-23T10:30:00Z",
      "issues": ["HTTP timeout after 10s"]
    }
  ]
}
```

**Agent Health Detail** (`GET /api/monitoring/agents/{name}`):
```json
{
  "agent_name": "research-agent",
  "aggregate_status": "healthy",
  "last_check_at": "2026-02-23T10:30:00Z",
  "checks": {
    "docker": {
      "status": "healthy",
      "container_status": "running",
      "cpu_percent": 45.2,
      "memory_percent": 62.1,
      "memory_mb": 512.4,
      "restart_count": 0,
      "oom_killed": false,
      "checked_at": "2026-02-23T10:30:00Z"
    },
    "network": {
      "status": "healthy",
      "reachable": true,
      "latency_ms": 45.2,
      "status_code": 200,
      "checked_at": "2026-02-23T10:30:00Z"
    },
    "business": {
      "status": "healthy",
      "runtime_available": true,
      "claude_available": true,
      "context_percent": 45.5,
      "active_executions": 1,
      "stuck_executions": 0,
      "recent_error_rate": 0.05,
      "checked_at": "2026-02-23T10:30:00Z"
    }
  },
  "recent_alerts": [
    {
      "id": "notif_abc123",
      "title": "Agent research-agent recovered",
      "priority": "normal",
      "created_at": "2026-02-23T09:15:00Z"
    }
  ],
  "uptime_percent_24h": 99.8,
  "avg_latency_24h_ms": 52.3
}
```

---

## WebSocket Events

Real-time health status updates via existing WebSocket infrastructure.

**Event: `agent_health_changed`**
```json
{
  "type": "agent_health_changed",
  "agent_name": "research-agent",
  "previous_status": "healthy",
  "current_status": "degraded",
  "issues": ["High CPU usage (92%)"],
  "timestamp": "2026-02-23T10:30:00Z"
}
```

**Event: `monitoring_alert`**
```json
{
  "type": "monitoring_alert",
  "notification_id": "notif_xyz789",
  "agent_name": "broken-agent",
  "alert_type": "unreachable",
  "priority": "high",
  "title": "Agent broken-agent is unhealthy",
  "timestamp": "2026-02-23T10:30:00Z"
}
```

**Broadcasting**:
- Use `WebSocketManager.broadcast()` for all clients
- Use `FilteredWebSocketManager.broadcast_filtered()` for Trinity Connect (filtered by agent access)

---

## MCP Tools

Extend MCP server with monitoring tools for programmatic access.

### `get_fleet_health`

Get health status for all accessible agents.

**Parameters**: None

**Returns**:
```json
{
  "summary": {
    "healthy": 9,
    "degraded": 2,
    "unhealthy": 1,
    "critical": 0
  },
  "agents": [
    {"name": "agent-a", "status": "healthy"},
    {"name": "agent-b", "status": "degraded", "issues": ["High memory"]}
  ]
}
```

### `get_agent_health`

Get detailed health for a specific agent.

**Parameters**:
- `agent_name` (required): Target agent name

**Returns**: Same as `GET /api/monitoring/agents/{name}` response

### `trigger_health_check`

Force immediate health check for an agent.

**Parameters**:
- `agent_name` (required): Target agent name

**Returns**:
```json
{
  "agent_name": "research-agent",
  "status": "healthy",
  "checked_at": "2026-02-23T10:30:00Z"
}
```

---

## Frontend UI

### Monitoring Page (`/monitoring`)

New dedicated page for fleet health visibility.

**Route**: `/monitoring`
**Auth**: Authenticated users (admin sees all, users see accessible agents)
**Navigation**: Add "Monitoring" to main navigation (between "Agents" and "Files")

#### Page Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Monitoring                                              [⚙️ Configure]  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │   ✅ 9     │  │   ⚠️ 2     │  │   ❌ 1     │  │   💀 0     │        │
│  │  Healthy   │  │  Degraded  │  │ Unhealthy  │  │  Critical  │        │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘        │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Active Alerts (3)                                      [Clear All] │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │ 🔴 broken-agent      HTTP timeout after 10s          2 min ago    │ │
│  │ 🟡 writer-agent      High CPU usage (92%)            5 min ago    │ │
│  │ 🟡 data-agent        Context at 96%                  12 min ago   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Agent Health Grid                           [Filter ▾] [Refresh]  │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │                                                                    │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │ │
│  │  │ research-agent   │  │ writer-agent     │  │ broken-agent     │ │ │
│  │  │ ✅ Healthy       │  │ ⚠️ Degraded      │  │ ❌ Unhealthy     │ │ │
│  │  │                  │  │                  │  │                  │ │ │
│  │  │ CPU: ████░░ 45%  │  │ CPU: █████░ 92%  │  │ ── Unreachable   │ │ │
│  │  │ MEM: ███░░░ 62%  │  │ MEM: ████░░ 78%  │  │ Last seen: 5m    │ │ │
│  │  │ CTX: ████░░ 45%  │  │ CTX: ███░░░ 55%  │  │                  │ │ │
│  │  │                  │  │                  │  │                  │ │ │
│  │  │ Latency: 45ms    │  │ Latency: 120ms   │  │ Timeout: 10s     │ │ │
│  │  │ Uptime: 99.9%    │  │ Uptime: 98.5%    │  │ Uptime: 85.2%    │ │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘ │ │
│  │                                                                    │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │ │
│  │  │ data-agent       │  │ system-agent     │  │ ...              │ │ │
│  │  │ ⚠️ Degraded      │  │ ✅ Healthy       │  │                  │ │ │
│  │  │ ...              │  │ ...              │  │                  │ │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Components

**MonitoringPage.vue** (main page):
- Summary cards (healthy/degraded/unhealthy/critical counts)
- Active alerts panel with dismiss/acknowledge actions
- Agent health grid with filtering (by status, by tag)
- Auto-refresh every 30 seconds
- Manual refresh button

**AgentHealthCard.vue** (reusable card):
- Agent name with status badge
- Progress bars for CPU, Memory, Context
- Latency display
- 24h uptime percentage
- Click to navigate to agent detail

**MonitoringConfigModal.vue** (admin only):
- Toggle monitoring on/off
- Adjust check intervals
- Set threshold values
- Configure alert cooldowns

**HealthStatusBadge.vue** (reusable badge):
- Color-coded status indicator
- Healthy: green
- Degraded: yellow/amber
- Unhealthy: red
- Critical: dark red with pulse

#### State Management

**stores/monitoring.js** (Pinia store):
```javascript
export const useMonitoringStore = defineStore('monitoring', {
  state: () => ({
    enabled: true,
    lastCheck: null,
    summary: { healthy: 0, degraded: 0, unhealthy: 0, critical: 0 },
    agents: [],
    alerts: [],
    config: null,
    loading: false,
    error: null
  }),

  actions: {
    async fetchStatus() { /* GET /api/monitoring/status */ },
    async fetchAgentHealth(name) { /* GET /api/monitoring/agents/{name} */ },
    async updateConfig(config) { /* PUT /api/monitoring/config */ },
    async triggerCheck(name) { /* POST /api/monitoring/agents/{name}/check */ }
  },

  getters: {
    unhealthyAgents: (state) => state.agents.filter(a =>
      ['unhealthy', 'critical'].includes(a.status)
    ),
    hasActiveAlerts: (state) => state.alerts.length > 0
  }
})
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Backend)

1. **Database Schema**
   - Add `agent_health_checks` table
   - Add migration function
   - Add indexes

2. **Health Check Service** (`src/backend/services/monitoring_service.py`)
   - Docker health check function
   - Network health check function
   - Business logic health check function
   - Aggregation logic
   - Background task scheduler

3. **REST API** (`src/backend/routers/monitoring.py`)
   - Status endpoints
   - Configuration endpoints
   - Manual trigger endpoint

### Phase 2: Notification Integration

4. **Alert Service** (`src/backend/services/monitoring_alerts.py`)
   - Threshold evaluation
   - Cooldown tracking
   - Notification creation
   - Recovery detection

5. **WebSocket Events**
   - Add `agent_health_changed` event type
   - Add `monitoring_alert` event type
   - Integrate with existing broadcast infrastructure

### Phase 3: Frontend UI

6. **Monitoring Page**
   - MonitoringPage.vue
   - AgentHealthCard.vue
   - MonitoringConfigModal.vue
   - HealthStatusBadge.vue

7. **Navigation & Integration**
   - Add route to router
   - Add to navigation menu
   - Add badge for active alerts

### Phase 4: MCP Tools

8. **MCP Integration** (`src/mcp-server/src/tools/monitoring.ts`)
   - `get_fleet_health` tool
   - `get_agent_health` tool
   - `trigger_health_check` tool

---

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `src/backend/services/monitoring_service.py` | Core monitoring service |
| `src/backend/services/monitoring_alerts.py` | Alert evaluation and notification |
| `src/backend/routers/monitoring.py` | REST API endpoints |
| `src/backend/db/monitoring.py` | Database operations |
| `src/frontend/src/views/Monitoring.vue` | Main monitoring page |
| `src/frontend/src/components/AgentHealthCard.vue` | Agent health card |
| `src/frontend/src/components/MonitoringConfigModal.vue` | Config modal |
| `src/frontend/src/components/HealthStatusBadge.vue` | Status badge |
| `src/frontend/src/stores/monitoring.js` | Pinia store |
| `src/mcp-server/src/tools/monitoring.ts` | MCP tools |
| `docs/memory/feature-flows/agent-monitoring.md` | Feature flow documentation |

### Modified Files

| File | Change |
|------|--------|
| `src/backend/database.py` | Add monitoring migration |
| `src/backend/db/schema.py` | Add `agent_health_checks` schema |
| `src/backend/main.py` | Mount monitoring router, start background task |
| `src/frontend/src/router/index.js` | Add `/monitoring` route |
| `src/frontend/src/components/NavBar.vue` | Add Monitoring nav item |
| `src/mcp-server/src/server.ts` | Register monitoring tools |
| `src/mcp-server/src/client.ts` | Add monitoring client methods |
| `docs/memory/feature-flows.md` | Add monitoring flow reference |

---

## Testing

### Unit Tests

- Health check functions (Docker, Network, Business)
- Aggregation logic
- Threshold evaluation
- Cooldown tracking

### Integration Tests

- API endpoint responses
- Notification creation
- WebSocket events
- Database persistence

### Manual Testing

1. **Healthy State**: All agents running, verify healthy status
2. **Network Failure**: Stop agent server, verify unreachable detection
3. **Container Stop**: Stop container, verify critical status
4. **High Resource**: Simulate high CPU/memory, verify degraded status
5. **Alert Flow**: Trigger unhealthy state, verify notification created
6. **Recovery**: Restore healthy state, verify recovery notification
7. **Cooldown**: Trigger multiple alerts, verify cooldown respected
8. **UI Display**: Verify monitoring page shows correct data

---

## Security Considerations

1. **Authentication**: All endpoints require authentication
2. **Authorization**: Users see only accessible agents; admins see all
3. **Rate Limiting**: Manual trigger endpoint limited to prevent abuse
4. **Data Access**: Health history follows agent access rules

---

## Future Enhancements

1. **External Integration**: Prometheus metrics endpoint, Grafana dashboards
2. **Custom Health Checks**: Allow agents to define custom health endpoints
3. **Auto-Recovery**: Automatic restart of unhealthy containers
4. **Anomaly Detection**: ML-based detection of unusual patterns
5. **SLA Tracking**: Define and track SLA targets per agent
6. **Incident Management**: Group related alerts into incidents

---

## Related Documents

- [Agent Notifications (NOTIF-001)](feature-flows/agent-notifications.md)
- [Host Telemetry (OBS-011/OBS-012)](feature-flows/host-telemetry.md)
- [Agent Lifecycle](feature-flows/agent-lifecycle.md)
- [Activity Stream](feature-flows/activity-stream.md)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-23 | Initial draft |
