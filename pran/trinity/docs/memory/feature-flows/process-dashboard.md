# Feature: Process Dashboard

## Overview

The Process Dashboard provides a centralized analytics and overview view of process engine activity. It displays key metrics (success rate, execution count, total cost), trend visualizations, process health cards, step performance analysis, and quick access to recent executions and published processes.

## User Story

As a platform administrator or process manager, I want to see an at-a-glance overview of all process execution metrics so that I can monitor system health, identify bottlenecks, and track costs.

## Entry Points

- **UI**: `src/frontend/src/components/ProcessSubNav.vue:57-59` - "Dashboard" tab link with ChartBarIcon
- **Route**: `/process-dashboard` defined in `src/frontend/src/router/index.js:126-130`
- **API Endpoints**:
  - `GET /api/processes/analytics/trends?days={n}` - Daily execution/cost trends
  - `GET /api/processes/analytics/all?days={n}` - Per-process metrics
  - `GET /api/executions/analytics/steps?days={n}&limit={n}` - Step performance data
  - `GET /api/processes` - Process list
  - `GET /api/executions` - Execution list

---

## Frontend Layer

### Components

#### Main View
- `src/frontend/src/views/ProcessDashboard.vue` (417 lines)
  - Uses `NavBar.vue` and `ProcessSubNav.vue` for navigation
  - Six overall stat cards (Total Processes, Published, Executions, Success Rate, Running Now, Total Cost)
  - Two TrendChart components (Execution Trend, Cost Trend)
  - Process Health cards grid (top 5 processes by execution count)
  - Slowest Steps and Most Expensive Steps lists
  - Recent Executions and Published Processes panels
  - Quick Actions section

#### Sub-components
- `src/frontend/src/components/ProcessSubNav.vue:57-59` - Dashboard link
  ```vue
  {
    path: '/process-dashboard',
    label: 'Dashboard',
    icon: ChartBarIcon,
  }
  ```

- `src/frontend/src/components/process/TrendChart.vue` (181 lines)
  - Stacked bar chart for executions (green=completed, red=failed)
  - Blue bar chart for costs
  - Supports `chartType`: 'executions' | 'cost' | 'success_rate'
  - Tooltip on hover with date and values
  - Y-axis labels with dynamic max value
  - X-axis shows day numbers

### State Management

Three Pinia stores are used:

#### Analytics Store
- `src/frontend/src/stores/analytics.js` (161 lines)

| State | Type | Description |
|-------|------|-------------|
| `trendData` | Object | Raw trend response from API |
| `processMetrics` | Array | Per-process metrics list |
| `stepPerformance` | Object | Slowest/most expensive steps |
| `loading` | Boolean | Loading state |
| `error` | String | Error message |
| `selectedDays` | Number | Time period filter (default: 30) |

| Getter | Returns |
|--------|---------|
| `dailyTrends` | Array of daily trend objects |
| `totalExecutions` | Total execution count |
| `overallSuccessRate` | Success rate percentage |
| `totalCost` | Formatted total cost string |
| `slowestSteps` | Array of slowest steps |
| `mostExpensiveSteps` | Array of most expensive steps |
| `topProcessesByExecutions` | Top 5 processes by execution count |
| `processesWithIssues` | Processes with <80% success rate |

| Action | Description |
|--------|-------------|
| `fetchTrendData(days)` | GET `/api/processes/analytics/trends` |
| `fetchAllProcessMetrics(days)` | GET `/api/processes/analytics/all` |
| `fetchProcessMetrics(processId, days)` | GET `/api/processes/{id}/analytics` |
| `fetchStepPerformance(days, limit)` | GET `/api/executions/analytics/steps` |
| `fetchAllAnalytics(days)` | Calls all three fetch methods in parallel |
| `setDays(days)` | Update selectedDays and refresh data |

#### Processes Store
- `src/frontend/src/stores/processes.js` (173 lines)

| Action | Description |
|--------|-------------|
| `fetchProcesses()` | GET `/api/processes` - populates `processes` array |
| `executeProcess(id, inputData)` | POST `/api/executions/processes/{id}/execute` |

#### Executions Store
- `src/frontend/src/stores/executions.js` (214 lines)

| Getter | Description |
|--------|-------------|
| `stats.running` | Count of currently running executions |

| Action | Description |
|--------|-------------|
| `fetchExecutions()` | GET `/api/executions` - populates `executions` array |

### API Calls

On mount and refresh:
```javascript
async function refreshData() {
  loading.value = true
  try {
    await Promise.all([
      processesStore.fetchProcesses(),
      executionsStore.fetchExecutions(),
      analyticsStore.fetchAllAnalytics(selectedDays.value),
    ])
  } finally {
    loading.value = false
  }
}
```

Time range change:
```javascript
function onDaysChange() {
  analyticsStore.fetchAllAnalytics(selectedDays.value)
}
```

---

## Backend Layer

### Endpoints

#### Trend Analytics
- **File**: `src/backend/routers/processes.py:964-992`
- **Route**: `GET /api/processes/analytics/trends`
- **Handler**: `get_process_trends()`

```python
@router.get("/analytics/trends")
async def get_process_trends(
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    process_id: Optional[str] = Query(None, description="Filter by process ID"),
):
```

**Response**:
```json
{
  "days": 30,
  "daily_trends": [
    {
      "date": "2026-01-15",
      "execution_count": 12,
      "completed_count": 10,
      "failed_count": 2,
      "total_cost": 1.25,
      "success_rate": 83.3
    }
  ],
  "total_executions": 145,
  "total_completed": 132,
  "total_failed": 13,
  "overall_success_rate": 91.0,
  "total_cost": "$45.67"
}
```

#### All Process Metrics
- **File**: `src/backend/routers/processes.py:995-1018`
- **Route**: `GET /api/processes/analytics/all`
- **Handler**: `get_all_process_analytics()`

```python
@router.get("/analytics/all")
async def get_all_process_analytics(
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
):
```

**Response**:
```json
{
  "processes": [
    {
      "process_id": "proc_abc123",
      "process_name": "Customer Onboarding",
      "execution_count": 45,
      "completed_count": 42,
      "failed_count": 3,
      "running_count": 0,
      "success_rate": 93.3,
      "average_duration_seconds": 125.5,
      "average_cost": "$0.85",
      "total_cost": "$38.25",
      "min_duration_seconds": 45.2,
      "max_duration_seconds": 310.8,
      "min_cost": "$0.25",
      "max_cost": "$2.15"
    }
  ],
  "days": 30
}
```

#### Single Process Metrics
- **File**: `src/backend/routers/processes.py:935-961`
- **Route**: `GET /api/processes/{process_id}/analytics`
- **Handler**: `get_process_analytics()`

#### Step Performance
- **File**: `src/backend/routers/executions.py:717-737`
- **Route**: `GET /api/executions/analytics/steps`
- **Handler**: `get_step_analytics()`

```python
@router.get("/analytics/steps")
async def get_step_analytics(
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    limit: int = Query(10, ge=1, le=50, description="Number of steps to return per category"),
):
```

**Response**:
```json
{
  "slowest_steps": [
    {
      "step_id": "research_analysis",
      "step_name": "research_analysis",
      "process_name": "Due Diligence",
      "execution_count": 28,
      "average_duration_seconds": 245.3,
      "total_cost": "$12.50",
      "average_cost": "$0.45",
      "failure_rate": 7.1
    }
  ],
  "most_expensive_steps": [
    {
      "step_id": "document_generation",
      "step_name": "document_generation",
      "process_name": "Report Generator",
      "execution_count": 15,
      "average_duration_seconds": 89.2,
      "total_cost": "$25.00",
      "average_cost": "$1.67",
      "failure_rate": 0.0
    }
  ]
}
```

### Analytics Service

- **File**: `src/backend/services/process_engine/services/analytics.py` (500 lines)

#### Data Classes

| Class | Purpose |
|-------|---------|
| `ProcessMetrics` | Per-process aggregated metrics |
| `DailyTrend` | Single day's execution data |
| `TrendData` | Aggregated trend over time period |
| `StepPerformanceEntry` | Single step's performance metrics |
| `StepPerformance` | Slowest and most expensive steps |

#### ProcessAnalytics Class

```python
class ProcessAnalytics:
    def __init__(
        self,
        definition_repo: ProcessDefinitionRepository,
        execution_repo: ProcessExecutionRepository,
    ):
```

| Method | Description |
|--------|-------------|
| `get_process_metrics(process_id, days)` | Metrics for single process |
| `get_all_process_metrics(days)` | Metrics for all published processes |
| `get_trend_data(days, process_id)` | Daily breakdown of executions |
| `get_step_performance(days, limit)` | Slowest and most expensive steps |
| `_calculate_metrics(process_id, process_name, executions)` | Internal aggregation helper |

#### Metrics Calculation Logic

1. **Success Rate**: `(completed_count / (completed_count + failed_count)) * 100`
2. **Average Duration**: Sum of durations / count of executions with duration
3. **Total Cost**: Sum of all execution costs
4. **Average Cost**: Total cost / count of executions with cost

### Database Operations

The analytics service queries from:
- `SqliteProcessDefinitionRepository` - Process definitions (for names, published status)
- `SqliteProcessExecutionRepository` - Execution records (for metrics calculation)

**Time Window Filtering**:
```python
cutoff = datetime.now(timezone.utc) - timedelta(days=days)
recent_executions = [
    e for e in executions
    if e.started_at and e.started_at >= cutoff
]
```

---

## UI Components Detail

### Overall Stats Cards (6 cards)
| Metric | Source | Color |
|--------|--------|-------|
| Total Processes | `processesStore.processes.length` | Gray |
| Published | Filtered processes with `status === 'published'` | Green |
| Executions (Nd) | `analyticsStore.totalExecutions` | Gray |
| Success Rate | `analyticsStore.overallSuccessRate` | Green/Yellow/Red based on value |
| Running Now | `executionsStore.stats.running` | Blue |
| Total Cost | `analyticsStore.totalCost` | Gray |

### Success Rate Color Logic
```javascript
const successRateColor = computed(() => {
  const rate = analyticsStore.overallSuccessRate
  if (rate >= 80) return 'text-green-600 dark:text-green-400'
  if (rate >= 50) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
})
```

### TrendChart Component

Props:
```javascript
{
  title: String,      // Chart title
  data: Array,        // Daily trend data
  days: Number,       // Number of days to display
  chartType: String,  // 'executions' | 'cost' | 'success_rate'
}
```

Bar height calculation:
```javascript
function getBarHeight(value) {
  if (maxValue.value === 0) return 0
  return Math.max((value / maxValue.value) * 100, 0)
}
```

### Process Health Cards
- Displays top 5 processes by execution count
- Click navigates to process detail (`/processes/{id}`)
- Shows: process name, success rate badge, execution count, avg time, avg cost

Health badge colors:
```javascript
function getHealthBadgeClass(successRate) {
  if (successRate >= 80) return 'bg-green-100 text-green-700'
  if (successRate >= 50) return 'bg-yellow-100 text-yellow-700'
  return 'bg-red-100 text-red-700'
}
```

### Time Range Selector
Options: 7, 30, 90 days (default: 30)

```html
<select v-model="selectedDays" @change="onDaysChange">
  <option :value="7">Last 7 days</option>
  <option :value="30">Last 30 days</option>
  <option :value="90">Last 90 days</option>
</select>
```

---

## Data Flow

```
User visits /process-dashboard
        │
        ▼
ProcessDashboard.vue mounted
        │
        ▼
    refreshData()
        │
        ├──► processesStore.fetchProcesses()
        │         └──► GET /api/processes
        │
        ├──► executionsStore.fetchExecutions()
        │         └──► GET /api/executions
        │
        └──► analyticsStore.fetchAllAnalytics(30)
                  │
                  ├──► GET /api/processes/analytics/trends?days=30
                  ├──► GET /api/processes/analytics/all?days=30
                  └──► GET /api/executions/analytics/steps?days=30&limit=10
                              │
                              ▼
                      ProcessAnalytics service
                              │
                              ├── get_trend_data()
                              ├── get_all_process_metrics()
                              └── get_step_performance()
                                        │
                                        ▼
                              Query execution repos
                              Filter by time window
                              Aggregate metrics
                                        │
                                        ▼
                              Return computed metrics
        │
        ▼
Vue reactive updates render charts and cards
```

---

## Error Handling

| Error Case | HTTP Status | Handling |
|------------|-------------|----------|
| Invalid days parameter | 422 | Pydantic validation (1-365) |
| Invalid process_id format | 400 | ProcessId parse error |
| Process not found | 404 | Repository returns None |
| Auth failure | 403 | Permission denied |
| Database error | 500 | Logged, generic error returned |

Frontend error handling:
```javascript
} catch (err) {
  console.error('Failed to fetch trend data:', err)
  error.value = err.response?.data?.detail || 'Failed to load trend data'
}
```

---

## Security Considerations

- **Authentication Required**: All API endpoints require valid JWT token
- **Authorization**: `CurrentUser` dependency validates user access
- **No Process-Level ACL**: All authenticated users can view analytics for all processes
- **Rate Limiting**: None (dashboard is typically low-frequency access)

---

## Performance Considerations

- **Parallel Data Fetching**: Three analytics endpoints called in parallel via `Promise.all`
- **Time Window Filtering**: In-memory filtering after database fetch (may need optimization for large datasets)
- **Execution Limit**: Default 10,000 execution limit per query
- **No Pagination**: Step performance and trend data returned in full

---

## Related Flows

- **Upstream**: [Process List](process-engine/process-definition.md) - Navigation from /processes
- **Downstream**: [Process Execution Detail](process-engine/process-execution.md) - Click on recent execution
- **Related**: [Process Analytics](process-engine/process-analytics.md) - Detailed analytics documentation

---

## Quick Actions

| Action | Route | Description |
|--------|-------|-------------|
| Create Process | `/processes/new` | Opens ProcessEditor for new process |
| View All Executions | `/executions` | Goes to ExecutionList page |
| Manage Processes | `/processes` | Goes to ProcessList page |

---

## Testing

### Prerequisites
- Backend running on `localhost:8000`
- At least one published process with executions
- User authenticated

### Test Steps

1. **Navigate to Dashboard**
   - Action: Click "Dashboard" in ProcessSubNav
   - Expected: Dashboard loads with stats cards
   - Verify: No console errors, data populates

2. **Change Time Range**
   - Action: Select "Last 7 days" from dropdown
   - Expected: Charts and metrics update
   - Verify: API calls with `?days=7`

3. **Refresh Data**
   - Action: Click refresh button (ArrowPathIcon)
   - Expected: Button spins, data reloads
   - Verify: All four API calls made

4. **Process Health Cards**
   - Action: Click on a process health card
   - Expected: Navigate to `/processes/{id}`
   - Verify: Process editor opens

5. **Execute from Dashboard**
   - Action: Click "Execute" on published process
   - Expected: Execution starts, recent executions updates
   - Verify: New execution appears in list

6. **View Execution Detail**
   - Action: Click on recent execution row
   - Expected: Navigate to `/executions/{id}`
   - Verify: Execution detail page opens

### Edge Cases
- Empty state: No processes or executions
- All failed executions: Success rate 0%, red color
- Very long step names: Truncation with ellipsis

---

## Revision History

| Date | Change |
|------|--------|
| 2026-01-21 | Initial documentation created |
