# Phase 20: Live Execution Streaming

> **Purpose**: Validate real-time execution log streaming, Live indicator, and stop functionality
> **Duration**: ~20 minutes
> **Assumes**: Phase 2 PASSED (agents running), Phase 7 PASSED (scheduling works)
> **Output**: Live streaming, stop button, and queue release verified

---

## Background

**Live Execution Streaming** (EXEC-009 to EXEC-013):
- Real-time SSE streaming of Claude Code execution logs
- "Live" indicator with green pulsing badge for running tasks
- Auto-scroll behavior during streaming
- Stop button terminates execution with SIGINT/SIGKILL
- Queue automatically releases after termination

**User Stories**:
- EXEC-009: Real-time execution logs (SSE)
- EXEC-010: "Live" indicator for running tasks
- EXEC-011: Auto-scroll during streaming
- EXEC-012: Stop running execution
- EXEC-013: See which executions are running

---

## Prerequisites

- [ ] Phase 2 PASSED (agents created and running)
- [ ] At least one agent available for testing
- [ ] Phase 7 PASSED (scheduling works) for scheduled task tests

---

## Test: Trigger Long-Running Task

### Step 1: Navigate to Agent Detail
**Action**:
- Go to http://localhost/agents
- Click on any running agent (e.g., test-echo)
- Wait for detail page to load

**Expected**:
- [ ] Agent detail page loads
- [ ] Tasks tab visible
- [ ] Agent status: Running

---

### Step 2: Create Long-Running Task
**Action**:
- Click "Tasks" tab
- Click "Create Task" or "+ Task" button
- Enter task message: "Write a detailed 500-word essay about the history of computing. Take your time and be thorough."
- Click "Run" or "Execute"

**Expected**:
- [ ] Task submission accepted
- [ ] Task appears in task list
- [ ] Status shows "Running" or spinner

**Verify**:
- [ ] Task ID generated
- [ ] Timestamp recorded
- [ ] No errors

---

## Test: Live Indicator

### Step 3: Verify Live Button Appears
**Action**:
- Look at the running task in Tasks panel
- Find the "Live" button/badge

**Expected**:
- [ ] Green pulsing badge visible
- [ ] "Live" text or icon displayed
- [ ] Badge animates (pulsing/breathing effect)
- [ ] Badge only appears for running tasks

**Verify**:
- [ ] Completed tasks do NOT have Live badge
- [ ] Pending tasks do NOT have Live badge
- [ ] Only running tasks show Live

---

### Step 4: Click Live Button
**Action**:
- Click the "Live" button on the running task
- Wait for navigation

**Expected**:
- [ ] Navigates to Execution Detail page
- [ ] URL pattern: `/agents/{name}/executions/{id}`
- [ ] Page shows execution metadata

**Verify**:
- [ ] Correct execution ID in URL
- [ ] Page title matches task

---

## Test: Real-Time Streaming

### Step 5: Verify SSE Streaming Active
**Action**:
- On Execution Detail page, observe the log area
- Watch for new log entries appearing

**Expected**:
- [ ] "Live" indicator at top of page
- [ ] Log entries appear in real-time
- [ ] No page refresh needed
- [ ] Entries stream as Claude Code runs

**Verify**:
- [ ] DevTools Network tab shows EventSource connection
- [ ] Connection type: `text/event-stream`
- [ ] Events arriving continuously

---

### Step 6: Verify Log Entry Types
**Action**:
- Watch the streaming log entries
- Identify different entry types

**Expected Entry Types**:
- [ ] `init` - Session initialization
- [ ] `assistant-text` - Claude's text responses
- [ ] `tool-call` - Tool invocations (Read, Write, Bash, etc.)
- [ ] `tool-result` - Tool outputs
- [ ] `result` - Final completion

**Verify**:
- [ ] Each entry has timestamp
- [ ] Tool calls show tool name
- [ ] Text entries show content

---

### Step 7: Verify Auto-Scroll
**Action**:
- Let log entries accumulate
- Observe scroll behavior

**Expected**:
- [ ] Log area auto-scrolls as new entries arrive
- [ ] Latest entry always visible
- [ ] Smooth scrolling (not jumpy)

**Manual Scroll Test**:
- [ ] Scroll up manually
- [ ] Auto-scroll pauses when user scrolls up
- [ ] Auto-scroll resumes when scrolled to bottom

---

## Test: Stop Running Execution

### Step 8: Find Stop Button
**Action**:
- On Execution Detail page (while task running)
- Or: Go back to Tasks panel
- Look for Stop button on running task

**Expected**:
- [ ] Stop button visible (red icon)
- [ ] Button only enabled for running tasks
- [ ] Tooltip: "Stop execution"

---

### Step 9: Stop the Execution
**Action**:
- Click Stop button
- Confirm if prompted
- Wait 5-10 seconds

**Expected**:
- [ ] Confirmation dialog (if implemented)
- [ ] Button shows loading state
- [ ] Execution terminates
- [ ] Status changes to "Cancelled" or "Stopped"

**Verify**:
- [ ] Task no longer running
- [ ] Live indicator disappears
- [ ] Final log entry shows termination

---

### Step 10: Verify Queue Release
**Action**:
- Check execution queue status
- Try to start another task

**Expected**:
- [ ] Queue slot released
- [ ] New task can start immediately
- [ ] No "agent busy" error

**API Check**:
```bash
# Check queue status
curl http://localhost:8000/api/agents/{name}/executions/queue
```

---

### Step 11: Verify Termination Signal Flow
**Action**:
- Check agent logs for termination signals

**Expected Signal Flow**:
1. SIGINT sent (graceful termination)
2. 5 second timeout
3. SIGKILL if needed (force termination)

```bash
# Check agent logs
docker logs agent-test-echo | grep -i "signal\|SIGINT\|SIGKILL\|terminate"
```

---

## Test: Running Task Visibility

### Step 12: Check Running Tasks Across Agents
**Action**:
- Start tasks on multiple agents
- Navigate to Dashboard or Agents page

**Expected**:
- [ ] Running tasks visible per agent
- [ ] Task count displayed
- [ ] Visual indicator for agents with running tasks

**Verify**:
- [ ] Can identify which agents have work in progress
- [ ] Execution stats update

---

### Step 13: Entry Points to Live View
**Action**:
- Test multiple entry points to Execution Detail

**Entry Points**:
1. **Tasks Panel**: Click "Live" badge on running task
2. **Tasks Panel**: Click external link icon on any task
3. **Timeline View**: Click on execution bar (if Dashboard Timeline enabled)

**Expected**:
- [ ] All entry points navigate to same Execution Detail page
- [ ] Correct execution ID passed
- [ ] Streaming works from any entry point

---

## Test: Late Joiner Support

### Step 14: Join Running Execution Late
**Action**:
- Start a long-running task
- Wait 30 seconds
- Open new browser tab
- Navigate to the execution detail page

**Expected**:
- [ ] Buffered entries loaded (catch-up)
- [ ] Previous log entries visible
- [ ] Live streaming continues from current point
- [ ] No missing entries

**Verify**:
- [ ] Late joiner sees complete log history
- [ ] SSE connection established
- [ ] Real-time updates continue

---

## Test: Execution After Completion

### Step 15: View Completed Execution
**Action**:
- Let an execution complete naturally
- Or: Navigate to a completed task
- Click on the task to view details

**Expected**:
- [ ] "Live" indicator NOT present
- [ ] Full transcript available
- [ ] All log entries visible
- [ ] Metadata shows completion status

**Verify**:
- [ ] Duration displayed
- [ ] Cost displayed (if applicable)
- [ ] No streaming (static view)

---

## Critical Validations

### SSE Connection Health
**Validation**: Verify SSE connection is stable

```bash
# Check for EventSource in browser console
# Or use curl to test SSE endpoint
curl -N http://localhost:8000/api/agents/{name}/executions/{id}/stream
```

### Activity Record Created
**Validation**: Termination creates activity record

- [ ] Check `agent_activities` table for `EXECUTION_CANCELLED` type
- [ ] Activity linked to execution ID
- [ ] Timestamp accurate

---

## Success Criteria

Phase 20 is **PASSED** when:
- [ ] Long-running task can be started
- [ ] "Live" green pulsing badge appears for running tasks
- [ ] Clicking Live navigates to Execution Detail page
- [ ] SSE streaming shows real-time log entries
- [ ] All log entry types display correctly
- [ ] Auto-scroll works during streaming
- [ ] Manual scroll pauses auto-scroll
- [ ] Stop button terminates execution
- [ ] Queue releases after termination
- [ ] Multiple entry points work (Tasks, Timeline)
- [ ] Late joiners see buffered entries
- [ ] Completed executions show full transcript

---

## Troubleshooting

**Live badge doesn't appear**:
- Task may have completed too quickly
- Use longer-running task
- Check task status in API

**SSE not streaming**:
- Check browser supports EventSource
- Verify SSE endpoint exists
- Check backend logs for SSE errors
- Verify agent-server has streaming endpoint

**Stop doesn't work**:
- Check process registry has execution
- Verify SIGINT handling in agent
- Check backend proxy endpoint
- Review termination signal flow in logs

**Queue not releasing**:
- Check Redis queue state
- Verify `complete()` called after termination
- Check for race conditions

**Missing log entries**:
- Check buffer size in agent-server
- Verify SSE message format
- Check for JSON parse errors

---

## Next Phase

Once Phase 20 is **PASSED**, proceed to:
- **Phase 21**: Session Management

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
**User Stories**: EXEC-009, EXEC-010, EXEC-011, EXEC-012, EXEC-013
