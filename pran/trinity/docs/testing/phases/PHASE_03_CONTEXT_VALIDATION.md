# Phase 3: Context Progress Bar Validation

> **Purpose**: Validate context % tracking via Tasks panel (API-based)
> **Duration**: ~5 minutes
> **Assumes**: Phase 2 PASSED (3 agents created, all running)
> **Output**: Context tracking behavior verified

---

## Important: Context Tracking Architecture

⚠️ **Context tracking ONLY works for `/api/chat` endpoint** (session-based conversations).

| Interaction Method | Tracks Context? | Why |
|-------------------|-----------------|-----|
| **Terminal** | ❌ NO | Direct PTY to Claude TUI, bypasses API |
| **Tasks Panel** | ❌ NO | Uses `/api/task` (stateless, no session) |
| **`/api/chat` API** | ✅ YES | Session-based, tracks cumulative tokens |

**For UI Testing**: Context tracking is not observable via Terminal or Tasks.
**For API Testing**: Use `/api/chat` endpoint directly.

---

## Prerequisites

- ✅ Phase 2 PASSED
- ✅ At least 1 agent running (test-echo)
- ✅ Agent shows status "running" (green)

---

## Test: Tasks Panel Functionality

Since context tracking requires `/api/chat` (not exposed in UI), this phase validates the Tasks panel works correctly.

### Step 1: Open Agent Detail Page
**Action**:
- Navigate to http://localhost/agents
- Click on test-echo agent card
- Click on **Tasks** tab

**Expected**:
- [ ] Tasks panel loads
- [ ] Shows task input field
- [ ] Shows "Run" button

---

### Step 2: Run a Task
**Action**:
- Enter message: "Hello World"
- Click "Run" button
- Wait for task to complete (5-10 seconds)

**Expected**:
- [ ] Task appears in history
- [ ] Status shows "success" (green)
- [ ] Response shows echo output
- [ ] Cost and duration displayed

---

### Step 3: Verify Task History
**Action**: Check the task list

**Expected**:
- [ ] Task entry visible with:
  - Status badge (success/error)
  - Trigger type (manual)
  - Timestamp
  - Duration
  - Cost

---

### Step 4: Run Multiple Tasks
**Action**: Run 2-3 more tasks with different messages

**Expected**:
- [ ] All tasks complete successfully
- [ ] Task history grows
- [ ] Stats update (Total, Success Rate, Total Cost, Avg Duration)

---

## Context Tracking via API (Optional)

To verify context tracking works, use direct API calls:

```bash
# Get auth token first (from browser localStorage or login)
TOKEN="your-jwt-token"

# Send message via /api/chat (tracks context)
curl -X POST "http://localhost:8000/api/agents/test-echo/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello World"}'

# Check context stats
curl "http://localhost:8000/api/agents/context-stats" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: `contextPercent` should be > 0 after sending messages via `/api/chat`.

---

## Success Criteria

Phase 3 is **PASSED** when:

- [ ] Tasks panel loads correctly
- [ ] Can run tasks via UI
- [ ] Task history displays correctly
- [ ] Task stats update properly

**Note**: Context % in header will show 0% because Tasks use `/api/task` (stateless).
This is expected behavior, not a bug.

---

## Next Phases

- **Phase 4**: State Persistence (test-counter)
- **Phase 5**: Agent-to-Agent Collaboration (test-delegator)
- **Phase 7**: Scheduling
- **Phase 8**: Execution Queue

---

**Status**: 🟢 UPDATED - Tests Tasks panel instead of Terminal-based context tracking
