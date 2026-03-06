# Requirements: Dashboard Timeline View

> **Created**: 2026-01-10
> **Status**: Draft
> **Priority**: High
> **Complexity**: Medium

## Overview

Transform the Dashboard to offer two distinct views: **Graph** (current node-based visualization) and **Timeline** (waterfall-style live activity view). The Timeline view will show real-time agent activity with rich agent labels, eliminating the need for a separate "replay" concept.

## Goals

1. Rename "Live" mode to "Graph" and "Replay" mode to "Timeline"
2. Make Timeline view work with **live events** (not just historical playback)
3. Add **rich agent labels** to Timeline showing stats, context, and controls
4. Keep Graph view completely unchanged (just rename the toggle button)
5. **No backend changes** - all data is already available

## Non-Goals

- Modifying the Graph view (VueFlow) in any way
- Adding new API endpoints
- Changing how data is stored or fetched

---

## Current State

### Dashboard.vue (739 lines)
- **Mode Toggle** (lines 66-85): "Live" and "Replay" buttons
- **ReplayTimeline** (lines 141-158): Only visible in replay mode
- **VueFlow Graph** (lines 187-252): Main visualization
- Live mode: WebSocket connected, polling active
- Replay mode: WebSocket disconnected, polling stopped

### ReplayTimeline.vue (674 lines)
- Waterfall timeline with agent rows, activity bars, communication arrows
- Playback controls: Play, Pause, Stop, Speed selector
- Zoom controls, "Active only" toggle
- 15-minute grid ticks, "Now" marker
- Agent labels: Just name + status dot (150px column)

### AgentNode.vue (393 lines) - Reference for Rich Labels
Data shown on graph nodes (to be mirrored in Timeline labels):
- Agent name, status dot, runtime badge
- Activity state (Active/Idle/Offline)
- Autonomy toggle (AUTO/Manual)
- Context progress bar (0-100%)
- Execution stats: tasks (24h), success rate, cost, last execution
- Resource indicators: memory, CPU limits

### network.js Store (1236 lines)
- WebSocket handles: `agent_collaboration`, `agent_status`, `agent_deleted`
- `handleCollaborationEvent()`: Adds to both `collaborationHistory` and `historicalCollaborations`
- `setReplayMode(true)`: Disconnects WebSocket, stops polling
- `setReplayMode(false)`: Connects WebSocket, starts polling
- Polling: Context stats (5s), Execution stats (5s), Agent list (10s)

---

## Requirements

### REQ-1: Rename Mode Toggle

**Current**: `[Live] [Replay]`
**New**: `[Graph] [Timeline]`

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `Dashboard.vue` | Lines 66-85 | Change button labels from "Live"/"Replay" to "Graph"/"Timeline" |
| `Dashboard.vue` | `toggleMode()` | Keep same logic, just different labels |

**Behavior**: Toggle switches between Graph view (VueFlow) and Timeline view (ReplayTimeline).

---

### REQ-2: Timeline View - Live Event Streaming

When Timeline view is active, it should show **real-time events** instead of just historical playback.

#### REQ-2.1: Keep WebSocket Connected in Timeline View

**Current**: `setReplayMode(true)` disconnects WebSocket
**New**: Timeline view keeps WebSocket connected

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `network.js` | `setReplayMode()` (lines 798-816) | Don't disconnect WebSocket when entering "Timeline" mode |
| `network.js` | New function `setViewMode(mode)` | Replace `setReplayMode()` with `setViewMode('graph' | 'timeline')` that keeps WebSocket connected |

**Note**: Keep polling active too (context stats, execution stats) so Timeline labels stay updated.

#### REQ-2.2: Append Live Events to Timeline

**Current**: `handleCollaborationEvent()` adds to arrays but Timeline doesn't show them live
**New**: Live events appear at the right edge of the Timeline

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `ReplayTimeline.vue` | `agentRows` computed | Already uses `props.events` - works if parent keeps passing updated data |
| `Dashboard.vue` | ReplayTimeline props | Already passes `:events="historicalCollaborations"` - events are reactive |

**Verification**: When a new `agent_collaboration` WebSocket event arrives:
1. `handleCollaborationEvent()` adds to `historicalCollaborations`
2. Timeline's `events` prop updates reactively
3. New activity bar appears at the right edge (at "now" position)

#### REQ-2.3: "Now" Marker Always at Right Edge

**Current**: "Now" marker is static (computed from `Date.now()` once)
**New**: "Now" marker updates continuously

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `ReplayTimeline.vue` | `nowX` computed (line 403-408) | Add interval to update `Date.now()` every second when not in playback mode |
| `ReplayTimeline.vue` | New ref `currentNow` | Create `ref(Date.now())` and update via `setInterval` in `onMounted` |

#### REQ-2.4: Auto-Scroll to "Now"

**Current**: User must manually scroll to see latest events
**New**: Timeline auto-scrolls to keep "Now" visible (unless user has scrolled back)

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `ReplayTimeline.vue` | New ref `autoScrollEnabled` | Default `true`, set to `false` when user scrolls left |
| `ReplayTimeline.vue` | `@scroll` handler | Detect if user scrolled away from right edge, disable auto-scroll |
| `ReplayTimeline.vue` | Watch for new events | If `autoScrollEnabled`, scroll container to show right edge |
| `ReplayTimeline.vue` | "Jump to Now" button | Button to re-enable auto-scroll and scroll to right edge |

---

### REQ-3: Remove Playback Controls in Live Mode

When viewing live (not replaying history), playback controls are not needed.

#### REQ-3.1: Hide Playback Controls

**Current**: Play/Pause/Stop/Speed always visible
**New**: Only show playback controls when actively replaying (user clicked on a past event)

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `ReplayTimeline.vue` | Playback controls (lines 4-48) | Wrap in `v-if="isReplayingHistory"` |
| `ReplayTimeline.vue` | New prop `isLiveMode` | Parent passes whether this is live viewing |
| `ReplayTimeline.vue` | New computed `isReplayingHistory` | True if user has scrolled back and clicked "play" on past events |

**Alternative Approach**: Remove playback entirely for MVP. Timeline is always live - scroll left to see history, scroll right (or click "Now") to return to live.

#### REQ-3.2: Keep These Controls

- **Zoom controls** (+/- and slider) - Always visible
- **"Active only" toggle** - Always visible
- **Time range selector** - Move from Dashboard header to Timeline header

---

### REQ-4: Rich Agent Labels (Option A)

Expand the left agent label column to show stats and controls, mirroring AgentNode.vue data.

#### REQ-4.1: Expand Label Column Width

**Current**: `labelWidth = 150` (line 356)
**New**: `labelWidth = 220`

#### REQ-4.2: Rich Label Layout

Each agent row label (left column) should show:

```
┌─────────────────────────────────────┐
│ ● research                      45% │  <- Status dot, name, context %
│ ████████████░░░░░░░░░░░░░░░░░░░░░░░ │  <- Context progress bar (mini)
│ 12 tasks · 92% · $0.82 · 2m ago     │  <- Execution stats row
└─────────────────────────────────────┘
```

**Data Sources** (from `network.js` store):
| Data | Source |
|------|--------|
| Status | `agents[].status` |
| Name | `agents[].name` |
| Context % | `contextStats[agentName].contextPercent` |
| Task count | `executionStats[agentName].taskCount` |
| Success rate | `executionStats[agentName].successRate` |
| Cost | `executionStats[agentName].totalCost` |
| Last execution | `executionStats[agentName].lastExecutionAt` |

#### REQ-4.3: Pass Stats to ReplayTimeline

**Current**: `ReplayTimeline` receives `agents` array but no stats
**New**: Pass stats as part of agent data or as separate prop

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `Dashboard.vue` | ReplayTimeline props | Add `:context-stats="contextStats"` and `:execution-stats="executionStats"` |
| `ReplayTimeline.vue` | Props | Add `contextStats` and `executionStats` props |
| `ReplayTimeline.vue` | `agentRows` computed | Merge stats into each row object |

#### REQ-4.4: Clickable Agent Labels

**Current**: Agent labels are not interactive
**New**: Clicking an agent label navigates to `/agents/{name}`

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `ReplayTimeline.vue` | Agent label div (lines 172-188) | Add `@click="navigateToAgent(row.name)"` and `cursor-pointer` class |
| `ReplayTimeline.vue` | New method `navigateToAgent()` | Use `router.push()` to navigate |

#### REQ-4.5: Mini Context Progress Bar

**Current**: No progress bar in Timeline labels
**New**: Add a compact progress bar below agent name

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `ReplayTimeline.vue` | Agent label div | Add mini progress bar div with Tailwind classes |

**Styling**:
```html
<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1 mt-1">
  <div
    class="h-full rounded-full"
    :class="progressBarColor(row.contextPercent)"
    :style="{ width: row.contextPercent + '%' }"
  ></div>
</div>
```

#### REQ-4.6: Execution Stats Row

**Current**: No stats in Timeline labels
**New**: Compact stats row matching AgentNode.vue format

**Format**: `{tasks} tasks · {rate}% · ${cost} · {time} ago`

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `ReplayTimeline.vue` | Agent label div | Add stats row after progress bar |
| `ReplayTimeline.vue` | Computed helpers | Add `formatLastExecution()` helper |

---

### REQ-5: Row Height Adjustment

With richer labels, rows need more height.

**Current**: `rowHeight = 32` (line 358)
**New**: `rowHeight = 64` (or dynamically based on content)

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `ReplayTimeline.vue` | `rowHeight` constant | Increase from 32 to 64 |
| `ReplayTimeline.vue` | `barHeight` constant | Keep at 16 or increase slightly |
| `ReplayTimeline.vue` | Activity bar positioning | Adjust `y` calculation for centered bars in taller rows |

---

### REQ-6: Stopped Agents Handling

Stopped agents should appear differently in the Timeline.

**Current**: All agents shown with same treatment
**New**: Stopped agents show grayed out, no activity expected

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `ReplayTimeline.vue` | Agent label styling | Add conditional class for stopped agents |
| `ReplayTimeline.vue` | Stats row | Show "Stopped" instead of stats for stopped agents |

**Styling**:
```html
<div :class="row.status === 'running' ? '' : 'opacity-50'">
  ...
</div>
```

---

### REQ-7: State Persistence

Remember user's view preference.

**Current**: Mode is stored in localStorage as `trinity-replay-mode`
**New**: Store as `trinity-dashboard-view` with values `'graph'` or `'timeline'`

**Changes**:
| File | Location | Change |
|------|----------|--------|
| `network.js` | `setViewMode()` | Save to `trinity-dashboard-view` |
| `Dashboard.vue` | `onMounted` | Load preference and apply |

---

## Implementation Order

1. **Phase 1: Rename Only** (Low risk)
   - Change toggle labels from "Live/Replay" to "Graph/Timeline"
   - No functional changes

2. **Phase 2: Keep WebSocket Connected** (Medium risk)
   - Modify `setReplayMode()` to not disconnect WebSocket
   - Verify live events appear in Timeline

3. **Phase 3: "Now" Marker Updates** (Low risk)
   - Add interval to update `nowX` continuously
   - Test auto-scroll behavior

4. **Phase 4: Rich Agent Labels** (Medium complexity)
   - Expand label width
   - Add stats props from Dashboard
   - Implement rich label layout
   - Add click-to-navigate

5. **Phase 5: Polish** (Low risk)
   - Remove playback controls (or hide in live mode)
   - Adjust row heights
   - Handle stopped agents styling

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/frontend/src/views/Dashboard.vue` | Rename toggle labels, pass stats props |
| `src/frontend/src/components/ReplayTimeline.vue` | Rich labels, live mode behavior, row height |
| `src/frontend/src/stores/network.js` | `setViewMode()` function, keep WebSocket connected |

---

## Testing Checklist

### Basic Functionality
- [ ] Toggle shows "Graph" and "Timeline" labels
- [ ] Graph view works exactly as before (no changes)
- [ ] Timeline view shows when "Timeline" selected

### Live Events in Timeline
- [ ] WebSocket stays connected in Timeline view
- [ ] New collaboration events appear at right edge
- [ ] "Now" marker updates continuously
- [ ] Activity bars animate for new events

### Rich Agent Labels
- [ ] Agent name visible
- [ ] Status dot shows correct color (green=running, gray=stopped)
- [ ] Context percentage displayed
- [ ] Mini progress bar shows context usage
- [ ] Execution stats row shows (tasks, rate, cost, time)
- [ ] Clicking agent name navigates to AgentDetail

### Edge Cases
- [ ] Stopped agents appear grayed out
- [ ] Agents with no execution history show "No tasks (24h)"
- [ ] Timeline works with 0 agents
- [ ] Timeline works with 1 agent
- [ ] Timeline handles 10+ agents (scrolling)

### Performance
- [ ] No jank with continuous "now" updates
- [ ] Live events don't cause layout thrashing
- [ ] Stats polling doesn't cause flickering

---

## Visual Mockup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Trinity                                    [Graph] [Timeline●]   2h▼  ● ⟳  │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Zoom +/-] [Active only ☐]                         0/15 events            │
├─────────────────────────────────────────────────────────────────────────────┤
│                     │ 09:00    09:30    10:00    10:30    11:00   NOW│     │
│                     ├──────────────────────────────────────────────────┤    │
│ ● research      45% │  ▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓●  │    │
│ ████████░░░░░░░░░░░ │                                                  │    │
│ 12 tasks·92%·$0.82  │                                                  │    │
├─────────────────────┼──────────────────────────────────────────────────┤    │
│ ● writer        78% │  ░░░░░░░░░░░░░░░░░░░▓▓▓▓▓░░░░░░░░░░░░░▓▓▓▓▓▓▓●  │    │
│ ████████████░░░░░░░ │                     └────────────────────────→   │    │
│ 8 tasks·100%·$1.24  │                                                  │    │
├─────────────────────┼──────────────────────────────────────────────────┤    │
│ ○ analyst   Stopped │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │    │
│                     │                                                  │    │
│ [Start]             │                                                  │    │
└─────────────────────┴──────────────────────────────────────────────────┘    │
```

---

## Success Criteria

1. User can toggle between Graph and Timeline views
2. Timeline shows live events streaming in real-time
3. Rich agent labels provide at-a-glance fleet health
4. No backend changes required
5. Graph view behavior unchanged

---

## Open Questions

1. **Playback controls**: Remove entirely, or keep for "scrub back and replay" feature?
   - Recommendation: Remove for MVP. Users can scroll to see history.

2. **Time range selector**: Move to Timeline header or keep in Dashboard header?
   - Recommendation: Keep in Dashboard header (affects both views).

3. **System Agent row**: Same treatment as regular agents, or special styling?
   - Recommendation: Same treatment, but with purple styling to match graph.

---

## References

- **Feature Flows**: `docs/memory/feature-flows/replay-timeline.md`, `agent-network-replay-mode.md`
- **Current Components**: `Dashboard.vue`, `ReplayTimeline.vue`, `AgentNode.vue`
- **Store**: `network.js`
