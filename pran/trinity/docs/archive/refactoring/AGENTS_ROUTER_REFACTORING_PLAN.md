# Agents Router Refactoring Plan

**Target File**: `src/backend/routers/agents.py` (2,928 lines)
**Objective**: Non-breaking refactoring that preserves all API signatures and external interfaces
**Created**: 2025-12-27

---

## Executive Summary

The `agents.py` router has grown to ~3000 lines handling 15+ distinct concerns. This plan moves internal logic to service modules while keeping all endpoint functions, exported functions, and API signatures unchanged.

### Safety Principles

1. **No API Changes**: All HTTP endpoints remain at same paths with same signatures
2. **No Import Changes for Consumers**: `main.py`, `systems.py`, `activities.py`, `system_service.py` will not need modification
3. **Keep Facade Pattern**: `agents.py` remains the single import point
4. **Incremental Changes**: Each step can be tested independently
5. **Feature Flows Preserved**: All documented feature flows remain accurate

---

## Current External Interface (MUST NOT CHANGE)

### Exported Functions (used by other modules)

| Function | Used By | Location |
|----------|---------|----------|
| `router` | `main.py:30` | APIRouter with all endpoints |
| `set_websocket_manager()` | `main.py:86` | WebSocket manager injection |
| `inject_trinity_meta_prompt()` | `main.py:92`, `system_agent.py` | Trinity injection helper |
| `start_agent_internal()` | `systems.py:382`, `system_service.py:398` | Internal agent start |
| `create_agent_internal()` | `systems.py:25` | Internal agent creation |
| `get_accessible_agents()` | `activities.py:42`, `systems.py:256,306,382,460` | Access-filtered agent list |

### Router Endpoints (25 total)

| Method | Path | Lines | Domain |
|--------|------|-------|--------|
| GET | `/api/agents` | 211-222 | CRUD |
| GET | `/api/agents/context-stats` | 225-305 | Stats |
| GET | `/api/agents/{name}` | 306-345 | CRUD |
| POST | `/api/agents` | 757-760 | CRUD |
| POST | `/api/agents/deploy-local` | 873-1140 | Deploy |
| DELETE | `/api/agents/{name}` | 1142-1249 | CRUD |
| POST | `/api/agents/{name}/start` | 1442-1480 | Lifecycle |
| POST | `/api/agents/{name}/stop` | 1483-1520 | Lifecycle |
| GET | `/api/agents/{name}/logs` | 1523-1549 | Logs/Stats |
| GET | `/api/agents/{name}/stats` | 1552-1613 | Logs/Stats |
| GET | `/api/agents/{name}/queue` | 1616-1642 | Queue |
| POST | `/api/agents/{name}/queue/clear` | 1645-1682 | Queue |
| POST | `/api/agents/{name}/queue/release` | 1685-1725 | Queue |
| GET | `/api/agents/{name}/info` | 1728-1808 | Info |
| GET | `/api/agents/{name}/files` | 1811-1871 | Files |
| GET | `/api/agents/{name}/files/download` | 1874-1935 | Files |
| GET | `/api/agents/{name}/activities` | 1942-1979 | Activities |
| GET | `/api/agents/activities/timeline` | 1982-2027 | Activities |
| GET | `/api/agents/{name}/permissions` | 2034-2084 | Permissions |
| PUT | `/api/agents/{name}/permissions` | 2087-2135 | Permissions |
| POST | `/api/agents/{name}/permissions/{target}` | 2138-2180 | Permissions |
| DELETE | `/api/agents/{name}/permissions/{target}` | 2183-2217 | Permissions |
| GET | `/api/agents/{name}/metrics` | 2224-2302 | Metrics |
| GET | `/api/agents/{name}/folders` | 2309-2389 | Folders |
| PUT | `/api/agents/{name}/folders` | 2392-2446 | Folders |
| GET | `/api/agents/{name}/folders/available` | 2449-2488 | Folders |
| GET | `/api/agents/{name}/folders/consumers` | 2491-2529 | Folders |
| GET | `/api/agents/{name}/api-key-setting` | 2536-2566 | API Key |
| PUT | `/api/agents/{name}/api-key-setting` | 2569-2617 | API Key |
| WS | `/api/agents/{name}/terminal` | 2624-2928 | Terminal |

---

## Proposed Architecture

```
src/backend/
├── routers/
│   └── agents.py           # Thin router layer (~500 lines)
│                           # - All endpoints (thin wrappers)
│                           # - External function exports (re-exports)
│                           # - Module-level state (manager, credential_manager)
│
└── services/
    └── agent_service/
        ├── __init__.py     # Re-exports for clean import
        ├── crud.py         # ~300 lines: create, delete, list, get
        ├── lifecycle.py    # ~250 lines: start, stop, inject, recreate
        ├── deploy.py       # ~270 lines: deploy-local endpoint logic
        ├── terminal.py     # ~310 lines: WebSocket PTY handling
        ├── permissions.py  # ~200 lines: agent-to-agent permissions
        ├── folders.py      # ~230 lines: shared folder config
        ├── files.py        # ~150 lines: file browser proxy
        ├── queue.py        # ~120 lines: execution queue
        ├── metrics.py      # ~100 lines: metrics proxy
        ├── stats.py        # ~150 lines: context stats, container stats
        └── helpers.py      # ~100 lines: shared utilities
```

---

## Step-by-Step Refactoring Plan

### Phase 1: Create Service Module Structure

**Goal**: Set up the new module structure without changing any behavior.

```bash
mkdir -p src/backend/services/agent_service
touch src/backend/services/agent_service/__init__.py
touch src/backend/services/agent_service/helpers.py
```

**File**: `src/backend/services/agent_service/__init__.py`
```python
"""
Agent Service - Business logic for agent operations.

This module contains the extracted business logic from routers/agents.py.
The router remains the single import point for external modules.
"""
from .helpers import (
    get_accessible_agents,
    sanitize_and_validate_name,
)
from .lifecycle import (
    inject_trinity_meta_prompt,
    start_agent_internal,
)
from .crud import (
    create_agent_internal,
)
```

**Verification**:
- [ ] Module imports work
- [ ] No runtime errors
- [ ] All tests pass

---

### Phase 2: Extract Helpers Module

**Goal**: Move shared utility functions that have no external dependencies.

**Create**: `src/backend/services/agent_service/helpers.py`

**Move these functions** (copy, don't delete yet):
- `get_accessible_agents()` (lines 172-208) - Used by activities.py, systems.py
- `get_agents_by_prefix()` (lines 783-810)
- `get_next_version_name()` (lines 813-843)
- `get_latest_version()` (lines 846-870)
- `_check_shared_folder_mounts_match()` (lines 1376-1416)
- `_check_api_key_env_matches()` (lines 1419-1440)

**Pattern**: Export from service, import in agents.py, delegate:

```python
# In agents.py, replace function body:
from services.agent_service.helpers import get_accessible_agents as _get_accessible_agents

def get_accessible_agents(current_user: User):
    """Facade - delegates to service layer."""
    return _get_accessible_agents(current_user)
```

**Verification**:
- [ ] `get_accessible_agents()` works from activities.py
- [ ] `get_accessible_agents()` works from systems.py
- [ ] All agent-related tests pass

---

### Phase 3: Extract Lifecycle Module

**Goal**: Move agent start/stop and Trinity injection logic.

**Create**: `src/backend/services/agent_service/lifecycle.py`

**Move these functions** (copy, then delegate):
- `inject_trinity_meta_prompt()` (lines 62-123)
- `start_agent_internal()` (lines 126-169)
- `_recreate_container_with_updated_config()` (lines 1252-1373)

**Dependencies to pass or import**:
- `db` (database)
- `docker_client` (from docker_service)
- `get_agent_container` (from docker_service)
- `get_anthropic_api_key` (from routers.settings)
- `logger`

**Pattern**:
```python
# lifecycle.py
from services.docker_service import docker_client, get_agent_container
from database import db
from routers.settings import get_anthropic_api_key

async def inject_trinity_meta_prompt(agent_name: str, max_retries: int = 5, retry_delay: float = 2.0) -> dict:
    # ... full implementation moved here
```

```python
# agents.py - keep as re-export
from services.agent_service.lifecycle import inject_trinity_meta_prompt, start_agent_internal
```

**Verification**:
- [ ] `inject_trinity_meta_prompt` importable from agents.py
- [ ] `start_agent_internal` works from systems.py
- [ ] Agent start/stop tests pass

---

### Phase 4: Extract CRUD Module

**Goal**: Move agent creation and deletion logic.

**Create**: `src/backend/services/agent_service/crud.py`

**Move these functions**:
- `create_agent_internal()` (lines 348-754) - The largest function, ~400 lines

**This function has many dependencies**:
- `db`, `docker_client`, `credential_manager`
- `get_github_template`, `generate_credential_files`
- `git_service`, `sanitize_agent_name`
- `get_anthropic_api_key`, `get_next_available_port`
- WebSocket `manager` for broadcasts

**Pattern** (pass manager as parameter):
```python
# crud.py
async def create_agent_internal(
    config: AgentConfig,
    current_user: User,
    request: Request,
    skip_name_sanitization: bool = False,
    ws_manager = None  # Optional WebSocket manager for broadcasts
) -> AgentStatus:
    # ... implementation
    if ws_manager:
        await ws_manager.broadcast(json.dumps({...}))
```

```python
# agents.py
from services.agent_service.crud import create_agent_internal as _create_agent_internal

async def create_agent_internal(config, current_user, request, skip_name_sanitization=False):
    return await _create_agent_internal(
        config, current_user, request, skip_name_sanitization,
        ws_manager=manager  # Pass module-level manager
    )
```

**Verification**:
- [ ] Agent creation works from UI
- [ ] Agent creation works from systems.py
- [ ] MCP key created correctly
- [ ] Git config created for GitHub agents
- [ ] Permissions granted automatically

---

### Phase 5: Extract Deploy Module

**Goal**: Move local agent deployment logic.

**Create**: `src/backend/services/agent_service/deploy.py`

**Move**:
- `deploy_local_agent()` endpoint logic (lines 873-1139) - NOT the endpoint decorator
- Supporting constants: `MAX_ARCHIVE_SIZE`, `MAX_CREDENTIALS`, `MAX_FILES`

**Pattern**:
```python
# deploy.py
async def deploy_local_agent_logic(
    body: DeployLocalRequest,
    current_user: User,
    request: Request,
    create_agent_fn,  # Pass create_agent_internal as dependency
    credential_manager
) -> DeployLocalResponse:
    # ... full implementation
```

```python
# agents.py - endpoint stays here
@router.post("/deploy-local")
async def deploy_local_agent(body: DeployLocalRequest, request: Request, current_user: User = Depends(get_current_user)):
    from services.agent_service.deploy import deploy_local_agent_logic
    return await deploy_local_agent_logic(
        body, current_user, request,
        create_agent_fn=create_agent_internal,
        credential_manager=credential_manager
    )
```

**Verification**:
- [ ] Local agent deployment via MCP works
- [ ] Versioning works (agent-1, agent-2)
- [ ] Credentials imported correctly

---

### Phase 6: Extract Terminal Module

**Goal**: Move WebSocket terminal handling.

**Create**: `src/backend/services/agent_service/terminal.py`

**Move**:
- `_active_terminal_sessions` dict
- `_terminal_lock` threading lock
- `agent_terminal()` WebSocket handler logic (lines 2624-2928)

**Pattern** (class-based for state management):
```python
# terminal.py
import threading

class TerminalSessionManager:
    def __init__(self):
        self._active_sessions = {}
        self._lock = threading.Lock()

    async def handle_terminal_session(
        self,
        websocket: WebSocket,
        agent_name: str,
        mode: str,
        docker_client,
        decode_token_fn,
        db
    ):
        # ... full implementation
```

```python
# agents.py
from services.agent_service.terminal import TerminalSessionManager

_terminal_manager = TerminalSessionManager()

@router.websocket("/{agent_name}/terminal")
async def agent_terminal(websocket: WebSocket, agent_name: str, mode: str = Query(default="claude")):
    await _terminal_manager.handle_terminal_session(
        websocket, agent_name, mode,
        docker_client=docker_client,
        decode_token_fn=decode_token,
        db=db
    )
```

**Verification**:
- [ ] Terminal connects and authenticates
- [ ] Session limiting works (1 per user per agent)
- [ ] PTY resize works
- [ ] Claude Code mode works
- [ ] Bash mode works
- [ ] Audit logs created

---

### Phase 7: Extract Permissions Module

**Goal**: Move permissions endpoints logic.

**Create**: `src/backend/services/agent_service/permissions.py`

**Move logic from**:
- `get_agent_permissions()` (lines 2034-2084)
- `set_agent_permissions()` (lines 2087-2135)
- `add_agent_permission()` (lines 2138-2180)
- `remove_agent_permission()` (lines 2183-2217)

**Pattern**: Move business logic, keep endpoint decorators in router.

**Verification**:
- [ ] Permissions tab loads in UI
- [ ] Grant/revoke permissions works
- [ ] Bulk set permissions works
- [ ] Audit logs created

---

### Phase 8: Extract Folders Module

**Goal**: Move shared folders endpoints logic.

**Create**: `src/backend/services/agent_service/folders.py`

**Move logic from**:
- `get_agent_folders()` (lines 2309-2389)
- `update_agent_folders()` (lines 2392-2446)
- `get_available_shared_folders()` (lines 2449-2488)
- `get_folder_consumers()` (lines 2491-2529)

**Verification**:
- [ ] Folders tab loads in UI
- [ ] Expose/consume toggles work
- [ ] Available folders list works
- [ ] Consumers list works

---

### Phase 9: Extract Remaining Modules

**Goal**: Move remaining endpoint logic.

**Create these modules**:

1. **`files.py`**: `list_agent_files_endpoint`, `download_agent_file_endpoint`
2. **`queue.py`**: `get_agent_queue_status`, `clear_agent_queue`, `force_release_agent`
3. **`metrics.py`**: `get_agent_metrics`
4. **`stats.py`**: `get_agents_context_stats`, `get_agent_stats_endpoint`
5. **`api_key.py`**: `get_agent_api_key_setting`, `update_agent_api_key_setting`

**Verification**:
- [ ] All endpoint tests pass
- [ ] File browser works
- [ ] Queue status works
- [ ] Metrics panel works
- [ ] Stats display works
- [ ] API key toggle works

---

### Phase 10: Final Cleanup

**Goal**: Remove dead code and optimize imports.

**Tasks**:
1. Remove duplicate function bodies (now in service modules)
2. Ensure all imports are clean
3. Update docstrings to indicate delegation
4. Verify file sizes:
   - `agents.py`: ~500 lines (endpoints + re-exports)
   - Each service module: 100-300 lines

**Final Structure**:
```python
# agents.py final structure (~500 lines)

"""Agent management routes - thin wrapper over service layer."""

# Standard imports
from fastapi import APIRouter, Depends, HTTPException, ...

# Service layer imports (re-exported for external consumers)
from services.agent_service import (
    get_accessible_agents,
    inject_trinity_meta_prompt,
    start_agent_internal,
    create_agent_internal,
)

# Module state
router = APIRouter(prefix="/api/agents", tags=["agents"])
credential_manager = CredentialManager(REDIS_URL)
manager = None

# Exported function for main.py
def set_websocket_manager(ws_manager):
    global manager
    manager = ws_manager

# All @router endpoints - thin wrappers calling service functions
@router.get("")
async def list_agents_endpoint(...):
    return get_accessible_agents(current_user)

# ... remaining endpoints
```

---

## Testing Strategy

### Pre-Refactoring

1. Run full test suite: `pytest tests/ -v`
2. Run API tests: `pytest tests/test_api.py -v`
3. Manual smoke test of key features

### During Refactoring (after each phase)

1. Run agent-related tests: `pytest tests/test_agent*.py -v`
2. Check imports work: `python -c "from routers.agents import router, create_agent_internal"`
3. Quick smoke test: Create agent, start, stop, delete

### Post-Refactoring

1. Full test suite
2. UI integration testing
3. MCP tool testing
4. Load testing (optional)

---

## Rollback Plan

Each phase creates new files without deleting old code. To rollback:

1. Delete new service module files
2. Remove import statements from agents.py
3. Uncomment original function bodies

The original function bodies are only deleted in Phase 10 after full verification.

---

## Metrics

### Before Refactoring
- `agents.py`: 2,928 lines
- Functions: 32
- Endpoints: 25
- Cognitive complexity: High

### After Refactoring (Target)
- `agents.py`: ~500 lines (thin router)
- `agent_service/`: 10 modules, 100-300 lines each
- Total lines: ~2,500 (slight reduction from cleanup)
- Cognitive complexity: Low per file

---

## Dependencies Summary

### External Modules That Import From agents.py

| Module | Imports | Must Continue Working |
|--------|---------|----------------------|
| `main.py` | `router`, `set_websocket_manager`, `inject_trinity_meta_prompt` | ✅ |
| `systems.py` | `create_agent_internal`, `get_accessible_agents`, `start_agent_internal` | ✅ |
| `activities.py` | `get_accessible_agents` | ✅ |
| `system_service.py` | `start_agent_internal` | ✅ |

### Internal Dependencies of agents.py

| Dependency | Used For |
|------------|----------|
| `database.db` | All database operations |
| `docker_client` | Container management |
| `credential_manager` | Credential handling |
| `git_service` | Git sync operations |
| `template_service` | Template processing |
| `scheduler_service` | Schedule management |
| `execution_queue` | Queue operations |
| `audit_service` | Audit logging |
| `docker_service` | Docker helpers |

---

## Feature Flows That Reference agents.py

These feature flows document current line numbers. After refactoring, consider updating them to reference service module locations:

1. `agent-lifecycle.md` - References lines 329-718, 726-729, 732-818, etc.
2. `agent-terminal.md` - References lines 2624-2900
3. `agent-permissions.md` - References lines 2037-2220
4. `agent-shared-folders.md` - References lines 2312-2529
5. `local-agent-deploy.md` - References line 856
6. `web-terminal.md` - References lines 2536-2617

**Note**: Feature flows can be updated after refactoring. The API behavior remains identical, only internal organization changes.

---

## Estimated Effort

| Phase | Effort | Risk |
|-------|--------|------|
| 1. Structure | 15 min | Low |
| 2. Helpers | 30 min | Low |
| 3. Lifecycle | 45 min | Medium |
| 4. CRUD | 60 min | Medium |
| 5. Deploy | 45 min | Low |
| 6. Terminal | 45 min | Medium |
| 7. Permissions | 30 min | Low |
| 8. Folders | 30 min | Low |
| 9. Remaining | 60 min | Low |
| 10. Cleanup | 30 min | Low |

**Total**: ~6 hours of focused work

---

## Execution Checklist

- [ ] Phase 1: Create module structure
- [ ] Phase 2: Extract helpers
- [ ] Phase 3: Extract lifecycle
- [ ] Phase 4: Extract CRUD
- [ ] Phase 5: Extract deploy
- [ ] Phase 6: Extract terminal
- [ ] Phase 7: Extract permissions
- [ ] Phase 8: Extract folders
- [ ] Phase 9: Extract remaining
- [ ] Phase 10: Final cleanup
- [ ] Update feature flows (optional)
- [ ] Update changelog
- [ ] Commit and push

---

## Notes

1. **Don't rush**: Each phase should be committed separately
2. **Test often**: Run tests after each phase
3. **Preserve signatures**: External callers must not change
4. **Use re-exports**: Keep agents.py as the import point
5. **Document as you go**: Update docstrings to indicate delegation

---

**Document Author**: Claude Code
**Ready for Execution**: Yes - start from Phase 1
