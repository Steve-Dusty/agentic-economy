# Activity Tracking Architecture - Proposal

> **Purpose**: Unified approach to tracking all agent activities for scalability
> **Date**: 2025-12-02
> **Status**: Proposal - Pending Decision

---

## Problem Statement

We currently track agent activities in multiple disconnected places:
- `chat_messages` table (persistent chat history)
- `schedule_executions` table (scheduled run logs)
- Agent activity endpoint (in-memory tool timeline)
- Audit logs (security events)
- WebSocket broadcasts (ephemeral real-time events)

**Issues**:
- No single source of truth for "what agents are doing"
- Hard to add new activity consumers (dashboards, alerts, analytics)
- Inconsistent data models across different tracking mechanisms
- Difficult to query cross-cutting concerns (e.g., "show me all activity for agent X today")

**Requirements**:
1. Track all agent activities uniformly
2. Support multiple consumers (WebSocket, UI, analytics, alerts)
3. Include tool calls and sub-agent invocations
4. Scalable to new activity types (file access, API calls, etc.)
5. Maintain backward compatibility with existing features

---

## Approach 1: Lightweight Event Broadcasting (Simplest)

### Architecture
```
Agent Activity Occurs
    ↓
Router/Service detects activity
    ↓
Call broadcast_activity(event_data)
    ↓
    ├→ WebSocket.broadcast(event)          [Real-time]
    ├→ Store in chat_messages/executions   [Persistence]
    └→ Audit log (if security relevant)    [Compliance]
```

### Implementation
```python
# src/backend/services/activity_service.py

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

class ActivityType(Enum):
    """Types of agent activities"""
    CHAT_START = "chat_start"
    CHAT_END = "chat_end"
    TOOL_CALL = "tool_call"
    SCHEDULE_START = "schedule_start"
    SCHEDULE_END = "schedule_end"
    AGENT_COLLABORATION = "agent_collaboration"
    FILE_ACCESS = "file_access"
    MODEL_CHANGE = "model_change"

class ActivityEvent:
    """Structured activity event"""
    def __init__(
        self,
        activity_type: ActivityType,
        agent_name: str,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.type = activity_type
        self.agent_name = agent_name
        self.user_id = user_id
        self.details = details or {}
        self.timestamp = datetime.utcnow()

    def to_websocket_event(self) -> Dict[str, Any]:
        """Format for WebSocket broadcast"""
        # Determine state for dashboard
        state = "idle"
        action_label = None

        if self.type == ActivityType.CHAT_START:
            state = "active"
            action_label = "Processing chat"
        elif self.type == ActivityType.TOOL_CALL:
            state = "active"
            tool_name = self.details.get("tool_name", "Unknown")
            action_label = f"Using {tool_name}"
        elif self.type == ActivityType.SCHEDULE_START:
            state = "active"
            action_label = "Running scheduled task"
        elif self.type == ActivityType.AGENT_COLLABORATION:
            state = "active"
            target = self.details.get("target_agent", "agent")
            action_label = f"Collaborating with {target}"

        event = {
            "type": "agent_activity",
            "agent_name": self.agent_name,
            "activity_type": self.type.value,
            "activity_state": state,
            "action": action_label,
            "timestamp": self.timestamp.isoformat()
        }

        # Include relevant details
        if "tool_name" in self.details:
            event["tool_name"] = self.details["tool_name"]
        if "target_agent" in self.details:
            event["target_agent"] = self.details["target_agent"]
        if "context_used" in self.details:
            event["context"] = {
                "used": self.details["context_used"],
                "max": self.details.get("context_max", 200000),
                "percentage": round((self.details["context_used"] / self.details.get("context_max", 200000)) * 100, 2)
            }

        return event

class ActivityService:
    """Central service for tracking all agent activities"""

    def __init__(self):
        self._websocket_manager = None
        self._subscribers: List[callable] = []

    def set_websocket_manager(self, manager):
        """Inject WebSocket manager for broadcasting"""
        self._websocket_manager = manager

    def subscribe(self, callback: callable):
        """Register a callback to receive all activity events"""
        self._subscribers.append(callback)

    async def track_activity(self, event: ActivityEvent):
        """
        Central method to track any agent activity.

        This broadcasts to WebSocket and notifies all subscribers.
        Persistence is handled by the calling code (chat.py, schedules.py, etc.)
        """
        # Broadcast to WebSocket for real-time updates
        if self._websocket_manager:
            ws_event = event.to_websocket_event()
            await self._websocket_manager.broadcast(json.dumps(ws_event))

        # Notify subscribers (future: metrics, alerts, analytics)
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    subscriber(event)
            except Exception as e:
                print(f"[Warning] Activity subscriber failed: {e}")

# Global singleton
activity_service = ActivityService()
```

### Usage in Routers
```python
# src/backend/routers/chat.py

from services.activity_service import activity_service, ActivityEvent, ActivityType

@router.post("/{name}/chat")
async def chat_with_agent(...):
    # Track chat start
    await activity_service.track_activity(ActivityEvent(
        activity_type=ActivityType.CHAT_START,
        agent_name=name,
        user_id=current_user.id,
        details={"message_preview": request.message[:50]}
    ))

    try:
        # Execute chat...
        response_data = await client.post(...)

        # Track chat end with context
        await activity_service.track_activity(ActivityEvent(
            activity_type=ActivityType.CHAT_END,
            agent_name=name,
            user_id=current_user.id,
            details={
                "context_used": session_data.get("context_tokens"),
                "context_max": session_data.get("context_window"),
                "cost": metadata.get("cost_usd"),
                "tool_count": len(execution_log)
            }
        ))

        # Persist to database (existing code)
        db.add_chat_message(...)

        return response_data
    except Exception as e:
        await activity_service.track_activity(ActivityEvent(
            activity_type=ActivityType.CHAT_END,
            agent_name=name,
            user_id=current_user.id,
            details={"error": str(e)}
        ))
        raise
```

### Pros
✅ Simple to implement (~100 lines of code)
✅ Minimal changes to existing code
✅ No new database tables
✅ Easy to add subscribers for future features
✅ Backward compatible

### Cons
❌ No centralized activity history (relies on existing tables)
❌ Can't easily query "all activities" across types
❌ Subscribers must handle their own persistence

---

## Approach 2: Activity Stream with Database (Recommended)

### Architecture
```
Agent Activity Occurs
    ↓
Router/Service detects activity
    ↓
Call activity_service.track(event)
    ↓
    ├→ Insert into agent_activities table    [Single source of truth]
    ├→ WebSocket.broadcast(event)            [Real-time]
    └→ Notify subscribers                    [Extensions]

Query Activities:
    ├→ Dashboard: Recent activities for visualization
    ├→ Analytics: Activity patterns and metrics
    ├→ Alerts: Anomaly detection
    └→ Audit: Compliance and investigation
```

### Database Schema
```sql
CREATE TABLE agent_activities (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    activity_type TEXT NOT NULL,  -- 'chat_start', 'tool_call', 'schedule_start', etc.
    user_id INTEGER,
    triggered_by TEXT,  -- 'user', 'schedule', 'agent', 'system'

    -- State tracking
    activity_state TEXT,  -- 'started', 'completed', 'failed'
    parent_activity_id TEXT,  -- Link to parent (e.g., tool_call → chat_start)

    -- Timestamps
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER,

    -- Activity-specific details (JSON)
    details TEXT,  -- {tool_name, target_agent, context_used, etc.}

    -- Observability
    context_used INTEGER,
    context_max INTEGER,
    cost REAL,
    error TEXT,

    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (parent_activity_id) REFERENCES agent_activities(id)
);

CREATE INDEX idx_agent_activities_agent ON agent_activities(agent_name, created_at DESC);
CREATE INDEX idx_agent_activities_type ON agent_activities(activity_type);
CREATE INDEX idx_agent_activities_user ON agent_activities(user_id);
CREATE INDEX idx_agent_activities_parent ON agent_activities(parent_activity_id);
```

### Enhanced Service
```python
class ActivityService:
    """Central service with database persistence"""

    async def track_activity(self, event: ActivityEvent) -> str:
        """
        Track activity with database persistence.
        Returns activity_id for linking child activities.
        """
        activity_id = str(uuid.uuid4())

        # Persist to database (single source of truth)
        db.insert_activity(
            id=activity_id,
            agent_name=event.agent_name,
            activity_type=event.type.value,
            user_id=event.user_id,
            details=json.dumps(event.details),
            started_at=event.timestamp.isoformat(),
            **event.details  # Extract relevant fields
        )

        # Broadcast to WebSocket
        if self._websocket_manager:
            await self._websocket_manager.broadcast(
                json.dumps(event.to_websocket_event())
            )

        # Notify subscribers
        await self._notify_subscribers(event)

        return activity_id

    async def complete_activity(
        self,
        activity_id: str,
        status: str = "completed",
        details: Optional[Dict] = None
    ):
        """Mark activity as completed with results"""
        duration_ms = db.calculate_duration(activity_id)

        db.update_activity(
            id=activity_id,
            activity_state=status,
            completed_at=datetime.utcnow().isoformat(),
            duration_ms=duration_ms,
            details=json.dumps(details) if details else None
        )

        # Broadcast completion
        event_data = {
            "type": "agent_activity_complete",
            "activity_id": activity_id,
            "status": status,
            "duration_ms": duration_ms
        }
        if self._websocket_manager:
            await self._websocket_manager.broadcast(json.dumps(event_data))
```

### Usage Pattern
```python
# Track start
activity_id = await activity_service.track_activity(ActivityEvent(
    activity_type=ActivityType.CHAT_START,
    agent_name=name,
    user_id=current_user.id
))

try:
    # Do work...

    # Track completion
    await activity_service.complete_activity(
        activity_id,
        status="completed",
        details={"context_used": tokens, "cost": cost}
    )
except Exception as e:
    await activity_service.complete_activity(
        activity_id,
        status="failed",
        details={"error": str(e)}
    )
```

### Query API
```python
@router.get("/api/agents/{name}/activities")
async def get_agent_activities(
    name: str,
    activity_type: Optional[str] = None,
    limit: int = 100
):
    """Get recent activities for an agent"""
    activities = db.get_agent_activities(
        agent_name=name,
        activity_type=activity_type,
        limit=limit
    )
    return {"activities": activities}

@router.get("/api/activities/timeline")
async def get_activity_timeline(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Get cross-agent activity timeline"""
    activities = db.get_activities_in_range(start_time, end_time)
    return {"timeline": activities}
```

### Pros
✅ Single source of truth for all activities
✅ Easy to query historical data
✅ Supports activity relationships (parent/child)
✅ Enables analytics and reporting
✅ Clean separation of concerns
✅ Scalable to new activity types

### Cons
❌ New database table and migrations
❌ More storage usage
❌ Need to manage table size (archival strategy)

---

## Approach 3: Event Sourcing (Most Robust)

### Architecture
```
Agent Activity Occurs
    ↓
Emit ActivityEvent to event stream
    ↓
Event Store (append-only log)
    ↓
    ├→ Projection: agent_activity_summary (materialized view)
    ├→ Projection: real-time dashboard state
    ├→ Projection: analytics aggregates
    └→ Projection: audit log

Benefits:
- Complete audit trail
- Replayable for debugging
- Time-travel queries
- Event-driven architecture
```

### Implementation
- Event store: Redis Streams or dedicated table
- Projections: Materialized views for different use cases
- Event handlers: Process events asynchronously

### Pros
✅ Complete audit trail
✅ Event replay for debugging
✅ Highly scalable
✅ Supports complex event processing

### Cons
❌ Significant complexity
❌ Steeper learning curve
❌ Overkill for current scale
❌ More infrastructure (Redis Streams, workers)

---

## Recommendation

**Start with Approach 2: Activity Stream with Database**

### Rationale
1. **Single Source of Truth**: `agent_activities` table captures everything
2. **Scalable**: Easy to add new activity types
3. **Queryable**: Dashboard, analytics, alerts can all read from same source
4. **Not Over-Engineered**: Right complexity for your scale (50+ agents)
5. **Migration Path**: Can evolve to Approach 3 later if needed

### Implementation Plan

**Phase 1: Core Infrastructure (2-3 hours)**
- ✅ Create `agent_activities` table
- ✅ Implement `ActivityService` with DB persistence
- ✅ Add WebSocket broadcasting
- ✅ Inject into main.py

**Phase 2: Chat Integration (1-2 hours)**
- ✅ Track chat start/end in chat.py
- ✅ Track tool calls (extract from execution_log)
- ✅ Include context updates

**Phase 3: Schedule Integration (1 hour)**
- ✅ Track schedule start/end in schedules.py
- ✅ Link to existing schedule_executions

**Phase 4: Collaboration Integration (30 min)**
- ✅ Track agent-to-agent calls
- ✅ Extend with source/target info

**Phase 5: Query API (1 hour)**
- ✅ Activity timeline endpoint
- ✅ Agent-specific activity list
- ✅ Filtering by type/time range

### Backward Compatibility
- Existing tables (`chat_messages`, `schedule_executions`) remain unchanged
- New `agent_activities` table supplements (doesn't replace) existing data
- Gradually migrate dashboards to use unified activity stream

---

## Tool/Sub-Agent Tracking

For tracking tools and sub-agents in broadcasts:

```python
# When processing execution_log from chat response:
for tool_call in execution_log:
    await activity_service.track_activity(ActivityEvent(
        activity_type=ActivityType.TOOL_CALL,
        agent_name=name,
        user_id=current_user.id,
        details={
            "tool_name": tool_call["tool"],
            "tool_input": tool_call.get("input_summary"),
            "duration_ms": tool_call.get("duration_ms"),
            "parent_activity_id": chat_activity_id  # Link to parent chat
        }
    ))

    # If it's a sub-agent call (MCP trinity tool)
    if tool_call["tool"] == "mcp__trinity__chat_with_agent":
        await activity_service.track_activity(ActivityEvent(
            activity_type=ActivityType.AGENT_COLLABORATION,
            agent_name=name,
            user_id=current_user.id,
            details={
                "target_agent": tool_call["input"].get("agent_name"),
                "message_preview": tool_call["input"].get("message", "")[:50]
            }
        ))
```

---

## Future Extensions

With this architecture, you can easily add:

1. **Metrics Collection**
   ```python
   activity_service.subscribe(metrics_collector.record_event)
   ```

2. **Alert System**
   ```python
   activity_service.subscribe(alert_manager.check_thresholds)
   ```

3. **Analytics Pipeline**
   ```python
   activity_service.subscribe(analytics_pipeline.enqueue)
   ```

4. **External Integrations**
   ```python
   activity_service.subscribe(slack_notifier.send_update)
   ```

All without modifying core activity tracking logic!

---

## Decision Required

Please choose:
1. **Approach 1** (Lightweight) - Fastest, minimal changes, no new tables
2. **Approach 2** (Activity Stream) - Recommended, single source of truth, scalable
3. **Approach 3** (Event Sourcing) - Most robust, highest complexity
4. **Hybrid** - Start with Approach 1, migrate to Approach 2 later

I recommend **Approach 2** for long-term scalability and clean architecture.
