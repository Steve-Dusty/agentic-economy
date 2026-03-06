# UI Freeze Fix Implementation Plan

> **Issue**: Intermittent UI freezes where tabs become unresponsive
> **Root Cause**: Multiple interacting bugs causing resource accumulation
> **Created**: 2026-01-02

---

## Executive Summary

Browser investigation confirmed multiple issues that compound to cause UI freezes:

1. **WebSocket reconnection loop** - Orphan connections persist after navigation
2. **Slow blocking API calls** - `/api/telemetry/containers` blocks on Docker stats
3. **No request cancellation** - In-flight requests continue after unmount
4. **Duplicate polling systems** - Both `network.js` and `agents.js` poll same endpoints

---

## Issue 1: WebSocket Reconnection Loop (Critical)

### Problem

In `src/frontend/src/stores/network.js:356-366`:

```javascript
websocket.value.onclose = () => {
  console.log('[Collaboration] WebSocket disconnected')
  isConnected.value = false

  // BUG: Always attempts reconnect, even after intentional disconnect
  setTimeout(() => {
    if (!isConnected.value) {
      console.log('[Collaboration] Attempting to reconnect...')
      connectWebSocket()
    }
  }, 5000)
}
```

When `disconnectWebSocket()` is called:
1. It calls `websocket.close()` which triggers `onclose`
2. `isConnected` is set to `false`
3. 5 seconds later, reconnection fires even though disconnect was intentional
4. Orphan WebSocket connects and processes messages on wrong pages

### Solution

Add an `intentionalDisconnect` flag:

```javascript
// Add new ref
const intentionalDisconnect = ref(false)

function connectWebSocket() {
  // Reset flag when intentionally connecting
  intentionalDisconnect.value = false

  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`

  // Prevent duplicate connections
  if (websocket.value?.readyState === WebSocket.OPEN) {
    console.log('[Collaboration] WebSocket already connected')
    return
  }

  try {
    websocket.value = new WebSocket(wsUrl)

    websocket.value.onopen = () => {
      console.log('[Collaboration] WebSocket connected')
      isConnected.value = true
    }

    // ... onmessage, onerror handlers unchanged ...

    websocket.value.onclose = () => {
      console.log('[Collaboration] WebSocket disconnected')
      isConnected.value = false

      // Only reconnect if this was NOT an intentional disconnect
      if (!intentionalDisconnect.value) {
        setTimeout(() => {
          if (!isConnected.value && !intentionalDisconnect.value) {
            console.log('[Collaboration] Attempting to reconnect...')
            connectWebSocket()
          }
        }, 5000)
      }
    }
  } catch (error) {
    console.error('[Collaboration] Failed to connect WebSocket:', error)
  }
}

function disconnectWebSocket() {
  // Set flag BEFORE closing to prevent reconnection
  intentionalDisconnect.value = true

  if (websocket.value) {
    websocket.value.close()
    websocket.value = null
    isConnected.value = false
  }
}
```

### Files to Modify
- `src/frontend/src/stores/network.js`

---

## Issue 2: Slow Container Stats API (High Priority)

### Problem

In `src/backend/routers/telemetry.py:83-89`:

```python
for agent in running_agents:
    # This blocks for ~1-2 seconds PER container
    stats = container.stats(stream=False)
```

With multiple containers, this can take 5-10+ seconds, causing:
- Request pile-up (new polls fire before old ones complete)
- Browser connection limits exhausted
- Pending promises accumulate

### Solution

Option A: **Parallelize with asyncio** (Recommended)

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Module-level executor for Docker operations
_executor = ThreadPoolExecutor(max_workers=4)

async def get_container_stats_async(container):
    """Get container stats in thread pool to avoid blocking."""
    loop = asyncio.get_event_loop()
    try:
        stats = await loop.run_in_executor(
            _executor,
            lambda: container.stats(stream=False)
        )
        return stats
    except Exception as e:
        return None

@router.get("/containers")
async def get_container_stats():
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker not available")

    try:
        agents = list_all_agents()
        running_agents = [a for a in agents if a.status == "running"]

        # Fetch all container stats in parallel
        containers = []
        for agent in running_agents:
            try:
                containers.append(docker_client.containers.get(f"agent-{agent.name}"))
            except:
                pass

        # Run all stats calls concurrently
        stats_results = await asyncio.gather(
            *[get_container_stats_async(c) for c in containers],
            return_exceptions=True
        )

        # Process results...
```

Option B: **Cache with short TTL** (Simpler)

```python
from functools import lru_cache
from time import time

_stats_cache = {}
_cache_ttl = 3  # seconds

@router.get("/containers")
async def get_container_stats():
    global _stats_cache

    now = time()
    if _stats_cache.get('timestamp', 0) > now - _cache_ttl:
        return _stats_cache['data']

    # ... fetch stats ...

    _stats_cache = {'timestamp': now, 'data': result}
    return result
```

### Files to Modify
- `src/backend/routers/telemetry.py`

---

## Issue 3: No Request Cancellation on Unmount (Medium Priority)

### Problem

When navigating away from Dashboard:
1. `onUnmounted` clears intervals
2. But in-flight HTTP requests continue
3. Their callbacks may run after component is gone
4. Can cause state updates on unmounted components

### Solution

Use AbortController for all polling requests:

```javascript
// In network.js store
const abortController = ref(null)

function startContextPolling() {
  if (contextPollingInterval.value) {
    clearInterval(contextPollingInterval.value)
  }

  // Create new AbortController for this polling session
  abortController.value = new AbortController()

  const fetchWithAbort = async () => {
    try {
      const response = await axios.get('/api/agents/context-stats', {
        signal: abortController.value?.signal
      })
      // ... process response
    } catch (error) {
      if (error.name === 'CanceledError' || error.name === 'AbortError') {
        // Ignore cancelled requests
        return
      }
      console.error('Failed to fetch context stats:', error)
    }
  }

  fetchWithAbort()
  contextPollingInterval.value = setInterval(fetchWithAbort, 5000)
}

function stopContextPolling() {
  // Abort any in-flight requests
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }

  if (contextPollingInterval.value) {
    clearInterval(contextPollingInterval.value)
    contextPollingInterval.value = null
  }
}
```

### Files to Modify
- `src/frontend/src/stores/network.js`
- `src/frontend/src/stores/agents.js`
- `src/frontend/src/components/HostTelemetry.vue` (already has timeout, add full abort)

---

## Issue 4: Duplicate WebSocket Systems (Low Priority)

### Problem

Two separate WebSocket connections to `/ws`:
1. `src/frontend/src/utils/websocket.js` - Global, connects in App.vue
2. `src/frontend/src/stores/network.js` - Per-Dashboard, connects on mount

Both listen to same events, potentially causing duplicate state updates.

### Solution

Consolidate to single WebSocket in network store (or utils), used globally:

Option A: **Remove utils/websocket.js, use network store globally**

```javascript
// In App.vue
onMounted(async () => {
  if (token) {
    // Use network store's WebSocket instead
    const networkStore = useNetworkStore()
    networkStore.connectWebSocket()
  }
})
```

Option B: **Keep both but deduplicate event handling**

Add event deduplication based on timestamp/ID to prevent double-processing.

### Files to Modify
- `src/frontend/src/App.vue`
- `src/frontend/src/utils/websocket.js`
- `src/frontend/src/stores/network.js`

---

## Issue 5: Vue Readonly Warning (Low Priority)

### Problem

```
[Vue warn] Set operation on key "edges" failed: target is readonly
```

The `edges` computed property in network.js is being mutated somewhere.

### Solution

Audit code for direct mutations of `edges` computed property. Ensure all edge modifications go through `collaborationEdges` or `permissionEdges` refs.

### Files to Audit
- `src/frontend/src/stores/network.js`
- `src/frontend/src/views/Dashboard.vue`
- VueFlow event handlers

---

## Implementation Order

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 1 | WebSocket reconnection loop | Low | High |
| 2 | Slow container stats API | Medium | High |
| 3 | Request cancellation | Medium | Medium |
| 4 | Duplicate WebSocket | Low | Low |
| 5 | Vue readonly warning | Low | Low |

### Phase 1: Quick Wins (1-2 hours)
- [x] Fix WebSocket intentional disconnect flag ✅ (2026-01-02)
- [ ] Add AbortController to polling functions

### Phase 2: Backend Optimization (2-3 hours)
- [x] Parallelize container stats with asyncio ✅ (2026-01-02)
- [ ] Add short TTL cache as fallback

### Phase 3: Cleanup (1 hour)
- [ ] Consolidate WebSocket systems
- [ ] Fix Vue readonly warning

---

## Testing Plan

### Manual Testing
1. Navigate Dashboard → Agents → Dashboard repeatedly
2. Check console for "Attempting to reconnect..." (should NOT appear after navigation)
3. Monitor Network tab for request pile-up
4. Verify no orphan WebSocket connections

### Automated Testing
```javascript
// Cypress test
it('should not reconnect WebSocket after intentional disconnect', () => {
  cy.visit('/');
  cy.wait(1000);
  cy.visit('/agents');
  cy.wait(6000); // Wait past reconnection timeout
  cy.window().then(win => {
    // Check console for reconnection attempts
    expect(win.console.logs).not.to.include('[Collaboration] Attempting to reconnect...');
  });
});
```

---

## Success Metrics

- [ ] No "Attempting to reconnect..." after navigation away from Dashboard
- [ ] `/api/telemetry/containers` responds in <1 second
- [ ] No pending requests visible after page navigation
- [ ] UI remains responsive during extended use
- [ ] Memory usage stable over time (no leaks)
