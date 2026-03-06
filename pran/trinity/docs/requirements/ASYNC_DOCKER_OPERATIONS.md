# Async Docker Operations (DOCKER-001)

> **Issue**: [#42](https://github.com/abilityai/trinity/issues/42) - Blocking Docker calls in async lifecycle functions freeze entire backend
> **Priority**: P1 (Critical Path)
> **Status**: Ready for Implementation

## Problem Statement

The FastAPI backend contains blocking Docker SDK calls within `async` functions. Since FastAPI uses a single-threaded async event loop, these blocking calls prevent ALL other requests from being processed, causing:

- HTTP 499 client timeout errors
- WebSocket connection drops
- UI unresponsiveness for 10-30+ seconds
- Docker health checks marking backend as "unhealthy"

## Root Cause

Docker SDK calls (`container.stop()`, `container.start()`, `container.reload()`, `docker_client.containers.run()`, etc.) are synchronous blocking operations. When called directly in an `async` function without `run_in_executor()`, they block the entire event loop.

**Example of problematic code:**
```python
async def recreate_container_with_updated_config(...):
    old_container.stop()                    # Blocks 1-5 seconds
    old_container.remove()                  # Blocks 0.5-1 second
    docker_client.containers.run(...)       # Blocks 3-8 seconds
    # Total: 10-25+ seconds of event loop blocking
```

---

## Solution Overview

### 1. Create Docker Utilities Module

Create `src/backend/services/docker_utils.py` with async wrappers for all blocking Docker operations using `ThreadPoolExecutor`.

### 2. Update All Affected Files

Replace direct Docker SDK calls with async wrappers in all affected files.

### 3. Zero Fallbacks

The solution must work without fallbacks. All Docker operations MUST go through the async wrappers.

---

## Technical Design

### New Module: `src/backend/services/docker_utils.py`

```python
"""
Async-safe Docker operations.

Wraps blocking Docker SDK calls in ThreadPoolExecutor to prevent
event loop blocking. All Docker operations in async contexts MUST
use these functions instead of calling the Docker SDK directly.

Reference: src/backend/routers/telemetry.py (existing correct pattern)
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
import docker

from services.docker_service import docker_client

# Shared executor - limited to 4 workers to avoid overwhelming Docker daemon
# This matches the pattern in telemetry.py
_docker_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="docker-")


# =============================================================================
# Container Operations
# =============================================================================

async def container_stop(container, timeout: int = 10) -> None:
    """Stop a container without blocking the event loop.

    Args:
        container: Docker container object
        timeout: Seconds to wait before killing (default 10)
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_docker_executor, lambda: container.stop(timeout=timeout))


async def container_remove(container, force: bool = False) -> None:
    """Remove a container without blocking the event loop.

    Args:
        container: Docker container object
        force: Force removal even if running
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_docker_executor, lambda: container.remove(force=force))


async def container_start(container) -> None:
    """Start a container without blocking the event loop.

    Args:
        container: Docker container object
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_docker_executor, container.start)


async def container_reload(container) -> None:
    """Reload container attributes without blocking the event loop.

    Args:
        container: Docker container object
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_docker_executor, container.reload)


async def container_stats(container, stream: bool = False) -> Dict[str, Any]:
    """Get container stats without blocking the event loop.

    Args:
        container: Docker container object
        stream: If False, return single stats snapshot (default False)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _docker_executor,
        lambda: container.stats(stream=stream)
    )


# =============================================================================
# Volume Operations
# =============================================================================

async def volume_get(name: str) -> Any:
    """Get a volume without blocking the event loop.

    Args:
        name: Volume name

    Returns:
        Volume object

    Raises:
        docker.errors.NotFound: If volume doesn't exist
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_docker_executor, docker_client.volumes.get, name)


async def volume_create(name: str, labels: Optional[Dict[str, str]] = None) -> Any:
    """Create a volume without blocking the event loop.

    Args:
        name: Volume name
        labels: Optional labels dict

    Returns:
        Created volume object
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _docker_executor,
        lambda: docker_client.volumes.create(name=name, labels=labels or {})
    )


async def volume_remove(volume) -> None:
    """Remove a volume without blocking the event loop.

    Args:
        volume: Volume object
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_docker_executor, volume.remove)


# =============================================================================
# Container Creation (Complex)
# =============================================================================

async def containers_run(
    image: str,
    command: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Run a container without blocking the event loop.

    Accepts all docker-py containers.run() kwargs.

    Args:
        image: Image name
        command: Optional command to run
        **kwargs: All other containers.run() parameters

    Returns:
        Container object (if detach=True) or logs
    """
    loop = asyncio.get_event_loop()

    def _run():
        return docker_client.containers.run(image, command=command, **kwargs)

    return await loop.run_in_executor(_docker_executor, _run)


# =============================================================================
# Container Listing (Already optimized in docker_service.py)
# =============================================================================
# Note: list_all_agents() and list_all_agents_fast() are already efficient
# and don't require async wrappers as they complete quickly (<50ms).
# Only wrap if profiling shows they become a bottleneck.
```

---

## Files to Modify

### Phase 1: Primary Offenders (Critical)

#### 1.1 `src/backend/services/agent_service/lifecycle.py`

**Current blocking calls:**
| Line | Call | Duration |
|------|------|----------|
| 215 | `container.reload()` | 100-500ms |
| 227 | `container.reload()` (after get) | 100-500ms |
| 229 | `container.start()` | 2-5s |
| 325 | `old_container.stop()` | 1-5s |
| 328 | `old_container.remove()` | 0.5-1s |
| 357 | `docker_client.volumes.get()` | 100-300ms |
| 359-365 | `docker_client.volumes.create()` | 200-500ms |
| 371-377 | `docker_client.containers.run('alpine', ...)` | 2-5s |
| 388 | `docker_client.volumes.get()` | 100-300ms |
| 398-418 | `docker_client.containers.run()` | 3-8s |

**Changes:**
```python
# Add import at top
from services.docker_utils import (
    container_stop, container_remove, container_start, container_reload,
    volume_get, volume_create, containers_run
)

# Line 215: Change from
container.reload()
# To
await container_reload(container)

# Line 227: Change from
container.reload()
# To
await container_reload(container)

# Line 229: Change from
container.start()
# To
await container_start(container)

# Lines 324-328: Change from
try:
    old_container.stop()
except Exception:
    pass
old_container.remove()
# To
try:
    await container_stop(old_container)
except Exception:
    pass
await container_remove(old_container)

# Lines 356-366: Change from
try:
    docker_client.volumes.get(shared_volume_name)
except docker.errors.NotFound:
    docker_client.volumes.create(...)
# To
try:
    await volume_get(shared_volume_name)
except docker.errors.NotFound:
    await volume_create(
        name=shared_volume_name,
        labels={
            'trinity.platform': 'agent-shared',
            'trinity.agent-name': agent_name
        }
    )

# Lines 371-377: Change from
docker_client.containers.run(
    'alpine',
    command='chown 1000:1000 /shared',
    volumes={shared_volume_name: {'bind': '/shared', 'mode': 'rw'}},
    remove=True
)
# To
await containers_run(
    'alpine',
    command='chown 1000:1000 /shared',
    volumes={shared_volume_name: {'bind': '/shared', 'mode': 'rw'}},
    remove=True
)

# Line 388: Change from
docker_client.volumes.get(source_volume)
# To
await volume_get(source_volume)

# Lines 398-418: Change from
new_container = docker_client.containers.run(...)
# To
new_container = await containers_run(...)
```

#### 1.2 `src/backend/routers/agents.py`

**Current blocking calls:**
| Line | Function | Call |
|------|----------|------|
| 305 | `delete_agent` | `container.stop()` |
| 306 | `delete_agent` | `container.remove()` |
| 314 | `delete_agent` | `volume.remove()` |
| 320 | `delete_agent` | `docker_client.volumes.get()` |
| 350 | `delete_agent` | `docker_client.volumes.get()` |
| 351 | `delete_agent` | `shared_volume.remove()` |
| 419 | `stop_agent_endpoint` | `container.stop()` |
| 518 | `get_agent_info` | `container.reload()` |
| 1162 | `generate_ssh_access` | `container.reload()` |

**Changes:**
```python
# Add import at top
from services.docker_utils import (
    container_stop, container_remove, container_reload,
    volume_get, volume_remove
)

# Lines 305-306 (delete_agent): Change from
container.stop()
container.remove()
# To
await container_stop(container)
await container_remove(container)

# Lines 313-314: Change from
volume = docker_client.volumes.get(agent_volume_name)
volume.remove()
# To
volume = await volume_get(agent_volume_name)
await volume_remove(volume)

# Lines 349-351: Change from
shared_volume = docker_client.volumes.get(shared_volume_name)
shared_volume.remove()
# To
shared_volume = await volume_get(shared_volume_name)
await volume_remove(shared_volume)

# Line 419 (stop_agent_endpoint): Change from
container.stop()
# To
await container_stop(container)

# Lines 518, 1162: Change from
container.reload()
# To
await container_reload(container)
```

### Phase 2: Agent Service Files

#### 2.1 `src/backend/services/agent_service/crud.py`

**Blocking calls (lines 317-451):**
- Line 323: `docker_client.volumes.get(agent_volume_name)`
- Line 325: `docker_client.volumes.create(...)`
- Line 372: `docker_client.volumes.get(shared_volume_name)`
- Line 374: `docker_client.volumes.create(...)`
- Line 386: `docker_client.containers.run('alpine', ...)`
- Line 405: `docker_client.volumes.get(source_volume)`
- Line 419: `docker_client.containers.run(...)`

**Note:** `create_agent()` is already `async def`. All these calls need wrapping.

#### 2.2 `src/backend/services/agent_service/files.py`

**Blocking calls:**
- Lines 45, 98, 150, 204, 273: `container.reload()`

**Changes:** Replace all `container.reload()` with `await container_reload(container)`

#### 2.3 `src/backend/services/agent_service/folders.py`

**Blocking calls:**
- Line 44: `container.reload()`

**Changes:** Replace with `await container_reload(container)`

#### 2.4 `src/backend/services/agent_service/stats.py`

**Blocking calls:**
- Line 134: `container.reload()`
- Line 142: `container.stats(stream=False)`

**Changes:**
```python
await container_reload(container)
stats = await container_stats(container, stream=False)
```

#### 2.5 `src/backend/services/agent_service/dashboard.py`

**Blocking calls:**
- Line 206: `container.reload()`

**Changes:** Replace with `await container_reload(container)`

#### 2.6 `src/backend/services/agent_service/api_key.py`

**Blocking calls:**
- Line 38: `container.reload()`

**Changes:** Replace with `await container_reload(container)`

#### 2.7 `src/backend/services/agent_service/terminal.py`

**Blocking calls:**
- Line 172: `container.reload()`

**Changes:** Replace with `await container_reload(container)`

#### 2.8 `src/backend/services/agent_service/metrics.py`

**Blocking calls:**
- Line 51: `container.reload()`

**Changes:** Replace with `await container_reload(container)`

### Phase 3: System Services

#### 3.1 `src/backend/services/system_agent_service.py`

**Blocking calls:**
- Line 47: `container.reload()`
- Line 76: `container.reload()`
- Line 91: `container.start()`
- Line 239: `docker_client.containers.run(...)`

**Changes:**
```python
from services.docker_utils import container_reload, container_start, containers_run

# All container.reload() -> await container_reload(container)
# container.start() -> await container_start(container)
# docker_client.containers.run(...) -> await containers_run(...)
```

#### 3.2 `src/backend/routers/ops.py`

**Blocking calls (restart_all_agents function, lines 296-297):**
- Line 296: `container.stop(timeout=30)`
- Line 297: `container.start()`

**Changes:**
```python
await container_stop(container, timeout=30)
await container_start(container)
```

#### 3.3 `src/backend/routers/system_agent.py`

**Blocking calls:**
- Lines 68, 130, 139, 221, 228, 388: `container.reload()`
- Lines 138, 227: `container.start()`

**Changes:** Replace all with async wrappers.

#### 3.4 `src/backend/services/agent_service/deploy.py`

**Blocking calls:**
- Line 303: `container.stop()`

**Changes:** Replace with `await container_stop(container)`

#### 3.5 `src/backend/routers/systems.py`

**Blocking calls:**
- Line 388: `container.stop()`

**Changes:** Replace with `await container_stop(container)`

#### 3.6 `src/backend/services/agent_service/helpers.py`

**Blocking calls:**
- Line 303: `docker_client.volumes.get(source_volume)`

**Note:** This is in a sync function `check_shared_folder_mounts_match()`. Either:
- Keep sync (it's fast) OR
- Convert to async and update all callers

**Decision:** Keep sync - volume_get is fast (<100ms) and only called during recreation checks.

#### 3.7 `src/backend/services/monitoring_service.py`

**Blocking calls:**
- Line 77: `docker_client.containers.get(...)`

**Note:** Monitoring service runs in background task. Review if wrapping needed based on performance.

---

## Integration Points to Preserve

### 1. WebSocket Broadcasts

After lifecycle operations, WebSocket events MUST still be broadcast:
```python
# agents.py - after start/stop/delete
if manager:
    await manager.broadcast(json.dumps(event))
if filtered_manager:
    await filtered_manager.broadcast_filtered(event)
```

### 2. Trinity Injection Flow

After container start, injection sequence MUST remain intact:
```python
await container_start(container)
trinity_result = await inject_trinity_meta_prompt(agent_name)
credentials_result = await inject_assigned_credentials(agent_name)
subscription_result = await inject_subscription_on_start(agent_name)
skills_result = await inject_assigned_skills(agent_name)
read_only_result = await inject_read_only_hooks(agent_name, config)
```

### 3. Error Handling

All Docker operations MUST preserve existing error handling:
```python
try:
    await container_stop(old_container)
except Exception:
    pass  # Container might already be stopped
await container_remove(old_container)
```

### 4. Activity Tracking

Activity events MUST still be tracked through the activity service after operations.

### 5. Database Operations

Database operations (ownership, schedules, permissions, etc.) MUST NOT be affected.

---

## Testing Requirements

### Unit Tests

Create `tests/test_docker_utils.py`:
```python
import pytest
import asyncio
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_container_stop_non_blocking():
    """Verify container_stop doesn't block event loop."""
    # Setup mock container
    # Call container_stop
    # Assert it completes without blocking other coroutines

@pytest.mark.asyncio
async def test_concurrent_operations():
    """Verify multiple Docker operations can run concurrently."""
    # Start multiple container operations
    # Assert they overlap in execution (not sequential)
```

### Integration Tests

1. **Reproduction Test**: Trigger container recreation while polling `/api/telemetry/host`
   - Before fix: Telemetry requests timeout
   - After fix: Telemetry requests succeed during recreation

2. **Concurrent Operations**: Start 3 agents simultaneously
   - Before fix: Operations block each other
   - After fix: Operations run in parallel

3. **WebSocket Stability**: Monitor WebSocket during lifecycle operations
   - Before fix: Connections drop
   - After fix: Connections remain stable

### Manual Testing Checklist

- [ ] Create agent - completes without blocking
- [ ] Start agent - UI remains responsive
- [ ] Stop agent - UI remains responsive
- [ ] Delete agent - UI remains responsive
- [ ] Container recreation (API key toggle) - no 499 errors
- [ ] Shared folder config change - no blocking
- [ ] Bulk operations (restart all) - parallel execution

---

## Performance Expectations

| Operation | Before (blocking) | After (async) |
|-----------|-------------------|---------------|
| Container recreation | 10-25s event loop block | 0s block |
| Agent start | 2-5s event loop block | 0s block |
| Agent stop | 1-5s event loop block | 0s block |
| Agent delete | 3-8s event loop block | 0s block |
| Concurrent requests | Queued/timeout | Processed normally |

---

## Implementation Order

### Phase 1: Core Infrastructure (Estimated: 30 min)
1. Create `src/backend/services/docker_utils.py`
2. Add unit tests for docker_utils

### Phase 2: Critical Path (Estimated: 1 hour)
1. Update `lifecycle.py` (primary offender)
2. Update `routers/agents.py` (delete/stop endpoints)
3. Test agent lifecycle operations

### Phase 3: Agent Services (Estimated: 45 min)
1. Update `crud.py`
2. Update `files.py`, `folders.py`, `stats.py`
3. Update `dashboard.py`, `api_key.py`, `terminal.py`, `metrics.py`

### Phase 4: System Services (Estimated: 30 min)
1. Update `system_agent_service.py`
2. Update `routers/ops.py`, `routers/system_agent.py`
3. Update `deploy.py`, `systems.py`

### Phase 5: Verification (Estimated: 30 min)
1. Run full test suite
2. Manual integration testing
3. Performance verification

---

## Rollback Plan

If issues are discovered:
1. Revert `docker_utils.py` import statements
2. All original Docker SDK calls remain functional
3. No database schema changes required

---

## Success Criteria

1. **No Event Loop Blocking**: `/api/telemetry/host` responds within 500ms even during container recreation
2. **No 499 Errors**: Frontend never receives HTTP 499 during lifecycle operations
3. **WebSocket Stability**: No connection drops during Docker operations
4. **Concurrent Operations**: Multiple lifecycle operations can run in parallel
5. **All Tests Pass**: Existing test suite passes with no regressions

---

## References

- **Correct Pattern**: `src/backend/routers/telemetry.py` (lines 18-147)
- **GitHub Issue**: [#42](https://github.com/abilityai/trinity/issues/42)
- **Python Docs**: [asyncio.loop.run_in_executor](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor)
- **Docker SDK**: [docker-py documentation](https://docker-py.readthedocs.io/)
