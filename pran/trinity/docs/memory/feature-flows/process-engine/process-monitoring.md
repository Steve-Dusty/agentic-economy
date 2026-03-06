# Feature: Process Monitoring

> Real-time monitoring of process executions via WebSocket events with live step progress updates, execution timeline visualization, and breadcrumb navigation for sub-processes

---

## Overview

Process Monitoring provides real-time visibility into process executions through the UI. Users can watch executions progress step-by-step, view step outputs, track costs, and navigate between parent/child sub-processes.

**Key Capabilities:**
- Real-time updates via WebSocket connection (10 event types)
- Step-by-step execution timeline with progress bar
- Output viewer for each step (loaded on demand)
- Breadcrumb navigation for nested sub-processes
- Approval UI inline for steps waiting approval
- Polling fallback when WebSocket disconnects

---

## Entry Points

- **UI**: `ProcessExecutionDetail.vue` - Main execution monitoring page
- **UI**: Click execution in list -> Navigate to `/executions/{id}`
- **API**: `GET /api/executions/{id}` - Get execution detail
- **API**: `GET /api/executions/{id}/events` - Get event history
- **API**: `GET /api/executions/{id}/steps/{step_id}/output` - Get step output
- **WebSocket**: `/ws?token={jwt}` - Real-time event stream

---

## Architecture

```
                               Frontend
+------------------------------------------------------------------+
|                                                                  |
|  ProcessExecutionDetail.vue                                      |
|  +------------------------------------------------------------+  |
|  | Breadcrumbs (lines 9-24)  - Parent chain navigation        |  |
|  | Header (lines 39-157)     - Status, actions, indicators    |  |
|  | Info Cards (lines 159-189) - Stats: trigger, times, cost   |  |
|  | Tabs (lines 191-239)       - Timeline, Input, Output, Events|
|  | ExecutionTimeline.vue     - Step progress visualization    |  |
|  +------------------------------------------------------------+  |
|                         |                                        |
|  useProcessWebSocket.js | (composable)                           |
|  +--------------------+ |                                        |
|  | connect()         | |                                         |
|  | handleMessage()   | |                                         |
|  | reconnect logic   | |                                         |
|  +--------------------+ |                                        |
+-------------------------|----------------------------------------+
                          | WebSocket /ws?token=...
                          v
+------------------------------------------------------------------+
|                              Backend                              |
|                                                                  |
|  main.py - WebSocket Endpoint (lines 309-356)                    |
|  +------------------------------------------------------------+  |
|  | ConnectionManager (lines 84-104)                           |  |
|  |   connect(websocket) - Accept and add to list              |  |
|  |   disconnect(websocket) - Remove from list                 |  |
|  |   broadcast(message) - Send to all connections             |  |
|  +------------------------------------------------------------+  |
|                          ^                                       |
|                          | manager.broadcast() called by         |
|                          |                                       |
|  websocket_publisher.py (lines 32-225)                           |
|  +------------------------------------------------------------+  |
|  | WebSocketEventPublisher                                    |  |
|  |   register_with_event_bus() - Subscribe to 10 event types  |  |
|  |   handle_event() - Convert domain event to JSON            |  |
|  |   _event_to_message() - Build WebSocket payload            |  |
|  +------------------------------------------------------------+  |
|                          ^                                       |
|                          | EventBus.publish() triggers           |
|                          |                                       |
|  bus.py - InMemoryEventBus (lines 98-243)                        |
|  +------------------------------------------------------------+  |
|  | subscribe(event_type, handler)                             |  |
|  | publish(event) - Notify all handlers asynchronously        |  |
|  | _safe_dispatch() - Error handling per handler              |  |
|  +------------------------------------------------------------+  |
|                          ^                                       |
|                          | Events emitted by                     |
|                          |                                       |
|  ExecutionEngine                                                 |
|  +------------------------------------------------------------+  |
|  | Publishes domain events during execution                   |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

---

## Frontend Layer

### ProcessExecutionDetail.vue

**Location**: `src/frontend/src/views/ProcessExecutionDetail.vue`

| Section | Lines | Description |
|---------|-------|-------------|
| Breadcrumb Navigation | 9-24 | Shows parent chain for sub-processes |
| Loading State | 27-35 | Spinner while fetching |
| Header | 39-157 | Status badge, execution ID, retry/parent badges |
| WebSocket Indicator | 113-125 | Green "Live" or gray "Polling" badge |
| Cancel Button | 128-135 | Cancel running/pending executions |
| Retry Button | 138-145 | Retry failed executions |
| Info Cards | 159-189 | Triggered by, started, completed, duration, cost |
| Tabs | 191-239 | Timeline, Input Data, Output Data, Event History |
| ExecutionTimeline | 244-249 | Delegated component for step visualization |

**Key State Variables** (lines 391-398):

```javascript
const loading = ref(false)
const execution = ref(null)
const activeTab = ref('timeline')
const actionInProgress = ref(false)
const executionId = computed(() => route.params.id)
const events = ref([])
const breadcrumbs = ref([])  // For nested sub-process navigation
```

**Display Status Enhancement** (lines 401-418):

```javascript
// Check if paused due to waiting_approval
const hasWaitingApproval = computed(() => {
  return execution.value?.steps?.some(s => s.status === 'waiting_approval') || false
})

// Display status (enhanced for approval visibility)
const displayStatus = computed(() => {
  if (execution.value?.status === 'paused' && hasWaitingApproval.value) {
    return 'awaiting_approval'
  }
  return execution.value?.status || 'unknown'
})
```

### ExecutionTimeline.vue

**Location**: `src/frontend/src/components/ExecutionTimeline.vue`

| Section | Lines | Description |
|---------|-------|-------------|
| Approval Alert Banner | 3-26 | Prominent alert for steps needing approval |
| Progress Header | 28-34 | "X/Y completed" counter |
| Progress Bar | 37-45 | Visual progress with color coding |
| Step List | 48-449 | Sorted steps with expandable details |
| Step Header | 60-142 | Status icon, name, badges, duration |
| Step Detail Panel | 145-447 | Timing, error display, approval UI, output |
| Approval UI | 264-328 | Approve/Reject buttons with dialog |
| Gateway Display | 373-416 | Route taken, conditions evaluated |
| Sub-process Display | 331-370 | Child execution link |

**Status Helper Functions** (lines 636-671):

```javascript
function getStepIcon(status) {
  const icons = {
    pending: '○',
    running: '◐',
    completed: '✓',
    failed: '✗',
    skipped: '–',
    waiting_approval: '⏳',
  }
  return icons[status] || '?'
}

function getStatusBadgeClasses(status) {
  const classes = {
    pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
    running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
    skipped: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
    waiting_approval: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  }
  return classes[status] || 'bg-gray-100 text-gray-600'
}
```

### useProcessWebSocket.js (Composable)

**Location**: `src/frontend/src/composables/useProcessWebSocket.js`

**Purpose**: Provides real-time updates for process executions via WebSocket.

| Method | Lines | Description |
|--------|-------|-------------|
| connect() | 43-96 | Establish WebSocket, handle auth |
| disconnect() | 98-104 | Clean close connection |
| handleMessage() | 106-146 | Route events to callbacks |

**Event Callbacks** (lines 21-32):

```javascript
const {
  executionId = ref(null),
  onStepStarted = () => {},
  onStepCompleted = () => {},
  onStepFailed = () => {},
  onProcessCompleted = () => {},
  onProcessFailed = () => {},
  onCompensationStarted = () => {},
  onCompensationCompleted = () => {},
  onCompensationFailed = () => {},
} = options
```

**Message Routing** (lines 106-146):

```javascript
function handleMessage(message) {
  // Only process events for process_event type
  if (message.type !== 'process_event') {
    return
  }

  // Filter by execution ID if set
  if (executionId.value && message.execution_id !== executionId.value) {
    return
  }

  lastEvent.value = message

  // Route to appropriate callback
  switch (message.event_type) {
    case 'step_started':
      onStepStarted(message)
      break
    case 'step_completed':
      onStepCompleted(message)
      break
    case 'step_failed':
      onStepFailed(message)
      break
    case 'process_completed':
      onProcessCompleted(message)
      break
    case 'process_failed':
      onProcessFailed(message)
      break
    case 'compensation_started':
      onCompensationStarted(message)
      break
    case 'compensation_completed':
      onCompensationCompleted(message)
      break
    case 'compensation_failed':
      onCompensationFailed(message)
      break
  }
}
```

### executions.js (Store)

**Location**: `src/frontend/src/stores/executions.js`

| Method | Lines | Description |
|--------|-------|-------------|
| fetchExecutions() | 70-100 | List executions with filters |
| getExecution(id) | 102-113 | Get single execution detail |
| cancelExecution(id) | 115-122 | Cancel running execution |
| retryExecution(id) | 124-131 | Create retry execution |
| getStepOutput(execId, stepId) | 133-143 | Fetch step output on demand |
| getExecutionEvents(id) | 145-155 | Fetch event history |

---

## Backend Layer

### WebSocket Endpoint

**Location**: `src/backend/main.py`

**ConnectionManager** (lines 84-104):

```python
class ConnectionManager:
    """WebSocket connection manager for broadcasting events."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()
```

**WebSocket Endpoint** (lines 309-356):

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    WebSocket endpoint for real-time updates.
    Accepts authentication via query parameter: /ws?token=<jwt_token>
    """
    # Validate token if provided
    authenticated = False
    username = None

    if token:
        try:
            payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username:
                authenticated = True
        except JWTError:
            pass

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Could authenticate via first message if not done via query param
            if not authenticated and data.startswith("Bearer "):
                # ... handle late auth
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**Publisher Injection** (line 124):

```python
# Set up process engine WebSocket publisher
set_websocket_publisher_broadcast(manager.broadcast)
```

### WebSocketEventPublisher

**Location**: `src/backend/services/process_engine/events/websocket_publisher.py`

**Class Definition** (lines 32-52):

```python
class WebSocketEventPublisher:
    """
    Publishes domain events to WebSocket clients.
    """

    # Event types that should be broadcast
    BROADCAST_EVENTS = {
        ProcessStarted,
        ProcessCompleted,
        ProcessFailed,
        StepStarted,
        StepCompleted,
        StepFailed,
        ApprovalRequested,
        CompensationStarted,
        CompensationCompleted,
        CompensationFailed,
    }
```

**Event Registration** (lines 90-94):

```python
def register_with_event_bus(self, event_bus: EventBus) -> None:
    """Register this publisher as a handler on the event bus."""
    for event_type in self.BROADCAST_EVENTS:
        event_bus.subscribe(event_type, self.handle_event)
    logger.info(f"WebSocket publisher registered for {len(self.BROADCAST_EVENTS)} event types")
```

**Event Handler** (lines 96-106):

```python
async def handle_event(self, event: DomainEvent) -> None:
    """Handle a domain event by broadcasting it to WebSocket clients."""
    if not self._broadcast_fn:
        logger.warning("No broadcast function set, skipping WebSocket publish")
        return

    # Convert event to WebSocket message
    message = self._event_to_message(event)
    if message:
        await self._broadcast_fn(json.dumps(message))
        logger.debug(f"Broadcast {event.__class__.__name__} for execution {getattr(event, 'execution_id', 'N/A')}")
```

**Message Conversion** (lines 108-190):

```python
def _event_to_message(self, event: DomainEvent) -> Optional[dict[str, Any]]:
    """Convert a domain event to a WebSocket message."""
    event_type = self._get_event_type(event)
    if not event_type:
        return None

    # Build base message
    message = {
        "type": "process_event",
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Add event-specific data
    if isinstance(event, ProcessStarted):
        message.update({
            "execution_id": str(event.execution_id),
            "process_id": str(event.process_id),
            "process_name": event.process_name,
            "triggered_by": event.triggered_by,
        })
    elif isinstance(event, StepStarted):
        message.update({
            "execution_id": str(event.execution_id),
            "step_id": str(event.step_id),
        })
    # ... similar for other event types

    return message
```

### InMemoryEventBus

**Location**: `src/backend/services/process_engine/events/bus.py`

**Publish Method** (lines 122-152):

```python
async def publish(self, event: DomainEvent) -> None:
    """
    Publish event to all relevant handlers.

    Handlers are invoked asynchronously via asyncio.create_task().
    Errors in handlers are logged but don't propagate.
    """
    event_type = type(event)

    # Collect all handlers for this event
    handlers: list[EventHandler] = []

    # Type-specific handlers
    handlers.extend(self._handlers.get(event_type, []))

    # Global handlers
    handlers.extend(self._global_handlers)

    if not handlers:
        logger.debug(f"No handlers for event {event_type.__name__}")
        return

    # Dispatch to all handlers concurrently
    for handler in handlers:
        task = asyncio.create_task(self._safe_dispatch(handler, event))
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
```

### Execution API Endpoints

**Location**: `src/backend/routers/executions.py`

| Method | Path | Lines | Description |
|--------|------|-------|-------------|
| GET | `/api/executions` | 417-467 | List with filters |
| GET | `/api/executions/{id}` | 470-505 | Get detail |
| POST | `/api/executions/{id}/cancel` | 508-551 | Cancel execution |
| POST | `/api/executions/{id}/retry` | 554-614 | Create retry |
| GET | `/api/executions/{id}/events` | 617-635 | Get event history |
| GET | `/api/executions/{id}/steps/{step_id}/output` | 638-665 | Get step output |

**Get Execution Detail** (lines 470-505):

```python
@router.get("/{execution_id}", response_model=ExecutionDetail)
async def get_execution(
    execution_id: str,
    current_user: CurrentUser,
):
    """Get detailed information about a specific execution."""
    execution_repo = get_execution_repo()
    definition_repo = get_definition_repo()

    try:
        eid = ExecutionId(execution_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid execution ID format")

    execution = execution_repo.get_by_id(eid)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_view_execution(current_user, execution)
    if not auth_result:
        raise HTTPException(status_code=403, detail=auth_result.reason)

    # Get definition for parallel structure info
    definition = definition_repo.get_by_id(execution.process_id)

    return _to_detail(execution, definition)
```

---

## Domain Events

**Location**: `src/backend/services/process_engine/domain/events.py`

### Event Types Broadcast to UI

| Event Class | Lines | WebSocket `event_type` | Payload Fields |
|-------------|-------|------------------------|----------------|
| ProcessStarted | 61-78 | `process_started` | execution_id, process_id, process_name, triggered_by |
| ProcessCompleted | 81-102 | `process_completed` | execution_id, process_id, process_name, duration_seconds |
| ProcessFailed | 105-128 | `process_failed` | execution_id, process_id, process_name, error, failed_step_id |
| StepStarted | 158-175 | `step_started` | execution_id, step_id |
| StepCompleted | 178-199 | `step_completed` | execution_id, step_id, duration_seconds |
| StepFailed | 202-227 | `step_failed` | execution_id, step_id, error |
| ApprovalRequested | 305-326 | `approval_requested` | execution_id, step_id, approvers |
| CompensationStarted | 358-375 | `compensation_started` | execution_id, process_id, process_name, compensation_count |
| CompensationCompleted | 378-395 | `compensation_completed` | execution_id, step_id, step_name, compensation_type |
| CompensationFailed | 398-417 | `compensation_failed` | execution_id, step_id, step_name, compensation_type, error |

### WebSocket Message Format

All messages follow this structure:

```json
{
  "type": "process_event",
  "event_type": "step_completed",
  "timestamp": "2026-01-23T10:30:45.123456",
  "execution_id": "abc123-uuid",
  "step_id": "research",
  "duration_seconds": 45
}
```

### Full Event Payloads

**process_started**:
```json
{
  "type": "process_event",
  "event_type": "process_started",
  "timestamp": "2026-01-23T10:30:00.000000",
  "execution_id": "exec-uuid",
  "process_id": "proc-uuid",
  "process_name": "content-pipeline",
  "triggered_by": "manual"
}
```

**step_completed**:
```json
{
  "type": "process_event",
  "event_type": "step_completed",
  "timestamp": "2026-01-23T10:30:45.000000",
  "execution_id": "exec-uuid",
  "step_id": "research",
  "duration_seconds": 45
}
```

**step_failed**:
```json
{
  "type": "process_event",
  "event_type": "step_failed",
  "timestamp": "2026-01-23T10:31:00.000000",
  "execution_id": "exec-uuid",
  "step_id": "write",
  "error": "Agent timeout: no response within 300s"
}
```

**process_failed**:
```json
{
  "type": "process_event",
  "event_type": "process_failed",
  "timestamp": "2026-01-23T10:31:05.000000",
  "execution_id": "exec-uuid",
  "process_id": "proc-uuid",
  "process_name": "content-pipeline",
  "error": "Step 'write' failed after 3 retries",
  "failed_step_id": "write"
}
```

**approval_requested**:
```json
{
  "type": "process_event",
  "event_type": "approval_requested",
  "timestamp": "2026-01-23T10:32:00.000000",
  "execution_id": "exec-uuid",
  "step_id": "human-review",
  "approvers": ["admin@example.com", "reviewer@example.com"]
}
```

**compensation_started**:
```json
{
  "type": "process_event",
  "event_type": "compensation_started",
  "timestamp": "2026-01-23T10:33:00.000000",
  "execution_id": "exec-uuid",
  "process_id": "proc-uuid",
  "process_name": "content-pipeline",
  "compensation_count": 2
}
```

---

## Breadcrumb Navigation

For sub-process executions, breadcrumbs show the parent chain.

### Building Breadcrumbs (ProcessExecutionDetail.vue lines 561-595)

```javascript
async function buildBreadcrumbs() {
  const crumbs = []
  let currentExec = execution.value

  // Start with current execution
  if (currentExec) {
    crumbs.unshift({
      id: currentExec.id,
      process_name: currentExec.process_name,
    })
  }

  // Traverse up the parent chain (max 10 levels to prevent infinite loops)
  let depth = 0
  while (currentExec?.parent_execution_id && depth < 10) {
    try {
      const parentExec = await executionsStore.getExecution(currentExec.parent_execution_id)
      if (parentExec) {
        crumbs.unshift({
          id: parentExec.id,
          process_name: parentExec.process_name,
        })
        currentExec = parentExec
      } else {
        break
      }
    } catch (e) {
      console.warn('Failed to load parent execution:', e)
      break
    }
    depth++
  }

  breadcrumbs.value = crumbs
}
```

### Breadcrumb Display (lines 9-24)

```vue
<nav v-if="breadcrumbs.length > 1" class="flex items-center space-x-2 text-sm mb-4">
  <HomeIcon class="w-4 h-4 text-gray-400" />
  <template v-for="(crumb, index) in breadcrumbs" :key="crumb.id">
    <ChevronRightIcon class="w-4 h-4 text-gray-400" />
    <router-link
      v-if="index < breadcrumbs.length - 1"
      :to="`/executions/${crumb.id}`"
      class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800"
    >
      {{ crumb.process_name }}
    </router-link>
    <span v-else class="text-gray-700 dark:text-gray-300 font-medium">
      {{ crumb.process_name }}
    </span>
  </template>
</nav>
```

**Visual:**
```
Home > parent-process > child-process > current-process (bold)
         clickable       clickable        current page
```

---

## Polling Fallback

When WebSocket disconnects, the UI falls back to polling.

### Auto-refresh Interval (ProcessExecutionDetail.vue lines 522-539)

```javascript
let refreshInterval = null

onMounted(() => {
  loadExecution()

  // Fallback auto-refresh for active executions (when WS not working)
  // Includes 'paused' because it may be waiting for approval
  refreshInterval = setInterval(() => {
    if (!wsConnected.value && execution.value &&
        (execution.value.status === 'running' ||
         execution.value.status === 'pending' ||
         execution.value.status === 'paused')) {
      loadExecution()
    }
  }, 5000)  // Poll every 5 seconds
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
```

### WebSocket Reconnection (useProcessWebSocket.js lines 74-86)

```javascript
ws.onclose = (event) => {
  isConnected.value = false
  console.log('[ProcessWS] Disconnected:', event.code, event.reason)

  // Attempt reconnection
  if (reconnectAttempts < maxReconnectAttempts) {
    reconnectAttempts++
    console.log(`[ProcessWS] Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`)
    setTimeout(connect, reconnectDelay)  // 3000ms
  } else {
    error.value = 'Connection lost. Please refresh the page.'
  }
}
```

---

## Status Display

### Execution Status (ProcessExecutionDetail.vue lines 688-726)

| Status | Icon | Background | Text Color |
|--------|------|------------|------------|
| `pending` | `⏳` | yellow-100 | yellow-800 |
| `running` | `🔄` | blue-100 | blue-800 |
| `completed` | `✅` | green-100 | green-800 |
| `failed` | `❌` | red-100 | red-800 |
| `cancelled` | `⛔` | gray-100 | gray-800 |
| `paused` | `⏸️` | purple-100 | purple-800 |
| `awaiting_approval` | `🔔` | amber-100 (animated pulse) | amber-800 |

### Status Explanation Tooltips (lines 715-726)

```javascript
function getStatusExplanation(status) {
  const explanations = {
    pending: 'Waiting to start. The execution is queued and will begin shortly.',
    running: 'Execution in progress. Steps are being processed by agents.',
    completed: 'All steps finished successfully. View step outputs below.',
    failed: 'Execution stopped due to an error. Check step details for more information.',
    cancelled: 'Execution was manually cancelled before completion.',
    paused: 'Awaiting human approval. Check the Approvals page to continue.',
    awaiting_approval: 'A step requires your approval before continuing. Go to Approvals to review.',
  }
  return explanations[status] || 'Unknown status'
}
```

---

## Error Handling

| Error Case | HTTP Status | Frontend Behavior |
|------------|-------------|-------------------|
| Invalid execution ID format | 400 | Show "Invalid execution ID" error |
| Execution not found | 404 | Show "Execution not found" with back link |
| Permission denied | 403 | Show forbidden message |
| WebSocket disconnect | - | Fall back to polling, show "Polling" indicator |
| Step output not found | 404 | Show "Output not available" |

---

## Security Considerations

1. **WebSocket Authentication**: Token passed as query parameter, validated via JWT
2. **Execution Access**: Users can only view executions they have permission for (via ProcessAuthorizationService)
3. **Step Output Access**: Same authorization as execution view

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- At least one published process
- WebSocket endpoint available at `/ws`

### Test Cases

1. **Real-time step updates**
   - Start a multi-step process execution
   - Watch the ExecutionTimeline component
   - **Expected**: Steps transition from pending -> running -> completed in real-time

2. **WebSocket connection indicator**
   - Open execution detail for a running process
   - **Expected**: Green "Live" badge appears next to status

3. **WebSocket reconnection**
   - Temporarily disable network
   - Re-enable network
   - **Expected**: Falls back to "Polling", reconnects automatically

4. **Breadcrumb navigation**
   - Execute a process that calls a sub-process
   - Navigate to sub-process execution
   - **Expected**: Breadcrumbs show parent -> child chain, links work

5. **Approval UI**
   - Execute process with human approval step
   - Wait for approval step
   - **Expected**: Approval banner appears, Approve/Reject buttons work

6. **Event history tab**
   - Click "Event History" tab
   - **Expected**: Shows chronological list of all events

---

## Related Flows

- [process-execution.md](./process-execution.md) - How events are generated by ExecutionEngine
- [sub-processes.md](./sub-processes.md) - Parent-child execution relationships
- [human-approval.md](./human-approval.md) - Approval UI details
- [process-analytics.md](./process-analytics.md) - Dashboard metrics

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | Rebuilt with accurate line numbers from source files |
| 2026-01-16 | Initial creation |
