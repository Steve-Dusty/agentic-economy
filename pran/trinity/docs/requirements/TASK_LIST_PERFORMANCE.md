# Task List Performance Optimization (PERF-001)

> **Status**: ✅ IMPLEMENTED
> **Priority**: MEDIUM
> **Created**: 2026-02-21
> **Implemented**: 2026-02-21
> **Author**: Eugene / Claude

## Overview

Optimize the task loading performance on the Agent Detail page's Tasks tab. When agents have many executions (100+), the current implementation transfers excessive data and causes slow load times.

## Problem Statement

When loading the Tasks tab, the API endpoint `/api/agents/{name}/executions` returns the full `execution_log` field for every execution record. This field contains the complete Claude Code transcript as JSON and can be **100KB+ per execution**.

With 100 executions (the current frontend limit), this means:
- **10+ MB of data transferred** on every tab load
- **Most data is never displayed** - the list view only shows status, message preview, duration, cost
- **Slow perceived performance** - users wait for data they don't see

### Evidence

**Database Query** (`db/schedules.py:628-633`):
```python
cursor.execute("""
    SELECT * FROM schedule_executions
    WHERE agent_name = ?
    ORDER BY started_at DESC
    LIMIT ?
""", (agent_name, limit))
```

**Response Model** (`routers/schedules.py:109-127`):
```python
class ExecutionResponse(BaseModel):
    # ... basic fields ...
    response: Optional[str]           # Can be large
    error: Optional[str]              # Can be large
    tool_calls: Optional[str]         # JSON array
    execution_log: Optional[str]      # <<<< 100KB+ per execution
```

**Frontend Usage** (`TasksPanel.vue:132-210`):
- List view only displays: status, triggered_by, started_at, message (truncated), duration_ms, cost, context_used
- `response` and `error` only shown when task is **expanded**
- `execution_log` only used in the **Execution Log Modal** (separate API call already exists)

## Solution: Lightweight List Endpoint

Create a summary response model that excludes heavy fields for list views.

### Architecture

```
Current (inefficient):
┌─────────────┐     ┌─────────────────────────────────────┐
│ TasksPanel  │────▶│ GET /api/agents/{name}/executions   │
│ loads tab   │     │ Returns: ALL fields including       │
└─────────────┘     │ execution_log (100KB × 100 = 10MB)  │
                    └─────────────────────────────────────┘

Proposed (efficient):
┌─────────────┐     ┌─────────────────────────────────────┐
│ TasksPanel  │────▶│ GET /api/agents/{name}/executions   │
│ loads tab   │     │ Returns: Summary fields only        │
└─────────────┘     │ (~1KB × 100 = 100KB)                │
                    └─────────────────────────────────────┘
        │
        │ (on expand)
        ▼
┌─────────────┐     ┌─────────────────────────────────────┐
│ User clicks │────▶│ GET /api/agents/{name}/executions/  │
│ expand task │     │ {id} - Returns full details         │
└─────────────┘     └─────────────────────────────────────┘
```

## Requirements

### REQ-1: Lightweight Execution Summary Model

Create `ExecutionSummary` response model excluding heavy fields.

**File**: `src/backend/routers/schedules.py`

```python
class ExecutionSummary(BaseModel):
    """Lightweight execution for list views - excludes large text fields."""
    id: str
    schedule_id: str
    agent_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    message: str
    triggered_by: str
    # Observability fields (small)
    context_used: Optional[int] = None
    context_max: Optional[int] = None
    cost: Optional[float] = None
    # Origin tracking (small)
    source_user_id: Optional[int] = None
    source_user_email: Optional[str] = None
    source_agent_name: Optional[str] = None
    source_mcp_key_id: Optional[str] = None
    source_mcp_key_name: Optional[str] = None
    # Session resume (small)
    claude_session_id: Optional[str] = None

    # EXCLUDED (large):
    # - response: Optional[str]      # Full response text
    # - error: Optional[str]         # Full error text
    # - tool_calls: Optional[str]    # JSON array of tool calls
    # - execution_log: Optional[str] # Full Claude Code transcript

    class Config:
        from_attributes = True
```

### REQ-2: Optimized Database Query

Create `get_agent_executions_summary()` that selects only needed columns.

**File**: `src/backend/db/schedules.py`

```python
def get_agent_executions_summary(self, agent_name: str, limit: int = 50) -> List[dict]:
    """Get execution summaries for list view - excludes large text fields."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id, schedule_id, agent_name, status, started_at, completed_at,
                duration_ms, message, triggered_by, context_used, context_max, cost,
                source_user_id, source_user_email, source_agent_name,
                source_mcp_key_id, source_mcp_key_name, claude_session_id
            FROM schedule_executions
            WHERE agent_name = ?
            ORDER BY started_at DESC
            LIMIT ?
        """, (agent_name, limit))
        return [dict(row) for row in cursor.fetchall()]
```

### REQ-3: Update List Endpoint Response Type

Change `/api/agents/{name}/executions` to return `ExecutionSummary` list.

**File**: `src/backend/routers/schedules.py`

```python
@router.get("/{name}/executions", response_model=List[ExecutionSummary])
async def get_agent_executions(
    name: AuthorizedAgent,
    limit: int = 50
):
    """Get execution summaries for an agent (lightweight for list views)."""
    executions = db.get_agent_executions_summary(name, limit=limit)
    return executions
```

### REQ-4: Composite Database Index

Add composite index for the common query pattern.

**File**: `src/backend/database.py`

```python
# Add to migrations section
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_executions_agent_started
    ON schedule_executions(agent_name, started_at DESC)
""")
```

This index optimizes the `WHERE agent_name = ? ORDER BY started_at DESC` query pattern.

### REQ-5: Frontend Lazy Loading for Details (Optional Enhancement)

When user expands a task, fetch `response` and `error` on demand if not already loaded.

**File**: `src/frontend/src/components/TasksPanel.vue`

This is optional - the current behavior of showing inline `response`/`error` from the list response can continue, but the summary endpoint won't include them. If inline expansion is desired, the frontend would need to fetch details on expand.

**Decision**: For simplicity, remove inline expand behavior for response/error. Users who need details click through to Execution Detail page (which already fetches full data).

## Files Changed

| File | Change |
|------|--------|
| `src/backend/routers/schedules.py` | Add `ExecutionSummary` model, update endpoint |
| `src/backend/db/schedules.py` | Add `get_agent_executions_summary()` method |
| `src/backend/database.py` | Add composite index, expose new method |
| `src/frontend/src/components/TasksPanel.vue` | Remove inline expand for response/error (optional) |

## Performance Impact

| Metric | Before | After |
|--------|--------|-------|
| **Data transferred** | ~10 MB | ~100 KB |
| **Columns fetched** | 18 (SELECT *) | 18 (explicit, no TEXT blobs) |
| **Index used** | `idx_executions_agent` (partial) | `idx_executions_agent_started` (covering) |

**Expected improvement**: 50-100x reduction in data transfer, sub-second load times.

## Backward Compatibility

- The `/api/agents/{name}/executions` endpoint changes response shape (removes fields)
- Existing `GET /api/agents/{name}/executions/{id}` continues returning full `ExecutionResponse`
- Frontend `TasksPanel.vue` does not use the removed fields in list view (verified)
- MCP tools that use execution lists may need review (if any)

## Testing

### Test Case 1: List Loads Fast
1. Create agent with 50+ executions
2. Navigate to Tasks tab
3. **Expected**: Tab loads in < 1 second
4. **Verify**: Network tab shows response < 200 KB

### Test Case 2: Details Still Available
1. Click on any task row to expand
2. **Expected**: Task details (status, cost, duration) display correctly
3. Click "View Details" button
4. **Expected**: Execution Detail page shows full response/error/transcript

### Test Case 3: Response/Error Display
1. Find a failed task in the list
2. **Expected**: Status badge shows "failed" (visible in summary)
3. **Expected**: Error details visible on Execution Detail page (not inline)

## Related Flows

- **Primary**: [tasks-tab.md](../memory/feature-flows/tasks-tab.md) - Tasks tab feature documentation
- **Related**: [execution-detail-page.md](../memory/feature-flows/execution-detail-page.md) - Full execution details
- **Related**: [execution-log-viewer.md](../memory/feature-flows/execution-log-viewer.md) - Execution transcript modal

## Revision History

| Date | Changes |
|------|---------|
| 2026-02-21 | Initial requirements document |
