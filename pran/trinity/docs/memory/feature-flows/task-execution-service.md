# Feature: Task Execution Service (EXEC-024)

## Overview
Unified service that encapsulates the full task-execution lifecycle (execution record, slot management, activity tracking, agent HTTP call with retry, credential sanitization, response persistence) so all callers share one code path.

## User Story
As the platform, I want all task execution paths (authenticated tasks, public link chat, scheduled executions) to use a single orchestration service so that every execution gets consistent tracking, slot enforcement, credential sanitization, and dashboard visibility.

## Entry Points

This is a **backend service** -- no direct UI entry point. Callers are:

| Caller | File | Endpoint | `triggered_by` |
|--------|------|----------|-----------------|
| Authenticated sync task | `src/backend/routers/chat.py:714` | `POST /api/agents/{name}/task` | `"manual"` or `"agent"` |
| Public link chat | `src/backend/routers/public.py:316` | `POST /api/public/chat/{token}` | `"public"` |
| (Future) Scheduler | `src/backend/services/scheduler_service.py` | Internal | `"schedule"` |

## Backend Layer

### Service File

**`src/backend/services/task_execution_service.py`** (new, 391 lines)

#### TaskExecutionResult dataclass (line 42)

```python
@dataclass
class TaskExecutionResult:
    execution_id: str
    status: str                         # "success" | "failed"
    response: str                       # Sanitized response text
    cost: Optional[float] = None
    context_used: Optional[int] = None
    context_max: Optional[int] = None
    session_id: Optional[str] = None    # Claude Code session ID
    execution_log: Optional[str] = None # Sanitized JSON transcript
    raw_response: dict = field(default_factory=dict)
    error: Optional[str] = None
```

Callers inspect `result.status` to decide HTTP response. The service never raises for agent-level errors.

#### agent_post_with_retry() (line 60)

Moved from `routers/chat.py`. Module-level async function. Used by:
- `TaskExecutionService.execute_task()` internally (line 218)
- `routers/chat.py` for `/chat` endpoint (line 215) and `_execute_task_background` (line 404)

```python
async def agent_post_with_retry(
    agent_name: str,
    endpoint: str,
    payload: dict,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float = 600.0,
) -> httpx.Response:
```

Exponential backoff: delay = `retry_delay * (2 ** attempt)`. Handles `httpx.ConnectError` for agent servers still booting.

#### TaskExecutionService.execute_task() (line 112)

Full execution lifecycle in one method:

```
Step  Action                                    Line   Dependency
----  ----------------------------------------  -----  ----------------------------------
1     Create execution record (if not provided)  148    db.create_task_execution()
2     Acquire capacity slot                      164    slot_service.acquire_slot()
3     Track activity start (CHAT_START)          188    activity_service.track_activity()
4     POST to agent /api/task with retry         218    agent_post_with_retry()
5     Sanitize response + execution log          240    sanitize_execution_log(), sanitize_response()
6     Update execution record with result        251    db.update_execution_status()
7     Complete activity                          265    activity_service.complete_activity()
8     Release slot (always, in finally block)    371    slot_service.release_slot()
```

**Signature:**
```python
async def execute_task(
    self,
    agent_name: str,
    message: str,
    triggered_by: str,                      # "manual"|"public"|"schedule"|"agent"|"mcp"
    source_user_id: Optional[int] = None,
    source_user_email: Optional[str] = None,
    source_agent_name: Optional[str] = None,
    source_mcp_key_id: Optional[str] = None,
    source_mcp_key_name: Optional[str] = None,
    model: Optional[str] = None,
    timeout_seconds: int = 120,
    resume_session_id: Optional[str] = None,
    allowed_tools: Optional[list] = None,
    system_prompt: Optional[str] = None,
    execution_id: Optional[str] = None,
) -> TaskExecutionResult:
```

If `execution_id` is provided, the caller has already created the execution record (e.g. `chat.py` creates it early for async-mode support). Otherwise the service creates one.

#### get_task_execution_service() (line 385)

Global singleton accessor. Lazy-initializes on first call.

### Caller 1: Authenticated Sync Task

**`src/backend/routers/chat.py:560-812`** -- `execute_parallel_task()`

The endpoint handles:
1. Container validation (lines 586-591)
2. Determine `triggered_by` from headers (lines 594-599)
3. Create execution record early (lines 602-613) -- passed to service as `execution_id`
4. Collaboration tracking for agent-to-agent (lines 618-640) -- stays in router
5. **Async mode branch** (lines 643-711) -- spawns `_execute_task_background()`, does NOT use service
6. **Sync mode branch** (lines 713-730) -- delegates to `task_execution_service.execute_task()`
7. Collaboration activity completion (lines 733-742)
8. Error translation to HTTP exceptions (lines 745-760)
9. Chat session persistence if `save_to_session` (lines 766-807)

```python
# Line 713-730
task_execution_service = get_task_execution_service()
result = await task_execution_service.execute_task(
    agent_name=name,
    message=request.message,
    triggered_by=triggered_by,
    source_user_id=current_user.id,
    source_user_email=current_user.email or current_user.username,
    source_agent_name=x_source_agent,
    ...
    execution_id=execution_id,  # Pre-created
)
```

### Caller 2: Public Link Chat

**`src/backend/routers/public.py:215-362`** -- `public_chat()`

The endpoint handles:
1. Link token validation (lines 231-233)
2. Session identity resolution: email or anonymous (lines 236-263)
3. Rate limiting by IP (lines 266-271)
4. Agent container check (lines 274-279)
5. Public chat session management (lines 284-295)
6. Store user message (lines 291-295)
7. Build context prompt with conversation history (lines 305-309)
8. **Delegate to service** (lines 311-322)
9. Error translation to HTTP exceptions (lines 324-341)
10. Store assistant response in public chat messages (lines 346-351)

```python
# Lines 311-322
task_execution_service = get_task_execution_service()
result = await task_execution_service.execute_task(
    agent_name=agent_name,
    message=context_prompt,
    triggered_by="public",
    source_user_email=source_email,    # verified_email or f"anonymous ({client_ip})"
    timeout_seconds=120,
)
```

Key behavioral change: public executions now get full tracking that was previously missing -- execution records, activity stream, slot management, credential sanitization, and Dashboard timeline visibility.

## Data Layer

### Database Operations

| Operation | Method | File | Line |
|-----------|--------|------|------|
| Create execution record | `db.create_task_execution()` | `src/backend/database.py:486` | Delegates to `_schedule_ops` |
| Get max parallel tasks | `db.get_max_parallel_tasks()` | `src/backend/database.py:401` | Delegates to `_agent_ops` |
| Update execution status | `db.update_execution_status()` | `src/backend/database.py:530` | Updates status, response, cost, context, logs |
| Get execution (for cancel check) | `db.get_execution()` | `src/backend/database.py:549` | Checks if status is "cancelled" before overwriting |

### Redis Operations

| Operation | Service | Key Pattern |
|-----------|---------|-------------|
| Acquire slot | `SlotService.acquire_slot()` | `agent:slots:{name}` (ZSET), `agent:slot:{name}:{exec_id}` (HASH) |
| Release slot | `SlotService.release_slot()` | Same keys, ZREM + DELETE |

Slot TTL: 30 minutes (safety net for orphaned slots).

## Side Effects

### Activity Tracking

| Event | Type | When |
|-------|------|------|
| Execution start | `ActivityType.CHAT_START` | After slot acquired (line 188) |
| Execution success | `complete_activity(status="completed")` | After response persisted (line 265) |
| Execution failure | `complete_activity(status="failed")` | On any exception (lines 300, 337, 359) |

### WebSocket Broadcasts

Activity events are broadcast via `ActivityService._broadcast_activity_event()`:

```json
{
  "type": "agent_activity",
  "agent_name": "agent-name",
  "activity_id": "uuid",
  "activity_type": "chat_start",
  "activity_state": "started",
  "action": "Processing: message preview...",
  "timestamp": "2026-03-04T12:00:00",
  "details": {
    "message_preview": "...",
    "execution_id": "exec-uuid",
    "triggered_by": "public"
  }
}
```

### Credential Sanitization

Applied before database persistence (defense-in-depth layer):

| Function | Source | Purpose |
|----------|--------|---------|
| `sanitize_execution_log()` | `src/backend/utils/credential_sanitizer.py:154` | Scrub API keys from JSON execution logs |
| `sanitize_response()` | `src/backend/utils/credential_sanitizer.py:172` | Scrub API keys from agent response text |

Patterns: OpenAI keys (`sk-*`), Anthropic keys (`sk-ant-*`), GitHub tokens (`ghp_*`, `github_pat_*`), AWS keys (`AKIA*`), Bearer tokens, and sensitive env var key-value pairs.

## Error Handling

The service catches all errors and returns `TaskExecutionResult` with `status="failed"`. Callers translate to HTTP.

| Error Case | Service Result | chat.py HTTP | public.py HTTP |
|------------|---------------|--------------|----------------|
| Slot not acquired | `status="failed", error="Agent at capacity..."` | 429 | 429 |
| Agent connect timeout | `status="failed", error="timed out..."` | 504 | 504 |
| Agent HTTP error | `status="failed", error=detail` | 503 | 502 |
| Unexpected exception | `status="failed", error=str(e)` | 503 | 502 |
| Cancelled execution | Preserved -- does not overwrite "cancelled" status | N/A | N/A |

Cancel protection (lines 293-294, 325-326, 350-351): Before writing "failed" status, checks `db.get_execution(execution_id)` -- if status is already "cancelled" (from user termination), the service does not overwrite it.

## Execution Lifecycle Diagram

```
Caller (chat.py or public.py)
  |
  v
execute_task()
  |
  +-- 1. db.create_task_execution()
  |      (if execution_id not provided)
  |
  +-- 2. slot_service.acquire_slot()
  |      |
  |      +-- FAIL --> return TaskExecutionResult(status="failed")
  |
  +-- 3. activity_service.track_activity(CHAT_START)
  |
  +-- 4. agent_post_with_retry(agent_name, "/api/task", payload)
  |      |
  |      +-- Retries: 3 attempts, exponential backoff (1s, 2s, 4s)
  |      |
  |      +-- httpx.ConnectError --> retry or fail
  |      +-- httpx.TimeoutException --> fail
  |      +-- httpx.HTTPError --> fail
  |
  +-- 5. sanitize_execution_log() + sanitize_response()
  |
  +-- 6. db.update_execution_status(status="success", ...)
  |
  +-- 7. activity_service.complete_activity(status="completed")
  |
  +-- 8. [FINALLY] slot_service.release_slot()
  |
  v
return TaskExecutionResult(status="success", ...)
```

## Agent Payload

The service POSTs to `http://agent-{name}:8000/api/task`:

```json
{
  "message": "task content",
  "model": "sonnet",
  "allowed_tools": ["Read", "Write"],
  "system_prompt": "additional instructions",
  "timeout_seconds": 120,
  "execution_id": "uuid",
  "resume_session_id": "claude-session-id"
}
```

Expected response from agent:

```json
{
  "response": "agent answer text",
  "session_id": "claude-code-session-id",
  "metadata": {
    "input_tokens": 1234,
    "output_tokens": 567,
    "cost_usd": 0.05,
    "context_window": 200000,
    "session_id": "claude-code-session-id"
  },
  "execution_log": [
    {"type": "tool_use", "tool": "Read", ...},
    {"type": "tool_result", ...}
  ]
}
```

## Testing

### Prerequisites
- Services running (`./scripts/deploy/start.sh`)
- At least one agent created and running
- A public link configured for the agent

### Test Steps

1. **Action**: Send a message via public link chat
   **Expected**: Execution appears in agent's Tasks tab with `triggered_by: public`
   **Verify**: `GET /api/agents/{name}/executions` includes an entry with source email or "anonymous (IP)"

2. **Action**: Check Dashboard timeline after public link message
   **Expected**: Execution box appears for the agent on the timeline
   **Verify**: Activity stream includes `CHAT_START` event with `triggered_by: "public"`

3. **Action**: Set agent max_parallel_tasks to 1, run an authenticated task, then immediately send a public link message
   **Expected**: Public link returns 429 "Agent is busy"
   **Verify**: Redis `agent:slots:{name}` ZSET has 1 entry

4. **Action**: Run authenticated sync task via Tasks tab
   **Expected**: Execution completes with same metadata as before (no regression)
   **Verify**: Response includes `task_execution_id`, cost, context usage

5. **Action**: Send a public message that triggers tool use (e.g., file read)
   **Expected**: Execution log in Tasks tab has credentials redacted
   **Verify**: No `sk-*`, `ghp_*`, or Bearer tokens in execution_log column

## Related Flows

- [parallel-headless-execution.md](parallel-headless-execution.md) -- the `/task` endpoint this service backs
- [parallel-capacity.md](parallel-capacity.md) -- slot management consumed by this service
- [public-agent-links.md](public-agent-links.md) -- primary beneficiary of unified tracking
- [activity-stream.md](activity-stream.md) -- activity tracking consumed by this service
- [tasks-tab.md](tasks-tab.md) -- UI that displays execution records
- [dashboard-timeline-view.md](dashboard-timeline-view.md) -- timeline that shows execution events
- [continue-execution-as-chat.md](continue-execution-as-chat.md) -- EXEC-023, resume_session_id support
