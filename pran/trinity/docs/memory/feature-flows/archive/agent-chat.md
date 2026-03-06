# Feature: Agent Chat API

> **⚠️ DEPRECATED UI (2025-12-25)**: The Chat tab UI has been replaced by the Web Terminal.
> This document now redirects to the relevant current documentation.

---

## Current Documentation

| Use Case | Document |
|----------|----------|
| **Interactive Claude Code usage** | [agent-terminal.md](agent-terminal.md) - Web Terminal with PTY access |
| **Chat API / Execution Queue** | [execution-queue.md](execution-queue.md) - Includes Chat API implementation details |
| **Stateless task execution** | [parallel-headless-execution.md](parallel-headless-execution.md) - POST /task endpoint |
| **Agent-to-agent communication** | [agent-to-agent-collaboration.md](agent-to-agent-collaboration.md) - MCP chat_with_agent |

---

## What Still Uses the Chat API

The `POST /api/agents/{name}/chat` endpoint is still actively used by:

1. **Scheduled executions** - Cron jobs send messages via the chat API
2. **MCP `chat_with_agent` tool** - Agent-to-agent communication
3. **Backend services** - Any programmatic agent interaction

All execution requests go through the **Execution Queue** to prevent parallel execution.
See [execution-queue.md](execution-queue.md) for complete documentation.

---

**Status**: ❌ UI Deprecated (2025-12-25) | ✅ API Still Active
**Merged Into**: [execution-queue.md](execution-queue.md)
