# Task Execution Service — Unified Execution Path (EXEC-024)

> **Status**: ✅ IMPLEMENTED
> **Priority**: HIGH
> **Created**: 2026-03-04
> **Author**: Eugene / Claude

## Overview

Extract task execution orchestration from `routers/chat.py` into a shared `services/task_execution_service.py` so that all callers (authenticated tasks, public link chat, scheduled executions) use a single code path for execution tracking, activity tracking, slot management, and response processing.

## Problem Statement

The platform has three code paths that execute tasks on agent containers:

| Caller | File | Execution Record | Activity Tracking | Slot Mgmt | Retry | Sanitization |
|--------|------|:---:|:---:|:---:|:---:|:---:|
| Authenticated `/task` | `routers/chat.py:610` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Public link chat | `routers/public.py:310` | ❌ | ❌ | ❌ | ❌ | ❌ |
| Scheduler | `services/scheduler_service.py` | ✅ | ✅ | ❌ | ❌ | ❌ |

`public.py` calls the agent container directly via raw `httpx.AsyncClient`, bypassing all platform infrastructure. Public link executions are invisible in the Tasks tab, Dashboard timeline, execution stats, and cost tracking.

The authenticated endpoint in `chat.py` is a ~400-line function that mixes HTTP routing concerns (auth, headers, request parsing) with execution orchestration (tracking, slots, activities, sanitization). This logic cannot be reused without duplication.

### Evidence

**`routers/public.py:310-370`** — Direct agent call, no tracking:
```python
async with httpx.AsyncClient(timeout=300.0) as client:
    response = await client.post(
        f"http://agent-{agent_name}:8000/api/task",
        json={"message": context_prompt, "timeout_seconds": 120}
    )
```

**Database confirmation** — Zero public executions recorded:
```sql
SELECT triggered_by, COUNT(*) FROM schedule_executions GROUP BY triggered_by;
-- schedule: 829, manual: 643, agent: 146, mcp: 33
-- (no "public" entries)
```

## Solution: Task Execution Service

Extract execution orchestration into `services/task_execution_service.py`. Routers become thin wrappers that handle their specific concerns (auth, link validation, session management) then delegate to the service.

### Architecture

```
Before (duplicated / missing):
┌──────────────┐     ┌─────────────────────────────────────────────────────┐
│ chat.py      │────▶│ Inline: create_execution → acquire_slot → track    │
│ /task        │     │ activity → call_agent → sanitize → update_execution│
└──────────────┘     │ → complete_activity → release_slot                  │
                     └─────────────────────────────────────────────────────┘

┌──────────────┐     ┌───────────────────────────────┐
│ public.py    │────▶│ Raw httpx call (no tracking)  │
│ /chat/{token}│     └───────────────────────────────┘
└──────────────┘

After (unified):
┌──────────────┐
│ chat.py      │──┐
│ (auth+headers│  │
└──────────────┘  │
                  ▼
┌──────────────┐  ┌────────────────────────────────────────────────┐
│ public.py    │─▶│ task_execution_service.execute_task()          │
│ (link+session│  │                                                │
└──────────────┘  │  1. create execution record                    │
                  │  2. acquire capacity slot                      │
┌──────────────┐  │  3. track activity start                       │
│ scheduler    │─▶│  4. call agent (with retry)                    │
│ (cron trigger│  │  5. sanitize + persist result                  │
└──────────────┘  │  6. track activity completion                  │
                  │  7. release slot (finally)                     │
                  └────────────────────────────────────────────────┘
```

## Requirements

### REQ-1: TaskExecutionService Class

Create `services/task_execution_service.py` with a stateless service class.

**File**: `src/backend/services/task_execution_service.py`

```python
@dataclass
class TaskExecutionResult:
    """Result of a task execution."""
    execution_id: str
    status: str                    # "success" | "failed"
    response: str                  # Sanitized response text
    cost: Optional[float]
    context_used: Optional[int]
    context_max: Optional[int]
    session_id: Optional[str]      # Claude Code session ID
    execution_log: Optional[str]   # Sanitized JSON transcript
    raw_response: dict             # Full agent response for callers that need it
    error: Optional[str]           # Error message if failed


class TaskExecutionService:
    async def execute_task(
        self,
        agent_name: str,
        message: str,
        triggered_by: str,               # "manual" | "public" | "schedule" | "agent" | "mcp"
        source_user_id: Optional[int],
        source_user_email: Optional[str],
        source_agent_name: Optional[str],
        source_mcp_key_id: Optional[str],
        source_mcp_key_name: Optional[str],
        model: Optional[str],
        timeout_seconds: int = 120,
        resume_session_id: Optional[str],
        allowed_tools: Optional[list],
        system_prompt: Optional[str],
    ) -> TaskExecutionResult:
        ...
```

The method performs the full lifecycle:
1. `db.create_task_execution()` — create execution record
2. `slot_service.acquire_slot()` — respect capacity limits
3. `activity_service.track_activity()` — emit `CHAT_START` for dashboard/timeline
4. `agent_post_with_retry()` — call agent's `/api/task` with retry
5. `sanitize_execution_log()` / `sanitize_response()` — credential scrubbing
6. `db.update_execution_status()` — persist result with full metadata
7. `activity_service.complete_activity()` — mark activity done/failed
8. `slot_service.release_slot()` — always release in `finally`

Errors (timeout, HTTP errors) follow the same pattern as `chat.py`: update execution to `"failed"`, complete activity with error, release slot, then raise.

### REQ-2: Refactor chat.py execute_parallel_task

The authenticated endpoint becomes a thin wrapper.

**File**: `src/backend/routers/chat.py`

```python
@router.post("/{name}/task")
async def execute_parallel_task(name, request, current_user, ...):
    # 1. Validate container exists + running
    # 2. Determine triggered_by from headers
    # 3. Handle collaboration tracking (agent-to-agent only)
    # 4. Call task_execution_service.execute_task(...)
    # 5. Handle async_mode (background task spawning)
    # 6. Handle save_to_session (chat persistence)
    # 7. Return response
```

Collaboration tracking (source agent WebSocket events) stays in the router because it's specific to the agent-to-agent use case. The `async_mode` and `save_to_session` features also stay in the router as they're caller-specific concerns.

### REQ-3: Refactor public.py public_chat

The public endpoint delegates to the service after its link/session validation.

**File**: `src/backend/routers/public.py`

```python
@router.post("/chat/{token}")
async def public_chat(token, chat_request, request):
    # 1. Validate link token
    # 2. Verify session / determine identity
    # 3. Rate limiting
    # 4. Check agent available
    # 5. Get/create public chat session
    # 6. Store user message in public_chat_messages
    # 7. Build context prompt
    # 8. Call task_execution_service.execute_task(
    #        triggered_by="public",
    #        source_user_email=verified_email or f"anonymous ({client_ip})",
    #    )
    # 9. Store assistant response in public_chat_messages
    # 10. Return PublicChatResponse
```

### REQ-4: Move agent_post_with_retry to Service Layer

The retry helper currently lives in `routers/chat.py` as a module-level function. Move it to the service or to `services/agent_client.py` where it architecturally belongs.

**From**: `src/backend/routers/chat.py:27`
**To**: `src/backend/services/task_execution_service.py` (private method)

### REQ-5: Consistent triggered_by Values

Document and enforce the allowed values:

| Value | Source | Example |
|-------|--------|---------|
| `manual` | Authenticated user via UI or API | Tasks tab "Run" button |
| `public` | Public link visitor | Public chat page |
| `schedule` | Cron scheduler | APScheduler trigger |
| `agent` | Agent-to-agent via MCP | Orchestrator delegating |
| `mcp` | External MCP client (non-agent) | Claude Code client |

## Files Changed

| File | Change |
|------|--------|
| `src/backend/services/task_execution_service.py` | **New** — Core execution orchestration service |
| `src/backend/routers/chat.py` | Refactor `execute_parallel_task` to use service; move `agent_post_with_retry` |
| `src/backend/routers/public.py` | Replace direct agent call with service call |
| `src/backend/services/agent_client.py` | Optional: absorb `agent_post_with_retry` into `AgentClient` |

## Scope Boundaries

### In Scope
- Extract execution orchestration into service
- Public link executions appear in Tasks tab and Dashboard timeline
- Slot management for public executions
- Credential sanitization for public execution logs

### Out of Scope
- Scheduler service refactoring (uses `AgentClient.task()` — separate pattern)
- Async mode refactoring (stays in `chat.py` as caller-specific)
- Chat session persistence (`save_to_session` stays in `chat.py`)
- Agent-to-agent collaboration tracking (stays in `chat.py`)

## Backward Compatibility

- No API changes — all existing endpoints keep their signatures
- New `triggered_by="public"` value appears in execution records
- Public executions now count toward capacity slots (behavioral change, but correct)
- Dashboard timeline shows public executions (new, additive)

## Testing

### Test Case 1: Public Link Execution Appears in Tasks Tab
1. Open a public link and send a message
2. Log into main UI, navigate to the agent's Tasks tab
3. **Expected**: Execution appears with `triggered_by: public` and source email/IP
4. **Verify**: Execution has cost, duration, context usage, and execution log

### Test Case 2: Public Link Execution on Dashboard Timeline
1. Open a public link and send a message
2. Check Dashboard timeline view
3. **Expected**: Execution box appears for the agent with "public" trigger badge

### Test Case 3: Capacity Slot Enforcement
1. Set agent max parallel tasks to 1
2. Trigger a task via authenticated UI
3. While running, send a message via public link
4. **Expected**: Public link returns 429 "Agent is busy"

### Test Case 4: Authenticated Tasks Still Work
1. Run a task via the Tasks tab
2. **Expected**: Execution appears with same metadata as before (no regression)

### Test Case 5: Credential Sanitization
1. Send a public message that triggers agent tool use
2. Check execution log in Tasks tab
3. **Expected**: No credentials visible in execution transcript

## Related Flows

- **Primary**: [tasks-tab.md](../memory/feature-flows/tasks-tab.md)
- **Related**: [public-agent-links.md](../memory/feature-flows/public-agent-links.md)
- **Related**: [parallel-capacity.md](../memory/feature-flows/parallel-capacity.md)
- **Related**: [dashboard-timeline-view.md](../memory/feature-flows/dashboard-timeline-view.md)

## Revision History

| Date | Changes |
|------|---------|
| 2026-03-04 | Initial requirements document |
