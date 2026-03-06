# Timeline Schedule Markers (TSM-001)

> **Status**: ✅ Implemented (2026-01-29)
> **Priority**: Medium
> **Author**: Claude
> **Created**: 2026-01-29

## Overview

Add visual markers on the Dashboard timeline showing when agent schedules are configured to run. Users can hover to see schedule details and click to navigate to the schedule configuration.

## User Story

As a platform operator viewing the Dashboard timeline, I want to see small markers indicating when each agent's schedules are set to run, so I can understand the planned automation cadence and quickly access schedule configurations.

## Requirements

### TSM-001: Schedule Markers Display

**Visual Design:**
- Small downward-pointing triangles (▼) at the top edge of each agent's row
- Position: At the `next_run_at` timestamp for each enabled schedule
- Color: Purple (#8b5cf6) for enabled schedules (matches scheduled execution bar color)
- Size: 8px wide × 8px tall
- Opacity: 0.8 default, 1.0 on hover

**Positioning:**
- Markers appear at the top of the agent row (y = rowIndex * rowHeight + 4)
- X position calculated from `next_run_at` using existing formula: `((timestamp - startTime) / duration) * actualGridWidth`
- Only show markers within the visible timeline range

**Timeline Extension:**
- Timeline extends **max 2 hours** into the future to show nearby schedule markers
- Far-off schedules (beyond 2 hours) don't extend the timeline to prevent scale distortion
- This ensures weekly/monthly schedules don't break the timeline scale

### TSM-002: Hover Tooltip

**Tooltip Content:**
```
Schedule: {schedule.name}
Next Run: {formatted_datetime}
Cron: {cron_expression}
Message: {message_preview}  (truncated to 50 chars)
```

**Implementation:**
- Use native SVG `<title>` element (consistent with existing activity bar tooltips)
- Format datetime using existing `formatLocalTime()` utility
- Truncate message preview with ellipsis if > 50 characters

### TSM-003: Click Navigation

**Behavior:**
- Click on schedule marker navigates to AgentDetail page with Schedules tab open
- Route: `/agents/{agent_name}?tab=schedules`
- Opens in same tab (consistent with `navigateToAgent()` pattern)

**Implementation:**
```javascript
function navigateToSchedule(marker) {
  router.push({
    path: `/agents/${marker.agentName}`,
    query: { tab: 'schedules' }
  })
}
```

### TSM-004: Data Fetching

**Endpoint:** `GET /api/ops/schedules?enabled_only=true`

**Response Fields Used:**
| Field | Purpose |
|-------|---------|
| `agent_name` | Match to agent row |
| `name` | Display in tooltip |
| `next_run_at` | Calculate x position |
| `cron_expression` | Display in tooltip |
| `message` | Display preview in tooltip |
| `enabled` | Filter (only show enabled) |

**Fetch Timing:**
- On Dashboard mount (alongside `fetchHistoricalCommunications`)
- No polling required (schedules change infrequently)

---

## Technical Design

### Files to Modify

| File | Changes |
|------|---------|
| `src/frontend/src/stores/network.js` | Add `schedules` state, `fetchSchedules()` action |
| `src/frontend/src/views/Dashboard.vue` | Call `fetchSchedules()`, pass `schedules` prop |
| `src/frontend/src/components/ReplayTimeline.vue` | Add `schedules` prop, render markers |

### Backend

**No changes required.** The existing endpoint provides all necessary data:
```
GET /api/ops/schedules?enabled_only=true
```

### Frontend: network.js (~20 lines)

```javascript
// State
const schedules = ref([])

// Action
async function fetchSchedules() {
  try {
    const response = await axios.get('/api/ops/schedules', {
      params: { enabled_only: true }
    })
    schedules.value = response.data.schedules || []
  } catch (error) {
    console.error('Failed to fetch schedules:', error)
    schedules.value = []
  }
}

// Export
return { ...existing, schedules, fetchSchedules }
```

### Frontend: Dashboard.vue (~5 lines)

```vue
<!-- Add prop to ReplayTimeline -->
<ReplayTimeline
  ...existing props...
  :schedules="schedules"
/>
```

```javascript
// In onMounted
await networkStore.fetchSchedules()

// Computed
const schedules = computed(() => networkStore.schedules)
```

### Frontend: ReplayTimeline.vue (~60 lines)

**Props:**
```javascript
schedules: { type: Array, default: () => [] }
```

**Computed:**
```javascript
const scheduleMarkers = computed(() => {
  if (!props.schedules.length || !startTime.value || !duration.value) return []

  const markers = []

  props.schedules.forEach(schedule => {
    if (!schedule.next_run_at) return

    const rowIndex = filteredAgentRows.value.findIndex(row => row.name === schedule.agent_name)
    if (rowIndex === -1) return

    const nextRunMs = getTimestampMs(schedule.next_run_at)
    if (nextRunMs < startTime.value || nextRunMs > endTime.value) return

    const x = ((nextRunMs - startTime.value) / duration.value) * actualGridWidth.value

    markers.push({
      x,
      rowIndex,
      id: schedule.id,
      name: schedule.name,
      agentName: schedule.agent_name,
      nextRun: schedule.next_run_at,
      cronExpression: schedule.cron_expression,
      message: schedule.message,
      enabled: schedule.enabled
    })
  })

  return markers
})
```

**Template (after activity bars):**
```vue
<!-- Schedule markers -->
<g v-for="(marker, i) in scheduleMarkers" :key="'sched-' + i">
  <polygon
    :points="getScheduleMarkerPoints(marker)"
    fill="#8b5cf6"
    opacity="0.8"
    class="cursor-pointer hover:opacity-100 transition-opacity"
    @click="navigateToSchedule(marker)"
  >
    <title>{{ getScheduleTooltip(marker) }}</title>
  </polygon>
</g>
```

**Helper Functions:**
```javascript
function getScheduleMarkerPoints(marker) {
  const x = marker.x
  const y = marker.rowIndex * rowHeight + 4
  // Downward-pointing triangle
  return `${x},${y} ${x - 4},${y + 8} ${x + 4},${y + 8}`
}

function getScheduleTooltip(marker) {
  const nextRun = formatLocalTime(marker.nextRun)
  const messagePreview = marker.message.length > 50
    ? marker.message.substring(0, 50) + '...'
    : marker.message
  return `Schedule: ${marker.name}\nNext Run: ${nextRun}\nCron: ${marker.cronExpression}\nMessage: ${messagePreview}`
}

function navigateToSchedule(marker) {
  router.push({
    path: `/agents/${marker.agentName}`,
    query: { tab: 'schedules' }
  })
}
```

---

## Visual Reference

### Timeline Mockup

```
Time:    09:00        09:15        09:30        10:00        10:15
         |            |            |            |            |
agent-a  ▼────────────▼────────────────────────███████──────|
         ^            ^                        ^
         │            │                        └─ Scheduled execution (purple bar)
         │            └─ Schedule marker (next run)
         └─ Schedule marker (future run)

agent-b  ─────────────▼────────────────────────────────────|
                      ^
                      └─ Single schedule marker

agent-c  ─────────────────────────────███────────────────────|
                                      ^
                                      └─ Manual execution (green bar, no markers)
```

### Tooltip Example

```
┌─────────────────────────────────┐
│ Schedule: Daily Status Report   │
│ Next Run: 09:00 AM              │
│ Cron: 0 9 * * *                 │
│ Message: Generate daily stat... │
└─────────────────────────────────┘
```

---

## Testing

### Prerequisites
- [ ] Backend running with schedules configured
- [ ] At least 2 agents with enabled schedules
- [ ] Dashboard accessible

### Test Cases

#### TC1: Marker Display
| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Dashboard | Timeline loads |
| 2 | Switch to Timeline mode | Timeline visible |
| 3 | Check agents with schedules | Purple triangles (▼) visible at top of agent rows |
| 4 | Verify position | Markers align with `next_run_at` time on x-axis |

#### TC2: Hover Tooltip
| Step | Action | Expected |
|------|--------|----------|
| 1 | Hover over schedule marker | Tooltip appears |
| 2 | Check tooltip content | Shows schedule name, next run time, cron expression, message preview |
| 3 | Move mouse away | Tooltip disappears |

#### TC3: Click Navigation
| Step | Action | Expected |
|------|--------|----------|
| 1 | Click on schedule marker | Navigates to AgentDetail page |
| 2 | Check URL | URL is `/agents/{agent_name}?tab=schedules` |
| 3 | Check active tab | Schedules tab is active |

#### TC4: Edge Cases
| Step | Action | Expected |
|------|--------|----------|
| 1 | Agent with no schedules | No markers on that row |
| 2 | Disabled schedules | Not shown (filtered by `enabled_only=true`) |
| 3 | Schedule outside time range | Not shown |
| 4 | Zoom in/out | Markers reposition correctly |
| 5 | "Active only" filter | Markers visible only on shown agents |

---

## Acceptance Criteria

- [ ] Schedule markers visible on timeline for agents with enabled schedules
- [ ] Markers positioned at correct `next_run_at` timestamp
- [ ] Hover shows tooltip with schedule details (name, next run, cron, message)
- [ ] Click navigates to `/agents/{name}?tab=schedules`
- [ ] Markers respect zoom level and time range
- [ ] Markers hidden for agents filtered by "Active only" toggle
- [ ] No backend changes required

---

## Future Enhancements (Out of Scope)

1. **Multiple future occurrences** - Parse cron expression to show next N runs
2. **Disabled schedule markers** - Show in gray for disabled schedules
3. **Schedule execution animation** - Flash marker when schedule fires
4. **Deep-link to specific schedule** - Add `scheduleId` query param support in AgentDetail

---

## Related Documents

- [Replay Timeline](../memory/feature-flows/replay-timeline.md) - Timeline component documentation
- [Scheduling](../memory/feature-flows/scheduling.md) - Agent scheduling feature flow
- [Dashboard Timeline View](../memory/feature-flows/dashboard-timeline-view.md) - Timeline mode documentation
