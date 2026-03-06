# Parallel Execution Capacity (CAPACITY-001)

> **Status**: Planning
> **Priority**: P1
> **Created**: 2026-02-28
> **Author**: Claude

## Overview

Implement configurable per-agent parallel execution capacity with visual representation on the Dashboard. Each agent has a maximum number of concurrent execution "threads" (slots), and the UI displays how many slots are currently occupied.

## Problem Statement

Currently, Trinity has no limit on parallel `/api/task` executions per agent. An orchestrator could spawn unlimited concurrent tasks, causing:
- Resource exhaustion (CPU, memory, API tokens)
- Cost explosion
- Agent unavailability for critical operations

Additionally, the Dashboard only shows a blinking green dot when an agent is active, providing no indication of HOW MUCH work the agent is handling.

## Solution

1. **Configurable capacity**: Each agent has `max_parallel_tasks` (1-10, default 3)
2. **Slot enforcement**: Reject new parallel tasks when at capacity (HTTP 429)
3. **Dashboard indicator**: Replace activity dot with capacity meter (X/Y slots)
4. **Timeline swim lanes**: Execution bars organized into fixed slot lanes

---

## Requirements

### R1: Agent Configuration

**R1.1**: Add `max_parallel_tasks` column to `agent_ownership` table
- Type: INTEGER
- Range: 1-10
- Default: 3
- Nullable: No

**R1.2**: Expose configuration via REST API
- `GET /api/agents/{name}` returns `max_parallel_tasks`
- `PUT /api/agents/{name}/capacity` updates the value
- Validation: Must be integer 1-10

**R1.3**: Add MCP tool for configuration
- `set_agent_capacity(agent_name, max_parallel_tasks)` - Set capacity
- `get_agent_capacity(agent_name)` - Get current capacity and slot usage

**R1.4**: UI configuration
- Add capacity setting in Agent Detail → Info tab or Settings section
- Slider or dropdown (1-10)
- Show current active count

---

### R2: Slot Tracking

**R2.1**: Redis slot tracking
- Key pattern: `agent:slots:{name}` (Redis SET)
- Value: Set of active execution IDs
- Operations:
  - `SADD` on execution start
  - `SREM` on execution complete/fail
  - `SCARD` to count active slots

**R2.2**: Slot acquisition flow
```
1. Client calls POST /api/agents/{name}/task
2. Backend checks SCARD agent:slots:{name}
3. If count >= max_parallel_tasks:
   - Return 429 Too Many Requests
   - Body: {"error": "Agent at capacity", "active": N, "max": M, "retry_after": 30}
4. If count < max:
   - Generate execution_id
   - SADD agent:slots:{name} execution_id
   - Proceed with execution
5. On completion (success or failure):
   - SREM agent:slots:{name} execution_id
```

**R2.3**: Slot cleanup
- TTL on slot entries: 30 minutes (safety net for orphaned slots)
- Use Redis ZADD with timestamp scores for automatic expiry
- Alternative: Background cleanup task every 60 seconds

**R2.4**: Slot state API
- `GET /api/agents/{name}/slots` returns:
  ```json
  {
    "agent_name": "research-agent",
    "max_parallel_tasks": 5,
    "active_slots": 3,
    "slot_details": [
      {"execution_id": "abc123", "started_at": "2026-02-28T10:00:00Z", "message_preview": "Research..."},
      {"execution_id": "def456", "started_at": "2026-02-28T10:01:00Z", "message_preview": "Analyze..."},
      {"execution_id": "ghi789", "started_at": "2026-02-28T10:02:00Z", "message_preview": "Write..."}
    ]
  }
  ```

**R2.5**: Bulk slot state for Dashboard
- `GET /api/agents/slots` returns slot state for all agents (single request)
- Used by Dashboard for efficient polling

---

### R3: Dashboard Agent Node Indicator

**R3.1**: Replace activity dot with capacity meter
- Current: Green blinking dot when agent has activity
- New: Horizontal bar showing X/Y slots occupied

**R3.2**: Visual design
```
┌──────────────────────────────────┐
│  research-agent                  │
│  ┌────────────────────┐          │
│  │ ■■■□□ │ 3/5 slots  │          │
│  └────────────────────┘          │
│  Running  [Toggle]  Auto [Toggle]│
└──────────────────────────────────┘
```

**R3.3**: Capacity meter states
| State | Visual | Color |
|-------|--------|-------|
| 0/N (idle) | `□□□□□` | Gray |
| 1-49% | `■□□□□` | Green |
| 50-79% | `■■■□□` | Yellow |
| 80-99% | `■■■■□` | Orange |
| N/N (full) | `■■■■■` | Red + pulse |

**R3.4**: Tooltip on hover
- Show slot details: execution IDs, durations, message previews

**R3.5**: Component location
- File: `src/frontend/src/components/AgentNode.vue`
- Replace lines 87-105 (activity indicator section)
- New component: `CapacityMeter.vue`

---

### R4: Dashboard Timeline Swim Lanes

**R4.1**: Organize execution bars into fixed slot lanes
- Current: Execution bars stack vertically within agent row
- New: Each agent row has N sub-rows (lanes) where N = `max_parallel_tasks`
- Each concurrent execution renders in a specific lane (slot 1, 2, 3...)

**R4.2**: Visual design
```
Time →                    10:00    10:05    10:10    10:15
                            │        │        │        │
research-agent (3/5)        │        │        │        │
  Slot 1  ──────────────────┼────────┼────────┤        │
  Slot 2  ──────────────────┼────┤   │        │        │
  Slot 3                    │    └───┼────────┼────────┤
  Slot 4  (empty)           │        │        │        │
  Slot 5  (empty)           │        │        │        │
                            │        │        │        │
writer-agent (1/3)          │        │        │        │
  Slot 1  ──────────────────┼────────┼────────┼────────┤
  Slot 2  (empty)           │        │        │        │
  Slot 3  (empty)           │        │        │        │
```

**R4.3**: Slot assignment algorithm
- When execution starts, assign to lowest available slot number
- Store `slot_number` in execution record (or compute on render)
- Maintain slot assignment for duration of execution

**R4.4**: Empty lanes
- Show faint placeholder lines for unused slots
- Optional: Collapse empty slots with "..." indicator

**R4.5**: Component location
- File: `src/frontend/src/components/ReplayTimeline.vue`
- Modify execution bar positioning logic
- Add lane grid lines

**R4.6**: Lane height
- Each lane: 24px height (matches current execution bar)
- Agent row total height: `max_parallel_tasks * 24px + header`

---

### R5: Backend Implementation

**R5.1**: Database migration
```sql
-- Migration: Add parallel capacity column
ALTER TABLE agent_ownership
ADD COLUMN max_parallel_tasks INTEGER DEFAULT 3 NOT NULL;

-- Constraint: Valid range
-- (Enforced in application layer, SQLite doesn't support CHECK well)
```

**R5.2**: New files
| File | Purpose |
|------|---------|
| `src/backend/services/slot_service.py` | Redis slot management |
| `src/backend/routers/capacity.py` | Capacity API endpoints |

**R5.3**: Modified files
| File | Change |
|------|--------|
| `src/backend/routers/chat.py` | Add slot check before `/task` execution |
| `src/backend/db/agents.py` | Add capacity CRUD methods |
| `src/backend/db_models.py` | Add capacity fields to models |
| `src/backend/database.py` | Migration function |

**R5.4**: Slot service interface
```python
class SlotService:
    async def acquire_slot(self, agent_name: str, execution_id: str) -> bool:
        """Try to acquire a slot. Returns False if at capacity."""

    async def release_slot(self, agent_name: str, execution_id: str) -> None:
        """Release a slot when execution completes."""

    async def get_slot_state(self, agent_name: str) -> SlotState:
        """Get current slot usage for an agent."""

    async def get_all_slot_states(self) -> Dict[str, SlotState]:
        """Get slot states for all agents (Dashboard)."""

    async def cleanup_stale_slots(self) -> int:
        """Remove slots older than TTL. Returns count removed."""
```

---

### R6: Frontend Implementation

**R6.1**: New components
| Component | Purpose |
|-----------|---------|
| `CapacityMeter.vue` | Horizontal bar showing X/Y slots |
| `SwimLaneTimeline.vue` | Timeline with fixed slot lanes (or modify ReplayTimeline) |

**R6.2**: Modified components
| Component | Change |
|-----------|--------|
| `AgentNode.vue` | Replace activity dot with CapacityMeter |
| `ReplayTimeline.vue` | Add swim lane logic |
| `AgentDetail.vue` | Add capacity configuration UI |

**R6.3**: Store changes
| Store | Change |
|-------|--------|
| `network.js` | Add `fetchSlotStates()`, store slot data per agent |

**R6.4**: Polling strategy
- Poll `GET /api/agents/slots` every 5 seconds when Dashboard visible
- Or: WebSocket event `slot_state_changed` for real-time updates

---

### R7: MCP Tools

**R7.1**: New tools
```typescript
// Set agent parallel capacity
set_agent_capacity(agent_name: string, max_parallel_tasks: number): void

// Get agent capacity and current usage
get_agent_capacity(agent_name: string): {
  max_parallel_tasks: number,
  active_slots: number,
  available_slots: number
}
```

**R7.2**: Update existing tool
- `chat_with_agent` with `parallel=true` should respect capacity
- Return clear error when at capacity: `"Agent at capacity (5/5 slots). Retry later."`

---

## Data Flow

### Execution Start
```
┌─────────┐     ┌─────────┐     ┌───────┐     ┌───────────┐
│  Client │────►│ Backend │────►│ Redis │────►│   Agent   │
│         │     │ /task   │     │ slots │     │ Container │
└─────────┘     └────┬────┘     └───────┘     └───────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Check slots  │
              │ SCARD < max? │
              └──────┬───────┘
                     │
         ┌───────────┴───────────┐
         │ YES                   │ NO
         ▼                       ▼
   ┌───────────┐          ┌───────────┐
   │ SADD slot │          │ Return    │
   │ Execute   │          │ 429 error │
   └───────────┘          └───────────┘
```

### Dashboard Update
```
┌───────────┐     ┌─────────┐     ┌───────┐
│ Dashboard │────►│ Backend │────►│ Redis │
│ (poll 5s) │     │ /slots  │     │ SCARD │
└─────┬─────┘     └─────────┘     └───────┘
      │
      ▼
┌─────────────┐
│ Update      │
│ CapacityMeter│
│ SwimLanes   │
└─────────────┘
```

---

## API Specification

### GET /api/agents/{name}/capacity
**Response:**
```json
{
  "agent_name": "research-agent",
  "max_parallel_tasks": 5,
  "active_slots": 3,
  "available_slots": 2,
  "slots": [
    {
      "slot_number": 1,
      "execution_id": "abc123",
      "started_at": "2026-02-28T10:00:00Z",
      "message_preview": "Research the market...",
      "duration_seconds": 45
    },
    {
      "slot_number": 2,
      "execution_id": "def456",
      "started_at": "2026-02-28T10:01:00Z",
      "message_preview": "Analyze competitor...",
      "duration_seconds": 30
    }
  ]
}
```

### PUT /api/agents/{name}/capacity
**Request:**
```json
{
  "max_parallel_tasks": 5
}
```
**Response:** Same as GET

### GET /api/agents/slots (bulk)
**Response:**
```json
{
  "agents": {
    "research-agent": {"max": 5, "active": 3},
    "writer-agent": {"max": 3, "active": 1},
    "orchestrator": {"max": 5, "active": 5}
  },
  "timestamp": "2026-02-28T10:05:00Z"
}
```

### POST /api/agents/{name}/task (updated error)
**429 Response (at capacity):**
```json
{
  "error": "Agent at capacity",
  "detail": "All 5 execution slots are occupied",
  "active_slots": 5,
  "max_parallel_tasks": 5,
  "retry_after_seconds": 30
}
```

---

## Database Schema

### Migration
```python
def _migrate_parallel_capacity():
    """Add parallel capacity column to agent_ownership."""
    cursor.execute("""
        ALTER TABLE agent_ownership
        ADD COLUMN max_parallel_tasks INTEGER DEFAULT 3 NOT NULL
    """)
```

### Updated Model
```python
class AgentOwnership(BaseModel):
    agent_name: str
    owner_id: str
    created_at: datetime
    max_parallel_tasks: int = 3  # NEW
    # ... existing fields
```

---

## Redis Schema

### Slot Tracking (ZSET for TTL support)
```
Key: agent:slots:{name}
Type: Sorted Set (ZSET)
Score: Unix timestamp (execution start time)
Member: execution_id

Operations:
- ZADD agent:slots:research-agent 1709114400 "exec_abc123"
- ZCARD agent:slots:research-agent  # Count active
- ZREM agent:slots:research-agent "exec_abc123"  # Release
- ZREMRANGEBYSCORE agent:slots:research-agent 0 {30_min_ago}  # Cleanup stale
```

### Slot Details (HASH for metadata)
```
Key: agent:slot:{name}:{execution_id}
Type: Hash
Fields:
  - started_at: ISO timestamp
  - message_preview: First 100 chars of message
  - slot_number: Assigned slot (1-N)
TTL: 30 minutes (auto-expire)
```

---

## Implementation Phases

### Phase 1: Backend Foundation (Core)
**Files to create/modify:**
- [ ] `src/backend/db/schema.py` - Add column definition
- [ ] `src/backend/db/migrations.py` - Migration function
- [ ] `src/backend/database.py` - Call migration
- [ ] `src/backend/services/slot_service.py` - NEW: Redis slot management
- [ ] `src/backend/routers/capacity.py` - NEW: Capacity endpoints
- [ ] `src/backend/routers/chat.py` - Add slot check to `/task`
- [ ] `src/backend/db/agents.py` - Add capacity CRUD
- [ ] `src/backend/db_models.py` - Add capacity to models

**Deliverable:** Capacity enforcement working, API available

### Phase 2: Dashboard Capacity Meter
**Files to create/modify:**
- [ ] `src/frontend/src/components/CapacityMeter.vue` - NEW
- [ ] `src/frontend/src/components/AgentNode.vue` - Replace activity dot
- [ ] `src/frontend/src/stores/network.js` - Add slot state fetching

**Deliverable:** Agent nodes show X/Y capacity meter

### Phase 3: Timeline Swim Lanes
**Files to create/modify:**
- [ ] `src/frontend/src/components/ReplayTimeline.vue` - Add lane logic
- [ ] `src/frontend/src/stores/network.js` - Include slot assignment in execution data

**Deliverable:** Timeline shows fixed slot lanes per agent

### Phase 4: Configuration UI & MCP
**Files to create/modify:**
- [ ] `src/frontend/src/views/AgentDetail.vue` - Capacity config UI
- [ ] `src/mcp-server/src/tools/capacity.ts` - NEW: MCP tools
- [ ] `src/mcp-server/src/client.ts` - Capacity client methods

**Deliverable:** Full feature complete

---

## Testing

### Unit Tests
- [ ] Slot acquisition when under capacity
- [ ] Slot rejection when at capacity
- [ ] Slot release on completion
- [ ] Slot release on failure
- [ ] Stale slot cleanup
- [ ] Capacity range validation (1-10)

### Integration Tests
- [ ] Parallel task respects capacity limit
- [ ] 429 response includes correct metadata
- [ ] Dashboard displays accurate slot state
- [ ] Timeline lanes render correctly
- [ ] WebSocket updates slot changes (if implemented)

### Edge Cases
- [ ] Backend restart with active slots (cleanup)
- [ ] Agent restart with active slots
- [ ] Concurrent slot acquisition race condition
- [ ] Slot cleanup doesn't remove active executions

---

## Rollback Plan

1. **Database**: Column is additive, no data loss on rollback
2. **Redis**: Slots auto-expire after 30 min TTL
3. **Frontend**: Feature flag to show old activity dot
4. **API**: New endpoints, no breaking changes to existing

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Capacity enforcement accuracy | 100% (no over-limit executions) |
| Dashboard update latency | < 2 seconds |
| Slot cleanup reliability | No orphaned slots after 1 hour |
| User comprehension | Capacity meter understood without docs |

---

## Open Questions

1. **Queue vs Reject**: When at capacity, should we queue requests or reject immediately?
   - **Recommendation**: Reject with 429 (simpler, caller decides retry strategy)

2. **Slot assignment persistence**: Store slot number in database or compute on render?
   - **Recommendation**: Compute on render (simpler, avoids schema change)

3. **WebSocket vs Polling**: Real-time slot updates or poll every 5s?
   - **Recommendation**: Start with polling, add WebSocket later if needed

4. **Default capacity**: What should new agents default to?
   - **Recommendation**: 3 (conservative, can be increased)

---

## Related Documents

- [Parallel Headless Execution](../memory/feature-flows/parallel-headless-execution.md)
- [Execution Queue](../memory/feature-flows/execution-queue.md)
- [Dashboard Timeline View](../memory/feature-flows/dashboard-timeline-view.md)
- [Agent Network](../memory/feature-flows/agent-network.md)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-28 | Initial requirements document created |
