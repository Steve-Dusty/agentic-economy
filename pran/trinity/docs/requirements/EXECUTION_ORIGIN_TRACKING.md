# Execution Origin Tracking (AUDIT-001)

> **Status**: PENDING IMPLEMENTATION
> **Priority**: HIGH
> **Created**: 2026-02-20
> **Author**: Eugene / Claude

## Overview

Comprehensive tracking of WHO triggered each execution in Trinity platform. Currently, executions track the trigger TYPE (manual, scheduled, mcp, agent) but not the full identity of the actor. This feature adds complete actor attribution to enable audit trails, accountability, and debugging.

## Problem Statement

When reviewing execution history in Trinity, users currently cannot answer:
1. **Who started this task?** - Which user or external client initiated the execution?
2. **Which MCP API key was used?** - For external integrations, which key made the call?
3. **Which user owns that key?** - For accountability, who is responsible for this action?
4. **Which agent triggered this?** - For agent-to-agent collaboration, what was the call chain?

This information is partially available at execution time but not persisted, making post-hoc analysis impossible.

## User Stories

1. **As a platform admin**, I want to see which user triggered each execution so I can audit usage and troubleshoot issues.
2. **As an agent owner**, I want to know when my agent was called by other agents or external MCP clients so I can understand usage patterns.
3. **As a compliance officer**, I want full attribution on all executions so I can produce audit reports.
4. **As a developer**, I want to trace execution chains across agents to debug multi-agent workflows.

## Current State Analysis

### What's Currently Tracked

**`schedule_executions` table** stores:
- `id` - Execution UUID
- `agent_name` - Target agent
- `triggered_by` - Text field with values: "manual", "schedule", "mcp", "agent"
- `message`, `response`, `status`, `cost`, etc.

**`agent_activities` table** stores:
- `triggered_by` - Same values as above
- `user_id` - FK to users table (available at activity creation time)
- `related_execution_id` - Links to schedule_executions
- `details` - JSON with additional context

### What's Available at Execution Time (but not persisted)

| Trigger Type | Available Data | Currently Stored |
|--------------|----------------|------------------|
| **User Manual** | `current_user.id`, `current_user.email` | Only `triggered_by="manual"` |
| **Schedule** | `schedule_id`, `schedule_name` | `schedule_id`, `triggered_by="schedule"` |
| **MCP (User)** | MCP key ID, user email, key name | Only `triggered_by="mcp"` |
| **MCP (Agent)** | Source agent name, agent's key ID | Only `triggered_by="agent"` |

### Data Available from MCP API Key Validation

When an MCP call is authenticated, `db.validate_mcp_api_key()` returns:
```python
{
    "key_id": "abc123",           # MCP API key ID
    "key_name": "My Claude Code", # User-assigned key name
    "user_id": "admin",           # Username (legacy naming)
    "user_email": "user@example.com",
    "agent_name": "agent-x",      # Only for agent-scoped keys
    "scope": "user"               # "user" or "agent"
}
```

## Requirements

### REQ-1: Extended Execution Schema

Add new columns to `schedule_executions` table:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `source_user_id` | INTEGER | Yes | FK to `users.id` - User who triggered |
| `source_user_email` | TEXT | Yes | User's email (denormalized for queries) |
| `source_agent_name` | TEXT | Yes | Calling agent name (for agent-to-agent) |
| `source_mcp_key_id` | TEXT | Yes | MCP API key ID used (for MCP calls) |
| `source_mcp_key_name` | TEXT | Yes | MCP API key name (denormalized) |

**Migration**: Add columns with `ALTER TABLE` allowing NULL for backward compatibility.

### REQ-2: Capture Origin Data at Execution Creation

Modify `db.create_task_execution()` and related functions to accept and store:

**For User Manual Triggers** (`triggered_by="manual"`):
- `source_user_id` = `current_user.id`
- `source_user_email` = `current_user.email`
- Others NULL

**For Schedule Triggers** (`triggered_by="schedule"`):
- All source fields NULL (schedules are system-triggered)
- `schedule_id` already captured

**For MCP User Triggers** (`triggered_by="mcp"`):
- `source_user_id` = user ID from MCP key validation
- `source_user_email` = user email from MCP key validation
- `source_mcp_key_id` = MCP API key ID
- `source_mcp_key_name` = MCP API key name

**For Agent-to-Agent Triggers** (`triggered_by="agent"`):
- `source_agent_name` = value from `X-Source-Agent` header
- `source_mcp_key_id` = agent's MCP key ID
- `source_mcp_key_name` = agent's MCP key name
- `source_user_id` = NULL (agent is the actor, not a user)

### REQ-3: Pass MCP Key Info Through Request Chain

**MCP Server → Backend API**:
When MCP server calls backend on behalf of a client, include MCP key info in request headers:
- `X-MCP-Key-ID: <key_id>`
- `X-MCP-Key-Name: <key_name>`

**Backend API**:
Extract these headers in `routers/chat.py` and pass to execution creation.

### REQ-4: Display Origin on Execution Detail Page

**ExecutionDetail.vue** should show a new "Triggered By" card:

For **User Manual**:
```
Triggered By: Manual
User: user@example.com
```

For **Schedule**:
```
Triggered By: Schedule
Schedule: Daily Report (schedule_id)
```

For **MCP (User)**:
```
Triggered By: MCP API
User: user@example.com
API Key: "My Claude Code" (key_id prefix)
```

For **Agent-to-Agent**:
```
Triggered By: Agent
Source Agent: agent-orchestrator
API Key: "agent-orchestrator-key" (auto-generated)
```

### REQ-5: Filter Executions by Origin

**TasksPanel.vue** (execution history) should support filtering by:
- All triggers
- Manual only
- Scheduled only
- MCP only
- Agent-to-agent only

**API Enhancement**:
`GET /api/agents/{name}/executions` should accept query param:
- `triggered_by=manual|schedule|mcp|agent`

### REQ-6: API Response Model Update

`ScheduleExecution` Pydantic model should include new fields:

```python
class ScheduleExecution(BaseModel):
    # ... existing fields ...
    source_user_id: Optional[int] = None
    source_user_email: Optional[str] = None
    source_agent_name: Optional[str] = None
    source_mcp_key_id: Optional[str] = None
    source_mcp_key_name: Optional[str] = None
```

## Data Flow Diagrams

### User Manual Execution
```
User (browser) → Frontend → POST /api/agents/{name}/task
                            ↓
                         Backend extracts:
                         - current_user.id
                         - current_user.email
                            ↓
                         db.create_task_execution(
                             triggered_by="manual",
                             source_user_id=current_user.id,
                             source_user_email=current_user.email
                         )
```

### MCP User Execution
```
Claude Code → POST /mcp (with Authorization: Bearer trinity_mcp_xxx)
              ↓
           MCP Server validates key:
           - key_id, key_name, user_email
              ↓
           POST /api/agents/{name}/chat
           Headers:
           - X-Via-MCP: true
           - X-MCP-Key-ID: abc123
           - X-MCP-Key-Name: "My Claude Code"
              ↓
           Backend extracts headers + validates user
              ↓
           db.create_task_execution(
               triggered_by="mcp",
               source_user_id=<from MCP key>,
               source_user_email=<from MCP key>,
               source_mcp_key_id=<from header>,
               source_mcp_key_name=<from header>
           )
```

### Agent-to-Agent Execution
```
Agent A → MCP client in container → POST /mcp (with agent-scoped key)
                                     ↓
                                  MCP Server validates agent key:
                                  - key_id, agent_name="agent-a"
                                     ↓
                                  POST /api/agents/{name}/chat
                                  Headers:
                                  - X-Source-Agent: agent-a
                                  - X-MCP-Key-ID: agent-a-key
                                  - X-MCP-Key-Name: "agent-a MCP key"
                                     ↓
                                  Backend extracts headers
                                     ↓
                                  db.create_task_execution(
                                      triggered_by="agent",
                                      source_agent_name="agent-a",
                                      source_mcp_key_id=<from header>,
                                      source_mcp_key_name=<from header>
                                  )
```

## Files to Modify

### Backend

| File | Changes |
|------|---------|
| `src/backend/database.py` | Add migration for new columns |
| `src/backend/db_models.py` | Add new fields to `ScheduleExecution`, `ScheduleExecutionCreate` models |
| `src/backend/db/schedules.py` | Update `create_execution()`, `create_task_execution()` to accept new fields |
| `src/backend/routers/chat.py` | Extract MCP key headers, pass to execution creation |
| `src/backend/routers/agents.py` | Update task endpoint similarly |
| `src/backend/routers/schedules.py` | Update execution list endpoint to support filtering |

### MCP Server

| File | Changes |
|------|---------|
| `src/mcp-server/src/server.ts` | Add MCP key info to requests sent to backend |
| `src/mcp-server/src/client.ts` | Include key headers in API calls |

### Frontend

| File | Changes |
|------|---------|
| `src/frontend/src/views/ExecutionDetail.vue` | Add "Triggered By" card with origin info |
| `src/frontend/src/components/TasksPanel.vue` | Add trigger type filter dropdown |

## Database Migration

```sql
-- Migration: Add execution origin tracking columns
ALTER TABLE schedule_executions ADD COLUMN source_user_id INTEGER;
ALTER TABLE schedule_executions ADD COLUMN source_user_email TEXT;
ALTER TABLE schedule_executions ADD COLUMN source_agent_name TEXT;
ALTER TABLE schedule_executions ADD COLUMN source_mcp_key_id TEXT;
ALTER TABLE schedule_executions ADD COLUMN source_mcp_key_name TEXT;

-- Index for filtering by trigger type (already indexed via triggered_by)
CREATE INDEX IF NOT EXISTS idx_executions_source_user ON schedule_executions(source_user_id);
CREATE INDEX IF NOT EXISTS idx_executions_source_agent ON schedule_executions(source_agent_name);
```

## Testing

### Test Cases

1. **Manual task execution**: Verify `source_user_id` and `source_user_email` populated
2. **MCP user call**: Verify MCP key info captured in execution record
3. **Agent-to-agent**: Verify source agent name and key info captured
4. **Schedule execution**: Verify source fields remain NULL (system triggered)
5. **UI display**: Verify ExecutionDetail shows correct origin info
6. **Filtering**: Verify API filtering by `triggered_by` works

### Backward Compatibility

- All new columns are nullable - existing data remains valid
- API responses include new fields with `null` values for old executions
- UI gracefully handles missing origin data ("Unknown" fallback)

## Security Considerations

1. **No credential exposure**: MCP key ID is safe to log, key VALUE is never stored
2. **User email denormalization**: Email stored for query convenience, not as PII exposure
3. **Audit compliance**: This feature SUPPORTS audit requirements (SEC-001) but is not the full audit system

## Related Requirements

- **SEC-001 (Audit Trail System)**: Full audit logging - this feature provides execution-level attribution that feeds into the broader audit system
- **EXEC-022 (Unified Executions Dashboard)**: Will benefit from origin tracking for filtering

## Implementation Phases

### Phase 1: Database & Backend (Priority)
1. Add database columns with migration
2. Update `create_task_execution()` to accept new fields
3. Update chat/task endpoints to capture and pass origin data
4. Update API response models

### Phase 2: MCP Integration
1. MCP server passes key info in headers
2. Backend extracts and uses headers

### Phase 3: Frontend Display
1. ExecutionDetail shows origin card
2. TasksPanel supports filtering

## Success Criteria

1. Every new execution has complete origin attribution stored
2. ExecutionDetail page shows WHO triggered each execution
3. Admins can filter executions by trigger type
4. Agent-to-agent call chains are traceable
5. MCP API key usage is auditable per execution

## Open Questions

1. **Should we track the full call chain for nested agent-to-agent calls?** (e.g., User → Agent A → Agent B → Agent C)
   - Recommendation: Track immediate source only (Agent B in this case), use activity stream for full chain reconstruction

2. **Should schedule executions track which user created the schedule?**
   - Recommendation: Yes, but via schedule record (already has `owner_id`), not duplicated in execution

3. **Should we add MCP key info to activity stream as well?**
   - Recommendation: Yes, for consistency - activity stream should mirror execution origin data
