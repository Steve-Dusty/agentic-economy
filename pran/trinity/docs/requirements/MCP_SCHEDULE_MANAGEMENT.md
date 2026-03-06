# MCP Schedule Management Tools

> **Feature ID**: MCP-SCHED-001
> **Status**: ✅ Implemented
> **Priority**: High
> **Created**: 2026-01-29
> **Implemented**: 2026-01-29
> **Author**: Claude Code (Opus 4.5)

---

## Executive Summary

Add MCP tools for programmatic schedule management, enabling head agents (Claude Code instances) to create, list, modify, and control schedules on Trinity agents through the Model Context Protocol.

**Current State**: The MCP server has 21 tools covering agent lifecycle, chat, system management, and credentials. Schedule management is only available through:
- REST API (`/api/agents/{name}/schedules/*`)
- System deployment manifests (`deploy_system` tool with YAML)
- UI (SchedulesPanel.vue)

**Gap**: No MCP tools for individual schedule CRUD operations. Agents cannot dynamically create or modify schedules on other agents.

**Solution**: Add 7 new MCP tools for schedule management, bringing total to 28 tools.

---

## Motivation

### Use Cases

1. **Dynamic Scheduling**: Head agent creates schedules on worker agents based on discovered requirements
2. **Schedule Orchestration**: Orchestrator agent enables/disables worker schedules based on system load
3. **Automated Setup**: Agent automatically creates schedules during initialization or configuration
4. **Adaptive Operations**: Agent adjusts schedule timing based on execution results or business events
5. **Self-Management**: Agent manages its own schedules programmatically

### Example Scenario

```
Head Agent (via MCP):
  1. Create worker agent "report-generator"
  2. Create schedule: "0 9 * * 1-5" (weekdays 9am) - "Generate daily sales report"
  3. Monitor execution history
  4. If failures > threshold, disable schedule and notify
  5. After fix, re-enable schedule
```

---

## Requirements

### REQ-1: List Agent Schedules Tool

**Tool Name**: `list_agent_schedules`

**Description**: List all schedules configured for an agent with their status, last/next execution times.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | Yes | Name of the agent to list schedules for |

**Returns**:
```json
{
  "agent_name": "my-agent",
  "schedule_count": 2,
  "schedules": [
    {
      "id": "sched_abc123",
      "name": "Daily Report",
      "cron_expression": "0 9 * * *",
      "message": "Generate daily sales report",
      "enabled": true,
      "timezone": "America/New_York",
      "description": "Morning sales summary",
      "last_run_at": "2026-01-28T14:00:00Z",
      "next_run_at": "2026-01-29T14:00:00Z",
      "created_at": "2026-01-15T10:00:00Z"
    }
  ]
}
```

**Backend Endpoint**: `GET /api/agents/{name}/schedules`

**Access Control**:
- User-scoped keys: Can list schedules on agents they own or have access to
- Agent-scoped keys: Can only list own schedules + permitted agents' schedules
- System-scoped keys: Can list all agents' schedules

---

### REQ-2: Create Schedule Tool

**Tool Name**: `create_agent_schedule`

**Description**: Create a new cron-based schedule for an agent.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | Yes | Target agent name |
| `name` | string | Yes | Human-readable schedule name |
| `cron_expression` | string | Yes | 5-field cron format (min hour day month dow) |
| `message` | string | Yes | Task message sent to agent on trigger |
| `timezone` | string | No | Timezone (default: UTC). E.g., "America/New_York" |
| `description` | string | No | Optional description |
| `enabled` | boolean | No | Start enabled (default: true) |

**Cron Format Reference**:
```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sun=0)
│ │ │ │ │
* * * * *
```

**Common Presets**:
- `0 9 * * *` - Daily at 9 AM
- `0 9 * * 1-5` - Weekdays at 9 AM
- `0 */6 * * *` - Every 6 hours
- `*/30 * * * *` - Every 30 minutes
- `0 0 1 * *` - First day of month at midnight

**Returns**:
```json
{
  "status": "created",
  "schedule": {
    "id": "sched_xyz789",
    "name": "Daily Report",
    "cron_expression": "0 9 * * *",
    "message": "Generate daily sales report",
    "enabled": true,
    "timezone": "America/New_York",
    "next_run_at": "2026-01-29T14:00:00Z"
  }
}
```

**Backend Endpoint**: `POST /api/agents/{name}/schedules`

**Validation**:
- Cron expression must be valid 5-field format (validated by croniter)
- Agent must exist and be accessible to caller
- Schedule name must be non-empty

**Access Control**:
- User-scoped keys: Can create schedules on owned agents
- Agent-scoped keys: Can only create schedules on self (not other agents)
- System-scoped keys: Can create schedules on any agent

---

### REQ-3: Get Schedule Details Tool

**Tool Name**: `get_agent_schedule`

**Description**: Get detailed information about a specific schedule.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | Yes | Agent name |
| `schedule_id` | string | Yes | Schedule ID |

**Returns**:
```json
{
  "id": "sched_abc123",
  "agent_name": "my-agent",
  "name": "Daily Report",
  "cron_expression": "0 9 * * *",
  "message": "Generate daily sales report",
  "enabled": true,
  "timezone": "America/New_York",
  "description": "Morning sales summary",
  "last_run_at": "2026-01-28T14:00:00Z",
  "next_run_at": "2026-01-29T14:00:00Z",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-20T15:30:00Z"
}
```

**Backend Endpoint**: `GET /api/agents/{name}/schedules/{schedule_id}`

---

### REQ-4: Update Schedule Tool

**Tool Name**: `update_agent_schedule`

**Description**: Update an existing schedule's configuration.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | Yes | Agent name |
| `schedule_id` | string | Yes | Schedule ID to update |
| `name` | string | No | New schedule name |
| `cron_expression` | string | No | New cron expression |
| `message` | string | No | New task message |
| `timezone` | string | No | New timezone |
| `description` | string | No | New description |
| `enabled` | boolean | No | Enable/disable |

**Returns**:
```json
{
  "status": "updated",
  "schedule": {
    "id": "sched_abc123",
    "name": "Updated Report",
    "cron_expression": "0 10 * * *",
    "enabled": true,
    "next_run_at": "2026-01-29T15:00:00Z"
  }
}
```

**Backend Endpoint**: `PUT /api/agents/{name}/schedules/{schedule_id}`

---

### REQ-5: Delete Schedule Tool

**Tool Name**: `delete_agent_schedule`

**Description**: Permanently delete a schedule and its execution history.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | Yes | Agent name |
| `schedule_id` | string | Yes | Schedule ID to delete |

**Returns**:
```json
{
  "status": "deleted",
  "schedule_id": "sched_abc123",
  "message": "Schedule 'Daily Report' deleted successfully"
}
```

**Backend Endpoint**: `DELETE /api/agents/{name}/schedules/{schedule_id}`

**Access Control**:
- Only schedule owner (creator) can delete
- System-scoped keys can delete any schedule

---

### REQ-6: Enable/Disable Schedule Tool

**Tool Name**: `toggle_agent_schedule`

**Description**: Enable or disable a schedule without deleting it.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | Yes | Agent name |
| `schedule_id` | string | Yes | Schedule ID |
| `enabled` | boolean | Yes | True to enable, false to disable |

**Returns**:
```json
{
  "status": "enabled",
  "schedule_id": "sched_abc123",
  "schedule_name": "Daily Report",
  "next_run_at": "2026-01-29T14:00:00Z"
}
```

**Backend Endpoints**:
- Enable: `POST /api/agents/{name}/schedules/{schedule_id}/enable`
- Disable: `POST /api/agents/{name}/schedules/{schedule_id}/disable`

---

### REQ-7: Trigger Schedule Tool

**Tool Name**: `trigger_agent_schedule`

**Description**: Manually trigger immediate execution of a schedule.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | Yes | Agent name |
| `schedule_id` | string | Yes | Schedule ID to trigger |

**Returns**:
```json
{
  "status": "triggered",
  "schedule_id": "sched_abc123",
  "execution_id": "exec_def456",
  "message": "Schedule 'Daily Report' triggered. Execution started."
}
```

**Backend Endpoint**: `POST /api/agents/{name}/schedules/{schedule_id}/trigger`

**Note**: Trigger creates a new execution record with `triggered_by='manual'`. The execution goes through the standard execution queue.

---

### REQ-8: Get Schedule Executions Tool

**Tool Name**: `get_schedule_executions`

**Description**: Get execution history for a specific schedule or all schedules on an agent.

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | Yes | Agent name |
| `schedule_id` | string | No | Specific schedule (optional - if omitted, returns all) |
| `limit` | number | No | Max results (default: 20, max: 100) |

**Returns**:
```json
{
  "agent_name": "my-agent",
  "execution_count": 15,
  "executions": [
    {
      "id": "exec_abc123",
      "schedule_id": "sched_xyz789",
      "schedule_name": "Daily Report",
      "status": "success",
      "started_at": "2026-01-28T14:00:05Z",
      "completed_at": "2026-01-28T14:02:30Z",
      "duration_ms": 145000,
      "triggered_by": "schedule",
      "context_used": 45000,
      "cost": 0.0234,
      "error": null
    }
  ]
}
```

**Backend Endpoints**:
- All executions: `GET /api/agents/{name}/executions?limit=N`
- Schedule-specific: `GET /api/agents/{name}/schedules/{schedule_id}/executions?limit=N`

---

## Architecture

### MCP Server Changes

**New File**: `src/mcp-server/src/tools/schedules.ts`

```typescript
/**
 * Schedule Management Tools
 *
 * MCP tools for managing agent schedules: list, create, update, delete, toggle, trigger
 */

import { z } from "zod";
import { TrinityClient } from "../client.js";
import type { McpAuthContext } from "../types.js";

export function createScheduleTools(
  client: TrinityClient,
  requireApiKey: boolean
) {
  const getClient = (authContext?: McpAuthContext): TrinityClient => {
    // ... standard auth pattern from agents.ts
  };

  return {
    listAgentSchedules: { /* REQ-1 */ },
    createAgentSchedule: { /* REQ-2 */ },
    getAgentSchedule: { /* REQ-3 */ },
    updateAgentSchedule: { /* REQ-4 */ },
    deleteAgentSchedule: { /* REQ-5 */ },
    toggleAgentSchedule: { /* REQ-6 */ },
    triggerAgentSchedule: { /* REQ-7 */ },
    getScheduleExecutions: { /* REQ-8 */ },
  };
}
```

### TrinityClient Extensions

**File**: `src/mcp-server/src/client.ts`

Add methods:
```typescript
// Schedule Management
async listAgentSchedules(agentName: string): Promise<Schedule[]>
async createAgentSchedule(agentName: string, schedule: ScheduleCreate): Promise<Schedule>
async getAgentSchedule(agentName: string, scheduleId: string): Promise<Schedule>
async updateAgentSchedule(agentName: string, scheduleId: string, updates: ScheduleUpdate): Promise<Schedule>
async deleteAgentSchedule(agentName: string, scheduleId: string): Promise<void>
async enableAgentSchedule(agentName: string, scheduleId: string): Promise<ScheduleStatus>
async disableAgentSchedule(agentName: string, scheduleId: string): Promise<ScheduleStatus>
async triggerAgentSchedule(agentName: string, scheduleId: string): Promise<TriggerResult>
async getAgentExecutions(agentName: string, limit?: number): Promise<Execution[]>
async getScheduleExecutions(agentName: string, scheduleId: string, limit?: number): Promise<Execution[]>
```

### Server Registration

**File**: `src/mcp-server/src/server.ts`

```typescript
// Register schedule management tools (8 tools)
const scheduleTools = createScheduleTools(client, requireApiKey);
server.addTool(scheduleTools.listAgentSchedules);
server.addTool(scheduleTools.createAgentSchedule);
server.addTool(scheduleTools.getAgentSchedule);
server.addTool(scheduleTools.updateAgentSchedule);
server.addTool(scheduleTools.deleteAgentSchedule);
server.addTool(scheduleTools.toggleAgentSchedule);
server.addTool(scheduleTools.triggerAgentSchedule);
server.addTool(scheduleTools.getScheduleExecutions);

console.log(`Registered ${totalTools} tools`); // Update: 21 + 8 = 29 tools
```

---

## Access Control Matrix

| Tool | User-Scoped | Agent-Scoped (Self) | Agent-Scoped (Other) | System-Scoped |
|------|-------------|---------------------|----------------------|---------------|
| list_agent_schedules | Own/Shared | Yes | Permitted only | All |
| create_agent_schedule | Own only | Yes | No | All |
| get_agent_schedule | Own/Shared | Yes | Permitted only | All |
| update_agent_schedule | Own only | Yes | No | All |
| delete_agent_schedule | Own only | Yes | No | All |
| toggle_agent_schedule | Own/Shared | Yes | Permitted only | All |
| trigger_agent_schedule | Own/Shared | Yes | Permitted only | All |
| get_schedule_executions | Own/Shared | Yes | Permitted only | All |

**Key Decisions**:
1. Agent-scoped keys can manage their OWN schedules (self-scheduling)
2. Agent-scoped keys cannot create/update/delete schedules on OTHER agents (even permitted)
3. Agent-scoped keys CAN read/toggle/trigger schedules on permitted agents (operational control)
4. System-scoped keys have full access (for orchestration)

---

## Implementation Plan

### Phase 1: Core Tools (REQ-1, REQ-2, REQ-5)
- `list_agent_schedules` - Essential for discovery
- `create_agent_schedule` - Core creation capability
- `delete_agent_schedule` - Cleanup capability

### Phase 2: Control Tools (REQ-6, REQ-7)
- `toggle_agent_schedule` - Enable/disable
- `trigger_agent_schedule` - Manual execution

### Phase 3: Query Tools (REQ-3, REQ-4, REQ-8)
- `get_agent_schedule` - Detail view
- `update_agent_schedule` - Modify existing
- `get_schedule_executions` - Execution history

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/mcp-server/src/tools/schedules.ts` | **NEW** - All 8 schedule tools |
| `src/mcp-server/src/client.ts` | Add 10 schedule-related methods |
| `src/mcp-server/src/types.ts` | Add Schedule, ScheduleCreate, Execution types |
| `src/mcp-server/src/server.ts` | Import and register schedule tools |
| `docs/memory/feature-flows/mcp-orchestration.md` | Add Schedule Tools section |
| `docs/memory/feature-flows/scheduling.md` | Add MCP integration section |

---

## Testing Requirements

### Unit Tests

1. **Parameter Validation**: Invalid cron expressions rejected
2. **Access Control**: Agent-scoped keys blocked from other agents' write operations
3. **Error Handling**: 404 for non-existent schedules/agents

### Integration Tests

```bash
# Test via MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8080/mcp

# Verify 29 tools registered (21 existing + 8 new)
```

### E2E Tests (Claude Code)

```
1. "List schedules for agent my-worker"
2. "Create a schedule on my-worker to run 'check health' every hour"
3. "Disable the health check schedule"
4. "Trigger the schedule manually"
5. "Show execution history for my-worker"
6. "Delete the health check schedule"
```

---

## Documentation Updates

### Feature Flow Updates

1. **mcp-orchestration.md**: Add "Schedule Tools" section with all 8 tools
2. **scheduling.md**: Add "MCP Integration" section showing programmatic access
3. **feature-flows.md**: Update tool count (21 → 29)

### Architecture Updates

1. **architecture.md**: Update MCP section with schedule tools count

---

## Success Metrics

1. **Functional**: All 8 tools work via MCP Inspector
2. **Integration**: Claude Code can manage schedules via natural language
3. **Access Control**: Agent-scoped keys properly restricted
4. **Documentation**: All flows documented

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Race condition on schedule updates | Backend uses database transactions |
| Agent creates too many schedules | Consider rate limiting (future) |
| Cron expression injection | Validated by croniter library |
| Orphaned schedules on agent delete | Cascade delete in database schema |

---

## Dependencies

- Backend schedule API (already implemented)
- MCP server authentication (already implemented)
- Agent access control (already implemented)

---

## Appendix: Cron Expression Examples

| Expression | Meaning |
|------------|---------|
| `* * * * *` | Every minute |
| `0 * * * *` | Every hour on the hour |
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `0 0 * * 0` | Every Sunday at midnight |
| `0 0 1 * *` | First of every month at midnight |
| `*/15 * * * *` | Every 15 minutes |
| `0 */4 * * *` | Every 4 hours |
| `0 9,17 * * *` | At 9 AM and 5 PM |

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-29 | Claude Code | Initial requirements document |
| 2026-01-29 | Claude Code | Implemented all 8 MCP tools |
