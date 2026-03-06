# Agent Notifications (NOTIF-001)

> **Status**: ✅ Implemented (Phase 1 Complete)
> **Priority**: HIGH
> **Created**: 2026-02-20
> **Completed**: 2026-02-20

## Overview

Enable agents to send structured notifications to the Trinity platform. Agents decide when and what to notify based on their own logic. Notifications are persisted, broadcast in real-time via WebSocket, and queryable via API.

## User Stories

1. As an **agent developer**, I want to instruct agents to send notifications under certain conditions so that important events are surfaced to users.

2. As a **platform user**, I want to see a stream of notifications from my agents so that I know when something needs attention.

3. As a **system operator**, I want to query notifications by agent, priority, or type so that I can monitor platform health.

## Scope

### In Scope
- MCP tool: `send_notification`
- Database table: `agent_notifications`
- WebSocket broadcast on new notification
- REST API endpoints for query and acknowledgment
- Basic agent instructions template

### Out of Scope (Future)
- UI for viewing notifications (will add later)
- Email/Slack/webhook forwarding
- Notification routing rules
- Auto-dismiss or retention policies

---

## Data Model

### Table: `agent_notifications`

```sql
CREATE TABLE agent_notifications (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    priority TEXT DEFAULT 'normal',
    category TEXT,
    metadata TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    acknowledged_at TEXT,
    acknowledged_by TEXT
);

CREATE INDEX idx_notifications_agent ON agent_notifications(agent_name, created_at DESC);
CREATE INDEX idx_notifications_status ON agent_notifications(status);
CREATE INDEX idx_notifications_priority ON agent_notifications(priority);
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `id` | TEXT | UUID, e.g., `notif_abc123` |
| `agent_name` | TEXT | Source agent name |
| `notification_type` | TEXT | `alert`, `info`, `status`, `completion`, `question` |
| `title` | TEXT | Short summary (required, max 200 chars) |
| `message` | TEXT | Detailed message (optional) |
| `priority` | TEXT | `low`, `normal`, `high`, `urgent` |
| `category` | TEXT | Free-form grouping: `progress`, `anomaly`, `health`, `error`, etc. |
| `metadata` | TEXT | JSON object with structured data |
| `status` | TEXT | `pending`, `acknowledged`, `dismissed` |
| `created_at` | TEXT | ISO8601 timestamp |
| `acknowledged_at` | TEXT | When status changed from pending |
| `acknowledged_by` | TEXT | User ID who acknowledged |

---

## MCP Tool

### `send_notification`

**Location**: `src/mcp-server/tools/notifications.ts`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `notification_type` | string | Yes | One of: `alert`, `info`, `status`, `completion`, `question` |
| `title` | string | Yes | Short summary (max 200 chars) |
| `message` | string | No | Detailed explanation |
| `priority` | string | No | `low`, `normal` (default), `high`, `urgent` |
| `category` | string | No | Free-form category for grouping |
| `metadata` | object | No | Any structured data |

**Example Call**:
```json
{
  "tool": "send_notification",
  "arguments": {
    "notification_type": "completion",
    "title": "Daily report generated",
    "message": "Processed 15,000 records. Report saved to content/reports/2026-02-20.pdf",
    "priority": "normal",
    "category": "progress",
    "metadata": {
      "records_processed": 15000,
      "output_path": "content/reports/2026-02-20.pdf"
    }
  }
}
```

**Response**:
```json
{
  "success": true,
  "notification_id": "notif_abc123"
}
```

**Backend Endpoint**: `POST /api/notifications`

---

## REST API

### Create Notification (MCP → Backend)

```
POST /api/notifications
Authorization: Bearer <MCP_API_KEY>
Content-Type: application/json

{
  "notification_type": "alert",
  "title": "High error rate detected",
  "message": "Error rate exceeded 5% threshold",
  "priority": "high",
  "category": "anomaly"
}
```

**Response**: `201 Created`
```json
{
  "id": "notif_abc123",
  "agent_name": "monitoring-agent",
  "created_at": "2026-02-20T10:30:00Z"
}
```

**Note**: `agent_name` extracted from MCP auth context (agent-scoped key).

### List Notifications

```
GET /api/notifications
GET /api/notifications?agent_name=my-agent
GET /api/notifications?status=pending
GET /api/notifications?priority=high,urgent
GET /api/notifications?limit=50
```

**Response**: `200 OK`
```json
{
  "count": 15,
  "notifications": [
    {
      "id": "notif_abc123",
      "agent_name": "my-agent",
      "notification_type": "alert",
      "title": "High error rate",
      "priority": "high",
      "status": "pending",
      "created_at": "2026-02-20T10:30:00Z"
    }
  ]
}
```

### Get Single Notification

```
GET /api/notifications/{id}
```

### Acknowledge Notification

```
POST /api/notifications/{id}/acknowledge
```

**Response**: `200 OK`
```json
{
  "id": "notif_abc123",
  "status": "acknowledged",
  "acknowledged_at": "2026-02-20T11:00:00Z",
  "acknowledged_by": "user@example.com"
}
```

### Dismiss Notification

```
POST /api/notifications/{id}/dismiss
```

### Get Agent Notifications

```
GET /api/agents/{name}/notifications
GET /api/agents/{name}/notifications?status=pending
```

---

## WebSocket Event

When a notification is created, broadcast to connected clients:

**Event Type**: `agent_notification`

```json
{
  "type": "agent_notification",
  "notification_id": "notif_abc123",
  "agent_name": "research-agent",
  "notification_type": "completion",
  "title": "Analysis complete",
  "priority": "normal",
  "category": "progress",
  "timestamp": "2026-02-20T10:30:00Z"
}
```

**Broadcast Pattern**:
- Main WebSocket (`/ws`): All connected UI clients
- Filtered WebSocket (`/ws/events`): Trinity Connect clients (filtered by accessible agents)

---

## Agent Instructions Template

Add to agent CLAUDE.md or as a skill:

```markdown
## Notifications

You can send notifications to Trinity when important events occur.

### When to Notify
- Task completion (especially scheduled tasks)
- Errors or anomalies that need attention
- Progress updates on long-running work
- Questions that require human input
- Health issues or resource warnings

### How to Notify
Use the `send_notification` MCP tool:

- **notification_type**: alert, info, status, completion, question
- **title**: Short summary (required)
- **message**: Details (optional)
- **priority**: low, normal, high, urgent
- **category**: progress, anomaly, health, error, etc.

### Examples

Task completed:
```
send_notification(
  notification_type="completion",
  title="Weekly report generated",
  priority="normal"
)
```

Error detected:
```
send_notification(
  notification_type="alert",
  title="API rate limit exceeded",
  message="GitHub API returned 429. Pausing for 1 hour.",
  priority="high",
  category="error"
)
```

Question for user:
```
send_notification(
  notification_type="question",
  title="Clarification needed",
  message="Found 3 duplicate entries. Should I merge or skip?",
  priority="normal"
)
```
```

---

## Implementation Plan

### Phase 1: Backend + MCP Tool
1. Add `agent_notifications` table to `database.py`
2. Create `db/notifications.py` with CRUD operations
3. Create `routers/notifications.py` with API endpoints
4. Add `send_notification` tool to MCP server
5. Add WebSocket broadcast on creation

### Phase 2: Integration
6. Update MCP tool count in docs
7. Add notification instructions to agent template guide
8. Test with a real agent

### Phase 3: UI (Future)
9. Notifications panel in Dashboard
10. Badge/indicator for unread notifications
11. Filter and search UI

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/backend/database.py` | Modify | Add table migration |
| `src/backend/db/notifications.py` | Create | CRUD operations |
| `src/backend/db_models.py` | Modify | Add Pydantic models |
| `src/backend/routers/notifications.py` | Create | API endpoints |
| `src/backend/main.py` | Modify | Mount router, add broadcast |
| `src/mcp-server/tools/notifications.ts` | Create | MCP tool |
| `src/mcp-server/client.ts` | Modify | Add API client method |
| `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` | Modify | Add notifications section |

---

## Success Criteria

1. Agent can call `send_notification` via MCP
2. Notification persisted to database
3. WebSocket event broadcast to connected clients
4. API returns notifications with filters
5. Acknowledge/dismiss changes status

---

## Related Documents

- `docs/memory/feature-flows/activity-stream.md` - Similar broadcast pattern
- `docs/memory/feature-flows/trinity-connect.md` - Filtered WebSocket
- `docs/memory/feature-flows/mcp-orchestration.md` - MCP tool patterns
