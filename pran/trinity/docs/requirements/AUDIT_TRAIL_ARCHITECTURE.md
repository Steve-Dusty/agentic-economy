# Audit Trail Architecture

> **Status**: Approved for Implementation
> **Created**: 2026-01-18
> **Priority**: HIGH
> **Requirement ID**: SEC-001

## Executive Summary

Comprehensive audit logging system for Trinity platform to track all user and agent actions with full actor attribution. Enables investigation of incidents, compliance reporting, and accountability.

## Problem Statement

### Current Gaps

| Event Type | Current Behavior | Risk |
|------------|------------------|------|
| Agent create/start/stop/delete | WebSocket broadcast only (ephemeral) | Cannot reconstruct who did what |
| MCP tool invocations | `console.log` only | No audit of API-based actions |
| User logins | Nothing | No authentication audit trail |
| Permission changes | Nothing | Cannot trace access control changes |
| Agent sharing | Nothing | Who shared what with whom unknown |
| Settings changes | Nothing | No config change history |
| Git sync operations | Nothing | Code deployment gaps |
| Credential operations | Nothing | Security-critical blind spot |

### What's Already Tracked (Keep As-Is)

| Event Type | Storage | Purpose |
|------------|---------|---------|
| Chat messages | `chat_messages` | Conversation history |
| Tool calls (during chat) | `agent_activities` | Runtime observability |
| Schedule executions | `schedule_executions` | Execution history with logs |
| Agent collaboration | `agent_activities` | Dashboard timeline |
| Container logs | Vector → JSON files | Debugging |
| **Process operations** | `audit_entries` (Process Engine) | Process-specific audit trail |

### Process Engine Audit (Implemented 2026-01-16)

The Process Engine has its own comprehensive audit system in `src/backend/services/process_engine/`:

| Component | Location | Description |
|-----------|----------|-------------|
| `AuditService` | `services/audit.py` | Service layer with log(), query(), count() |
| `AuditRepository` | `repositories/audit.py` | SQLite storage in `audit_entries` table |
| Domain Events | `domain/events.py` | 25+ immutable event types |

**Process Engine Audit Actions** (`AuditAction` enum):
- Process lifecycle: `PROCESS_CREATE`, `PROCESS_READ`, `PROCESS_UPDATE`, `PROCESS_DELETE`, `PROCESS_PUBLISH`, `PROCESS_ARCHIVE`
- Execution: `EXECUTION_TRIGGER`, `EXECUTION_VIEW`, `EXECUTION_CANCEL`, `EXECUTION_RETRY`, `EXECUTION_COMPLETE`, `EXECUTION_FAIL`
- Approval: `APPROVAL_REQUEST`, `APPROVAL_DECIDE`, `APPROVAL_DELEGATE`, `APPROVAL_EXPIRE`
- Admin: `ADMIN_CONFIG_CHANGE`, `ADMIN_RECOVERY`, `AUTH_FAILURE`

**Relationship to Platform Audit**:
- Process Engine audit is **domain-specific** (process workflows)
- Platform audit (`audit_log`) is **cross-cutting** (agents, auth, MCP, credentials)
- Both are append-only and immutable
- **Decision**: Keep separate for separation of concerns; unified query API can span both if needed

## Solution: Dedicated Audit Log

### Design Principles

1. **Append-only**: No updates or deletes within retention period
2. **Actor attribution**: Every event linked to WHO performed it
3. **MCP-aware**: Full context from MCP API key authentication
4. **Queryable**: Indexed for common investigation patterns
5. **Tamper-evident**: Optional hash chain for compliance
6. **Separate concerns**: Audit ≠ Observability (different retention, queries)

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Audit Data Flow                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │  Frontend    │     │  MCP Server  │     │  Scheduler   │                │
│  │  (User)      │     │  (Agent/API) │     │  (System)    │                │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                │
│         │                    │                    │                         │
│         ▼                    ▼                    ▼                         │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                     Backend API Layer                            │       │
│  │  ┌─────────────────────────────────────────────────────────┐    │       │
│  │  │                   AuditService                           │    │       │
│  │  │  - Extract actor from JWT/MCP context                    │    │       │
│  │  │  - Generate event_id (UUID)                              │    │       │
│  │  │  - Compute entry_hash (optional)                         │    │       │
│  │  │  - INSERT into audit_log                                 │    │       │
│  │  └─────────────────────────────────────────────────────────┘    │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                     SQLite: audit_log                            │       │
│  │  - Append-only (triggers prevent UPDATE/DELETE)                  │       │
│  │  - Indexed for fast queries                                      │       │
│  │  - Hash chain for tamper evidence (optional)                     │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │  Audit API   │     │  WebSocket   │     │  Export      │                │
│  │  (query)     │     │  (optional)  │     │  (CSV/JSON)  │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Database Schema

### Table: `audit_log`

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Event identification
    event_id TEXT UNIQUE NOT NULL,        -- UUID for deduplication
    event_type TEXT NOT NULL,             -- Category (see AuditEventType)
    event_action TEXT NOT NULL,           -- Specific action (create, start, delete, etc.)

    -- Actor attribution (WHO)
    actor_type TEXT NOT NULL,             -- 'user', 'agent', 'system', 'mcp_client'
    actor_id TEXT,                        -- user.id or agent_name
    actor_email TEXT,                     -- For user actors
    actor_ip TEXT,                        -- Client IP address

    -- MCP-specific attribution
    mcp_key_id TEXT,                      -- MCP API key ID if via MCP
    mcp_key_name TEXT,                    -- MCP API key name
    mcp_scope TEXT,                       -- 'user', 'agent', 'system'

    -- Target (WHAT was affected)
    target_type TEXT,                     -- 'agent', 'user', 'schedule', 'permission', etc.
    target_id TEXT,                       -- agent_name, user_id, schedule_id, etc.

    -- Event details
    timestamp TEXT NOT NULL,              -- ISO8601 UTC with 'Z' suffix
    details TEXT,                         -- JSON payload with event-specific data

    -- Request context
    request_id TEXT,                      -- Correlation ID for request tracing
    source TEXT NOT NULL,                 -- 'api', 'mcp', 'scheduler', 'system'
    endpoint TEXT,                        -- API endpoint path

    -- Tamper evidence (optional hash chain)
    previous_hash TEXT,                   -- Hash of previous entry
    entry_hash TEXT,                      -- SHA256 of this entry's content

    -- Metadata
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for common query patterns
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_event_type ON audit_log(event_type, timestamp DESC);
CREATE INDEX idx_audit_actor ON audit_log(actor_type, actor_id, timestamp DESC);
CREATE INDEX idx_audit_target ON audit_log(target_type, target_id, timestamp DESC);
CREATE INDEX idx_audit_mcp_key ON audit_log(mcp_key_id, timestamp DESC);
CREATE INDEX idx_audit_request ON audit_log(request_id);

-- Immutability enforcement
CREATE TRIGGER audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'Audit log entries cannot be modified');
END;

CREATE TRIGGER audit_log_no_delete
BEFORE DELETE ON audit_log
WHEN OLD.timestamp > datetime('now', '-365 days')
BEGIN
    SELECT RAISE(ABORT, 'Audit log entries cannot be deleted within retention period');
END;
```

## Event Types

### Enum: `AuditEventType`

```python
class AuditEventType(str, Enum):
    # Agent lifecycle
    AGENT_LIFECYCLE = "agent_lifecycle"
    # Actions: create, start, stop, delete, recreate

    # Execution
    EXECUTION = "execution"
    # Actions: task_triggered, chat_started, schedule_triggered

    # Authentication
    AUTHENTICATION = "authentication"
    # Actions: login_success, login_failed, logout, token_refresh

    # Authorization
    AUTHORIZATION = "authorization"
    # Actions: permission_grant, permission_revoke, share, unshare

    # Configuration
    CONFIGURATION = "configuration"
    # Actions: settings_change, resource_limits, autonomy_toggle

    # Credentials
    CREDENTIALS = "credentials"
    # Actions: create, delete, reload, oauth_complete

    # MCP Operations
    MCP_OPERATION = "mcp_operation"
    # Actions: tool_call, key_create, key_revoke

    # Git Operations
    GIT_OPERATION = "git_operation"
    # Actions: sync, pull, init, commit

    # System
    SYSTEM = "system"
    # Actions: startup, shutdown, emergency_stop
```

## Service Layer

### File: `src/backend/services/audit_service.py`

```python
"""
Audit logging service for security and compliance tracking.

All administrative actions flow through this service to ensure
consistent, immutable audit trail with actor attribution.
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from database import db
from models import User


class AuditEventType(str, Enum):
    AGENT_LIFECYCLE = "agent_lifecycle"
    EXECUTION = "execution"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONFIGURATION = "configuration"
    CREDENTIALS = "credentials"
    MCP_OPERATION = "mcp_operation"
    GIT_OPERATION = "git_operation"
    SYSTEM = "system"


class AuditService:
    """
    Centralized audit logging with immutability guarantees.

    Features:
    - Actor attribution from JWT or MCP context
    - Append-only storage
    - Optional hash chain for tamper evidence
    - Structured for compliance queries
    """

    def __init__(self):
        self._last_hash: Optional[str] = None
        self._hash_chain_enabled = False  # Enable for compliance mode

    async def log(
        self,
        event_type: AuditEventType,
        event_action: str,
        source: str,
        # Actor (at least one required)
        actor_user: Optional[User] = None,
        actor_agent_name: Optional[str] = None,
        actor_ip: Optional[str] = None,
        # MCP context (if via MCP)
        mcp_key_id: Optional[str] = None,
        mcp_key_name: Optional[str] = None,
        mcp_scope: Optional[str] = None,
        # Target
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        # Context
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an audit event.

        Returns:
            event_id: UUID of the created audit entry
        """
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Determine actor type and ID
        if actor_user:
            actor_type = "user"
            actor_id = str(actor_user.id)
            actor_email = actor_user.email
        elif actor_agent_name:
            actor_type = "agent"
            actor_id = actor_agent_name
            actor_email = None
        elif mcp_scope == "system":
            actor_type = "system"
            actor_id = "trinity-system"
            actor_email = None
        else:
            actor_type = "mcp_client"
            actor_id = mcp_key_id
            actor_email = None

        # Build entry
        entry = {
            "event_id": event_id,
            "event_type": event_type.value,
            "event_action": event_action,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "actor_email": actor_email,
            "actor_ip": actor_ip,
            "mcp_key_id": mcp_key_id,
            "mcp_key_name": mcp_key_name,
            "mcp_scope": mcp_scope,
            "target_type": target_type,
            "target_id": target_id,
            "timestamp": timestamp,
            "details": json.dumps(details) if details else None,
            "request_id": request_id,
            "source": source,
            "endpoint": endpoint,
        }

        # Compute hash chain (optional)
        if self._hash_chain_enabled:
            entry["previous_hash"] = self._last_hash
            entry["entry_hash"] = self._compute_hash(entry)
            self._last_hash = entry["entry_hash"]

        # Insert (append-only)
        db.create_audit_entry(entry)

        return event_id

    def _compute_hash(self, entry: Dict) -> str:
        """Compute SHA256 hash of entry content."""
        content = json.dumps({
            "event_id": entry["event_id"],
            "event_type": entry["event_type"],
            "event_action": entry["event_action"],
            "actor_id": entry["actor_id"],
            "target_id": entry["target_id"],
            "timestamp": entry["timestamp"],
            "details": entry["details"],
            "previous_hash": entry.get("previous_hash")
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    async def verify_chain(self, start_id: int, end_id: int) -> bool:
        """Verify hash chain integrity between two entries."""
        entries = db.get_audit_entries_range(start_id, end_id)

        for i, entry in enumerate(entries):
            if i == 0:
                continue
            expected_hash = self._compute_hash(entry)
            if entry["entry_hash"] != expected_hash:
                return False
        return True


# Global instance
audit_service = AuditService()
```

### File: `src/backend/db/audit.py`

```python
"""
Database operations for audit log.
"""

from typing import Dict, List, Optional, Any


def create_audit_entry(self, entry: Dict[str, Any]) -> None:
    """Insert audit log entry (append-only)."""
    self.execute("""
        INSERT INTO audit_log (
            event_id, event_type, event_action,
            actor_type, actor_id, actor_email, actor_ip,
            mcp_key_id, mcp_key_name, mcp_scope,
            target_type, target_id,
            timestamp, details, request_id, source, endpoint,
            previous_hash, entry_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry["event_id"], entry["event_type"], entry["event_action"],
        entry["actor_type"], entry["actor_id"], entry.get("actor_email"), entry.get("actor_ip"),
        entry.get("mcp_key_id"), entry.get("mcp_key_name"), entry.get("mcp_scope"),
        entry.get("target_type"), entry.get("target_id"),
        entry["timestamp"], entry.get("details"), entry.get("request_id"),
        entry["source"], entry.get("endpoint"),
        entry.get("previous_hash"), entry.get("entry_hash")
    ))


def get_audit_entries(
    self,
    event_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """Query audit log with filters."""
    conditions = []
    params = []

    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)
    if actor_id:
        conditions.append("actor_id = ?")
        params.append(actor_id)
    if target_type:
        conditions.append("target_type = ?")
        params.append(target_type)
    if target_id:
        conditions.append("target_id = ?")
        params.append(target_id)
    if start_time:
        conditions.append("timestamp >= ?")
        params.append(start_time)
    if end_time:
        conditions.append("timestamp <= ?")
        params.append(end_time)

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    params.extend([limit, offset])

    return self.fetch_all(f"""
        SELECT * FROM audit_log
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    """, params)


def get_audit_entry(self, event_id: str) -> Optional[Dict]:
    """Get single audit entry by event_id."""
    return self.fetch_one(
        "SELECT * FROM audit_log WHERE event_id = ?",
        (event_id,)
    )


def get_audit_entries_range(self, start_id: int, end_id: int) -> List[Dict]:
    """Get entries by ID range for hash chain verification."""
    return self.fetch_all(
        "SELECT * FROM audit_log WHERE id BETWEEN ? AND ? ORDER BY id",
        (start_id, end_id)
    )
```

## API Endpoints

### File: `src/backend/routers/audit.py`

```python
"""
Audit log API endpoints.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import datetime

from database import db
from dependencies import get_current_user, require_admin
from models import User
from services.audit_service import audit_service

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
async def list_audit_entries(
    event_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_admin)  # Admin only
):
    """
    List audit log entries with optional filters.

    Admin access required.
    """
    entries = db.get_audit_entries(
        event_type=event_type,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )
    return {"entries": entries, "count": len(entries)}


@router.get("/{event_id}")
async def get_audit_entry(
    event_id: str,
    current_user: User = Depends(require_admin)
):
    """Get single audit entry by event_id."""
    entry = db.get_audit_entry(event_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return entry


@router.get("/export")
async def export_audit_log(
    start_time: str,
    end_time: str,
    format: str = Query(default="json", regex="^(json|csv)$"),
    current_user: User = Depends(require_admin)
):
    """
    Export audit log for compliance reporting.

    Returns all entries in the time range.
    """
    entries = db.get_audit_entries(
        start_time=start_time,
        end_time=end_time,
        limit=100000  # High limit for export
    )

    if format == "csv":
        # Return CSV format
        import csv
        import io
        output = io.StringIO()
        if entries:
            writer = csv.DictWriter(output, fieldnames=entries[0].keys())
            writer.writeheader()
            writer.writerows(entries)
        return {"content": output.getvalue(), "format": "csv"}

    return {"entries": entries, "format": "json"}


@router.post("/verify-integrity")
async def verify_audit_integrity(
    start_id: int,
    end_id: int,
    current_user: User = Depends(require_admin)
):
    """
    Verify hash chain integrity for a range of entries.

    Returns True if chain is intact, False if tampering detected.
    """
    is_valid = await audit_service.verify_chain(start_id, end_id)
    return {"valid": is_valid, "start_id": start_id, "end_id": end_id}
```

## Integration Points

### 1. Agent Lifecycle (agents.py)

```python
# In start_agent_endpoint, stop_agent_endpoint, create_agent, delete_agent

await audit_service.log(
    event_type=AuditEventType.AGENT_LIFECYCLE,
    event_action="start",  # or "stop", "create", "delete"
    actor_user=current_user,
    actor_ip=request.client.host,
    target_type="agent",
    target_id=agent_name,
    source="api",
    endpoint=f"/api/agents/{agent_name}/start",
    request_id=getattr(request.state, "request_id", None),
    details={"container_id": container.id, "template": template_name}
)
```

### 2. MCP Server (agents.ts, chat.ts)

```typescript
// After each tool execution
await apiClient.post("/api/audit/log", {
    event_type: "mcp_operation",
    event_action: "tool_call",
    mcp_key_id: authContext.keyId,
    mcp_key_name: authContext.keyName,
    mcp_scope: authContext.scope,
    actor_agent_name: authContext.agentName,
    target_type: "agent",
    target_id: targetAgentName,
    source: "mcp",
    details: { tool: "start_agent", params: { name } }
});
```

### 3. Authentication (auth.py)

```python
# In login endpoints (email verify, admin login)

await audit_service.log(
    event_type=AuditEventType.AUTHENTICATION,
    event_action="login_success",  # or "login_failed"
    actor_user=user if success else None,
    actor_ip=request.client.host,
    source="api",
    endpoint="/api/auth/email/verify",
    details={"method": "email", "email": email}
)
```

### 4. Permissions (sharing.py, permissions endpoints)

```python
# When sharing agent or granting permissions

await audit_service.log(
    event_type=AuditEventType.AUTHORIZATION,
    event_action="share",  # or "permission_grant", "permission_revoke"
    actor_user=current_user,
    target_type="agent",
    target_id=agent_name,
    source="api",
    details={"shared_with": target_email, "access_level": "shared"}
)
```

### 5. Scheduler Service

```python
# When schedule triggers execution

await audit_service.log(
    event_type=AuditEventType.EXECUTION,
    event_action="schedule_triggered",
    actor_type="system",
    actor_id="scheduler",
    target_type="agent",
    target_id=agent_name,
    source="scheduler",
    details={"schedule_id": schedule.id, "schedule_name": schedule.name}
)
```

## Query Examples

### Investigation Queries

```sql
-- All actions by a specific user in the last 24 hours
SELECT * FROM audit_log
WHERE actor_id = 'user_123'
  AND timestamp > datetime('now', '-24 hours')
ORDER BY timestamp DESC;

-- All MCP tool calls from a specific API key
SELECT * FROM audit_log
WHERE mcp_key_id = 'key_abc'
ORDER BY timestamp DESC;

-- All agent lifecycle events for a specific agent
SELECT * FROM audit_log
WHERE target_type = 'agent'
  AND target_id = 'my-agent'
  AND event_type = 'agent_lifecycle'
ORDER BY timestamp DESC;

-- Chain of events in a time window (incident investigation)
SELECT * FROM audit_log
WHERE timestamp BETWEEN '2026-01-15T10:00:00Z' AND '2026-01-15T11:00:00Z'
ORDER BY timestamp ASC;

-- All permission changes in the system
SELECT * FROM audit_log
WHERE event_type = 'authorization'
ORDER BY timestamp DESC;

-- Failed login attempts (security monitoring)
SELECT * FROM audit_log
WHERE event_type = 'authentication'
  AND event_action = 'login_failed'
ORDER BY timestamp DESC;

-- All actions by agents (not users)
SELECT * FROM audit_log
WHERE actor_type = 'agent'
ORDER BY timestamp DESC;
```

## Implementation Plan

### Phase 1: Core Infrastructure (Sprint 1)
- [ ] Create `audit_log` table with schema
- [ ] Add indexes and immutability triggers
- [ ] Create `AuditService` class
- [ ] Create `db/audit.py` database operations
- [ ] Add to DatabaseManager
- [ ] Create `/api/audit` router with basic endpoints
- [ ] Unit tests for service and DB operations

### Phase 2: Backend Integration (Sprint 2)
- [ ] Add audit logging to agent lifecycle (create, start, stop, delete)
- [ ] Add audit logging to authentication (login success/failure)
- [ ] Add audit logging to authorization (share, permissions)
- [ ] Add audit logging to settings changes
- [ ] Add audit logging to credential operations
- [ ] Add request_id middleware for correlation

### Phase 3: MCP Integration (Sprint 3)
- [ ] Add audit endpoint for MCP server to call
- [ ] Add audit logging to all MCP tools
- [ ] Pass full MCP auth context (key_id, key_name, scope, agent_name)
- [ ] Track API key usage statistics

### Phase 4: Advanced Features (Sprint 4)
- [ ] Enable hash chain for compliance mode
- [ ] Add export functionality (CSV, JSON)
- [ ] Add retention policy automation
- [ ] Add chain verification endpoint
- [ ] Documentation and compliance guide

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `src/backend/services/audit_service.py` | Audit service with logging logic |
| `src/backend/db/audit.py` | Database operations for audit_log |
| `src/backend/routers/audit.py` | API endpoints for audit queries |
| `docs/memory/feature-flows/audit-trail.md` | Feature flow documentation |

### Modified Files
| File | Change |
|------|--------|
| `src/backend/database.py` | Add audit_log table schema, mount db/audit.py |
| `src/backend/main.py` | Mount audit router |
| `src/backend/routers/agents.py` | Add audit logging to lifecycle endpoints |
| `src/backend/routers/auth.py` | Add audit logging to login endpoints |
| `src/backend/routers/sharing.py` | Add audit logging to share/unshare |
| `src/backend/services/agent_service/lifecycle.py` | Add audit logging |
| `src/backend/services/agent_service/crud.py` | Add audit logging to create/delete |
| `src/mcp-server/src/tools/agents.ts` | Add audit logging to tool calls |
| `src/mcp-server/src/tools/chat.ts` | Add audit logging to chat_with_agent |

## Relationship to Existing Systems

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              Trinity Data Systems                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │   audit_log      │  │  audit_entries   │  │ agent_activities │  │     Vector       │ │
│  │   (NEW)          │  │  (PROCESS ENGINE)│  │   (EXISTING)     │  │   (EXISTING)     │ │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤ │
│  │ Platform Audit   │  │ Process Audit    │  │ Observability    │  │ Debugging        │ │
│  │ WHO did WHAT     │  │ Process workflow │  │ Runtime timeline │  │ Container logs   │ │
│  │ Agents, Auth,    │  │ Definition CRUD  │  │ Dashboard viz    │  │ stdout/stderr    │ │
│  │ MCP, Credentials │  │ Exec lifecycle   │  │ Tool calls       │  │ File-based       │ │
│  │ IMMUTABLE        │  │ IMMUTABLE        │  │ Mutable          │  │ 90 day rotation  │ │
│  │ 1 year retention │  │ 1 year retention │  │ 90 day retention │  │                  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                                           │
│  Keep Existing (No Changes):                                                              │
│  - schedule_executions.execution_log → Full Claude Code transcripts                      │
│  - chat_messages → Conversation content                                                   │
│  - chat_sessions → Session metadata                                                       │
│  - process_executions, process_step_executions → Process execution state                 │
│                                                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Audit System Boundaries

| System | Scope | Storage | Retention |
|--------|-------|---------|-----------|
| **Platform Audit** (`audit_log`) | Agents, Auth, MCP, Credentials, Git, Settings | SQLite in main DB | 1 year |
| **Process Audit** (`audit_entries`) | Process definitions, Executions, Approvals | SQLite in process DB | 1 year |
| **Agent Activities** | Runtime observability (tool calls, chat, collaboration) | SQLite in main DB | 90 days |
| **Vector Logs** | Container stdout/stderr for debugging | JSON files | 90 days |

**Why Two Audit Systems?**
1. **Separation of concerns**: Process Engine is a self-contained domain with its own lifecycle
2. **Database isolation**: Process Engine can use separate database file if needed
3. **Query optimization**: Process queries don't affect platform audit performance
4. **Unified view possible**: Future API can aggregate both for compliance reporting

## Security Considerations

1. **Admin-only access**: Audit API requires admin role
2. **No PII in logs**: Don't log credential values, only metadata
3. **Immutability**: Database triggers prevent modification
4. **Retention**: 1-year minimum before deletion allowed
5. **Hash chain**: Optional tamper evidence for compliance

## Success Criteria

- [ ] All agent lifecycle events logged with actor attribution
- [ ] All MCP tool calls logged with API key attribution
- [ ] All authentication events logged (success and failure)
- [ ] All permission changes logged
- [ ] Query API returns results in <100ms for typical queries
- [ ] Hash chain verification works for any ID range
- [ ] Export produces valid CSV/JSON for compliance

## References

- [Event Sourcing Best Practices 2025](https://www.baytechconsulting.com/blog/event-sourcing-explained-2025)
- [Audit Trail Implementation Guide](https://www.datasunrise.com/knowledge-center/data-audit-trails/)
- [Immutability Enforcement Patterns](https://www.designgurus.io/answers/detail/how-do-you-enforce-immutability-and-appendonly-audit-trails)
