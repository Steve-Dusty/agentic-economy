# Live Execution Streaming Requirements

> **Status**: ✅ Implemented (2026-01-13)
> **Created**: 2026-01-13
> **Related Features**: [execution-termination.md](../memory/feature-flows/execution-termination.md), [execution-detail-page.md](../memory/feature-flows/execution-detail-page.md)

## Overview

Enable real-time streaming of Claude Code execution logs to the Execution Detail page, allowing users to monitor task progress as it happens and interrupt execution mid-stream if needed.

## Problem Statement

### Current State

1. **Logs only available after completion**: The Execution Detail page (`/agents/{name}/executions/{id}`) currently fetches the execution log only AFTER the execution completes. For long-running tasks (10+ minutes), users have no visibility into progress.

2. **Termination is blind**: The Stop button (added 2026-01-12) allows terminating executions, but users cannot see what the agent is doing before deciding to stop. They're essentially "flying blind."

3. **Buffered output**: The agent server accumulates all `raw_messages` in memory and only returns them when the subprocess completes (`claude_code.py:676-688`). The streaming capability exists but isn't exposed.

### User Pain Points

- "What is my agent doing right now?"
- "Is it stuck or making progress?"
- "Should I stop this or let it continue?"
- "I want to interrupt before it makes a mistake"

## User Story

As an agent operator, I want to see the execution log updating in real-time while a task is running so that I can monitor progress and make informed decisions about whether to continue or terminate.

## Requirements

### Functional Requirements

#### FR1: Live Log Streaming on Execution Detail Page

- When navigating to `/agents/{name}/executions/{id}` for a **running** execution:
  - Automatically start streaming log entries as they are produced
  - Display each entry (assistant text, tool call, tool result) as it arrives
  - Auto-scroll to follow new entries (with option to disable)
  - Show "streaming" indicator while execution is in progress

- When execution completes:
  - Show completion indicator (success/failed/cancelled)
  - Display final stats (duration, cost, turns)
  - Stop streaming, show static log

#### FR2: Streaming Transport

- Use Server-Sent Events (SSE) for one-way streaming (simpler than WebSocket for this use case)
- Or use existing WebSocket infrastructure if more appropriate
- Must handle connection drops and reconnection gracefully

#### FR3: Integration with Termination

- Stop button remains visible during streaming
- After termination, stream shows final state and closes
- Cancelled status reflected immediately in UI

#### FR4: Entry Point from Running Task (Implemented 2026-01-13)

- [x] Tasks panel shows "Live" button for running tasks (green badge with pulsing dot)
- [x] Click navigates to Execution Detail page
- [ ] Streaming active on arrival (pending FR1-FR3 implementation)

**Implementation Details** (`TasksPanel.vue:213-232`):
- Visibility: `v-if="!task.id.startsWith('local-') || task.execution_id"`
- Route: Uses `task.id` for server executions, `task.execution_id` for local tasks
- Styling: Green background, "Live" label with `animate-pulse` dot for running tasks

### Non-Functional Requirements

#### NFR1: Latency

- Log entries should appear in UI within 500ms of being produced by Claude Code
- No batching/buffering delays

#### NFR2: Performance

- Streaming should not significantly increase backend memory usage
- Multiple concurrent streams (different users watching same execution) should be supported

#### NFR3: Security

- Same authorization as existing execution log endpoint
- Only users with agent access can stream logs

## Technical Analysis

### Current Architecture

```
Claude Code Subprocess
    │
    ├─► stdout (stream-json, line-by-line, REAL-TIME)
    │
    ▼
agent_server/services/claude_code.py
    │
    ├─► process_stream_line() - parses each line as it arrives
    ├─► raw_messages.append() - BUFFERS in memory
    │
    ▼ (only after subprocess completes)
    │
Agent Server /api/task response
    │
    ▼
Backend /api/agents/{name}/task
    │
    ├─► db.update_execution_status() - stores execution_log
    │
    ▼
Database (schedule_executions.execution_log)
    │
    ▼ (only on subsequent request)
    │
GET /api/agents/{name}/executions/{id}/log
    │
    ▼
Frontend ExecutionDetail.vue
```

### Proposed Architecture

```
Claude Code Subprocess
    │
    ├─► stdout (stream-json, line-by-line)
    │
    ▼
agent_server/services/claude_code.py
    │
    ├─► process_stream_line()
    ├─► raw_messages.append() (still buffer for final response)
    ├─► NEW: push to streaming endpoint/channel
    │
    ▼
Agent Server NEW: GET /api/executions/{id}/stream (SSE)
    │
    ▼
Backend NEW: GET /api/agents/{name}/executions/{id}/stream
    │
    ▼
Frontend ExecutionDetail.vue (EventSource or WebSocket)
```

### Key Implementation Points

#### 1. Agent Server Changes (`docker/base-image/agent_server/`)

**Option A: SSE Endpoint**
```python
# New endpoint: GET /api/executions/{execution_id}/stream
@router.get("/api/executions/{execution_id}/stream")
async def stream_execution_log(execution_id: str):
    """SSE endpoint streaming log entries as they arrive."""
    async def event_generator():
        registry = get_process_registry()
        # Subscribe to log entries for this execution
        async for entry in registry.subscribe_logs(execution_id):
            yield f"data: {json.dumps(entry)}\n\n"
        yield "data: {\"type\": \"stream_end\"}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Required Changes to ProcessRegistry**:
- Add `asyncio.Queue` per execution for log entry publishing
- `claude_code.py` pushes entries to queue as they arrive
- Streaming endpoint consumes from queue

**Option B: WebSocket**
- Extend existing WebSocket infrastructure
- Add new message type `execution_log_entry`
- Frontend subscribes to specific execution ID

#### 2. Backend Proxy (`src/backend/routers/chat.py`)

```python
@router.get("/{name}/executions/{execution_id}/stream")
async def stream_execution_log(
    name: str,
    execution_id: str,
    current_user: User = Depends(get_current_user)
):
    """Proxy SSE stream from agent container."""
    # Validate access
    if not db.can_user_access_agent(current_user.username, name):
        raise HTTPException(status_code=403)

    # Proxy SSE from agent
    async def proxy_stream():
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"http://agent-{name}:8000/api/executions/{execution_id}/stream"
            ) as response:
                async for chunk in response.aiter_text():
                    yield chunk

    return StreamingResponse(proxy_stream(), media_type="text/event-stream")
```

#### 3. Frontend Changes (`src/frontend/src/views/ExecutionDetail.vue`)

```javascript
// When execution is running, connect to SSE
function startStreaming() {
  const eventSource = new EventSource(
    `/api/agents/${agentName.value}/executions/${executionId.value}/stream`,
    { headers: authStore.authHeader }  // Note: SSE doesn't support custom headers natively
  )

  eventSource.onmessage = (event) => {
    const entry = JSON.parse(event.data)
    if (entry.type === 'stream_end') {
      eventSource.close()
      loadExecution()  // Fetch final state
    } else {
      logEntries.value.push(entry)
    }
  }
}
```

**Note**: SSE doesn't support custom headers in browser. Solutions:
1. Use query param for token: `?token=...`
2. Use cookies for auth
3. Switch to WebSocket (supports headers)

### Challenges

1. **SSE Auth**: Browser's EventSource API doesn't support custom headers. Need to use cookie-based auth or query param token, or use WebSocket instead.

2. **Multiple Subscribers**: If multiple users view the same running execution, need to support multiple consumers of the log stream.

3. **Reconnection**: If user navigates away and back, need to replay missed entries (or start from where they left off).

4. **Partial Logs**: If streaming starts after execution began, need to send already-buffered entries first.

5. **Memory**: Long-running executions could accumulate large logs. May need to limit buffer size.

## Alternatives Considered

### 1. Polling

**Approach**: Frontend polls `GET /executions/{id}/log?offset=N` every 1-2 seconds.

**Pros**: Simpler, no new infrastructure
**Cons**: Wasteful, 1-2s latency, doesn't scale

### 2. WebSocket with Existing Infrastructure

**Approach**: Extend existing WebSocket (`/ws`) to broadcast log entries as `agent_execution_log` events.

**Pros**: Reuses existing connection, already handles auth
**Cons**: Mixes concerns (status broadcasts vs streaming data), may need per-execution subscriptions

### 3. Long Polling

**Approach**: Frontend makes request, server holds until new entries available.

**Pros**: Lower latency than polling, works with HTTP
**Cons**: Complex, connection management issues

## Recommendation

**Primary**: Use existing **WebSocket infrastructure** with a new message type:

```json
{
  "type": "execution_log_entry",
  "execution_id": "abc123",
  "entry": {
    "type": "assistant",
    "message": {...}
  }
}
```

**Rationale**:
- Already handles authentication
- Already has reconnection logic
- Frontend already connected during session
- Just needs subscription management per execution

**Flow**:
1. Frontend subscribes: sends `{"type": "subscribe_execution", "execution_id": "..."}`
2. Backend tracks subscriptions
3. Agent server pushes entries via internal API
4. Backend broadcasts to subscribed clients
5. Frontend unsubscribes on page leave or execution complete

## Scope & Phases

### Phase 1: Basic Streaming (MVP)

- [ ] Agent server: Add log entry queue per execution in ProcessRegistry
- [ ] Agent server: Push entries as they arrive in `claude_code.py`
- [ ] Agent server: New SSE or WebSocket endpoint for streaming
- [ ] Backend: Proxy streaming endpoint with auth
- [ ] Frontend: ExecutionDetail connects to stream when execution is running
- [ ] Frontend: Display entries as they arrive
- [ ] Frontend: Stop button works during streaming

### Phase 2: Robustness

- [ ] Handle reconnection (replay missed entries)
- [ ] Handle "join in progress" (send buffered entries first)
- [ ] Multiple subscriber support
- [ ] Memory limits on buffer

### Phase 3: Enhanced UX

- [ ] Auto-scroll toggle
- [ ] Live search/filter
- [ ] Pause streaming (buffer without displaying)
- [ ] Jump to specific tool call

## Dependencies

- Execution Termination feature (completed 2026-01-12) - provides process registry
- Execution Detail Page (completed 2026-01-10) - provides UI foundation

## Estimated Effort

| Component | Estimate |
|-----------|----------|
| Agent Server streaming infrastructure | 2-3 hours |
| Backend proxy endpoint | 1-2 hours |
| Frontend streaming UI | 2-3 hours |
| Testing & edge cases | 2-3 hours |
| **Total (Phase 1)** | **7-11 hours** |

## Open Questions

1. **WebSocket vs SSE**: WebSocket reuses existing infra but mixes concerns. SSE is cleaner but has auth challenges. Which do we prefer?

2. **Entry granularity**: Stream every line from Claude Code, or batch into logical units (e.g., complete tool call + result)?

3. **Partial message streaming**: Claude Code supports `--include-partial-messages` for token-by-token output. Do we want this level of granularity? (Probably not for MVP)

4. **Historical streams**: If user opens completed execution, should we offer "replay" of the stream, or just show static log?

## Related Documentation

- Claude Code CLI: `--output-format stream-json` produces real-time line-by-line JSON output
- Claude Code CLI: `--include-partial-messages` for token-by-token streaming (beyond scope)
- [Execution Queue](../memory/feature-flows/execution-queue.md) - execution lifecycle
- [Process Registry](../memory/feature-flows/execution-termination.md) - tracks running subprocesses

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-13 | Claude | FR4 implemented - "Live" button in Tasks panel for running tasks |
| 2026-01-13 | Claude | Initial requirements specification |
