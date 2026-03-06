# Feature: Agent Rename (RENAME-001)

## Overview
Rename agents via UI, MCP tool, or REST API. Updates all database references atomically, renames Docker container, and broadcasts WebSocket events for real-time UI updates. System agents cannot be renamed.

## User Story
As a Trinity platform user, I want to rename my agents so that I can keep agent names meaningful and organized as their purpose evolves.

---

## Entry Points

| Method | Location | Description |
|--------|----------|-------------|
| **UI** | `src/frontend/src/components/AgentHeader.vue:26-35` | Pencil icon next to agent name |
| **API** | `PUT /api/agents/{name}/rename` | REST endpoint with `{new_name}` body |
| **MCP** | `rename_agent` tool | MCP tool with `name` and `new_name` parameters |

---

## Frontend Layer

### AgentHeader.vue (`src/frontend/src/components/AgentHeader.vue`)

**Lines 8-37**: Editable agent name section

```vue
<!-- Inline editing mode -->
<template v-if="isEditingName">
  <input
    ref="nameInput"
    v-model="editedName"
    @keydown.enter="saveName"
    @keydown.escape="cancelEditName"
    @blur="saveName"
  />
</template>

<!-- Display mode with pencil icon -->
<template v-else>
  <h1>{{ agent.name }}</h1>
  <button
    v-if="agent.can_share && !agent.is_system"
    @click="startEditName"
    title="Rename agent"
  >
    <svg><!-- pencil icon --></svg>
  </button>
</template>
```

**Lines 283-294**: Emits list includes `rename` event
```javascript
const emit = defineEmits([
  'toggle', 'delete', 'toggle-autonomy', 'toggle-read-only',
  'open-resource-modal', 'git-pull', 'git-push', 'git-refresh',
  'update-tags', 'add-tag', 'remove-tag', 'rename'
])
```

**Lines 397-431**: Name editing functions
```javascript
function startEditName() {
  editedName.value = props.agent.name
  isEditingName.value = true
  nextTick(() => nameInput.value?.focus())
}

function saveName() {
  const trimmed = editedName.value.trim()
  if (!trimmed || trimmed === props.agent.name) {
    cancelEditName()
    return
  }
  emit('rename', trimmed)
  isEditingName.value = false
}
```

### AgentDetail.vue (`src/frontend/src/views/AgentDetail.vue`)

**Lines 457-494**: `renameAgent()` handler

```javascript
async function renameAgent(newName) {
  if (!agent.value || renameLoading.value) return
  renameLoading.value = true

  try {
    const response = await fetch(`/api/agents/${agent.value.name}/rename`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ new_name: newName })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to rename agent')
    }

    const result = await response.json()
    showNotification(`Agent renamed to '${result.new_name}'`, 'success')

    // Navigate to new URL
    router.replace({ name: 'AgentDetail', params: { name: result.new_name } })
  } catch (error) {
    showNotification(error.message, 'error')
  } finally {
    renameLoading.value = false
  }
}
```

**Line 59**: Event handler wiring in template
```vue
<AgentHeader @rename="renameAgent" ... />
```

---

## Backend Layer

### Endpoint (`src/backend/routers/agents.py:1362-1510`)

```python
class RenameAgentRequest(BaseModel):
    new_name: str

@router.put("/{agent_name}/rename")
async def rename_agent_endpoint(
    agent_name: str,
    body: RenameAgentRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
```

**Business Logic Flow**:

1. **Permission Check** (lines 1397-1407)
   ```python
   if not db.can_user_rename_agent(current_user.username, agent_name):
       if db.is_system_agent(agent_name):
           raise HTTPException(403, "System agents cannot be renamed")
       raise HTTPException(403, "Permission denied")
   ```

2. **Name Validation** (lines 1410-1425)
   ```python
   # Sanitize for Docker compatibility
   sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '-', new_name.lower())
   sanitized_name = re.sub(r'-+', '-', sanitized_name).strip('-')

   # Validate
   if len(sanitized_name) > 63:
       raise HTTPException(400, "Name too long")
   if sanitized_name == agent_name:
       raise HTTPException(400, "New name same as current")
   ```

3. **Check Name Availability** (lines 1428-1430)
   ```python
   existing = get_agent_container(sanitized_name)
   if existing:
       raise HTTPException(409, "Agent already exists")
   ```

4. **Stop Container if Running** (lines 1440-1443)
   ```python
   was_running = container.status == "running"
   if was_running:
       await container_stop(container)
   ```

5. **Rename Docker Container** (lines 1446-1448)
   ```python
   new_container_name = f"agent-{sanitized_name}"
   await container_rename(container, new_container_name)
   ```

6. **Update Database** (lines 1468-1474)
   ```python
   if not db.rename_agent(agent_name, sanitized_name):
       # Rollback container rename on failure
       await container_rename(container, f"agent-{agent_name}")
       raise HTTPException(500, "Database update failed")
   ```

7. **Broadcast WebSocket** (lines 1477-1489)
   ```python
   event = {
       "event": "agent_renamed",
       "type": "agent_renamed",
       "name": sanitized_name,
       "data": {"old_name": agent_name, "new_name": sanitized_name}
   }
   await manager.broadcast(json.dumps(event))
   await filtered_manager.broadcast_filtered(event)
   ```

8. **Return Response** (lines 1495-1501)
   ```python
   return {
       "message": f"Agent renamed from '{agent_name}' to '{sanitized_name}'",
       "old_name": agent_name,
       "new_name": sanitized_name,
       "was_running": was_running,
       "note": "Restart needed" if was_running else None
   }
   ```

### Async Docker Wrapper (`src/backend/services/docker_utils.py:82-90`)

```python
async def container_rename(container, new_name: str) -> None:
    """Rename a container without blocking the event loop."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _docker_executor,
        lambda: container.rename(new_name)
    )
```

---

## Data Layer

### Database Operations (`src/backend/db/agents.py:620-800`)

**`rename_agent()` Method** (lines 624-779)

Atomically updates `agent_name` in all 17 tables that reference it:

| Table | Field(s) Updated |
|-------|------------------|
| `agent_ownership` | `agent_name` (primary) |
| `agent_sharing` | `agent_name` |
| `agent_schedules` | `agent_name` |
| `schedule_executions` | `agent_name` |
| `chat_sessions` | `agent_name` |
| `chat_messages` | `agent_name` |
| `agent_activities` | `agent_name` |
| `agent_permissions` | `source_agent` AND `target_agent` |
| `agent_shared_folder_config` | `agent_name` |
| `agent_git_config` | `agent_name` |
| `agent_skills` | `agent_name` |
| `agent_tags` | `agent_name` |
| `agent_public_links` | `agent_name` |
| `mcp_api_keys` | `agent_name` |
| `agent_health_checks` | `agent_name` |
| `agent_dashboard_values` | `agent_name` |
| `monitoring_alert_cooldowns` | `agent_name` |

```python
def rename_agent(self, old_name: str, new_name: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # Validate old exists, new doesn't
            # Update all 17 tables in transaction
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            conn.rollback()
            return False
```

**`can_user_rename_agent()` Method** (lines 781-800)

```python
def can_user_rename_agent(self, username: str, agent_name: str) -> bool:
    """Check if user can rename (owner or admin, NOT system agents)."""
    user = self._user_ops.get_user_by_username(username)
    if not user:
        return False

    owner = self.get_agent_owner(agent_name)
    if owner and owner.get("is_system", False):
        return False  # System agents cannot be renamed

    if user["role"] == "admin":
        return True
    if owner and owner["owner_username"] == username:
        return True

    return False
```

---

## MCP Layer

### Tool Definition (`src/mcp-server/src/tools/agents.ts:260-296`)

```typescript
renameAgent: {
  name: "rename_agent",
  description:
    "Rename an agent in the Trinity platform. " +
    "Changes the agent name across all references. " +
    "System agents cannot be renamed. Only owners or admins can rename.",
  parameters: z.object({
    name: z.string().describe("Current agent name"),
    new_name: z.string().describe("New agent name"),
  }),
  execute: async ({ name, new_name }, context) => {
    const authContext = context?.session;

    // Prevent system agent self-rename
    if (authContext?.scope === "system" && authContext?.agentName === name) {
      return JSON.stringify({
        error: "Cannot rename system agent",
        reason: "System agents cannot be renamed."
      });
    }

    const apiClient = getClient(authContext);
    const result = await apiClient.renameAgent(name, new_name);
    return JSON.stringify(result, null, 2);
  },
}
```

### Client Method (`src/mcp-server/src/client.ts:277-296`)

```typescript
async renameAgent(
  name: string,
  newName: string
): Promise<{
  message: string;
  old_name: string;
  new_name: string;
  was_running: boolean;
  note?: string;
}> {
  return this.request<{...}>(
    "PUT",
    `/api/agents/${encodeURIComponent(name)}/rename`,
    { new_name: newName }
  );
}
```

---

## Side Effects

### WebSocket Broadcasts

| Event | Payload | Recipients |
|-------|---------|------------|
| `agent_renamed` | `{old_name, new_name}` | All connected UI clients |

Both main WebSocket manager and filtered Trinity Connect manager receive the event.

### Docker Operations

| Operation | Effect |
|-----------|--------|
| `container_stop()` | Stops container if running |
| `container_rename()` | Changes container name from `agent-{old}` to `agent-{new}` |

Note: Container is NOT auto-restarted. Volume rename is deferred to next restart via `recreate_container_with_updated_config()`.

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Not authorized | 403 | "You don't have permission to rename this agent" |
| System agent | 403 | "System agents cannot be renamed" |
| Empty name | 400 | "New name cannot be empty" |
| Same name | 400 | "New name is the same as current name" |
| Name too long | 400 | "Agent name too long (max 63 characters)" |
| Invalid after sanitize | 400 | "Invalid agent name after sanitization" |
| Name taken | 409 | "Agent with name '{name}' already exists" |
| Agent not found | 404 | "Agent not found" |
| Database failure | 500 | "Failed to update database" |
| Docker failure | 500 | "Failed to rename agent: {error}" |

---

## Security Considerations

1. **Authorization**: Only agent owners and platform admins can rename agents
2. **System Agent Protection**: `trinity-system` and other `is_system=true` agents cannot be renamed
3. **Name Sanitization**: All names sanitized for Docker/DNS compatibility (lowercase, alphanumeric + hyphens)
4. **Atomic Updates**: Database changes wrapped in transaction with rollback on failure
5. **Container Rollback**: If database update fails, container name is restored

---

## Testing

### Prerequisites
- Backend running at http://localhost:8000
- Frontend running at http://localhost
- Logged in as agent owner or admin
- Agent exists and is not a system agent

### Test Steps

1. **UI Rename (Happy Path)**
   - Action: Click pencil icon, type new name, press Enter
   - Expected: Name updates, URL changes, notification shown
   - Verify: `docker ps` shows new container name

2. **Cancel Rename**
   - Action: Click pencil, type name, press Escape
   - Expected: Reverts to original name, no API call

3. **API Rename**
   ```bash
   curl -X PUT http://localhost:8000/api/agents/old-name/rename \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"new_name": "new-name"}'
   ```
   - Expected: `{"message": "Agent renamed...", "old_name": "...", "new_name": "..."}`

4. **MCP Tool Rename**
   - Action: Use `rename_agent` tool with name and new_name
   - Expected: Same response as API

5. **Error Cases**
   - [ ] Try renaming system agent -> 403
   - [ ] Try renaming as non-owner -> 403
   - [ ] Try duplicate name -> 409
   - [ ] Try empty name -> 400

---

## Related Flows

- **Parent**: [agent-lifecycle.md](agent-lifecycle.md) - Rename is part of agent lifecycle
- **Related**: [agent-sharing.md](agent-sharing.md) - Shares are updated atomically
- **Related**: [scheduling.md](scheduling.md) - Schedules are updated atomically
- **Related**: [mcp-orchestration.md](mcp-orchestration.md) - MCP tool interface

---

**Last Updated**: 2026-03-01
**Status**: Implemented
**Issues**: None - feature fully operational
