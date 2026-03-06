# Feature: Dynamic Dashboards (DASH-001)

> **Last Updated**: 2026-02-23 - Initial documentation for historical data visualization and platform metrics injection.

## Overview

Dynamic Dashboards extends the agent dashboard system with historical data visualization (sparklines) and platform metrics injection, while preserving the agent-controlled `dashboard.yaml` paradigm. The platform captures widget values on each dashboard fetch, calculates trends, and optionally appends auto-tracked execution metrics.

## User Story

As a platform operator, I want to see historical trends for agent-defined metrics so that I can visualize performance over time without modifying agent dashboards.

As an agent developer, I want my dashboard to show platform-tracked execution stats automatically so that I get observability without manual instrumentation.

## Entry Points

- **UI**: `src/frontend/src/components/DashboardPanel.vue:135-143` - SparklineChart renders historical data
- **API**: `GET /api/agent-dashboard/{name}?include_history=true&history_hours=24&include_platform_metrics=true`

## Architecture

```
+------------------+     +-------------------+     +----------------------+
| DashboardPanel   | --> | Backend Router    | --> | Agent Server         |
| (Vue Component)  |     | /api/agent-       |     | /api/dashboard       |
|                  |     | dashboard/{name}  |     |                      |
+------------------+     +-------------------+     +----------------------+
        |                        |                         |
        v                        v                         v
  SparklineChart          dashboard.py service      dashboard.yaml file
  (uPlot-based)           - Capture snapshot         ~/dashboard.yaml
                          - Enrich with history
                          - Inject platform metrics
                                 |
                                 v
                          +------------------+
                          | Database         |
                          | agent_dashboard_ |
                          | values table     |
                          +------------------+
```

## Data Flow Summary

1. **Frontend** requests dashboard with `include_history=true`
2. **Backend** fetches raw config from agent's `/api/dashboard`
3. **Change Detection**: If `dashboard.yaml` mtime changed, capture widget snapshot
4. **History Enrichment**: Query historical values, calculate stats, inject `history` field
5. **Platform Metrics**: If enabled, query execution stats and append section
6. **Response**: Enriched config with sparkline data returned to frontend
7. **Rendering**: SparklineChart renders historical values in metric/progress widgets

---

## Frontend Layer

### Components

**DashboardPanel.vue:135-143** - Sparkline integration for metric widgets:
```html
<!-- Sparkline -->
<SparklineChart
  v-if="widget.history?.values?.length > 1"
  :data="widget.history.values.map(v => v.v)"
  :color="getSparklineColor(widget)"
  :y-max="widget.history.max || 100"
  :width="120"
  :height="24"
  class="mt-2"
/>
```

**DashboardPanel.vue:191-199** - Sparkline for progress widgets:
```html
<SparklineChart
  v-if="widget.history?.values?.length > 1"
  :data="widget.history.values.map(v => v.v)"
  :color="getSparklineColor(widget)"
  :y-max="100"
  :width="120"
  :height="24"
  class="mt-2"
/>
```

**DashboardPanel.vue:120-131** - Trend indicator display:
```html
<div v-if="widget.trend || widget.history?.trend" class="flex items-center text-sm" :class="getTrendColor(widget.trend || widget.history?.trend)">
  <svg v-if="(widget.trend || widget.history?.trend) === 'up'" ... />
  <svg v-else-if="(widget.trend || widget.history?.trend) === 'down'" ... />
  <span v-if="widget.trend_value || widget.history?.trend_percent" class="ml-1">
    {{ widget.trend_value || (widget.history?.trend_percent ? `${widget.history.trend_percent > 0 ? '+' : ''}${widget.history.trend_percent}%` : '') }}
  </span>
</div>
```

**DashboardPanel.vue:84** - Platform section styling:
```html
<div
  v-for="(section, sectionIndex) in dashboardData.config.sections"
  :key="sectionIndex"
  class="space-y-4"
  :class="section.platform_managed ? 'mt-6 pt-6 border-t border-indigo-200 dark:border-indigo-800' : ''"
>
```

**DashboardPanel.vue:92-94** - "Auto" badge for platform sections:
```html
<span v-if="section.platform_managed" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">
  Auto
</span>
```

### SparklineChart Component

**src/frontend/src/components/SparklineChart.vue** (148 lines)

Props:
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `data` | Array | required | Array of numeric values |
| `color` | String | `#3b82f6` | Line color (CSS) |
| `yMax` | Number | `100` | Maximum Y scale value |
| `width` | Number | `60` | Chart width in pixels |
| `height` | Number | `20` | Chart height in pixels |

Implementation:
```javascript
// Uses uPlot for lightweight sparkline rendering
import uPlot from 'uplot'

function createChartOpts() {
  return {
    width: props.width,
    height: props.height,
    padding: [2, 0, 2, 0],
    cursor: { show: false },
    legend: { show: false },
    scales: {
      x: { time: false },
      y: { min: 0, max: props.yMax }
    },
    series: [
      {},
      {
        stroke: props.color,
        width: 1.5,
        fill: props.color + '30',  // 30% opacity fill
        spanGaps: true,
        points: { show: false }
      }
    ]
  }
}
```

### Helper Functions

**DashboardPanel.vue:412-417** - Sparkline color based on trend:
```javascript
const getSparklineColor = (widget) => {
  const trend = widget.history?.trend
  if (trend === 'up') return '#10b981'   // green-500
  if (trend === 'down') return '#ef4444' // red-500
  return '#3b82f6'                        // blue-500 (stable)
}
```

### State Management

**stores/agents.js:545-550** - Store action:
```javascript
async getAgentDashboard(name) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agent-dashboard/${name}`, {
    headers: authStore.authHeader
  })
  return response.data
}
```

---

## Backend Layer

### Router

**src/backend/routers/agent_dashboard.py** (85 lines)

```python
router = APIRouter(prefix="/api/agent-dashboard", tags=["agent-dashboard"])

@router.get("/{name}")
async def get_agent_dashboard(
    name: str,
    include_history: bool = Query(
        default=True,
        description="Include historical sparkline data for widgets"
    ),
    history_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Hours of history to include (1-168)"
    ),
    include_platform_metrics: bool = Query(
        default=True,
        description="Include platform-managed metrics section"
    ),
    current_user: User = Depends(get_current_user)
):
    return await get_agent_dashboard_logic(
        name,
        current_user,
        include_history=include_history,
        history_hours=history_hours,
        include_platform_metrics=include_platform_metrics
    )
```

### Service Layer

**src/backend/services/agent_service/dashboard.py** (286 lines)

**Main Flow** - `get_agent_dashboard_logic()` (Line 157-286):
```python
async def get_agent_dashboard_logic(
    agent_name: str,
    current_user: User,
    include_history: bool = True,
    history_hours: int = 24,
    include_platform_metrics: bool = True
) -> dict:
    # 1. Authorization check
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, ...)

    # 2. Get container and check status
    container = get_agent_container(agent_name)
    if container.status != "running":
        return {"status": "stopped", ...}

    # 3. Fetch from agent's internal API
    agent_url = f"http://agent-{agent_name}:8000/api/dashboard"
    response = await client.get(agent_url)
    data = response.json()

    # 4. Capture snapshot if dashboard changed (DASH-001)
    if data.get("has_dashboard") and data.get("config") and data.get("last_modified"):
        last_mtime = db.get_last_captured_mtime(agent_name)
        current_mtime = data["last_modified"]
        if last_mtime != current_mtime:
            db.capture_dashboard_snapshot(agent_name, data["config"], current_mtime)

    # 5. Enrich with history if requested (DASH-001)
    if include_history and data.get("has_dashboard") and data.get("config"):
        _enrich_widgets_with_history(data["config"], agent_name, history_hours)

    # 6. Add platform metrics section if requested (DASH-001)
    if include_platform_metrics and data.get("has_dashboard") and data.get("config"):
        config = data["config"]
        if config.get("platform_metrics") is not False:
            platform_section = _build_platform_metrics_section(agent_name, history_hours)
            if platform_section["widgets"]:
                config["sections"].append(platform_section)

    return data
```

**History Enrichment** - `_enrich_widgets_with_history()` (Line 103-154):
```python
def _enrich_widgets_with_history(config: dict, agent_name: str, hours: int = 24) -> dict:
    """Enrich trackable widgets with historical data and trends."""
    # Get all widget history at once
    all_history = db.get_all_widget_history(agent_name, hours)

    for section_idx, section in enumerate(config.get("sections", [])):
        for widget_idx, widget in enumerate(section.get("widgets", [])):
            widget_type = widget.get("type")

            # Only enrich trackable widgets
            if widget_type not in ("metric", "progress", "status"):
                continue

            # Get widget key
            widget_key = widget.get("id") or f"s{section_idx}_w{widget_idx}"

            # Get history for this widget
            history_values = all_history.get(widget_key, [])

            if len(history_values) > 1:
                stats = db.calculate_widget_stats(history_values)
                widget["history"] = {
                    "values": history_values,
                    "trend": stats["trend"],
                    "trend_percent": stats["trend_percent"],
                    "min": stats["min"],
                    "max": stats["max"],
                    "avg": stats["avg"]
                }

    return config
```

**Platform Metrics Section** - `_build_platform_metrics_section()` (Line 20-100):
```python
def _build_platform_metrics_section(agent_name: str, hours: int = 24) -> dict:
    """Build the platform metrics section with execution and health stats."""
    exec_stats = db.get_agent_execution_stats(agent_name, hours)
    health = db.get_latest_health_check(agent_name, "aggregate")

    widgets = []

    # Tasks metric
    widgets.append({
        "type": "metric",
        "id": "__platform_tasks",
        "label": f"Tasks ({hours}h)",
        "value": exec_stats["task_count"],
        "platform_source": "executions.count"
    })

    # Success rate (only if tasks exist)
    if exec_stats["task_count"] > 0:
        success_rate = exec_stats["success_rate"]
        widgets.append({
            "type": "metric",
            "id": "__platform_success_rate",
            "label": "Success Rate",
            "value": f"{success_rate}%",
            "color": "green" if success_rate >= 90 else ("yellow" if success_rate >= 70 else "red"),
            "platform_source": "executions.success_rate"
        })

    # Cost (only if non-zero)
    if exec_stats["total_cost"] > 0:
        widgets.append({
            "type": "metric",
            "id": "__platform_cost",
            "label": f"Cost ({hours}h)",
            "value": f"${exec_stats['total_cost']:.2f}",
            "platform_source": "executions.cost"
        })

    # Health status
    if health:
        health_status = health.status.value
        widgets.append({
            "type": "status",
            "id": "__platform_health",
            "label": "Health",
            "value": health_status.title(),
            "color": "green" if health_status == "healthy" else ("yellow" if health_status == "degraded" else "red"),
            "platform_source": "health.status"
        })

    # Running tasks
    if exec_stats["running_count"] > 0:
        widgets.append({
            "type": "metric",
            "id": "__platform_running",
            "label": "Running",
            "value": exec_stats["running_count"],
            "color": "blue",
            "platform_source": "executions.running"
        })

    return {
        "title": "Platform Metrics",
        "description": "Automatically tracked by Trinity",
        "layout": "grid",
        "columns": 4,
        "platform_managed": True,
        "widgets": widgets
    }
```

---

## Database Layer

### Schema

**src/backend/db/schema.py:461-474** - Dashboard values table:
```python
"agent_dashboard_values": """
    CREATE TABLE IF NOT EXISTS agent_dashboard_values (
        id TEXT PRIMARY KEY,
        agent_name TEXT NOT NULL,
        widget_key TEXT NOT NULL,
        widget_label TEXT,
        widget_type TEXT NOT NULL,
        value_numeric REAL,
        value_text TEXT,
        dashboard_mtime TEXT NOT NULL,
        captured_at TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
""",
```

**Indexes** (schema.py + migrations.py):
```sql
CREATE INDEX IF NOT EXISTS idx_dashboard_values_agent_time
  ON agent_dashboard_values(agent_name, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_dashboard_values_widget
  ON agent_dashboard_values(agent_name, widget_key, captured_at DESC);
```

### Migration

**src/backend/db/migrations.py:420-444** - Migration function:
```python
def _migrate_agent_dashboard_values_table(cursor, conn):
    """Create agent_dashboard_values table for dashboard history (DASH-001)."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_dashboard_values (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            widget_key TEXT NOT NULL,
            widget_label TEXT,
            widget_type TEXT NOT NULL,
            value_numeric REAL,
            value_text TEXT,
            dashboard_mtime TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_values_agent_time ON agent_dashboard_values(agent_name, captured_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_values_widget ON agent_dashboard_values(agent_name, widget_key, captured_at DESC)")
    conn.commit()
```

### Dashboard History Operations

**src/backend/db/dashboard_history.py** (314 lines) - NEW FILE

**capture_dashboard_snapshot()** (Line 29-108):
```python
def capture_dashboard_snapshot(
    self,
    agent_name: str,
    config: Dict[str, Any],
    dashboard_mtime: str
) -> int:
    """Capture snapshot of all trackable widget values from a dashboard config.

    Trackable widgets are: metric, progress, status (with numeric values).
    """
    for section_idx, section in enumerate(config.get("sections", [])):
        for widget_idx, widget in enumerate(section.get("widgets", [])):
            widget_type = widget.get("type")

            # Only track widgets with meaningful values
            if widget_type not in ("metric", "progress", "status"):
                continue

            widget_key = widget.get("id") or f"s{section_idx}_w{widget_idx}"
            value = widget.get("value")

            # Extract numeric value (handle strings like "1,234" or "95%")
            value_numeric = None
            if isinstance(value, (int, float)):
                value_numeric = float(value)
            elif isinstance(value, str):
                cleaned = value.replace(",", "").replace("%", "").replace("$", "").strip()
                try:
                    value_numeric = float(cleaned)
                except ValueError:
                    pass

            # Insert record
            cursor.execute("""
                INSERT INTO agent_dashboard_values (
                    id, agent_name, widget_key, widget_label, widget_type,
                    value_numeric, value_text, dashboard_mtime, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ...)
```

**get_all_widget_history()** (Line 152-191):
```python
def get_all_widget_history(self, agent_name: str, hours: int = 24) -> Dict[str, List[Dict]]:
    """Get history for all widgets of an agent, keyed by widget_key."""
    cursor.execute("""
        SELECT widget_key, captured_at, value_numeric, value_text
        FROM agent_dashboard_values
        WHERE agent_name = ?
        AND captured_at > datetime('now', ? || ' hours')
        ORDER BY widget_key, captured_at ASC
    """, (agent_name, f"-{hours}"))

    results: Dict[str, List] = {}
    for row in cursor.fetchall():
        widget_key = row["widget_key"]
        if widget_key not in results:
            results[widget_key] = []
        results[widget_key].append({"t": row["captured_at"], "v": row["value_numeric"]})

    return results
```

**calculate_widget_stats()** (Line 193-253):
```python
def calculate_widget_stats(self, values: List[Dict]) -> Dict[str, Any]:
    """Calculate statistics from historical values."""
    numeric_values = [v["v"] for v in values if isinstance(v.get("v"), (int, float))]

    min_val = min(numeric_values)
    max_val = max(numeric_values)
    avg_val = sum(numeric_values) / len(numeric_values)

    # Calculate trend: compare first half avg to second half avg
    trend = "stable"
    trend_percent = 0
    if len(numeric_values) >= 2:
        mid = len(numeric_values) // 2
        first_half_avg = sum(numeric_values[:mid]) / mid
        second_half_avg = sum(numeric_values[mid:]) / (len(numeric_values) - mid)
        if first_half_avg > 0:
            trend_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100
            if trend_percent > 5:
                trend = "up"
            elif trend_percent < -5:
                trend = "down"

    return {
        "min": round(min_val, 2),
        "max": round(max_val, 2),
        "avg": round(avg_val, 2),
        "trend": trend,
        "trend_percent": round(trend_percent, 1)
    }
```

**get_last_captured_mtime()** (Line 255-276):
```python
def get_last_captured_mtime(self, agent_name: str) -> Optional[str]:
    """Get the most recent dashboard_mtime that was captured for an agent.
    Used for change detection - only capture new snapshots when mtime changes.
    """
    cursor.execute("""
        SELECT dashboard_mtime FROM agent_dashboard_values
        WHERE agent_name = ?
        ORDER BY captured_at DESC
        LIMIT 1
    """, (agent_name,))
    row = cursor.fetchone()
    return row["dashboard_mtime"] if row else None
```

### Execution Stats Query

**src/backend/db/schedules.py:673-728** - `get_agent_execution_stats()`:
```python
def get_agent_execution_stats(self, agent_name: str, hours: int = 24) -> Dict:
    """Get execution statistics for a single agent.
    Used for platform metrics injection in dashboard (DASH-001).
    """
    cursor.execute("""
        SELECT
            COUNT(*) as task_count,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
            SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_count,
            SUM(COALESCE(cost, 0)) as total_cost,
            AVG(duration_ms) as avg_duration_ms,
            MAX(started_at) as last_execution_at
        FROM schedule_executions
        WHERE agent_name = ?
        AND started_at > datetime('now', ? || ' hours')
    """, (agent_name, f"-{hours}"))

    return {
        "task_count": row["task_count"],
        "success_count": row["success_count"] or 0,
        "failed_count": row["failed_count"] or 0,
        "running_count": row["running_count"] or 0,
        "success_rate": round((success_count / task_count * 100), 1),
        "total_cost": round(row["total_cost"] or 0, 4),
        "avg_duration_ms": int(row["avg_duration_ms"]) if row["avg_duration_ms"] else None,
        "last_execution_at": row["last_execution_at"]
    }
```

### Database Manager Delegation

**src/backend/database.py:1029-1058**:
```python
# Dashboard History (delegated to db/dashboard_history.py) - DASH-001

def capture_dashboard_snapshot(self, agent_name: str, config: dict, dashboard_mtime: str):
    return self._dashboard_history_ops.capture_dashboard_snapshot(agent_name, config, dashboard_mtime)

def get_widget_history(self, agent_name: str, widget_key: str, hours: int = 24, limit: int = 100):
    return self._dashboard_history_ops.get_widget_history(agent_name, widget_key, hours, limit)

def get_all_widget_history(self, agent_name: str, hours: int = 24):
    return self._dashboard_history_ops.get_all_widget_history(agent_name, hours)

def calculate_widget_stats(self, values: list):
    return self._dashboard_history_ops.calculate_widget_stats(values)

def get_last_captured_mtime(self, agent_name: str):
    return self._dashboard_history_ops.get_last_captured_mtime(agent_name)

def cleanup_old_dashboard_snapshots(self, days: int = 30):
    return self._dashboard_history_ops.cleanup_old_snapshots(days)

def delete_agent_dashboard_history(self, agent_name: str):
    return self._dashboard_history_ops.delete_agent_dashboard_history(agent_name)

def get_agent_execution_stats(self, agent_name: str, hours: int = 24):
    return self._schedule_ops.get_agent_execution_stats(agent_name, hours)
```

---

## Agent Layer

### Dashboard Endpoint

**docker/base-image/agent_server/routers/dashboard.py:150-229**:
```python
@router.get("/api/dashboard")
async def get_dashboard():
    """Get agent dashboard configuration."""
    dashboard_path = get_dashboard_path()  # /home/developer/dashboard.yaml

    if not dashboard_path.exists():
        return {"has_dashboard": False, ...}

    content = dashboard_path.read_text()
    config = yaml.safe_load(content)

    # Validate configuration
    errors = validate_dashboard(config)
    if errors:
        return {"has_dashboard": False, "error": f"Validation errors: {'; '.join(errors)}"}

    # Get file modification time (used for change detection)
    stat = dashboard_path.stat()
    last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

    return {
        "has_dashboard": True,
        "config": config,
        "last_modified": last_modified,
        "error": None
    }
```

### Platform Metrics Opt-Out

Agents can disable platform metrics injection by adding to `dashboard.yaml`:
```yaml
platform_metrics: false
```

---

## Response Format

### Enriched Widget Response

```json
{
  "type": "metric",
  "label": "Revenue",
  "value": 12500,
  "unit": "$",
  "history": {
    "values": [
      {"t": "2026-02-23T08:00:00Z", "v": 10000},
      {"t": "2026-02-23T12:00:00Z", "v": 11200},
      {"t": "2026-02-23T16:00:00Z", "v": 12500}
    ],
    "trend": "up",
    "trend_percent": 12.5,
    "min": 10000,
    "max": 12500,
    "avg": 11233.33
  }
}
```

### Platform Metrics Section Response

```json
{
  "title": "Platform Metrics",
  "description": "Automatically tracked by Trinity",
  "layout": "grid",
  "columns": 4,
  "platform_managed": true,
  "widgets": [
    {
      "type": "metric",
      "id": "__platform_tasks",
      "label": "Tasks (24h)",
      "value": 47,
      "platform_source": "executions.count"
    },
    {
      "type": "metric",
      "id": "__platform_success_rate",
      "label": "Success Rate",
      "value": "95.7%",
      "color": "green",
      "platform_source": "executions.success_rate"
    },
    {
      "type": "metric",
      "id": "__platform_cost",
      "label": "Cost (24h)",
      "value": "$2.34",
      "platform_source": "executions.cost"
    },
    {
      "type": "status",
      "id": "__platform_health",
      "label": "Health",
      "value": "Healthy",
      "color": "green",
      "platform_source": "health.status"
    }
  ]
}
```

---

## Side Effects

- **No WebSocket broadcasts**: Dashboard is polled, not pushed
- **No Audit Log**: Read-only operation (snapshot capture is internal)
- **Database Write**: Widget values captured on each dashboard fetch (if mtime changed)

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Not authenticated | 401 | Unauthorized |
| No access to agent | 403 | You don't have permission to access this agent |
| Agent not found | 404 | Agent not found |
| Agent not running | 200 | `error: "Agent must be running to read dashboard"` |
| No dashboard.yaml | 200 | `error: "No dashboard.yaml found..."` |
| YAML parse error | 200 | `error: "YAML parse error at line X, column Y: ..."` |

---

## Security Considerations

- **Authorization**: User must have access to agent (owner or shared)
- **Query Parameter Validation**: `history_hours` bounded to 1-168
- **No PII in History**: Only numeric values captured, labels stored for reference
- **Platform Metrics Source Tracking**: `platform_source` field identifies data origin

---

## Performance Considerations

- **Batch History Fetch**: `get_all_widget_history()` fetches all widget history in single query
- **Index Optimization**: Composite indexes on `(agent_name, captured_at)` and `(agent_name, widget_key, captured_at)`
- **Change Detection**: Snapshots only captured when `dashboard.yaml` mtime changes (not on every request)
- **Cleanup**: `cleanup_old_dashboard_snapshots(days=30)` for maintenance

---

## Widget Key Generation

Widgets are identified by:
1. **Explicit ID**: If widget has `id` field in YAML, use that
2. **Position-based**: Otherwise generate as `s{section_idx}_w{widget_idx}`

Example:
```yaml
sections:
  - widgets:
      - type: metric       # key: "s0_w0"
        label: Revenue
      - type: metric       # key: "revenue_metric"
        id: revenue_metric
        label: Revenue
```

---

## Trend Calculation

Trend is calculated by comparing first-half average to second-half average:

```python
mid = len(values) // 2
first_half_avg = sum(values[:mid]) / mid
second_half_avg = sum(values[mid:]) / (len(values) - mid)
trend_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100

if trend_percent > 5:
    trend = "up"
elif trend_percent < -5:
    trend = "down"
else:
    trend = "stable"
```

---

## Testing

### Test Steps

1. **History Capture**
   - Create agent with `dashboard.yaml` containing metric widget
   - Fetch dashboard multiple times with different values
   - Verify `agent_dashboard_values` table has records

2. **Sparkline Rendering**
   - Fetch dashboard with `include_history=true`
   - Verify widgets have `history.values` array
   - Verify SparklineChart renders in UI

3. **Platform Metrics**
   - Run some scheduled executions for agent
   - Fetch dashboard with `include_platform_metrics=true`
   - Verify "Platform Metrics" section appears with correct stats

4. **Platform Metrics Opt-Out**
   - Add `platform_metrics: false` to `dashboard.yaml`
   - Fetch dashboard
   - Verify no platform section in response

5. **Query Parameters**
   - Test `history_hours=1` vs `history_hours=168`
   - Test `include_history=false`
   - Test `include_platform_metrics=false`

---

## Related Flows

- **Upstream**: [agent-dashboard.md](agent-dashboard.md) - Base dashboard feature this extends
- **Upstream**: [agent-monitoring.md](agent-monitoring.md) - Health status used in platform metrics
- **Upstream**: [scheduling.md](scheduling.md) - Execution stats used in platform metrics
- **Similar**: [agent-custom-metrics.md](agent-custom-metrics.md) - Legacy metrics (replaced by dashboards)

---

## Revision History

| Date | Change |
|------|--------|
| 2026-02-23 | Initial documentation for DASH-001 - Dashboard history tracking, sparkline visualization, platform metrics injection |
