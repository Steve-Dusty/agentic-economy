# Implementation Plan: Docker Stats Optimization

> **Priority**: CRITICAL
> **Estimated Impact**: 15-25 seconds → <1 second for `/api/agents`
> **Dependencies**: None
> **Related Issue**: Sequential Docker stats fetching

---

## Problem Summary

The `/api/agents` endpoint fetches live Docker stats for each agent **sequentially**. Docker's `container.stats(stream=False)` call takes ~2-2.5 seconds per container due to CPU sampling requirements. With 7+ agents, this causes 15-25 second response times.

**Current Flow**:
```
GET /api/agents
  → get_accessible_agents()
    → list_all_agents() [calls docker API for each container]
    → For each agent: db queries + Docker stats
  → Return 15-25 seconds later
```

---

## Chosen Solution: Lazy Stats Loading (Option A)

Remove stats from the agent list endpoint. Fetch stats on-demand via a separate endpoint.

**Why this approach**:
- Simplest implementation
- No background threads or caching complexity
- Frontend already has `useAgentStats` composable for per-agent stats
- Stats aren't needed on the agent list page (only on agent detail)

---

## Implementation Steps

### Step 1: Verify Current Behavior

**File**: `src/backend/services/docker_service.py`

Check what `list_all_agents()` currently returns. Look for any stats fetching in the agent list flow.

```bash
grep -n "stats" src/backend/services/docker_service.py
```

**Expected finding**: The slow path is likely in how we populate agent data with live container stats.

---

### Step 2: Create Lightweight Agent List Function

**File**: `src/backend/services/docker_service.py`

Add a fast version that only returns container metadata without stats:

```python
def list_all_agents_fast() -> List[AgentStatus]:
    """
    List all Trinity agent containers WITHOUT fetching live stats.
    Returns container state from Docker labels only - no stats() calls.

    This is 10-100x faster than list_all_agents() because it doesn't
    block on Docker's stats API (~2s per container).
    """
    agents = []
    try:
        containers = docker_client.containers.list(
            all=True,
            filters={"label": "trinity.platform=agent"}
        )
        for container in containers:
            labels = container.labels
            # Extract basic info from labels only - no stats() call
            agent = AgentStatus(
                name=labels.get("trinity.agent-name", container.name.replace("agent-", "")),
                status=container.status,
                type=labels.get("trinity.agent-type", "unknown"),
                # No cpu_percent, memory_used, etc. - these require stats()
                created_at=container.attrs.get("Created", ""),
                ssh_port=int(labels.get("trinity.ssh-port", 0)) or None,
                base_image_version=labels.get("trinity.base-image-version"),
            )
            agents.append(agent)
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
    return agents
```

---

### Step 3: Update get_accessible_agents() to Use Fast Version

**File**: `src/backend/services/agent_service/helpers.py`

```python
# Change this import:
from services.docker_service import list_all_agents

# To:
from services.docker_service import list_all_agents_fast

# Update the function:
def get_accessible_agents(current_user: User) -> list:
    """Get list of all agents accessible to the current user."""
    # Use fast version - no Docker stats fetching
    all_agents = list_all_agents_fast()  # Changed from list_all_agents()

    # ... rest of function unchanged
```

---

### Step 4: Ensure Stats Endpoint Exists

**File**: `src/backend/routers/agents.py`

Verify the existing `/api/agents/{name}/stats` endpoint works correctly:

```python
@router.get("/{agent_name}/stats")
async def get_agent_stats_endpoint(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get live container stats (CPU, memory, network) for an agent."""
    return await get_agent_stats_logic(agent_name, current_user)
```

**Status**: This endpoint already exists at `src/backend/services/agent_service/stats.py:123`

---

### Step 5: Frontend Verification

**File**: `src/frontend/src/composables/useAgentStats.js`

The frontend already fetches stats separately via `useAgentStats`:

```javascript
// This composable already handles per-agent stats polling
const loadStats = async () => {
    if (!agentRef.value || agentRef.value.status !== 'running') return
    const stats = await agentsStore.getAgentStats(agentRef.value.name)
    // ...
}
```

No frontend changes needed - stats are already fetched lazily.

---

## Files to Modify

| File | Change |
|------|--------|
| `src/backend/services/docker_service.py` | Add `list_all_agents_fast()` function |
| `src/backend/services/agent_service/helpers.py` | Use `list_all_agents_fast()` instead of `list_all_agents()` |

---

## Testing Plan

### Before Implementation

```bash
# Measure current response time
time curl -s http://localhost:8000/api/agents \
  -H "Authorization: Bearer $TOKEN" > /dev/null
# Expected: 15-25 seconds with 7+ running agents
```

### After Implementation

```bash
# Measure new response time
time curl -s http://localhost:8000/api/agents \
  -H "Authorization: Bearer $TOKEN" > /dev/null
# Expected: <1 second

# Verify stats still work for individual agents
curl http://localhost:8000/api/agents/test-agent/stats \
  -H "Authorization: Bearer $TOKEN"
# Expected: Returns CPU, memory, network stats
```

### UI Verification

1. Open http://localhost → Agent list loads quickly
2. Click into an agent → Stats panel shows CPU/memory after ~1 second
3. Sparkline charts update every 5 seconds

---

## Rollback Plan

If issues arise, revert `helpers.py` to use `list_all_agents()`:

```python
# Rollback: change back to original
all_agents = list_all_agents()  # Full stats, slower
```

---

## Alternative: Background Cache (Option C)

If lazy loading causes UX issues (e.g., users want to see stats on list page), implement a background cache:

```python
# src/backend/services/agent_service/stats_cache.py

import threading
from time import time, sleep
from typing import Dict

_stats_cache: Dict[str, dict] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 10  # seconds

def get_cached_stats(agent_name: str) -> dict:
    """Get stats from cache. Never blocks on Docker API."""
    with _cache_lock:
        entry = _stats_cache.get(agent_name, {})
        return entry.get("stats", {})

def _refresh_all_stats():
    """Background thread that refreshes stats for all running agents."""
    while True:
        try:
            from services.docker_service import docker_client
            containers = docker_client.containers.list(
                filters={"label": "trinity.platform=agent", "status": "running"}
            )
            for container in containers:
                try:
                    stats = container.stats(stream=False)
                    agent_name = container.labels.get("trinity.agent-name", "")
                    with _cache_lock:
                        _stats_cache[agent_name] = {
                            "stats": _parse_stats(stats),
                            "updated_at": time()
                        }
                except Exception:
                    pass
        except Exception:
            pass
        sleep(_CACHE_TTL)

# Start background thread on module import
_refresh_thread = threading.Thread(target=_refresh_all_stats, daemon=True)
_refresh_thread.start()
```

This is only needed if users require stats on the agent list page.

---

## Notes

- Docker's stats API latency is unavoidable (~2s per container)
- The only solutions are: don't fetch stats, parallelize, or cache
- Lazy loading is the cleanest approach for our use case
- Background caching adds complexity but enables stats on list page

---

## Completion Checklist

- [x] Add `list_all_agents_fast()` to docker_service.py (2026-01-12)
- [x] Update helpers.py to use fast version (2026-01-12)
- [x] Test response time improvement (37ms with 4 agents)
- [x] Verify stats endpoint still works (~1s per agent)
- [ ] Verify frontend stats panel still works (needs manual UI test)
- [x] Update changelog.md (2026-01-12)
