# Agent Dashboard Requirements

> **Status**: Draft
> **Created**: 2026-01-12
> **Author**: Claude Code
> **Replaces**: Custom Metrics (Req 9.9) - Full replacement, no backward compatibility

---

## Executive Summary

Replace the Metrics tab with a flexible **Agent Dashboard** system. Agents author a single `dashboard.yaml` file that Trinity renders as a custom UI panel. The agent controls both layout and data.

**Key Principle**: Agent controls the template and data. Trinity renders it.

---

## Problem Statement

### Current Limitations (Metrics System)

1. **Rigid Schema**: Only 6 predefined metric types
2. **No Layout Control**: Fixed 4-column grid
3. **Limited Content**: Only numeric/status values - no text, tables, lists
4. **Two-File Approach**: Requires `template.yaml` (definitions) + `metrics.json` (values)
5. **No Context**: Can't display explanatory text or documentation

### Solution

Single `dashboard.yaml` file with flexible widget types and layout control.

---

## Dashboard File Format

### Location

`/home/developer/dashboard.yaml` (primary) or `/home/developer/workspace/dashboard.yaml` (fallback)

### Root Structure

```yaml
title: string        # Required: Dashboard title
description: string  # Optional: Subtitle
refresh: number      # Optional: Auto-refresh seconds (default: 30, min: 5)
sections: array      # Required: List of sections
```

### Section Structure

```yaml
sections:
  - title: string        # Optional: Section header
    description: string  # Optional: Section description
    layout: string       # Optional: "grid" (default), "list"
    columns: number      # Optional: 1-4 for grid layout (default: 3)
    collapsed: boolean   # Optional: Start collapsed (default: false)
    widgets: array       # Required: List of widgets
```

---

## Widget Types

### 1. Metric Widget
Display a single numeric value.

```yaml
- type: metric
  label: "Messages Sent"      # Required
  value: 42                   # Required: number or string
  unit: "msgs"                # Optional
  description: "Total..."     # Optional: tooltip
  trend: "up"                 # Optional: "up", "down", "neutral"
  trend_value: "+12%"         # Optional: trend label
```

### 2. Status Widget
Display a colored status badge.

```yaml
- type: status
  label: "Current State"      # Required
  value: "active"             # Required
  color: "green"              # Required: green, red, yellow, gray, blue, orange, purple
  description: "Agent is..."  # Optional
```

### 3. Progress Widget
Display a progress bar.

```yaml
- type: progress
  label: "Goal Progress"      # Required
  value: 75                   # Required: 0-100
  max: 100                    # Optional: default 100
  color: "blue"               # Optional
  show_value: true            # Optional: show percentage text (default: true)
```

### 4. Text Widget
Display simple text.

```yaml
- type: text
  content: "Last updated..."  # Required
  size: "sm"                  # Optional: "xs", "sm", "md", "lg"
  color: "gray"               # Optional
  align: "left"               # Optional: "left", "center", "right"
```

### 5. Markdown Widget
Display rich text from markdown.

```yaml
- type: markdown
  content: |                  # Required
    ## Summary
    Latest research shows **interesting** trends...

    - Finding 1
    - Finding 2
```

### 6. Table Widget
Display tabular data.

```yaml
- type: table
  title: "Recent Activity"    # Optional
  columns:                    # Required: array of column definitions
    - key: "date"
      label: "Date"
    - key: "action"
      label: "Action"
    - key: "status"
      label: "Status"
  rows:                       # Required: array of row objects
    - date: "2025-01-12"
      action: "Research"
      status: "Complete"
  max_rows: 10                # Optional: limit displayed rows
```

### 7. List Widget
Display a bullet or numbered list.

```yaml
- type: list
  title: "Top Opportunities"  # Optional
  style: "bullet"             # Optional: "bullet", "number", "none" (default: "bullet")
  items:                      # Required
    - "Opportunity 1"
    - "Opportunity 2"
  max_items: 10               # Optional
```

### 8. Link Widget
Display a clickable link or button.

```yaml
- type: link
  label: "View Report"        # Required
  url: "/files/report.pdf"    # Required
  style: "button"             # Optional: "link", "button" (default: "link")
  color: "blue"               # Optional
  external: false             # Optional: open in new tab
```

### 9. Image Widget
Display an image.

```yaml
- type: image
  src: "/files/chart.png"     # Required: relative path to agent files
  alt: "Chart description"    # Required
  caption: "Figure 1..."      # Optional
```

### 10. Divider Widget
Horizontal line separator.

```yaml
- type: divider
```

### 11. Spacer Widget
Vertical space.

```yaml
- type: spacer
  size: "md"                  # Optional: "sm", "md", "lg"
```

---

## Layout System

### Grid Layout (default)
- Responsive: 1 col (mobile) → 2 cols (tablet) → N cols (desktop)
- `columns: 1-4` controls max columns
- Widgets fill left-to-right, top-to-bottom
- Widget can span columns with `colspan: 2`

### List Layout
- Single column, full width
- Best for tables, markdown, wide content

---

## API Specification

### Agent Server Endpoint

**GET /api/dashboard**

```json
{
  "has_dashboard": true,
  "config": {
    "title": "Research Dashboard",
    "refresh": 30,
    "sections": [...]
  },
  "last_modified": "2025-01-12T10:30:00Z",
  "error": null
}
```

If no dashboard.yaml:
```json
{
  "has_dashboard": false,
  "config": null,
  "error": "No dashboard.yaml found"
}
```

If parse error:
```json
{
  "has_dashboard": false,
  "config": null,
  "error": "YAML parse error at line 15: ..."
}
```

### Backend Endpoint

**GET /api/agents/{name}/dashboard**

Same response as agent server, plus:
- `agent_name`: Agent identifier
- `status`: "running" or "stopped"

---

## Implementation Plan

### Step 1: Agent Server
1. Create `/api/dashboard` endpoint in `agent_server/routers/info.py`
2. Read and parse `dashboard.yaml`
3. Return structured response

### Step 2: Backend
1. Create `services/agent_service/dashboard.py`
2. Add `GET /api/agents/{name}/dashboard` to router
3. Proxy to agent server with access control

### Step 3: Frontend
1. Create `DashboardPanel.vue` main component
2. Create widget components in `components/dashboard/`:
   - `MetricWidget.vue`
   - `StatusWidget.vue`
   - `ProgressWidget.vue`
   - `TextWidget.vue`
   - `MarkdownWidget.vue`
   - `TableWidget.vue`
   - `ListWidget.vue`
   - `LinkWidget.vue`
   - `ImageWidget.vue`
   - `DividerWidget.vue`
   - `SpacerWidget.vue`
3. Add store action `getAgentDashboard()`
4. Replace Metrics tab with Dashboard in `AgentDetail.vue`

### Step 4: Cleanup
1. Delete `MetricsPanel.vue`
2. Delete `/api/metrics` from agent server
3. Delete `services/agent_service/metrics.py`
4. Remove metrics route from backend
5. Remove `getAgentMetrics` from store

### Step 5: Documentation
1. Update `TRINITY_COMPATIBLE_AGENT_GUIDE.md` - replace Custom Metrics with Dashboard
2. Create `feature-flows/agent-dashboard.md`
3. Archive `feature-flows/agent-custom-metrics.md`
4. Update `requirements.md`

### Step 6: Templates
1. Create `dashboard.yaml` for `demo-researcher`
2. Create `dashboard.yaml` for `demo-analyst`
3. Create `dashboard.yaml` for `trinity-system`
4. Remove `metrics:` from template.yaml files
5. Delete `metrics.json` files

---

## Files to Create

| File | Purpose |
|------|---------|
| `docker/base-image/agent_server/routers/dashboard.py` | Agent server endpoint |
| `src/backend/services/agent_service/dashboard.py` | Backend service |
| `src/frontend/src/components/DashboardPanel.vue` | Main dashboard component |
| `src/frontend/src/components/dashboard/MetricWidget.vue` | Metric widget |
| `src/frontend/src/components/dashboard/StatusWidget.vue` | Status widget |
| `src/frontend/src/components/dashboard/ProgressWidget.vue` | Progress widget |
| `src/frontend/src/components/dashboard/TextWidget.vue` | Text widget |
| `src/frontend/src/components/dashboard/MarkdownWidget.vue` | Markdown widget |
| `src/frontend/src/components/dashboard/TableWidget.vue` | Table widget |
| `src/frontend/src/components/dashboard/ListWidget.vue` | List widget |
| `src/frontend/src/components/dashboard/LinkWidget.vue` | Link widget |
| `src/frontend/src/components/dashboard/ImageWidget.vue` | Image widget |
| `src/frontend/src/components/dashboard/DividerWidget.vue` | Divider widget |
| `src/frontend/src/components/dashboard/SpacerWidget.vue` | Spacer widget |
| `docs/memory/feature-flows/agent-dashboard.md` | Feature flow doc |
| `config/agent-templates/demo-researcher/dashboard.yaml` | Example |
| `config/agent-templates/demo-analyst/dashboard.yaml` | Example |
| `config/agent-templates/trinity-system/dashboard.yaml` | Example |

## Files to Delete

| File | Reason |
|------|--------|
| `src/frontend/src/components/MetricsPanel.vue` | Replaced by DashboardPanel |
| `src/backend/services/agent_service/metrics.py` | Replaced by dashboard.py |
| `tests/test_agent_metrics.py` | Replaced by dashboard tests |
| `config/agent-templates/*/metrics.json` | No longer used |
| `docs/memory/feature-flows/agent-custom-metrics.md` | Move to archive |

## Files to Modify

| File | Changes |
|------|---------|
| `docker/base-image/agent_server/routers/info.py` | Remove /api/metrics, add /api/dashboard |
| `src/backend/routers/agents.py` | Remove metrics endpoint, add dashboard endpoint |
| `src/backend/services/agent_service/__init__.py` | Export dashboard, remove metrics |
| `src/frontend/src/views/AgentDetail.vue` | Replace Metrics tab with Dashboard |
| `src/frontend/src/stores/agents.js` | Replace getAgentMetrics with getAgentDashboard |
| `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` | Replace Custom Metrics section with Dashboard |
| `docs/memory/requirements.md` | Update Req 9.9 |
| `docs/memory/roadmap.md` | Add Dashboard item |
| `config/agent-templates/*/template.yaml` | Remove metrics: section |

---

## Example Dashboard

```yaml
# /home/developer/dashboard.yaml
title: "Research Dashboard"
description: "Autonomous research findings and status"
refresh: 60

sections:
  - title: "Overview"
    layout: grid
    columns: 4
    widgets:
      - type: status
        label: "Status"
        value: "active"
        color: "green"

      - type: metric
        label: "Research Cycles"
        value: 42
        trend: "up"
        trend_value: "+5 today"

      - type: metric
        label: "Findings"
        value: 156

      - type: progress
        label: "Daily Goal"
        value: 75

  - title: "Recent Findings"
    layout: list
    widgets:
      - type: table
        columns:
          - key: "date"
            label: "Date"
          - key: "topic"
            label: "Topic"
          - key: "score"
            label: "Score"
        rows:
          - date: "2025-01-12"
            topic: "AI Agent Architectures"
            score: "8.5"
          - date: "2025-01-11"
            topic: "Market Trends"
            score: "7.2"

      - type: markdown
        content: |
          ## Summary

          Today's research focused on **AI agent architectures**.

          Key findings:
          - Hierarchical delegation patterns
          - Persistent memory strategies
          - Event-driven coordination

      - type: link
        label: "View Full Report"
        url: "/files/reports/latest.pdf"
        style: "button"
```

---

## Success Criteria

1. Agents define dashboards via single `dashboard.yaml` file
2. All 11 widget types render correctly
3. Auto-refresh works with configurable interval
4. Error handling shows helpful messages
5. Documentation updated
6. Example dashboards created for demo templates
7. All metrics code removed

---

## Future Enhancements (Not in Scope)

- Chart widget (bar, line, pie)
- Widget actions (buttons that trigger agent commands)
- Dashboard history/snapshots
- Multiple dashboards per agent
- Dashboard templates/presets
