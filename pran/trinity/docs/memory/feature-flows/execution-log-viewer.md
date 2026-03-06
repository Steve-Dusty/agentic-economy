# Feature: Execution Log Viewer

## Overview

The Execution Log Viewer displays Claude Code execution transcripts in a formatted chat-like interface within the Tasks panel. When users click the document icon on a completed task, a modal window shows the complete execution history including Claude's thinking, tool calls, tool results, and final cost/duration metrics.

**Important**: All execution types (scheduled, manual trigger, user tasks, MCP calls) now use the same log format - raw Claude Code `stream-json` output. This was standardized on 2025-01-02 (scheduler) and 2026-01-10 (chat endpoint) by ensuring all endpoints return raw format.

**Performance Note (PERF-001)**: The `execution_log` field is excluded from the list endpoint (`GET /api/agents/{name}/executions`) for performance. The log viewer fetches logs via the dedicated endpoint (`GET /api/agents/{name}/executions/{id}/log`), which is unaffected by this optimization.

## User Story

As an agent operator, I want to view the complete execution transcript of any task so that I can understand what Claude did, debug issues, and verify the reasoning process.

## Entry Points

- **UI**: `src/frontend/src/components/TasksPanel.vue:234-243` - Document icon button on task rows
- **API**: `GET /api/agents/{name}/executions/{id}/log` - Retrieve stored execution log

---

## Frontend Layer

### Components

**TasksPanel.vue:234-243** - View Log Button:
```vue
<!-- View Log Button (Modal) -->
<button
  v-if="task.status !== 'running' && !task.id.startsWith('local-')"
  @click="viewExecutionLog(task)"
  class="p-1.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 rounded transition-colors"
  title="View execution log (modal)"
>
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
</button>
```

**Button Visibility Logic**:
- Only shown when `task.status !== 'running'` (completed/failed tasks only)
- Only shown when `!task.id.startsWith('local-')` (server-persisted tasks only)

**TasksPanel.vue:316-432** - Execution Log Modal:
```vue
<Teleport to="body">
  <div
    v-if="showLogModal"
    class="fixed inset-0 z-50 overflow-y-auto"
    @click.self="closeLogModal"
  >
    <div class="flex items-center justify-center min-h-screen p-4">
      <div class="fixed inset-0 bg-black/50 transition-opacity"></div>
      <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
        <!-- Modal Header -->
        <!-- Modal Body with formatted transcript -->
      </div>
    </div>
  </div>
</Teleport>
```

### State Management

**TasksPanel.vue:499-503** - Modal State:
```javascript
// Execution log modal state
const showLogModal = ref(false)
const logData = ref(null)
const logLoading = ref(false)
const logError = ref(null)
```

### API Calls

**TasksPanel.vue:803-820** - viewExecutionLog():
```javascript
async function viewExecutionLog(task) {
  showLogModal.value = true
  logLoading.value = true
  logError.value = null
  logData.value = null

  try {
    const response = await axios.get(`/api/agents/${props.agentName}/executions/${task.id}/log`, {
      headers: authStore.authHeader
    })
    logData.value = response.data
  } catch (error) {
    logError.value = error.response?.data?.detail || error.message || 'Failed to load execution log'
  } finally {
    logLoading.value = false
  }
}
```

**TasksPanel.vue:822-827** - closeLogModal():
```javascript
function closeLogModal() {
  showLogModal.value = false
  logData.value = null
  logError.value = null
}
```

### Log Parsing

**TasksPanel.vue:839-930** - parseExecutionLog():

This function transforms raw Claude Code JSON stream output into structured entries for display.

```javascript
function parseExecutionLog(log) {
  if (!log) return []

  // Handle string log (legacy format)
  if (typeof log === 'string') {
    try {
      log = JSON.parse(log)
    } catch {
      return [{ type: 'assistant-text', text: log }]
    }
  }

  // Must be an array
  if (!Array.isArray(log)) {
    return [{ type: 'assistant-text', text: JSON.stringify(log, null, 2) }]
  }

  const entries = []

  for (const msg of log) {
    // Session init message
    if (msg.type === 'system' && msg.subtype === 'init') {
      entries.push({
        type: 'init',
        model: msg.model || 'unknown',
        toolCount: msg.tools?.length || 0,
        mcpServers: msg.mcp_servers?.map(s => s.name) || []
      })
      continue
    }

    // Assistant message (can contain text and/or tool_use)
    if (msg.type === 'assistant') {
      const content = msg.message?.content || []
      for (const block of content) {
        if (block.type === 'text' && block.text) {
          entries.push({ type: 'assistant-text', text: block.text })
        } else if (block.type === 'tool_use') {
          entries.push({
            type: 'tool-call',
            tool: block.name || 'unknown',
            input: typeof block.input === 'string'
              ? block.input
              : JSON.stringify(block.input, null, 2)
          })
        }
      }
      continue
    }

    // User message (typically tool results)
    if (msg.type === 'user') {
      const content = msg.message?.content || []
      for (const block of content) {
        if (block.type === 'tool_result') {
          let resultContent = block.content
          if (Array.isArray(resultContent)) {
            resultContent = resultContent
              .map(c => c.text || c.content || JSON.stringify(c))
              .join('\n')
          }
          // Truncate very long results
          if (resultContent && resultContent.length > 2000) {
            resultContent = resultContent.substring(0, 2000) + '\n... (truncated)'
          }
          entries.push({
            type: 'tool-result',
            content: resultContent || '(empty result)'
          })
        }
      }
      continue
    }

    // Final result message
    if (msg.type === 'result') {
      entries.push({
        type: 'result',
        numTurns: msg.num_turns || msg.numTurns || '-',
        duration: msg.duration_ms ? formatDuration(msg.duration_ms) : (msg.duration || '-'),
        cost: msg.cost_usd?.toFixed(4) || msg.total_cost_usd?.toFixed(4) || '0.0000'
      })
      continue
    }
  }

  return entries
}
```

### Entry Types and Rendering

| Entry Type | Source Message | Visual Style | Content |
|------------|----------------|--------------|---------|
| `init` | `{type: "system", subtype: "init"}` | Gray box | Model, tool count, MCP servers |
| `assistant-text` | `{type: "assistant", message.content[].type: "text"}` | Indigo bubble | Claude's thinking text |
| `tool-call` | `{type: "assistant", message.content[].type: "tool_use"}` | Amber bubble | Tool name + JSON input |
| `tool-result` | `{type: "user", message.content[].type: "tool_result"}` | Green bubble | Result content (truncated if >2000 chars) |
| `result` | `{type: "result"}` | Gray box with border | Turns, duration, cost |

**Visual Components**:

**Init Block (lines 357-369)**:
```vue
<div v-if="entry.type === 'init'" class="bg-gray-100 dark:bg-gray-900 rounded-lg p-3 text-xs">
  <div class="flex items-center space-x-2 text-gray-500 dark:text-gray-400 mb-1">
    <span class="font-semibold">Session Started</span>
    <span>{{ entry.model }}</span>
    <span>{{ entry.toolCount }} tools</span>
  </div>
  <div v-if="entry.mcpServers.length" class="text-gray-400 dark:text-gray-500">
    MCP: {{ entry.mcpServers.join(', ') }}
  </div>
</div>
```

**Assistant Text (lines 371-382)**:
```vue
<div v-else-if="entry.type === 'assistant-text'" class="flex space-x-3">
  <div class="flex-shrink-0 w-8 h-8 bg-indigo-100 dark:bg-indigo-900/50 rounded-full flex items-center justify-center">
    <!-- Computer icon -->
  </div>
  <div class="flex-1 min-w-0 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-3">
    <div class="text-xs font-medium text-indigo-700 dark:text-indigo-300 mb-1">Claude</div>
    <div class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words">{{ entry.text }}</div>
  </div>
</div>
```

**Tool Call (lines 384-398)**:
```vue
<div v-else-if="entry.type === 'tool-call'" class="flex space-x-3">
  <div class="flex-shrink-0 w-8 h-8 bg-amber-100 dark:bg-amber-900/50 rounded-full flex items-center justify-center">
    <!-- Gear icon -->
  </div>
  <div class="flex-1 min-w-0 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3">
    <span class="text-xs font-medium text-amber-700 dark:text-amber-300">{{ entry.tool }}</span>
    <pre class="text-xs text-gray-600 dark:text-gray-400 bg-white/50 dark:bg-black/20 rounded p-2 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">{{ entry.input }}</pre>
  </div>
</div>
```

**Tool Result (lines 400-411)**:
```vue
<div v-else-if="entry.type === 'tool-result'" class="flex space-x-3">
  <div class="flex-shrink-0 w-8 h-8 bg-green-100 dark:bg-green-900/50 rounded-full flex items-center justify-center">
    <!-- Checkmark icon -->
  </div>
  <div class="flex-1 min-w-0 bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
    <div class="text-xs font-medium text-green-700 dark:text-green-300 mb-1">Result</div>
    <pre class="text-xs text-gray-600 dark:text-gray-400 ... max-h-48 overflow-y-auto">{{ entry.content }}</pre>
  </div>
</div>
```

**Final Result (lines 413-425)**:
```vue
<div v-else-if="entry.type === 'result'" class="bg-gray-100 dark:bg-gray-900 rounded-lg p-3 text-xs border-t-2 border-gray-300 dark:border-gray-600">
  <div class="flex items-center justify-between text-gray-500 dark:text-gray-400">
    <div class="flex items-center space-x-3">
      <span class="font-semibold text-green-600 dark:text-green-400">Completed</span>
      <span>{{ entry.numTurns }} turns</span>
    </div>
    <div class="flex items-center space-x-3 font-mono">
      <span>{{ entry.duration }}</span>
      <span class="text-indigo-600 dark:text-indigo-400">${{ entry.cost }}</span>
    </div>
  </div>
</div>
```

---

## Backend Layer

### Endpoint

**File**: `src/backend/routers/schedules.py:339-379`

```python
@router.get("/{name}/executions/{execution_id}/log")
async def get_execution_log(
    name: AuthorizedAgent,
    execution_id: str
):
    """
    Get the full execution log for a specific execution.

    Returns the raw Claude Code execution transcript as JSON array.
    This includes all tool calls, thinking, and responses.
    """
    execution = db.get_execution(execution_id)
    if not execution or execution.agent_name != name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )

    if not execution.execution_log:
        return {
            "execution_id": execution_id,
            "has_log": False,
            "log": None,
            "message": "No execution log available for this execution"
        }

    # Parse the JSON log for structured response
    try:
        log_data = json.loads(execution.execution_log)
    except json.JSONDecodeError:
        log_data = execution.execution_log

    return {
        "execution_id": execution_id,
        "agent_name": name,
        "has_log": True,
        "log": log_data,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "status": execution.status
    }
```

### Response Models

**Log Available**:
```json
{
  "execution_id": "abc123",
  "agent_name": "my-agent",
  "has_log": true,
  "log": [
    {"type": "system", "subtype": "init", "model": "sonnet", "tools": [...], "mcp_servers": [...]},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "Let me analyze..."}, {"type": "tool_use", "name": "Read", "input": {...}}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result", "content": [...]}]}},
    {"type": "result", "num_turns": 3, "duration_ms": 5000, "cost_usd": 0.0045}
  ],
  "started_at": "2025-12-31T10:00:00Z",
  "completed_at": "2025-12-31T10:01:00Z",
  "status": "success"
}
```

**No Log Available**:
```json
{
  "execution_id": "abc123",
  "has_log": false,
  "log": null,
  "message": "No execution log available for this execution"
}
```

---

## Agent Layer

### Log Capture

Both `/api/chat` and `/api/task` endpoints now capture and return raw Claude Code `stream-json` format.

**File**: `docker/base-image/agent_server/services/claude_code.py`

**`execute_claude_code()` (lines 389-546)** - For chat endpoint:
```python
async def execute_claude_code(prompt: str, stream: bool = False, model: Optional[str] = None) -> tuple[str, List[ExecutionLogEntry], ExecutionMetadata, List[Dict]]:
    # ...
    execution_log: List[ExecutionLogEntry] = []
    raw_messages: List[Dict] = []  # Capture ALL raw JSON messages for execution log viewer

    def read_subprocess_output():
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            # Capture raw JSON for full execution log (same as execute_headless_task)
            try:
                raw_msg = json.loads(line.strip())
                raw_messages.append(raw_msg)
            except json.JSONDecodeError:
                pass
            # Process each line for activity tracking
            process_stream_line(line, execution_log, metadata, tool_start_times, response_parts)

    # Returns: (response_text, execution_log, metadata, raw_messages)
    return response_text, execution_log, metadata, raw_messages
```

**`execute_headless_task()` (lines 553-766)** - For task endpoint:
```python
async def execute_headless_task(
    prompt: str,
    model: Optional[str] = None,
    allowed_tools: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    timeout_seconds: int = 900,
    max_turns: Optional[int] = None,
    execution_id: Optional[str] = None
) -> tuple[str, List[ExecutionLogEntry], ExecutionMetadata, str]:
    # ...
    raw_messages: List[Dict] = []  # Capture ALL raw JSON messages from Claude Code

    # Read stdout (stream-json for metadata)
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        # Capture raw JSON for full execution log
        try:
            raw_msg = json.loads(line.strip())
            raw_messages.append(raw_msg)
        except json.JSONDecodeError:
            pass

    # Return raw_messages as the execution log (full JSON transcript from Claude Code)
    return response_text, raw_messages, metadata, final_session_id
```

### Chat Endpoint Returns Raw Format

**File**: `docker/base-image/agent_server/routers/chat.py:24-93`

```python
@router.post("/api/chat")
async def chat(request: ChatRequest):
    # ...
    response_text, execution_log, metadata, raw_messages = await runtime.execute(
        prompt=request.message,
        model=effective_model,
        continue_session=True,
        stream=request.stream
    )

    # Return enhanced response with execution log and session stats
    # Use raw_messages (full Claude Code JSON transcript) for execution log viewer compatibility
    return {
        "response": response_text,
        "execution_log": raw_messages,  # Full Claude Code stream-json format for UI
        "execution_log_simplified": [entry.model_dump() for entry in execution_log],  # For activity tracking
        "metadata": metadata.model_dump(),
        "session": {...},
        "timestamp": datetime.now().isoformat()
    }
```

### Task Endpoint Returns Raw Format

**File**: `docker/base-image/agent_server/routers/chat.py:96-137`

```python
@router.post("/api/task")
async def execute_task(request: ParallelTaskRequest):
    # ...
    response_text, raw_messages, metadata, session_id = await runtime.execute_headless(
        prompt=request.message,
        model=request.model,
        # ...
    )

    # raw_messages contains the full Claude Code JSON stream (init, assistant, user, result)
    return {
        "response": response_text,
        "execution_log": raw_messages,  # Full JSON transcript from Claude Code
        "metadata": metadata.model_dump(),
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }
```

### Claude Code Output Format

Claude Code with `--output-format stream-json` outputs one JSON object per line:

| Message Type | Content | Example |
|--------------|---------|---------|
| `system` (init) | Session info, tools, MCP servers | `{"type": "system", "subtype": "init", "model": "sonnet", ...}` |
| `assistant` | Claude's thinking and tool calls | `{"type": "assistant", "message": {"content": [...]}}` |
| `user` | Tool results | `{"type": "user", "message": {"content": [...]}}` |
| `result` | Final stats | `{"type": "result", "num_turns": 3, "cost_usd": 0.0045}` |

---

## Data Layer

### Storage

The execution log is stored in the `schedule_executions` table:

**Column**: `execution_log TEXT`

**Storage Location**: `src/backend/db/schedules.py` - `update_execution_status()` method

```python
def update_execution_status(
    self,
    execution_id: str,
    status: str,
    response: str = None,
    error: str = None,
    context_used: int = None,
    context_max: int = None,
    cost: float = None,
    tool_calls: str = None,
    execution_log: str = None  # Full JSON transcript
) -> bool:
    cursor.execute("""
        UPDATE schedule_executions
        SET status = ?, completed_at = ?, duration_ms = ?, response = ?, error = ?,
            context_used = ?, context_max = ?, cost = ?, tool_calls = ?, execution_log = ?
        WHERE id = ?
    """, (..., execution_log, execution_id))
```

### Log Persistence

**Backend Chat Router** (`src/backend/routers/chat.py`):
```python
# Update execution record with success
if execution_id:
    if "execution_log" in response_data and response_data["execution_log"] is not None:
        try:
            execution_log_json = json.dumps(response_data["execution_log"])
        except Exception:
            pass

    db.update_execution_status(
        execution_id=execution_id,
        status="success",
        response=response_data.get("response"),
        # ...
        execution_log=execution_log_json
    )
```

---

## Error Handling

| Error Case | HTTP Status | UI Display |
|------------|-------------|------------|
| Execution not found | 404 | Error message in modal |
| Access denied | 403 | Error message in modal |
| No log available | 200 | "No execution log available for this task." |
| JSON parse error | - | Fallback to raw string display |
| Network error | - | Error message in modal |

---

## Security Considerations

1. **Authorization**: Uses `AuthorizedAgent` dependency that calls `db.can_user_access_agent()` check before returning log
2. **Agent Ownership**: Only agent owners/shared users can view execution logs
3. **Credential Sanitization** (Added 2026-02-16): All execution logs are sanitized before storage to prevent credential leakage:
   - **Agent-side**: `sanitize_subprocess_line()` and `sanitize_dict()` filter credentials from subprocess output in real-time (`docker/base-image/agent_server/services/claude_code.py:491-529`)
   - **Backend-side**: `sanitize_execution_log()` provides defense-in-depth before database persistence (`src/backend/routers/chat.py:283-286, 699-712`)
   - **Patterns detected**: API keys (sk-*, ghp_*, trinity_mcp_*), OAuth tokens, Bearer/Basic auth, sensitive env vars
4. **Log Content**: Logs may contain file contents from tool results (but credentials are redacted)
5. **Truncation**: Tool results >2000 chars are truncated in display (not storage)

---

## Log Format Standardization

### Phase 1: Scheduler Fix (2025-01-02)

**Problem**: Scheduled executions were not displaying in the log viewer. The root cause was that the scheduler used `/api/chat` which returned a simplified format.

**Solution**: Added `AgentClient.task()` method (`src/backend/services/agent_client.py`) that calls `/api/task` and returns raw format.

### Phase 2: Chat Endpoint Fix (2026-01-10)

**Problem**: MCP calls and interactive chat executions still returned simplified format.

**Original Issue**:
| Endpoint | Response Format | `parseExecutionLog()` Compatible |
|----------|-----------------|----------------------------------|
| `/api/task` | Raw Claude Code `stream-json` | Yes |
| `/api/chat` | Simplified `ExecutionLogEntry` | No |

**Solution**: Modified the agent server to return raw format from both endpoints:

1. **Agent Server Changes** (`docker/base-image/agent_server/`):
   - `services/claude_code.py`: Updated `execute_claude_code()` to capture `raw_messages`
   - `services/runtime_adapter.py`: Updated abstract interface signature
   - `routers/chat.py`: Returns `raw_messages` as `execution_log`

2. **Backend Changes** (`src/backend/routers/chat.py`):
   - Extracts both `execution_log` (raw) and `execution_log_simplified`
   - Uses simplified format for activity tracking
   - Stores raw format in database for UI

### Verification

All execution types now produce logs that `parseExecutionLog()` can render:
- **User tasks** (via Tasks panel Run button): Uses `/api/task` directly
- **Scheduled tasks** (cron): Uses `AgentClient.task()` -> `/api/task`
- **Manual triggers** (play button): Uses `AgentClient.task()` -> `/api/task`
- **MCP calls** (user or agent-to-agent): Uses `/api/chat` -> raw format
- **Terminal chat**: Uses `/api/chat` -> raw format

---

## Related Flows

- **Upstream**: [tasks-tab.md](tasks-tab.md) - Tasks panel that hosts the log viewer
- **Upstream**: [parallel-headless-execution.md](parallel-headless-execution.md) - How tasks are executed and logs captured
- **Upstream**: [scheduling.md](scheduling.md) - Scheduled executions now use `/api/task` for raw log format
- **Related**: [agent-terminal.md](agent-terminal.md) - Alternative interactive execution method

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-02-21 | **PERF-001**: Added note that `execution_log` is excluded from list endpoint for performance. Log viewer uses dedicated `/log` endpoint which is unaffected. |
| 2026-02-16 | **Security Fix (Credential Sanitization)**: Execution logs are now sanitized at two layers before storage. Agent-side: `sanitize_subprocess_line()` filters Claude Code output in real-time. Backend-side: `sanitize_execution_log()` provides defense-in-depth. Sensitive patterns (API keys, tokens, auth headers) are replaced with `***REDACTED***`. Updated Security Considerations section. |
| 2026-01-23 | **Line number update**: Updated all line number references to match current implementation. View Log Button moved to lines 234-243. Modal at lines 316-432. Modal state at lines 499-503. viewExecutionLog() at lines 803-820. parseExecutionLog() at lines 839-930. Visual components at lines 357-425. Backend endpoint at lines 339-379 (using AuthorizedAgent dependency). Agent server execute_claude_code() at lines 389-546, execute_headless_task() at lines 553-766. |
| 2026-01-10 | **Chat endpoint log fix**: Updated `/api/chat` to return raw Claude Code format. Modified `execute_claude_code()` to capture `raw_messages`. Backend now extracts both formats for activity tracking and UI. All execution types including MCP calls now produce parseable logs. |
| 2025-01-02 | **Scheduler log fix**: Documented switch from `/api/chat` to `/api/task` for scheduled executions. Added `AgentClient.task()` method and `_parse_task_response()`. All execution types now produce parseable logs. |
| 2025-12-31 | Initial documentation |

---

## Testing

### Prerequisites
- Trinity platform running
- At least one agent created and running
- At least one completed task execution

### Test Steps

1. **View Execution Log (Success)**
   - Go to Agent Detail -> Tasks tab
   - Complete a task (e.g., "What is 2+2?")
   - Click document icon on completed task
   - **Expected**: Modal opens showing formatted transcript

2. **Verify Entry Types**
   - Execute a task that uses tools (e.g., "Read the file at /home/user/test.txt")
   - View execution log
   - **Expected**: See init block, assistant text, tool-call block, tool-result block, result block

3. **Handle No Log**
   - Find an older execution from before log capture was implemented
   - Click view log
   - **Expected**: "No execution log available for this task." message

4. **Truncation of Long Results**
   - Execute a task that reads a large file
   - View execution log
   - **Expected**: Tool result shows "... (truncated)" after 2000 chars

5. **Modal Close**
   - Open execution log modal
   - Click outside modal or X button
   - **Expected**: Modal closes, state resets

### Edge Cases
- View log while task is running (button should be hidden)
- View log for local-only task (button should be hidden)
- View log with corrupted JSON (should fallback to raw string)

### Status
Implemented and verified 2025-12-31
