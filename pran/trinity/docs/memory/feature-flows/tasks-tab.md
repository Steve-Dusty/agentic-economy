# Feature: Tasks Tab

## Overview

The Tasks tab provides a unified view for headless agent executions within the Agent Detail page. It consolidates all task executions (manual, scheduled, agent-to-agent) into a single interface with the ability to trigger new tasks directly, monitor running tasks and queue status in real-time, and re-run historical tasks.

**Performance Optimization (2026-02-21)**: The list endpoint now returns lightweight `ExecutionSummary` objects (excluding large `response`, `error`, `tool_calls`, `execution_log` fields). Task details are fetched on-demand when users expand a task row. This reduces data transfer by 50-100x for agents with many executions.

**Log Format Standardization (2025-01-02)**: All execution types (manual tasks, scheduled executions, manual triggers) now use the `/api/task` endpoint which returns raw Claude Code `stream-json` format. This ensures the [Execution Log Viewer](execution-log-viewer.md) can properly render all execution transcripts.

## User Story

As an agent operator, I want to view and trigger headless task executions from a single location so that I can manage agent workloads without entering the terminal or managing multiple interfaces.

## Entry Points

- **UI**: `src/frontend/src/views/AgentDetail.vue:201-204` - Tasks tab button
- **UI**: `src/frontend/src/components/TasksPanel.vue` - Main component
- **API**: `POST /api/agents/{name}/task` - Execute a parallel task (creates execution record)
- **API**: `POST /api/agents/{name}/chat` - Agent-to-agent chat (creates execution record when `X-Source-Agent` header present) *(added 2025-12-30)*
- **API**: `GET /api/agents/{name}/executions` - Get execution summaries (lightweight, excludes large fields)
- **API**: `GET /api/agents/{name}/executions/{id}` - Get full execution details (on-demand)
- **API**: `GET /api/agents/{name}/executions/{execution_id}/log` - Get full execution log *(added 2025-12-31)*
- **API**: `GET /api/agents/{name}/queue` - Get queue status
- **API**: `POST /api/agents/{name}/queue/clear` - Clear queued tasks
- **API**: `POST /api/agents/{name}/queue/release` - Force release queue

---

## Frontend Layer

### Components

**AgentDetail.vue:884-885** - Tab content rendering:
```vue
<!-- Tasks Tab Content -->
<div v-if="activeTab === 'tasks'" class="p-6">
  <TasksPanel v-if="agent" :agent-name="agent.name" :agent-status="agent.status" />
</div>
```

**TasksPanel.vue** - Main tasks component with the following sections:
- **Header (lines 4-47)**: Title, queue status indicator, refresh button
- **Summary Stats (lines 49-69)**: Total tasks, success rate, total cost, avg duration - Compact layout with smaller padding (`px-3 py-2`) and text (`text-base`, `text-[10px]`)
- **New Task Input (lines 71-101)**: Model selector + textarea for task message, Run button - Uses `items-stretch` so Run button height matches textarea
  - **Model Selector (line 86, MODEL-001)**: `ModelSelector` component above textarea, persisted per-agent in localStorage
  - **Keyboard shortcuts**: Enter to submit, Shift+Enter for newline, Cmd/Ctrl+Enter also works
- **Task History (lines 103-315)**: Scrollable list of all tasks with expand/collapse
  - **Action Buttons per Task** (lines 210-311):
    - Open Execution Detail (lines 211-233): External link / Live button for running tasks
    - View Log (lines 234-244): Modal for execution transcript
    - Copy Input (lines 245-254): Copy task message to clipboard
    - **Stop Execution** (lines 255-271): Terminate running task (new 2026-01-12)
    - Re-run (lines 272-283): Repeat the same task
    - **Make Repeatable** (lines 284-294): Create schedule from task message (calendar icon)
    - Expand/Collapse (lines 295-310): Show/hide task details
- **Execution Log Modal (lines 317-433)**: Modal for viewing execution transcript
- **Queue Management (lines 435-453)**: Force release and clear queue buttons

### Events Emitted

**TasksPanel.vue:451** - Component events:
```javascript
const emit = defineEmits(['create-schedule'])
```

- `create-schedule`: Emitted when user clicks "Make Repeatable" button, passes task message

### State Management

**TasksPanel.vue:510-530** - Local reactive state:
```javascript
const props = defineProps({
  agentName: { type: String, required: true },
  agentStatus: { type: String, default: 'stopped' },
  highlightExecutionId: { type: String, default: null },
  initialMessage: { type: String, default: '' }
})

// State
const executions = ref([])           // Server-persisted executions (ExecutionSummary - lightweight)
const pendingTasks = ref([])         // Local tasks awaiting server response
const queueStatus = ref(null)        // Current queue status
const loading = ref(true)
const newTaskMessage = ref('')       // New task input
const taskLoading = ref(false)       // Submit in progress
const expandedTaskId = ref(null)     // Currently expanded task
const expandLoadingTaskId = ref(null)  // PERF-001: Track which task is loading details
const taskDetailsCache = ref({})     // PERF-001: Cache for task details (response/error)
const terminatingTaskId = ref(null)  // Task being terminated (new 2026-01-12)
const runningExecutions = ref([])    // Running executions from agent (for termination)

// Model selection (MODEL-001) - persisted per-agent in localStorage
const taskModelKey = computed(() => `trinity-task-model-${props.agentName}`)
const selectedModel = ref(localStorage.getItem(`trinity-task-model-${props.agentName}`) || 'claude-opus-4-5')
watch(selectedModel, (val) => { localStorage.setItem(taskModelKey.value, val) })
```

**Computed Properties (lines 291-316)**:
```javascript
// Combine local pending tasks with server executions for seamless UX
const allTasks = computed(() => {
  const pending = pendingTasks.value.filter(p => {
    return !executions.value.some(e => e.message === p.message && e.started_at === p.started_at)
  })
  return [...pending, ...executions.value]
})

const successRate = computed(() => { /* ... */ })
const totalCost = computed(() => { /* ... */ })
const avgDuration = computed(() => { /* ... */ })
```

### API Calls

**Load Executions (lines 329-338)** - Returns lightweight `ExecutionSummary`:
```javascript
async function loadExecutions() {
  // PERF-001: Returns ExecutionSummary (excludes response, error, tool_calls, execution_log)
  const response = await axios.get(`/api/agents/${props.agentName}/executions?limit=100`, {
    headers: authStore.authHeader
  })
  executions.value = response.data
}
```

**Fetch Task Details on Expand (lines 805-836)** - PERF-001 on-demand loading:
```javascript
// PERF-001: Fetch task details when user expands a task row
async function fetchTaskDetails(taskId) {
  // Skip local tasks (no server record yet)
  if (taskId.startsWith('local-')) {
    return
  }

  // Check cache first
  if (taskDetailsCache.value[taskId] !== undefined) {
    return
  }

  // Fetch full details from server
  expandLoadingTaskId.value = taskId
  try {
    const response = await axios.get(`/api/agents/${props.agentName}/executions/${taskId}`, {
      headers: authStore.authHeader
    })
    // Cache response and error fields
    taskDetailsCache.value[taskId] = {
      response: response.data.response,
      error: response.data.error
    }
  } catch (error) {
    console.error('Failed to load task details:', error)
    taskDetailsCache.value[taskId] = { response: null, error: null }
  } finally {
    expandLoadingTaskId.value = null
  }
}
```

**Load Queue Status (lines 341-354)**:
```javascript
async function loadQueueStatus() {
  if (props.agentStatus !== 'running') {
    queueStatus.value = null
    return
  }
  const response = await axios.get(`/api/agents/${props.agentName}/queue`, {
    headers: authStore.authHeader
  })
  queueStatus.value = response.data
}
```

**Run New Task (lines 357-433)**:
```javascript
async function runNewTask() {
  // Create local pending task for immediate UI feedback
  const localTask = {
    id: 'local-' + Date.now(),
    message: taskMessage,
    status: 'running',
    triggered_by: 'manual',
    started_at: new Date().toISOString(),
    // ... other fields
  }
  pendingTasks.value.unshift(localTask)

  // Submit to server (MODEL-001: include selected model)
  const payload = { message: taskMessage }
  if (selectedModel.value) {
    payload.model = selectedModel.value
  }
  const response = await axios.post(`/api/agents/${props.agentName}/task`, payload, {
    headers: authStore.authHeader })

  // Update local task with response data
  // Refresh server executions
  await loadExecutions()
  loadQueueStatus()
}
```

**Make Repeatable (lines 654-657)**:
```javascript
// Create schedule from task (make repeatable)
function makeRepeatable(task) {
  emit('create-schedule', task.message)
}
```

This emits the `create-schedule` event with the task message, which is handled by AgentDetail.vue to switch to the Schedules tab with the message pre-filled.

**Queue Management (lines 908-936)**:
```javascript
async function forceReleaseQueue() {
  await axios.post(`/api/agents/${props.agentName}/queue/release`, {}, {
    headers: authStore.authHeader
  })
  await loadQueueStatus()
}

async function clearQueue() {
  await axios.post(`/api/agents/${props.agentName}/queue/clear`, {}, {
    headers: authStore.authHeader
  })
  await loadQueueStatus()
}
```

### Execution Termination (Added 2026-01-12)

Running tasks can be stopped via the Stop button, which terminates the Claude Code subprocess gracefully.

**Load Running Executions** (lines 619-634):
```javascript
async function loadRunningExecutions() {
  if (props.agentStatus !== 'running') {
    runningExecutions.value = []
    return
  }
  const response = await axios.get(`/api/agents/${props.agentName}/executions/running`, {
    headers: authStore.authHeader
  })
  runningExecutions.value = response.data.executions || []
}
```

**Execution ID Matching** (lines 509-530):
```javascript
// Enhance running tasks with execution_id from runningExecutions
const enhanceWithExecutionId = (task) => {
  if (task.status !== 'running' || task.execution_id) {
    return task
  }
  // Match by message preview (first 100 chars)
  const match = runningExecutions.value.find(e =>
    e.metadata?.message_preview === task.message.substring(0, 100)
  )
  if (match) {
    return { ...task, execution_id: match.execution_id }
  }
  return task
}
```

**Terminate Task** (lines 742-777):
```javascript
async function terminateTask(task) {
  if (!task.execution_id) return

  terminatingTaskId.value = task.id
  try {
    await axios.post(
      `/api/agents/${props.agentName}/executions/${task.execution_id}/terminate`,
      {},
      { headers: authStore.authHeader }
    )
    // Update task status locally
    // Refresh data to get updated status
    await loadAllData()
  } finally {
    terminatingTaskId.value = null
  }
}
```

See [execution-termination.md](execution-termination.md) for full feature documentation.

### Polling

Queue status is polled every 5 seconds when agent is running (watch handler on agentStatus prop).

---

## Backend Layer

### Endpoints

#### POST /api/agents/{name}/task

**File**: `src/backend/routers/chat.py:358-569`

Execute a stateless task in parallel mode (no conversation context).

**Request Model** (`src/backend/models.py`):
```python
class ParallelTaskRequest(BaseModel):
    message: str  # The task to execute
    model: Optional[str] = None  # Model override: sonnet, opus, haiku
    allowed_tools: Optional[List[str]] = None  # Tool restrictions
    system_prompt: Optional[str] = None  # Additional instructions
    timeout_seconds: Optional[int] = 300  # Execution timeout
```

**Business Logic (lines 358-569)**:
1. Validate agent container exists and is running
2. Determine execution source (user or agent-to-agent via `X-Source-Agent` header)
3. **Create task execution record in database** via `db.create_task_execution()`
4. Track activity via `activity_service.track_activity()`
5. If agent-to-agent, broadcast collaboration event via WebSocket
6. Forward request to agent's internal `/api/task` endpoint
7. Update execution record with result (success/failure, cost, duration)
8. Log audit event

**Key difference from /chat**: This endpoint does NOT use the execution queue - tasks run in parallel.

#### GET /api/agents/{name}/executions

**File**: `src/backend/routers/schedules.py:435-459`

Get execution summaries for an agent - optimized for list views.

**PERF-001 (2026-02-21)**: Returns lightweight `ExecutionSummary` objects that exclude large text fields (`response`, `error`, `tool_calls`, `execution_log`). This reduces data transfer by 50-100x for agents with many executions.

```python
@router.get("/{name}/executions", response_model=List[ExecutionSummary])
async def get_agent_executions(
    name: AuthorizedAgent,
    limit: int = 50
):
    """Get execution summaries for an agent - optimized for list views.

    Returns lightweight ExecutionSummary objects that exclude large text fields:
    - response, error, tool_calls, execution_log

    For full execution details including response/error, use:
    GET /api/agents/{name}/executions/{id}
    """
    executions = db.get_agent_executions_summary(name, limit=limit)
    return executions
```

#### GET /api/agents/{name}/executions/{id}

**File**: `src/backend/routers/schedules.py:462-476`

Get full execution details including response, error, and execution_log. Used for on-demand loading when user expands a task row.

```python
@router.get("/{name}/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    name: AuthorizedAgent,
    execution_id: str
):
    """Get full details of a specific execution."""
    execution = db.get_execution(execution_id)
    if not execution or execution.agent_name != name:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionResponse(**execution.model_dump())
```

#### GET /api/agents/{name}/queue

**File**: `src/backend/routers/agents.py:445-451`
**Service**: `src/backend/services/agent_service/queue.py:18-43`

Get execution queue status for an agent.

```python
@router.get("/{agent_name}/queue")
async def get_agent_queue_status(agent_name: str, current_user: User = Depends(get_current_user)):
    return await get_agent_queue_status_logic(agent_name, current_user)
```

Returns `QueueStatus` model with:
- `is_busy`: Whether agent is currently executing
- `current_execution`: Details of running execution
- `queue_length`: Number of waiting executions
- `queued_executions`: List of queued execution details

#### GET /api/agents/{name}/executions/{execution_id}/log

**File**: `src/backend/routers/schedules.py:426-473`

Get the full execution log for a specific execution. *(Added 2025-12-31)*

```python
@router.get("/{name}/executions/{execution_id}/log")
async def get_execution_log(
    name: str,
    execution_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the full execution log for a specific execution."""
```

**Response** (log available):
```json
{
  "execution_id": "abc123",
  "agent_name": "my-agent",
  "has_log": true,
  "log": [
    {"type": "assistant", "message": {...}},
    {"type": "tool_use", "name": "Read", "input": {...}},
    {"type": "tool_result", "content": [...]}
  ],
  "started_at": "2025-12-31T10:00:00Z",
  "completed_at": "2025-12-31T10:01:00Z",
  "status": "success"
}
```

**Response** (no log):
```json
{
  "execution_id": "abc123",
  "has_log": false,
  "log": null,
  "message": "No execution log available for this execution"
}
```

#### POST /api/agents/{name}/queue/clear

**File**: `src/backend/routers/agents.py:454-460`
**Service**: `src/backend/services/agent_service/queue.py:46-82`

Clear all queued executions for an agent (does not stop running execution).

#### POST /api/agents/{name}/queue/release

**File**: `src/backend/routers/agents.py:463-469`
**Service**: `src/backend/services/agent_service/queue.py:85-124`

Force release an agent from its running state (emergency use for stuck executions).

---

## Agent Layer

### Agent Server Endpoint

**File**: `docker/base-image/agent_server/routers/chat.py:83-119`

```python
@router.post("/api/task")
async def execute_task(request: ParallelTaskRequest):
    """
    Execute a stateless task in parallel mode (no conversation context).

    Unlike /api/chat, this endpoint:
    - Does NOT acquire execution lock (parallel allowed)
    - Does NOT use --continue flag (stateless)
    - Each call is independent and can run concurrently
    """
    response_text, execution_log, metadata, session_id = await execute_headless_task(
        prompt=request.message,
        model=request.model,
        allowed_tools=request.allowed_tools,
        system_prompt=request.system_prompt,
        timeout_seconds=request.timeout_seconds or 300
    )

    return {
        "response": response_text,
        "execution_log": [entry.model_dump() for entry in execution_log],
        "metadata": metadata.model_dump(),
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }
```

### Claude Code Execution

The `execute_headless_task()` function in `agent_server/services/claude_code.py` runs Claude Code without conversation context:

```bash
claude --print --output-format stream-json --model {model} "prompt"
```

**Key differences from conversational chat**:
- No `--continue` flag (fresh context each time)
- No conversation history updates
- No execution lock (parallel allowed)
- Unique session ID generated per execution

---

## Data Layer

### Database Operations

**File**: `src/backend/db/schedules.py:298-328`

**Create Task Execution**:
```python
def create_task_execution(self, agent_name: str, message: str, triggered_by: str = "manual") -> Optional[ScheduleExecution]:
    """Create a new execution record for a manual/API-triggered task (no schedule)."""
    execution_id = self._generate_id()
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO schedule_executions (
            id, schedule_id, agent_name, status, started_at, message, triggered_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        execution_id,
        "__manual__",  # Special marker for manual/API-triggered tasks
        agent_name,
        "running",
        now,
        message,
        triggered_by
    ))
```

**Update Execution Status** (`src/backend/db/schedules.py:362-405`):
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
    tool_calls: str = None
) -> bool:
    # Calculate duration from started_at
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)
    # Update record
```

**Get Agent Executions Summary** (`src/backend/db/schedules.py:655-682`) - PERF-001:
```python
def get_agent_executions_summary(self, agent_name: str, limit: int = 50) -> List[dict]:
    """Get execution summaries for list view - excludes large text fields.

    Returns lightweight dicts without: response, error, tool_calls, execution_log
    """
    cursor.execute("""
        SELECT
            id, schedule_id, agent_name, status, started_at, completed_at,
            duration_ms, message, triggered_by, context_used, context_max, cost,
            source_user_id, source_user_email, source_agent_name,
            source_mcp_key_id, source_mcp_key_name, claude_session_id
        FROM schedule_executions
        WHERE agent_name = ?
        ORDER BY started_at DESC
        LIMIT ?
    """, (agent_name, limit))
    return [dict(row) for row in cursor.fetchall()]
```

**Get Full Execution** (`src/backend/db/schedules.py:447-453`):
```python
def get_execution(self, execution_id: str) -> Optional[ScheduleExecution]:
    """Get a specific execution by ID with all fields."""
    cursor.execute("SELECT * FROM schedule_executions WHERE id = ?", (execution_id,))
    row = cursor.fetchone()
    return self._row_to_schedule_execution(row) if row else None
```

**Note**: The `create_task_execution` method was added 2025-12-28 specifically for manual task persistence.

### Database Schema

**Table**: `schedule_executions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT | Unique execution ID |
| `schedule_id` | TEXT | Schedule ID or `__manual__` for tasks |
| `agent_name` | TEXT | Agent name |
| `status` | TEXT | pending, running, success, failed |
| `started_at` | TEXT | ISO timestamp |
| `completed_at` | TEXT | ISO timestamp (nullable) |
| `duration_ms` | INTEGER | Execution duration in ms |
| `message` | TEXT | Task message |
| `response` | TEXT | Claude's response (nullable) |
| `error` | TEXT | Error message if failed (nullable) |
| `triggered_by` | TEXT | manual, schedule, agent |
| `context_used` | INTEGER | Tokens used (nullable) |
| `context_max` | INTEGER | Context window size (nullable) |
| `cost` | REAL | Cost in USD (nullable) |
| `tool_calls` | TEXT | JSON array of tool calls (nullable) |
| `execution_log` | TEXT | Full Claude Code execution transcript (JSON, nullable) *(added 2025-12-31)* |
| `model_used` | TEXT | Model used for this execution (nullable) *(added 2026-03-02, MODEL-001)* |

**Index** (PERF-001):
```sql
CREATE INDEX IF NOT EXISTS idx_executions_agent_started
ON schedule_executions(agent_name, started_at DESC)
```

This composite index optimizes the `WHERE agent_name = ? ORDER BY started_at DESC` query pattern used by the list endpoint.

---

## Execution Queue (Redis)

**File**: `src/backend/services/execution_queue.py`

The execution queue ensures only one execution runs per agent at a time for the `/chat` endpoint. **Note: The `/task` endpoint bypasses this queue entirely for parallel execution.**

### Queue Configuration

```python
MAX_QUEUE_SIZE = 3           # Max queued requests per agent
EXECUTION_TTL = 600          # 10 minutes max execution time
QUEUE_WAIT_TIMEOUT = 120     # 120 seconds max wait in queue
```

### Redis Keys

- `agent:running:{agent_name}` - Currently running execution (JSON)
- `agent:queue:{agent_name}` - Waiting queue (Redis list)

### QueueStatus Model

```python
class QueueStatus(BaseModel):
    agent_name: str
    is_busy: bool
    current_execution: Optional[Execution] = None
    queue_length: int
    queued_executions: List[Execution] = []
```

---

## Side Effects

### WebSocket Broadcasts

**Agent Collaboration Event** (when X-Source-Agent header present):
```python
{
    "type": "agent_collaboration",
    "source_agent": "orchestrator",
    "target_agent": "worker",
    "action": "parallel_task",
    "timestamp": "2025-12-28T10:00:00Z"
}
```

### Audit Log

**File**: `src/backend/routers/chat.py:430-443`

```python
await log_audit_event(
    event_type="agent_interaction",
    action="parallel_task",
    user_id=current_user.username,
    agent_name=name,
    resource=f"agent-{name}",
    result="success",
    details={
        "source": source.value,
        "source_agent": x_source_agent,
        "session_id": response_data.get("session_id"),
        "execution_id": execution_id
    }
)
```

### Activity Tracking

Tasks are tracked in the `agent_activities` table via `activity_service.track_activity()`:
- Activity type: `CHAT_START` (reused for tasks)
- Details include: parallel_mode=True, model, timeout_seconds, execution_id

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | Agent not found |
| Agent not running | 503 | Agent is not running |
| Task timeout | 504 | Task execution timed out after N seconds |
| HTTP error to agent | 503 | Failed to execute task. The agent may be unavailable. |
| Access denied | 403 | Access denied |

---

## UI States

### Queue Status Indicator

**Idle State** (green):
```
[Green dot] Idle
```

**Busy State** (yellow pulsing):
```
[Yellow pulsing dot] Busy | 2 queued
```

### Task Status Badges

| Status | Badge Color | Indicator |
|--------|-------------|-----------|
| running | Yellow | Pulsing dot |
| success | Green | Solid dot |
| failed | Red | Solid dot |
| queued | Gray | Solid dot |

### Trigger Badges

| Trigger | Color |
|---------|-------|
| manual | Blue |
| schedule | Purple |
| paid | Yellow |
| public | Teal |
| agent | Gray |

---

## Security Considerations

1. **Authorization**: All endpoints require authentication via `get_current_user`
2. **Agent Access**: `db.can_user_access_agent()` check before any operation
3. **No Credential Exposure**: Task messages may contain sensitive data but are stored in database (not logged)
4. **Queue Protection**: Queue clear/release endpoints require agent access permissions

---

## Related Flows

- **Upstream**: [parallel-headless-execution.md](parallel-headless-execution.md) - Core `/task` endpoint implementation. **2026-02-20**: Now supports `save_to_session` parameter for Chat tab persistence
- **Upstream**: [execution-queue.md](execution-queue.md) - Queue system (bypassed by tasks)
- **Related**: [scheduling.md](scheduling.md) - Scheduled executions share the same database table (now use `/api/task` for log format); **Make Repeatable** feature creates schedules from task messages (2026-02-20: schedules now support per-schedule timeout and allowed_tools)
- **Related**: [execution-log-viewer.md](execution-log-viewer.md) - Log viewer that renders execution transcripts
- **Related**: [execution-termination.md](execution-termination.md) - Stop button, process registry, graceful termination
- **Related**: [authenticated-chat-tab.md](authenticated-chat-tab.md) - Chat tab uses same `/task` endpoint for Dashboard tracking. **2026-02-20**: Session persistence via `save_to_session=true` parameter
- **Related**: [persistent-chat-tracking.md](persistent-chat-tracking.md) - Chat session tables (`chat_sessions`, `chat_messages`) used by Chat tab via `/task` endpoint
- **Related**: [model-selection.md](model-selection.md) - Model selector in task input, `model_used` field in execution records (MODEL-001)
- **Downstream**: [activity-monitoring.md](activity-monitoring.md) - Activity tracking for tasks

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-03-04 | **Paid/Public trigger types**: Added `paid` (yellow) and `public` (teal) to Trigger Badges table and filter dropdown. |
| 2026-03-02 | **MODEL-001 Model Selection**: Added `ModelSelector.vue` component above task textarea (line 86). Model persisted per-agent in localStorage. Model sent in POST /task payload. `model_used` displayed in task history rows (line 205). New `model_used TEXT` column in `schedule_executions` table. |
| 2026-02-21 | **PERF-001 Performance Optimization**: List endpoint now returns `ExecutionSummary` (excludes `response`, `error`, `tool_calls`, `execution_log`). Frontend loads details on-demand when user expands task row via `GET /api/agents/{name}/executions/{id}`. Added `taskDetailsCache` and `fetchTaskDetails()` function. New composite index `idx_executions_agent_started`. Data transfer reduced 50-100x. |
| 2026-02-20 | **Make Repeatable enhancement**: Updated test step and Related Flows to note that schedules created via "Make Repeatable" now support per-schedule timeout and allowed_tools configuration. |
| 2026-02-18 | **UI Redesign (UI-001)**: Reordered sections - Stats (49-69) now first, then Task Input (71-101), then Task History (103-315). Stats section more compact with smaller padding. Run button height now matches textarea. Updated line numbers throughout. |
| 2026-01-12 | **Execution Termination**: Added Stop button (lines 255-271) for running tasks, `terminateTask()` function, `loadRunningExecutions()`, execution_id matching via `enhanceWithExecutionId()`. See [execution-termination.md](execution-termination.md). |
| 2026-01-12 | Added "Make Repeatable" feature - calendar icon button to create schedule from task, emits `create-schedule` event to parent |
| 2025-01-02 | Added note about log format standardization - all execution types now use `/api/task` for raw Claude Code format |
| 2025-12-31 | Initial documentation - execution log viewer added |

---

## Testing

### Prerequisites
- Trinity platform running (`./scripts/deploy/start.sh`)
- At least one agent created and running

### Test Steps

1. **Navigate to Tasks Tab**
   - Go to Agent Detail page for any agent
   - Click "Tasks" tab
   - **Expected**: Tasks panel loads with empty state or existing executions

2. **Submit New Task (Agent Running)**
   - Enter task message: "What is 2+2?"
   - Click "Run" button
   - **Expected**:
     - Task appears immediately with "running" status (local optimistic update)
     - After completion, status changes to "success"
     - Response can be expanded by clicking task row

3. **Submit Task (Agent Stopped)**
   - Stop the agent
   - Attempt to submit task
   - **Expected**:
     - Run button is disabled
     - Warning message: "Agent must be running to execute tasks"

4. **Re-run Historical Task**
   - Click re-run icon on any completed task
   - **Expected**: Task message populates input and submits automatically

5. **Make Repeatable (Create Schedule from Task)**
   - Find a completed task in the history
   - Click the calendar icon ("Create schedule from this task")
   - **Expected**:
     - UI switches to Schedules tab automatically
     - Create schedule form opens with message field pre-filled with task message
     - User can add schedule name, cron expression, timeout, allowed tools, and click Create

6. **Queue Status (with /chat endpoint)**
   - Open terminal tab and start a long-running task
   - Switch to Tasks tab
   - **Expected**: Queue status shows "Busy" indicator

7. **Force Release Queue**
   - When queue shows "Busy"
   - Click "Force Release Queue"
   - **Expected**: Queue indicator returns to "Idle"

### Edge Cases
- Submit empty task (should be disabled)
- Submit very long task message (should work, message truncated in display)
- Multiple rapid task submissions (all should complete independently)

### Status
Verified 2025-12-31 - Execution log storage and retrieval endpoint added
