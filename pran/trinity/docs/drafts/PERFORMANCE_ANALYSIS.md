# Performance Analysis Report

> **Date**: 2026-01-12
> **Issue**: `/api/agents` endpoint taking 15-25 seconds, overall system slowness
> **Status**: Analysis complete, implementation pending

---

## Executive Summary

The Trinity platform experiences severe performance degradation in production due to:
1. **Sequential Docker stats fetching** - ~2-2.5 seconds latency per container
2. **N+1 database query problem** - 120-180+ queries per agent list request
3. **Aggressive frontend polling** - 50+ API requests per minute per open agent page
4. **Blocking Docker API calls** - Synchronous stats collection on individual endpoints

---

## Issue 0: Sequential Docker Stats in Agent List (CRITICAL)

### The Problem

The `/api/agents` endpoint takes **15-25 seconds** to respond because it fetches live Docker stats for each agent **sequentially**. The `docker stats` command has inherent latency (~2-2.5 seconds per container even with `--no-stream`), so with 7 agents running, the endpoint blocks for 15+ seconds before returning.

### Impact

- UI feels broken when loading agent lists
- Any tab that calls `/api/agents` is affected
- Scales linearly with number of agents (N agents × 2.5s = response time)

### Root Cause

Docker's stats API is inherently slow - it needs to sample CPU/memory over a time window to calculate percentages. Even with `stream=False`, each call takes 1-2+ seconds.

### Recommended Fixes

**Option A: Remove stats from list endpoint (SIMPLEST)**
- Don't include stats in the `/api/agents` response
- Fetch stats separately via `/api/agents/{name}/stats` only when explicitly requested
- Frontend fetches stats lazily when user clicks into an agent

**Option B: Parallelize stats collection**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def get_all_agent_stats_parallel(agents):
    """Fetch stats for all agents concurrently."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=10) as executor:
        tasks = [
            loop.run_in_executor(executor, lambda a=agent: get_container_stats(a))
            for agent in agents
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

**Option C: Background cache with periodic refresh**
```python
import threading
from time import time

_stats_cache = {}
_cache_lock = threading.Lock()
_cache_refresh_interval = 10  # seconds

def get_cached_stats(agent_name: str) -> dict:
    """Get stats from cache, never block on Docker API."""
    with _cache_lock:
        cached = _stats_cache.get(agent_name, {})
        return cached.get("stats", {})

def _refresh_stats_background():
    """Background thread that refreshes all agent stats periodically."""
    while True:
        agents = list_all_agents()
        for agent in agents:
            if agent.status == "running":
                try:
                    stats = get_container_stats_sync(agent.name)
                    with _cache_lock:
                        _stats_cache[agent.name] = {
                            "stats": stats,
                            "updated_at": time()
                        }
                except Exception:
                    pass
        time.sleep(_cache_refresh_interval)

# Start background thread on module load
threading.Thread(target=_refresh_stats_background, daemon=True).start()
```

**Expected Impact**: 15-25 seconds → <1 second

---

## Issue 1: N+1 Query Problem (CRITICAL)

### Location
`src/backend/services/agent_service/helpers.py:82-126`

### Problem
The `get_accessible_agents()` function makes **6-9 separate database queries per agent**:

```python
def get_accessible_agents(current_user: User) -> list:
    all_agents = list_all_agents()  # Docker API call
    user_data = db.get_user_by_username(current_user.username)  # 1 query

    for agent in all_agents:  # N iterations
        db.can_user_access_agent(...)      # 2-3 queries (user, owner, sharing)
        db.get_agent_owner(agent_name)     # 1 query
        db.is_agent_shared_with_user(...)  # 2 queries
        db.get_autonomy_enabled(...)       # 1 query
        db.get_git_config(...)             # 1 query
        db.get_resource_limits(...)        # 1 query
```

### Impact
- **20 agents = 120-180 database queries** per `/api/agents` request
- Each query opens a new SQLite connection via `get_db_connection()`
- Response time: **15+ seconds** in production

### Database Query Breakdown Per Agent

| Function | Queries | Notes |
|----------|---------|-------|
| `can_user_access_agent()` | 2-3 | Calls `get_user_by_username()`, `get_agent_owner()`, `is_agent_shared_with_user()` |
| `get_agent_owner()` | 1 | JOIN query with users table |
| `is_agent_shared_with_user()` | 2 | Calls `get_user_by_username()` + sharing check |
| `get_autonomy_enabled()` | 1 | Simple SELECT |
| `get_git_config()` | 1 | Simple SELECT |
| `get_resource_limits()` | 1 | Simple SELECT |

**Total per agent: 8-10 queries**

---

## Issue 2: Aggressive Frontend Polling (HIGH)

### Location
`src/frontend/src/composables/*.js`

### Problem
Multiple concurrent polling loops run from a single `AgentDetail.vue` page:

| File | Interval | Purpose | Requests/min |
|------|----------|---------|--------------|
| `useSessionActivity.js:117` | **2 seconds** | Activity status | 30 |
| `useAgentStats.js:59` | 5 seconds | CPU/memory stats | 12 |
| `useAgentLogs.js:45` | 10 seconds | Container logs | 6 |
| `useGitSync.js:164` | 30 seconds | Git status | 2 |

### Impact
- **~50 API requests per minute** per open agent detail page
- Multiple users/tabs multiply this load
- Backend overwhelmed with concurrent requests

### Polling Code References

```javascript
// useSessionActivity.js:117
activityRefreshInterval = setInterval(loadSessionActivity, 2000) // Every 2 seconds

// useAgentStats.js:59
statsRefreshInterval = setInterval(loadStats, 5000) // Every 5 seconds

// useAgentLogs.js:45
logsRefreshInterval = setInterval(refreshLogs, 10000) // Every 10 seconds

// useGitSync.js:164
gitStatusInterval = setInterval(loadGitStatus, 30000) // Every 30 seconds
```

---

## Issue 3: Blocking Docker API Calls (MEDIUM)

### Location
`src/backend/services/agent_service/stats.py:139`

### Problem
```python
stats = container.stats(stream=False)  # Blocking call, 1-2 seconds
```

The `container.stats(stream=False)` call is synchronous and can take 1-2 seconds per container.

### Impact
- Stats endpoint blocks the event loop
- With 20 agents polling stats every 5 seconds, this creates significant load
- Contributes to overall slowness

---

## Issue 4: No Database Connection Pooling (LOW)

### Location
`src/backend/db/connection.py`

### Problem
Each database query creates a new connection:
```python
with get_db_connection() as conn:
    # query
# connection closed
```

### Impact
- **125 occurrences** of `get_db_connection()` across 12 files
- Connection overhead adds up with high query volume
- SQLite handles this reasonably well, but still suboptimal

---

## Recommended Fixes

### Fix 1: Batch Database Queries (HIGH PRIORITY)

**Goal**: Reduce 120+ queries to 3-4 queries total

**Implementation**:

1. Create a new function `get_all_agent_metadata()` in `db/agents.py`:

```python
def get_all_agent_metadata(user_email: str) -> Dict[str, Dict]:
    """
    Get all agent metadata in a single query.
    Returns dict keyed by agent_name with ownership, sharing, autonomy, git, resources.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                ao.agent_name,
                ao.owner_id,
                u.username as owner_username,
                u.email as owner_email,
                COALESCE(ao.autonomy_enabled, 0) as autonomy_enabled,
                COALESCE(ao.is_system, 0) as is_system,
                ao.memory_limit,
                ao.cpu_limit,
                gc.github_repo,
                CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END as is_shared_with_user
            FROM agent_ownership ao
            LEFT JOIN users u ON ao.owner_id = u.id
            LEFT JOIN git_configs gc ON gc.agent_name = ao.agent_name
            LEFT JOIN agent_sharing s ON s.agent_name = ao.agent_name
                AND s.shared_with_email = ?
        """, (user_email.lower() if user_email else '',))

        return {row["agent_name"]: dict(row) for row in cursor.fetchall()}
```

2. Update `get_accessible_agents()` to use batch query:

```python
def get_accessible_agents(current_user: User) -> list:
    all_agents = list_all_agents()  # Still need Docker call
    user_data = db.get_user_by_username(current_user.username)
    is_admin = user_data and user_data["role"] == "admin"
    user_email = user_data.get("email") if user_data else None

    # Single batch query for all metadata
    all_metadata = db.get_all_agent_metadata(user_email)

    accessible_agents = []
    for agent in all_agents:
        agent_dict = agent.dict()
        agent_name = agent_dict.get("name")
        metadata = all_metadata.get(agent_name, {})

        # Access check using cached metadata
        owner_username = metadata.get("owner_username")
        is_owner = owner_username == current_user.username
        is_shared = bool(metadata.get("is_shared_with_user"))

        if not (is_admin or is_owner or is_shared):
            continue

        # Populate from cached metadata
        agent_dict["owner"] = owner_username
        agent_dict["is_owner"] = is_owner
        agent_dict["is_shared"] = is_shared and not is_owner and not is_admin
        agent_dict["is_system"] = bool(metadata.get("is_system"))
        agent_dict["autonomy_enabled"] = bool(metadata.get("autonomy_enabled"))
        agent_dict["github_repo"] = metadata.get("github_repo")
        agent_dict["memory_limit"] = metadata.get("memory_limit")
        agent_dict["cpu_limit"] = metadata.get("cpu_limit")

        accessible_agents.append(agent_dict)

    return accessible_agents
```

**Expected Impact**: 120+ queries → 2 queries (user lookup + batch metadata)

---

### Fix 2: Add Response Caching (MEDIUM PRIORITY)

**Goal**: Cache frequently-accessed data to reduce redundant queries

**Implementation Options**:

#### Option A: Simple In-Memory Cache with TTL

```python
from functools import lru_cache
from time import time

_agent_cache = {}
_cache_ttl = 5  # seconds

def get_accessible_agents_cached(current_user: User) -> list:
    cache_key = f"{current_user.username}:{int(time() / _cache_ttl)}"
    if cache_key in _agent_cache:
        return _agent_cache[cache_key]

    result = get_accessible_agents(current_user)
    _agent_cache[cache_key] = result

    # Cleanup old entries
    current_bucket = int(time() / _cache_ttl)
    _agent_cache = {k: v for k, v in _agent_cache.items()
                    if int(k.split(':')[1]) >= current_bucket - 1}

    return result
```

#### Option B: Redis Cache (if already using Redis)

```python
import json
from credentials import get_redis_client

def get_accessible_agents_cached(current_user: User) -> list:
    redis = get_redis_client()
    cache_key = f"agents:{current_user.username}"

    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = get_accessible_agents(current_user)
    redis.setex(cache_key, 5, json.dumps(result))  # 5 second TTL
    return result
```

---

### Fix 3: Reduce Polling Frequency (MEDIUM PRIORITY)

**Goal**: Reduce API request volume by 50%+

**Implementation**:

| Composable | Current | Recommended | Change |
|------------|---------|-------------|--------|
| `useSessionActivity.js` | 2s | 5s | -60% requests |
| `useAgentStats.js` | 5s | 10s | -50% requests |
| `useAgentLogs.js` | 10s | 15s | -33% requests |
| `useGitSync.js` | 30s | 60s | -50% requests |

**Code Changes**:

```javascript
// useSessionActivity.js:117
activityRefreshInterval = setInterval(loadSessionActivity, 5000) // Was 2000

// useAgentStats.js:59
statsRefreshInterval = setInterval(loadStats, 10000) // Was 5000

// useAgentLogs.js:45
logsRefreshInterval = setInterval(refreshLogs, 15000) // Was 10000

// useGitSync.js:164
gitStatusInterval = setInterval(loadGitStatus, 60000) // Was 30000
```

**Expected Impact**: ~50 req/min → ~20 req/min per agent page

---

### Fix 4: WebSocket Push Notifications (LOW PRIORITY - FUTURE)

**Goal**: Replace polling with event-driven updates

**Implementation**:

1. Backend broadcasts state changes via existing WebSocket:
```python
# When agent state changes
await manager.broadcast(json.dumps({
    "event": "agent_stats_update",
    "data": {"name": agent_name, "cpu": cpu, "memory": memory}
}))
```

2. Frontend listens instead of polling:
```javascript
// Instead of setInterval, listen to WebSocket
websocket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.event === 'agent_stats_update' && data.data.name === agentName) {
        updateStats(data.data)
    }
}
```

**Expected Impact**: Eliminates most polling, real-time updates

---

### Fix 5: Async Docker Stats (LOW PRIORITY)

**Goal**: Non-blocking stats collection

**Implementation**:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=4)

async def get_agent_stats_async(container):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, lambda: container.stats(stream=False))
```

---

## Implementation Priority

| Fix | Priority | Effort | Impact | Dependencies |
|-----|----------|--------|--------|--------------|
| Fix 0: Remove/Cache Docker Stats | **CRITICAL** | Low | Very High | None |
| Fix 1: Batch Queries | HIGH | Medium | Very High | None |
| Fix 2: Response Caching | MEDIUM | Low | Medium | Fix 1 |
| Fix 3: Reduce Polling | MEDIUM | Low | Medium | None |
| Fix 4: WebSocket Push | LOW | High | High | Existing WebSocket |
| Fix 5: Async Docker | LOW | Medium | Low | None |

**Recommended order**: Fix 0 → Fix 1 → Fix 3 → Fix 2 → Fix 4

---

## Verification Plan

After implementing fixes:

1. **Measure `/api/agents` response time**
   ```bash
   time curl -s http://localhost:8000/api/agents -H "Authorization: Bearer $TOKEN" > /dev/null
   ```
   - Before: **15-25 seconds** (with Docker stats)
   - After Fix 0: <2 seconds (Docker stats removed/cached)
   - After Fix 1: **<500ms** (batch queries)

2. **Monitor database queries**
   - Enable SQLite query logging
   - Count queries per request
   - Before: 120-180 queries
   - Target: 2-4 queries

3. **Monitor network requests**
   - Browser DevTools → Network tab
   - Before: ~50 requests/min
   - Target: ~20 requests/min

4. **Load test with multiple agents**
   - Create 30+ agents
   - Open multiple agent detail pages
   - Verify system remains responsive

---

## Related Files

### Backend
- `src/backend/services/agent_service/helpers.py` - `get_accessible_agents()`
- `src/backend/services/agent_service/stats.py` - Docker stats
- `src/backend/db/agents.py` - Agent database operations
- `src/backend/db/connection.py` - Database connection

### Frontend
- `src/frontend/src/views/AgentDetail.vue` - Main agent page
- `src/frontend/src/composables/useAgentStats.js` - Stats polling
- `src/frontend/src/composables/useSessionActivity.js` - Activity polling
- `src/frontend/src/composables/useAgentLogs.js` - Logs polling
- `src/frontend/src/composables/useGitSync.js` - Git status polling

---

## Notes

- SQLite is single-writer, so connection pooling has limited benefit
- Redis is already used for credentials - can leverage for caching
- WebSocket infrastructure exists - can extend for push notifications
- Docker stats streaming mode could be used for real-time updates
