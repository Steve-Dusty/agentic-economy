# Plan: Execution Termination & Live Logging

> **Status**: Implemented
> **Created**: 2026-01-12
> **Implemented**: 2026-01-12
> **Priority**: High
> **Requirement**: Ability to terminate running executions and view live logs

## Problem Statement

When manually running an execution or when an automated execution is in progress, users need to:
1. **Terminate execution at any point** - Stop runaway agents or incorrect behavior
2. **See live logs during execution** - Monitor what the agent is doing in real-time
3. **Make informed decisions** - Stop execution if it's not performing correctly

## Current Architecture Gaps

### 1. Process Handle Not Stored

The subprocess created in `claude_code.py` is stored only in a local variable:
```python
process = subprocess.Popen(cmd, ...)
# process handle is lost after function returns
```

**File**: `docker/base-image/agent_server/services/claude_code.py`

### 2. No Connection Between Queue State and Process

`force_release()` in `execution_queue.py` only clears Redis state - it doesn't actually stop the running subprocess:
```python
async def force_release(self, agent_name: str) -> bool:
    # Only deletes Redis key - process keeps running!
    self.redis.delete(running_key)
```

**File**: `src/backend/services/execution_queue.py`

### 3. No Termination Endpoint

Neither the agent server nor backend has an endpoint to terminate running executions.

### 4. No Live Log Streaming

Logs are buffered and returned only after execution completes. The `--output-format stream-json` flag provides streaming output, but it's not forwarded to the frontend during execution.

## Implementation Approach

### Layer 1: Agent Container (docker/base-image/agent_server/)

#### 1.1 Process Registry

New file to store running process handles by execution_id:

```python
# New: services/process_registry.py
import subprocess
import signal
import logging
from typing import Dict, Optional
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)

class ProcessRegistry:
    """
    Registry for tracking running subprocess handles.
    Enables termination of executions by execution_id.
    """

    def __init__(self):
        self._processes: Dict[str, dict] = {}
        self._lock = Lock()

    def register(self, execution_id: str, process: subprocess.Popen, metadata: dict = None):
        """Register a running process."""
        with self._lock:
            self._processes[execution_id] = {
                "process": process,
                "started_at": datetime.utcnow(),
                "metadata": metadata or {}
            }
            logger.info(f"[ProcessRegistry] Registered execution {execution_id}")

    def unregister(self, execution_id: str):
        """Unregister a completed process."""
        with self._lock:
            if execution_id in self._processes:
                del self._processes[execution_id]
                logger.info(f"[ProcessRegistry] Unregistered execution {execution_id}")

    def terminate(self, execution_id: str, graceful_timeout: int = 5) -> dict:
        """
        Terminate a running process.

        Args:
            execution_id: The execution to terminate
            graceful_timeout: Seconds to wait after SIGINT before SIGKILL

        Returns:
            dict with termination status
        """
        with self._lock:
            entry = self._processes.get(execution_id)
            if not entry:
                return {"success": False, "reason": "not_found"}

            process = entry["process"]
            if process.poll() is not None:
                # Already finished
                del self._processes[execution_id]
                return {"success": False, "reason": "already_finished", "returncode": process.returncode}

        # Terminate outside lock to avoid blocking
        try:
            # Graceful termination first (SIGINT = Ctrl+C)
            logger.info(f"[ProcessRegistry] Sending SIGINT to execution {execution_id}")
            process.send_signal(signal.SIGINT)

            try:
                process.wait(timeout=graceful_timeout)
                logger.info(f"[ProcessRegistry] Execution {execution_id} terminated gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful didn't work
                logger.warning(f"[ProcessRegistry] Force killing execution {execution_id}")
                process.kill()
                process.wait(timeout=2)

            with self._lock:
                if execution_id in self._processes:
                    del self._processes[execution_id]

            return {"success": True, "returncode": process.returncode}

        except Exception as e:
            logger.error(f"[ProcessRegistry] Error terminating {execution_id}: {e}")
            return {"success": False, "reason": "error", "error": str(e)}

    def get_status(self, execution_id: str) -> Optional[dict]:
        """Get status of a registered process."""
        with self._lock:
            entry = self._processes.get(execution_id)
            if not entry:
                return None

            process = entry["process"]
            poll_result = process.poll()

            return {
                "execution_id": execution_id,
                "running": poll_result is None,
                "returncode": poll_result,
                "started_at": entry["started_at"].isoformat(),
                "metadata": entry["metadata"]
            }

    def list_running(self) -> list:
        """List all running executions."""
        with self._lock:
            result = []
            for exec_id, entry in self._processes.items():
                process = entry["process"]
                if process.poll() is None:
                    result.append({
                        "execution_id": exec_id,
                        "started_at": entry["started_at"].isoformat(),
                        "metadata": entry["metadata"]
                    })
            return result

    def cleanup_finished(self) -> int:
        """Remove entries for finished processes. Returns count cleaned."""
        with self._lock:
            finished = [
                exec_id for exec_id, entry in self._processes.items()
                if entry["process"].poll() is not None
            ]
            for exec_id in finished:
                del self._processes[exec_id]
            if finished:
                logger.info(f"[ProcessRegistry] Cleaned up {len(finished)} finished processes")
            return len(finished)


# Global instance
_process_registry: Optional[ProcessRegistry] = None

def get_process_registry() -> ProcessRegistry:
    """Get the global process registry instance."""
    global _process_registry
    if _process_registry is None:
        _process_registry = ProcessRegistry()
    return _process_registry
```

#### 1.2 Termination Endpoint

Add to agent server router:

```python
# In routers/chat.py

from services.process_registry import get_process_registry

@router.post("/api/executions/{execution_id}/terminate")
async def terminate_execution(execution_id: str):
    """Terminate a running execution by ID."""
    registry = get_process_registry()
    result = registry.terminate(execution_id)

    if result["success"]:
        return {"status": "terminated", "execution_id": execution_id}
    elif result["reason"] == "not_found":
        raise HTTPException(status_code=404, detail="Execution not found")
    elif result["reason"] == "already_finished":
        return {"status": "already_finished", "returncode": result["returncode"]}
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Termination failed"))

@router.get("/api/executions/running")
async def list_running_executions():
    """List all currently running executions."""
    registry = get_process_registry()
    return {"executions": registry.list_running()}

@router.get("/api/executions/{execution_id}/status")
async def get_execution_status(execution_id: str):
    """Get status of a specific execution."""
    registry = get_process_registry()
    status = registry.get_status(execution_id)
    if not status:
        raise HTTPException(status_code=404, detail="Execution not found")
    return status
```

#### 1.3 Modify Execution Functions

Update `execute_claude_code()` and `execute_headless_task()`:

```python
# In services/claude_code.py

from services.process_registry import get_process_registry

async def execute_claude_code(message: str, ...) -> dict:
    execution_id = str(uuid.uuid4())
    registry = get_process_registry()

    process = subprocess.Popen(cmd, ...)

    # Register process for potential termination
    registry.register(execution_id, process, metadata={
        "type": "chat",
        "message_preview": message[:100]
    })

    try:
        # ... existing execution logic ...
        return {
            "response": response,
            "execution_id": execution_id,  # Include in response
            # ... other fields
        }
    finally:
        registry.unregister(execution_id)
```

### Layer 2: Backend (src/backend/)

#### 2.1 Proxy Termination Endpoint

```python
# In routers/chat.py

@router.post("/api/agents/{name}/executions/{execution_id}/terminate")
async def terminate_agent_execution(
    name: str,
    execution_id: str,
    current_user: User = Depends(get_current_user)
):
    """Terminate a running execution on an agent."""
    # Verify agent exists and user has access
    agent = await get_agent_or_404(name)
    await verify_agent_access(agent, current_user)

    # Proxy to agent container
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"http://agent-{name}:8000/api/executions/{execution_id}/terminate",
                timeout=10.0
            )
            result = response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach agent: {e}")

    # Clear queue state if termination succeeded
    if result.get("status") == "terminated":
        queue = get_execution_queue()
        await queue.force_release(name)

        # Log activity
        await track_activity(
            agent_name=name,
            activity_type=ActivityType.EXECUTION_TERMINATED,
            user_id=current_user.id,
            metadata={"execution_id": execution_id}
        )

    return result
```

#### 2.2 Update Execution Model

```python
# In models.py

class ExecutionResponse(BaseModel):
    response: str
    execution_id: str  # Add this field
    # ... existing fields
```

### Layer 3: Frontend (src/frontend/)

#### 3.1 Stop Button in TasksPanel

```vue
<!-- In TasksPanel.vue -->
<template>
  <div v-if="currentExecution" class="execution-status">
    <div class="flex items-center gap-2">
      <span class="animate-pulse">Running...</span>
      <button
        @click="terminateExecution"
        class="btn btn-danger btn-sm"
        :disabled="terminating"
      >
        {{ terminating ? 'Stopping...' : 'Stop Execution' }}
      </button>
    </div>

    <!-- Live log viewer -->
    <div v-if="showLogs" class="log-viewer">
      <pre>{{ liveLog }}</pre>
    </div>
  </div>
</template>

<script setup>
const terminating = ref(false)

async function terminateExecution() {
  if (!currentExecution.value?.execution_id) return

  terminating.value = true
  try {
    await api.post(
      `/agents/${agentName}/executions/${currentExecution.value.execution_id}/terminate`
    )
    // Refresh status
    await refreshQueueStatus()
  } catch (error) {
    console.error('Failed to terminate:', error)
  } finally {
    terminating.value = false
  }
}
</script>
```

#### 3.2 Live Log Streaming (WebSocket)

```javascript
// New: composables/useExecutionLogs.js

export function useExecutionLogs(agentName) {
  const logs = ref([])
  const connected = ref(false)
  let ws = null

  function connect(executionId) {
    const wsUrl = `ws://${window.location.host}/api/agents/${agentName}/executions/${executionId}/logs`
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      const logEntry = JSON.parse(event.data)
      logs.value.push(logEntry)
    }

    ws.onclose = () => {
      connected.value = false
    }
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  return { logs, connected, connect, disconnect }
}
```

### Signal Handling

Claude Code responds to these signals:

| Signal | Behavior |
|--------|----------|
| **SIGINT** (Ctrl+C) | Graceful cancellation, finishes current tool |
| **SIGTERM** | Terminate signal, slightly less graceful |
| **SIGKILL** | Force kill (last resort, no cleanup) |

Recommended termination sequence:
1. Send SIGINT (graceful)
2. Wait 5 seconds
3. If still running, send SIGKILL (force)

### Files to Modify

| Layer | File | Changes |
|-------|------|---------|
| Agent | `services/process_registry.py` | **New file** - process tracking |
| Agent | `services/claude_code.py` | Register/unregister processes |
| Agent | `services/gemini_runtime.py` | Same for Gemini CLI |
| Agent | `routers/chat.py` | Add termination endpoint |
| Agent | `models.py` | Add execution_id to responses |
| Backend | `routers/chat.py` | Proxy termination to agent |
| Backend | `models.py` | Add execution_id field |
| Backend | `services/execution_queue.py` | Link execution_id to queue |
| Frontend | `TasksPanel.vue` | Add stop button |
| Frontend | `useExecutionLogs.js` | **New file** - WebSocket for logs |

### Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Orphaned processes | Medium | Registry cleanup on container restart |
| Race conditions | Low | Mutex lock in process registry |
| Partial results | Low | Return whatever was captured before termination |
| Queue state inconsistency | Medium | Always clear queue after termination |
| WebSocket connection issues | Low | Fallback to polling |

### Implementation Phases

#### Phase 1: Process Registry (Agent Container)
- Create `process_registry.py`
- Modify `claude_code.py` to register/unregister processes
- Modify `gemini_runtime.py` similarly
- Add termination endpoint to agent router
- **Estimated effort**: Core infrastructure

#### Phase 2: Backend Integration
- Add proxy termination endpoint
- Update execution queue to track execution_id
- Add activity tracking for terminations
- **Estimated effort**: API layer

#### Phase 3: Frontend Stop Button
- Add stop button to TasksPanel
- Show execution_id in UI
- Handle termination feedback
- **Estimated effort**: UI updates

#### Phase 4: Live Log Streaming
- Add WebSocket endpoint for log streaming
- Modify execution functions to stream logs
- Add log viewer component to frontend
- **Estimated effort**: Real-time streaming

### Testing Plan

1. **Unit Tests**
   - Process registry register/unregister/terminate
   - Graceful vs force termination
   - Concurrent execution handling

2. **Integration Tests**
   - End-to-end termination flow
   - Queue state consistency after termination
   - WebSocket connection lifecycle

3. **Manual Tests**
   - Terminate long-running execution
   - Terminate execution during tool use
   - Verify no orphaned processes

### Future Enhancements

1. **Termination reasons** - Track why execution was terminated (user, timeout, error)
2. **Partial result recovery** - Save and return work completed before termination
3. **Bulk termination** - Terminate all executions for an agent
4. **Auto-termination rules** - Terminate based on resource usage or time limits
