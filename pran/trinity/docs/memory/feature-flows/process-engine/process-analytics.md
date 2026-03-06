# Feature: Process Analytics & Cost Tracking

> Metrics, success rates, duration trends, cost aggregation, and threshold alerts

---

## Overview

Process Analytics provides comprehensive visibility into process execution performance and costs. This feature enables operators to monitor process health, identify bottlenecks, and control costs through configurable threshold alerts.

**Key Capabilities:**
1. **Per-Process Metrics** - Success rates, durations, costs for individual processes
2. **Trend Analysis** - Daily execution counts and costs over configurable time windows
3. **Step Performance** - Identifies slowest and most expensive steps across all processes
4. **Cost Threshold Alerts** - Automatic alerting when costs exceed configured limits

---

## User Story

As a platform operator, I want to view analytics about process executions so that I can identify performance issues, track costs, and set alerts for budget overruns.

---

## Entry Points

- **UI**: ProcessDashboard at `/process-dashboard` - `src/frontend/src/views/ProcessDashboard.vue`
- **UI**: NavBar "Alerts" link - badge shows active alert count
- **API**: `GET /api/processes/{id}/analytics` - Single process metrics
- **API**: `GET /api/processes/analytics/trends` - Trend data with time filtering
- **API**: `GET /api/processes/analytics/all` - Metrics for all published processes
- **API**: `GET /api/executions/analytics/steps` - Step-level performance data
- **API**: `GET /api/alerts` - Cost alerts listing

---

## Architecture

```
Frontend                                Backend                                  Database

ProcessDashboard.vue                    processes.py                             trinity_processes.db
    |                                       |                                        |
    +-- fetchAllAnalytics() ------------> GET /analytics/all                         |
    |                                       |                                        |
    +-- fetchTrendData() ---------------> GET /analytics/trends                      |
    |                                       |                                        |
    +-- fetchStepPerformance() ---------> GET /analytics/steps ----+                 |
    |                                       |                      |                 |
    v                                       v                      |                 |
analytics.js store                      analytics.py               |                 |
    |                                       |                      |                 |
    +-- processMetrics                      +-- ProcessAnalytics   |                 |
    +-- dailyTrends                             |                  |                 |
    +-- slowestSteps                            +-- get_process_metrics()            |
    +-- mostExpensiveSteps                      +-- get_trend_data()                 |
                                                +-- get_step_performance()           |
                                                    |                                |
                                                    v                                |
                                            ProcessExecutionRepository  <----------->+

                                        alerts.py                                trinity_alerts.db
                                            |                                        |
Alerts Page                                 +-- CostAlertService                     |
    |                                           |                                    |
    +-- list_alerts() ------------------> GET /api/alerts                            |
    +-- dismiss_alert() ----------------> POST /api/alerts/{id}/dismiss              |
    +-- set_threshold() ----------------> PUT /api/alerts/thresholds/{process_id}    |
```

---

## Frontend Layer

### ProcessDashboard.vue

**File**: `src/frontend/src/views/ProcessDashboard.vue`

| Section | Lines | Description |
|---------|-------|-------------|
| Time Period Selector | 18-27 | Select dropdown (7/30/90 days) |
| Summary Cards | 41-66 | Total processes, published, executions, success rate, running, cost |
| Trend Charts | 69-86 | TrendChart components for executions and cost |
| Process Health Cards | 89-123 | Top processes by executions with health badges |
| Step Performance | 126-182 | Slowest steps and most expensive steps tables |
| Recent Executions | 185-220 | Latest 5 executions with status badges |

**Key Methods:**

```javascript
// ProcessDashboard.vue:341-352 - refreshData()
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

// ProcessDashboard.vue:354-356 - onDaysChange()
function onDaysChange() {
  analyticsStore.fetchAllAnalytics(selectedDays.value)
}
```

### TrendChart.vue

**File**: `src/frontend/src/components/process/TrendChart.vue`

| Feature | Lines | Description |
|---------|-------|-------------|
| Props | 106-124 | title, data, days, chartType (executions/cost/success_rate) |
| Bar Height Calculation | 148-156 | getBarHeight(), getCostBarHeight() based on max values |
| Color Coding | 158-162 | getSuccessRateColor() - green (>=80%), yellow (>=50%), red |
| Stacked Bars | 46-57 | Completed (green) + Failed (red) stacked bars for executions |
| Tooltip | 28-42 | Hover tooltip showing date and values |

### Analytics Store

**File**: `src/frontend/src/stores/analytics.js`

| State | Description |
|-------|-------------|
| `trendData` | Raw trend response from API |
| `processMetrics` | Array of per-process metrics |
| `stepPerformance` | Slowest and most expensive steps |
| `selectedDays` | Current time window (7/30/90) |

| Getter | Lines | Description |
|--------|-------|-------------|
| `dailyTrends` | 22 | `trendData.daily_trends` array |
| `totalExecutions` | 24 | Sum from trend data |
| `overallSuccessRate` | 26 | Percentage from trend data |
| `totalCost` | 28 | Formatted cost string |
| `slowestSteps` | 30 | From stepPerformance |
| `mostExpensiveSteps` | 32 | From stepPerformance |
| `topProcessesByExecutions` | 34-38 | Sorted top 5 processes |

| Action | Lines | Description |
|--------|-------|-------------|
| `fetchTrendData()` | 45-62 | GET `/api/processes/analytics/trends?days={days}` |
| `fetchAllProcessMetrics()` | 64-80 | GET `/api/processes/analytics/all?days={days}` |
| `fetchProcessMetrics()` | 82-93 | GET `/api/processes/{id}/analytics?days={days}` |
| `fetchStepPerformance()` | 95-111 | GET `/api/executions/analytics/steps?days={days}&limit={limit}` |
| `fetchAllAnalytics()` | 113-129 | Parallel fetch of all three endpoints |

---

## Backend Layer

### Analytics Endpoints

**File**: `src/backend/routers/processes.py`

| Endpoint | Lines | Handler |
|----------|-------|---------|
| `GET /{id}/analytics` | 935-961 | `get_process_analytics()` |
| `GET /analytics/trends` | 964-992 | `get_process_trends()` |
| `GET /analytics/all` | 995-1019 | `get_all_process_analytics()` |
| `GET /{id}/cost-stats` | 866-927 | `get_process_cost_stats()` |

**File**: `src/backend/routers/executions.py`

| Endpoint | Lines | Handler |
|----------|-------|---------|
| `GET /analytics/steps` | 717-737 | `get_step_analytics()` |

### ProcessAnalytics Service

**File**: `src/backend/services/process_engine/services/analytics.py`

#### Data Classes

| Class | Lines | Fields |
|-------|-------|--------|
| `ProcessMetrics` | 32-67 | process_id, process_name, execution_count, completed_count, failed_count, running_count, success_rate, average_duration_seconds, average_cost, total_cost, min/max_duration_seconds, min/max_cost |
| `DailyTrend` | 70-88 | date, execution_count, completed_count, failed_count, total_cost, success_rate |
| `TrendData` | 91-111 | days, daily_trends, total_executions, total_completed, total_failed, overall_success_rate, total_cost |
| `StepPerformanceEntry` | 114-136 | step_id, step_name, process_name, execution_count, average_duration_seconds, total_cost, average_cost, failure_rate |
| `StepPerformance` | 139-149 | slowest_steps, most_expensive_steps |

#### Service Methods

| Method | Lines | Description |
|--------|-------|-------------|
| `get_process_metrics()` | 170-210 | Calculate metrics for single process with time window |
| `get_all_process_metrics()` | 212-255 | Calculate metrics for all published processes |
| `get_trend_data()` | 257-344 | Daily breakdowns with optional process filter |
| `get_step_performance()` | 346-446 | Aggregate step data, return slowest and most expensive |
| `_calculate_metrics()` | 448-500 | Internal calculation from execution list |

#### Metrics Calculation Logic

```python
# analytics.py:448-500 - _calculate_metrics()
def _calculate_metrics(self, process_id, process_name, executions) -> ProcessMetrics:
    metrics = ProcessMetrics(process_id=process_id, process_name=process_name)

    durations = []
    costs = []

    for execution in executions:
        metrics.execution_count += 1

        if execution.status == ExecutionStatus.COMPLETED:
            metrics.completed_count += 1
        elif execution.status == ExecutionStatus.FAILED:
            metrics.failed_count += 1
        elif execution.status == ExecutionStatus.RUNNING:
            metrics.running_count += 1

        # Duration
        if execution.duration:
            durations.append(execution.duration.seconds)

        # Cost
        if execution.total_cost and execution.total_cost.amount > 0:
            costs.append(execution.total_cost.amount)
            metrics.total_cost += execution.total_cost.amount

    # Calculate rates and averages
    finished = metrics.completed_count + metrics.failed_count
    if finished > 0:
        metrics.success_rate = (metrics.completed_count / finished) * 100

    if durations:
        metrics.average_duration_seconds = sum(durations) / len(durations)
        metrics.min_duration_seconds = min(durations)
        metrics.max_duration_seconds = max(durations)

    if costs:
        metrics.average_cost = metrics.total_cost / len(costs)
        metrics.min_cost = min(costs)
        metrics.max_cost = max(costs)

    return metrics
```

---

## Cost Tracking

### How Costs Are Captured

Costs flow from agent task responses through step handlers to execution totals:

**File**: `src/backend/services/process_engine/engine/execution_engine.py`

```python
# execution_engine.py:545-577 - _handle_step_success()
async def _handle_step_success(self, execution, step_def, result):
    step_id = step_def.id
    output = result.output or {}

    # Complete the step
    execution.complete_step(step_id, output)

    # Extract and store cost from output if available
    step_exec = execution.step_executions[str(step_id)]
    if output.get("cost"):
        try:
            cost = Money.from_string(output["cost"])
            step_exec.cost = cost
            # Add to execution total
            execution.add_cost(cost)
        except (ValueError, KeyError):
            pass  # Ignore invalid cost format

    # Extract and store token usage from output if available
    if output.get("token_usage"):
        try:
            token_usage = TokenUsage.from_dict(output["token_usage"])
            step_exec.token_usage = token_usage
        except (ValueError, KeyError, TypeError):
            pass
```

### Cost Aggregation

- **Step Level**: Each `StepExecution` stores individual `cost` (Money)
- **Execution Level**: `ProcessExecution.total_cost` accumulates via `add_cost()`
- **Process Level**: Analytics service aggregates across executions

---

## Cost Threshold Alerts

### CostAlertService

**File**: `src/backend/services/process_engine/services/alerts.py`

#### Enums and Data Classes

| Type | Lines | Values |
|------|-------|--------|
| `ThresholdType` | 24-28 | PER_EXECUTION, DAILY, WEEKLY |
| `AlertSeverity` | 31-34 | WARNING, CRITICAL |
| `AlertStatus` | 37-40 | ACTIVE, DISMISSED |
| `CostThreshold` | 43-78 | id, process_id, threshold_type, threshold_amount, currency, enabled, created_at, updated_at |
| `CostAlert` | 81-134 | id, process_id, process_name, execution_id, threshold_type, threshold_amount, actual_amount, currency, severity, status, message, created_at, dismissed_at, dismissed_by |

#### Service Class

**Class**: `CostAlertService` (lines 137-582)

| Method | Lines | Description |
|--------|-------|-------------|
| `__init__()` | 147-154 | Initialize with separate DB (trinity_alerts.db) |
| `_ensure_tables()` | 156-200 | Create cost_thresholds and cost_alerts tables |
| `get_thresholds()` | 206-231 | List all thresholds for a process |
| `set_threshold()` | 233-278 | Create or update a threshold (UPSERT) |
| `delete_threshold()` | 280-294 | Remove threshold by process and type |
| `check_execution_cost()` | 300-337 | Check per-execution threshold, return alert if exceeded |
| `check_daily_costs()` | 339-377 | Check daily threshold (dedupes alerts by day) |
| `check_weekly_costs()` | 379-417 | Check weekly threshold (dedupes alerts by week) |
| `get_alerts()` | 509-538 | List alerts with optional filters |
| `get_active_alerts_count()` | 540-552 | Count active alerts (for NavBar badge) |
| `dismiss_alert()` | 554-570 | Mark alert as dismissed with timestamp and user |

#### Severity Determination

```python
# alerts.py:321-324 - check_execution_cost()
# Determine severity based on overage ratio
overage = cost / threshold.threshold_amount
severity = AlertSeverity.CRITICAL if overage > 2 else AlertSeverity.WARNING
```

| Condition | Severity |
|-----------|----------|
| Cost <= 2x threshold | WARNING |
| Cost > 2x threshold | CRITICAL |

### Integration with ExecutionEngine

**File**: `src/backend/services/process_engine/engine/execution_engine.py`

```python
# execution_engine.py:751-788 - Cost threshold check on completion
async def _check_cost_thresholds(self, execution: ProcessExecution) -> None:
    """Check if execution cost exceeds configured thresholds."""
    if not self.cost_alert_service:
        return

    if not execution.total_cost or execution.total_cost.amount <= 0:
        return

    try:
        # Check per-execution threshold
        alert = self.cost_alert_service.check_execution_cost(
            process_id=str(execution.process_id),
            process_name=execution.process_name,
            execution_id=str(execution.id),
            cost=execution.total_cost.amount,
        )

        if alert:
            logger.warning(
                f"Cost alert triggered for execution {execution.id}: "
                f"${execution.total_cost.amount:.2f} exceeded threshold "
                f"(alert_id={alert.id}, severity={alert.severity.value})"
            )
    except Exception as e:
        # Don't fail execution if cost alert check fails
        logger.error(f"Failed to check cost thresholds: {e}")
```

### Alert API Endpoints

**File**: `src/backend/routers/alerts.py`

| Endpoint | Lines | Handler | Description |
|----------|-------|---------|-------------|
| `GET /api/alerts` | 104-139 | `list_alerts()` | List with status/process filters |
| `GET /api/alerts/count` | 143-154 | `get_alerts_count()` | Active count for NavBar badge |
| `GET /api/alerts/thresholds/{process_id}` | 157-174 | `get_process_thresholds()` | List thresholds for process |
| `PUT /api/alerts/thresholds/{process_id}` | 177-208 | `set_process_threshold()` | Create/update threshold |
| `DELETE /api/alerts/thresholds/{process_id}/{type}` | 211-236 | `delete_process_threshold()` | Remove threshold |
| `GET /api/alerts/{id}` | 240-254 | `get_alert()` | Single alert details |
| `POST /api/alerts/{id}/dismiss` | 257-280 | `dismiss_alert()` | Dismiss an alert |

---

## Database Schema

### cost_thresholds Table

**File**: `src/backend/services/process_engine/services/alerts.py:162-174`

```sql
CREATE TABLE IF NOT EXISTS cost_thresholds (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    threshold_type TEXT NOT NULL,     -- per_execution, daily, weekly
    threshold_amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(process_id, threshold_type)
);
```

### cost_alerts Table

**File**: `src/backend/services/process_engine/services/alerts.py:177-194`

```sql
CREATE TABLE IF NOT EXISTS cost_alerts (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    execution_id TEXT,                 -- NULL for daily/weekly alerts
    threshold_type TEXT NOT NULL,
    threshold_amount REAL NOT NULL,
    actual_amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    severity TEXT DEFAULT 'warning',   -- warning, critical
    status TEXT DEFAULT 'active',      -- active, dismissed
    message TEXT,
    created_at TEXT NOT NULL,
    dismissed_at TEXT,
    dismissed_by TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_alerts_process ON cost_alerts(process_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON cost_alerts(status);
```

**Database File**: `~/trinity-data/trinity_alerts.db` (separate from main DB)

---

## API Response Examples

### Process Metrics Response

```json
{
  "process_id": "550e8400-e29b-41d4-a716-446655440000",
  "process_name": "content-pipeline",
  "execution_count": 150,
  "completed_count": 140,
  "failed_count": 10,
  "running_count": 0,
  "success_rate": 93.3,
  "average_duration_seconds": 120.5,
  "average_cost": "$0.35",
  "total_cost": "$52.50",
  "min_duration_seconds": 45.2,
  "max_duration_seconds": 340.8,
  "min_cost": "$0.10",
  "max_cost": "$1.25"
}
```

### Trend Data Response

```json
{
  "days": 30,
  "daily_trends": [
    {
      "date": "2026-01-15",
      "execution_count": 5,
      "completed_count": 4,
      "failed_count": 1,
      "total_cost": 1.75,
      "success_rate": 80.0
    }
  ],
  "total_executions": 150,
  "total_completed": 140,
  "total_failed": 10,
  "overall_success_rate": 93.3,
  "total_cost": "$52.50"
}
```

### Step Performance Response

```json
{
  "slowest_steps": [
    {
      "step_id": "research-step",
      "step_name": "research-step",
      "process_name": "content-pipeline",
      "execution_count": 45,
      "average_duration_seconds": 180.5,
      "total_cost": "$15.75",
      "average_cost": "$0.35",
      "failure_rate": 5.0
    }
  ],
  "most_expensive_steps": [
    {
      "step_id": "analysis-step",
      "step_name": "analysis-step",
      "process_name": "data-pipeline",
      "execution_count": 30,
      "average_duration_seconds": 95.2,
      "total_cost": "$22.50",
      "average_cost": "$0.75",
      "failure_rate": 2.0
    }
  ]
}
```

### Cost Alert Response

```json
{
  "id": "alert-550e8400",
  "process_id": "process-550e8400",
  "process_name": "content-pipeline",
  "execution_id": "exec-550e8400",
  "threshold_type": "per_execution",
  "threshold_amount": 0.50,
  "actual_amount": 1.25,
  "currency": "USD",
  "severity": "critical",
  "status": "active",
  "message": "Execution cost $1.25 exceeded threshold $0.50",
  "created_at": "2026-01-23T10:30:00Z",
  "dismissed_at": null,
  "dismissed_by": null
}
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Invalid process ID | 400 | "Invalid process ID format" |
| Process not found | 404 | "Process definition not found" |
| Invalid threshold type | 400 | "Invalid threshold type: {type}. Valid: per_execution, daily, weekly" |
| Invalid status filter | 400 | "Invalid status: {status}" |
| Alert not found | 404 | "Alert not found" |
| Alert already dismissed | 400 | "Alert already dismissed" |
| Threshold not found | 404 | "Threshold not found" |

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- At least one published process with completed executions
- Some executions should have costs attached

### Test Cases

1. **View process dashboard**
   - Navigate to `/process-dashboard`
   - Verify summary cards show correct totals
   - Verify trend charts render with data

2. **Change time period**
   - Select different periods (7/30/90 days)
   - Verify data updates and charts re-render

3. **View step performance**
   - Check "Slowest Steps" section shows data
   - Check "Most Expensive Steps" section shows data

4. **Configure cost threshold**
   - Set a per_execution threshold below typical cost
   - Run a process execution
   - Verify alert is generated

5. **View and dismiss alerts**
   - Navigate to Alerts page
   - Verify alerts appear with severity badges
   - Click dismiss on an alert
   - Verify status changes to "dismissed"

### API Test Commands

```bash
# Get process analytics
curl -X GET "http://localhost:8000/api/processes/{process_id}/analytics?days=30" \
  -H "Authorization: Bearer $TOKEN"

# Get trends
curl -X GET "http://localhost:8000/api/processes/analytics/trends?days=30" \
  -H "Authorization: Bearer $TOKEN"

# Get step performance
curl -X GET "http://localhost:8000/api/executions/analytics/steps?days=30&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Set threshold
curl -X PUT "http://localhost:8000/api/alerts/thresholds/{process_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"threshold_type": "per_execution", "amount": 0.50, "enabled": true}'

# List alerts
curl -X GET "http://localhost:8000/api/alerts?status=active" \
  -H "Authorization: Bearer $TOKEN"

# Dismiss alert
curl -X POST "http://localhost:8000/api/alerts/{alert_id}/dismiss" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Related Flows

- **Upstream**: [process-execution.md](./process-execution.md) - Cost capture during step execution
- **Related**: [process-monitoring.md](./process-monitoring.md) - Real-time execution monitoring
- **Frontend**: [alerts-page.md](../alerts-page.md) - Alerts page UI flow

---

## Revision History

| Date | Change |
|------|--------|
| 2026-01-23 | **Rebuilt** with accurate line numbers, added step performance, detailed data class documentation |
| 2026-01-16 | Initial creation |
