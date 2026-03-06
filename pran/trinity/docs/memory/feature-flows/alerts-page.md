# Feature: Alerts Page

> Cost threshold alerts for process execution monitoring

---

## Overview

The Alerts Page (`/alerts`) displays cost threshold alerts triggered by the Process Engine. When process executions exceed configured cost thresholds (per-execution, daily, or weekly), alerts are created and displayed here for user review and dismissal.

## User Story

As a platform administrator, I want to monitor process execution costs and receive alerts when costs exceed configured thresholds so that I can identify runaway processes and control spending.

---

## Entry Points

| Entry Point | Location | Description |
|-------------|----------|-------------|
| **NavBar Bell Icon** | `src/frontend/src/components/NavBar.vue:57-72` | Bell icon with red badge showing active alert count |
| **Direct URL** | `/alerts` route | Direct navigation to alerts page |

### NavBar Notification Badge

```vue
<!-- NavBar.vue:57-72 -->
<router-link
  to="/alerts"
  class="relative p-2 rounded-lg..."
  title="Cost Alerts"
>
  <svg class="w-5 h-5"><!-- bell icon --></svg>
  <span
    v-if="alertsStore.activeCount > 0"
    class="absolute -top-1 -right-1 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white transform bg-red-500 rounded-full"
  >
    {{ alertsStore.activeCount > 99 ? '99+' : alertsStore.activeCount }}
  </span>
</router-link>
```

---

## Architecture

```
Frontend                              Backend                              Database
--------                              -------                              --------
NavBar.vue                            routers/alerts.py                    trinity_alerts.db
  └── alertsStore.startPolling()        └── GET /api/alerts                  ├── cost_thresholds
                                            └── CostAlertService              └── cost_alerts
Alerts.vue                                      └── get_alerts()
  ├── fetchAlerts()
  │   └── GET /api/alerts             GET /api/alerts/count
  └── dismissAlert()                    └── get_active_alerts_count()
      └── POST /api/alerts/{id}/dismiss
                                      POST /api/alerts/{id}/dismiss
stores/alerts.js                        └── dismiss_alert()
  ├── alerts[]
  ├── activeCount
  ├── fetchAlerts()
  ├── fetchActiveCount()
  ├── dismissAlert()
  └── startPolling() / stopPolling()
```

---

## Frontend Layer

### Route Definition

```javascript
// router/index.js:114-118
{
  path: '/alerts',
  name: 'Alerts',
  component: () => import('../views/Alerts.vue'),
  meta: { requiresAuth: true }
}
```

### Alerts.vue Component

**File**: `src/frontend/src/views/Alerts.vue` (200 lines)

| Section | Lines | Description |
|---------|-------|-------------|
| Header | 8-37 | Title, status filter dropdown, refresh button |
| Stats Cards | 39-49 | Active count, total shown |
| Alert List | 51-121 | Alert cards with severity icon, details, dismiss button |
| Empty State | 115-119 | BellSlashIcon when no alerts |

**Key Methods:**

```javascript
// Alerts.vue:149-166
async function fetchAlerts() {
  loading.value = true
  try {
    await alertsStore.fetchAlerts({
      status: statusFilter.value || undefined,
    })
  } finally {
    loading.value = false
  }
}

async function dismissAlert(alertId) {
  try {
    await alertsStore.dismissAlert(alertId)
  } catch (err) {
    console.error('Failed to dismiss alert:', err)
  }
}
```

**Visual Elements:**

| Element | Lines | Description |
|---------|-------|-------------|
| Severity Icon | 67-76 | Red (critical) or yellow (warning) triangle icon |
| Threshold Type Badge | 80-86 | Blue (per_execution), purple (daily), indigo (weekly) |
| Status Badge | 97-103 | Red (active) or gray (dismissed) |
| Dismiss Button | 104-110 | Only shown for active alerts |

### Alerts Store

**File**: `src/frontend/src/stores/alerts.js` (182 lines)

| State | Type | Description |
|-------|------|-------------|
| `alerts` | Array | List of alert objects |
| `activeCount` | Number | Count of active (non-dismissed) alerts |
| `loading` | Boolean | Loading state |
| `error` | String | Error message |

| Action | Lines | Description |
|--------|-------|-------------|
| `fetchAlerts(options)` | 31-60 | Fetch alerts with status/process filters |
| `fetchActiveCount()` | 62-72 | Fetch only the active count (for badge) |
| `dismissAlert(alertId)` | 74-94 | Dismiss alert and update local state |
| `startPolling(intervalMs)` | 147-153 | Start polling for badge updates (default 60s) |
| `stopPolling()` | 155-160 | Stop the polling interval |

**Polling Setup (NavBar):**

```javascript
// NavBar.vue:246-266
onMounted(async () => {
  alertsStore.startPolling(60000)  // Poll every 60 seconds
})

onUnmounted(() => {
  alertsStore.stopPolling()
})
```

### API Calls

```javascript
// Fetch alerts list
GET /api/alerts?status={active|dismissed}&limit=50&offset=0

// Fetch active count (for badge)
GET /api/alerts/count

// Dismiss alert
POST /api/alerts/{alertId}/dismiss
```

---

## Backend Layer

### Router: alerts.py

**File**: `src/backend/routers/alerts.py` (281 lines)

| Endpoint | Method | Lines | Description |
|----------|--------|-------|-------------|
| `/api/alerts` | GET | 104-139 | List alerts with filters |
| `/api/alerts/count` | GET | 143-154 | Get active alert count |
| `/api/alerts/{alert_id}` | GET | 240-254 | Get single alert |
| `/api/alerts/{alert_id}/dismiss` | POST | 257-280 | Dismiss an alert |
| `/api/alerts/thresholds/{process_id}` | GET | 157-174 | Get process thresholds |
| `/api/alerts/thresholds/{process_id}` | PUT | 177-208 | Set/update threshold |
| `/api/alerts/thresholds/{process_id}/{type}` | DELETE | 211-236 | Delete threshold |

**Endpoint: List Alerts**

```python
# alerts.py:104-139
@router.get("", response_model=AlertListResponse)
async def list_alerts(
    current_user: CurrentUser,
    status: Optional[str] = Query(None),  # active, dismissed
    process_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    service = get_alert_service()

    status_filter = None
    if status:
        status_filter = AlertStatus(status)  # Validates enum

    alerts = service.get_alerts(
        status=status_filter,
        process_id=process_id,
        limit=limit,
        offset=offset,
    )
    active_count = service.get_active_alerts_count()

    return AlertListResponse(
        alerts=[AlertResponse(**a.to_dict()) for a in alerts],
        total=len(alerts),
        active_count=active_count,
    )
```

**Endpoint: Dismiss Alert**

```python
# alerts.py:257-280
@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    current_user: CurrentUser,
):
    service = get_alert_service()

    alert = service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == AlertStatus.DISMISSED:
        raise HTTPException(status_code=400, detail="Alert already dismissed")

    success = service.dismiss_alert(alert_id, dismissed_by=current_user.email)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to dismiss alert")

    logger.info(f"Alert {alert_id} dismissed by {current_user.email}")
    return {"message": "Alert dismissed", "alert_id": alert_id}
```

### Service: CostAlertService

**File**: `src/backend/services/process_engine/services/alerts.py` (582 lines)

**Enums:**

```python
# alerts.py:24-40
class ThresholdType(str, Enum):
    PER_EXECUTION = "per_execution"
    DAILY = "daily"
    WEEKLY = "weekly"

class AlertSeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    DISMISSED = "dismissed"
```

**Alert Generation Logic:**

```python
# alerts.py:300-337 (check_execution_cost)
def check_execution_cost(
    self,
    process_id: str,
    process_name: str,
    execution_id: str,
    cost: Decimal,
) -> Optional[CostAlert]:
    """Check if an execution cost exceeds the per-execution threshold."""
    thresholds = self.get_thresholds(process_id)

    for threshold in thresholds:
        if not threshold.enabled:
            continue
        if threshold.threshold_type != ThresholdType.PER_EXECUTION:
            continue

        if cost > threshold.threshold_amount:
            # Severity: CRITICAL if >2x threshold, else WARNING
            overage = cost / threshold.threshold_amount
            severity = AlertSeverity.CRITICAL if overage > 2 else AlertSeverity.WARNING

            alert = self._create_alert(
                process_id=process_id,
                process_name=process_name,
                execution_id=execution_id,
                threshold=threshold,
                actual_amount=cost,
                severity=severity,
                message=f"Execution cost ${cost:.2f} exceeded threshold ${threshold.threshold_amount:.2f}",
            )
            return alert

    return None
```

**Alert Dismissal:**

```python
# alerts.py:554-570
def dismiss_alert(self, alert_id: str, dismissed_by: str) -> bool:
    """Dismiss an alert."""
    conn = sqlite3.connect(self._db_path)
    cursor = conn.cursor()

    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        UPDATE cost_alerts
        SET status = ?, dismissed_at = ?, dismissed_by = ?
        WHERE id = ?
    """, (AlertStatus.DISMISSED.value, now, dismissed_by, alert_id))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success
```

---

## Alert Types

### Threshold Types

| Type | Value | Check Trigger | Description |
|------|-------|---------------|-------------|
| Per-Execution | `per_execution` | On execution complete | Single execution cost exceeded |
| Daily | `daily` | Periodic/on execution | Aggregated daily cost exceeded |
| Weekly | `weekly` | Periodic/on execution | Aggregated weekly cost exceeded |

### Alert Severity Levels

| Severity | Condition | UI Indicator |
|----------|-----------|--------------|
| `warning` | Cost > threshold but < 2x | Yellow triangle icon, yellow background |
| `critical` | Cost > 2x threshold | Red triangle icon, red background |

### Alert Status

| Status | Description | UI Behavior |
|--------|-------------|-------------|
| `active` | Alert not yet addressed | Red badge, Dismiss button shown |
| `dismissed` | Alert acknowledged by user | Gray badge, no dismiss button |

---

## Database Schema

### Database Location

The alerts service uses a separate SQLite database:
- Path: `~/trinity-data/trinity_alerts.db`
- Derived from: `TRINITY_DB_PATH` environment variable with `_alerts` suffix

### cost_thresholds Table

```sql
-- alerts.py:162-174
CREATE TABLE cost_thresholds (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    threshold_type TEXT NOT NULL,      -- per_execution, daily, weekly
    threshold_amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(process_id, threshold_type)
);
```

### cost_alerts Table

```sql
-- alerts.py:177-194
CREATE TABLE cost_alerts (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    execution_id TEXT,                  -- NULL for daily/weekly alerts
    threshold_type TEXT NOT NULL,
    threshold_amount REAL NOT NULL,
    actual_amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    severity TEXT DEFAULT 'warning',    -- warning, critical
    status TEXT DEFAULT 'active',       -- active, dismissed
    message TEXT,
    created_at TEXT NOT NULL,
    dismissed_at TEXT,
    dismissed_by TEXT
);

CREATE INDEX idx_alerts_process ON cost_alerts(process_id);
CREATE INDEX idx_alerts_status ON cost_alerts(status);
```

---

## Alert Generation Flow

### Trigger: Process Execution Completion

```
ExecutionEngine._complete_execution()
    │
    ├── execution.complete(output_data)
    ├── execution_repo.save(execution)
    ├── _publish_event(ProcessCompleted)
    │
    └── _check_cost_thresholds(execution)          # alerts.py integration
            │
            └── CostAlertService.check_execution_cost()
                    │
                    ├── Get enabled thresholds for process
                    ├── Compare cost vs threshold
                    ├── Determine severity (warning/critical)
                    └── _create_alert() -> INSERT into cost_alerts
```

**ExecutionEngine Integration:**

```python
# execution_engine.py:751-787
async def _check_cost_thresholds(
    self,
    execution: ProcessExecution,
) -> None:
    """Check if execution cost exceeds configured thresholds."""
    if not self.cost_alert_service:
        return

    if not execution.total_cost or execution.total_cost.amount <= 0:
        return

    try:
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

---

## Threshold Configuration

Thresholds are configured per-process via the alerts API. There is currently no dedicated UI for threshold configuration - it is managed through API calls.

### API: Set Threshold

```bash
PUT /api/alerts/thresholds/{process_id}
Content-Type: application/json

{
  "threshold_type": "per_execution",  # or "daily", "weekly"
  "amount": 0.50,
  "enabled": true
}
```

### API: Get Process Thresholds

```bash
GET /api/alerts/thresholds/{process_id}

Response:
{
  "process_id": "uuid",
  "thresholds": [
    {
      "id": "uuid",
      "process_id": "uuid",
      "threshold_type": "per_execution",
      "threshold_amount": 0.50,
      "currency": "USD",
      "enabled": true,
      "created_at": "2026-01-16T10:00:00Z",
      "updated_at": "2026-01-16T10:00:00Z"
    }
  ]
}
```

---

## WebSocket / Real-Time Updates

Currently, alerts use **polling** rather than WebSocket broadcasting:

- **NavBar**: `alertsStore.startPolling(60000)` - polls every 60 seconds
- **Alerts Page**: Manual refresh via button

There is no WebSocket broadcast for new alerts - the UI must poll or refresh manually.

---

## Error Handling

| Error Case | HTTP Status | Message | Handling |
|------------|-------------|---------|----------|
| Alert not found | 404 | "Alert not found" | Show error message |
| Alert already dismissed | 400 | "Alert already dismissed" | Ignore (already handled) |
| Invalid status filter | 400 | "Invalid status: {value}" | Show validation error |
| Invalid threshold type | 400 | "Invalid threshold type" | Show validation error |
| Dismiss failed | 500 | "Failed to dismiss alert" | Show error, retry |

---

## Security Considerations

1. **Authentication Required**: All endpoints require `CurrentUser` dependency
2. **User Tracking**: `dismissed_by` field records who dismissed each alert
3. **No Authorization Filtering**: All authenticated users can see all alerts (no per-user filtering)

---

## Related Flows

| Flow | Relationship |
|------|--------------|
| [process-analytics.md](process-engine/process-analytics.md) | Cost tracking, alert service integration |
| [process-execution.md](process-engine/process-execution.md) | Alert trigger point in execution engine |
| [process-monitoring.md](process-engine/process-monitoring.md) | Dashboard integration |

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- At least one process with configured cost threshold
- Process execution that exceeds threshold

### Test Cases

1. **View alerts page**
   - Action: Navigate to `/alerts`
   - Expected: Page loads, shows alerts list (or empty state)
   - Verify: Header, filter dropdown, stats cards visible

2. **Filter by status**
   - Action: Select "Active" from dropdown
   - Expected: Only active alerts shown
   - Verify: API call includes `?status=active`

3. **Dismiss alert**
   - Action: Click "Dismiss" on active alert
   - Expected: Alert status changes to dismissed, badge count decreases
   - Verify: `dismissed_at` and `dismissed_by` populated in database

4. **NavBar badge updates**
   - Action: Wait 60 seconds (polling interval)
   - Expected: Badge count refreshes
   - Verify: `GET /api/alerts/count` called

5. **Cost alert generation**
   - Setup: Configure threshold for process (e.g., $0.10 per_execution)
   - Action: Run process with cost exceeding threshold
   - Expected: New alert appears in list
   - Verify: Alert has correct process name, amounts, severity

6. **Critical severity**
   - Setup: Threshold of $0.10
   - Action: Run process with cost >$0.20 (>2x threshold)
   - Expected: Alert severity is "critical" with red icon
   - Verify: `severity: "critical"` in response

### Status: Working

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-21 | Initial creation |
