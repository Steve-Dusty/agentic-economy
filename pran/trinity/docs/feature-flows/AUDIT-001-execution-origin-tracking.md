# Feature: Execution Origin Tracking (AUDIT-001)

## Overview

Tracks WHO triggered each execution in Trinity by capturing the complete identity of the actor: user information, MCP API key details, and source agent for agent-to-agent calls. This enables audit trails, accountability, and debugging of execution chains.

## User Story

- **As a platform admin**, I want to see which user triggered each execution so I can audit usage and troubleshoot issues.
- **As an agent owner**, I want to know when my agent was called by other agents or external MCP clients so I can understand usage patterns.
- **As a developer**, I want to trace execution chains across agents to debug multi-agent workflows.

## Entry Points

| Trigger Type | UI | API |
|--------------|-----|-----|
| **Manual** | TasksPanel.vue "Run" button | `POST /api/agents/{name}/task` |
| **MCP (User)** | Claude Code with MCP key | MCP `chat_with_agent` tool |
| **MCP (Agent)** | Agent calling via MCP | MCP `chat_with_agent` tool with agent scope |
| **Schedule** | Automatic cron trigger | Dedicated scheduler service |

## Data Model

### New Columns (schedule_executions table)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `source_user_id` | INTEGER | Yes | FK to `users.id` - User who triggered |
| `source_user_email` | TEXT | Yes | User's email (denormalized for queries) |
| `source_agent_name` | TEXT | Yes | Calling agent name (for agent-to-agent) |
| `source_mcp_key_id` | TEXT | Yes | MCP API key ID used (for MCP calls) |
| `source_mcp_key_name` | TEXT | Yes | MCP API key name (denormalized) |

### Pydantic Model

```python
# src/backend/db_models.py:137-161
class ScheduleExecution(BaseModel):
    # ... existing fields ...
    # Origin tracking fields (AUDIT-001)
    source_user_id: Optional[int] = None
    source_user_email: Optional[str] = None
    source_agent_name: Optional[str] = None
    source_mcp_key_id: Optional[str] = None
    source_mcp_key_name: Optional[str] = None
```

---

## Data Flow Diagrams

### Flow 1: Manual Task Execution

```
User (browser)
    -> TasksPanel.vue "Run" button (line 97-100)
    -> POST /api/agents/{name}/task
    -> routers/chat.py:execute_parallel_task (line 545)
        - Extract current_user from JWT
        - triggered_by = "manual"
    -> db.create_task_execution() (line 587-596)
        - source_user_id = current_user.id
        - source_user_email = current_user.email
        - source_agent_name = None
        - source_mcp_key_id = None
        - source_mcp_key_name = None
    -> schedule_executions table
```

### Flow 2: MCP User Execution

```
Claude Code
    -> POST /mcp (with Authorization: Bearer trinity_mcp_xxx)
    -> MCP Server validates key (server.ts:44-64)
        - Returns: key_id, key_name, user_email, scope="user"
    -> McpAuthContext stored in session (server.ts:142-151)
        - keyId, keyName, agentName, scope
    -> chat_with_agent tool (tools/chat.ts:196-290)
        - Builds mcpKeyInfo from authContext (line 245-248)
    -> client.chat() or client.task() (client.ts:403-539)
        - Headers: X-Via-MCP: true
        - Headers: X-MCP-Key-ID, X-MCP-Key-Name
    -> POST /api/agents/{name}/chat or /task
    -> routers/chat.py (lines 112-116)
        - Extract headers: x_mcp_key_id, x_mcp_key_name
    -> db.create_task_execution() (line 178-187)
        - source_user_id = current_user.id (from MCP key validation)
        - source_user_email = current_user.email
        - source_mcp_key_id = x_mcp_key_id
        - source_mcp_key_name = x_mcp_key_name
        - triggered_by = "mcp"
```

### Flow 3: Agent-to-Agent Execution

```
Agent A (orchestrator)
    -> MCP client in container
    -> POST /mcp (with agent-scoped key)
    -> MCP Server validates agent key
        - Returns: key_id, agent_name="agent-a", scope="agent"
    -> chat_with_agent tool
        - sourceAgent = authContext.agentName
        - mcpKeyInfo = { keyId, keyName }
    -> client.task() (client.ts:474-539)
        - Headers: X-Source-Agent: agent-a
        - Headers: X-Via-MCP: true
        - Headers: X-MCP-Key-ID, X-MCP-Key-Name
    -> POST /api/agents/{name}/task
    -> routers/chat.py:execute_parallel_task
        - Extract x_source_agent header
        - triggered_by = "agent"
    -> db.create_task_execution() (line 587-596)
        - source_user_id = None (agent is the actor)
        - source_user_email = None
        - source_agent_name = "agent-a"
        - source_mcp_key_id = agent's key ID
        - source_mcp_key_name = agent's key name
```

### Flow 4: Schedule Execution

```
Scheduler Service (src/scheduler/service.py)
    -> Cron trigger fires
    -> _execute_schedule_job()
    -> Creates execution via backend API
    -> db.create_schedule_execution()
        - source_user_id = None (system triggered)
        - source_user_email = None
        - source_agent_name = None
        - source_mcp_key_id = None
        - source_mcp_key_name = None
        - triggered_by = "schedule"

Note: Schedule owner is tracked via schedule.owner_id,
not duplicated in execution record.
```

---

## Frontend Layer

### ExecutionDetail.vue - Origin Display

**File**: `src/frontend/src/views/ExecutionDetail.vue`

**Lines 164-190**: Origin Information Card

```vue
<!-- Origin Information (AUDIT-001) -->
<div v-if="hasOriginInfo" class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
  <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Execution Origin</h3>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
    <!-- User -->
    <div v-if="execution.source_user_email">
      <span class="text-gray-500">User:</span>
      <span class="ml-2 font-medium">{{ execution.source_user_email }}</span>
    </div>
    <!-- Source Agent (for agent-to-agent) -->
    <div v-if="execution.source_agent_name">
      <span class="text-gray-500">Source Agent:</span>
      <router-link :to="{ name: 'AgentDetail', params: { name: execution.source_agent_name } }">
        {{ execution.source_agent_name }}
      </router-link>
    </div>
    <!-- MCP Key (for MCP calls) -->
    <div v-if="execution.source_mcp_key_name">
      <span class="text-gray-500">MCP Key:</span>
      <span class="ml-2 font-medium">{{ execution.source_mcp_key_name }}</span>
    </div>
  </div>
</div>
```

**Lines 426-432**: Computed property for origin info detection

```javascript
const hasOriginInfo = computed(() => {
  if (!execution.value) return false
  return execution.value.source_user_email ||
         execution.value.source_agent_name ||
         execution.value.source_mcp_key_name
})
```

### TasksPanel.vue - Trigger Type Filter

**File**: `src/frontend/src/components/TasksPanel.vue`

**Lines 9-20**: Filter dropdown

```vue
<select v-model="triggerFilter" class="text-xs px-2 py-1.5 ...">
  <option value="all">All triggers</option>
  <option value="manual">Manual</option>
  <option value="schedule">Schedule</option>
  <option value="mcp">MCP</option>
  <option value="agent">Agent</option>
</select>
```

---

## Backend Layer

### Database Migration

**File**: `src/backend/database.py:333-356`

```python
def _migrate_execution_origin_tracking(cursor, conn):
    """Add execution origin tracking columns to schedule_executions table (AUDIT-001)."""
    cursor.execute("PRAGMA table_info(schedule_executions)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("source_user_id", "INTEGER"),
        ("source_user_email", "TEXT"),
        ("source_agent_name", "TEXT"),
        ("source_mcp_key_id", "TEXT"),
        ("source_mcp_key_name", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to schedule_executions...")
            cursor.execute(f"ALTER TABLE schedule_executions ADD COLUMN {col_name} {col_type}")

    conn.commit()
```

### Execution Creation Functions

**File**: `src/backend/db/schedules.py`

**Lines 430-493**: `create_task_execution()` - For manual/API-triggered tasks

```python
def create_task_execution(
    self,
    agent_name: str,
    message: str,
    triggered_by: str = "manual",
    source_user_id: int = None,
    source_user_email: str = None,
    source_agent_name: str = None,
    source_mcp_key_id: str = None,
    source_mcp_key_name: str = None,
) -> Optional[ScheduleExecution]:
```

**Lines 495-553**: `create_schedule_execution()` - For scheduled tasks

```python
def create_schedule_execution(
    self,
    schedule_id: str,
    agent_name: str,
    message: str,
    triggered_by: str = "schedule",
    source_user_id: int = None,
    # ... same parameters
) -> Optional[ScheduleExecution]:
```

### Chat Router Header Extraction

**File**: `src/backend/routers/chat.py`

**Lines 112-116**: Header parameters

```python
@router.post("/{name}/chat")
async def chat_with_agent(
    name: str,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    x_source_agent: Optional[str] = Header(None),
    x_via_mcp: Optional[str] = Header(None),
    x_mcp_key_id: Optional[str] = Header(None),
    x_mcp_key_name: Optional[str] = Header(None)
):
```

**Lines 178-187**: Execution creation with origin data

```python
task_execution = db.create_task_execution(
    agent_name=name,
    message=request.message,
    triggered_by=triggered_by,
    source_user_id=current_user.id,
    source_user_email=current_user.email or current_user.username,
    source_agent_name=x_source_agent,
    source_mcp_key_id=x_mcp_key_id,
    source_mcp_key_name=x_mcp_key_name
)
```

---

## MCP Server Layer

### Authentication Context

**File**: `src/mcp-server/src/types.ts:64-72`

```typescript
export interface McpAuthContext extends Record<string, unknown> {
  userId: string;
  userEmail?: string;
  keyId?: string;        // MCP API key ID (AUDIT-001)
  keyName: string;
  agentName?: string;    // For agent-scoped keys
  scope: "user" | "agent" | "system";
  mcpApiKey?: string;
}
```

### Server Key Validation

**File**: `src/mcp-server/src/server.ts:142-151`

```typescript
const authContext: McpAuthContext = {
  userId: result.user_id || "unknown",
  userEmail: result.user_email,
  keyId: result.key_id,  // MCP API key ID (AUDIT-001)
  keyName: result.key_name || "unknown",
  agentName: result.agent_name,
  scope: scope as "user" | "agent" | "system",
  mcpApiKey: apiKey,
};
```

### Chat Tool MCP Key Info

**File**: `src/mcp-server/src/tools/chat.ts:244-248`

```typescript
// Build MCP key info for execution origin tracking (AUDIT-001)
const mcpKeyInfo = authContext ? {
  keyId: authContext.keyId,
  keyName: authContext.keyName,
} : undefined;
```

### Client Header Injection

**File**: `src/mcp-server/src/client.ts:421-427`

```typescript
// Add MCP key info headers for execution origin tracking (AUDIT-001)
if (mcpKeyInfo?.keyId) {
  headers["X-MCP-Key-ID"] = mcpKeyInfo.keyId;
}
if (mcpKeyInfo?.keyName) {
  headers["X-MCP-Key-Name"] = mcpKeyInfo.keyName;
}
```

---

## Scheduler Layer

### Models

**File**: `src/scheduler/models.py:68-73`

```python
@dataclass
class ScheduleExecution:
    # ... existing fields ...
    # Origin tracking fields (AUDIT-001)
    source_user_id: Optional[int] = None
    source_user_email: Optional[str] = None
    source_agent_name: Optional[str] = None
    source_mcp_key_id: Optional[str] = None
    source_mcp_key_name: Optional[str] = None
```

### Database Row Mapping

**File**: `src/scheduler/database.py:101-107`

```python
# Origin tracking fields (AUDIT-001)
source_user_id=row["source_user_id"] if "source_user_id" in row_keys else None,
source_user_email=row["source_user_email"] if "source_user_email" in row_keys else None,
source_agent_name=row["source_agent_name"] if "source_agent_name" in row_keys else None,
source_mcp_key_id=row["source_mcp_key_id"] if "source_mcp_key_id" in row_keys else None,
source_mcp_key_name=row["source_mcp_key_name"] if "source_mcp_key_name" in row_keys else None
```

---

## Origin Data by Trigger Type

| Trigger Type | source_user_id | source_user_email | source_agent_name | source_mcp_key_id | source_mcp_key_name |
|--------------|----------------|-------------------|-------------------|-------------------|---------------------|
| **Manual** | current_user.id | current_user.email | NULL | NULL | NULL |
| **Schedule** | NULL | NULL | NULL | NULL | NULL |
| **MCP (User)** | MCP key owner ID | MCP key owner email | NULL | MCP key ID | MCP key name |
| **MCP (Agent)** | NULL | NULL | source agent name | agent's MCP key ID | agent's MCP key name |

---

## API Response Examples

### Execution with Manual Trigger

```json
{
  "id": "abc123",
  "agent_name": "my-agent",
  "triggered_by": "manual",
  "source_user_id": 1,
  "source_user_email": "user@example.com",
  "source_agent_name": null,
  "source_mcp_key_id": null,
  "source_mcp_key_name": null
}
```

### Execution with MCP User Trigger

```json
{
  "id": "def456",
  "agent_name": "my-agent",
  "triggered_by": "mcp",
  "source_user_id": 1,
  "source_user_email": "user@example.com",
  "source_agent_name": null,
  "source_mcp_key_id": "key_abc123",
  "source_mcp_key_name": "My Claude Code"
}
```

### Execution with Agent-to-Agent Trigger

```json
{
  "id": "ghi789",
  "agent_name": "worker-agent",
  "triggered_by": "agent",
  "source_user_id": null,
  "source_user_email": null,
  "source_agent_name": "orchestrator-agent",
  "source_mcp_key_id": "key_orch123",
  "source_mcp_key_name": "orchestrator-agent MCP key"
}
```

---

## Error Handling

| Error Case | HTTP Status | Handling |
|------------|-------------|----------|
| Invalid MCP API key | 401 | MCP Server rejects request before backend |
| Missing headers | N/A | Fields stored as NULL (backward compatible) |
| Old executions without origin data | N/A | Fields return NULL (backward compatible) |

---

## Security Considerations

1. **No credential exposure**: MCP key ID is safe to store; key VALUE is never stored in executions
2. **User email denormalization**: Email stored for query convenience, mirrors existing patterns
3. **Audit trail support**: This feature provides execution-level attribution that feeds into broader audit systems
4. **Backward compatibility**: All new columns are nullable - existing data remains valid

---

## Testing

### Prerequisites

- Trinity platform running with MCP server
- At least one agent created
- MCP API key created for testing

### Test Cases

1. **Manual Task Execution**
   - Trigger a task via TasksPanel
   - Verify `source_user_id` and `source_user_email` populated
   - Verify origin info displayed on ExecutionDetail page

2. **MCP User Call**
   - Call `chat_with_agent` via Claude Code with MCP key
   - Verify MCP key info captured in execution record
   - Verify `triggered_by = "mcp"`

3. **Agent-to-Agent Call**
   - Configure agent with MCP key
   - Have agent call another agent
   - Verify `source_agent_name` captured
   - Verify `triggered_by = "agent"`

4. **Schedule Execution**
   - Create and trigger a schedule
   - Verify all source fields are NULL
   - Verify `triggered_by = "schedule"`

5. **Filter by Trigger Type**
   - Use TasksPanel dropdown to filter by trigger type
   - Verify filtered results match expected executions

6. **Backward Compatibility**
   - View old executions created before migration
   - Verify UI handles missing origin data gracefully ("Unknown" fallback)

---

## Related Flows

- **Upstream**: [execution-queue.md](execution-queue.md) - Queue submission creates execution record
- **Upstream**: [mcp-api-keys.md](mcp-api-keys.md) - Key validation provides origin data
- **Downstream**: [execution-detail-page.md](execution-detail-page.md) - Displays origin info
- **Downstream**: [tasks-tab.md](tasks-tab.md) - Filter by trigger type

---

## Files Changed

### Backend

| File | Changes |
|------|---------|
| `src/backend/database.py:333-356` | Migration function `_migrate_execution_origin_tracking()` |
| `src/backend/db_models.py:156-161` | Origin fields in `ScheduleExecution` model |
| `src/backend/db/schedules.py:430-553` | `create_task_execution()`, `create_schedule_execution()` accept origin params |
| `src/backend/routers/chat.py:112-116` | Extract MCP key headers |
| `src/backend/routers/chat.py:178-187,587-596` | Pass origin data to execution creation |

### MCP Server

| File | Changes |
|------|---------|
| `src/mcp-server/src/types.ts:64-72` | `McpAuthContext` includes `keyId` |
| `src/mcp-server/src/server.ts:142-151` | Store `keyId` in auth context |
| `src/mcp-server/src/tools/chat.ts:244-248` | Build `mcpKeyInfo` from auth context |
| `src/mcp-server/src/client.ts:421-427,499-505` | Inject `X-MCP-Key-ID`, `X-MCP-Key-Name` headers |

### Scheduler

| File | Changes |
|------|---------|
| `src/scheduler/models.py:68-73` | Origin fields in `ScheduleExecution` dataclass |
| `src/scheduler/database.py:101-107` | Map origin columns in `_row_to_execution()` |

### Frontend

| File | Changes |
|------|---------|
| `src/frontend/src/views/ExecutionDetail.vue:164-190` | Origin Information card |
| `src/frontend/src/views/ExecutionDetail.vue:426-432` | `hasOriginInfo` computed property |
| `src/frontend/src/components/TasksPanel.vue:9-20` | Trigger type filter dropdown |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-02-20 | Initial implementation (AUDIT-001) |
