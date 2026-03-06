# Unified Executions Dashboard

> **Requirement ID**: EXEC-022
> **Priority**: HIGH
> **Status**: ⏳ Not Started
> **Created**: 2026-02-05
> **Source**: `docs/planning/WORKFLOW_PRIORITIES_2026-02.md`

---

## Overview

Create a unified execution dashboard showing all task executions across all agents in a single view. This provides visibility into "what happened" across the entire agent fleet, critical for both monitoring orchestrated workflows and tracking Agent-as-a-Service usage.

## Business Context

**Problem**: When agents run scheduled tasks or collaborate, there's no unified view of:
- What happened across the fleet
- What the results were
- Where outputs are stored
- Whether executions succeeded or failed

**Current State**: Execution history is per-agent only (Tasks tab in Agent Detail). To see what happened, users must:
1. Navigate to each agent individually
2. Check the Tasks tab
3. Mentally correlate executions across agents

**Solution**: A unified `/executions` page showing all executions across all accessible agents with filtering, search, and real-time updates.

**Strategic Value**: Essential for both personal monitoring ("how is my company running?") and client visibility ("what has this agent done for me?").

---

## Current State Analysis

### Database Schema

**`schedule_executions` table** (`src/backend/db/schedules.py`):
```sql
CREATE TABLE schedule_executions (
    id TEXT PRIMARY KEY,              -- token_urlsafe(16)
    schedule_id TEXT NOT NULL,        -- FK or "__manual__"
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,             -- pending, running, success, failed
    started_at TEXT NOT NULL,         -- ISO timestamp (UTC)
    completed_at TEXT,
    duration_ms INTEGER,
    message TEXT NOT NULL,            -- Task input
    response TEXT,                    -- Final response
    error TEXT,
    triggered_by TEXT NOT NULL,       -- manual, schedule, agent, user, mcp
    context_used INTEGER,
    context_max INTEGER,
    cost REAL,
    tool_calls TEXT,                  -- JSON array
    execution_log TEXT                -- Full transcript
)
```

### Existing Endpoints

| Endpoint | Scope | Purpose |
|----------|-------|---------|
| `GET /api/agents/{name}/executions` | Per-agent | List executions for one agent |
| `GET /api/agents/{name}/executions/{id}` | Per-execution | Get execution detail |
| `GET /api/agents/{name}/executions/{id}/log` | Per-execution | Get execution transcript |
| `GET /api/agents/{name}/executions/{id}/stream` | Per-execution | SSE stream for live execution |
| `GET /api/agents/execution-stats` | All agents | Aggregate stats (24h) |

### Existing UI Components

- **TasksPanel.vue** (1046 lines): Per-agent execution history with inline details
- **ExecutionDetail.vue** (496 lines): Dedicated page for single execution
- **ReplayTimeline.vue**: Waterfall visualization in Dashboard

---

## Requirements

### R1: Unified Executions API

**R1.1**: New endpoint for cross-agent execution listing
```
GET /api/executions
Query Parameters:
  - agent_name: string (optional, filter by agent)
  - status: string (optional, filter: pending|running|success|failed)
  - triggered_by: string (optional, filter: manual|schedule|agent|mcp)
  - start_time: ISO timestamp (optional, filter executions after this time)
  - end_time: ISO timestamp (optional, filter executions before this time)
  - limit: number (default 50, max 200)
  - offset: number (default 0, for pagination)
  - search: string (optional, search in message/response)
Auth: Returns only executions for agents user can access
Returns: ExecutionListResponse
```

**R1.2**: Response model
```python
class ExecutionListResponse(BaseModel):
    executions: List[ExecutionSummary]
    total_count: int
    has_more: bool
    filters_applied: Dict[str, str]

class ExecutionSummary(BaseModel):
    id: str
    agent_name: str
    agent_display_name: Optional[str]  # From template metadata
    status: str
    triggered_by: str
    message: str  # Truncated to 200 chars
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[int]
    cost: Optional[float]
    has_error: bool
```

**R1.3**: Aggregate statistics endpoint
```
GET /api/executions/stats
Query Parameters:
  - hours: number (default 24, range: 1-168)
  - agent_name: string (optional)
Auth: Scoped to accessible agents
Returns: {
  total_executions: int,
  successful: int,
  failed: int,
  running: int,
  total_cost: float,
  avg_duration_ms: int,
  by_trigger: { manual: int, schedule: int, agent: int, mcp: int },
  by_agent: [{ agent_name, count, success_rate, cost }]
}
```

### R2: Unified Executions Page

**R2.1**: Page location and routing
- Route: `/executions`
- NavBar: Add "Executions" item (visible to admin and user roles, not client)
- Breadcrumb: Dashboard → Executions

**R2.2**: Page layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Executions                                        [Refresh] [⚙] │
├─────────────────────────────────────────────────────────────────┤
│ Stats Cards (4 columns):                                         │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│ │ Total    │ │ Success  │ │ Failed   │ │ Cost     │            │
│ │ 142      │ │ 89%      │ │ 16       │ │ $12.45   │            │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
├─────────────────────────────────────────────────────────────────┤
│ Filters:                                                         │
│ [Agent ▼] [Status ▼] [Trigger ▼] [Time Range ▼] [🔍 Search...] │
├─────────────────────────────────────────────────────────────────┤
│ Execution List (scrollable):                                     │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ ● ruby-agent        success   2m ago   "Process invoice"  │   │
│ │   Schedule • 45s • $0.02 • 12.5K tokens                   │   │
│ ├───────────────────────────────────────────────────────────┤   │
│ │ ◐ researcher        running   now      "Analyze market"   │   │
│ │   Manual • --      • --                              [Stop]│   │
│ ├───────────────────────────────────────────────────────────┤   │
│ │ ✕ crypto-analyst    failed    5m ago   "Check portfolio"  │   │
│ │   Agent • 120s • $0.15 • Error: Rate limited              │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│ [Load More] or infinite scroll                                  │
└─────────────────────────────────────────────────────────────────┘
```

**R2.3**: Execution row interactions
- Click row → Navigate to `/agents/{name}/executions/{id}` (ExecutionDetail page)
- Click agent name → Navigate to `/agents/{name}`
- Stop button (running only) → `POST /api/agents/{name}/executions/{id}/terminate`
- Hover → Show full message in tooltip

**R2.4**: Filter behavior
- Filters update URL query params for shareability
- Filters persist across page navigation (localStorage)
- "Clear filters" resets to defaults
- Filters apply immediately (debounced for search)

### R3: Real-Time Updates

**R3.1**: WebSocket integration
- Subscribe to execution events via existing WebSocket
- Events: `execution_started`, `execution_completed`, `execution_failed`
- New executions appear at top of list
- Running executions update status in-place
- Optional: Sound/toast notification for failures

**R3.2**: Auto-refresh fallback
- Poll every 10 seconds if WebSocket disconnected
- Visual indicator when in polling mode

**R3.3**: Live execution indicator
- Running executions show animated spinner
- "Live" badge links to ExecutionDetail with streaming

### R4: Performance Requirements

**R4.1**: Query optimization
- Index on `(agent_name, started_at DESC)`
- Index on `(status, started_at DESC)`
- Index on `(triggered_by, started_at DESC)`
- Limit default results to prevent slow queries

**R4.2**: Pagination
- Cursor-based pagination preferred (offset can be slow)
- Or: Offset pagination with max 200 results per page
- "Load more" pattern instead of traditional pagination

**R4.3**: Caching
- Stats endpoint cached for 5 seconds
- Execution list not cached (real-time important)

---

## Implementation Plan

### Phase 1: Backend API
1. Create `src/backend/routers/unified_executions.py`
2. Implement `GET /api/executions` with filters and pagination
3. Implement `GET /api/executions/stats` for aggregate metrics
4. Add database indexes for query performance
5. Integrate with existing auth (filter by accessible agents)

### Phase 2: Frontend Page
1. Create `src/frontend/src/views/ExecutionList.vue`
2. Implement stats cards with auto-refresh
3. Implement filter bar with dropdowns and search
4. Implement execution list with click-through
5. Add route to `router/index.js`
6. Add NavBar item

### Phase 3: Real-Time
1. Add WebSocket event handlers for execution events
2. Implement in-place updates for running executions
3. Implement new execution insertion at top
4. Add fallback polling

### Phase 4: Polish
1. URL query param sync for filters
2. localStorage persistence for filter preferences
3. Empty state design
4. Error handling and loading states
5. Mobile responsiveness

---

## API Changes

### New Endpoints

```python
# src/backend/routers/unified_executions.py

@router.get("/api/executions")
async def list_all_executions(
    agent_name: Optional[str] = None,
    status: Optional[str] = None,
    triggered_by: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
) -> ExecutionListResponse:
    """List executions across all accessible agents"""

@router.get("/api/executions/stats")
async def get_execution_stats(
    hours: int = Query(default=24, ge=1, le=168),
    agent_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
) -> ExecutionStatsResponse:
    """Get aggregate execution statistics"""
```

### Database Changes

```sql
-- Add indexes for unified query performance
CREATE INDEX IF NOT EXISTS idx_executions_started_at
  ON schedule_executions(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_executions_status_started
  ON schedule_executions(status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_executions_triggered_started
  ON schedule_executions(triggered_by, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_executions_agent_started
  ON schedule_executions(agent_name, started_at DESC);
```

### WebSocket Events

```json
// New execution started
{
  "type": "execution_started",
  "execution": {
    "id": "abc123",
    "agent_name": "ruby-agent",
    "message": "Process invoice...",
    "triggered_by": "schedule",
    "started_at": "2026-02-05T..."
  }
}

// Execution completed
{
  "type": "execution_completed",
  "execution": {
    "id": "abc123",
    "agent_name": "ruby-agent",
    "status": "success",
    "duration_ms": 45000,
    "cost": 0.02,
    "completed_at": "2026-02-05T..."
  }
}

// Execution failed
{
  "type": "execution_failed",
  "execution": {
    "id": "abc123",
    "agent_name": "ruby-agent",
    "status": "failed",
    "error": "Rate limited",
    "completed_at": "2026-02-05T..."
  }
}
```

---

## Frontend Changes

### New Files

| File | Purpose |
|------|---------|
| `src/frontend/src/views/ExecutionList.vue` | Main executions page |
| `src/frontend/src/stores/executions.js` | Pinia store for execution state |
| `src/frontend/src/composables/useExecutionFilters.js` | Filter logic composable |

### Modified Files

| File | Change |
|------|--------|
| `src/frontend/src/router/index.js` | Add `/executions` route |
| `src/frontend/src/components/NavBar.vue` | Add "Executions" menu item |
| `src/frontend/src/utils/websocket.js` | Handle execution events |

---

## Security Considerations

1. **Access control**: Only show executions for agents user can access
2. **Rate limiting**: Prevent abuse of list endpoint
3. **Search injection**: Sanitize search parameter for SQL
4. **Sensitive data**: Don't expose full execution log in list view

---

## Testing Checklist

- [ ] List shows executions from multiple agents
- [ ] Filter by agent works correctly
- [ ] Filter by status works correctly
- [ ] Filter by trigger type works correctly
- [ ] Time range filter works correctly
- [ ] Search finds matches in message/response
- [ ] Pagination loads more results
- [ ] Click through to execution detail works
- [ ] Running executions show live indicator
- [ ] Stop button terminates execution
- [ ] WebSocket updates list in real-time
- [ ] Stats cards show correct aggregates
- [ ] Admin sees all executions
- [ ] User sees only own + shared agent executions
- [ ] Client role cannot access page (if implemented)
- [ ] Empty state displays correctly
- [ ] Error state displays correctly

---

## Related Documents

- `docs/memory/feature-flows/execution-detail-page.md` - Existing execution detail
- `docs/memory/feature-flows/tasks-tab.md` - Per-agent execution history
- `docs/memory/feature-flows/execution-queue.md` - Execution queue system
- `docs/planning/WORKFLOW_PRIORITIES_2026-02.md` - Strategic context

---

## Success Criteria

1. User can see all executions across all their agents in one view
2. Real-time updates show new executions and status changes
3. Filters enable finding specific executions quickly
4. Stats provide at-a-glance health metrics
5. Page performs well with 1000+ executions
6. Integrates seamlessly with existing ExecutionDetail page
