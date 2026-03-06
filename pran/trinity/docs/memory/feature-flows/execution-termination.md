# Feature: Execution Termination

## Overview

Execution Termination allows users to stop running Claude Code executions mid-flight by sending graceful signals (SIGINT) to the subprocess, with fallback to force kill (SIGKILL) if needed. This feature enables users to cancel long-running or stuck tasks without waiting for them to complete.

## User Story

As an agent operator, I want to stop a running task execution so that I can cancel stuck or unnecessary operations and reclaim agent resources.

## Entry Points

- **UI (Stop)**: `src/frontend/src/components/TasksPanel.vue:243-258` - Stop button for running tasks
- **UI (Live)**: `src/frontend/src/components/TasksPanel.vue:213-232` - Live button navigates to Execution Detail page (see [execution-detail-page.md](execution-detail-page.md))
- **API (Backend)**: `POST /api/agents/{name}/executions/{execution_id}/terminate?task_execution_id={id}`
- **API (Agent)**: `POST /api/executions/{execution_id}/terminate`
- **API (Agent)**: `GET /api/executions/running`

---

## Architecture

```
+---------------------------+      +---------------------------+      +----------------------------+
|       TasksPanel.vue      |      |     Backend chat.py       |      |   Agent agent_server/      |
|---------------------------|      |---------------------------|      |----------------------------|
| Stop Button (running task)|----->| POST /{name}/executions/  |----->| POST /api/executions/      |
|                           |      | {execution_id}/terminate  |      | {execution_id}/terminate   |
|---------------------------|      |---------------------------|      |----------------------------|
| terminateTask()           |      | Proxy to agent container  |      | ProcessRegistry.terminate()|
| loadRunningExecutions()   |      | Update DB: cancelled      |      | SIGINT -> wait 5s -> SIGKILL
+---------------------------+      | Track activity            |      +----------------------------+
                                   +---------------------------+
```

---

## Unified Execution ID Flow

The execution ID is now unified across the entire system. The backend generates the database `execution_id` and passes it to the agent container, which uses it for process registry. This ensures the same ID is used for:

1. **Database tracking**: `task_executions.id` column
2. **Process registry**: Key for subprocess lookup and termination
3. **API termination**: URL parameter matches both database and registry

### Flow Diagram

```
Backend (chat.py)                       Agent Container (claude_code.py)
+-------------------------------+       +----------------------------------+
| 1. Create task_execution      |       |                                  |
|    execution = db.create_     |       |                                  |
|      task_execution(...)      |       |                                  |
|    execution_id = execution.id|       |                                  |
|                               |       |                                  |
| 2. Pass to agent in payload   |------>| 3. Use execution_id for registry |
|    payload = {                |       |    task_session_id = execution_id|
|      "execution_id": exec_id  |       |      or str(uuid.uuid4())        |
|    }                          |       |                                  |
|                               |       | 4. Register subprocess           |
|                               |       |    registry.register(            |
|                               |       |      task_session_id, process)   |
+-------------------------------+       +----------------------------------+
```

---

## Agent Layer

### Process Registry (`docker/base-image/agent_server/services/process_registry.py`)

Thread-safe registry for tracking running subprocess handles.

**Class**: `ProcessRegistry` (lines 18-163)

| Method | Description |
|--------|-------------|
| `register(execution_id, process, metadata)` | Register a running subprocess with metadata |
| `unregister(execution_id)` | Remove a completed process from registry |
| `terminate(execution_id, graceful_timeout=5)` | Graceful SIGINT -> SIGKILL termination |
| `get_status(execution_id)` | Get status of a registered process |
| `list_running()` | List all currently running executions |
| `cleanup_finished()` | Remove entries for finished processes |

**Termination Flow** (lines 54-110):
```python
def terminate(self, execution_id: str, graceful_timeout: int = 5) -> dict:
    # 1. Check if process exists
    if not entry:
        return {"success": False, "reason": "not_found"}

    # 2. Check if already finished
    if process.poll() is not None:
        return {"success": False, "reason": "already_finished", "returncode": ...}

    # 3. Graceful termination (SIGINT = Ctrl+C)
    process.send_signal(signal.SIGINT)

    try:
        process.wait(timeout=graceful_timeout)  # Wait 5 seconds
    except subprocess.TimeoutExpired:
        # 4. Force kill if graceful didn't work
        process.kill()
        process.wait(timeout=2)

    return {"success": True, "returncode": process.returncode}
```

### Process Registration in Claude Code (`docker/base-image/agent_server/services/claude_code.py`)

**Conversational Chat** (lines 468-536):
```python
# Generate execution_id
execution_id = str(uuid.uuid4())

# Register process after Popen
registry = get_process_registry()
registry.register(execution_id, process, metadata={
    "type": "chat",
    "message_preview": prompt[:100]
})

try:
    # ... execute and parse response ...
    metadata.execution_id = execution_id  # Include in response metadata
finally:
    # Always unregister when done
    registry.unregister(execution_id)
```

**Headless Task** (lines 625-655):
```python
# Use provided execution_id if available (from backend database)
# This enables termination tracking with unified ID
task_session_id = execution_id or str(uuid.uuid4())

registry = get_process_registry()
registry.register(task_session_id, process, metadata={
    "type": "task",
    "message_preview": prompt[:100]
})

try:
    # ... execute and parse response ...
    metadata.execution_id = task_session_id  # Include in response metadata
finally:
    registry.unregister(task_session_id)
```

### Agent Server Endpoints (`docker/base-image/agent_server/routers/chat.py`)

**POST /api/task** (lines 94-135):
```python
@router.post("/api/task")
async def execute_task(request: ParallelTaskRequest):
    # Execute via runtime adapter in headless mode
    # Pass execution_id from request (provided by backend)
    runtime = get_runtime()
    response_text, raw_messages, metadata, session_id = await runtime.execute_headless(
        prompt=request.message,
        model=request.model,
        execution_id=request.execution_id  # Use provided ID for process registry
    )
```

**POST /api/executions/{execution_id}/terminate** (lines 242-261):
```python
@router.post("/api/executions/{execution_id}/terminate")
async def terminate_execution(execution_id: str):
    registry = get_process_registry()
    result = registry.terminate(execution_id)

    if result["success"]:
        return {"status": "terminated", "execution_id": execution_id}
    elif result["reason"] == "not_found":
        raise HTTPException(status_code=404, detail="Execution not found")
    elif result["reason"] == "already_finished":
        return {"status": "already_finished", "execution_id": execution_id, "returncode": ...}
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Termination failed"))
```

**GET /api/executions/running** (lines 264-272):
```python
@router.get("/api/executions/running")
async def list_running_executions():
    registry = get_process_registry()
    return {"executions": registry.list_running()}
```

---

## Backend Layer

### Proxy Endpoints (`src/backend/routers/chat.py`)

**Passing Execution ID to Agent** (lines 486-496):
```python
# Create execution record in database first
execution = db.create_task_execution(
    agent_name=name,
    message=request.message,
    triggered_by=triggered_by
)
execution_id = execution.id if execution else None

# Pass execution_id to agent in payload
payload = {
    "message": request.message,
    "execution_id": execution_id  # Database execution ID for process registry
}
```

**Status Preservation on Termination** (lines 567-616):

The backend error handlers check if an execution was already cancelled before overwriting the status. This prevents the "cancelled" status from being replaced with "failed" when the HTTP request naturally fails after termination.

```python
# Timeout handler (lines 567-578)
except httpx.TimeoutException:
    if execution_id:
        # Check if already cancelled - don't overwrite with timeout
        existing = db.get_execution(execution_id)
        if existing and existing.status == "cancelled":
            logger.info(f"Execution {execution_id} already cancelled, not overwriting with timeout status")
        else:
            db.update_execution_status(execution_id, status="failed", error="...")

# HTTP error handler (lines 591-616)
except httpx.HTTPError as e:
    if execution_id:
        # Check if execution was already cancelled (terminated by user)
        existing = db.get_execution(execution_id)
        if existing and existing.status == "cancelled":
            logger.info(f"Execution {execution_id} already cancelled, not overwriting with failed status")
        else:
            db.update_execution_status(execution_id, status="failed", error=error_msg)
```

**POST /api/agents/{name}/executions/{execution_id}/terminate** (lines 1073-1158):
```python
@router.post("/{name}/executions/{execution_id}/terminate")
async def terminate_agent_execution(
    name: str,
    execution_id: str,
    task_execution_id: Optional[str] = None,  # Query param for database update
    current_user: User = Depends(get_current_user)
):
    # 1. Validate agent exists and is running
    container = get_agent_container(name)
    if not container or container.status != "running":
        raise HTTPException(...)

    # 2. Proxy termination request to agent container
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"http://agent-{name}:8000/api/executions/{execution_id}/terminate"
        )

    # 3. Clear queue state if termination succeeded
    if result.get("status") in ["terminated", "already_finished"]:
        queue = get_execution_queue()
        await queue.force_release(name)

        # 4. Update database execution record to "cancelled"
        if task_execution_id:
            db.update_execution_status(
                execution_id=task_execution_id,
                status="cancelled",
                error="Execution terminated by user"
            )

    # 5. Track activity
    await activity_service.track_activity(
        agent_name=name,
        activity_type=ActivityType.EXECUTION_CANCELLED,
        details={"execution_id": execution_id, "status": result.get("status")}
    )

    return result
```

---

## Frontend Layer

### TasksPanel.vue (`src/frontend/src/components/TasksPanel.vue`)

**Stop Button UI** (lines 242-258):
```vue
<!-- Stop Button (for running tasks) -->
<button
  v-if="task.status === 'running' && task.execution_id"
  @click="terminateTask(task)"
  :disabled="terminatingTaskId === task.id"
  class="p-1.5 text-gray-400 hover:text-red-600 ..."
  title="Stop execution"
>
  <!-- Spinner when terminating, stop icon otherwise -->
</button>
```

**Cancelled Status Badge** (lines 138-158):
```vue
<!-- Status badge with cancelled (orange) styling -->
<span
  :class="[
    'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
    task.status === 'success' ? 'bg-green-100 ... text-green-800 ...' :
    task.status === 'failed' ? 'bg-red-100 ... text-red-800 ...' :
    task.status === 'cancelled' ? 'bg-orange-100 ... text-orange-800 ...' :
    task.status === 'running' ? 'bg-yellow-100 ... text-yellow-800 ...' :
    'bg-gray-100 ...'
  ]"
>
```

**State** (lines 485, 494):
```javascript
const terminatingTaskId = ref(null)        // ID of task being terminated
const runningExecutions = ref([])           // Running executions from agent
```

**Load Running Executions with Improved Polling** (lines 598-623):
```javascript
async function loadQueueStatus() {
  // ... load queue status ...

  // Fetch running executions for termination support if:
  // 1. Queue is busy (scheduled/queued tasks), OR
  // 2. We have local running tasks (manual tasks via /task endpoint bypass queue)
  const hasLocalRunningTasks = pendingTasks.value.some(t => t.status === 'running')
  if (response.data.is_busy || hasLocalRunningTasks) {
    await loadRunningExecutions()
  } else {
    runningExecutions.value = []
  }
}
```

**Execution ID Matching** (lines 513-533):
```javascript
// Enhance running tasks with execution_id from runningExecutions
const enhanceWithExecutionId = (task) => {
  if (task.status !== 'running' || task.execution_id) {
    return task
  }
  // Match by message preview (first 100 chars)
  const messagePreview = task.message.substring(0, 100)
  const match = runningExecutions.value.find(e =>
    e.metadata?.message_preview === messagePreview
  )
  if (match) {
    return { ...task, execution_id: match.execution_id }
  }
  // If only one running execution, assume it's this task
  if (runningExecutions.value.length === 1) {
    return { ...task, execution_id: runningExecutions.value[0].execution_id }
  }
  return task
}
```

**Terminate Task with Unified ID** (lines 754-789):
```javascript
async function terminateTask(task) {
  if (!task.execution_id) {
    console.error('No execution_id available for termination')
    return
  }

  terminatingTaskId.value = task.id

  try {
    // Pass task_execution_id as query param so backend can update database record
    // With unified ID, execution_id and task_execution_id are the same
    await axios.post(
      `/api/agents/${props.agentName}/executions/${task.execution_id}/terminate?task_execution_id=${task.execution_id}`,
      {},
      { headers: authStore.authHeader }
    )

    // Update task status locally to 'cancelled' while we wait for refresh
    const idx = pendingTasks.value.findIndex(t => t.id === task.id)
    if (idx !== -1) {
      pendingTasks.value[idx].status = 'cancelled'
      pendingTasks.value[idx].error = 'Execution terminated by user'
    }

    // Refresh data to get updated status
    await loadAllData()
  } catch (error) {
    console.error('Failed to terminate task:', error)
  } finally {
    terminatingTaskId.value = null
  }
}
```

---

## Data Models

### ParallelTaskRequest (`docker/base-image/agent_server/models.py:215-223`)
```python
class ParallelTaskRequest(BaseModel):
    message: str
    model: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    system_prompt: Optional[str] = None
    timeout_seconds: Optional[int] = 900
    max_turns: Optional[int] = None
    execution_id: Optional[str] = None  # Database execution ID (used for process registry if provided)
```

### ExecutionMetadata (`docker/base-image/agent_server/models.py:75-89`)
```python
class ExecutionMetadata(BaseModel):
    # ... other fields ...
    execution_id: Optional[str] = None  # Unique ID for process registry (termination)
```

### ActivityType (`src/backend/models.py:135`)
```python
class ActivityType(str, Enum):
    # ... other types ...
    EXECUTION_CANCELLED = "execution_cancelled"
```

---

## Side Effects

### Activity Tracking

When a task is terminated, an activity record is created:
```python
await activity_service.track_activity(
    agent_name=name,
    activity_type=ActivityType.EXECUTION_CANCELLED,
    user_id=current_user.id,
    triggered_by="user",
    related_execution_id=task_execution_id,
    details={
        "execution_id": execution_id,
        "task_execution_id": task_execution_id,
        "status": "terminated" | "already_finished",
        "returncode": int  # Process exit code
    }
)
```

### Queue State

The execution queue is force-released after successful termination to allow new executions:
```python
queue = get_execution_queue()
await queue.force_release(name)
```

### Database Status Preservation

When termination succeeds:
1. Backend updates `task_executions.status` to "cancelled"
2. Error handlers in `/task` endpoint check existing status before overwriting
3. If already "cancelled", the "failed" status is not written

---

## Signal Handling

| Signal | Purpose | Timeout |
|--------|---------|---------|
| `SIGINT` | Graceful termination (Ctrl+C) | 5 seconds |
| `SIGKILL` | Force kill (after SIGINT timeout) | 2 seconds |

Claude Code handles SIGINT gracefully, finishing its current operation before exiting. This allows tools like `Write` or `Bash` to complete their current action.

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | Agent not found |
| Agent not running | 503 | Agent is not running |
| Execution not found | 404 | Execution not found |
| Already finished | 200 | status: "already_finished" |
| Connection error | 502 | Failed to connect to agent |
| Timeout | 504 | Timeout connecting to agent |
| Termination error | 500 | Termination failed |

---

## Security Considerations

1. **Authentication**: All termination endpoints require valid JWT token via `get_current_user`
2. **Authorization**: Only users with agent access can terminate executions (implicit via agent container access)
3. **Queue Protection**: Queue is force-released after termination to prevent stuck state
4. **Audit Trail**: All terminations are tracked in activity log with user ID

---

## Related Flows

- **Upstream**: [execution-queue.md](execution-queue.md) - Queue management and execution tracking
- **Upstream**: [parallel-headless-execution.md](parallel-headless-execution.md) - Task execution that generates execution_id
- **Related**: [tasks-tab.md](tasks-tab.md) - UI component displaying stop button
- **Related**: [activity-stream.md](activity-stream.md) - Activity tracking for cancellations

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-13 | Added "Live" button entry point (lines 213-232) - green badge with pulsing dot for running tasks, navigates to Execution Detail page for real-time monitoring |
| 2026-01-13 | Updated: Unified execution ID flow (backend passes to agent), status preservation in error handlers, frontend polling improvements, cancelled status styling |
| 2026-01-12 | Initial documentation - Execution Termination feature |
