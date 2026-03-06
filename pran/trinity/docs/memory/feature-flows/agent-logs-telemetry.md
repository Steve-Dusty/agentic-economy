# Feature: Agent Logs & Live Telemetry

## Overview
Real-time monitoring of agent containers through live telemetry metrics. Provides visibility into container health (CPU, memory, uptime) in the AgentHeader.

> **Note (2026-02-18)**: The Logs tab has been **removed** from AgentDetail.vue. Logs can still be accessed via the API endpoint for programmatic use. Container logs are also available via the Terminal tab (bash mode) or the MCP `get_agent_logs` tool.

## User Story
As a platform user, I want to monitor my agent's resource usage so that I can ensure healthy operation.

---

## Entry Points

### Logs API (No UI Tab)
- **UI**: Logs tab removed from AgentDetail.vue (2026-02-18)
- **API**: `GET /api/agents/{name}/logs?tail=100` - Still available for programmatic access

### Live Telemetry
- **UI**: `src/frontend/src/views/AgentDetail.vue:28-36` - Stats props passed to AgentHeader
- **API**: `GET /api/agents/{name}/stats`

---

## Frontend Layer

### Components

#### AgentDetail.vue - Composable Setup
**Location**: `src/frontend/src/views/AgentDetail.vue:277-285`

```javascript
// Stats composable
const {
  agentStats,
  statsLoading,
  cpuHistory,
  memoryHistory,
  startStatsPolling,
  stopStatsPolling
} = useAgentStats(agent, agentsStore)
```

#### AgentHeader.vue - Live Stats Bar
**Location**: `src/frontend/src/components/AgentHeader.vue:98-162` (Row 2, right side)

Displays real-time telemetry in the agent header when status is "running":

| Line | Element | Purpose |
|------|---------|---------|
| 137-142 | Loading indicator | Shows "Loading..." with spinner |
| 100-135 | Stats display row | CPU, Memory, Uptime metrics |
| 102-115 | CPU widget | SparklineChart + percentage with color coding (fixed width `w-10`) |
| 117-130 | Memory widget | SparklineChart + bytes display (fixed width `w-14`) |
| 132-134 | Uptime widget | Time since container started (fixed width `w-16`) |
| 151-161 | Resource config button | Opens resource modal |
| 144-149 | Stopped state | Shows creation date and resource allocation |

**Color Thresholds** (lines 113, 128):
- Green: < 50%
- Yellow: 50-80%
- Red: > 80%

**Note**: Network stats are collected by the backend but not displayed in the UI (removed for cleaner layout).

#### LogsPanel.vue - REMOVED
**Status**: Logs tab removed from AgentDetail.vue as of 2026-02-18.

> The LogsPanel.vue component still exists in the codebase but is no longer rendered in the Agent Detail page. The logs API endpoint remains available for programmatic access via the MCP `get_agent_logs` tool or direct API calls.

### State Management

**Location**: `src/frontend/src/stores/agents.js`

```javascript
// Line 183-189: Get agent logs
async getAgentLogs(name, tail = 100) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/logs?tail=${tail}`, {
    headers: authStore.authHeader
  })
  return response.data.logs
}

// Line 276-282: Get agent stats
async getAgentStats(name) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/stats`, {
    headers: authStore.authHeader
  })
  return response.data
}
```

### Composables

#### useAgentStats.js
**Location**: `src/frontend/src/composables/useAgentStats.js`

```javascript
// Line 4: History configuration
const MAX_POINTS = 30  // 30 samples at 10s = 5 minutes

// Line 56-60: Stats polling
const startStatsPolling = () => {
  initHistory()
  loadStats()
  statsRefreshInterval = setInterval(loadStats, 10000) // 10 seconds
}
```

Returns: `agentStats`, `statsLoading`, `cpuHistory`, `memoryHistory`, `loadStats`, `startStatsPolling`, `stopStatsPolling`

#### useAgentLogs.js
**Location**: `src/frontend/src/composables/useAgentLogs.js`

```javascript
// Line 43-52: Auto-refresh toggle watch
watch(autoRefreshLogs, (enabled) => {
  if (enabled) {
    logsRefreshInterval = setInterval(refreshLogs, 15000) // 15 seconds
  } else {
    if (logsRefreshInterval) {
      clearInterval(logsRefreshInterval)
      logsRefreshInterval = null
    }
  }
})

// Line 35-40: Smart scroll detection
const handleLogsScroll = () => {
  if (!logsContainer.value) return
  const { scrollTop, scrollHeight, clientHeight } = logsContainer.value
  userScrolledUp.value = scrollTop + clientHeight < scrollHeight - 50
}
```

Returns: `logs`, `logLines`, `autoRefreshLogs`, `logsContainer`, `userScrolledUp`, `refreshLogs`, `handleLogsScroll`

### Polling Behavior

**Stats Polling** (when agent is running):
- Interval: 10 seconds
- History: 30 samples (5 minutes of data at 10s intervals)
- Method: `startStatsPolling()` in `onMounted()`
- Cleanup: `stopStatsPolling()` in `onUnmounted()`

**Logs Auto-Refresh** (optional):
- Interval: 15 seconds (actual, despite UI showing "10s")
- User-controlled toggle
- Smart scroll: Auto-scroll to bottom unless user scrolled up (within 50px threshold)

---

## Backend Layer

### Endpoints

#### GET /api/agents/{agent_name}/logs
**File**: `src/backend/routers/agents.py:367-383`

**Handler**:
```python
@router.get("/{agent_name}/logs")
async def get_agent_logs_endpoint(
    agent_name: AuthorizedAgentByName,
    request: Request,
    tail: int = 100
):
    """Get agent container logs."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        logs = container.logs(tail=tail).decode('utf-8')
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")
```

**Parameters**:
- `tail`: Number of lines (default: 100)

**Response**:
```json
{
  "logs": "string with newline-separated log entries"
}
```

**Note**: Uses `AuthorizedAgentByName` dependency for authorization check. No audit logging on this endpoint (removed for simplicity).

#### GET /api/agents/{agent_name}/stats
**File**: `src/backend/routers/agents.py:386-393` (thin router layer)
**Business Logic**: `src/backend/services/agent_service/stats.py:123-184`

**Handler** (thin router layer):
```python
@router.get("/{agent_name}/stats")
async def get_agent_stats_endpoint(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get live container stats (CPU, memory, network) for an agent."""
    return await get_agent_stats_logic(agent_name, current_user)
```

### Business Logic

> **Note**: Business logic is in `services/agent_service/stats.py`

#### get_agent_stats_logic
**Location**: `src/backend/services/agent_service/stats.py:123-184`

```python
async def get_agent_stats_logic(agent_name: str, current_user: User) -> dict:
    """Get live container stats (CPU, memory, network) for an agent."""
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.reload()
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent is not running")

    stats = container.stats(stream=False)  # One-shot, not streaming
    # ... calculations ...
```

#### CPU Calculation
**Location**: `src/backend/services/agent_service/stats.py:145-152`

```python
cpu_stats = stats.get("cpu_stats", {})
precpu_stats = stats.get("precpu_stats", {})

cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - \
            precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
system_delta = cpu_stats.get("system_cpu_usage", 0) - \
               precpu_stats.get("system_cpu_usage", 0)

if system_delta > 0 and cpu_delta > 0:
    num_cpus = len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", [])) or 1
    cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
```

#### Memory Calculation
**Location**: `src/backend/services/agent_service/stats.py:154-158`

```python
memory_stats = stats.get("memory_stats", {})
memory_used = memory_stats.get("usage", 0)
memory_limit = memory_stats.get("limit", 0)
cache = memory_stats.get("stats", {}).get("cache", 0)
memory_used_actual = max(0, memory_used - cache)  # Subtract cache
```

#### Network Stats
**Location**: `src/backend/services/agent_service/stats.py:160-162`

```python
networks = stats.get("networks", {})
network_rx = sum(net.get("rx_bytes", 0) for net in networks.values())
network_tx = sum(net.get("tx_bytes", 0) for net in networks.values())
```

#### Uptime Calculation
**Location**: `src/backend/services/agent_service/stats.py:164-171`

```python
started_at = container.attrs.get("State", {}).get("StartedAt", "")
uptime_seconds = 0
if started_at:
    try:
        start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00").split(".")[0])
        uptime_seconds = int((datetime.now(start_time.tzinfo) - start_time).total_seconds())
    except Exception:
        pass
```

#### Stats Response
**Location**: `src/backend/services/agent_service/stats.py:173-182`

```python
return {
    "cpu_percent": round(cpu_percent, 1),
    "memory_used_bytes": memory_used_actual,
    "memory_limit_bytes": memory_limit,
    "memory_percent": round((memory_used_actual / memory_limit * 100) if memory_limit > 0 else 0, 1),
    "network_rx_bytes": network_rx,   # Returned but not displayed in UI
    "network_tx_bytes": network_tx,   # Returned but not displayed in UI
    "uptime_seconds": uptime_seconds,
    "status": container.status
}
```

**UI Display**: Only `cpu_percent`, `memory_used_bytes`, `memory_percent`, and `uptime_seconds` are shown in the header. Network stats are available for programmatic use but not displayed.

---

## Data Layer

### Docker API Operations
- `container.logs(tail=N)` - Fetch last N lines of container stdout/stderr
- `container.stats(stream=False)` - One-shot container metrics
- `container.attrs["State"]["StartedAt"]` - Container start timestamp
- `container.reload()` - Refresh container state

### No Database Operations
This feature reads directly from Docker API - no database persistence.

---

## UI Display

### Telemetry Stats Bar (Header)

**Component**: `AgentHeader.vue:98-162`

| Metric | Display | Color Coding | Width |
|--------|---------|--------------|-------|
| CPU | `XX.X%` with sparkline chart | Green (<50%), Yellow (50-80%), Red (>80%) | `w-10` (fixed) |
| Memory | `847 MB` with sparkline | Similar thresholds | `w-14` (fixed) |
| Uptime | `2h 15m` | Gray | `w-16` (fixed) |

**Note**: Fixed widths prevent layout jumping when stats update.

### Logs Tab Features (REMOVED)

> **Note**: The Logs tab has been removed from AgentDetail.vue as of 2026-02-18. The functionality below is no longer exposed in the UI but remains available via API.

**Component**: `LogsPanel.vue` (no longer rendered)

- Scrollable container (h-96 = 384px)
- Line count selector: 50, 100, 200, 500
- Auto-refresh toggle (15-second interval)
- Manual refresh button
- Smart auto-scroll (pauses when user scrolls up, 50px threshold)
- Monospace font with line wrapping

---

## Side Effects

### No Audit Logging
Unlike the previous implementation, logs viewing is no longer audited (removed for simplicity in the current codebase).

### No WebSocket Broadcasts
Stats and logs are pull-based, not push-based.

---

## Error Handling

| Error Case | HTTP Status | UI Behavior |
|------------|-------------|-------------|
| Agent not found | 404 | Show error toast |
| Agent not running (stats) | 400 | Hide stats bar, show "Stats unavailable" |
| Docker API error | 500 | Log error, don't crash |
| Stats calculation error | 500 | Return error message |

---

## Security Considerations

### Authorization
- Logs endpoint: Uses `AuthorizedAgentByName` dependency (checks owner, shared users, admins)
- Stats endpoint: Uses `get_current_user` dependency
- Access allowed for owner, shared users, and admins
- No credential data exposed in logs (container logs only)

### Rate Limiting
- 10-second stats polling interval prevents API overload
- 15-second logs auto-refresh interval for reduced load
- `stream=False` for stats prevents long-running connections

---

## Known Issues

### UI/Code Mismatch for Logs Auto-Refresh Interval (Historical)
- **UI Label**: `LogsPanel.vue:20` says "Auto-refresh (10s)"
- **Actual Interval**: `useAgentLogs.js:45` uses 15000ms (15 seconds)
- **Impact**: N/A - Logs tab removed from UI (2026-02-18)

---

## Related Flows

- **Upstream**: [Agent Lifecycle](agent-lifecycle.md) - Container must exist
- **Related**: [Activity Monitoring](activity-monitoring.md) - Real-time tool execution (different data source)
- **Related**: [Agent Chat](agent-chat.md) - Session info also displayed in header

---

## MCP Server Integration

The MCP server provides similar functionality via:
- `get_agent_logs(agent_name, lines)` - Retrieve container logs
- `get_agent(name)` - Get agent status (includes running/stopped)

See [MCP Orchestration](mcp-orchestration.md) for MCP tool details.

---

## Status
**Last Updated**: 2026-02-18
**Verified**: Stats display shows only CPU, Memory, Uptime (network removed from UI)

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-02-18 | **Logs tab removed from UI**: The Logs tab has been removed from AgentDetail.vue visibleTabs. Logs API endpoint remains available for programmatic access via MCP tools or direct API calls. Updated Overview, Entry Points, LogsPanel section, and Known Issues to reflect this change. |
| 2026-02-18 | **Network stats removed from UI**: Updated documentation to reflect current AgentHeader.vue implementation. Stats display now shows only CPU, Memory, and Uptime (lines 100-135). Network stats still returned by backend API but not displayed. Added fixed width notes (`w-10`, `w-14`, `w-16`) to prevent layout jumping. Updated all line numbers for Row 2 stats section (98-162). |
| 2026-01-23 | **Full verification and update**: Verified all line numbers against current codebase. Logs endpoint now at lines 367-383 (was 404-430). Stats endpoint at 386-393. Documented UI/code mismatch for auto-refresh interval (UI says 10s, code uses 15s). Audit logging removed from logs endpoint. Updated AgentHeader.vue stats display lines (172-235). Added composable file locations. |
| 2026-01-12 | **Polling interval optimization**: Stats polling changed from 5s to 10s, logs auto-refresh changed from 10s to 15s. Stats history reduced from 60 to 30 samples (still 5 min at 10s intervals). Updated composables `useAgentStats.js` and `useAgentLogs.js`. |
| 2025-12-30 | **Updated for service layer refactor**: Stats logic moved from `agents.py` to `services/agent_service/stats.py`. Logs endpoint now at lines 404-430 (was 558-584). Stats endpoint now at 433-440 delegating to service layer. Updated all business logic line references to stats.py. |
| 2025-12-02 | Initial documentation |
