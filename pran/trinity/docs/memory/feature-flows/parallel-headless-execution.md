# Feature Flow: Parallel Headless Execution

> **Requirement**: 12.1 - Parallel Headless Execution
> **Status**: Implemented
> **Created**: 2025-12-22
> **Updated**: 2026-03-04 (EXEC-024 service extraction)
> **Verified**: 2026-02-05

## Revision History

| Date | Changes |
|------|---------|
| 2026-03-04 | **EXEC-024 Service Extraction**: Sync path of `POST /api/agents/{name}/task` refactored. The ~250 lines of inline execution logic (slot acquisition, activity tracking, agent call with retry, sanitization, execution record updates, error handling, slot release) extracted into `TaskExecutionService.execute_task()` in `src/backend/services/task_execution_service.py`. Sync path in `chat.py:713-730` now delegates to the service. `agent_post_with_retry()` moved to the service module and imported back into `chat.py` for use by `/chat` and `_execute_task_background`. Async mode path unchanged (still uses `_execute_task_background` inline). |
| 2026-03-02 | **MODEL-001 Model Selection**: `model_used` field now recorded on every execution record via `db.create_task_execution(model_used=request.model)`. Backend `chat.py:593` passes model to execution record. TasksPanel sends `model` in POST body. See [model-selection.md](model-selection.md). |
| 2026-02-17 | **Added PUB-003 use case**: Public Chat Agent Introduction uses `/api/task` to fetch agent intro. Cross-reference to public-agent-links.md added. |
| 2026-02-21 | **Bug Fix (EXEC-023)**: Fixed `DatabaseManager.update_execution_status()` wrapper in `src/backend/database.py:1295-1299` - was missing `claude_session_id` parameter, causing task executions to fail storing session IDs for the "Continue Execution as Chat" feature. The underlying `db/schedules.py:update_execution_status()` (lines 559-610) already supported the parameter. |
| 2026-02-20 | **Chat Session Persistence (CHAT-001)**: `/task` endpoint now supports `save_to_session`, `user_message`, `create_new_session` parameters for authenticated Chat tab. When `save_to_session=true`, messages persist to `chat_sessions` and `chat_messages` tables. Response includes `chat_session_id`. New `db.create_new_chat_session()` method closes existing sessions before creating new one. |
| 2026-02-16 | **Security Fix (Credential Leakage Prevention)**: Agent-side and backend-side credential sanitization now prevents secrets from appearing in execution logs. Agent sanitizes subprocess output via `sanitize_subprocess_line()` and response text via `sanitize_text()` (claude_code.py:491-529, 693-747). Backend provides defense-in-depth via `sanitize_execution_log()` and `sanitize_response()` (now called from `TaskExecutionService` in `services/task_execution_service.py:241-247` for sync path, and from `_execute_task_background` in `chat.py:419-426` for async path). |
| 2026-02-15 | **Claude Max subscription support**: Headless task execution now supports Claude Max subscription authentication. If user ran `/login` in web terminal, the OAuth session stored in `~/.claude.json` is used instead of requiring `ANTHROPIC_API_KEY`. The mandatory API key check was removed from `execute_headless_task()` in `docker/base-image/agent_server/services/claude_code.py`. |
| 2026-02-12 | **Test fix**: `test_parallel_task_does_not_show_in_queue` (in `tests/test_execution_queue.py`) now uses `async_mode: True` to avoid 30s timeout. The test verifies that parallel tasks bypass the execution queue. |
| 2026-02-05 | **SSE streaming fix**: Documented nginx configuration required for live execution streaming. Added `proxy_buffering off`, `proxy_cache off`, `chunked_transfer_encoding on` directives. Added frontend implementation details using fetch with ReadableStream. |
| 2026-01-30 | **Async mode (fire-and-forget)**: Added `async_mode` parameter for non-blocking execution. Backend spawns background task, returns immediately with `execution_id`. Poll for results. New section documents implementation, use cases, and API. |
| 2026-01-23 | Verified all line numbers against current codebase. Updated file references. |
| 2026-01-12 | Added max_turns parameter for runaway prevention |
| 2025-12-31 | Added execution log persistence details |
| 2025-12-22 | Initial documentation |

## Overview

This feature enables Trinity agents to execute multiple independent tasks in parallel without blocking the main conversation context. It unlocks agent-to-agent orchestration patterns where an orchestrator can delegate to multiple workers simultaneously.

## Problem Statement

**Prior Limitation**: Trinity agents could only process one request at a time due to:
1. Platform-level execution queue (Redis) that serializes requests
2. Container-level execution lock (`asyncio.Lock`)
3. Use of `--continue` flag which requires sequential execution to maintain conversation context

**Solution**: New parallel task mode that bypasses queue and lock, runs stateless (no --continue).

## Two Execution Modes

| Mode | Endpoint | Context | Parallel | Use Case |
|------|----------|---------|----------|----------|
| **Sequential Chat** | `POST /api/agents/{name}/chat` | Maintains conversation | No | Interactive chat, multi-turn reasoning |
| **Parallel Task** | `POST /api/agents/{name}/task` | Stateless | Yes | Agent delegation, batch processing |

## Architecture Diagram

```
                                    +-----------------------------+
                                    |     Sequential Chat         |
User/Agent --> POST /chat --------->|  Execution Queue (Redis)    |--> claude --continue
                                    |  One at a time              |
                                    +-----------------------------+

                                    +-----------------------------+
                                    |     Parallel Task           |
User/Agent --> POST /task --------->|  No queue, no lock          |--> claude -p (headless)
              (can send N)          |  N concurrent allowed       |    (N processes)
                                    +-----------------------------+
```

## Data Flow

### 1. MCP Tool Call (Orchestrator Agent)

```
Orchestrator Agent
       |
       v
+---------------------------------------------+
| chat_with_agent(                            |
|   agent_name: "worker-1",                   |
|   message: "Process file X",                |
|   parallel: true,                           |
|   timeout_seconds: 300                      |
| )                                           |
+---------------------------------------------+
       |
       v
   MCP Server (src/mcp-server)
       |
       v
   client.task(name, message, options)
       |
       v
   POST /api/agents/{name}/task
```

### 2. Backend Processing

```
POST /api/agents/{name}/task
       |
       v
+---------------------------------------------+
| Router (chat.py:560-812)                    |
| 1. Validate agent exists and is running     |
| 2. Create execution record (early, for     |
|    async mode and tracking)                 |
| 3. Broadcast collaboration event (if        |
|    agent-to-agent)                          |
| 4. If async_mode: spawn background task     |
|    via _execute_task_background(), return    |
|    immediately                              |
| 5. If sync: delegate to                     |
|    TaskExecutionService.execute_task()      |
|    (NO EXECUTION QUEUE)                     |
+---------------------------------------------+
       |  (sync path)
       v
+---------------------------------------------+
| TaskExecutionService (EXEC-024)             |
| services/task_execution_service.py          |
|                                             |
| 1. Acquire capacity slot                    |
| 2. Track activity start                     |
| 3. Call agent via agent_post_with_retry()   |
| 4. Sanitize response + execution log        |
| 5. Update execution record (success/fail)   |
| 6. Complete activity                        |
| 7. Release slot (finally)                   |
| 8. Return TaskExecutionResult               |
+---------------------------------------------+
       |
       v
+---------------------------------------------+
| Router (post-service)                       |
| - Complete collaboration activity           |
| - Translate failed status to HTTP errors    |
| - Persist to chat session (save_to_session) |
| - Return response                           |
+---------------------------------------------+
       |
       v
   POST http://agent-{name}:8000/api/task
```

### 3. Agent Container Execution

```
POST /api/task
       |
       v
+---------------------------------------------+
| execute_headless_task()                     |
|                                             |
| - NO execution lock acquired                |
| - Build command:                            |
|   claude -p --output-format stream-json     |
|   --verbose --dangerously-skip-permissions  |
|   [--model X] [--allowedTools Y]            |
|   [--append-system-prompt Z]                |
|   [--max-turns N]                           |
|   [--mcp-config ~/.mcp.json]                |
|                                             |
| - NO --continue flag (stateless)            |
| - Parse streaming JSON output               |
| - Return response with session_id           |
+---------------------------------------------+
```

## Key Files

### Agent Server (docker/base-image/agent_server/)

| File | Line | Purpose |
|------|------|---------|
| `models.py` | 215-232 | ParallelTaskRequest, ParallelTaskResponse models |
| `services/claude_code.py` | 553-739 | execute_headless_task() function |
| `services/gemini_runtime.py` | 489-642 | execute_headless() for Gemini CLI |
| `services/runtime_adapter.py` | 99-129 | AgentRuntime.execute_headless() interface |
| `routers/chat.py` | 96-137 | POST /api/task endpoint |

### Backend (src/backend/)

| File | Line | Purpose |
|------|------|---------|
| `models.py` | 109-117 | ParallelTaskRequest model with max_turns and async_mode |
| `services/task_execution_service.py` | 42-53 | `TaskExecutionResult` dataclass (status, response, cost, etc.) |
| `services/task_execution_service.py` | 60-96 | `agent_post_with_retry()` HTTP helper with exponential backoff |
| `services/task_execution_service.py` | 103-376 | `TaskExecutionService.execute_task()` — full sync execution lifecycle |
| `routers/chat.py` | 21-24 | Imports `get_task_execution_service` and `agent_post_with_retry` from service |
| `routers/chat.py` | 370-557 | `_execute_task_background()` helper for async mode (still inline) |
| `routers/chat.py` | 560-812 | POST /api/agents/{name}/task endpoint |
| `routers/chat.py` | 713-730 | Sync path delegation to `TaskExecutionService.execute_task()` |
| `routers/chat.py` | 744-760 | Translates `TaskExecutionResult.status == "failed"` to HTTP errors |
| `routers/schedules.py` | 323-336 | GET /api/agents/{name}/executions/{id} endpoint (polling) |
| `routers/schedules.py` | 339-379 | GET /api/agents/{name}/executions/{id}/log endpoint |
| `services/agent_client.py` | 194-287 | AgentClient.task() method |

### MCP Server (src/mcp-server/)

| File | Line | Purpose |
|------|------|---------|
| `src/client.ts` | 399-454 | task() method with async_mode option |
| `src/tools/chat.ts` | 132-284 | chat_with_agent tool with parallel and async parameters |
| `src/tools/chat.ts` | 187-194 | async parameter definition |

### Sync vs Async Code Paths (EXEC-024)

As of EXEC-024, the sync and async execution paths diverge:

| Aspect | Sync (`async_mode=false`) | Async (`async_mode=true`) |
|--------|---------------------------|---------------------------|
| Execution logic | `TaskExecutionService.execute_task()` in `services/task_execution_service.py` | `_execute_task_background()` inline in `routers/chat.py:370-557` |
| Slot management | Service acquires/releases slots internally | Router acquires slot before spawning; background task releases in `finally` |
| Activity tracking | Service tracks start/completion internally | Router tracks start; background task completes activities |
| Result handling | Returns `TaskExecutionResult`; router translates to HTTP | Background task updates DB directly |
| HTTP helper | `agent_post_with_retry()` defined in service, called internally | Same function imported from service into `chat.py` |

The router (`chat.py:560-812`) still handles: container validation, execution record creation (early), collaboration tracking (WebSocket events), async mode branching, session persistence (`save_to_session`), and translating `TaskExecutionResult.status == "failed"` to HTTP error codes (429/504/503).

## API Specifications

### Agent Server: POST /api/task

**Request**:
```json
{
  "message": "string",           // Required: Task to execute
  "model": "sonnet|opus|haiku",  // Optional: Model override
  "allowed_tools": ["Read"],     // Optional: Tool restrictions
  "system_prompt": "string",     // Optional: Additional instructions
  "timeout_seconds": 900,        // Optional: Timeout (default 15 min)
  "max_turns": 50,               // Optional: Max agentic turns (runaway prevention)
  "execution_id": "uuid"         // Optional: Database execution ID for process registry
}
```

**Response**:
```json
{
  "response": "string",          // Claude's response
  "execution_log": [...],        // Tool calls and results (also saved to DB)
  "metadata": {
    "cost_usd": 0.01,
    "duration_ms": 5000,
    "input_tokens": 1000,
    "output_tokens": 500,
    "tool_count": 3
  },
  "session_id": "uuid",          // Unique per task
  "timestamp": "2025-12-22T...",
  "chat_session_id": "string"    // Only present when save_to_session=true
}
```

**Note**: The `execution_log` is persisted to the `schedule_executions` database table and can be retrieved via `GET /api/agents/{name}/executions/{execution_id}/log`.

### Backend: POST /api/agents/{name}/task

Same request/response as agent server, with additional parameters:

**Backend-Only Request Parameters** (`src/backend/models.py:81-92`):
| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `async_mode` | bool | false | If true, return immediately with execution_id (fire-and-forget) |
| `save_to_session` | bool | false | If true, persist messages to `chat_sessions` table (for authenticated Chat tab) |
| `user_message` | string | null | Original user message without context prefix (for clean session display) |
| `create_new_session` | bool | false | If true, close existing active sessions and create a new one |

**Backend Features**:
- Authentication via JWT token
- Access control validation
- Activity tracking (sync: via `TaskExecutionService`; async: via `_execute_task_background`)
- Audit logging
- **Slot management** - Capacity-limited parallel execution via `SlotService` (CAPACITY-001)
- **Execution log persistence** - Full transcript saved to `schedule_executions.execution_log`
- **Credential sanitization** - `sanitize_execution_log()` and `sanitize_response()` applied to all results
- **Process registry** - Passes `execution_id` to agent for termination tracking
- **Chat session persistence** - When `save_to_session=true`, persists to `chat_sessions` and `chat_messages` tables
- **Service delegation** (EXEC-024) - Sync path delegates to `TaskExecutionService.execute_task()`

### Backend: GET /api/agents/{name}/executions/{execution_id}/log

Retrieve the full execution log for any task execution.

**File**: `src/backend/routers/schedules.py:339-379`

**Response**:
```json
{
  "execution_id": "abc123",
  "agent_name": "worker-1",
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

### MCP Tool: chat_with_agent

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| agent_name | string | required | Target agent |
| message | string | required | Task to execute |
| parallel | boolean | false | Enable parallel mode |
| model | string | null | Model override (parallel only) |
| allowed_tools | string[] | null | Tool restrictions (parallel only) |
| system_prompt | string | null | Additional instructions (parallel only) |
| timeout_seconds | number | 300 | Timeout in seconds (parallel only) |
| max_turns | number | null | Max agentic turns for runaway prevention (parallel only) |
| async | boolean | false | Fire-and-forget mode - return immediately with execution_id (parallel only) |

## Key Differences: Chat vs Task

| Aspect | Chat (Sequential) | Task (Parallel) |
|--------|-------------------|-----------------|
| Endpoint | POST /api/chat | POST /api/task |
| Execution Queue | Yes (Redis) | No |
| Execution Lock | Yes (asyncio.Lock) | No |
| --continue flag | Yes | No |
| Conversation context | Maintained | Stateless |
| Session updates | Yes | No |
| Concurrent requests | 1 per agent | N per agent |
| Use case | Interactive chat | Batch processing |

## Runaway Prevention: max_turns Parameter

**Added**: 2026-01-12

The `max_turns` parameter limits the number of agentic turns an agent can take before the CLI exits. This prevents runaway agents that get stuck in infinite loops or continue executing far beyond expected scope.

### How It Works

When `max_turns` is specified:

1. **Agent Server** passes `--max-turns N` to the Claude Code or Gemini CLI command
2. **CLI** counts each agentic turn (tool use + tool result cycle)
3. **At limit**: CLI exits with an error, returning partial results
4. **Response**: Includes whatever work was completed before the limit

### Implementation Details

**Claude Code** (`docker/base-image/agent_server/services/claude_code.py:622-625`):
```python
if max_turns is not None:
    cmd.extend(["--max-turns", str(max_turns)])
    logger.info(f"[Headless Task] Limiting to {max_turns} agentic turns")
```

**Gemini CLI** (`docker/base-image/agent_server/services/gemini_runtime.py:542-544`):
```python
if max_turns is not None:
    cmd.extend(["--max-turns", str(max_turns)])
    logger.info(f"[Headless Task {session_id}] Limiting to {max_turns} agentic turns")
```

### Usage Examples

**Conservative limit for simple tasks**:
```json
{
  "message": "Read the README.md file and summarize it",
  "max_turns": 5
}
```

**Higher limit for complex analysis**:
```json
{
  "message": "Analyze this codebase and create a report",
  "max_turns": 50,
  "timeout_seconds": 1800
}
```

**Combined with tool restrictions**:
```json
{
  "message": "Search for security vulnerabilities",
  "allowed_tools": ["Read", "Grep", "Glob"],
  "max_turns": 100,
  "timeout_seconds": 3600
}
```

### Recommended Values

| Task Type | Recommended max_turns | Rationale |
|-----------|----------------------|-----------|
| Simple queries | 5-10 | Few file reads needed |
| Code analysis | 25-50 | Multiple file traversals |
| Refactoring | 50-100 | Many edit operations |
| Deep research | 100-200 | Extensive exploration |
| Unlimited | null (default) | Trusted orchestrators only |

### When to Use

- **Always** for user-triggered parallel tasks
- **Always** for scheduled tasks without human supervision
- **Recommended** for agent-to-agent delegation
- **Optional** for interactive chat (human can cancel)

### Relationship with timeout_seconds

Both parameters provide safety limits:

| Parameter | Protects Against | Behavior at Limit |
|-----------|-----------------|-------------------|
| `timeout_seconds` | Wall-clock time exceeded | Process killed, HTTP 504 |
| `max_turns` | Too many agentic operations | CLI exits gracefully, HTTP 500 |

Use both together for comprehensive protection:
```json
{
  "message": "Complex task",
  "max_turns": 50,
  "timeout_seconds": 900
}
```

## Async Mode (Fire-and-Forget)

**Added**: 2026-01-30

Async mode enables non-blocking task execution where the API returns immediately with an `execution_id` that can be polled later for results.

### How It Works

When `async_mode=true` is specified:

1. **Backend acquires capacity slot** (CAPACITY-001)
2. **Backend creates execution record** with `status="running"`
3. **Tracks activity** (CHAT_START with async_mode: true)
4. **Spawns background task** via `asyncio.create_task(_execute_task_background(...))`
5. **Returns immediately** with `execution_id` for polling
6. **Background task executes** the Claude Code command (via `agent_post_with_retry`)
7. **Updates execution record** when complete (success/failed)
8. **Completes activities** asynchronously
9. **Releases slot** in `finally` block

Note: Async mode does **not** use `TaskExecutionService`. It uses the inline `_execute_task_background()` function because it needs to manage its own activity IDs, collaboration tracking, and slot release timing.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Async Mode Flow                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Orchestrator                                                    │
│       │                                                          │
│       ├── POST /api/agents/worker/task {async_mode: true}       │
│       │                                                          │
│       v                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Backend (chat.py — async branch)                        │    │
│  │                                                          │    │
│  │  1. Acquire capacity slot (CAPACITY-001)                 │    │
│  │  2. Create execution record (status="running")           │    │
│  │  3. Track activities (CHAT_START)                        │    │
│  │  4. asyncio.create_task(_execute_task_background(...))   │    │
│  │  5. Return immediately:                                  │    │
│  │     { status: "accepted", execution_id: "abc123" }       │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│       │<────────────────────┘  (immediate response)              │
│       │                                                          │
│       │  Poll: GET /api/agents/worker/executions/abc123          │
│       │                                                          │
│                        (Background task runs independently)      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  _execute_task_background()                               │   │
│  │                                                           │   │
│  │  - Calls agent container /api/task                        │   │
│  │  - On success: db.update_execution_status("success")      │   │
│  │  - On failure: db.update_execution_status("failed")       │   │
│  │  - Completes activities                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Details

**Backend Model** (`src/backend/models.py:117`):
```python
class ParallelTaskRequest(BaseModel):
    # ... existing fields ...
    async_mode: Optional[bool] = False  # If true, return immediately with execution_id
```

**Background Task Handler** (`src/backend/routers/chat.py:370-557`):
```python
async def _execute_task_background(
    agent_name: str,
    request: ParallelTaskRequest,
    execution_id: str,
    task_activity_id: str,
    collaboration_activity_id: Optional[str],
    x_source_agent: Optional[str],
    release_slot: bool = False,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None
):
    """
    Background task execution for async mode.
    Runs the task and updates execution record/activities when complete.
    Note: This still uses inline logic (not TaskExecutionService) because
    async mode needs to manage its own activity IDs and collaboration tracking.
    """
    try:
        # Call agent container (agent_post_with_retry imported from task_execution_service)
        response = await agent_post_with_retry(agent_name, "/api/task", payload, ...)

        # Sanitize + update execution record with success
        db.update_execution_status(execution_id=execution_id, status="success", ...)

        # Persist to chat session if requested (THINK-001)
        # Complete activities
        await activity_service.complete_activity(task_activity_id, ...)

    except Exception as e:
        # Update execution record with failure
        db.update_execution_status(execution_id=execution_id, status="failed", error=str(e))

        # Complete activities with failure
        await activity_service.complete_activity(task_activity_id, status="failed", ...)

    finally:
        # Release slot when task completes (CAPACITY-001)
        if slot_service and release_slot:
            await slot_service.release_slot(agent_name, execution_id)
```

**Endpoint Logic — Async branch** (`src/backend/routers/chat.py:643-711`):
```python
# Async mode: acquire slot here, spawn background task which releases it
if request.async_mode:
    # Acquire slot (CAPACITY-001), track activity, update status to "running"
    # ... slot acquisition, activity tracking ...

    # Spawn background task (slot will be released when task completes)
    asyncio.create_task(
        _execute_task_background(
            agent_name=name,
            request=request,
            execution_id=execution_id,
            task_activity_id=task_activity_id,
            collaboration_activity_id=collaboration_activity_id,
            x_source_agent=x_source_agent,
            release_slot=True,
            user_id=current_user.id,
            user_email=current_user.email or current_user.username
        )
    )

    # Return immediately with execution_id for polling
    return {
        "status": "accepted",
        "execution_id": execution_id,
        "agent_name": name,
        "message": "Task accepted. Poll GET /api/agents/{name}/executions/{execution_id} for results.",
        "async_mode": True
    }

# ---- Sync mode: delegate to TaskExecutionService (EXEC-024) ----
task_execution_service = get_task_execution_service()
result = await task_execution_service.execute_task(
    agent_name=name,
    message=request.message,
    triggered_by=triggered_by,
    source_user_id=current_user.id,
    source_user_email=current_user.email or current_user.username,
    source_agent_name=x_source_agent,
    # ... additional params ...
    execution_id=execution_id,
)

# Translate TaskExecutionResult.status == "failed" to HTTP errors
if result.status == "failed":
    if "at capacity" in (result.error or ""):
        raise HTTPException(status_code=429, ...)
    elif "timed out" in (result.error or ""):
        raise HTTPException(status_code=504, ...)
    else:
        raise HTTPException(status_code=503, ...)
```

**MCP Client** (`src/mcp-server/src/client.ts:399-454`):
```typescript
async task(name: string, message: string, options?: {
  // ... existing options ...
  async_mode?: boolean;  // If true, return immediately with execution_id
}, sourceAgent?: string) {
  // Async mode returns immediately; sync mode waits for full execution
  const timeout = options?.async_mode ? 30 : (options?.timeout_seconds || 600) + 10;
  // ...
}
```

**MCP Tool** (`src/mcp-server/src/tools/chat.ts:187-194`):
```typescript
async: z
  .boolean()
  .optional()
  .default(false)
  .describe(
    "If true, return immediately with execution_id (fire-and-forget). " +
    "Only applies when parallel=true. Poll the execution endpoint for results."
  ),
```

### API Specification

**Request**:
```json
{
  "message": "Process large dataset",
  "async_mode": true,
  "model": "sonnet",
  "timeout_seconds": 3600
}
```

**Immediate Response** (HTTP 200):
```json
{
  "status": "accepted",
  "execution_id": "abc123xyz789",
  "agent_name": "worker-1",
  "message": "Task accepted. Poll GET /api/agents/{name}/executions/{execution_id} for results.",
  "async_mode": true
}
```

**Polling Endpoint**: `GET /api/agents/{name}/executions/{execution_id}`

**Response when running**:
```json
{
  "id": "abc123xyz789",
  "agent_name": "worker-1",
  "status": "running",
  "message": "Process large dataset",
  "triggered_by": "manual",
  "started_at": "2026-01-30T10:00:00Z",
  "completed_at": null,
  "response": null,
  "cost": null
}
```

**Response when complete**:
```json
{
  "id": "abc123xyz789",
  "agent_name": "worker-1",
  "status": "success",
  "message": "Process large dataset",
  "triggered_by": "manual",
  "started_at": "2026-01-30T10:00:00Z",
  "completed_at": "2026-01-30T10:05:00Z",
  "response": "Dataset processed successfully. 10,000 records analyzed.",
  "cost": 0.15,
  "context_used": 50000,
  "context_max": 200000
}
```

### Use Cases

#### 1. Fan-Out Pattern
Spawn multiple long-running tasks without blocking:

```python
# Orchestrator spawns 10 workers, doesn't wait
execution_ids = []
for i, batch in enumerate(data_batches):
    result = mcp__trinity__chat_with_agent(
        agent_name=f"worker-{i}",
        message=f"Process batch: {batch}",
        parallel=true,
        async=true
    )
    execution_ids.append(result["execution_id"])

# Continue with other work while workers process...

# Later: collect results
for agent_name, exec_id in zip(worker_names, execution_ids):
    result = poll_execution(agent_name, exec_id)  # Helper to wait for completion
    results.append(result)
```

#### 2. Background Analysis
Trigger analysis that runs independently:

```python
# Start long-running analysis
result = mcp__trinity__chat_with_agent(
    agent_name="analysis-agent",
    message="Analyze codebase for security vulnerabilities",
    parallel=true,
    async=true,
    timeout_seconds=7200  # 2 hours
)

# Don't wait - check results later via UI or API
print(f"Analysis started: {result['execution_id']}")
```

#### 3. Scheduled Cleanup
System agent triggers maintenance without blocking:

```python
# Nightly cleanup across fleet
for agent in get_all_agents():
    mcp__trinity__chat_with_agent(
        agent_name=agent,
        message="Run nightly cleanup: clear temp files, rotate logs",
        parallel=true,
        async=true
    )
# All cleanup jobs run concurrently, system agent continues
```

### Key Differences: Sync vs Async

| Aspect | Sync (async_mode=false) | Async (async_mode=true) |
|--------|------------------------|-------------------------|
| Return time | After task completes | Immediately |
| Response | Full result with execution_log | execution_id only |
| HTTP timeout | timeout_seconds + 10 | 30 seconds |
| Result retrieval | In response | Poll endpoint |
| Error handling | Exception in response | Poll for error status |
| Connection held | Yes, for duration | No, released immediately |

### Limitations and Considerations

1. **No streaming in async mode**: Cannot use SSE streaming with async; poll for final result only
2. **Orphaned tasks**: If backend restarts, background tasks are lost (execution stays "running")
3. **No cancellation via async**: Must use separate termination endpoint
4. **Database required**: execution_id comes from database record; fails if DB unavailable
5. **Activity completion async**: Activities complete after task finishes, not at request time

---

## Live Execution Streaming

Task executions can be monitored in real-time via Server-Sent Events (SSE).

### Endpoint

**Backend**: `GET /api/agents/{name}/executions/{execution_id}/stream`
**File**: `src/backend/routers/chat.py:1382-1443`

**Agent Server**: `GET /api/executions/{execution_id}/stream`
**File**: `docker/base-image/agent_server/routers/chat.py:295-369`

### nginx Configuration (Required for Production)

SSE streaming requires nginx proxy buffering to be disabled. Without this, nginx buffers the SSE response and events don't stream in real-time.

**File**: `src/frontend/nginx.conf`

```nginx
location /api/ {
    proxy_pass http://trinity-backend:8000/api/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
    proxy_read_timeout 86400;

    # SSE (Server-Sent Events) support - REQUIRED for live execution streaming
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding on;
}
```

**Key SSE directives**:
| Directive | Purpose |
|-----------|---------|
| `proxy_buffering off` | Disable response buffering so events stream immediately |
| `proxy_cache off` | Prevent caching of SSE stream |
| `chunked_transfer_encoding on` | Enable chunked transfer for streaming |

### Frontend Implementation

**File**: `src/frontend/src/views/ExecutionDetail.vue:446-519`

The frontend uses `fetch` with `ReadableStream` instead of `EventSource` because:
1. `EventSource` doesn't support custom headers (needed for JWT auth)
2. `fetch` with `ReadableStream` allows proper SSE parsing with auth

```javascript
fetch(url, {
  headers: {
    'Authorization': `Bearer ${authStore.token}`,
    'Accept': 'text/event-stream'
  }
}).then(response => {
  const reader = response.body.getReader()
  // Process SSE stream...
})
```

### Process Registry

The process registry (`docker/base-image/agent_server/services/process_registry.py`) enables:
- Tracking running executions
- Terminating executions
- Live log streaming via pub/sub

### SSE Message Format

```
data: {"type": "init", "execution_id": "abc123", "status": "running"}

data: {"type": "assistant", "message": {...}, "timestamp": "..."}

data: {"type": "tool_use", "name": "Read", "input": {...}}

data: {"type": "tool_result", "content": [...]}

data: {"type": "stream_end", "status": "success"}
```

## Testing

Tests are in `tests/test_parallel_task.py`:

| Test Class | Purpose |
|------------|---------|
| TestParallelTaskEndpoint | Endpoint existence, 404/503 handling |
| TestParallelTaskResponse | Response format validation |
| TestParallelTaskOptions | Model, timeout parameter handling |
| TestParallelTaskStateless | Verifies no context pollution |
| TestParallelExecution | Multiple concurrent tasks |

Run tests:
```bash
cd tests && pytest test_parallel_task.py -v
```

### Related Tests in Other Files

**`tests/test_execution_queue.py`**:
- `TestQueueWithParallelTasks::test_parallel_task_does_not_show_in_queue` - Verifies parallel tasks bypass the execution queue. Uses `async_mode: True` to return immediately (avoids waiting for task completion which could timeout).

## Use Cases

### 1. Orchestrator-Worker Pattern
```
Orchestrator spawns 5 parallel workers:
  +-> Worker 1: "Process file A" (parallel=true)
  +-> Worker 2: "Process file B" (parallel=true)
  +-> Worker 3: "Process file C" (parallel=true)
  +-> Worker 4: "Process file D" (parallel=true)
  +-> Worker 5: "Process file E" (parallel=true)

All 5 execute concurrently, no queue blocking.
```

### 2. Batch Processing
```
System Agent runs nightly batch:
  for each agent in fleet:
    chat_with_agent(agent, "Run health check", parallel=true)
```

### 3. Research Tasks
```
Orchestrator gathers info from multiple sources:
  +-> Research Agent 1: "Find info about X" (parallel=true)
  +-> Research Agent 2: "Find info about Y" (parallel=true)
  +-> Research Agent 3: "Find info about Z" (parallel=true)

Combine results after all complete.
```

### 4. Public Chat Agent Introduction (PUB-003)
```
Public user opens /chat/{token}
  +-> Backend calls agent's /api/task endpoint
  +-> Prompt: "Introduce yourself in 2 paragraphs"
  +-> Agent responds with personalized introduction
  +-> Response displayed as first chat message

See: public-agent-links.md (PUB-003 section)
```

## Authentication (Updated 2026-02-15)

Claude Code uses whatever authentication is available in the agent container:

1. **OAuth session** (Claude Pro/Max subscription): If user ran `/login` in web terminal, session stored in `~/.claude.json` is used
2. **API key**: If `ANTHROPIC_API_KEY` environment variable is set (platform key or user-injected)

The mandatory `ANTHROPIC_API_KEY` check was removed from `execute_headless_task()` to support Claude Max subscriptions. This means:
- Agents with "Authenticate in Terminal" setting can run parallel tasks after user logs in via web terminal
- Scheduled tasks and MCP-triggered executions use the subscription instead of API billing
- API key is still supported for agents that have it configured

**Implementation**: `docker/base-image/agent_server/services/claude_code.py:586-590` - Removed mandatory API key check

## Security Considerations

1. **Access Control**: Same rules as chat - owner, shared, or admin
2. **Rate Limiting**: Consider implementing concurrency limits
3. **Audit Trail**: All parallel tasks logged with user attribution
4. **Tool Restrictions**: `allowed_tools` parameter for sandboxing
5. **Timeout**: Hard limit (`timeout_seconds`) prevents wall-clock runaway
6. **Turn Limit**: `max_turns` prevents infinite agentic loops

## Chat Session Persistence (CHAT-001)

**Added**: 2026-02-20

The `/task` endpoint now supports optional chat session persistence for the authenticated Chat tab (`ChatPanel.vue`). This enables multi-turn conversations via headless execution while maintaining session history.

### How It Works

When `save_to_session=true` is passed (`src/backend/routers/chat.py:766-807`):

1. **Session Management**:
   - If `create_new_session=true`: Close existing active sessions and create a new one (`db.create_new_chat_session()`)
   - Otherwise: Get or create session for this user+agent (`db.get_or_create_chat_session()`)

2. **Message Persistence**:
   - User message added to `chat_messages` table (uses `user_message` if provided, otherwise `message`)
   - Assistant response added with cost/context metadata

3. **Response Augmentation**:
   - Response includes `chat_session_id` for frontend session tracking

### Database Operations

**File**: `src/backend/db/chat.py:223-263`

**New Method: `create_new_chat_session()`** (lines 233-263):
```python
def create_new_chat_session(self, agent_name: str, user_id: int, user_email: str) -> ChatSession:
    """
    Create a new chat session, closing any existing active sessions for this user+agent.
    Use this when user explicitly wants a new conversation (e.g., "New Chat" button).
    """
    # 1. Close existing active sessions
    # 2. Create new session with token_urlsafe(16) ID
    # 3. Return new ChatSession
```

### Frontend Usage

**File**: `src/frontend/src/components/ChatPanel.vue:299-324`

```javascript
// Send via task endpoint with session persistence
const response = await axios.post(`/api/agents/${props.agentName}/task`, {
  message: contextPrompt,      // Full message with conversation context
  save_to_session: true,       // Persist to chat_sessions table
  user_message: userMessage,   // Original message (for clean session display)
  create_new_session: !currentSessionId.value  // New session if none active
}, { headers: authStore.authHeader })

// Update session ID from response
if (response.data.chat_session_id) {
  currentSessionId.value = response.data.chat_session_id
}
```

### Use Case: Chat Tab

The authenticated Chat tab (`ChatPanel.vue`) uses this to:
1. Track conversations in session dropdown (survives page refresh)
2. Allow switching between past sessions
3. Support "New Chat" button to start fresh conversation
4. Maintain Dashboard activity visibility (unlike Terminal which uses PTY)

See [authenticated-chat-tab.md](authenticated-chat-tab.md) for full Chat tab documentation.

## Future Enhancements

1. **Concurrency Limits**: Agent-level (default 5), platform-level (default 50)
2. **Activity Type**: New `parallel_task` activity type (currently reuses CHAT_START)
3. ~~**Session Persistence**: Optional session persistence with TTL for resume~~ **IMPLEMENTED** (CHAT-001)
4. **Batch API**: `POST /api/agents/{name}/batch` for multiple tasks
5. **Priority Queue**: Priority parameter for urgent tasks
6. **Async mode service migration**: Migrate `_execute_task_background()` to use `TaskExecutionService` for consistency (EXEC-024 follow-up)
