# Feature: Read-Only Mode (CFG-007)

## Overview

Read-only mode prevents agents from modifying source code, instructions, or configuration files while allowing output to designated directories. Uses Claude Code's PreToolUse hooks to intercept Write/Edit/NotebookEdit operations.

## User Story

As an agent owner, I want to enable read-only mode so that the agent cannot modify critical files (code, configs, CLAUDE.md) while still allowing it to write reports and output files.

## Entry Points

- **UI (Agent Detail)**: `src/frontend/src/components/AgentHeader.vue:128-136` - ReadOnlyToggle component
- **UI (Agents List)**: `src/frontend/src/views/Agents.vue:248-255` - ReadOnlyToggle in card toggles row (between Running and Autonomy)
- **API**: `GET/PUT /api/agents/{name}/read-only`

---

## Frontend Layer

### Components

#### ReadOnlyToggle.vue (172 lines)
`src/frontend/src/components/ReadOnlyToggle.vue`

Reusable toggle component with rose/red color scheme for read-only state indication.

| Line Range | Element | Description |
|------------|---------|-------------|
| 1-68 | Template | Toggle button with lock icon, loading spinner, size variants |
| 70-119 | Props | `modelValue`, `disabled`, `loading`, `showLabel`, `size` |
| 122-162 | Computed | Size classes for sm/md/lg variants |
| 164-170 | toggle() | Emits `update:modelValue` and `toggle` events |

**Features:**
- Rose background when enabled (read-only ON)
- Lock icon inside toggle when enabled
- Loading spinner during API call
- ARIA support with descriptive labels
- Three sizes: sm, md, lg

#### AgentHeader.vue
`src/frontend/src/components/AgentHeader.vue:128-136`

Contains the ReadOnlyToggle in the header actions row.

```vue
<!-- Read-Only Mode Toggle (not for system agents) -->
<template v-if="!agent.is_system && agent.can_share">
  <div class="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>
  <ReadOnlyToggle
    :model-value="agent.read_only_enabled"
    :loading="readOnlyLoading"
    size="md"
    @toggle="$emit('toggle-read-only')"
  />
</template>
```

**Props passed from parent:**
- `readOnlyLoading`: Loading state during API call

**Events emitted:**
- `toggle-read-only`: Triggered when user clicks toggle

### View Handler

#### AgentDetail.vue
`src/frontend/src/views/AgentDetail.vue:373-411`

```javascript
// Read-only mode state
const readOnlyLoading = ref(false)

async function toggleReadOnly() {
  if (!agent.value || readOnlyLoading.value) return

  readOnlyLoading.value = true
  const newState = !agent.value.read_only_enabled

  try {
    const response = await fetch(`/api/agents/${agent.value.name}/read-only`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ enabled: newState })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to update read-only mode')
    }

    const result = await response.json()

    // Update local state
    agent.value.read_only_enabled = newState

    showNotification(
      newState
        ? `Read-only mode enabled. Agent cannot modify source files.${result.hooks_injected ? '' : ' Hooks will be applied on next agent start.'}`
        : 'Read-only mode disabled. Agent can modify all files.',
      'success'
    )
  } catch (error) {
    console.error('Failed to toggle read-only mode:', error)
    showNotification(error.message || 'Failed to update read-only mode', 'error')
  } finally {
    readOnlyLoading.value = false
  }
}
```

### State Management

Agent state includes `read_only_enabled` from backend response.

| Location | Description |
|----------|-------------|
| `AgentDetail.vue:196-197` | `read_only_enabled` extracted in `get_agent_endpoint()` response |
| `AgentDetail.vue:331` | `readOnlyLoading` ref for UI loading state |

### API Calls

```javascript
// Get read-only status
GET /api/agents/{name}/read-only
Authorization: Bearer {token}

// Set read-only status
PUT /api/agents/{name}/read-only
Authorization: Bearer {token}
Content-Type: application/json

{
  "enabled": true,
  "config": {  // Optional - uses defaults if not provided
    "blocked_patterns": ["*.py", "*.js", "CLAUDE.md", ...],
    "allowed_patterns": ["content/*", "output/*", "*.log", ...]
  }
}
```

---

## Backend Layer

### Endpoints

#### routers/agents.py
`src/backend/routers/agents.py:814-848`

```python
@router.get("/{agent_name}/read-only")
async def get_agent_read_only_status(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get the read-only mode status for an agent."""
    from services.agent_service.read_only import get_read_only_status_logic
    return await get_read_only_status_logic(agent_name, current_user)


@router.put("/{agent_name}/read-only")
async def set_agent_read_only_status(
    agent_name: str,
    body: dict,
    current_user: User = Depends(get_current_user)
):
    """Set the read-only mode status for an agent."""
    from services.agent_service.read_only import set_read_only_status_logic
    return await set_read_only_status_logic(agent_name, body, current_user)
```

### Service Layer

#### read_only.py
`src/backend/services/agent_service/read_only.py` (317 lines)

**Functions:**

| Function | Lines | Description |
|----------|-------|-------------|
| `get_default_config()` | 39-44 | Returns default blocked/allowed patterns |
| `get_read_only_status_logic()` | 47-69 | GET endpoint handler - returns status and config |
| `set_read_only_status_logic()` | 72-150 | PUT endpoint handler - validates, saves, injects hooks |
| `inject_read_only_hooks()` | 153-216 | Writes config + guard script + merges settings |
| `_merge_hook_settings()` | 219-267 | Merges PreToolUse hook into settings.local.json |
| `remove_read_only_hooks()` | 270-317 | Removes hook registration from settings |

**Default Blocked Patterns:**
```python
DEFAULT_BLOCKED_PATTERNS = [
    "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.vue", "*.svelte",
    "*.go", "*.rs", "*.rb", "*.java", "*.c", "*.cpp", "*.h",
    "*.sh", "*.bash", "Makefile", "Dockerfile",
    "CLAUDE.md", "README.md", ".claude/*", ".env", ".env.*",
    "template.yaml", "*.yaml", "*.yml", "*.json", "*.toml"
]
```

**Default Allowed Patterns:**
```python
DEFAULT_ALLOWED_PATTERNS = [
    "content/*", "output/*", "reports/*", "exports/*",
    "*.log", "*.txt"
]
```

#### lifecycle.py
`src/backend/services/agent_service/lifecycle.py:243-256`

Hooks are injected during agent startup:

```python
# Inject read-only hooks if enabled
read_only_result = {"status": "skipped", "reason": "not_enabled"}
read_only_data = db.get_read_only_mode(agent_name)
if read_only_data.get("enabled"):
    try:
        read_only_result = await inject_read_only_hooks(agent_name, read_only_data.get("config"))
        if read_only_result.get("success"):
            read_only_result["status"] = "success"
        else:
            read_only_result["status"] = "failed"
    except Exception as e:
        logger.warning(f"Failed to inject read-only hooks into agent {agent_name}: {e}")
        read_only_result = {"status": "failed", "error": str(e)}
```

### Database Operations

#### db/agents.py
`src/backend/db/agents.py:463-516`

```python
def get_read_only_mode(self, agent_name: str) -> dict:
    """
    Get read-only mode status and configuration for an agent.

    Returns:
        dict with 'enabled' (bool) and 'config' (dict or None)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(read_only_mode, 0) as read_only_mode, read_only_config
            FROM agent_ownership WHERE agent_name = ?
        """, (agent_name,))
        row = cursor.fetchone()
        if row:
            import json
            config = None
            if row["read_only_config"]:
                try:
                    config = json.loads(row["read_only_config"])
                except json.JSONDecodeError:
                    config = None
            return {
                "enabled": bool(row["read_only_mode"]),
                "config": config
            }
        return {"enabled": False, "config": None}


def set_read_only_mode(self, agent_name: str, enabled: bool, config: dict = None) -> bool:
    """
    Set read-only mode status and configuration for an agent.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        import json
        config_json = json.dumps(config) if config else None
        cursor.execute("""
            UPDATE agent_ownership SET read_only_mode = ?, read_only_config = ?
            WHERE agent_name = ?
        """, (1 if enabled else 0, config_json, agent_name))
        conn.commit()
        return cursor.rowcount > 0
```

#### database.py Migration
`src/backend/database.py:260-276`

```python
def _migrate_agent_ownership_read_only_mode(cursor, conn):
    """Add read_only_mode and read_only_config columns to agent_ownership table."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("read_only_mode", "INTEGER DEFAULT 0"),  # 0 = disabled, 1 = enabled
        ("read_only_config", "TEXT")  # JSON config for blocked/allowed patterns
    ]

    for col_name, col_def in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to agent_ownership for read-only mode...")
            cursor.execute(f"ALTER TABLE agent_ownership ADD COLUMN {col_name} {col_def}")

    conn.commit()
```

---

## Agent Layer

### Guard Script

#### read-only-guard.py
`config/hooks/read-only-guard.py` (124 lines)

PreToolUse hook script that intercepts Write/Edit/NotebookEdit operations.

**Protocol:**
- Input: JSON via stdin with `tool_input.file_path`
- Exit 0: Allow operation
- Exit 2 + stderr message: Block operation (feedback to Claude)

**Logic Flow:**
1. Parse JSON input from Claude Code
2. Extract `file_path` from `tool_input`
3. Normalize path (strip `/home/developer/`, resolve `../`)
4. Check allowed patterns first (allowed takes precedence)
5. Check blocked patterns
6. Default: allow (anything not blocked is permitted)

```python
def main():
    # Read JSON input from stdin (Claude Code hook protocol)
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # Fail open

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("notebook_path", "")

    if not file_path:
        sys.exit(0)  # Allow

    config = load_config()
    blocked = config.get("blocked_patterns", DEFAULT_BLOCKED)
    allowed = config.get("allowed_patterns", DEFAULT_ALLOWED)

    # Allowed patterns take precedence
    if matches_any(file_path, allowed):
        sys.exit(0)  # Allow

    # Check blocked patterns
    if matches_any(file_path, blocked):
        print(f"Read-only mode: Cannot modify '{file_path}' (protected path)", file=sys.stderr)
        sys.exit(2)  # Block

    sys.exit(0)  # Default allow
```

### Files Written to Agent Container

When read-only mode is enabled, three files are written:

| Path | Purpose |
|------|---------|
| `~/.trinity/read-only-config.json` | Configuration with blocked/allowed patterns |
| `~/.trinity/hooks/read-only-guard.py` | Guard script (copied from config/hooks/) |
| `~/.claude/settings.local.json` | Hook registration merged into existing settings |

### Hook Registration

The hook is registered in `~/.claude/settings.local.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /home/developer/.trinity/hooks/read-only-guard.py"
          }
        ]
      }
    ]
  }
}
```

---

## Data Flow Diagram

```
User clicks ReadOnlyToggle
        │
        ▼
AgentDetail.vue:toggleReadOnly()
        │
        ▼
PUT /api/agents/{name}/read-only
        │
        ▼
routers/agents.py:set_agent_read_only_status()
        │
        ▼
services/agent_service/read_only.py:set_read_only_status_logic()
        │
        ├─► db.set_read_only_mode() - Save to SQLite
        │
        └─► If running: inject_read_only_hooks()
                    │
                    ├─► Write ~/.trinity/read-only-config.json
                    ├─► Write ~/.trinity/hooks/read-only-guard.py
                    └─► Merge into ~/.claude/settings.local.json
```

**On Agent Start:**

```
lifecycle.py:start_agent_internal()
        │
        ▼
db.get_read_only_mode()
        │
        ▼
If enabled: inject_read_only_hooks()
        │
        ├─► AgentClient.write_file() x3
        └─► Return injection result
```

**During Claude Code Operation:**

```
Claude Code: Write/Edit/NotebookEdit
        │
        ▼
PreToolUse hook triggered
        │
        ▼
read-only-guard.py receives JSON input
        │
        ▼
Check file_path against patterns
        │
        ├─► Allowed pattern match → Exit 0 (allow)
        ├─► Blocked pattern match → Exit 2 + stderr (block)
        └─► No match → Exit 0 (allow)
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | Agent not found |
| Not owner | 403 | Only the owner can modify read-only settings |
| System agent | 403 | Cannot modify read-only mode for system agent |
| Missing enabled field | 400 | enabled is required |
| Invalid config type | 400 | config must be an object |
| Invalid patterns | 400 | blocked_patterns/allowed_patterns must be a list |
| Hook injection failed | 200 | Returns `hooks_injected: false` with message |

---

## Security Considerations

1. **Owner-only access**: Only the agent owner (checked via `can_user_share_agent`) can modify read-only settings
2. **System agent protection**: Read-only mode cannot be enabled for the system agent (`trinity-system`)
3. **Fail-safe design**: Guard script fails open (allows) on JSON parse errors or missing file path
4. **Allowed takes precedence**: Even if a file matches blocked patterns, allowed patterns override
5. **Normalized paths**: Guard script normalizes paths to prevent `../` bypasses

---

## API Response Examples

### GET /api/agents/{name}/read-only

```json
{
  "agent_name": "my-agent",
  "enabled": true,
  "config": {
    "blocked_patterns": ["*.py", "*.js", "CLAUDE.md", ...],
    "allowed_patterns": ["content/*", "output/*", "*.log", ...]
  }
}
```

### PUT /api/agents/{name}/read-only

**Request:**
```json
{
  "enabled": true,
  "config": null  // Use defaults
}
```

**Response:**
```json
{
  "status": "updated",
  "agent_name": "my-agent",
  "enabled": true,
  "config": {
    "blocked_patterns": [...],
    "allowed_patterns": [...]
  },
  "hooks_injected": true,
  "message": "Read-only mode enabled."
}
```

---

## Testing

### Prerequisites
- Trinity backend running
- At least one agent created and owned by test user
- Agent running (for immediate hook injection test)

### Test Steps

1. **Enable via UI**
   - Navigate to agent detail page
   - Click ReadOnlyToggle (should show "Editable")
   - Toggle should turn rose/red with lock icon
   - Notification: "Read-only mode enabled"

2. **Verify Hook Injection (Running Agent)**
   - SSH into agent container
   - Check `~/.trinity/read-only-config.json` exists
   - Check `~/.trinity/hooks/read-only-guard.py` exists
   - Check `~/.claude/settings.local.json` has PreToolUse hook

3. **Test File Protection**
   - In agent terminal, try to create a Python file
   - Claude should receive: "Read-only mode: Cannot modify 'test.py' (protected path)"

4. **Test Allowed Patterns**
   - In agent terminal, create file in `content/` directory
   - Should succeed (allowed pattern)

5. **Disable via UI**
   - Click ReadOnlyToggle again
   - Should return to gray "Editable" state
   - Notification: "Read-only mode disabled"

6. **Restart Injection**
   - Enable read-only, stop agent, start agent
   - Verify hooks are injected on startup

### Edge Cases
- Enable on stopped agent: hooks injected on next start
- System agent: toggle should not appear
- Non-owner user: toggle should not appear (requires `can_share`)

---

## Related Flows

- **Upstream**: [agent-lifecycle.md](agent-lifecycle.md) - Hook injection on agent start
- **Related**: [container-capabilities.md](container-capabilities.md) - Similar per-agent security setting
- **Related**: [autonomy-mode.md](autonomy-mode.md) - Similar toggle pattern in AgentHeader

---

## Agents Page Integration

### Entry Point

`src/frontend/src/views/Agents.vue:248-255` - ReadOnlyToggle between Running and Autonomy toggles

### Template Structure

```vue
<!-- Running, Read-Only, and Autonomy toggles (same row) -->
<div class="flex items-center justify-between mb-2">
  <RunningStateToggle ... />
  <ReadOnlyToggle
    v-if="!agent.is_system && !agent.is_shared"
    :model-value="getAgentReadOnlyState(agent.name)"
    :loading="readOnlyLoading === agent.name"
    size="sm"
    @toggle="handleReadOnlyToggle(agent)"
  />
  <AutonomyToggle ... />
</div>
```

**Note (2026-02-18)**: ReadOnlyToggle now shows labels (`:show-label` removed) for consistency with other toggles. All toggles on this row use `size="sm"`.

### State Management

| Line | Element | Description |
|------|---------|-------------|
| 377 | `readOnlyLoading` | Ref tracking which agent's toggle is loading |
| 378 | `agentReadOnlyStates` | Map of agent_name -> boolean read-only state |
| 444 | onMounted | Calls `fetchAllReadOnlyStates()` |

### Functions

| Line | Function | Description |
|------|----------|-------------|
| 540-542 | `getAgentReadOnlyState(agentName)` | Returns boolean from `agentReadOnlyStates` map |
| 544-563 | `fetchAllReadOnlyStates()` | Parallel fetch of read-only status for all owned agents |
| 565-594 | `handleReadOnlyToggle(agent)` | Toggles read-only mode via PUT API, updates local state |

### Visibility Conditions

ReadOnlyToggle only shown when:
- `!agent.is_system` - Not the system agent
- `!agent.is_shared` - User owns the agent (not viewing someone else's shared agent)

### Data Flow

```
User clicks ReadOnlyToggle on agent card
        |
        v
handleReadOnlyToggle(agent) [line 565]
        |
        +-- Set readOnlyLoading = agent.name
        |
        v
PUT /api/agents/{name}/read-only
        |
        +-- Success: Update agentReadOnlyStates[agent.name]
        |            Show notification
        |
        +-- Error: Show error notification
        |
        v
Finally: readOnlyLoading = null
```

---

## Revision History

| Date | Change |
|------|--------|
| 2026-02-18 17:50 | **Toggle Consistency Fix**: Removed `:show-label="false"` from ReadOnlyToggle in Agents.vue - it now shows labels like the other toggles. All toggles (Running, ReadOnly, Autonomy) now use consistent `size="sm"` across both Agents.vue and AgentHeader.vue. |
| 2026-02-18 | **Agents Page Integration**: Added ReadOnlyToggle to Agents.vue card tiles (lines 248-255). Shows for owned agents (not system, not shared). Added `agentReadOnlyStates` state (line 378), `readOnlyLoading` (line 377), `fetchAllReadOnlyStates()` (lines 544-563), `handleReadOnlyToggle()` (lines 565-594). Toggle positioned between Running and Autonomy toggles in same row. |
| 2026-02-17 | Initial documentation (CFG-007) |
