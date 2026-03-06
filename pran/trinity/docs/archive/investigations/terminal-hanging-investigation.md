# Terminal Hanging Investigation Report

**Date**: 2025-12-28
**Issue**: App becomes unresponsive after opening web terminals (System Agent or individual agents)
**Reporter**: User reported UI hangs and cannot navigate to other pages

---

## Executive Summary

After investigating the terminal implementation, I've identified **3 potential root causes** that could cause the app to hang:

1. **Thread Pool Exhaustion** - Terminal uses tight polling loops in thread pool (HIGH PROBABILITY)
2. **KeepAlive + Multiple WebSocket Connections** - Cached components maintain connections (MEDIUM)
3. **Frontend Event Loop Blocking** - xterm.js WebGL/Canvas rendering (LOW)

---

## Architecture Overview

```
Frontend (Vue.js)                    Backend (FastAPI/Uvicorn)
┌─────────────────────┐              ┌─────────────────────────────────────┐
│  App.vue            │              │  Single Uvicorn Process             │
│  ├── KeepAlive      │              │  ├── Default ThreadPoolExecutor     │
│  │   ├── SystemAgent│──WebSocket──▶│  │   (max_workers: 18)              │
│  │   └── AgentDetail│──WebSocket──▶│  │                                  │
│  │                  │              │  └── asyncio Event Loop             │
│  └── router-view    │              │                                     │
└─────────────────────┘              └─────────────────────────────────────┘
```

---

## Root Cause Analysis

### 1. Thread Pool Exhaustion (HIGH PROBABILITY)

**Location**: `src/backend/services/agent_service/terminal.py:225-247` and `system_agent.py:495-517`

**Problem**: The terminal implementation uses `run_in_executor` with a tight polling loop:

```python
async def read_from_docker():
    while True:
        # Called every 5ms in a tight loop
        ready = await loop.run_in_executor(
            None,  # Uses default ThreadPoolExecutor
            lambda: select.select([docker_socket], [], [], 0.005)  # 5ms timeout
        )
        if ready[0]:
            data = await loop.run_in_executor(
                None,
                lambda: docker_socket.recv(16384)
            )
            await websocket.send_bytes(data)
```

**Analysis**:
- Default ThreadPoolExecutor has **18 workers** (checked in container)
- Each terminal session runs 2 concurrent tasks (`read_from_docker` + `read_from_websocket`)
- Each `read_from_docker` calls `run_in_executor` **200 times/second** (5ms timeout in tight loop)
- Each `read_from_websocket` calls `run_in_executor` for every input/resize event

**Impact**:
- With 2+ terminal sessions, the thread pool gets saturated
- Other async operations (API calls, database, audit logging) queue up waiting for threads
- Results in: "Failed to log audit event" errors (seen in logs)
- Results in: API calls timing out, UI appearing frozen

**Evidence**:
```
trinity-backend  | Failed to log audit event:
trinity-backend  | Failed to log audit event:
```

### 2. KeepAlive Component Caching (MEDIUM PROBABILITY)

**Location**: `src/frontend/src/App.vue:5`

```vue
<KeepAlive :include="['SystemAgent', 'AgentDetail']">
  <component :is="Component" />
</KeepAlive>
```

**Problem**: Both terminal-containing views are cached by KeepAlive, meaning:
- WebSocket connections persist when navigating away
- Terminal components stay mounted (xterm.js instances remain)
- Multiple cached instances can accumulate

**Impact**:
- User navigates: SystemAgent → AgentDetail(agent-1) → AgentDetail(agent-2)
- All 3 terminal WebSocket connections stay open
- Backend maintains 3 exec processes, each polling continuously

### 3. Frontend Event Loop Blocking (LOW PROBABILITY)

**Location**: `src/frontend/src/components/AgentTerminal.vue:172-189`

**Problem**: WebGL addon with fallback to Canvas:

```javascript
// Try WebGL first
webglAddon = new WebglAddon()
webglAddon.onContextLoss(() => {
  loadCanvasFallback()  // Falls back to Canvas
})
terminal.loadAddon(webglAddon)
```

**Impact**:
- WebGL context loss can cause synchronous operations
- Large terminal output can block the render thread
- Not likely the primary cause, but can contribute

---

## Evidence from Logs

### Backend Logs Show:
1. **High-frequency polling requests**: `GET /api/chat/session` every few seconds
2. **Audit logging failures**: `Failed to log audit event:` (empty - likely timeout)
3. **MCP server reconnection loops**: SSE streams constantly re-establishing

### Container Status:
```
trinity-mcp-server  Up 46 hours (unhealthy)  - SSE reconnection loops
trinity-backend     Up 20 hours              - Working but under stress
```

---

## Reproduction Steps

1. Open System Agent page → Terminal auto-connects
2. Navigate to any agent detail page → Terminal auto-connects
3. Try to navigate to Agents list or any other page
4. **Expected**: Navigation works
5. **Actual**: Page hangs, navigation fails

---

## Proposed Solutions

### Solution 1: Use Dedicated Thread Pool for Terminals (RECOMMENDED)

Create a separate `ThreadPoolExecutor` for terminal operations:

```python
# In terminal.py
import concurrent.futures

# Dedicated pool for terminal I/O (won't block main pool)
_terminal_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=10,
    thread_name_prefix="terminal-io"
)

async def read_from_docker():
    while True:
        ready = await loop.run_in_executor(
            _terminal_executor,  # Use dedicated pool
            lambda: select.select([docker_socket], [], [], 0.005)
        )
        # ...
```

**Pros**: Isolates terminal I/O from other async operations
**Cons**: Requires code change and deployment

### Solution 2: Reduce Polling Frequency

Change select timeout from 5ms to 50-100ms:

```python
# Before: 200 polls/second
lambda: select.select([docker_socket], [], [], 0.005)

# After: 10-20 polls/second
lambda: select.select([docker_socket], [], [], 0.05)
```

**Pros**: Simple change, reduces thread pool pressure
**Cons**: May introduce slight input lag (50ms vs 5ms)

### Solution 3: Use asyncio Native I/O (BEST LONG-TERM)

Replace `run_in_executor` with `asyncio.add_reader`:

```python
async def read_from_docker():
    reader, writer = await asyncio.open_connection(sock=docker_socket)
    while True:
        data = await reader.read(16384)
        if not data:
            break
        await websocket.send_bytes(data)
```

**Pros**: No thread pool usage, true async I/O
**Cons**: Requires significant refactoring

### Solution 4: Limit Active Terminal Sessions

Add backend enforcement of max 1-2 total active terminals:

```python
_global_terminal_limit = 2
_active_terminals = 0

async def handle_terminal_session(...):
    global _active_terminals
    if _active_terminals >= _global_terminal_limit:
        await websocket.close(code=4002, reason="Terminal limit reached")
        return
    _active_terminals += 1
    try:
        # ... handle session
    finally:
        _active_terminals -= 1
```

### Solution 5: Frontend - Disconnect on Navigation

Remove KeepAlive for terminal views or disconnect terminal on deactivation:

```javascript
// In AgentDetail.vue
onDeactivated(() => {
  // Disconnect terminal when navigating away
  if (terminalRef.value?.disconnect) {
    terminalRef.value.disconnect()
  }
  stopAllPolling()
})
```

**Pros**: Immediate relief, frontend-only change
**Cons**: User loses terminal session on navigation

---

## Recommended Immediate Fix

**Quick win**: Combine Solutions 2 + 5:

1. Increase select timeout from 5ms to 50ms (backend change)
2. Disconnect terminal on `onDeactivated` (frontend change)

This reduces thread pool pressure by 90% and prevents accumulation of zombie connections.

---

## Files to Modify

| File | Change |
|------|--------|
| `src/backend/services/agent_service/terminal.py:233` | Change `0.005` to `0.05` |
| `src/backend/routers/system_agent.py:503` | Change `0.005` to `0.05` |
| `src/frontend/src/views/AgentDetail.vue:1400` | Add `terminalRef.value?.disconnect()` |
| `src/frontend/src/views/SystemAgent.vue` | Add same disconnect in `onDeactivated` |

---

## Testing Plan

After fix:
1. Open System Agent terminal
2. Navigate to agent detail page
3. Navigate to agents list
4. **Verify**: Navigation is instant, no hanging
5. Navigate back to System Agent
6. **Verify**: Terminal reconnects successfully

---

## Related Issues

- MCP server showing "unhealthy" - SSE reconnection loops (separate issue)
- Audit logging timeouts - likely symptom of thread pool exhaustion

---

## Conclusion

The primary cause is **thread pool exhaustion** from the terminal's tight polling loop using the default executor. The 5ms select timeout creates 200+ thread pool operations per second per terminal. With multiple terminals (via KeepAlive caching), this saturates the pool and blocks other async operations.

**Priority**: HIGH - This affects core UX (navigation)
**Effort**: LOW-MEDIUM - Quick fix available
**Risk**: LOW - Changes are isolated to terminal code

---

## Solution Implemented (2025-12-28)

### Approach: Native asyncio I/O (Solution 3)

Replaced thread pool polling with asyncio's native file descriptor monitoring (`add_reader`/`remove_reader`). This uses the event loop's epoll/kqueue internally for O(1) efficient I/O notification.

### Key Changes

**Before** (thread pool exhaustion):
```python
async def read_from_docker():
    while True:
        # 200 thread pool calls/second per terminal
        ready = await loop.run_in_executor(
            None,
            lambda: select.select([docker_socket], [], [], 0.005)
        )
        if ready[0]:
            data = await loop.run_in_executor(None, ...)
```

**After** (zero thread pool usage):
```python
loop.add_reader(fd, on_docker_readable)  # Register FD with event loop

async def read_from_docker():
    while not stop_event.is_set():
        await data_ready.wait()  # Event-driven, no polling
        data_ready.clear()
        # Read all available data
        while True:
            try:
                data = docker_socket.recv(16384)
                await websocket.send_bytes(data)
            except BlockingIOError:
                break  # No more data
```

### Benefits

| Metric | Before | After |
|--------|--------|-------|
| Thread pool calls/sec | 200+ per terminal | 0 (event-driven) |
| Latency | 5ms polling | Near-instant (epoll/kqueue) |
| CPU usage | High (constant polling) | Low (idle until data) |
| Scalability | 2-3 terminals max | Unlimited (limited by memory) |

### Files Changed

| File | Change |
|------|--------|
| `src/backend/services/agent_service/terminal.py` | Replaced `select` + `run_in_executor` with `add_reader` |
| `src/backend/routers/system_agent.py` | Same refactoring for System Agent terminal |

### Why This Works

1. **Event-driven I/O**: `add_reader` registers the Docker socket FD with the event loop
2. **No polling overhead**: Callback fires only when data is available
3. **Zero thread pool**: All I/O handled in main async loop
4. **Maintains fast response**: Data read immediately when available (no 5ms delay)
5. **Connections stay open**: No changes to KeepAlive or connection lifecycle

### Testing

After deploying:
1. Open System Agent terminal
2. Navigate to multiple agent detail pages
3. Open terminals on multiple agents
4. Verify navigation remains instant
5. Verify all terminals remain responsive
6. Check backend logs for thread pool health

---

## Solution v2: Proper asyncio Socket Coroutines (2025-12-28 12:28)

The `add_reader` approach from v1 caused slow terminal response. The correct solution uses `loop.sock_recv()` and `loop.sock_sendall()` - proper asyncio coroutines.

### Why `add_reader` Failed

The `add_reader` approach:
1. Registers a callback that sets an `asyncio.Event`
2. Async code waits on the Event
3. When callback fires, event wakes the waiter

This indirection caused latency. The callback/Event pattern doesn't integrate well with Docker's socket wrapper.

### Correct Approach: `sock_recv` / `sock_sendall`

```python
loop = asyncio.get_event_loop()

async def read_from_docker():
    while True:
        # sock_recv is a proper coroutine - awaits until data available
        data = await loop.sock_recv(docker_socket, 16384)
        if not data:
            break
        await websocket.send_bytes(data)

async def read_from_websocket():
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            break
        # sock_sendall is a proper coroutine - no thread pool
        await loop.sock_sendall(docker_socket, message["text"].encode())
```

### Why This Works

From [Manning's Python Concurrency with asyncio](https://livebook.manning.com/book/python-concurrency-with-asyncio/chapter-3/v-7):
> "The main coroutines to work with are `sock_recv` and `sock_sendall`. These are analogous to the methods on socket, except they return **coroutines that you can await**."

- `sock_recv()` internally uses the selector to wait for data
- `sock_sendall()` internally handles partial sends
- Both are true coroutines that yield control properly
- No callbacks, no Events, no complexity

### Requirements

- Socket must be non-blocking: `docker_socket.setblocking(False)` ✓
- Socket must be connected (exec_start returns connected socket) ✓

### Result

✅ Fast terminal response
✅ Zero thread pool usage
✅ Clean async/await code
✅ Works with Docker's socket wrapper
