# Feature: Agent Dashboard

> **Last Updated**: 2026-02-12 - Dashboard tab now conditionally hidden when agent doesn't have `dashboard.yaml` file.

## Overview

Agent-defined dashboard system that replaces the static Metrics tab. Agents define a `dashboard.yaml` file with declarative widget configuration, and Trinity renders it in the Dashboard tab. The Dashboard tab is now **conditionally visible** - it only appears when the agent has a `dashboard.yaml` file.

## User Story

As an agent developer, I want to define a custom dashboard in YAML so that I can expose agent-specific metrics, status, and data without modifying Trinity platform code.

## Entry Points

- **UI**: `src/frontend/src/views/AgentDetail.vue:88-90` - Dashboard tab renders `DashboardPanel` component
- **Tab Visibility**: `src/frontend/src/views/AgentDetail.vue:442-444` - Dashboard tab only shown if `hasDashboard.value === true`
- **API**: `GET /api/agent-dashboard/{name}` - Fetches dashboard configuration from agent

## Dashboard Tab Conditional Visibility (2026-02-12)

The Dashboard tab is now **conditionally hidden** when an agent doesn't have a `dashboard.yaml` file. This provides a cleaner UI for agents that don't define custom dashboards.

### Implementation

**State** (`AgentDetail.vue:269`):
```javascript
const hasDashboard = ref(false)
```

**Check Function** (`AgentDetail.vue:491-502`):
```javascript
async function checkDashboardExists() {
  if (!agent.value?.name) {
    hasDashboard.value = false
    return
  }
  try {
    const response = await agentsStore.getAgentDashboard(agent.value.name)
    hasDashboard.value = response?.has_dashboard === true
  } catch (err) {
    hasDashboard.value = false
  }
}
```

**Tab Definition** (`AgentDetail.vue:442-444`):
```javascript
// Dashboard tab - only show if agent has a dashboard.yaml file
if (hasDashboard.value) {
  tabs.push({ id: 'dashboard', label: 'Dashboard' })
}
```

**Triggers**:
1. On mount - if agent is running (`AgentDetail.vue:588-590`)
2. On agent status change to 'running' (`AgentDetail.vue:545`)
3. On route change to different agent (`AgentDetail.vue:521-523`)
4. On component reactivation (`AgentDetail.vue:610-612`)

**Reset**:
- When agent stops, `hasDashboard` is reset to `false` (`AgentDetail.vue:552`)
- When navigating to different agent (`AgentDetail.vue:510`)

## Architecture

```
+------------------+     +-------------------+     +----------------------+
| DashboardPanel   | --> | Backend Router    | --> | Agent Server         |
| (Vue Component)  |     | /api/agent-       |     | /api/dashboard       |
|                  |     | dashboard/{name}  |     |                      |
+------------------+     +-------------------+     +----------------------+
        |                        |                         |
        |                        | httpx                   |
        v                        v                         v
  agents.js store         dashboard.py service      dashboard.yaml file
  getAgentDashboard()     get_agent_dashboard_logic  ~/dashboard.yaml
```

## Frontend Layer

### Components

**AgentDetail.vue:88-89** - Tab integration
```html
<!-- Dashboard Tab Content -->
<div v-if="activeTab === 'dashboard'" class="p-6">
  <DashboardPanel :agent-name="agent.name" :agent-status="agent.status" />
</div>
```

**AgentDetail.vue:226, 417** - Component import and tab definition
```javascript
import DashboardPanel from '../components/DashboardPanel.vue'
// ...
{ id: 'dashboard', label: 'Dashboard' }
```

**DashboardPanel.vue** - Main dashboard renderer (509 lines)
- Line 4-6: Loading state with spinner
- Line 9-19: Agent not running state
- Line 22-32: Error state with error message display
- Line 35-48: No dashboard defined state (prompts user to create `~/dashboard.yaml`)
- Line 51-294: Dashboard display with sections and widgets
- Line 298-312: Props definition (`agentName`, `agentStatus`)
- Line 319-333: `loadDashboard()` - fetches data via store action
- Line 457-465: Auto-refresh based on `config.refresh` (default 30s)
- Line 475-495: Watchers for `agentName` and `agentStatus` changes

### Widget Renderers (DashboardPanel.vue)

| Widget Type | Lines | Description |
|-------------|-------|-------------|
| metric | 100-122 | Numeric value with trend indicator (up/down arrows) |
| status | 125-138 | Colored badge with label |
| progress | 141-159 | Progress bar (0-100%) with color |
| text | 162-173 | Simple text with size/color/align options |
| markdown | 176-182 | Rendered markdown content (uses marked.js) |
| table | 185-219 | Tabular data with columns and rows |
| list | 222-239 | Bullet or numbered list |
| link | 242-257 | Clickable link or button style |
| divider | 260-265 | Horizontal separator (spans full width) |
| spacer | 268-274 | Vertical space (sm/md/lg sizes) |
| image | 277-290 | Image display with optional caption |

### Helper Functions (DashboardPanel.vue)

| Function | Lines | Purpose |
|----------|-------|---------|
| `formatValue()` | 336-342 | Locale-aware number formatting |
| `formatRelativeTime()` | 345-354 | "2m ago" style timestamps |
| `renderMarkdown()` | 357-360 | Convert markdown to HTML |
| `getTrendColor()` | 363-367 | Green for up, red for down |
| `getStatusColors()` | 370-381 | Color map for status badges |
| `getProgressBarColor()` | 384-394 | Progress bar fill colors |
| `getImageUrl()` | 447-454 | Convert `/files/` paths to API URLs |

### State Management

**stores/agents.js:493-499** - Store action
```javascript
async getAgentDashboard(name) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agent-dashboard/${name}`, {
    headers: authStore.authHeader
  })
  return response.data
}
```

### API Calls

```javascript
// From DashboardPanel.vue:322
const response = await agentsStore.getAgentDashboard(props.agentName)

// Translates to:
GET /api/agent-dashboard/{name}
```

## Backend Layer

### Router

**src/backend/routers/agent_dashboard.py** (44 lines)

```python
router = APIRouter(prefix="/api/agent-dashboard", tags=["agent-dashboard"])

@router.get("/{name}")
async def get_agent_dashboard(
    name: str,
    current_user: User = Depends(get_current_user)
):
    return await get_agent_dashboard_logic(name, current_user)
```

**src/backend/main.py:49, 265** - Router registration
```python
from routers.agent_dashboard import router as agent_dashboard_router
# ...
app.include_router(agent_dashboard_router)
```

### Service Layer

**src/backend/services/agent_service/dashboard.py** (107 lines)

**get_agent_dashboard_logic()** - Line 18-106
1. **Authorization** (Line 49-50): Check `db.can_user_access_agent()`
2. **Container lookup** (Line 52-54): Get Docker container by name
3. **Status check** (Line 59-67): Return early if agent not running
4. **HTTP call** (Line 71-87): Call agent's internal `/api/dashboard` endpoint
5. **Error handling** (Lines 88-106): Timeout, connection errors

```python
async def get_agent_dashboard_logic(agent_name: str, current_user: User) -> dict:
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # If not running, return basic info
    if container.status != "running":
        return {"agent_name": agent_name, "has_dashboard": False, ...}

    # Fetch from agent's internal API
    agent_url = f"http://agent-{agent_name}:8000/api/dashboard"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(agent_url)
        # ...
```

## Agent Layer

### Agent Server Router

**docker/base-image/agent_server/routers/dashboard.py** (238 lines)

**Router Registration** - Registered in `routers/__init__.py:11, 21`:
```python
from .dashboard import router as dashboard_router
```

**Main Endpoint** - Line 158-237:
```python
@router.get("/api/dashboard")
async def get_dashboard():
    dashboard_path = find_dashboard_yaml()
    if not dashboard_path:
        return {"has_dashboard": False, "error": "No dashboard.yaml found..."}

    content = dashboard_path.read_text()
    config = yaml.safe_load(content)
    errors = validate_dashboard(config)
    # ...
```

### File Location

**get_dashboard_path()** - Line 18-20
```python
def get_dashboard_path() -> Path:
    """Get the fixed path to dashboard.yaml."""
    return Path("/home/developer/dashboard.yaml")
```

> **Note**: The agent home directory is `/home/developer`. All agent files live there directly (no workspace subdirectory).

### Validation

**validate_dashboard()** - Line 130-155
- Validates required `title` field
- Validates required `sections` array
- Validates `refresh` >= 5 seconds (default 30)
- Calls `validate_section()` for each section

**validate_section()** - Line 99-127
- Validates required `widgets` array
- Validates `layout` is 'grid' or 'list' (default 'grid')
- Validates `columns` is 1-4 (default 3)
- Calls `validate_widget()` for each widget

**validate_widget()** - Line 31-96
- Validates required `type` field
- Validates type is one of 11 valid types
- Type-specific required field validation:
  - `metric`: label, value
  - `status`: label, value, color
  - `progress`: label, value
  - `text`: content
  - `markdown`: content
  - `table`: columns, rows
  - `list`: items
  - `link`: label, url
  - `image`: src, alt

## Dashboard YAML Schema

```yaml
title: "Agent Dashboard"      # Required
description: "Optional description"
refresh: 30                   # Auto-refresh interval (seconds, min 5)

sections:
  - title: "Metrics"          # Optional section title
    description: "Key metrics"
    layout: grid              # 'grid' (default) or 'list'
    columns: 3                # 1-4 columns for grid layout
    widgets:
      - type: metric
        label: "Total Users"
        value: 1234
        unit: "users"
        trend: up             # 'up', 'down', or omit
        trend_value: "+12%"
        description: "Optional detail"
        colspan: 2            # Span multiple columns

      - type: status
        label: "System Status"
        value: "Healthy"
        color: green          # green, red, yellow, gray, blue, orange, purple

      - type: progress
        label: "Disk Usage"
        value: 75
        color: yellow

      - type: text
        content: "Plain text content"
        size: md              # xs, sm, md, lg
        color: gray
        align: center         # left, center, right

      - type: markdown
        content: "**Bold** and *italic*"

      - type: table
        title: "Recent Events"
        columns:
          - { key: date, label: Date }
          - { key: event, label: Event }
        rows:
          - { date: "2024-01-01", event: "Started" }
        max_rows: 5

      - type: list
        title: "Tasks"
        items: ["Task 1", "Task 2"]
        style: bullet         # bullet, number, none
        max_items: 10

      - type: link
        label: "Documentation"
        url: "https://example.com"
        external: true        # Opens in new tab
        style: button         # 'button' or omit for text link
        color: blue

      - type: image
        src: "/files/chart.png"   # Will be converted to API path
        alt: "Chart"
        caption: "Weekly metrics"

      - type: divider         # Horizontal line

      - type: spacer
        size: lg              # sm (8px), md (16px), lg (32px)
```

## Response Format

### Success Response
```json
{
  "agent_name": "my-agent",
  "has_dashboard": true,
  "config": {
    "title": "Agent Dashboard",
    "description": "...",
    "refresh": 30,
    "sections": [...]
  },
  "last_modified": "2024-01-15T10:30:00",
  "status": "running",
  "error": null
}
```

### Error Responses

**Agent not running:**
```json
{
  "agent_name": "my-agent",
  "has_dashboard": false,
  "config": null,
  "last_modified": null,
  "status": "stopped",
  "error": "Agent must be running to read dashboard"
}
```

**No dashboard file:**
```json
{
  "has_dashboard": false,
  "config": null,
  "last_modified": null,
  "error": "No dashboard.yaml found at /home/developer/dashboard.yaml"
}
```

**Validation error:**
```json
{
  "has_dashboard": false,
  "config": null,
  "last_modified": null,
  "error": "Validation errors: Missing required 'title' field; Section 0, Widget 1 (status): missing required 'color' field"
}
```

## Side Effects

- **No WebSocket broadcasts**: Dashboard is polled, not pushed
- **No Audit Log**: Read-only operation
- **No Database Operations**: Configuration is file-based

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Not authenticated | 401 | Unauthorized |
| No access to agent | 403 | You don't have permission to access this agent |
| Agent not found | 404 | Agent not found |
| Agent not running | 200 | `error: "Agent must be running to read dashboard"` |
| No dashboard.yaml | 200 | `error: "No dashboard.yaml found..."` |
| YAML parse error | 200 | `error: "YAML parse error at line X, column Y: ..."` |
| Validation error | 200 | `error: "Validation errors: ..."` |
| Agent timeout | 200 | `error: "Agent is starting up, please try again"` |

## Security Considerations

- **Authorization**: User must have access to agent (owner or shared)
- **File Path**: Dashboard file located at `/home/developer/dashboard.yaml`
- **Image URLs**: `/files/` paths converted to authenticated API paths
- **YAML Parsing**: Uses `yaml.safe_load()` to prevent code execution
- **Markdown Rendering**: Uses `marked` library (client-side)

## Auto-Refresh

The component implements auto-refresh based on the `refresh` value in the dashboard config:

```javascript
// DashboardPanel.vue:457-465
const startRefresh = () => {
  if (refreshInterval) clearInterval(refreshInterval)
  const refreshSeconds = dashboardData.value?.config?.refresh || 30
  refreshInterval = setInterval(() => {
    if (props.agentStatus === 'running') {
      loadDashboard()
    }
  }, refreshSeconds * 1000)
}
```

- Minimum refresh interval: 5 seconds (validated server-side)
- Default refresh interval: 30 seconds
- Stops refreshing when agent is not running
- Restarts when agent status changes to running

## Testing

### Prerequisites
- Agent container running
- User has access to the agent

### Test Steps

1. **No Dashboard File**
   - Action: View Dashboard tab for agent without `dashboard.yaml`
   - Expected: "No Dashboard Defined" message with instructions
   - Verify: Shows `~/dashboard.yaml` path hint

2. **Valid Dashboard**
   - Action: Create `~/dashboard.yaml` with valid widgets, view Dashboard tab
   - Expected: All widgets rendered correctly
   - Verify: Title, sections, and all widget types display

3. **Validation Error**
   - Action: Create `dashboard.yaml` missing required fields
   - Expected: "Dashboard Error" message with specific errors
   - Verify: Error message lists all validation failures

4. **Auto-Refresh**
   - Action: Set `refresh: 10` in config, modify `dashboard.yaml`
   - Expected: Changes appear within 10 seconds
   - Verify: Update timestamp shows recent time

5. **Agent Not Running**
   - Action: Stop agent, view Dashboard tab
   - Expected: "Agent Not Running" message
   - Verify: No loading spinner, clear instructions

### Edge Cases
- YAML syntax error (e.g., bad indentation)
- Widget with missing required fields
- Empty dashboard.yaml file
- Image widget with invalid path

### Status
- Not Tested (new feature)

## Related Flows

- **Upstream**: Agent Lifecycle (agent must be running)
- **Downstream**: None
- **Similar**: Agent Custom Metrics (replaced by this feature)

## Revision History

| Date | Change |
|------|--------|
| 2026-02-12 | **Conditional Tab Visibility**: Dashboard tab now hidden when agent doesn't have `dashboard.yaml`. Added `hasDashboard` ref (line 269), `checkDashboardExists()` function (lines 491-502), and conditional tab inclusion (lines 442-444). Tab checked on mount, status change, route change, and component reactivation. |
| 2026-02-11 | Fixed workspace path references - dashboard.yaml only at `/home/developer/dashboard.yaml` (no workspace fallback) |
| 2026-01-12 | Initial documentation - 11 widget types, YAML-based configuration |
