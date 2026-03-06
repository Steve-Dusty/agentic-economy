# Feature: Execution List Page

## Overview

The Execution List Page (`/executions`) provides a centralized view of all process executions across the platform. Users can monitor execution status, filter by status or process, and navigate to individual execution details.

## User Story

As a process operator, I want to view all process executions in one place so that I can monitor their status, identify failures, and take action when needed.

## Entry Points

1. **NavBar (Primary Navigation)**: `src/frontend/src/components/NavBar.vue:26-31` - "Processes" link highlights for `/executions` paths
2. **ProcessSubNav (Secondary Navigation)**: `src/frontend/src/components/ProcessSubNav.vue:62-66` - "Executions" tab with `PlayCircleIcon`
3. **Process Dashboard Links**: `src/frontend/src/views/ProcessDashboard.vue:190,272` - "View All" links in execution widgets
4. **Process Editor**: `src/frontend/src/views/ProcessEditor.vue:1453` - Redirect after starting execution

## Route Definition

```javascript
// src/frontend/src/router/index.js:102-106
{
  path: '/executions',
  name: 'ExecutionList',
  component: () => import('../views/ExecutionList.vue'),
  meta: { requiresAuth: true }
}
```

---

## Frontend Layer

### Component: ExecutionList.vue

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/views/ExecutionList.vue`

| Section | Lines | Description |
|---------|-------|-------------|
| Template | 1-248 | Page layout with filters, stats cards, table, pagination |
| Script | 250-418 | Component logic with store integration |

### Layout Structure

1. **Header Row** (lines 8-43)
   - Title: "Executions"
   - Subtitle: "Monitor and manage process executions"
   - Auto-refresh indicator (green pulsing dot when live)
   - Pause/Resume button for auto-refresh
   - Manual refresh button

2. **Filters Panel** (lines 46-92)
   - Status dropdown filter (All, Pending, Running, Awaiting Approval, Completed, Failed, Cancelled)
   - Process dropdown filter (populated from unique processes in current data)
   - Clear filters button

3. **Stats Cards** (lines 94-116)
   - Total executions count
   - Completed count (green)
   - Failed count (red)
   - Running count (blue)
   - Total cost (summed from all executions)

4. **Executions Table** (lines 130-227)
   - Columns: Status, Process, Started, Duration, Cost, Actions
   - Clickable rows navigate to execution detail
   - Action buttons: Cancel (for running/pending), Retry (for failed), View

5. **Pagination** (lines 205-226)
   - Shows "Showing X of Y executions"
   - Previous/Next page buttons
   - Disabled states at boundaries

6. **Empty State** (lines 229-244)
   - Shows when no executions match filters
   - Link to `/processes` to create processes

### State Management

**Store**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/stores/executions.js`

| Property | Type | Description |
|----------|------|-------------|
| `executions` | `ref([])` | Array of execution summaries |
| `currentExecution` | `ref(null)` | Currently selected execution detail |
| `loading` | `ref(false)` | Loading state |
| `error` | `ref(null)` | Error message |
| `total` | `ref(0)` | Total count for pagination |
| `filters` | `ref({})` | Current filter values |

**Computed Properties** (lines 32-67):
- `activeExecutions` - Filter for running/pending
- `completedExecutions` - Filter for completed
- `failedExecutions` - Filter for failed
- `stats` - Computed statistics including total cost

**Actions** (lines 69-187):

| Action | Lines | Description |
|--------|-------|-------------|
| `fetchExecutions(options)` | 70-100 | Fetch executions with filters |
| `getExecution(id)` | 102-113 | Get single execution detail |
| `cancelExecution(id)` | 115-122 | Cancel running execution |
| `retryExecution(id)` | 124-131 | Retry failed execution |
| `getStepOutput(executionId, stepId)` | 133-143 | Get step output |
| `getExecutionEvents(id)` | 145-155 | Get execution audit events |
| `startPolling(intervalMs)` | 158-164 | Start auto-refresh polling |
| `stopPolling()` | 166-171 | Stop auto-refresh polling |
| `setFilters(newFilters)` | 174-177 | Apply filters and refetch |
| `clearFilters()` | 179-187 | Reset filters to defaults |

### API Calls

```javascript
// Fetch executions list
await axios.get('/api/executions', {
  params: { status, process_id, limit, offset },
  headers: { Authorization: `Bearer ${token}` }
})

// Cancel execution
await axios.post(`/api/executions/${id}/cancel`, {}, {
  headers: { Authorization: `Bearer ${token}` }
})

// Retry execution
await axios.post(`/api/executions/${id}/retry`, {}, {
  headers: { Authorization: `Bearer ${token}` }
})
```

### Lifecycle Hooks

```javascript
// ExecutionList.vue:283-293
onMounted(() => {
  if (autoRefresh.value) {
    executionsStore.startPolling(30000)  // 30 second interval
  } else {
    executionsStore.fetchExecutions()
  }
})

onUnmounted(() => {
  executionsStore.stopPolling()
})
```

---

## Backend Layer

### API Endpoints

**Router**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/routers/executions.py`

| Method | Endpoint | Lines | Description |
|--------|----------|-------|-------------|
| GET | `/api/executions` | 417-467 | List executions with filters |
| GET | `/api/executions/{id}` | 470-505 | Get execution detail |
| POST | `/api/executions/{id}/cancel` | 508-551 | Cancel running execution |
| POST | `/api/executions/{id}/retry` | 554-614 | Retry failed execution |

### List Executions Endpoint

**`GET /api/executions`** (lines 417-467)

Query Parameters:
- `status` (optional): Filter by execution status
- `process_id` (optional): Filter by process definition ID
- `limit` (default: 50, max: 100): Page size
- `offset` (default: 0): Pagination offset

Authorization:
- Requires `EXECUTION_VIEW` permission
- VIEWER role can only see own executions

Response Model: `ExecutionListResponse` (lines 119-125)

```python
class ExecutionListResponse(BaseModel):
    executions: List[ExecutionSummary]
    total: int
    limit: int
    offset: int
```

### Cancel Execution Endpoint

**`POST /api/executions/{id}/cancel`** (lines 508-551)

Authorization:
- Requires `EXECUTION_CANCEL` permission

Validation:
- Execution must exist
- Status must be `pending`, `running`, or `paused`

Side Effects:
- Updates execution status to `cancelled`
- Logs cancellation with user info

### Retry Execution Endpoint

**`POST /api/executions/{id}/retry`** (lines 554-614)

Authorization:
- Requires `EXECUTION_RETRY` permission

Validation:
- Execution must exist
- Status must be `failed`
- Process definition must exist

Side Effects:
- Creates new execution with same input data
- Links new execution to original via `retry_of` field
- Runs new execution in background task

---

## Data Layer

### Repository: SqliteProcessExecutionRepository

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/services/process_engine/repositories/sqlite_executions.py`

### Database Schema

**Table: `process_executions`** (lines 75-89)

```sql
CREATE TABLE IF NOT EXISTS process_executions (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    process_version TEXT NOT NULL,
    process_name TEXT NOT NULL,
    status TEXT NOT NULL,
    triggered_by TEXT DEFAULT 'manual',
    input_data TEXT DEFAULT '{}',
    output_data TEXT DEFAULT '{}',
    total_cost_amount INTEGER DEFAULT 0,
    total_cost_currency TEXT DEFAULT 'USD',
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_exec_process_id ON process_executions(process_id);
CREATE INDEX IF NOT EXISTS idx_exec_status ON process_executions(status);
CREATE INDEX IF NOT EXISTS idx_exec_started_at ON process_executions(started_at);
```

**Table: `step_executions`** (lines 99-115)

```sql
CREATE TABLE IF NOT EXISTS step_executions (
    execution_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    status TEXT NOT NULL,
    input_data TEXT DEFAULT '{}',
    output_data TEXT DEFAULT '{}',
    error_data TEXT DEFAULT '{}',
    cost_amount INTEGER DEFAULT 0,
    cost_currency TEXT DEFAULT 'USD',
    started_at TEXT,
    completed_at TEXT,
    retry_count INTEGER DEFAULT 0,
    PRIMARY KEY (execution_id, step_id),
    FOREIGN KEY (execution_id) REFERENCES process_executions(id)
);

CREATE INDEX IF NOT EXISTS idx_step_exec_status ON step_executions(status);
```

### Repository Methods

| Method | Lines | Description |
|--------|-------|-------------|
| `list_all(limit, offset, status)` | 310-344 | List executions with optional status filter |
| `list_by_process(process_id, limit, offset)` | 253-280 | List executions for a specific process |
| `list_active()` | 282-308 | List pending/running/paused executions |
| `count(status)` | 346-360 | Count executions with optional filter |
| `get_by_id(id)` | 205-227 | Get single execution with step data |

---

## Execution Statuses

**Enum**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/services/process_engine/domain/enums.py:27-34`

```python
class ExecutionStatus(str, Enum):
    PENDING = "pending"      # Waiting to start
    RUNNING = "running"      # Currently executing
    PAUSED = "paused"        # Waiting for human approval
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"        # Failed with error
    CANCELLED = "cancelled"  # Manually cancelled
```

### Frontend Status Display

**Display Mapping** (ExecutionList.vue:377-388):
- `paused` status displays as "Awaiting Approval" with bell icon
- All other statuses display as-is

**Status Icons** (lines 349-360):
| Status | Icon |
|--------|------|
| pending | hourglass |
| running | arrows-circle |
| completed | checkmark |
| failed | X |
| cancelled | stop |
| paused | pause |
| awaiting_approval | bell |

**Status Colors** (lines 362-373):
| Status | Light Mode | Dark Mode |
|--------|------------|-----------|
| pending | yellow-100/800 | yellow-900/300 |
| running | blue-100/800 | blue-900/300 |
| completed | green-100/800 | green-900/300 |
| failed | red-100/800 | red-900/300 |
| cancelled | gray-100/800 | gray-700/300 |
| paused | purple-100/800 | purple-900/300 |

---

## Filtering and Sorting

### Available Filters

1. **Status Filter** (lines 49-64)
   - All Status (default)
   - Pending
   - Running
   - Awaiting Approval (maps to `paused`)
   - Completed
   - Failed
   - Cancelled

2. **Process Filter** (lines 67-79)
   - Dynamically populated from unique processes in current execution list
   - Shows process name, filters by process ID

### Filter Application

```javascript
// ExecutionList.vue:305-311
function applyFilters() {
  executionsStore.setFilters({
    status: statusFilter.value,
    processId: processFilter.value,
    offset: 0,  // Reset to first page
  })
}
```

### Sorting

Executions are sorted by `created_at DESC` in the repository (lines 329-330 in sqlite_executions.py).

---

## Pagination

### Frontend Implementation

```javascript
// ExecutionList.vue:319-326
function previousPage() {
  const newOffset = Math.max(0, executionsStore.filters.offset - executionsStore.filters.limit)
  executionsStore.setFilters({ offset: newOffset })
}

function nextPage() {
  executionsStore.setFilters({ offset: executionsStore.filters.offset + executionsStore.filters.limit })
}
```

### Page Size

- Default: 50 items per page
- Maximum: 100 items per page (enforced by backend)

---

## Navigation to Execution Detail

### Click Navigation

Clicking any table row navigates to execution detail:

```javascript
// ExecutionList.vue:328-330
function viewExecution(execution) {
  router.push(`/executions/${execution.id}`)
}
```

### View Button

Explicit view button in actions column:

```vue
<!-- ExecutionList.vue:192-198 -->
<router-link
  :to="`/executions/${execution.id}`"
  class="p-1.5 rounded-lg text-blue-600 ..."
  title="View details"
>
  <EyeIcon class="h-4 w-4" />
</router-link>
```

### Detail Page Route

```javascript
// router/index.js:120-124
{
  path: '/executions/:id',
  name: 'ProcessExecutionDetail',
  component: () => import('../views/ProcessExecutionDetail.vue'),
  meta: { requiresAuth: true }
}
```

---

## Relationship to Process Definitions

### Process Association

Each execution is linked to a process definition via:
- `process_id` - UUID of the process definition
- `process_version` - Version string (e.g., "1.0.0")
- `process_name` - Cached name for display

### Process Filter Population

The process filter dropdown is populated from the current execution list:

```javascript
// ExecutionList.vue:272-280
const uniqueProcesses = computed(() => {
  const seen = new Map()
  executionsStore.executions.forEach(e => {
    if (!seen.has(e.process_id)) {
      seen.set(e.process_id, { id: e.process_id, name: e.process_name })
    }
  })
  return Array.from(seen.values())
})
```

---

## Auto-Refresh / Live Updates

### Polling Implementation

```javascript
// stores/executions.js:157-171
let pollInterval = null

function startPolling(intervalMs = 30000) {
  stopPolling()
  fetchExecutions()
  pollInterval = setInterval(() => {
    fetchExecutions()
  }, intervalMs)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}
```

### UI Indicator

```vue
<!-- ExecutionList.vue:18-25 -->
<div class="flex items-center gap-2 text-sm text-gray-500">
  <span
    class="w-2 h-2 rounded-full"
    :class="autoRefresh ? 'bg-green-500 animate-pulse' : 'bg-gray-400'"
  ></span>
  <span>{{ autoRefresh ? 'Live' : 'Paused' }}</span>
</div>
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Invalid execution ID format | 400 | "Invalid execution ID format" |
| Execution not found | 404 | "Execution not found" |
| Invalid status filter | 400 | "Invalid status: {status}" |
| Cannot cancel completed execution | 400 | "Cannot cancel execution in status: {status}" |
| Cannot retry non-failed execution | 400 | "Can only retry failed executions (status: {status})" |
| Unauthorized | 403 | "Forbidden" |

---

## Security Considerations

### Authorization

**Permission Checks** (from `ProcessAuthorizationService`):
- `EXECUTION_VIEW` - Required to list/view executions
- `EXECUTION_CANCEL` - Required to cancel executions
- `EXECUTION_RETRY` - Required to retry executions
- `EXECUTION_TRIGGER` - Required to start new executions

**Role-Based Access**:
- `VIEWER` role can only see own executions
- `OPERATOR` role can view/cancel/retry all executions
- `ADMIN` role has full access

### Audit Logging

All authorization failures are logged:
```python
auth.log_authorization_failure(
    current_user, "execution.list", "execution", None, auth_result.reason
)
```

---

## Related Flows

- **Upstream**: [Process Definition](process-engine/process-definition.md) - Defines executable processes
- **Downstream**: [Process Execution Detail](process-engine/process-execution.md) - Detailed execution view
- **Related**: [Approvals Page](process-engine/human-approval.md) - Handles paused executions
- **Related**: [Process Dashboard](process-engine/process-monitoring.md) - Summary widgets

---

## Testing

### Prerequisites
1. Backend and frontend services running
2. At least one published process definition
3. User with OPERATOR or ADMIN role

### Test Steps

1. **Navigate to Executions Page**
   - Action: Click "Processes" in NavBar, then "Executions" in sub-nav
   - Expected: Page loads with executions table or empty state
   - Verify: URL is `/executions`

2. **Verify Auto-Refresh**
   - Action: Observe the "Live" indicator with green pulsing dot
   - Expected: Page auto-refreshes every 30 seconds
   - Verify: Click "Pause" to stop auto-refresh, indicator changes to "Paused"

3. **Filter by Status**
   - Action: Select "Failed" from status dropdown
   - Expected: Table shows only failed executions
   - Verify: All visible status badges show "Failed"

4. **Filter by Process**
   - Action: Select a process from dropdown
   - Expected: Table shows only executions for that process
   - Verify: Process column shows same name for all rows

5. **Navigate to Detail**
   - Action: Click any row in the table
   - Expected: Navigate to execution detail page
   - Verify: URL is `/executions/{id}`

6. **Cancel Execution** (requires running execution)
   - Action: Click cancel button on running execution
   - Expected: Execution status changes to "cancelled"
   - Verify: Cancel button disappears, status badge updates

7. **Retry Execution** (requires failed execution)
   - Action: Click retry button on failed execution
   - Expected: New execution created, page refreshes
   - Verify: New execution appears in list

8. **Pagination**
   - Action: Click "Next" when more than 50 executions exist
   - Expected: Next page of results loads
   - Verify: "Showing X of Y" updates, Previous button enabled

### Status: Working
