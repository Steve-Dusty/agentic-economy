# Dynamic Dashboards - Requirements Specification

> **Requirement ID**: DASH-001
> **Priority**: MEDIUM
> **Status**: Implemented
> **Created**: 2026-02-23
> **Implemented**: 2026-02-23
> **Author**: Claude Code

## Overview

Extend the Agent Dashboard system to support dynamic, historical data visualization while preserving the agent-controlled dashboard.yaml paradigm.

### Problem Statement

Current dashboards are **static snapshots**:
- Widget values are hardcoded in `dashboard.yaml` (e.g., `value: 1234`)
- No historical trends - just point-in-time values
- No platform metrics - agents must manually track executions, costs, health
- When an agent updates values, previous values are lost

### Goals

1. **Track dashboard value history** - When agents update dashboard.yaml, capture values for timeline visualization
2. **Append platform metrics** - Trinity automatically adds execution stats, costs, health to all dashboards
3. **Enable sparkline/trend visualization** - Show historical trends inline with metric widgets
4. **Preserve agent control** - Agents still own their dashboard.yaml; platform enriches, never overwrites

### Non-Goals

- Changing the dashboard.yaml schema (backward compatible)
- Real-time streaming (polling with auto-refresh is sufficient)
- Complex charting (sparklines only, full analytics elsewhere)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Agent Container                                                    │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ /home/developer/dashboard.yaml                                │  │
│  │   - Agent-defined widgets with static or dynamic values       │  │
│  │   - File modification time tracked via stat()                 │  │
│  │   - GET /api/dashboard returns config + last_modified         │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Trinity Backend                                                    │
│                                                                     │
│  GET /api/agent-dashboard/{name}                                    │
│    │                                                                │
│    ├─► Fetch dashboard from agent container                        │
│    │                                                                │
│    ├─► CHANGE DETECTION (new)                                      │
│    │     Compare last_modified with cached value                    │
│    │     If changed → capture all metric widget values to DB       │
│    │                                                                │
│    ├─► HISTORY ENRICHMENT (new)                                    │
│    │     Query agent_dashboard_values for sparkline data           │
│    │     Inject `history` and `trend` fields into metric widgets   │
│    │                                                                │
│    ├─► PLATFORM METRICS SECTION (new)                              │
│    │     Append "Platform Metrics" section with:                   │
│    │     - Execution stats (24h count, success rate, cost)         │
│    │     - Health status (uptime, latency)                         │
│    │     - Context usage trends                                    │
│    │                                                                │
│    └─► Return enriched dashboard response                          │
│                                                                     │
│  Database Tables:                                                   │
│    agent_dashboard_values (NEW) - Historical widget values         │
│    agent_health_checks (existing) - Health metrics                 │
│    schedule_executions (existing) - Execution stats                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (DashboardPanel.vue)                                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Agent-Defined Section                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                   │   │
│  │  │ Users: 1,234 ↑  │  │ Revenue: $5.2K  │                   │   │
│  │  │ [▁▂▃▄▅▆▇█▇▆]   │  │ [▁▁▂▃▅▆▇█▇▆]    │  ← Sparklines     │   │
│  │  └─────────────────┘  └─────────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Platform Metrics (auto-appended)                           │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                   │   │
│  │  │ Tasks (24h): 47 │  │ Cost: $2.34     │                   │   │
│  │  │ [▂▃▄▃▅▆▇▆▅▄]   │  │ [▁▂▂▃▄▅▆▇▆▅]    │                   │   │
│  │  └─────────────────┘  └─────────────────┘                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                   │   │
│  │  │ Success: 94.2%  │  │ Uptime: 99.8%   │                   │   │
│  │  └─────────────────┘  └─────────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Feature 1: Dashboard Value History Tracking (DASH-001a)

### Description

When an agent updates their `dashboard.yaml` file, Trinity captures all numeric metric values with timestamps. This enables historical trend visualization.

### Change Detection Mechanism

The agent server already returns `last_modified` (file mtime) with each dashboard response. Trinity caches this per-agent and compares on each fetch:

```python
# Pseudocode
cached_mtime = dashboard_mtime_cache.get(agent_name)
current_mtime = dashboard_response["last_modified"]

if cached_mtime != current_mtime:
    # File changed - capture all metric values
    capture_dashboard_snapshot(agent_name, dashboard_response["config"])
    dashboard_mtime_cache[agent_name] = current_mtime
```

### Database Schema

**New Table: `agent_dashboard_values`**

```sql
CREATE TABLE agent_dashboard_values (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,

    -- Widget identification
    widget_key TEXT NOT NULL,           -- Composite: "{section_idx}:{widget_idx}" or explicit "id" from YAML
    widget_label TEXT,                  -- Human-readable label for display
    widget_type TEXT NOT NULL,          -- "metric", "progress", "status"

    -- Captured value
    value_numeric REAL,                 -- For numeric values (metric, progress)
    value_text TEXT,                    -- For string values (status)

    -- Context
    dashboard_mtime TEXT NOT NULL,      -- File mtime when captured
    captured_at TEXT NOT NULL,          -- ISO timestamp with Z suffix

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX idx_dashboard_values_agent_time
    ON agent_dashboard_values(agent_name, captured_at DESC);
CREATE INDEX idx_dashboard_values_widget
    ON agent_dashboard_values(agent_name, widget_key, captured_at DESC);
CREATE INDEX idx_dashboard_values_cleanup
    ON agent_dashboard_values(created_at);
```

### Widget Key Generation

Widgets are identified by a stable key:

1. **Explicit ID** (preferred): If widget has `id` field in YAML, use it
2. **Position-based** (fallback): `"{section_index}:{widget_index}"`
3. **Label-based** (alternative): Sanitized label if unique

```yaml
# Agent can provide explicit IDs for stable tracking:
sections:
  - widgets:
    - type: metric
      id: "daily_users"        # ← Stable key across YAML restructuring
      label: "Daily Users"
      value: 1234
```

### Capture Logic

Only capture trackable widget types:

| Widget Type | Captured | Value Field |
|-------------|----------|-------------|
| `metric` | ✅ Yes | `value_numeric` (parse float from value) |
| `progress` | ✅ Yes | `value_numeric` (0-100) |
| `status` | ✅ Yes | `value_text` (color/state) |
| `text` | ❌ No | - |
| `markdown` | ❌ No | - |
| `table` | ❌ No | - |
| `list` | ❌ No | - |
| `link` | ❌ No | - |
| `image` | ❌ No | - |
| `divider` | ❌ No | - |
| `spacer` | ❌ No | - |

### Retention Policy

- **Default**: 30 days
- **Cleanup**: Daily job deletes records older than retention period
- **Configurable**: Via settings or environment variable

### API Changes

**Modified Response**: `GET /api/agent-dashboard/{name}`

```json
{
  "agent_name": "my-agent",
  "has_dashboard": true,
  "config": {
    "title": "My Dashboard",
    "sections": [
      {
        "widgets": [
          {
            "type": "metric",
            "label": "Daily Users",
            "value": 1234,
            "history": {                    // NEW - injected by platform
              "values": [
                {"t": "2026-02-23T10:00:00Z", "v": 1180},
                {"t": "2026-02-23T11:00:00Z", "v": 1205},
                {"t": "2026-02-23T12:00:00Z", "v": 1234}
              ],
              "trend": "up",                // "up", "down", "stable"
              "trend_percent": 4.6,
              "min": 1150,
              "max": 1250,
              "avg": 1206
            }
          }
        ]
      }
    ]
  },
  "last_modified": "2026-02-23T12:30:00Z",
  "platform_metrics_enabled": true          // NEW
}
```

**New Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_history` | bool | `true` | Include sparkline history data |
| `history_hours` | int | `24` | Hours of history to include |
| `include_platform_metrics` | bool | `true` | Append platform metrics section |

---

## Feature 2: Platform Metrics Section (DASH-001b)

### Description

Trinity automatically appends a "Platform Metrics" section to every agent dashboard, showing execution statistics, costs, and health data that the platform tracks.

### Metrics Included

| Metric | Source | Widget Type |
|--------|--------|-------------|
| Tasks (24h) | `schedule_executions` COUNT | `metric` with sparkline |
| Success Rate | `schedule_executions` calculation | `metric` (percentage) |
| Total Cost (24h) | `schedule_executions` SUM(cost) | `metric` with sparkline |
| Avg Duration | `schedule_executions` AVG(duration_ms) | `metric` |
| Uptime (24h) | `agent_health_checks` | `metric` (percentage) |
| Health Status | `agent_health_checks` latest | `status` (color-coded) |
| Context Usage | `agent_health_checks` latest | `progress` |

### Platform Section Structure

```json
{
  "title": "Platform Metrics",
  "description": "Automatically tracked by Trinity",
  "layout": "grid",
  "columns": 4,
  "platform_managed": true,           // Flag indicating this section is auto-generated
  "widgets": [
    {
      "type": "metric",
      "label": "Tasks (24h)",
      "value": 47,
      "history": { ... },
      "platform_source": "executions.count"
    },
    {
      "type": "metric",
      "label": "Success Rate",
      "value": "94.2%",
      "trend": "up",
      "platform_source": "executions.success_rate"
    },
    {
      "type": "metric",
      "label": "Cost (24h)",
      "value": "$2.34",
      "unit": "USD",
      "history": { ... },
      "platform_source": "executions.total_cost"
    },
    {
      "type": "status",
      "label": "Health",
      "value": "Healthy",
      "color": "green",
      "platform_source": "health.status"
    },
    {
      "type": "progress",
      "label": "Context",
      "value": 45,
      "color": "blue",
      "platform_source": "health.context_percent"
    },
    {
      "type": "metric",
      "label": "Uptime",
      "value": "99.8%",
      "platform_source": "health.uptime"
    }
  ]
}
```

### Data Sources

Platform metrics are populated from existing database tables:

```python
# Execution stats
exec_stats = db.get_agent_execution_stats(agent_name, hours=24)
# Returns: task_count, success_count, failed_count, total_cost, avg_duration_ms

# Health stats
health = db.get_latest_health_check(agent_name, check_type="aggregate")
# Returns: status, cpu_percent, memory_percent, context_percent, uptime

# Historical data for sparklines
exec_history = db.get_execution_counts_by_hour(agent_name, hours=24)
cost_history = db.get_execution_costs_by_hour(agent_name, hours=24)
```

### Opt-Out Mechanism

Agents can disable platform metrics by adding to their `dashboard.yaml`:

```yaml
title: "My Dashboard"
platform_metrics: false              # Disable auto-appended section
sections:
  - ...
```

---

## Feature 3: Sparkline Widget Enhancement (DASH-001c)

### Description

Enhance the existing `metric` widget type to optionally display inline sparkline charts showing historical trends.

### Frontend Changes

**DashboardPanel.vue** modifications:

1. Import existing `SparklineChart.vue` component
2. Detect `history` field on metric widgets
3. Render sparkline below the value

```vue
<!-- Metric widget with optional sparkline -->
<div v-if="widget.type === 'metric'" class="metric-widget">
  <div class="label">{{ widget.label }}</div>
  <div class="value-row">
    <span class="value">{{ formatValue(widget.value) }}</span>
    <span v-if="widget.history?.trend" :class="getTrendClass(widget.history.trend)">
      {{ getTrendIcon(widget.history.trend) }}
    </span>
  </div>
  <!-- Sparkline chart if history available -->
  <SparklineChart
    v-if="widget.history?.values?.length > 1"
    :data="widget.history.values.map(v => v.v)"
    :color="getSparklineColor(widget)"
    :width="120"
    :height="24"
    class="mt-1"
  />
</div>
```

### Sparkline Data Format

```typescript
interface WidgetHistory {
  values: Array<{
    t: string;  // ISO timestamp
    v: number;  // Numeric value
  }>;
  trend: 'up' | 'down' | 'stable';
  trend_percent: number;
  min: number;
  max: number;
  avg: number;
}
```

### Trend Calculation

```python
def calculate_trend(values: List[float]) -> tuple[str, float]:
    """Calculate trend direction and percentage change."""
    if len(values) < 2:
        return ("stable", 0.0)

    first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
    second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)

    if first_half_avg == 0:
        return ("stable", 0.0)

    change_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100

    if change_percent > 5:
        return ("up", change_percent)
    elif change_percent < -5:
        return ("down", change_percent)
    else:
        return ("stable", change_percent)
```

---

## Implementation Plan

### Phase 1: Database & Capture (Backend)

1. Add `agent_dashboard_values` table to `db/schema.py`
2. Create `DashboardOperations` class in `db/dashboard_history.py`
3. Implement change detection in `services/agent_service/dashboard.py`
4. Add capture logic for metric/progress/status widgets
5. Add retention cleanup to daily maintenance

**Files**:
- `src/backend/db/schema.py` (add table)
- `src/backend/db/dashboard_history.py` (new file)
- `src/backend/database.py` (expose operations)
- `src/backend/services/agent_service/dashboard.py` (modify)

### Phase 2: History Enrichment (Backend)

1. Query historical values when serving dashboard
2. Calculate sparkline data (values array, min/max/avg)
3. Calculate trend direction and percentage
4. Inject `history` field into widget responses

**Files**:
- `src/backend/services/agent_service/dashboard.py` (modify)

### Phase 3: Platform Metrics Section (Backend)

1. Query execution stats from `schedule_executions`
2. Query health stats from `agent_health_checks`
3. Build platform metrics section structure
4. Append to dashboard response (respecting opt-out)

**Files**:
- `src/backend/services/agent_service/dashboard.py` (modify)
- `src/backend/db/schedules.py` (add aggregation methods if needed)

### Phase 4: Frontend Sparklines (Frontend)

1. Import `SparklineChart` into `DashboardPanel.vue`
2. Add sparkline rendering for metric widgets with history
3. Add trend indicators (↑ ↓ →)
4. Style platform metrics section distinctly

**Files**:
- `src/frontend/src/components/DashboardPanel.vue` (modify)

### Phase 5: Testing & Documentation

1. Add API tests for new query parameters
2. Test change detection with mock dashboard updates
3. Test retention cleanup
4. Update feature flow documentation

---

## Database Operations

### New Methods (DashboardOperations class)

```python
class DashboardOperations:
    def capture_dashboard_snapshot(
        self,
        agent_name: str,
        config: dict,
        dashboard_mtime: str
    ) -> int:
        """Capture all trackable widget values. Returns count of values stored."""

    def get_widget_history(
        self,
        agent_name: str,
        widget_key: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """Get historical values for a specific widget."""

    def get_all_widget_history(
        self,
        agent_name: str,
        hours: int = 24
    ) -> Dict[str, List]:
        """Get history for all widgets, keyed by widget_key."""

    def calculate_widget_stats(
        self,
        values: List[Dict]
    ) -> Dict:
        """Calculate min, max, avg, trend from value list."""

    def cleanup_old_snapshots(
        self,
        days: int = 30
    ) -> int:
        """Delete snapshots older than N days. Returns count deleted."""
```

### New Aggregation Methods (ScheduleOperations class)

```python
# Add to existing db/schedules.py

def get_execution_counts_by_hour(
    self,
    agent_name: str,
    hours: int = 24
) -> List[Dict]:
    """Get execution counts bucketed by hour for sparkline."""

def get_execution_costs_by_hour(
    self,
    agent_name: str,
    hours: int = 24
) -> List[Dict]:
    """Get total cost bucketed by hour for sparkline."""
```

---

## API Specification

### Modified Endpoint

**GET /api/agent-dashboard/{name}**

**Query Parameters** (all optional):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_history` | boolean | `true` | Include sparkline history in widget responses |
| `history_hours` | integer | `24` | Hours of history to include (1-168) |
| `include_platform_metrics` | boolean | `true` | Append platform metrics section |

**Response** (enriched):

```json
{
  "agent_name": "my-agent",
  "has_dashboard": true,
  "config": {
    "title": "Agent Dashboard",
    "sections": [
      {
        "title": "Business Metrics",
        "widgets": [
          {
            "type": "metric",
            "label": "Revenue",
            "value": 5234.50,
            "unit": "$",
            "history": {
              "values": [
                {"t": "2026-02-22T12:00:00Z", "v": 4800.00},
                {"t": "2026-02-22T18:00:00Z", "v": 5100.00},
                {"t": "2026-02-23T00:00:00Z", "v": 5234.50}
              ],
              "trend": "up",
              "trend_percent": 9.1,
              "min": 4500.00,
              "max": 5300.00,
              "avg": 4950.00
            }
          }
        ]
      },
      {
        "title": "Platform Metrics",
        "platform_managed": true,
        "layout": "grid",
        "columns": 4,
        "widgets": [
          {
            "type": "metric",
            "label": "Tasks (24h)",
            "value": 47,
            "platform_source": "executions.count",
            "history": { ... }
          }
        ]
      }
    ]
  },
  "last_modified": "2026-02-23T12:30:00Z",
  "snapshot_captured": true,
  "history_hours": 24
}
```

---

## Testing

### Unit Tests

1. **Change detection**: Verify capture triggers only on mtime change
2. **Widget key generation**: Test explicit ID, position-based, label-based
3. **Value extraction**: Test parsing numeric values from various formats
4. **Trend calculation**: Test up/down/stable detection
5. **Retention cleanup**: Verify old records deleted correctly

### Integration Tests

1. **End-to-end capture**: Update dashboard.yaml, verify values stored
2. **History retrieval**: Query history after multiple captures
3. **Platform metrics**: Verify execution stats injected correctly
4. **Opt-out**: Verify platform_metrics: false respected

### Manual Testing

1. Create agent with dashboard.yaml containing metrics
2. Update values several times over an hour
3. View dashboard and verify sparklines appear
4. Verify platform metrics section shows correct data
5. Check 24h history populates correctly

---

## Security Considerations

1. **No credential exposure**: Dashboard values are business metrics only
2. **Access control**: Existing agent access checks apply
3. **Rate limiting**: Capture only on change, not every request
4. **Data isolation**: Each agent's history is separate

---

## Performance Considerations

1. **Capture overhead**: Only on file change (tracked via mtime)
2. **Query efficiency**: Indexed by (agent_name, captured_at DESC)
3. **Response size**: History limited to 100 values per widget
4. **Retention**: 30-day default prevents unbounded growth

---

## Future Enhancements

1. **Custom retention per agent**: Allow agents to specify retention in dashboard.yaml
2. **Alert thresholds**: Define alerts when metric crosses threshold
3. **Comparison views**: Compare current vs. previous period
4. **Export**: Download historical data as CSV
5. **Aggregation options**: Hourly/daily/weekly bucketing

---

## Related Documents

- `docs/memory/feature-flows/agent-dashboard.md` - Current dashboard implementation
- `docs/memory/feature-flows/subscription-management.md` - Platform metrics pattern
- `docs/requirements/AGENT_MONITORING.md` - Health check data source (MON-001)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-23 | Initial draft |
| 2026-02-23 | Implemented all phases - schema, operations, service, API, frontend |
