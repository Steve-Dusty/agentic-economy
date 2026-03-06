# Trinity Connect: Local-Remote Agent Synchronization

> **Requirement ID**: SYNC-001
> **Status**: Draft v2
> **Priority**: HIGH
> **Created**: 2026-02-05
> **Updated**: 2026-02-05

## Problem Statement

Users want to coordinate work between:
- **Local Claude Code** (running on their machine)
- **Trinity Agents** (running in Docker containers on Trinity platform)

Current options require polling or manual sync. Users need **real-time, push-based notifications** where a remote Trinity agent can wake up a local Claude Code instance when something happens.

## Solution Overview

Use a **blocking Bash script as a wake-up mechanism**:

1. Local Claude Code starts a listener script (via Bash tool or skill)
2. Script connects to a **new dedicated WebSocket endpoint** with MCP API key authentication
3. Server filters events to only agents the authenticated user can access
4. When matching event arrives, script prints it and exits
5. Claude Code sees the output and reacts to the event
6. Claude Code restarts the listener for the next event

This creates an event-driven loop without requiring daemons, hooks, or complex infrastructure.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Event-Driven Local Agent Loop                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Claude Code invokes: ./trinity-listen.sh                            │
│                              │                                           │
│                              ▼                                           │
│  2. Script connects to /ws/events?token=trinity_mcp_xxx                 │
│     Server validates MCP key, gets user's accessible agents              │
│                              │                                           │
│                              │  ← [Waits, receiving only filtered events]│
│                              │                                           │
│  3. Trinity Agent completes task ─────────────────────────►│            │
│     Server checks: Is this agent accessible to listener?   │            │
│     YES → Forward event                                    │            │
│                              │◄──────────────────────────────┘           │
│                              ▼                                           │
│  4. Script receives event, PRINTS it, EXITS                             │
│                              │                                           │
│                              ▼                                           │
│  5. Bash tool completes → Claude Code sees output                       │
│                              │                                           │
│                              ▼                                           │
│  6. Claude reacts to the event (processes work, responds, etc.)         │
│                              │                                           │
│                              ▼                                           │
│  7. Claude restarts listener: ./trinity-listen.sh                       │
│                              │                                           │
│                              └──────────► GOTO step 2                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Separate Endpoint (`/ws/events`)

**NOT modifying `/ws`**. The existing `/ws` endpoint serves the web UI with different requirements:
- Browser-based JWT authentication
- All events broadcast (UI shows everything)
- No filtering needed (UI handles display)

The new `/ws/events` endpoint:
- MCP API key authentication
- Server-side event filtering based on user's accessible agents
- Designed for external clients (CLI tools, scripts)

### 2. MCP API Key Authentication

Uses existing MCP API key infrastructure:
- Same keys users create in Settings → API Keys
- Validated via `db.validate_mcp_api_key()`
- Returns user identity for permission checking

### 3. Server-Side Event Filtering

Events are filtered **at the server** based on `db.can_user_access_agent()`:
- User only sees events for agents they own, are shared with, or (if admin) all agents
- Prevents information leakage
- No client-side filtering needed

### 4. Use Existing Events

**No new event types needed.** Trinity already broadcasts these events:

| Event Type | Source | When |
|------------|--------|------|
| `schedule_execution_completed` | `scheduler_service.py:261,316` | Scheduled task completes (success or fail) |
| `agent_activity` with `activity_state: completed` | `activity_service.py:138` | Any activity completes (chat, task, etc.) |
| `agent_activity` with `activity_state: failed` | `activity_service.py:138` | Any activity fails |
| `agent_collaboration` | `activity_service.py:89` | Agent-to-agent MCP call |
| `agent_started` / `agent_stopped` | `lifecycle.py` | Container state changes |

The listener can filter client-side by event type if needed.

---

## Components

### 1. New WebSocket Endpoint (`/ws/events`)

**Location**: `src/backend/main.py` (new endpoint, separate from `/ws`)

```python
# New WebSocket endpoint for external listeners with MCP key auth
@app.websocket("/ws/events")
async def websocket_events_endpoint(
    websocket: WebSocket,
    token: str = Query(None)  # MCP API key via query param
):
    """
    WebSocket endpoint for external event listeners.

    Authentication: MCP API key via ?token= query parameter
    Events: Filtered to only agents the authenticated user can access

    Usage: wscat -c "ws://localhost:8000/ws/events?token=trinity_mcp_xxx"
    """
    # Validate MCP API key
    if not token or not token.startswith("trinity_mcp_"):
        await websocket.close(code=4001, reason="MCP API key required")
        return

    key_info = db.validate_mcp_api_key(token)
    if not key_info:
        await websocket.close(code=4001, reason="Invalid MCP API key")
        return

    user_email = key_info.get("user_email")
    user_id = key_info.get("user_id")
    is_admin = key_info.get("is_admin", False)

    # Get list of accessible agents for this user (cached, refreshed periodically)
    accessible_agents = db.get_accessible_agent_names(user_email, is_admin)

    await websocket.accept()
    await websocket.send_json({
        "type": "connected",
        "user": user_email,
        "accessible_agents": accessible_agents,
        "message": "Listening for events. Events filtered to your accessible agents."
    })

    # Add to filtered connections manager
    await filtered_manager.connect(websocket, user_email, is_admin, accessible_agents)

    try:
        while True:
            # Keep connection alive, handle pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "refresh":
                # Refresh accessible agents list
                accessible_agents = db.get_accessible_agent_names(user_email, is_admin)
                await filtered_manager.update_accessible_agents(websocket, accessible_agents)
                await websocket.send_json({
                    "type": "refreshed",
                    "accessible_agents": accessible_agents
                })
    except WebSocketDisconnect:
        filtered_manager.disconnect(websocket)
```

### 2. Filtered WebSocket Manager

**Location**: `src/backend/main.py` (new class)

```python
class FilteredWebSocketManager:
    """WebSocket manager that filters events based on user's accessible agents."""

    def __init__(self):
        self.connections: Dict[WebSocket, Dict] = {}  # ws -> {email, is_admin, agents}

    async def connect(self, websocket: WebSocket, email: str, is_admin: bool, agents: List[str]):
        self.connections[websocket] = {
            "email": email,
            "is_admin": is_admin,
            "accessible_agents": set(agents)
        }

    def disconnect(self, websocket: WebSocket):
        self.connections.pop(websocket, None)

    async def update_accessible_agents(self, websocket: WebSocket, agents: List[str]):
        if websocket in self.connections:
            self.connections[websocket]["accessible_agents"] = set(agents)

    async def broadcast_filtered(self, event: dict):
        """Broadcast event only to users who can access the event's agent."""
        # Extract agent name from event (different fields for different event types)
        agent_name = (
            event.get("agent_name") or
            event.get("agent") or
            event.get("source_agent") or
            event.get("target_agent")
        )

        if not agent_name:
            return  # Can't filter without agent name

        disconnected = []
        for websocket, info in self.connections.items():
            # Admin sees all, otherwise check accessible agents
            if info["is_admin"] or agent_name in info["accessible_agents"]:
                try:
                    await websocket.send_json(event)
                except Exception:
                    disconnected.append(websocket)

        # Clean up disconnected
        for ws in disconnected:
            self.disconnect(ws)

# Global instance
filtered_manager = FilteredWebSocketManager()
```

### 3. Hook Into Existing Broadcasts

**Modification**: Add `filtered_manager.broadcast_filtered()` calls alongside existing `manager.broadcast()` calls.

**In `activity_service.py:200`**:
```python
await self.websocket_manager.broadcast(event)
# Also send to filtered listeners
await filtered_manager.broadcast_filtered(event)
```

**In `scheduler_service.py` (lines 260, 315, 342, etc.)**:
```python
await self._broadcast({...})
# Also send to filtered listeners
await filtered_manager.broadcast_filtered({...})
```

### 4. Listener Script (`trinity-listen.sh`)

**Location**: User's local machine or `scripts/trinity-listen.sh` for documentation

```bash
#!/bin/bash
# trinity-listen.sh - Blocks until Trinity event arrives
#
# Usage:
#   trinity-listen.sh                    # Listen for all events
#   trinity-listen.sh my-agent           # Filter to specific agent
#   trinity-listen.sh all completed      # Filter by event state
#
# Environment:
#   TRINITY_API_KEY    - Required: Your MCP API key
#   TRINITY_WS_URL     - Optional: WebSocket URL (default: ws://localhost:8000/ws/events)

set -e

TRINITY_WS="${TRINITY_WS_URL:-ws://localhost:8000/ws/events}"
API_KEY="${TRINITY_API_KEY:?TRINITY_API_KEY environment variable required}"
AGENT_FILTER="${1:-all}"
STATE_FILTER="${2:-all}"  # all, completed, failed, started

# Validate we have a tool to connect
if command -v websocat &> /dev/null; then
    WS_TOOL="websocat"
elif command -v wscat &> /dev/null; then
    WS_TOOL="wscat"
else
    echo "Error: websocat or wscat required. Install with:" >&2
    echo "  cargo install websocat" >&2
    echo "  # or" >&2
    echo "  npm install -g wscat" >&2
    exit 1
fi

echo "Connecting to Trinity (agent: $AGENT_FILTER, state: $STATE_FILTER)..." >&2

# Connect and process events
if [ "$WS_TOOL" = "websocat" ]; then
    websocat --text "${TRINITY_WS}?token=${API_KEY}" | \
    while IFS= read -r line; do
        event_type=$(echo "$line" | jq -r '.type // empty' 2>/dev/null)

        # Skip connection confirmation
        if [ "$event_type" = "connected" ] || [ "$event_type" = "refreshed" ]; then
            echo "Connected. Waiting for events..." >&2
            continue
        fi

        # Extract agent and state
        agent=$(echo "$line" | jq -r '.agent_name // .agent // .source_agent // empty' 2>/dev/null)
        state=$(echo "$line" | jq -r '.activity_state // .status // empty' 2>/dev/null)

        # Apply filters
        if [ "$AGENT_FILTER" != "all" ] && [ "$agent" != "$AGENT_FILTER" ]; then
            continue
        fi
        if [ "$STATE_FILTER" != "all" ] && [ "$state" != "$STATE_FILTER" ]; then
            continue
        fi

        # Output the event and exit
        echo "=== TRINITY EVENT ==="
        echo "$line" | jq .
        echo "=== END EVENT ==="
        exit 0
    done
else
    # wscat version
    wscat -c "${TRINITY_WS}?token=${API_KEY}" | \
    while IFS= read -r line; do
        # Same logic as above...
        event_type=$(echo "$line" | jq -r '.type // empty' 2>/dev/null)
        if [ "$event_type" = "connected" ]; then
            echo "Connected. Waiting for events..." >&2
            continue
        fi

        agent=$(echo "$line" | jq -r '.agent_name // .agent // .source_agent // empty' 2>/dev/null)
        state=$(echo "$line" | jq -r '.activity_state // .status // empty' 2>/dev/null)

        if [ "$AGENT_FILTER" != "all" ] && [ "$agent" != "$AGENT_FILTER" ]; then
            continue
        fi
        if [ "$STATE_FILTER" != "all" ] && [ "$state" != "$STATE_FILTER" ]; then
            continue
        fi

        echo "=== TRINITY EVENT ==="
        echo "$line" | jq .
        echo "=== END EVENT ==="
        exit 0
    done
fi
```

### 5. Database Helper Method

**Location**: `src/backend/db/agents.py` (new method)

```python
def get_accessible_agent_names(self, user_email: str, is_admin: bool = False) -> List[str]:
    """Get list of agent names the user can access."""
    if is_admin:
        # Admin sees all agents
        cursor = self.conn.execute("SELECT agent_name FROM agent_ownership")
        return [row[0] for row in cursor.fetchall()]

    # Get owned + shared agents
    cursor = self.conn.execute("""
        SELECT DISTINCT agent_name FROM (
            SELECT ao.agent_name FROM agent_ownership ao
            JOIN users u ON ao.owner_id = u.id
            WHERE u.email = ?
            UNION
            SELECT agent_name FROM agent_sharing
            WHERE shared_with_email = ?
        )
    """, (user_email, user_email))
    return [row[0] for row in cursor.fetchall()]
```

---

## Event Types (Existing)

These events are already broadcast and will be forwarded to `/ws/events` listeners:

### `schedule_execution_completed`

Broadcast when a scheduled task or manual trigger completes.

```json
{
  "type": "schedule_execution_completed",
  "agent": "my-research-agent",
  "schedule_id": "sched_abc123",
  "execution_id": "exec_xyz789",
  "status": "success"  // or "failed"
}
```

**Source**: `scheduler_service.py:261, 316, 342`

### `agent_activity` (completed)

Broadcast when any activity completes (chat, task, tool call).

```json
{
  "type": "agent_activity",
  "agent_name": "my-agent",
  "activity_id": "act_123",
  "activity_type": "chat_start",  // or "schedule_start", "tool_call"
  "activity_state": "completed",  // or "failed"
  "action": "Completed: chat_start",
  "timestamp": "2026-02-05T10:30:00.000Z",
  "details": {
    "context_used": 5000,
    "context_max": 200000,
    "cost_usd": 0.02,
    "tool_count": 5
  }
}
```

**Source**: `activity_service.py:138`

### `agent_collaboration`

Broadcast when agent-to-agent communication occurs.

```json
{
  "type": "agent_activity",
  "agent_name": "source-agent",
  "activity_type": "agent_collaboration",
  "activity_state": "started",
  "details": {
    "source_agent": "source-agent",
    "target_agent": "target-agent",
    "action": "chat"
  }
}
```

**Source**: `activity_service.py:89`, `chat.py:194-206`

### `agent_started` / `agent_stopped`

Broadcast when container state changes.

```json
{
  "type": "agent_started",
  "name": "my-agent",
  "trinity_injection": true
}
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (MVP)

| Task | Location | Effort |
|------|----------|--------|
| Add `FilteredWebSocketManager` class | `src/backend/main.py` | Low |
| Add `/ws/events` endpoint | `src/backend/main.py` | Low |
| Add `get_accessible_agent_names()` | `src/backend/db/agents.py` | Low |
| Hook filtered broadcasts into activity_service | `activity_service.py:200` | Low |
| Hook filtered broadcasts into scheduler_service | `scheduler_service.py` (multiple) | Low |
| Create `trinity-listen.sh` script | `scripts/trinity-listen.sh` | Low |
| Document in DEPLOYMENT.md | `docs/DEPLOYMENT.md` | Low |

**Estimated effort**: 2-3 hours

### Phase 2: Enhanced Reliability

| Task | Location | Effort |
|------|----------|--------|
| Add reconnection logic to listener script | `scripts/trinity-listen.sh` | Low |
| Add heartbeat/ping support | `/ws/events` endpoint | Low |
| Add connection timeout handling | `/ws/events` endpoint | Low |
| Rate limit connections per user | `/ws/events` endpoint | Medium |

### Phase 3: MCP Tools (Optional)

| Task | Location | Effort |
|------|----------|--------|
| Add `notify_agent` MCP tool | `src/mcp-server/tools/agents.ts` | Low |
| Add `/api/agents/{name}/notify` endpoint | `src/backend/routers/agents.py` | Low |

---

## Usage Examples

### Example 1: Wait for Task Completion

```bash
# Terminal: Local Claude Code session

User: "Start listening for my-research-agent to complete its task"

Claude runs:
$ export TRINITY_API_KEY="trinity_mcp_xxx"
$ ./trinity-listen.sh my-research-agent completed

# [Blocks until event arrives...]

# Output:
=== TRINITY EVENT ===
{
  "type": "schedule_execution_completed",
  "agent": "my-research-agent",
  "execution_id": "exec_123",
  "status": "success"
}
=== END EVENT ===

Claude: "my-research-agent has completed its task successfully. Let me check the results..."
```

### Example 2: React to Any Agent Activity

```bash
# Listen for any completed activity across all accessible agents
$ ./trinity-listen.sh all completed
```

### Example 3: Monitor Specific Agent

```bash
# Listen for all events from a specific agent
$ ./trinity-listen.sh my-data-processor all
```

### Example 4: Continuous Monitoring Loop

In a Claude Code skill or script:

```bash
while true; do
    echo "Waiting for next event..."
    EVENT=$(./trinity-listen.sh my-agent completed)

    # Process the event
    AGENT=$(echo "$EVENT" | jq -r '.agent // .agent_name')
    STATUS=$(echo "$EVENT" | jq -r '.status // .activity_state')

    echo "Agent $AGENT completed with status: $STATUS"

    # Do something with the result...
    git pull  # Get latest files

    # Continue listening
done
```

---

## Security Considerations

1. **MCP API Key Required**: `/ws/events` requires valid MCP API key - no anonymous access
2. **Server-Side Filtering**: Events filtered at server, not client - prevents information leakage
3. **Permission Model**: Uses existing `can_user_access_agent()` - owner, shared, or admin
4. **Key Rotation**: If key is compromised, revoke in Settings → API Keys
5. **Rate Limiting**: Consider limiting connections per user (Phase 2)

---

## Testing

### 1. WebSocket Authentication

```bash
# Should connect successfully with valid MCP key
websocat "ws://localhost:8000/ws/events?token=trinity_mcp_xxx"

# Should receive: {"type": "connected", "user": "user@example.com", ...}

# Should fail with invalid key
websocat "ws://localhost:8000/ws/events?token=invalid"
# Connection closed with code 4001
```

### 2. Event Filtering

```bash
# Terminal 1: Connect as user who owns agent-a but not agent-b
websocat "ws://localhost:8000/ws/events?token=trinity_mcp_user1"

# Terminal 2: Trigger execution on agent-a (should see event)
curl -X POST http://localhost:8000/api/agents/agent-a/schedules/123/trigger \
  -H "Authorization: Bearer $JWT"

# Terminal 3: Trigger execution on agent-b (should NOT see event)
curl -X POST http://localhost:8000/api/agents/agent-b/schedules/456/trigger \
  -H "Authorization: Bearer $JWT"
```

### 3. Listener Script

```bash
# Terminal 1: Start listener
export TRINITY_API_KEY="trinity_mcp_xxx"
./trinity-listen.sh my-agent

# Terminal 2: Trigger event
curl -X POST http://localhost:8000/api/agents/my-agent/schedules/123/trigger \
  -H "Authorization: Bearer $JWT"

# Terminal 1 should print event and exit
```

---

## Related Features

- **Execution Queue**: `docs/memory/feature-flows/execution-queue.md`
- **Activity Stream**: `docs/memory/feature-flows/activity-stream.md`
- **MCP API Keys**: `docs/memory/feature-flows/mcp-api-keys.md`
- **Scheduling**: `docs/memory/feature-flows/scheduling.md`

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-05 | v2 | Major revision: Separate `/ws/events` endpoint, MCP key auth, server-side filtering, use existing events |
| 2026-02-05 | v1 | Initial draft |
