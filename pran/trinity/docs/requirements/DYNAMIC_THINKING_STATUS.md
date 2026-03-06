# Dynamic Thinking Status Labels in Agent Chat

> **Requirement ID**: THINK-001
> **GitHub Issue**: #41
> **Priority**: P1
> **Status**: Ready for Implementation

## Problem

When a user sends a message in the Chat tab, they see a static "Thinking..." label with bouncing dots for the entire duration (30s to several minutes). No insight into what the agent is actually doing. This feels unengaging and provides no trust signal that work is happening.

## Solution

Replace the static "Thinking..." indicator with dynamically changing, human-readable status labels that reflect the agent's actual activity in real-time. Examples: "Reading file...", "Searching code...", "Writing implementation...", "Running tests..."

## Architecture

### Current State

The Chat tab uses a **synchronous request-response** pattern:

```
User sends message
    → POST /api/agents/{name}/task (waits for completion)
    → loading = true → static "Thinking..." shown
    → response arrives → loading = false → message displayed
```

Meanwhile, the agent-side **already streams execution events** in real-time:
- Claude Code runs with `--output-format stream-json`
- Each line is published via `ProcessRegistry.publish_log_entry(execution_id, msg)`
- SSE endpoint exists at `/api/executions/{execution_id}/stream`
- Backend proxy exists at `/api/agents/{name}/executions/{execution_id}/stream`
- `ExecutionDetail.vue` already renders these events live

**The streaming infrastructure exists — it just isn't wired to the Chat tab.**

### Proposed Architecture

```
User sends message in Chat tab
    ↓
POST /api/agents/{name}/task (async_mode=true)
    ↓ returns immediately with { execution_id, status: "accepted" }
    ↓
ChatPanel opens SSE connection:
  GET /api/agents/{name}/executions/{execution_id}/stream
    ↓
Parse incoming stream-json events → update status label
    ↓
On "result" event → fetch final response, display message
```

## Stream-JSON Event → Status Label Mapping

| Stream Event | Content Block | Status Label |
|---|---|---|
| `type: "init"` | — | "Starting session..." |
| `type: "assistant"` | `content[].type: "thinking"` | "Thinking..." |
| `type: "assistant"` | `content[].type: "text"` | "Responding..." |
| `type: "assistant"` | `content[].type: "tool_use"` | Mapped by tool name (see below) |
| `type: "user"` | `content[].type: "tool_result"` | "Processing results..." |
| `type: "result"` | — | Hide indicator, show response |

### Tool Name → Label Map

| Tool Name | Status Label |
|---|---|
| `Read` | "Reading file..." |
| `Grep` | "Searching code..." |
| `Glob` | "Finding files..." |
| `Bash` | "Running command..." |
| `Edit` | "Editing code..." |
| `Write` | "Writing file..." |
| `WebSearch` | "Searching web..." |
| `WebFetch` | "Fetching page..." |
| `Task` | "Delegating to agent..." |
| `NotebookEdit` | "Editing notebook..." |
| `mcp__*` | "Using {server}..." (extract server name from prefix) |
| (unknown) | "Working..." |

## Implementation Plan

### Phase 1: Frontend — SSE Status Subscription

**File: `src/frontend/src/components/ChatPanel.vue`**

1. Switch from synchronous `axios.post()` to async flow:
   - POST `/api/agents/{name}/task` with `async_mode: true`
   - Receive `{ execution_id, status: "accepted" }` immediately
   - Open SSE stream to `/api/agents/{name}/executions/{execution_id}/stream`
2. Parse each SSE `data:` line for status-relevant events
3. Update a reactive `statusText` ref on each relevant event
4. Poll or listen for execution completion to get the final response
5. On completion: fetch response from `GET /api/agents/{name}/executions/{execution_id}` and display

**File: `src/frontend/src/components/chat/ChatLoadingIndicator.vue`**

Already accepts a `text` prop — no changes needed to the component itself.

**File: `src/frontend/src/components/chat/ChatMessages.vue`**

Pass dynamic `loadingText` from ChatPanel instead of static "Thinking...".

### Phase 2: Status Label Utility

**New file: `src/frontend/src/utils/execution-status.js`**

```javascript
const TOOL_STATUS_MAP = {
  Read: 'Reading file...',
  Grep: 'Searching code...',
  Glob: 'Finding files...',
  Bash: 'Running command...',
  Edit: 'Editing code...',
  Write: 'Writing file...',
  WebSearch: 'Searching web...',
  WebFetch: 'Fetching page...',
  Task: 'Delegating to agent...',
  NotebookEdit: 'Editing notebook...',
}

export function getStatusFromStreamEvent(event) {
  if (event.type === 'init') return 'Starting session...'
  if (event.type === 'result') return null // done

  const content = event.message?.content || []
  for (const block of content) {
    if (block.type === 'thinking') return 'Thinking...'
    if (block.type === 'text') return 'Responding...'
    if (block.type === 'tool_use') {
      const name = block.name || ''
      if (name.startsWith('mcp__')) {
        const server = name.split('__')[1] || 'tool'
        return `Using ${server}...`
      }
      return TOOL_STATUS_MAP[name] || 'Working...'
    }
    if (block.type === 'tool_result') return 'Processing results...'
  }
  return null // no status change
}
```

### Phase 3: Backend — Return Execution ID for Chat Tasks

**File: `src/backend/routers/chat.py`**

The `/task` endpoint already supports `async_mode=True` which returns `execution_id` immediately. Verify this works correctly with `save_to_session=True` (chat persistence).

If async_mode doesn't support session saving, add a completion callback that:
1. Fetches the final response from the agent
2. Saves to `chat_sessions` / `chat_messages` tables
3. Broadcasts a WebSocket event `chat_response_ready` with the execution_id

### Phase 4: Completion Detection

Two options for detecting when the execution finishes:

**Option A (preferred): SSE stream_end event**
- The SSE stream already emits `{"type": "stream_end"}` when execution completes
- ChatPanel detects this, then fetches response from execution record

**Option B: Polling fallback**
- Poll `GET /api/agents/{name}/executions/{execution_id}` every 2s
- When `status` changes to `completed`, read the response

### Phase 5: PublicChat Integration

**File: `src/frontend/src/views/PublicChat.vue`**

Apply the same pattern:
1. POST to public chat endpoint
2. If execution_id is returned, subscribe to SSE for status
3. Update `chatLoading` text dynamically

Note: Public chat uses a different endpoint (`/api/public/chat/{token}`) which may need a new SSE proxy route for unauthenticated streaming.

## Files to Modify

| Layer | File | Change |
|---|---|---|
| Frontend | `src/frontend/src/components/ChatPanel.vue` | Async submission + SSE status subscription |
| Frontend | `src/frontend/src/components/chat/ChatMessages.vue` | Pass dynamic loadingText |
| Frontend | `src/frontend/src/components/chat/ChatLoadingIndicator.vue` | Add transition animation between labels |
| Frontend | `src/frontend/src/utils/execution-status.js` | **New** — status label mapping utility |
| Frontend | `src/frontend/src/views/PublicChat.vue` | Same pattern for public chat |
| Backend | `src/backend/routers/chat.py` | Ensure async_mode works with session persistence |

## Existing Infrastructure (No Changes Needed)

| Component | Location | Already Does |
|---|---|---|
| Stream-JSON parsing | `agent_server/services/claude_code.py:266` | `process_stream_line()` — parses tool_use events |
| Live log publishing | `agent_server/services/process_registry.py:199` | `publish_log_entry()` — broadcasts to SSE subscribers |
| Agent SSE endpoint | `agent_server/routers/chat.py:300` | `/api/executions/{id}/stream` — SSE stream |
| Backend SSE proxy | `src/backend/routers/chat.py:1498` | `/api/agents/{name}/executions/{id}/stream` — authenticated proxy |
| Loading indicator | `components/chat/ChatLoadingIndicator.vue` | Accepts `text` prop (already dynamic) |

## UX Requirements

- Smooth CSS transition when label text changes (fade or slide)
- Minimum display time per label: 500ms (prevent flicker on fast tool calls)
- If no events received for 10s, fall back to "Working..." (heartbeat timeout)
- Label should show tool context when available (e.g., "Reading src/main.py..." from tool input)
- Bouncing dots animation continues alongside the dynamic text

## Edge Cases

- **Execution fails before streaming starts**: Fall back to static "Thinking...", show error on timeout
- **SSE connection drops**: Reconnect with late-joiner support (ProcessRegistry buffers entries)
- **Multiple rapid tool calls**: Show latest tool, don't queue labels
- **Agent container unreachable**: Timeout after 30s, show error
- **User sends another message while streaming**: Queue or block input until current completes

## Testing

### Prerequisites
- Backend + frontend running
- At least one agent running
- Logged in as authenticated user

### Test Steps

1. **Basic status cycling**
   - Send a message that triggers tool use (e.g., "read the README file")
   - Verify status changes from "Thinking..." → "Reading file..." → "Responding..."
   - Verify final response appears correctly

2. **Multi-tool execution**
   - Send a complex message (e.g., "find all Python files and count lines")
   - Verify multiple status transitions (Searching... → Running command... → Responding...)

3. **Long execution**
   - Send a task that takes >30s
   - Verify status keeps updating, no timeout

4. **Error handling**
   - Stop the agent mid-execution
   - Verify graceful error display

5. **Public chat**
   - Test same behavior on public chat link
