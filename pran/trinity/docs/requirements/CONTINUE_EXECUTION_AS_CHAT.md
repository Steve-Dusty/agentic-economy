# Continue Execution as Chat (EXEC-023)

> **Status**: IMPLEMENTED
> **Priority**: MEDIUM
> **Created**: 2026-02-20
> **Author**: Eugene / Claude

## Overview

Enable users to continue a failed or completed execution as an interactive chat conversation with full context preservation. When an execution fails or produces unexpected results, users can click "Continue as Chat" to resume the Claude Code session with all prior context intact, allowing them to investigate, fix issues, and continue the work interactively.

## Problem Statement

When an execution fails or produces unexpected results:
1. **Context is lost** - The execution transcript is view-only; users cannot follow up
2. **Manual reproduction required** - Users must copy/paste context to start a new chat
3. **No session continuity** - Starting fresh loses the agent's understanding of what happened
4. **Large context overhead** - Execution transcripts can be 150K+ tokens, impossible to copy into a new chat

Users need a way to seamlessly transition from viewing an execution to interacting with the agent about that specific execution, preserving full context.

## User Stories

1. **As an agent operator**, I want to click "Continue as Chat" on a failed execution so I can ask the agent what went wrong and fix it together.
2. **As a developer**, I want to continue a partially successful execution to complete the remaining work without re-explaining context.
3. **As a debugging user**, I want the full execution history available in chat so the agent remembers every tool call, error, and decision from the execution.

## Solution: Claude Code Session Resume

### Key Insight

Claude Code stores complete session history on disk at:
```
~/.claude/projects/{project-path}/{session_id}.jsonl
```

Each execution already returns a `session_id` from Claude Code. By storing this ID and using `--resume {session_id}`, we can continue the exact session with full context - no copying or injection needed.

### Architecture

```
┌───────────────────┐     ┌───────────────────┐     ┌──────────────────────┐
│ Execution runs    │────▶│ Claude Code runs  │────▶│ Session stored at    │
│ via /task         │     │ returns session_id│     │ ~/.claude/projects/  │
└───────────────────┘     └───────────────────┘     │ {path}/{session}.jsonl│
                                                     └──────────────────────┘
         │                                                     │
         ▼                                                     │
┌───────────────────┐                                          │
│ Store claude_     │                                          │
│ session_id in     │                                          │
│ schedule_executions│                                          │
└───────────────────┘                                          │
         │                                                     │
         ▼                                                     ▼
┌───────────────────┐     ┌───────────────────┐     ┌──────────────────────┐
│ User clicks       │────▶│ /task with        │────▶│ claude --resume      │
│ "Continue as Chat"│     │ resume_session_id │     │ {session_id} -p ...  │
└───────────────────┘     └───────────────────┘     └──────────────────────┘
```

### Why This Approach

| Approach | Pros | Cons |
|----------|------|------|
| **Copy context to new chat** | Simple | 150K tokens won't fit in request, loses tool results |
| **Inject context via API** | Backend controls | Duplicates data, complex injection logic |
| **Resume Claude session** ✓ | Native, complete, efficient | Requires session_id storage |

## Requirements

### REQ-1: Store Claude Session ID in Executions

Add `claude_session_id` column to `schedule_executions` table.

**Database Migration**:
```sql
ALTER TABLE schedule_executions ADD COLUMN claude_session_id TEXT;
```

**Capture Point**: When execution completes, store the `session_id` from Claude Code's response metadata.

### REQ-2: Agent Server Resume Support

Add `resume_session_id` parameter to agent server's `/api/task` endpoint.

**Current behavior**:
```bash
# Stateless - no session continuity
claude -p "message" --output-format stream-json
```

**New behavior when `resume_session_id` provided**:
```bash
# Resume specific Claude Code session
claude -p "message" --resume {session_id} --output-format stream-json
```

**Request Model Update**:
```python
class TaskRequest(BaseModel):
    message: str
    # ... existing fields ...
    resume_session_id: Optional[str] = None  # NEW: Claude session to resume
```

### REQ-3: Backend Pass-Through

Backend `/api/agents/{name}/task` endpoint passes `resume_session_id` to agent server.

**Data Flow**:
```
Frontend → POST /api/agents/{name}/task
           { message: "What went wrong?", resume_session_id: "abc123" }
              ↓
           Backend validates user has access to agent
              ↓
           POST http://agent:8000/api/task
           { message: "What went wrong?", resume_session_id: "abc123" }
              ↓
           Agent server uses: claude --resume abc123 -p "What went wrong?"
```

### REQ-4: Frontend "Continue as Chat" Button

Add button to `ExecutionDetail.vue` that:
1. Is visible for any execution with `claude_session_id`
2. Navigates to Chat tab with context
3. Pre-populates first message (optional)

**Button Location**: Quick actions area in ExecutionDetail header (alongside "Stop" and "Copy ID")

**Button Design**:
```vue
<button
  v-if="execution?.claude_session_id"
  @click="continueAsChat"
  class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg flex items-center gap-2"
>
  <ChatBubbleIcon class="w-4 h-4" />
  Continue as Chat
</button>
```

### REQ-5: Chat Tab Resume Mode

When navigating to Chat tab with `resumeSessionId` query param:

1. **Show context banner**: "Continuing from execution {execution_id}"
2. **First message uses resume**: Pass `resume_session_id` to `/task` endpoint
3. **Subsequent messages**: Continue normally with `--continue`

**Navigation**:
```javascript
router.push({
  name: 'AgentDetail',
  params: { name: agentName },
  query: {
    tab: 'chat',
    resumeSessionId: execution.claude_session_id,
    executionId: execution.id
  }
})
```

### REQ-6: ChatPanel Resume Handling

Modify `ChatPanel.vue` to:

1. **Detect resume mode**: Check for `resumeSessionId` in route query
2. **Show resume banner**: Display which execution we're continuing
3. **First message handling**: Include `resume_session_id` in `/task` request
4. **Clear resume mode**: After first message, subsequent messages are normal

**State**:
```javascript
const resumeSessionId = ref(null)  // From route query
const resumeExecutionId = ref(null)  // For display purposes
const isResumeMode = computed(() => !!resumeSessionId.value)
```

## Files to Modify

### Database

| File | Changes |
|------|---------|
| `src/backend/database.py` | Add migration for `claude_session_id` column |

### Backend Models

| File | Changes |
|------|---------|
| `src/backend/db_models.py` | Add `claude_session_id` to `ScheduleExecution` model |
| `src/backend/models.py` | Add `resume_session_id` to `ParallelTaskRequest` |

### Backend Routers

| File | Changes |
|------|---------|
| `src/backend/routers/chat.py` | Store `session_id` in execution, pass `resume_session_id` to agent |
| `src/backend/db/schedules.py` | Update `create_task_execution()` to accept `claude_session_id` |

### Agent Server

| File | Changes |
|------|---------|
| `docker/base-image/agent_server/models.py` | Add `resume_session_id` to `TaskRequest` |
| `docker/base-image/agent_server/routers/chat.py` | Pass `resume_session_id` to runtime |
| `docker/base-image/agent_server/services/claude_code.py` | Use `--resume` when `resume_session_id` provided |

### Frontend

| File | Changes |
|------|---------|
| `src/frontend/src/views/ExecutionDetail.vue` | Add "Continue as Chat" button |
| `src/frontend/src/components/ChatPanel.vue` | Handle `resumeSessionId` query param |
| `src/frontend/src/views/AgentDetail.vue` | Parse and pass resume query params |

## Implementation Phases

### Phase 1: Database & Storage (Backend)
1. Add `claude_session_id` column migration
2. Update `create_task_execution()` to accept and store session ID
3. Update `/task` endpoint to capture `session_id` from agent response
4. Update `ScheduleExecution` model

**Estimated lines**: ~30

### Phase 2: Agent Server Resume Support
1. Add `resume_session_id` to `TaskRequest` model
2. Update `execute_headless_task()` to use `--resume` when provided
3. Update `/api/task` endpoint to pass through parameter

**Estimated lines**: ~20

### Phase 3: Backend Pass-Through
1. Add `resume_session_id` to `ParallelTaskRequest` model
2. Pass through in `/task` endpoint

**Estimated lines**: ~10

### Phase 4: Frontend Integration
1. Add "Continue as Chat" button to `ExecutionDetail.vue`
2. Update `ChatPanel.vue` to handle resume mode
3. Show context banner when in resume mode

**Estimated lines**: ~50

## Testing

### Test Cases

1. **Execute task, verify session_id stored**: Run a task, check `schedule_executions.claude_session_id` is populated
2. **Resume from failed execution**: Click "Continue as Chat" on failed execution, verify context is preserved
3. **Resume from successful execution**: Click "Continue as Chat" on completed execution, ask follow-up question
4. **Session file exists**: Verify `~/.claude/projects/{path}/{session_id}.jsonl` exists on agent
5. **Multiple resumes**: Resume same execution multiple times, verify each continues correctly
6. **Missing session file**: Handle case where session file was deleted (graceful fallback)

### Manual Testing Flow

1. Run a task that will fail (e.g., "Edit file that doesn't exist")
2. Go to Execution Detail page
3. Click "Continue as Chat"
4. Verify navigation to Chat tab with banner
5. Send message: "What went wrong?"
6. Verify agent has full context of the failed execution

## Edge Cases

### Session File Deleted
If the session file no longer exists on the agent:
- Claude Code will fail to resume
- Fallback: Start fresh session, inject execution summary as context

### Agent Restarted
Session files are stored in agent workspace which persists across restarts:
- `~/.claude/projects/` is inside `/home/developer/` (persisted volume)
- Sessions should survive agent restarts

### Very Old Executions
Over time, session files may be cleaned up by Claude Code:
- Check if `claude_session_id` is set but resume fails
- Show user-friendly error: "Session expired, starting fresh"

## Security Considerations

1. **Session isolation**: Each agent has its own session files, no cross-agent access
2. **User authorization**: Only users with agent access can continue executions
3. **No credential exposure**: Session files may contain tool outputs but credentials are already sanitized

## UX Considerations

### Button Visibility
- Show "Continue as Chat" for ALL executions with `claude_session_id` (not just failed)
- Users may want to continue successful executions to do more work

### Resume Banner
When in resume mode, show a dismissible banner:
```
ℹ️ Continuing from execution abc123 (failed 5 minutes ago)
   The agent has full context from that execution.
   [Dismiss]
```

### Input Placeholder
In resume mode, show helpful placeholder:
```
Ask about the execution or continue the work...
```

## Success Criteria

1. Users can click "Continue as Chat" on any execution with a session ID
2. The resumed chat has full context from the original execution
3. Users can ask "What went wrong?" and get accurate answers referencing the execution
4. No manual copying of context is required
5. Works with execution transcripts up to 150K tokens

## Related Requirements

- **CHAT-001 (Authenticated Chat Tab)**: Chat tab infrastructure used for resume
- **EXEC-022 (Unified Executions Dashboard)**: Will show "Continue as Chat" action
- **AUDIT-001 (Execution Origin Tracking)**: Already implemented, tracks execution source

## Open Questions

1. **Should resumed chats create a Trinity chat_session?**
   - Recommendation: Yes, for persistence and history
   - The Trinity session links to the Claude session via `source_execution_id`

2. **Should we show execution context in chat history?**
   - Recommendation: No, the agent has context internally
   - Show only the user's follow-up messages and agent responses

3. **What if user has the Chat tab open when clicking button?**
   - Recommendation: Navigate to Chat tab, start fresh resume (don't mix with existing conversation)
