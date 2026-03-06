# Slot Indicator UI (SLOT-UI-001)

> **Status**: Pending Implementation
> **Priority**: P2 - Enhancement
> **Depends On**: CAPACITY-001 (Parallel Execution Capacity) - ✅ Implemented

## Summary

Replace green blinking status dots across the platform with horizontal "slot bar" indicators that visualize agent parallel execution capacity and current slot usage.

## Problem Statement

The current UI uses a simple green blinking dot to indicate agent activity. This provides no visibility into:
- How many parallel execution slots an agent has (1-10, default 3)
- How many slots are currently occupied by running tasks
- When an agent is approaching or at capacity

With CAPACITY-001 implemented, the backend tracks slot usage but the UI doesn't surface this information.

## Requirements

### REQ-1: Slot Indicator Component

Create a reusable `SlotIndicator.vue` component that displays horizontal bars representing execution slots.

**Visual Design:**
```
Active (2/3):     ████  ████  ░░░░   (2 green pulsing, 1 gray)
At capacity (3/3): ████  ████  ████   (all amber pulsing)
Idle (0/3):       ░░░░  ░░░░  ░░░░   (all gray, no pulse)
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `maxSlots` | Number | 3 | Total slots (from `max_parallel_tasks`) |
| `activeSlots` | Number | 0 | Currently occupied slots |
| `size` | String | 'md' | Bar size: 'sm', 'md', 'lg' |

**Behavior:**
- Render `maxSlots` horizontal bars
- First `activeSlots` bars are lit (green/amber)
- Remaining bars are dim (gray)
- Active bars pulse when `activeSlots > 0`
- All bars turn amber when `activeSlots === maxSlots` (at capacity)
- Tooltip shows "X/Y slots active"

**Styling:**
| State | Color | Animation |
|-------|-------|-----------|
| Active slot | Green (#10b981) | 0.8s pulse |
| At capacity | Amber (#f59e0b) | 0.8s pulse |
| Available slot | Gray (#9ca3af) | None |

### REQ-2: Dashboard Integration

**Header Stats (Dashboard.vue lines 35-39):**

Replace the "X active" collaboration indicator:

Before:
```
🟢 3 running • 🟢⚡ 2 active
```

After:
```
🟢 3 running • 5/9 slots
```

Show aggregate slot usage across all agents.

**Agent Nodes (AgentNode.vue lines 47-53):**

Replace the status dot with SlotIndicator:

Before:
```
┌──────────────────────┐
│ [Agent Name]      🟢 │  ← Green pulsing dot
└──────────────────────┘
```

After:
```
┌──────────────────────┐
│ [Agent Name]  ══ ══ ─│  ← 2/3 slot bars
└──────────────────────┘
```

### REQ-3: Agents Page Integration

**Agent Cards (Agents.vue lines 220-227):**

Replace the status dot with SlotIndicator in each agent card.

### REQ-4: Timeline Integration

**Agent Rows (ReplayTimeline.vue lines 130-139):**

Replace the status dot with SlotIndicator in timeline agent rows.

### REQ-5: Agent Detail Integration

**Agent Header (AgentHeader.vue after line 44):**

Add SlotIndicator next to the status badge:

```
my-agent  [Running]  ══ ─ ─   (1/3 slots)
```

Only show when agent status is "running".

### REQ-6: Store Updates

**agents.js store:**

Add slot state management:

```javascript
// State
slotStates: {}  // { agentName: { max: 3, active: 1 } }

// Action
async fetchSlotStates() {
  // GET /api/agents/slots
  // Update slotStates
}
```

Integrate with existing context polling (every 5 seconds).

## API Dependencies

Uses existing endpoints from CAPACITY-001:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/agents/slots` | Bulk slot state for all agents |
| Response: `{ agents: { "agent-name": { max: 3, active: 1 } } }` |

## UI/UX Notes

1. **Context progress bar**: Keep as-is (not removed)
2. **No capacity settings modal**: Clicking indicator does not open settings
3. **Animation**: Simple pulse is sufficient
4. **Responsive**: Bars scale with size prop for different contexts

## Files Affected

| File | Change |
|------|--------|
| `src/frontend/src/components/SlotIndicator.vue` | CREATE |
| `src/frontend/src/stores/agents.js` | MODIFY - Add slotStates |
| `src/frontend/src/components/AgentNode.vue` | MODIFY - Replace dot |
| `src/frontend/src/views/Dashboard.vue` | MODIFY - Header + nodes |
| `src/frontend/src/views/Agents.vue` | MODIFY - Replace dot |
| `src/frontend/src/components/ReplayTimeline.vue` | MODIFY - Replace dot |
| `src/frontend/src/components/AgentHeader.vue` | MODIFY - Add indicator |

## Acceptance Criteria

- [ ] SlotIndicator component renders bars based on props
- [ ] Dashboard header shows aggregate "X/Y slots" instead of "X active"
- [ ] AgentNode shows slot bars instead of green dot
- [ ] Agents page cards show slot bars
- [ ] Timeline agent rows show slot bars
- [ ] AgentHeader shows slot indicator for running agents
- [ ] Bars pulse green when active
- [ ] Bars turn amber when at capacity (all slots used)
- [ ] Slot state updates via polling (5s interval)
- [ ] Tooltip shows "X/Y slots active"

## Testing

### Manual Test Steps

1. Start services and login
2. Create test agent (default 3 slots)
3. Navigate to Dashboard - verify SlotIndicator on agent node
4. Trigger 2 parallel tasks via API
5. Verify 2 bars pulsing green, 1 gray
6. Trigger 3rd task - verify all bars amber
7. Trigger 4th task - verify 429 response
8. Wait for tasks to complete - verify bars return to gray
9. Check Agents page, Timeline, Agent Detail - all show indicators

### API Test

```bash
# Get slot state
curl http://localhost:8000/api/agents/slots \
  -H "Authorization: Bearer $TOKEN"

# Expected response
{
  "agents": {
    "test-agent": {"max": 3, "active": 2}
  },
  "timestamp": "2026-03-01T12:00:00Z"
}
```

## Related

- **CAPACITY-001**: Per-agent parallel execution capacity (backend) - ✅ Implemented
- **Feature Flow**: `docs/memory/feature-flows/parallel-capacity.md`
