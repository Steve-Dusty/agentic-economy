# Agent Custom Metrics - Requirements Specification

**Document Created:** 2025-12-10
**Status:** Ready for Implementation
**Priority:** HIGH
**Requirement ID:** 9.9

---

## Executive Summary

Allow agents to define custom metrics in their `template.yaml` that the Trinity platform displays in the UI. This enables agent-specific observability where each agent can expose domain-relevant KPIs (e.g., a social media agent shows "posts scheduled", a research agent shows "sources analyzed").

---

## User Story

**As a** platform operator,
**I want to** see agent-specific metrics defined by the agent template,
**So that** I can understand what the agent is doing in domain-relevant terms beyond generic tool call counts.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AGENT REPOSITORY                                  │
│                                                                           │
│  template.yaml                                                            │
│  ├── metrics:                                                             │
│  │   ├── - name: messages_echoed                                          │
│  │   │     type: counter                                                  │
│  │   │     label: "Messages Echoed"                                       │
│  │   │     description: "Total messages processed"                        │
│  │   └── - name: avg_word_count                                           │
│  │         type: gauge                                                    │
│  │         label: "Avg Words"                                             │
│  │         unit: "words"                                                  │
│                                                                           │
│  metrics.json (written by agent)                                          │
│  ├── messages_echoed: 42                                                  │
│  └── avg_word_count: 12.5                                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         AGENT SERVER                                      │
│                                                                           │
│  GET /api/metrics                                                         │
│  └── Reads template.yaml for metric definitions                           │
│  └── Reads metrics.json for current values                                │
│  └── Returns: { metrics: [...], definitions: [...] }                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND API                                       │
│                                                                           │
│  GET /api/agents/{name}/metrics                                           │
│  └── Proxies to agent container                                           │
│  └── Access control (owner/shared/admin)                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                          │
│                                                                           │
│  MetricsPanel.vue (new component)                                         │
│  └── Displays metrics in Info tab or dedicated Metrics tab                │
│  └── Renders based on metric type (counter, gauge, percentage)            │
│  └── Auto-refresh every 30 seconds when visible                           │
│                                                                           │
│  AgentNode.vue (Dashboard)                                                │
│  └── Optional: Show 1-2 key metrics inline on agent cards                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Metric Types

| Type | Description | Display Style | Example |
|------|-------------|---------------|---------|
| `counter` | Monotonically increasing value | Large number with label | "42 Messages" |
| `gauge` | Current value that can go up/down | Number with trend indicator | "12.5 Avg Words" |
| `percentage` | 0-100 value | Progress bar with percentage | "75% Success Rate" |
| `status` | Enum/state value | Colored badge | "ACTIVE", "IDLE" |
| `duration` | Time in seconds | Formatted (e.g., "2h 15m") | "Uptime: 2h 15m" |
| `bytes` | Size in bytes | Formatted (e.g., "1.2 MB") | "Data Processed: 1.2 MB" |

---

## Template Schema Extension

Add `metrics` field to `template.yaml`:

```yaml
# template.yaml
name: my-agent
display_name: "My Agent"

# NEW: Custom metrics definitions
metrics:
  - name: messages_processed       # Required: internal identifier (snake_case)
    type: counter                  # Required: counter|gauge|percentage|status|duration|bytes
    label: "Messages"              # Required: display label
    description: "Total messages processed"  # Optional: tooltip/help text
    icon: "chat"                   # Optional: icon name (heroicons)

  - name: success_rate
    type: percentage
    label: "Success Rate"
    description: "Percentage of successful operations"
    warning_threshold: 80          # Optional: show yellow if below
    critical_threshold: 50         # Optional: show red if below

  - name: current_state
    type: status
    label: "State"
    values:                        # Required for status type
      - value: "active"
        color: "green"
        label: "Active"
      - value: "idle"
        color: "gray"
        label: "Idle"
      - value: "error"
        color: "red"
        label: "Error"

  - name: processing_time
    type: duration
    label: "Total Processing Time"

  - name: data_processed
    type: bytes
    label: "Data Processed"

# Existing fields...
resources:
  cpu: "2"
  memory: "4g"
```

---

## Metrics Data File

Agents write metrics to `metrics.json` in their workspace:

```json
{
  "messages_processed": 42,
  "success_rate": 87.5,
  "current_state": "active",
  "processing_time": 3725,
  "data_processed": 1258291,
  "last_updated": "2025-12-10T10:30:00Z"
}
```

**Rules:**
- File MUST be valid JSON
- Keys MUST match metric `name` from template.yaml
- Values MUST be numbers (except `status` type which is string)
- `last_updated` is optional but recommended
- File is read-only by platform (agent writes it)

---

## API Endpoints

### GET /api/agents/{name}/metrics

**Description:** Get agent custom metrics with definitions

**Response:**
```json
{
  "agent_name": "test-echo",
  "has_metrics": true,
  "last_updated": "2025-12-10T10:30:00Z",
  "definitions": [
    {
      "name": "messages_echoed",
      "type": "counter",
      "label": "Messages Echoed",
      "description": "Total messages processed",
      "icon": "chat"
    }
  ],
  "values": {
    "messages_echoed": 42
  }
}
```

**If no metrics defined:**
```json
{
  "agent_name": "test-echo",
  "has_metrics": false,
  "message": "No metrics defined in template.yaml"
}
```

**If agent not running:**
```json
{
  "agent_name": "test-echo",
  "has_metrics": false,
  "status": "stopped",
  "message": "Agent must be running to read metrics"
}
```

---

## Agent Server Implementation

### New Endpoint: GET /api/metrics

**Location:** `docker/base-image/agent_server/routers/info.py` (add to existing router)

```python
@router.get("/api/metrics")
async def get_metrics():
    """Get agent custom metrics."""

    # 1. Read metric definitions from template.yaml
    template_path = find_template_yaml()
    if not template_path:
        return {"has_metrics": False, "message": "No template.yaml found"}

    template_data = yaml.safe_load(template_path.read_text())
    metric_definitions = template_data.get("metrics", [])

    if not metric_definitions:
        return {"has_metrics": False, "message": "No metrics defined"}

    # 2. Read current values from metrics.json
    metrics_path = Path.home() / "workspace" / "metrics.json"
    values = {}
    last_updated = None

    if metrics_path.exists():
        try:
            data = json.loads(metrics_path.read_text())
            last_updated = data.pop("last_updated", None)
            values = data
        except json.JSONDecodeError:
            pass

    return {
        "has_metrics": True,
        "definitions": metric_definitions,
        "values": values,
        "last_updated": last_updated
    }
```

---

## Backend Implementation

### New Endpoint: GET /api/agents/{name}/metrics

**Location:** `src/backend/routers/agents.py`

```python
@router.get("/{agent_name}/metrics")
async def get_agent_metrics(
    agent_name: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get agent custom metrics."""

    # 1. Access control
    if not can_access_agent(current_user, agent_name):
        raise HTTPException(403, "Access denied")

    # 2. Check agent exists and is running
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(404, "Agent not found")

    if container.status != "running":
        return {
            "agent_name": agent_name,
            "has_metrics": False,
            "status": "stopped",
            "message": "Agent must be running to read metrics"
        }

    # 3. Proxy to agent
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"http://agent-{agent_name}:8000/api/metrics")
            data = response.json()
            data["agent_name"] = agent_name
            return data
    except Exception as e:
        return {
            "agent_name": agent_name,
            "has_metrics": False,
            "message": f"Failed to read metrics: {str(e)}"
        }
```

---

## Frontend Implementation

### MetricsPanel.vue (New Component)

**Location:** `src/frontend/src/components/MetricsPanel.vue`

**Features:**
- Grid layout for metric cards
- Type-specific rendering (counter, gauge, percentage, etc.)
- Color-coded thresholds for percentages
- Auto-refresh every 30 seconds when tab is active
- Loading and error states
- "No metrics defined" message for agents without metrics

**Metric Card Styles:**
- Counter: Large number with label
- Gauge: Number with optional up/down trend arrow
- Percentage: Circular or linear progress bar
- Status: Colored badge
- Duration: Formatted time string
- Bytes: Formatted size string

### Integration Points

**AgentDetail.vue:**
- Add "Metrics" tab (or embed in Info tab)
- Load metrics when tab activated
- Pass agent-name to MetricsPanel component

**AgentNode.vue (Dashboard):**
- Optional: Show 1-2 primary metrics inline on cards
- Primary metrics flagged with `primary: true` in template.yaml

---

## Test Agent Metrics Definitions

### test-agent-echo
```yaml
metrics:
  - name: messages_echoed
    type: counter
    label: "Messages"
    description: "Total messages echoed"
  - name: total_words
    type: counter
    label: "Words"
    description: "Total words processed"
  - name: total_characters
    type: counter
    label: "Characters"
    description: "Total characters processed"
  - name: avg_message_length
    type: gauge
    label: "Avg Length"
    unit: "chars"
    description: "Average message length"
```

### test-agent-counter
```yaml
metrics:
  - name: counter_value
    type: gauge
    label: "Counter"
    description: "Current counter value"
  - name: increment_count
    type: counter
    label: "Increments"
    description: "Total increment operations"
  - name: decrement_count
    type: counter
    label: "Decrements"
    description: "Total decrement operations"
  - name: reset_count
    type: counter
    label: "Resets"
    description: "Total reset operations"
```

### test-agent-delegator
```yaml
metrics:
  - name: delegations_sent
    type: counter
    label: "Delegations"
    description: "Total tasks delegated to other agents"
  - name: delegations_succeeded
    type: counter
    label: "Succeeded"
    description: "Successful delegations"
  - name: delegations_failed
    type: counter
    label: "Failed"
    description: "Failed delegations"
  - name: success_rate
    type: percentage
    label: "Success Rate"
    description: "Delegation success rate"
    warning_threshold: 80
    critical_threshold: 50
  - name: unique_agents_contacted
    type: gauge
    label: "Agents Contacted"
    description: "Number of unique agents delegated to"
```

### test-agent-worker
```yaml
metrics:
  - name: plans_created
    type: counter
    label: "Plans"
    description: "Total workplans created"
  - name: tasks_completed
    type: counter
    label: "Tasks Done"
    description: "Total tasks completed"
  - name: tasks_failed
    type: counter
    label: "Tasks Failed"
    description: "Total tasks failed"
  - name: active_plans
    type: gauge
    label: "Active Plans"
    description: "Currently active workplans"
  - name: completion_rate
    type: percentage
    label: "Completion Rate"
    description: "Task completion rate"
```

### test-agent-scheduler
```yaml
metrics:
  - name: scheduled_executions
    type: counter
    label: "Scheduled Runs"
    description: "Total scheduled executions"
  - name: manual_executions
    type: counter
    label: "Manual Runs"
    description: "Total manual executions"
  - name: last_execution_status
    type: status
    label: "Last Status"
    values:
      - value: "success"
        color: "green"
        label: "Success"
      - value: "failed"
        color: "red"
        label: "Failed"
      - value: "none"
        color: "gray"
        label: "None"
  - name: total_log_entries
    type: counter
    label: "Log Entries"
    description: "Total log entries written"
```

### test-agent-queue
```yaml
metrics:
  - name: requests_processed
    type: counter
    label: "Requests"
    description: "Total requests processed"
  - name: total_delay_seconds
    type: duration
    label: "Total Delay"
    description: "Cumulative delay time"
  - name: avg_delay
    type: gauge
    label: "Avg Delay"
    unit: "sec"
    description: "Average delay per request"
  - name: queue_depth
    type: gauge
    label: "Queue Depth"
    description: "Current items in queue"
```

### test-agent-files
```yaml
metrics:
  - name: files_created
    type: counter
    label: "Files Created"
    description: "Total files created"
  - name: files_deleted
    type: counter
    label: "Files Deleted"
    description: "Total files deleted"
  - name: total_bytes_written
    type: bytes
    label: "Data Written"
    description: "Total bytes written"
  - name: current_file_count
    type: gauge
    label: "File Count"
    description: "Current files in workspace"
```

### test-agent-error
```yaml
metrics:
  - name: normal_responses
    type: counter
    label: "Normal"
    description: "Normal responses"
  - name: intentional_failures
    type: counter
    label: "Failures"
    description: "Intentional failure triggers"
  - name: timeouts
    type: counter
    label: "Timeouts"
    description: "Timeout triggers"
  - name: error_rate
    type: percentage
    label: "Error Rate"
    description: "Percentage of error responses"
    warning_threshold: 20
    critical_threshold: 50
```

---

## Implementation Phases

### Phase 1: Schema & Agent Server (Day 1)
1. Add `metrics` to template.yaml schema in AGENT_TEMPLATE_SPEC.md
2. Update GITHUB_NATIVE_AGENTS.md with metrics configuration
3. Implement `GET /api/metrics` in agent-server
4. Update all 8 test agent template.yaml files

### Phase 2: Backend API (Day 1)
1. Add `GET /api/agents/{name}/metrics` endpoint
2. Add route to agents.py router
3. Test with running agent

### Phase 3: Frontend UI (Day 2)
1. Create MetricsPanel.vue component
2. Add Metrics tab to AgentDetail.vue
3. Implement type-specific rendering
4. Add auto-refresh

### Phase 4: Polish (Day 2)
1. Add metrics to Dashboard agent cards (optional)
2. Document in feature-flows
3. Update requirements.md

---

## Testing

### Prerequisites
- [ ] Agent running with metrics defined in template.yaml
- [ ] Agent writes metrics.json after operations

### Test Cases

1. **Metrics API Basic**
   - Call `GET /api/agents/{name}/metrics`
   - Verify definitions match template.yaml
   - Verify values match metrics.json

2. **No Metrics Defined**
   - Test agent without `metrics` in template.yaml
   - Should return `has_metrics: false`

3. **Agent Stopped**
   - Test stopped agent
   - Should return `status: stopped`

4. **Metrics Update**
   - Agent updates metrics.json
   - Next API call shows new values

5. **Type Rendering**
   - Test each metric type displays correctly
   - Counter: number
   - Gauge: number with trend
   - Percentage: progress bar
   - Status: colored badge
   - Duration: formatted time
   - Bytes: formatted size

6. **Threshold Colors**
   - Percentage below critical: red
   - Percentage below warning: yellow
   - Percentage above warning: green

---

## Security Considerations

- Metrics are read-only (platform reads, agent writes)
- Access control enforced (owner/shared/admin)
- No sensitive data in metrics (just numbers/state)
- Rate limiting on metrics API (same as other endpoints)

---

## Future Enhancements

1. **Metrics History**: Store time-series data for graphs
2. **Alerting**: Trigger alerts when thresholds breached
3. **Aggregation**: Platform-wide metrics dashboard
4. **Custom Widgets**: Allow more complex visualizations
5. **Export**: Prometheus/OpenTelemetry export

---

## Files to Create/Modify

### New Files
- `docs/AGENT_CUSTOM_METRICS_SPEC.md` (this file)
- `src/frontend/src/components/MetricsPanel.vue`
- `docs/memory/feature-flows/agent-custom-metrics.md`

### Modified Files
- `docs/AGENT_TEMPLATE_SPEC.md` - Add metrics schema
- `docs/GITHUB_NATIVE_AGENTS.md` - Add metrics configuration section
- `docker/base-image/agent_server/routers/info.py` - Add metrics endpoint
- `src/backend/routers/agents.py` - Add metrics proxy endpoint
- `src/frontend/src/views/AgentDetail.vue` - Add Metrics tab
- `src/frontend/src/stores/agents.js` - Add getAgentMetrics action
- `docs/memory/requirements.md` - Add requirement 9.9
- All 8 test agent template.yaml files

---

## Related Documents

- [Agent Template Spec](./AGENT_TEMPLATE_SPEC.md)
- [GitHub Native Agents](./GITHUB_NATIVE_AGENTS.md)
- [Agent Info Display](../docs/memory/feature-flows/agent-info-display.md)
- [Requirements](../docs/memory/requirements.md)
