# Feature: Host Telemetry

## Overview

Real-time infrastructure monitoring displaying host CPU, memory, and disk usage directly in the Dashboard header, with optional aggregate container statistics for running agents.

## User Stories

### OBS-011: View Host CPU/Memory/Disk
**As a** platform operator
**I want to** see host CPU, memory, and disk usage
**So that** I can monitor infrastructure health at a glance

### OBS-012: View Aggregate Container Stats
**As a** platform operator
**I want to** see aggregate container CPU and memory usage
**So that** I can understand resource distribution across running agents

## Entry Points

- **UI**: `src/frontend/src/components/HostTelemetry.vue` - Inline component in Dashboard header
- **Dashboard Integration**: `src/frontend/src/views/Dashboard.vue:59` - `<HostTelemetry />` component
- **API - Host Stats**: `GET /api/telemetry/host`
- **API - Container Stats**: `GET /api/telemetry/containers`

---

## Frontend Layer

### Components

#### HostTelemetry.vue (194 lines)
`src/frontend/src/components/HostTelemetry.vue`

| Section | Lines | Description |
|---------|-------|-------------|
| State Setup | 11-18 | `cpuHistory`, `memHistory` arrays, `hostStats` ref |
| History Init | 22-25 | Initialize 60-point rolling arrays with nulls |
| Fetch Stats | 27-56 | Poll `/api/telemetry/host`, update history arrays |
| Format Helpers | 58-73 | `formatPercent()`, `formatMemory()`, `getColorClass()` |
| Polling Setup | 75-83 | `onMounted`: init history, start 5s interval |
| Template | 86-136 | CPU/Mem sparklines + Disk progress bar |

**Visual Components:**
- CPU: Blue sparkline chart + percentage
- Memory: Purple sparkline chart + used/total GB
- Disk: Green progress bar + percentage

**Color Thresholds:**
```javascript
// getColorClass(percent) at line 67-73
< 50%  -> green
50-75% -> yellow
75-90% -> orange
>= 90% -> red
```

#### SparklineChart.vue (148 lines)
`src/frontend/src/components/SparklineChart.vue`

Uses uPlot library for lightweight SVG charts:
- Props: `data` (array), `color` (CSS), `yMax` (100), `width` (60px), `height` (20px)
- Updates reactively on data changes
- No axes, legend, or cursor (minimal footprint)

### State Management

No Pinia store - component manages its own state:
- `hostStats`: Current metrics snapshot
- `cpuHistory`: Rolling 60-point array (5 min at 5s intervals)
- `memHistory`: Rolling 60-point array

### API Calls

```javascript
// HostTelemetry.vue:30-35
const hostRes = await fetch(`${API_BASE}/api/telemetry/host`, {
  signal: AbortSignal.timeout(3000)
})
```

**Polling:** Every 5 seconds (`setInterval` at line 78)

---

## Backend Layer

### Router
`src/backend/routers/telemetry.py`

Registered in main.py:
```python
# main.py:47
from routers.telemetry import router as telemetry_router

# main.py:263
app.include_router(telemetry_router)
```

### Endpoints

#### GET /api/telemetry/host
`src/backend/routers/telemetry.py:29-66`

Returns host system statistics via psutil.

**No authentication required** (follows OpenTelemetry pattern).

**Response Schema:**
```json
{
  "cpu": {
    "percent": 45.2,
    "count": 8
  },
  "memory": {
    "percent": 62.3,
    "used_gb": 12.5,
    "total_gb": 20.0
  },
  "disk": {
    "percent": 54.1,
    "used_gb": 108.2,
    "total_gb": 200.0
  },
  "timestamp": "2026-01-13T12:00:00.000000Z"
}
```

**Implementation Details:**
```python
# Line 26: Prime CPU counter on module load
psutil.cpu_percent(interval=None)

# Line 39: Non-blocking CPU read
cpu_percent = psutil.cpu_percent(interval=None)

# Line 43-46: Memory and disk via psutil
mem = psutil.virtual_memory()
disk = psutil.disk_usage('/')
```

#### GET /api/telemetry/containers
`src/backend/routers/telemetry.py:112-173`

Returns aggregate statistics across all running agent containers.

**No authentication required**.

**Response Schema:**
```json
{
  "running_count": 3,
  "total_cpu_percent": 15.2,
  "total_memory_mb": 1024.5,
  "containers": [
    {"name": "agent-a", "cpu": 8.1, "memory_mb": 512.2},
    {"name": "agent-b", "cpu": 4.5, "memory_mb": 256.1},
    {"name": "agent-c", "cpu": 2.6, "memory_mb": 256.2}
  ],
  "timestamp": "2026-01-13T12:00:00.000000Z"
}
```

**Performance Optimization:**
```python
# Line 18-20: Thread pool for parallel Docker stats
_docker_executor = ThreadPoolExecutor(max_workers=4)

# Line 126: Use fast agent listing (labels only)
agents = list_all_agents_fast()

# Line 140-147: Parallel execution with asyncio
tasks = [
    loop.run_in_executor(_docker_executor, _get_single_container_stats_sync, agent.name)
    for agent in running_agents
]
containers_stats = await asyncio.gather(*tasks, return_exceptions=True)
```

**Single Container Stats Helper:**
```python
# Line 69-109: _get_single_container_stats_sync(agent_name)
# - Gets container by name
# - Reads stats (one-shot, ~1-2s per container)
# - Calculates CPU % from deltas
# - Calculates memory (usage - cache)
```

### Business Logic

1. **CPU Calculation** (lines 82-89):
   ```python
   cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
              stats['precpu_stats']['cpu_usage']['total_usage']
   system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                 stats['precpu_stats']['system_cpu_usage']
   cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
   ```

2. **Memory Calculation** (lines 92-95):
   ```python
   memory_usage = stats['memory_stats'].get('usage', 0)
   memory_cache = stats['memory_stats'].get('stats', {}).get('cache', 0)
   memory_used = memory_usage - memory_cache  # Exclude cache for accuracy
   ```

### Docker Integration

Uses `services/docker_service.py`:
```python
# Line 16: Import
from services.docker_service import docker_client, list_all_agents_fast
```

**list_all_agents_fast()** (docker_service.py:101-159):
- Extracts data from container labels only
- Avoids slow operations: `container.attrs`, `container.image`, `container.stats()`
- Performance: ~50ms for 10 agents vs ~2-3s with full metadata

---

## Data Flow

```
Dashboard.vue
    |
    +-- <HostTelemetry /> (line 59)
           |
           +-- onMounted() -> initHistory() + fetchStats()
           |
           +-- setInterval(fetchStats, 5000)
                   |
                   +-- GET /api/telemetry/host
                           |
                           +-- psutil.cpu_percent()
                           +-- psutil.virtual_memory()
                           +-- psutil.disk_usage('/')
                           |
                           +-- Return JSON response
                   |
                   +-- Update cpuHistory[], memHistory[]
                   |
                   +-- SparklineChart re-renders
```

---

## Side Effects

- **No WebSocket**: Pure polling model
- **No Audit Logging**: Telemetry endpoints are read-only, high-frequency
- **No Database**: Metrics are computed fresh each request
- **No Authentication**: Public endpoints (infrastructure monitoring should be accessible)

---

## Error Handling

| Error Case | HTTP Status | Handling |
|------------|-------------|----------|
| psutil error | 500 | `Error getting host stats: {message}` |
| Docker unavailable | 503 | `Docker not available` |
| Container stats error | - | Returns `{error: message}` per container, continues |
| Fetch timeout | - | Frontend: 3s timeout, silently fails |

**Frontend Error Handling:**
```javascript
// HostTelemetry.vue:32
signal: AbortSignal.timeout(3000)

// Lines 52-55
} catch (e) {
  loading.value = false
  error.value = e.message
}
```

---

## Security Considerations

- **No Authentication Required**: Follows OTel pattern for infrastructure metrics
- **Read-Only**: No mutation endpoints
- **Rate Limiting**: Not implemented (polling interval is client-controlled)
- **No PII**: Only system metrics exposed

---

## Related Flows

- **Upstream**: Dashboard page load triggers HostTelemetry mount
- **Downstream**: None (display-only)
- **Related**: [opentelemetry-integration.md](opentelemetry-integration.md) - OTel metrics from agents
- **Related**: [agent-logs-telemetry.md](agent-logs-telemetry.md) - Per-agent container logs

---

## Testing

### Prerequisites
- Trinity backend running (`./scripts/deploy/start.sh`)
- At least one agent created (for container stats)

### Test Steps

#### Test 1: Host Stats Display
| Step | Action | Expected | Verify |
|------|--------|----------|--------|
| 1 | Navigate to Dashboard (`/`) | Page loads with header | Header visible |
| 2 | Look at right side of stats bar | See "CPU", "Mem", "Disk" stats | Sparklines visible |
| 3 | Wait 5 seconds | Values update | Numbers change |
| 4 | Check color coding | Values <50% are green | Color matches threshold |

#### Test 2: API Direct Access
| Step | Action | Expected | Verify |
|------|--------|----------|--------|
| 1 | `curl http://localhost:8000/api/telemetry/host` | JSON response | Contains cpu, memory, disk |
| 2 | `curl http://localhost:8000/api/telemetry/containers` | JSON response | Contains running_count, containers array |

#### Test 3: Container Stats (OBS-012)
| Step | Action | Expected | Verify |
|------|--------|----------|--------|
| 1 | Start 2+ agents | Containers running | `docker ps` shows agents |
| 2 | Call `/api/telemetry/containers` | Aggregate stats | `running_count >= 2` |
| 3 | Check containers array | Per-agent breakdown | Each has cpu, memory_mb |

### Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| No running agents | `running_count: 0`, empty `containers` array |
| Docker unavailable | 503 error on `/containers`, host stats still work |
| High CPU load (>90%) | Red color class applied |
| Disk nearly full (>90%) | Red progress bar |

### Cleanup
No cleanup required - read-only endpoints.

### Status
- Host Telemetry Display: Working
- Container Aggregate Stats: Working (API only, no UI integration)

---

## Revision History

| Date | Change |
|------|--------|
| 2026-01-13 | Initial documentation |
