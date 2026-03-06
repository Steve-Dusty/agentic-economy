# Database.py Refactoring Plan

**Target File:** `src/backend/database.py` (2183 lines)
**Goal:** Split into modules under 1000 lines each

---

## Current Structure Analysis

| Section | Lines | Description |
|---------|-------|-------------|
| Pydantic Models | 1-220 | Data models for all entities |
| Init/Migrations | 221-580 | Schema creation and migrations |
| User Management | 581-860 | User CRUD, prefs, auth |
| Agent Ownership/Sharing | 861-1096 | Ownership, sharing, permissions |
| MCP API Keys | 1097-1372 | Key management |
| Schedules/Executions | 1373-1680 | Scheduling system |
| Git Config | 1681-1762 | Git settings per agent |
| Chat Sessions | 1763-1994 | Chat persistence |
| Activity Stream | 1995-2183 | Activity logging |

---

## Proposed Structure

```
src/backend/
├── database.py          # Core init, connection, base migrations (~400 lines)
├── models.py            # All Pydantic models (~220 lines)
└── db/
    ├── __init__.py      # Re-exports for backward compatibility
    ├── users.py         # User management + preferences (~280 lines)
    ├── agents.py        # Agent ownership, sharing (~240 lines)
    ├── mcp_keys.py      # MCP API key management (~280 lines)
    ├── schedules.py     # Schedules + executions (~310 lines)
    ├── chat.py          # Chat sessions + messages (~235 lines)
    └── activities.py    # Activity stream (~190 lines)
```

---

## Module Details

### 1. database.py (~400 lines)
**Purpose:** Core database initialization and migrations

**Contents:**
- Database connection setup
- `get_db_path()` function
- `init_db()` function
- Schema migrations
- Re-exports from submodules for backward compatibility

**Key Functions to Keep:**
- `init_db()`
- `get_db_path()`
- Migration functions

---

### 2. models.py (~220 lines)
**Purpose:** All Pydantic data models

**Contents:**
- `User`, `UserPreferences`
- `Agent`, `AgentShare`
- `MCPAPIKey`
- `Schedule`, `ScheduleExecution`
- `GitConfig`
- `ChatSession`, `ChatMessage`
- `Activity`

**Dependencies:** None (pure data models)

---

### 3. db/users.py (~280 lines)
**Purpose:** User management operations

**Functions to Extract:**
- `create_user()`
- `get_user_by_id()`
- `get_user_by_email()`
- `get_user_by_auth0_id()`
- `update_user()`
- `delete_user()`
- `get_user_preferences()`
- `update_user_preferences()`
- `list_users()`

**Dependencies:** `models.py`, `database.py` (for connection)

---

### 4. db/agents.py (~240 lines)
**Purpose:** Agent ownership and sharing

**Functions to Extract:**
- `get_agent_owner()`
- `set_agent_owner()`
- `get_agents_for_user()`
- `can_user_access_agent()`
- `share_agent()`
- `unshare_agent()`
- `get_agent_shares()`
- `get_shared_agents_for_user()`

**Dependencies:** `models.py`, `database.py`

---

### 5. db/mcp_keys.py (~280 lines)
**Purpose:** MCP API key management

**Functions to Extract:**
- `create_mcp_api_key()`
- `get_mcp_api_key()`
- `get_mcp_api_keys_for_user()`
- `update_mcp_api_key()`
- `delete_mcp_api_key()`
- `validate_mcp_api_key()`
- `record_mcp_api_key_usage()`

**Dependencies:** `models.py`, `database.py`

---

### 6. db/schedules.py (~310 lines)
**Purpose:** Schedule and execution management

**Functions to Extract:**
- `create_schedule()`
- `get_schedule()`
- `get_schedules_for_agent()`
- `update_schedule()`
- `delete_schedule()`
- `get_due_schedules()`
- `create_schedule_execution()`
- `get_schedule_executions()`
- `update_schedule_execution()`

**Dependencies:** `models.py`, `database.py`

---

### 7. db/chat.py (~235 lines)
**Purpose:** Chat session and message persistence

**Functions to Extract:**
- `create_chat_session()`
- `get_chat_session()`
- `get_chat_sessions_for_agent()`
- `update_chat_session()`
- `delete_chat_session()`
- `add_chat_message()`
- `get_chat_messages()`
- `get_latest_chat_session()`

**Dependencies:** `models.py`, `database.py`

---

### 8. db/activities.py (~190 lines)
**Purpose:** Activity stream logging

**Functions to Extract:**
- `log_activity()`
- `get_activities_for_agent()`
- `get_activities_for_user()`
- `get_recent_activities()`
- `delete_activities_for_agent()`

**Dependencies:** `models.py`, `database.py`

---

## Migration Strategy

### Step 1: Create models.py
```python
# src/backend/models.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    # ... extract from database.py lines 1-220
```

### Step 2: Create db/ package
```python
# src/backend/db/__init__.py
"""Database submodules for domain-specific operations."""

from .users import *
from .agents import *
from .mcp_keys import *
from .schedules import *
from .chat import *
from .activities import *
```

### Step 3: Extract each module
Extract functions one module at a time, keeping original signatures.

### Step 4: Update database.py for backward compatibility
```python
# src/backend/database.py
# ... core init code ...

# Re-export for backward compatibility
from .models import *
from .db import *
```

### Step 5: Gradual import migration
Update routers to import from specific modules:
```python
# Before
from database import create_user, get_user_by_id

# After
from db.users import create_user, get_user_by_id
```

---

## Estimated Line Counts

| File | Lines | Status |
|------|-------|--------|
| `database.py` | ~400 | Core + re-exports |
| `models.py` | ~220 | Pure models |
| `db/users.py` | ~280 | User management |
| `db/agents.py` | ~240 | Ownership/sharing |
| `db/mcp_keys.py` | ~280 | API keys |
| `db/schedules.py` | ~310 | Scheduling |
| `db/chat.py` | ~235 | Chat persistence |
| `db/activities.py` | ~190 | Activity stream |
| **Total** | ~2155 | Slight overhead from imports |

---

## Risk Mitigation

1. **Backward Compatibility**
   - Keep re-exports in `database.py` initially
   - All existing imports continue to work
   - Deprecation warnings can be added later

2. **Testing**
   - Test each extraction before proceeding
   - Run existing API tests after each step
   - Verify database operations work correctly

3. **Circular Imports**
   - Models have no dependencies (extract first)
   - All db/* modules depend only on models and core database
   - Core database.py doesn't import from db/*

4. **Connection Handling**
   - Keep connection logic in core `database.py`
   - Pass connection/path to submodule functions
   - Or use a shared connection getter

---

## Feature Flows to Update

After refactoring, update line references in:
- `docs/memory/feature-flows/persistent-chat-tracking.md`
- Any other flows referencing `database.py`
