# Requirements: Timeline All Executions Display

> **Created**: 2026-01-10
> **Status**: ✅ Implemented
> **Goal**: Show ALL executions on Dashboard Timeline (scheduled, manual, collaboration) - not just agent-to-agent collaborations

## Problem Statement

Currently, the Dashboard Timeline only shows `agent_collaboration` events (agent-to-agent calls). Users cannot see:
- Scheduled task executions
- Manual task executions (via Tasks tab or MCP)
- API-triggered tasks

All this data EXISTS in the database (`agent_activities` table) but isn't being queried or displayed.

## Current State Analysis

### Backend (Already Complete)

The backend already tracks ALL execution types in `agent_activities`:

| Activity Type | Triggered By | Has `target_agent` | Source |
|---------------|--------------|---------------------|--------|
| `agent_collaboration` | `agent` | ✅ Yes | Agent-to-agent MCP calls |
| `schedule_start` | `schedule` | ❌ No | APScheduler cron jobs |
| `schedule_end` | `schedule` | ❌ No | Scheduler completion |
| `chat_start` | `user` / `agent` / `manual` | ❌ No | User chats, MCP calls, manual tasks |
| `chat_end` | `user` / `agent` / `manual` | ❌ No | Chat completion |

**Key API**: `GET /api/activities/timeline?activity_types=X,Y,Z` - Already supports comma-separated types!

### Frontend (Needs Changes)

Current code in `network.js:120-179`:
```javascript
// CURRENT: Only fetches collaborations
const params = {
  activity_types: 'agent_collaboration',  // ← Problem: only one type!
  start_time: startTime.toISOString(),
  limit: 500
}
```

## Requirements

### 1. Expand Activity Types Query (Frontend)

**File**: `src/frontend/src/stores/network.js`

Change `fetchHistoricalCollaborations()` to fetch ALL execution types:

```javascript
const params = {
  activity_types: 'agent_collaboration,schedule_start,schedule_end,chat_start,chat_end',
  start_time: startTime.toISOString(),
  limit: 500
}
```

### 2. Filter Out Regular User Chats (Frontend)

Keep only:
- ✅ `agent_collaboration` - all
- ✅ `schedule_start` / `schedule_end` - all
- ✅ `chat_start` / `chat_end` where `triggered_by != 'user'` (agent-initiated)
- ✅ `chat_start` / `chat_end` where `details.parallel_mode == true` (manual tasks)
- ❌ `chat_start` / `chat_end` where `triggered_by == 'user'` AND NOT `parallel_mode` (regular user chats)

```javascript
// Filter logic
const isUserChat = activity.activity_type.startsWith('chat_')
  && activity.triggered_by === 'user'
  && !details.parallel_mode

if (isUserChat) return null  // Skip regular user chats
```

### 3. Parse Events by Type (Frontend)

Update event parsing to handle both collaboration and execution events:

```javascript
// Current: Expects target_agent
return {
  source_agent: details.source_agent || activity.agent_name,
  target_agent: details.target_agent,  // ← null for executions
  timestamp: activity.started_at,
  ...
}

// NEW: Handle missing target_agent for executions
return {
  source_agent: activity.agent_name,
  target_agent: details.target_agent || null,  // null = execution, not collaboration
  timestamp: activity.started_at,
  activity_type: activity.activity_type,  // NEW: Pass through
  triggered_by: activity.triggered_by,    // NEW: Pass through
  schedule_name: details.schedule_name,   // NEW: For scheduled tasks
  ...
}
```

### 4. Render Executions Without Arrows (Frontend)

**File**: `src/frontend/src/components/ReplayTimeline.vue`

Current logic creates arrows between `source_agent` → `target_agent`. For executions (no `target_agent`):
- Show activity bar on the agent row (already works)
- Do NOT render communication arrow
- Use different color to distinguish execution types

### 5. Color Coding by Execution Type (Frontend)

| Activity Type | Color | Description |
|---------------|-------|-------------|
| `agent_collaboration` | Cyan (`#06b6d4`) | Agent-to-agent call |
| `schedule_start/end` | Purple (`#8b5cf6`) | Scheduled execution |
| `chat_start/end` (manual) | Green (`#22c55e`) | Manual task |
| Error state | Red (`#ef4444`) | Any failed execution |

```javascript
function getBarColor(activity) {
  if (activity.hasError) return '#ef4444'  // Red for errors (existing)
  if (activity.isInProgress) return '#f59e0b'  // Amber for in-progress (existing)

  // NEW: Color by activity type
  if (activity.activityType === 'agent_collaboration') return '#06b6d4'  // Cyan
  if (activity.activityType?.startsWith('schedule_')) return '#8b5cf6'  // Purple
  if (activity.triggeredBy === 'manual') return '#22c55e'  // Green

  return '#3b82f6'  // Default blue
}
```

### 6. Legend or Tooltip Enhancement (Optional)

Add visual indicator in tooltips showing execution type:
- "Scheduled: daily-report (2m 15s)"
- "Manual Task (45s)"
- "Agent Call: researcher → analyst (1m 30s)"

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Backend (NO CHANGES NEEDED)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐     ┌──────────────────────┐                       │
│  │ schedule_start  │────▶│                      │                       │
│  │ schedule_end    │     │  agent_activities    │                       │
│  ├─────────────────┤     │  table               │                       │
│  │ chat_start      │────▶│                      │◀── GET /api/activities│
│  │ chat_end        │     │  (all types stored)  │    /timeline?types=   │
│  ├─────────────────┤     │                      │                       │
│  │ agent_collab    │────▶│                      │                       │
│  └─────────────────┘     └──────────────────────┘                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Frontend (CHANGES NEEDED)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  network.js                                                              │
│  ┌──────────────────────────────────────────────┐                       │
│  │ fetchHistoricalCollaborations()              │                       │
│  │   ↓                                          │                       │
│  │ 1. Query ALL activity types                  │  ← CHANGE             │
│  │ 2. Filter out regular user chats             │  ← NEW                │
│  │ 3. Parse with activity_type field            │  ← CHANGE             │
│  │ 4. Store in historicalCollaborations         │                       │
│  └──────────────────────────────────────────────┘                       │
│                          │                                               │
│                          ▼                                               │
│  ReplayTimeline.vue                                                      │
│  ┌──────────────────────────────────────────────┐                       │
│  │ agentRows computed:                          │                       │
│  │   - Activity bars (all types)                │                       │
│  │   - Color by activity_type                   │  ← CHANGE             │
│  │   - Arrows only for collaborations           │  ← Already works      │
│  │   - Enhanced tooltips                        │  ← CHANGE             │
│  └──────────────────────────────────────────────┘                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Files to Modify

| File | Change | Complexity |
|------|--------|------------|
| `src/frontend/src/stores/network.js` | Expand activity_types query, filter logic, parse activity_type | Medium |
| `src/frontend/src/components/ReplayTimeline.vue` | Color coding, tooltip enhancement | Low |
| `docs/memory/feature-flows/dashboard-timeline-view.md` | Update documentation | Low |

## Backend Changes (NONE REQUIRED)

The backend already:
- ✅ Stores all activity types in `agent_activities` table
- ✅ Supports comma-separated `activity_types` parameter
- ✅ Returns `activity_type`, `triggered_by`, `details` in response
- ✅ Has `duration_ms`, `error`, `activity_state` for all types

## Implementation Steps

### Step 1: Expand Query (network.js)

```diff
- activity_types: 'agent_collaboration',
+ activity_types: 'agent_collaboration,schedule_start,schedule_end,chat_start,chat_end',
```

### Step 2: Add Filter Logic (network.js)

```javascript
.filter(activity => {
  // Skip regular user chats
  if (activity.activity_type.startsWith('chat_')) {
    const details = typeof activity.details === 'string'
      ? JSON.parse(activity.details)
      : activity.details || {}
    if (activity.triggered_by === 'user' && !details.parallel_mode) {
      return false  // Skip regular user chats
    }
  }
  return true
})
```

### Step 3: Expand Event Parsing (network.js)

```javascript
return {
  source_agent: activity.agent_name,
  target_agent: details.target_agent || null,
  timestamp: activity.started_at || activity.created_at,
  activity_id: activity.id,
  status: activity.activity_state,
  duration_ms: activity.duration_ms,
  // NEW fields
  activity_type: activity.activity_type,
  triggered_by: activity.triggered_by,
  schedule_name: details.schedule_name || null,
  error: activity.error
}
```

### Step 4: Color Coding (ReplayTimeline.vue)

Update `getBarColor()` function to use `activity_type` for coloring.

### Step 5: Tooltip Enhancement (ReplayTimeline.vue)

Update `getBarTooltip()` to show execution type and schedule name.

## Testing Checklist

### Prerequisites
- [ ] Backend running with some historical data
- [ ] At least one agent with: scheduled task, manual task, collaboration history

### Test Cases

1. **Scheduled Execution Visibility**
   - [ ] Create schedule, trigger manually
   - [ ] Switch to Timeline view
   - [ ] Verify purple bar appears on agent row
   - [ ] Verify tooltip shows "Scheduled: {name}"

2. **Manual Task Visibility**
   - [ ] Run manual task from Tasks tab
   - [ ] Verify green bar appears on Timeline
   - [ ] Verify tooltip shows "Manual Task"

3. **Agent Collaboration (Existing)**
   - [ ] Trigger agent-to-agent call
   - [ ] Verify cyan bar AND arrow appears
   - [ ] Verify tooltip shows source → target

4. **User Chats Filtered Out**
   - [ ] Send regular chat message to agent
   - [ ] Verify NO new bar appears on Timeline
   - [ ] Only automated executions should show

5. **Mixed History**
   - [ ] With varied history (scheduled + manual + collaboration)
   - [ ] Verify all three colors visible
   - [ ] Verify arrows only for collaborations

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance with many events | Limit already at 500, existing pagination |
| Arrow rendering for non-collabs | Filter in arrow generation (target_agent required) |
| Legacy events missing fields | Provide defaults for activity_type, triggered_by |

## Success Criteria

- [x] Timeline shows scheduled executions as purple bars
- [x] Timeline shows manual tasks as green bars
- [x] Timeline shows collaborations as cyan bars with arrows
- [x] Regular user chats do NOT appear on timeline
- [x] Tooltips show execution type and relevant info
- [x] No backend changes required
- [x] No performance regression
