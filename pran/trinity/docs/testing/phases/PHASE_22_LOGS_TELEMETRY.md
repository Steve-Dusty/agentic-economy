# Phase 22: Logs & Telemetry

> **Purpose**: Validate container logs viewing, CPU/memory telemetry, and observability features
> **Duration**: ~15 minutes
> **Assumes**: Phase 2 PASSED (agents running)
> **Output**: Logs and telemetry display verified

---

## Background

**Observability Features** (OBS-001 to OBS-007):
- View container logs for debugging
- Search and filter log content
- Real-time CPU and memory usage
- Context window percentage display
- Tool call tracking and statistics

**User Stories**:
- OBS-001: View container logs
- OBS-002: Search/filter logs
- OBS-003: See CPU/memory usage
- OBS-004: See context window percentage
- OBS-005: See real-time tool calls
- OBS-006: See tool call details
- OBS-007: See aggregated tool statistics

---

## Prerequisites

- [ ] Phase 2 PASSED (agents created and running)
- [ ] At least one agent with activity (messages sent)
- [ ] Agent has been running for at least 1 minute

---

## Test: Container Logs Display

### Step 1: Navigate to Logs Tab
**Action**:
- Go to http://localhost/agents
- Click on a running agent
- Click "Logs" tab

**Expected**:
- [ ] Logs tab loads
- [ ] Container logs displayed
- [ ] Logs show recent output
- [ ] Timestamps visible

**Verify**:
- [ ] Log content from container stdout/stderr
- [ ] Auto-scrolls to latest entries

---

### Step 2: Verify Log Content
**Action**:
- Read the displayed logs
- Look for expected entries

**Expected Log Types**:
- [ ] Startup messages
- [ ] Health check entries
- [ ] API request logs (if agent-server verbose)
- [ ] Claude Code execution output
- [ ] Error messages (if any)

**Verify**:
- [ ] Logs are readable
- [ ] Timestamps in consistent format
- [ ] Log levels visible (INFO, ERROR, etc.)

---

### Step 3: Test Log Refresh
**Action**:
- Send a message to the agent via Terminal
- Switch back to Logs tab
- Wait for auto-refresh (15s interval)

**Expected**:
- [ ] New log entries appear
- [ ] Recent activity visible in logs
- [ ] No manual refresh needed

**Verify**:
- [ ] Auto-refresh interval: ~15 seconds
- [ ] New entries appended

---

### Step 4: Test Log Search/Filter (if implemented)
**Action**:
- Look for search/filter input in Logs tab
- Enter search term: "error" or "claude"
- Apply filter

**Expected**:
- [ ] Logs filtered to matching entries
- [ ] Matched terms highlighted
- [ ] Clear filter restores all logs

**Note**: If search not implemented, skip and document as gap.

---

## Test: CPU/Memory Telemetry

### Step 5: Verify Header Telemetry Display
**Action**:
- On agent detail page, look at the header area
- Find CPU and memory indicators

**Expected**:
- [ ] CPU usage percentage displayed
- [ ] Memory usage displayed (MB or %)
- [ ] Values update periodically
- [ ] Sparkline charts (if implemented)

**Verify**:
- [ ] Stats refresh every ~10 seconds
- [ ] Values change with agent activity

---

### Step 6: Test Telemetry During Load
**Action**:
- Send a complex message to generate CPU load
- Watch telemetry values change

**Expected**:
- [ ] CPU spikes during processing
- [ ] Memory may increase during execution
- [ ] Values return to baseline after completion

**Verify**:
- [ ] Real-time updates reflect actual load
- [ ] No stale/cached values

---

### Step 7: Verify Host Telemetry in Dashboard
**Action**:
- Navigate to Dashboard (http://localhost/)
- Look at header/top area for host stats

**Expected** (if implemented):
- [ ] Host CPU usage displayed
- [ ] Host memory usage displayed
- [ ] Host disk usage displayed
- [ ] Aggregate container stats

**Verify**:
- [ ] Host stats independent of individual agents
- [ ] Updates periodically

---

## Test: Context Window Tracking

### Step 8: Verify Context Display
**Action**:
- On agent detail page, look for context indicator
- Check progress bar and percentage

**Expected**:
- [ ] Context percentage displayed (e.g., "15.5K / 200K")
- [ ] Progress bar visual
- [ ] Color-coded: Green (low) → Yellow → Orange → Red (high)

**Verify**:
- [ ] Percentage matches actual usage
- [ ] Progress bar fills proportionally

---

### Step 9: Test Context Growth
**Action**:
- Send several messages to agent
- Watch context percentage increase

**Expected**:
- [ ] Context % increases with each exchange
- [ ] Progress bar grows
- [ ] Color may change if significant increase

**Verify**:
- [ ] Context tracking accurate
- [ ] No stuck at 0% bug (Phase 3 issue)

---

## Test: Tool Call Tracking

### Step 10: Trigger Tool Calls
**Action**:
- Send message that requires tools: "Read the file CLAUDE.md and tell me what it says"
- Wait for response

**Expected**:
- [ ] Agent uses Read tool
- [ ] Tool call tracked in activity

---

### Step 11: Verify Tool Call Display
**Action**:
- Look for Activity panel or tool call section
- Find the tool calls from recent message

**Expected**:
- [ ] Tool name displayed (Read, Write, Bash, etc.)
- [ ] Tool call duration shown
- [ ] Parameters visible (file path, etc.)
- [ ] Result/status shown

**Verify**:
- [ ] All tool calls captured
- [ ] Details accurate

---

### Step 12: Check Tool Statistics
**Action**:
- Look for aggregated tool stats
- May be in Activity panel summary

**Expected**:
- [ ] Tool counts per type
- [ ] Total tool calls
- [ ] Most used tools ranked

**Verify**:
- [ ] Statistics aggregate correctly
- [ ] Counts match actual tool calls

---

## Test: Activity Timeline (OBS-008 to OBS-010)

### Step 13: Check Activity Timeline on Dashboard
**Action**:
- Navigate to Dashboard
- Switch to Timeline view (if available)
- Look for activity entries

**Expected**:
- [ ] Timeline shows recent activities
- [ ] Multiple agents' activities visible
- [ ] Time-ordered display

---

### Step 14: Test Activity Type Filter
**Action**:
- Look for filter dropdown in Timeline
- Filter by activity type (e.g., "chat_start", "tool_call")

**Expected**:
- [ ] Filter options available
- [ ] Timeline filters to selected type
- [ ] Multiple filter values supported

---

### Step 15: Test Time Range Filter
**Action**:
- Look for time range selector
- Select "Last hour" or specific range

**Expected**:
- [ ] Activities filtered by time
- [ ] Only activities within range shown
- [ ] Range updates URL or state

---

## Critical Validations

### Log API Endpoint
**Validation**: Logs API returns container output

```bash
curl -H "Authorization: Bearer {token}" \
  "http://localhost:8000/api/agents/{name}/logs?tail=50"
```

### Stats API Endpoint
**Validation**: Stats API returns telemetry

```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agents/{name}/stats
```

Expected response:
```json
{
  "cpu_percent": 2.5,
  "memory_mb": 256,
  "memory_percent": 12.5,
  "network_rx": 1024,
  "network_tx": 512,
  "uptime": "1:23:45"
}
```

---

## Success Criteria

Phase 22 is **PASSED** when:
- [ ] Logs tab displays container logs
- [ ] Logs show recent entries with timestamps
- [ ] Logs auto-refresh periodically
- [ ] CPU/memory telemetry displayed in header
- [ ] Telemetry updates in real-time
- [ ] Context percentage displayed and accurate
- [ ] Context progress bar color-coded
- [ ] Tool calls tracked with details
- [ ] Tool statistics aggregated
- [ ] Activity timeline shows cross-agent activities
- [ ] Activity filters work (type, time)

---

## Troubleshooting

**Logs tab empty**:
- Agent may have just started
- Check agent is running: `docker ps | grep {name}`
- Verify logs endpoint: `curl .../api/agents/{name}/logs`

**Telemetry not updating**:
- Check polling interval (10s)
- Verify stats endpoint works
- Check for JavaScript errors in console

**Context stuck at 0%**:
- Known bug (Phase 3)
- Check Claude Code returns context info
- Verify parsing in backend

**Tool calls not showing**:
- Activity tracking may be disabled
- Check message generated tool calls
- Verify activity table has entries

**Timeline empty**:
- No recent activities
- Check time range filter
- Verify activities exist in database

---

## Next Phase

Once Phase 22 is **PASSED**, proceed to:
- **Phase 23**: Agent Configuration

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
**User Stories**: OBS-001 to OBS-010
