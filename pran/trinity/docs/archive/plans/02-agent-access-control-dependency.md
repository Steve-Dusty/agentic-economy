# Implementation Plan: Agent Access Control Dependency

**Priority**: HIGH
**Report Section**: 1.1 - Access Control Checks
**Estimated Effort**: Low
**Impact**: High - Eliminates ~100 lines of duplicated code, centralizes security logic

---

## Problem Statement

The same access control pattern appears in nearly every router endpoint (50+ times):

```python
# In routers/schedules.py, git.py, agents.py, chat.py, etc.
if not db.can_user_access_agent(current_user.username, name):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )
```

**Files Affected**:
- `routers/schedules.py`: 10+ occurrences
- `routers/git.py`: 6+ occurrences
- `routers/agents.py`: Multiple occurrences
- `routers/chat.py`: Multiple occurrences
- `routers/credentials.py`: Multiple occurrences

**Why this is a problem:**
1. Violates DRY principle - same code repeated 50+ times
2. Inconsistent error messages across endpoints
3. Easy to forget when adding new endpoints
4. Changes to access control require updating many files

---

## Solution

Create FastAPI dependencies that handle agent access authorization declaratively.

---

## Implementation Steps

### Step 1: Add Dependencies to `dependencies.py`

**File**: `src/backend/dependencies.py`

Add these new dependencies after the existing `get_current_user`:

```python
from typing import Annotated

def get_authorized_agent(
    name: str,
    current_user: User = Depends(get_current_user)
) -> str:
    """
    Dependency that validates user has access to an agent.

    Used for endpoints that require read access to an agent.
    Returns the agent name if authorized.

    Raises:
        HTTPException(403): If user cannot access the agent
    """
    if not db.can_user_access_agent(current_user.username, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to agent"
        )
    return name


def get_owned_agent(
    name: str,
    current_user: User = Depends(get_current_user)
) -> str:
    """
    Dependency that validates user owns or can share an agent.

    Used for endpoints that require owner-level access (delete, share, configure).
    Returns the agent name if authorized.

    Raises:
        HTTPException(403): If user is not owner/admin
    """
    if not db.can_user_share_agent(current_user.username, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required"
        )
    return name


# Type aliases for cleaner signatures
AuthorizedAgent = Annotated[str, Depends(get_authorized_agent)]
OwnedAgent = Annotated[str, Depends(get_owned_agent)]
CurrentUser = Annotated[User, Depends(get_current_user)]
```

### Step 2: Update Router Endpoints

**Example - Before** (`routers/schedules.py`):

```python
@router.get("/{name}/schedules", response_model=List[ScheduleResponse])
async def list_agent_schedules(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """List all schedules for an agent."""
    # Check user has access to this agent
    if not db.can_user_access_agent(current_user.username, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    schedules = db.list_agent_schedules(name)
    return [ScheduleResponse(**s.model_dump()) for s in schedules]
```

**Example - After** (using dependency):

```python
from dependencies import get_authorized_agent, CurrentUser

@router.get("/{name}/schedules", response_model=List[ScheduleResponse])
async def list_agent_schedules(
    name: str = Depends(get_authorized_agent),
    current_user: CurrentUser = None  # Still available if needed
):
    """List all schedules for an agent."""
    # Access check already done by dependency
    schedules = db.list_agent_schedules(name)
    return [ScheduleResponse(**s.model_dump()) for s in schedules]
```

**Or using the type alias** (cleaner):

```python
from dependencies import AuthorizedAgent

@router.get("/{name}/schedules", response_model=List[ScheduleResponse])
async def list_agent_schedules(name: AuthorizedAgent):
    """List all schedules for an agent."""
    schedules = db.list_agent_schedules(name)
    return [ScheduleResponse(**s.model_dump()) for s in schedules]
```

### Step 3: Update Each Router File

Apply the pattern to each router. The mapping:

| Access Level | Old Pattern | New Dependency |
|--------------|-------------|----------------|
| Read access | `can_user_access_agent()` | `get_authorized_agent` / `AuthorizedAgent` |
| Owner access | `can_user_share_agent()` | `get_owned_agent` / `OwnedAgent` |

**Files to update**:

1. **`routers/schedules.py`** (~10 endpoints)
   - `list_agent_schedules` → `AuthorizedAgent`
   - `create_schedule` → `OwnedAgent`
   - `get_schedule` → `AuthorizedAgent`
   - `update_schedule` → `OwnedAgent`
   - `delete_schedule` → `OwnedAgent`
   - `enable_schedule` → `OwnedAgent`
   - `disable_schedule` → `OwnedAgent`
   - `trigger_schedule` → `AuthorizedAgent`
   - `list_executions` → `AuthorizedAgent`

2. **`routers/git.py`** (~6 endpoints)
   - `get_git_status` → `AuthorizedAgent`
   - `sync_to_github` → `OwnedAgent`
   - `get_git_log` → `AuthorizedAgent`
   - `pull_from_github` → `AuthorizedAgent`
   - `get_git_config` → `AuthorizedAgent`
   - `initialize_github_sync` → `OwnedAgent`

3. **`routers/agents.py`** (multiple endpoints)
   - `get_agent` → `AuthorizedAgent`
   - `delete_agent` → `OwnedAgent`
   - `start_agent` → `AuthorizedAgent`
   - `stop_agent` → `AuthorizedAgent`
   - etc.

4. **`routers/chat.py`** (multiple endpoints)
   - `chat_with_agent` → `AuthorizedAgent`
   - `get_chat_history` → `AuthorizedAgent`
   - etc.

5. **`routers/credentials.py`** (multiple endpoints)

6. **`routers/sharing.py`** (multiple endpoints)

### Step 4: Handle Edge Cases

Some endpoints need both the agent name AND the current user:

```python
@router.post("/{name}/share")
async def share_agent(
    name: str = Depends(get_owned_agent),
    current_user: User = Depends(get_current_user),
    share_request: ShareRequest = ...
):
    # Need current_user to record who shared
    db.share_agent(name, share_request.email, current_user.username)
```

For these, keep both dependencies.

---

## Migration Strategy

### Phase 1: Add Dependencies (Non-Breaking)
1. Add new dependencies to `dependencies.py`
2. Run existing tests to ensure nothing breaks

### Phase 2: Migrate One Router at a Time
1. Start with `routers/schedules.py` (clean, well-tested)
2. Test thoroughly
3. Move to next router

### Phase 3: Remove Duplicated Checks
1. After all routers migrated, search for remaining `can_user_access_agent` calls
2. Ensure none are in router code (service layer is fine)

---

## Files Changed

| File | Change |
|------|--------|
| `dependencies.py` | Add `get_authorized_agent`, `get_owned_agent`, type aliases |
| `routers/schedules.py` | Replace 10 access checks with dependency |
| `routers/git.py` | Replace 6 access checks with dependency |
| `routers/agents.py` | Replace access checks with dependency |
| `routers/chat.py` | Replace access checks with dependency |
| `routers/credentials.py` | Replace access checks with dependency |
| `routers/sharing.py` | Replace access checks with dependency |

---

## Testing

1. **Unit Tests**: Add to `tests/test_dependencies.py`
   ```python
   def test_get_authorized_agent_allows_owner():
       # Setup user owns agent
       # Call dependency
       # Assert returns agent name

   def test_get_authorized_agent_denies_unauthorized():
       # Setup user doesn't own agent
       # Call dependency
       # Assert HTTPException 403
   ```

2. **Integration Tests**: Existing endpoint tests should still pass
   - All schedule endpoints
   - All git endpoints
   - All agent endpoints

3. **Manual Testing**:
   - Login as non-owner, try to access agent → 403
   - Login as owner, access works
   - Login as admin, access works (bypass)

---

## Rollback Plan

If issues arise:
1. Revert router changes (dependencies remain but unused)
2. Dependencies are additive - no breaking changes

---

## Benefits

1. **DRY**: Single implementation of access control logic
2. **Consistency**: Same error format across all endpoints
3. **Safety**: New endpoints naturally use dependency
4. **Testability**: Easy to mock in tests
5. **Documentation**: OpenAPI schema shows authorization requirements
6. **~100 lines removed**: Less code to maintain
