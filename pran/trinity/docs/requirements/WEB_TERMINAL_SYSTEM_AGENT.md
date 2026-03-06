# Web Terminal for System Agent

> **Status**: Requirements Approved
> **Priority**: High
> **Created**: 2025-12-25
> **Requirement ID**: 11.5

---

## Overview

Enable secure, interactive Claude Code sessions with the System Agent (`trinity-system`) directly from the Trinity web UI. The terminal should preserve ALL Claude Code TUI functionality including interactive prompts, keyboard shortcuts, colors, and streaming output.

## Problem Statement

Users need to interact with the System Agent for platform operations (fleet management, health checks, cost monitoring). Currently, this requires:
1. SSH access to the Trinity server
2. Docker exec into the container
3. Running Claude Code manually

This creates friction and security concerns (exposing SSH ports, managing keys).

## Solution: PTY-Forwarding Web Terminal

A browser-based terminal using **xterm.js** that connects via WebSocket to the backend, which allocates a real **PTY** (pseudo-terminal) via Docker exec. This preserves the full Claude Code TUI experience.

### Architecture

```
┌─────────────────┐      WebSocket       ┌─────────────────┐      PTY/Socket      ┌─────────────────┐
│   Browser       │◄───────────────────►│   Backend       │◄───────────────────►│  trinity-system │
│   (xterm.js)    │   Binary frames      │   (FastAPI)     │   docker exec -it   │   (Claude Code) │
└─────────────────┘                      └─────────────────┘                      └─────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Terminal emulator | xterm.js v6.0.0 | Industry standard, used by VS Code, full TUI support |
| Transport | WebSocket (binary) | Bidirectional, low latency, supports PTY escape codes |
| PTY allocation | Docker SDK `exec_run(tty=True, socket=True)` | Real PTY preserves all terminal features |
| Security | Admin-only, JWT auth, no SSH port exposure | Zero attack surface, uses existing auth |

---

## Functional Requirements

### FR-1: Terminal Access Button
- **Location**: System Agent page (`/system-agent`)
- **UI**: "Open Terminal" button in the header actions area
- **Behavior**: Opens modal or side panel with terminal
- **Access**: Admin users only

### FR-2: Full PTY Terminal
- **Must preserve**: All Claude Code TUI functionality
  - Interactive prompts and dialogs
  - Keyboard shortcuts (Escape, Ctrl+C, etc.)
  - ANSI colors and formatting
  - Streaming output with cursor positioning
  - vim-mode editing
  - Tab completion
  - Mouse events (if supported by Claude Code)

### FR-3: Terminal Resize
- Terminal must respond to browser window/panel resize
- Send resize events (cols, rows) to backend
- Backend must call `docker exec_resize()` to update PTY dimensions

### FR-4: Session Lifecycle
- **Connect**: Establish WebSocket, spawn PTY, start Claude Code
- **Active**: Bidirectional byte forwarding
- **Disconnect**: Clean PTY termination, WebSocket close
- **Reconnect**: Fresh session (no resume - stateless)

### FR-5: Default Shell Options
- Option 1: Start directly in Claude Code (`claude`)
- Option 2: Start in bash shell (`/bin/bash`)
- UI: Toggle or dropdown to select mode before connecting

---

## Non-Functional Requirements

### NFR-1: Security
- Admin-only access enforced via JWT
- No SSH port exposure (internal Docker network only)
- Audit logging for terminal sessions (start/end timestamps)
- WebSocket connection authenticated on establishment
- Session timeout after inactivity (configurable, default 30 min)

### NFR-2: Performance
- Latency: < 50ms for keystroke echo (local network)
- No buffering of terminal output (stream immediately)
- Handle high-throughput output (e.g., long file listings)

### NFR-3: Reliability
- Graceful handling of container restart during session
- Clear error message if container not running
- Auto-close terminal if WebSocket disconnects

---

## Technical Specification

### Frontend Components

#### New Dependencies (package.json)
```json
{
  "@xterm/xterm": "^6.0.0",
  "@xterm/addon-fit": "^0.10.0",
  "@xterm/addon-web-links": "^0.11.0"
}
```

> **Note**: The old `xterm` and `xterm-addon-*` packages are deprecated. Use the new `@xterm/*` scoped packages.

#### Component: `SystemAgentTerminal.vue`
```vue
<template>
  <div class="terminal-container" ref="terminalContainer"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'

const props = defineProps({
  mode: { type: String, default: 'claude' } // 'claude' or 'bash'
})

const terminalContainer = ref(null)
let terminal = null
let fitAddon = null
let ws = null

onMounted(() => {
  // Initialize terminal
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: {
      background: '#1e1e1e',
      foreground: '#d4d4d4'
    }
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.loadAddon(new WebLinksAddon())

  terminal.open(terminalContainer.value)
  fitAddon.fit()

  // Connect WebSocket
  const token = localStorage.getItem('trinity_token')
  const wsUrl = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/system-agent/terminal?mode=${props.mode}`

  ws = new WebSocket(wsUrl)
  ws.binaryType = 'arraybuffer'

  // Auth on connect
  ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'auth', token }))
  }

  // Terminal output from server
  ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      terminal.write(new Uint8Array(event.data))
    } else {
      // JSON control message
      const msg = JSON.parse(event.data)
      if (msg.type === 'error') {
        terminal.write(`\r\n\x1b[31mError: ${msg.message}\x1b[0m\r\n`)
      }
    }
  }

  ws.onclose = () => {
    terminal.write('\r\n\x1b[33mConnection closed.\x1b[0m\r\n')
  }

  // Terminal input to server
  terminal.onData(data => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  })

  // Handle resize
  const resizeObserver = new ResizeObserver(() => {
    fitAddon.fit()
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'resize',
        cols: terminal.cols,
        rows: terminal.rows
      }))
    }
  })
  resizeObserver.observe(terminalContainer.value)
})

onBeforeUnmount(() => {
  if (ws) ws.close()
  if (terminal) terminal.dispose()
})
</script>

<style scoped>
.terminal-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
}
</style>
```

### Backend Implementation

#### WebSocket Endpoint: `/ws/system-agent/terminal`

**File**: `src/backend/routers/system_agent.py`

```python
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect, Query
from services.docker_service import docker_client
from dependencies import decode_token
from services.audit_service import log_audit_event

SYSTEM_AGENT_NAME = "trinity-system"

@router.websocket("/ws/terminal")
async def system_agent_terminal(
    websocket: WebSocket,
    mode: str = Query(default="claude")  # 'claude' or 'bash'
):
    await websocket.accept()

    # Authenticate via first message
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth_data = json.loads(auth_msg)
        if auth_data.get("type") != "auth":
            await websocket.close(code=4001, reason="Expected auth message")
            return

        user = decode_token(auth_data.get("token"))
        if not user or not user.get("is_admin"):
            await websocket.close(code=4003, reason="Admin access required")
            return
    except asyncio.TimeoutError:
        await websocket.close(code=4001, reason="Auth timeout")
        return
    except Exception as e:
        await websocket.close(code=4001, reason=str(e))
        return

    # Get container
    try:
        container = docker_client.containers.get(SYSTEM_AGENT_NAME)
        if container.status != "running":
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "System agent is not running"
            }))
            await websocket.close()
            return
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Container not found: {e}"
        }))
        await websocket.close()
        return

    # Audit log
    await log_audit_event("terminal_session", "system_agent_terminal", {
        "user_email": user.get("email"),
        "mode": mode,
        "action": "start"
    })

    # Create exec with TTY
    cmd = ["claude"] if mode == "claude" else ["/bin/bash"]
    exec_instance = docker_client.api.exec_create(
        SYSTEM_AGENT_NAME,
        cmd,
        stdin=True,
        tty=True,
        stdout=True,
        stderr=True,
        environment={"TERM": "xterm-256color"}
    )
    exec_id = exec_instance["Id"]

    # Start exec and get socket
    socket = docker_client.api.exec_start(exec_id, socket=True, tty=True)
    sock = socket._sock  # Get underlying socket
    sock.setblocking(False)

    # Bidirectional forwarding
    async def read_from_container():
        """Read from Docker socket, send to WebSocket."""
        loop = asyncio.get_event_loop()
        while True:
            try:
                data = await loop.run_in_executor(None, lambda: sock.recv(4096))
                if not data:
                    break
                await websocket.send_bytes(data)
            except Exception:
                break

    async def read_from_websocket():
        """Read from WebSocket, send to Docker socket."""
        while True:
            try:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break

                if "text" in message:
                    # Control message (resize)
                    try:
                        ctrl = json.loads(message["text"])
                        if ctrl.get("type") == "resize":
                            docker_client.api.exec_resize(
                                exec_id,
                                height=ctrl.get("rows", 24),
                                width=ctrl.get("cols", 80)
                            )
                    except json.JSONDecodeError:
                        # Plain text input
                        sock.sendall(message["text"].encode())
                elif "bytes" in message:
                    sock.sendall(message["bytes"])
            except WebSocketDisconnect:
                break
            except Exception:
                break

    # Run both tasks
    try:
        await asyncio.gather(
            read_from_container(),
            read_from_websocket()
        )
    finally:
        sock.close()
        await log_audit_event("terminal_session", "system_agent_terminal", {
            "user_email": user.get("email"),
            "mode": mode,
            "action": "end"
        })
```

#### Docker SDK Notes

**Current version in project**: `docker==7.1.0`

Key methods:
- `docker_client.api.exec_create()` - Create exec instance with TTY
- `docker_client.api.exec_start(exec_id, socket=True, tty=True)` - Get socket
- `docker_client.api.exec_resize(exec_id, height, width)` - Resize PTY

**Known issue**: In Python 3, `socket=True` returns `SocketIO` object. Use `._sock` to get raw socket, or iterate on the socket object directly.

---

## UI Integration

### System Agent Page Updates

**File**: `src/frontend/src/views/SystemAgent.vue`

Add to header actions:
```vue
<button
  @click="openTerminal"
  class="px-3 py-1.5 text-sm font-medium text-white bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2"
>
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
  </svg>
  Open Terminal
</button>
```

### Terminal Modal

Full-screen or large modal with:
- Terminal occupying main area
- Header with mode toggle (Claude / Bash)
- Close button
- Status indicator (connected/disconnected)

---

## Security Considerations

| Threat | Mitigation |
|--------|------------|
| Unauthorized access | JWT auth required, admin-only check |
| Session hijacking | Token validated on WebSocket connect |
| Container escape | Standard Docker security (non-root, cap-drop) |
| DoS via many terminals | Limit to 1 active terminal per user |
| Data exfiltration | Audit logging of session start/end |

---

## Testing Plan

### Manual Testing

1. **Admin Access**
   - Login as admin, navigate to System Agent page
   - Click "Open Terminal", verify terminal opens
   - Type `echo hello`, verify output

2. **Non-Admin Rejection**
   - Login as non-admin user
   - Attempt to open terminal (button should be hidden or disabled)
   - If accessed directly, verify 403 response

3. **Claude Code Functionality**
   - Open terminal in "claude" mode
   - Run `/help` command
   - Verify colors, formatting preserved
   - Test Ctrl+C to cancel
   - Test interactive prompts

4. **Resize Handling**
   - Resize browser window
   - Verify terminal re-renders correctly
   - Run `stty size` to confirm PTY dimensions match

5. **Session Cleanup**
   - Close terminal modal
   - Verify WebSocket disconnected
   - Verify no orphaned exec processes in container

### Edge Cases

- Container not running: Show error message
- WebSocket disconnect: Show reconnect option or error
- Long-running output: Verify no freezing
- Special characters: Test unicode, emojis

---

## Implementation Phases

### Phase 1: Core Terminal (2-3 hours)
- [ ] Add xterm.js dependencies to frontend
- [ ] Create `SystemAgentTerminal.vue` component
- [ ] Add WebSocket endpoint to `routers/system_agent.py`
- [ ] Basic bidirectional PTY forwarding

### Phase 2: Polish (1-2 hours)
- [ ] Modal/panel UI integration
- [ ] Mode toggle (Claude/Bash)
- [ ] Error handling and status indicators
- [ ] Audit logging

### Phase 3: Security Hardening (1 hour)
- [ ] Admin-only enforcement
- [ ] Session timeout
- [ ] Rate limiting (1 terminal per user)

---

## Dependencies

### Frontend (New)
| Package | Version | Purpose |
|---------|---------|---------|
| `@xterm/xterm` | ^6.0.0 | Terminal emulator core |
| `@xterm/addon-fit` | ^0.10.0 | Auto-resize terminal to container |
| `@xterm/addon-web-links` | ^0.11.0 | Clickable URLs in terminal |

### Backend (Existing)
| Package | Version | Notes |
|---------|---------|-------|
| `docker` | 7.1.0 | Already installed, supports exec with socket |
| `websockets` | 14.1 | Already installed via uvicorn[standard] |

---

## References

- [xterm.js Official Site](https://xtermjs.org/)
- [xterm.js GitHub](https://github.com/xtermjs/xterm.js)
- [@xterm/xterm npm](https://www.npmjs.com/package/@xterm/xterm)
- [Docker SDK for Python - Containers](https://docker-py.readthedocs.io/en/stable/containers.html)
- [Docker SDK for Python - Low-level API](https://docker-py.readthedocs.io/en/stable/api.html)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [FastAPI + Docker exec WebSocket (GitHub Issue #1990)](https://github.com/fastapi/fastapi/issues/1990)
- [dockerpty - PTY handler for Docker](https://github.com/d11wtq/dockerpty)

---

## Acceptance Criteria

- [ ] Admin user can open terminal from System Agent page
- [ ] Terminal preserves full Claude Code TUI (colors, prompts, shortcuts)
- [ ] Non-admin users cannot access terminal
- [ ] Terminal resizes correctly with browser window
- [ ] Session cleanup on disconnect (no orphaned processes)
- [ ] Audit log entries for terminal sessions
- [ ] Error messages for container-not-running state
