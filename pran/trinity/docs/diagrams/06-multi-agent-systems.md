# Trinity Multi-Agent System Architecture

## What This Diagram Shows

This document illustrates Trinity's multi-agent orchestration capabilities:

1. **System Manifest Deployment** - YAML-based declarative deployment of agent fleets
2. **Permission Presets** - Four permission patterns: full-mesh, orchestrator-workers, none, explicit
3. **Shared Folder Architecture** - File-based collaboration via Docker volumes
4. **Orchestrator-Worker Pattern** - Parallel task delegation with `parallel=true`
5. **System Agent Integration** - The `trinity-system` agent's role in fleet management

---

## System Manifest Deployment

```
+---------------------------------------------------------------------------------+
|                      SYSTEM MANIFEST DEPLOYMENT                                 |
|                                                                                 |
|                                                                                 |
|   +-------------------------------------------------------------------------+  |
|   |                        system.yaml                                       |  |
|   |                                                                          |  |
|   |   name: content-production                                               |  |
|   |   description: Autonomous content pipeline                               |  |
|   |                                                                          |  |
|   |   prompt: |                                                              |  |
|   |     You are part of the Content Production system.                       |  |
|   |     Coordinate with other agents via Trinity MCP.                        |  |
|   |                                                                          |  |
|   |   agents:                                                                |  |
|   |     orchestrator:                                                        |  |
|   |       template: github:YourOrg/orchestrator-template                     |  |
|   |       resources: {cpu: "2", memory: "4g"}                                |  |
|   |       folders: {expose: true, consume: true}                             |  |
|   |                                                                          |  |
|   |     researcher:                                                          |  |
|   |       template: local:research-agent                                     |  |
|   |       folders: {expose: true}                                            |  |
|   |                                                                          |  |
|   |     writer:                                                              |  |
|   |       template: local:writer-agent                                       |  |
|   |       folders: {consume: true}                                           |  |
|   |       schedules:                                                         |  |
|   |         - name: daily-draft                                              |  |
|   |           cron: "0 9 * * *"                                              |  |
|   |           message: "Write daily content draft"                           |  |
|   |                                                                          |  |
|   |   permissions:                                                           |  |
|   |     preset: orchestrator-workers                                         |  |
|   |                                                                          |  |
|   +-------------------------------------------------------------------------+  |
|                                                                                 |
|                                      |                                          |
|                                      | POST /api/systems/deploy                 |
|                                      v                                          |
|                                                                                 |
|   +-------------------------------------------------------------------------+  |
|   |                        DEPLOYMENT RESULT                                 |  |
|   |                                                                          |  |
|   |   Created Agents:                                                        |  |
|   |   +-- content-production-orchestrator                                    |  |
|   |   +-- content-production-researcher                                      |  |
|   |   +-- content-production-writer                                          |  |
|   |                                                                          |  |
|   |   Permissions (orchestrator-workers preset):                             |  |
|   |   +-- orchestrator -> researcher [check]                                 |  |
|   |   +-- orchestrator -> writer [check]                                     |  |
|   |   +-- researcher -> orchestrator [check]                                 |  |
|   |   +-- writer -> orchestrator [check]                                     |  |
|   |                                                                          |  |
|   |   Shared Folders:                                                        |  |
|   |   +-- orchestrator: expose + consume                                     |  |
|   |   +-- researcher: expose only                                            |  |
|   |   +-- writer: consume only                                               |  |
|   |                                                                          |  |
|   |   Schedules:                                                             |  |
|   |   +-- writer: daily-draft @ 9 AM                                         |  |
|   |                                                                          |  |
|   |   Trinity Prompt: Updated globally                                       |  |
|   |                                                                          |  |
|   |   All agents started: [check]                                            |  |
|   |                                                                          |  |
|   +-------------------------------------------------------------------------+  |
|                                                                                 |
+----------------------------------------------------------------------------------+
```

## Permission Presets

```
+---------------------------------------------------------------------------------+
|                         PERMISSION PRESETS                                      |
|                                                                                 |
|                                                                                 |
|   +-----------------------------+    +-----------------------------+           |
|   |      FULL-MESH              |    |    ORCHESTRATOR-WORKERS     |           |
|   |                             |    |                             |           |
|   |   Every agent can           |    |   First agent is            |           |
|   |   call every other          |    |   orchestrator, others      |           |
|   |                             |    |   are workers               |           |
|   |                             |    |                             |           |
|   |      +---+                  |    |         +---+               |           |
|   |      | A |<--------+        |    |         | O |               |           |
|   |      +-+-+         |        |    |         +-+-+               |           |
|   |        |           |        |    |       +---+---+             |           |
|   |        v           |        |    |       v       v             |           |
|   |      +---+       +-+-+      |    |     +---+   +---+           |           |
|   |      | B |<----->| C |      |    |     |W1 |   |W2 |           |           |
|   |      +---+       +---+      |    |     +-+-+   +-+-+           |           |
|   |                             |    |       |       |             |           |
|   |   A<->B, A<->C, B<->C       |    |       +---+---+             |           |
|   |                             |    |           v                 |           |
|   |                             |    |         +---+               |           |
|   |                             |    |         | O |               |           |
|   |                             |    |         +---+               |           |
|   |                             |    |                             |           |
|   |                             |    |   O->W1, O->W2              |           |
|   |                             |    |   W1->O, W2->O              |           |
|   |                             |    |   (workers can't call       |           |
|   |                             |    |    each other)              |           |
|   |                             |    |                             |           |
|   +-----------------------------+    +-----------------------------+           |
|                                                                                 |
|   +-----------------------------+    +-----------------------------+           |
|   |         NONE                |    |        EXPLICIT             |           |
|   |                             |    |                             |           |
|   |   No permissions            |    |   Custom permission         |           |
|   |   granted                   |    |   matrix                    |           |
|   |                             |    |                             |           |
|   |      +---+                  |    |   permissions:              |           |
|   |      | A |                  |    |     explicit:               |           |
|   |      +---+                  |    |       orchestrator:         |           |
|   |                             |    |         - researcher        |           |
|   |      +---+                  |    |         - writer            |           |
|   |      | B |                  |    |       researcher:           |           |
|   |      +---+                  |    |         - writer            |           |
|   |                             |    |                             |           |
|   |      +---+                  |    |   O->R, O->W, R->W          |           |
|   |      | C |                  |    |                             |           |
|   |      +---+                  |    |                             |           |
|   |                             |    |                             |           |
|   |   (isolated agents)         |    |                             |           |
|   |                             |    |                             |           |
|   +-----------------------------+    +-----------------------------+           |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

## Shared Folder Architecture

```
+---------------------------------------------------------------------------------+
|                      SHARED FOLDER ARCHITECTURE                                 |
|                                                                                 |
|                                                                                 |
|   +-------------------------------------------------------------------------+  |
|   |                        DOCKER VOLUMES                                    |  |
|   |                                                                          |  |
|   |   agent-researcher-shared (Docker Volume)                                |  |
|   |   agent-writer-shared (Docker Volume)                                    |  |
|   |                                                                          |  |
|   +-------------------------------------------------------------------------+  |
|                                                                                 |
|                                                                                 |
|   +------------------------------+    +------------------------------+         |
|   |      RESEARCHER AGENT        |    |       WRITER AGENT           |         |
|   |      (expose: true)          |    |       (consume: true)        |         |
|   |                              |    |                              |         |
|   |   /home/developer/           |    |   /home/developer/           |         |
|   |   +-- workspace/             |    |   +-- workspace/             |         |
|   |   |   +-- [code]             |    |   |   +-- [code]             |         |
|   |   |                          |    |   |                          |         |
|   |   +-- shared-out/ <----------+----+---+                          |         |
|   |   |   +-- research-data.json |    |   |                          |         |
|   |   |       (written here)     |    |   |                          |         |
|   |   |                          |    |   |                          |         |
|   |   +-- shared-in/             |    |   +-- shared-in/             |         |
|   |       (empty - not consuming)|    |       +-- researcher/ <------+-----+   |
|   |                              |    |           +-- research-      |     |   |
|   |                              |    |               data.json      |     |   |
|   |                              |    |               (mounted here) |     |   |
|   |                              |    |                              |     |   |
|   +------------------------------+    +------------------------------+     |   |
|                                                                             |   |
|                                                                             |   |
|   +-------------------------------------------------------------------------+   |
|   |                                                                             |
|   |   Volume Mount:                                                             |
|   |   agent-researcher-shared:/home/developer/shared-out (in researcher)        |
|   |   agent-researcher-shared:/home/developer/shared-in/researcher (in writer)  |
|   |                                                                             |
|   |   Permission Required:                                                      |
|   |   Writer must have permission to call Researcher                            |
|   |   (same permission as for chat_with_agent)                                  |
|   |                                                                             |
|   +-----------------------------------------------------------------------------+
|                                                                                 |
|                                                                                 |
|   Data Flow:                                                                    |
|   ----------                                                                    |
|                                                                                 |
|   1. Researcher writes to /home/developer/shared-out/research-data.json         |
|   2. Docker volume persists the file                                            |
|   3. Writer reads from /home/developer/shared-in/researcher/research-data.json  |
|   4. No network communication needed - pure file-based collaboration            |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

## Orchestrator-Worker Pattern with Parallel Execution

```
+---------------------------------------------------------------------------------+
|                      ORCHESTRATOR-WORKER PATTERN                                |
|                                                                                 |
|                                                                                 |
|   +-------------------------------------------------------------------------+  |
|   |                        ORCHESTRATOR AGENT                                |  |
|   |                                                                          |  |
|   |   Role: Decompose complex tasks, delegate to workers, aggregate results |  |
|   |                                                                          |  |
|   |   Capabilities:                                                          |  |
|   |   * mcp__trinity__list_agents() - See available workers                  |  |
|   |   * mcp__trinity__chat_with_agent(parallel=true) - Parallel execution    |  |
|   |   * Read shared-in folders for worker outputs                            |  |
|   |   * Write instructions to shared-out for workers                         |  |
|   |                                                                          |  |
|   |   +-------------------------------------------------------------+       |  |
|   |   |                    TASK DECOMPOSITION                        |       |  |
|   |   |                                                              |       |  |
|   |   |   User Request: "Create a market analysis report"           |       |  |
|   |   |                                                              |       |  |
|   |   |   +--------------+                                           |       |  |
|   |   |   |  Orchestrator |                                          |       |  |
|   |   |   |   analyzes    |                                          |       |  |
|   |   |   |   request     |                                          |       |  |
|   |   |   +------+-------+                                           |       |  |
|   |   |          |                                                   |       |  |
|   |   |          v                                                   |       |  |
|   |   |   +----------------------------------------------------------+      |  |
|   |   |   |              PARALLEL TASK DISPATCH                       |      |  |
|   |   |   |                  (parallel=true)                          |      |  |
|   |   |   |                                                           |      |  |
|   |   |   |   chat_with_agent(      chat_with_agent(                  |      |  |
|   |   |   |     target="researcher",  target="analyst",               |      |  |
|   |   |   |     message="Research     message="Analyze                |      |  |
|   |   |   |       competitors",        market trends",                |      |  |
|   |   |   |     parallel=true,        parallel=true,                  |      |  |
|   |   |   |     max_turns=50)         max_turns=50)                   |      |  |
|   |   |   |          |                     |                          |      |  |
|   |   |   |          v                     v                          |      |  |
|   |   |   |   +------------+        +------------+                    |      |  |
|   |   |   |   | Researcher |        |  Analyst   |                    |      |  |
|   |   |   |   |  (worker)  |        |  (worker)  |                    |      |  |
|   |   |   |   +-----+------+        +-----+------+                    |      |  |
|   |   |   |         |                     |                           |      |  |
|   |   |   |         |  Writes to          |  Writes to                |      |  |
|   |   |   |         |  shared-out         |  shared-out               |      |  |
|   |   |   |         |                     |                           |      |  |
|   |   |   |         v                     v                           |      |  |
|   |   |   |   +--------------------------------------------+          |      |  |
|   |   |   |   |        ORCHESTRATOR AGGREGATES              |          |      |  |
|   |   |   |   |                                             |          |      |  |
|   |   |   |   |  Reads from shared-in/researcher/           |          |      |  |
|   |   |   |   |  Reads from shared-in/analyst/              |          |      |  |
|   |   |   |   |  Combines into final report                 |          |      |  |
|   |   |   |   |                                             |          |      |  |
|   |   |   |   +--------------------------------------------+          |      |  |
|   |   |   |                                                           |      |  |
|   |   |   +-----------------------------------------------------------+      |  |
|   |   |                                                              |       |  |
|   |   +-------------------------------------------------------------+       |  |
|   |                                                                          |  |
|   +-------------------------------------------------------------------------+  |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

## System Agent Fleet Management

```
+---------------------------------------------------------------------------------+
|                      SYSTEM AGENT (trinity-system)                              |
|                                                                                 |
|   The trinity-system agent is a privileged, auto-deployed agent that           |
|   manages platform operations. It has system-scoped MCP access that            |
|   bypasses all permission checks.                                               |
|                                                                                 |
|   +-------------------------------------------------------------------------+  |
|   |                        FLEET ARCHITECTURE                                |  |
|   |                                                                          |  |
|   |                     +-------------------+                                |  |
|   |                     |  trinity-system   |                                |  |
|   |                     |  (System Agent)   |                                |  |
|   |                     |  scope: "system"  |                                |  |
|   |                     +--------+----------+                                |  |
|   |                              |                                           |  |
|   |              +---------------+---------------+                           |  |
|   |              |               |               |                           |  |
|   |              v               v               v                           |  |
|   |     +--------+-----+ +------+-------+ +-----+--------+                   |  |
|   |     | orchestrator | |  researcher  | |    writer    |                   |  |
|   |     | (user agent) | | (user agent) | | (user agent) |                   |  |
|   |     +--------+-----+ +------+-------+ +-----+--------+                   |  |
|   |              |               |               |                           |  |
|   |              +---------------+---------------+                           |  |
|   |                              |                                           |  |
|   |                     Permission-based                                     |  |
|   |                     collaboration                                        |  |
|   |                                                                          |  |
|   +-------------------------------------------------------------------------+  |
|                                                                                 |
|   System Agent Operations:                                                      |
|   --------------------------                                                    |
|                                                                                 |
|   * /ops/status        - Fleet status report (all agents)                       |
|   * /ops/health        - Health check with issues & recommendations             |
|   * /ops/restart       - Restart specific agent                                 |
|   * /ops/restart-all   - Restart entire fleet                                   |
|   * /ops/stop          - Stop specific agent                                    |
|   * /ops/costs         - Cost report from OTel metrics                          |
|   * /ops/schedules     - Schedule management                                    |
|   * /ops/emergency-stop - Halt all executions immediately                       |
|                                                                                 |
|   MCP Scope Hierarchy:                                                          |
|   ---------------------                                                         |
|                                                                                 |
|   +---------------+     +---------------+     +---------------+                 |
|   |    SYSTEM     |     |     AGENT     |     |     USER      |                 |
|   |   (bypass)    | >   |  (permitted)  | >   | (owner/shared)|                 |
|   +---------------+     +---------------+     +---------------+                 |
|                                                                                 |
|   - system: Bypasses ALL permission checks (trinity-system only)                |
|   - agent: Can only call explicitly permitted agents                            |
|   - user: Human users, checked via ownership/sharing                            |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

## Parallel vs Sequential Execution

```
+---------------------------------------------------------------------------------+
|                      EXECUTION MODE COMPARISON                                  |
|                                                                                 |
|   +---------------------------------------+------------------------------------+|
|   |          SEQUENTIAL CHAT              |         PARALLEL TASK              ||
|   |          (default mode)               |         (parallel=true)            ||
|   +---------------------------------------+------------------------------------+|
|   |                                       |                                    ||
|   |   POST /api/agents/{name}/chat        |   POST /api/agents/{name}/task     ||
|   |                                       |                                    ||
|   |   - Maintains conversation context    |   - Stateless (no context)         ||
|   |   - Uses --continue flag              |   - No --continue flag             ||
|   |   - Execution queue (Redis)           |   - NO execution queue             ||
|   |   - Execution lock (asyncio.Lock)     |   - NO execution lock              ||
|   |   - 1 request at a time per agent     |   - N concurrent requests          ||
|   |   - Interactive chat use case         |   - Batch/delegation use case      ||
|   |                                       |                                    ||
|   +---------------------------------------+------------------------------------+|
|                                                                                 |
|   Parallel Execution Flow:                                                      |
|   -------------------------                                                     |
|                                                                                 |
|   Orchestrator                                                                  |
|       |                                                                         |
|       +---> chat_with_agent("worker-1", "Task A", parallel=true, max_turns=50)  |
|       |         \                                                               |
|       +---> chat_with_agent("worker-2", "Task B", parallel=true, max_turns=50)  |
|       |          \                                                              |
|       +---> chat_with_agent("worker-3", "Task C", parallel=true, max_turns=50)  |
|                   \                                                             |
|                    +---> All 3 execute CONCURRENTLY                             |
|                    |                                                            |
|                    +---> No queue blocking                                      |
|                    |                                                            |
|                    +---> Results returned as each completes                     |
|                                                                                 |
|   Parallel Task Parameters:                                                     |
|   --------------------------                                                    |
|                                                                                 |
|   | Parameter         | Type      | Default | Description                      |
|   |-------------------|-----------|---------|----------------------------------|
|   | parallel          | boolean   | false   | Enable parallel mode             |
|   | max_turns         | number    | null    | Limit agentic turns (runaway)    |
|   | timeout_seconds   | number    | 300     | Wall-clock timeout               |
|   | model             | string    | null    | Model override                   |
|   | allowed_tools     | string[]  | null    | Tool restrictions                |
|   | system_prompt     | string    | null    | Additional instructions          |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

---

## Sources

### Feature Flows (Detailed Documentation)

| Feature Flow | Description |
|--------------|-------------|
| [system-manifest.md](../memory/feature-flows/system-manifest.md) | Complete system manifest deployment documentation |
| [agent-shared-folders.md](../memory/feature-flows/agent-shared-folders.md) | File-based collaboration via Docker volumes |
| [agent-permissions.md](../memory/feature-flows/agent-permissions.md) | Agent-to-agent permission system |
| [parallel-headless-execution.md](../memory/feature-flows/parallel-headless-execution.md) | Parallel task execution with `parallel=true` |
| [internal-system-agent.md](../memory/feature-flows/internal-system-agent.md) | System agent (`trinity-system`) operations |

### Code References

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| System manifest models | `src/backend/models.py` | 248-286 | SystemManifest, SystemAgentConfig, SystemPermissions |
| System deployment | `src/backend/services/system_service.py` | 1-552 | YAML parsing, validation, deployment logic |
| Systems router | `src/backend/routers/systems.py` | 1-427 | POST /api/systems/deploy, list, restart, export |
| Permission service | `src/backend/services/agent_service/permissions.py` | 1-169 | Permission business logic |
| Permissions router | `src/backend/routers/agents.py` | 642-681 | GET/PUT permissions endpoints |
| Shared folders service | `src/backend/services/agent_service/folders.py` | 1-218 | Folder configuration logic |
| Parallel task endpoint | `src/backend/routers/chat.py` | 418-630 | POST /api/agents/{name}/task |
| Parallel execution | `docker/base-image/agent_server/services/claude_code.py` | 553-739 | execute_headless_task() |
| chat_with_agent tool | `src/mcp-server/src/tools/chat.ts` | 130-270 | MCP tool with parallel parameter |
| System agent service | `src/backend/services/system_agent_service.py` | 1-300 | Auto-deployment logic |
| Ops router | `src/backend/routers/ops.py` | 1-682 | Fleet operations endpoints |

### Database Tables

| Table | Purpose |
|-------|---------|
| `agent_permissions` | Source-target permission pairs |
| `agent_shared_folder_config` | Expose/consume settings per agent |
| `agent_schedules` | Scheduled tasks per agent |
| `system_settings` | Global settings including `trinity_prompt` |

### MCP Tools

| Tool | Description |
|------|-------------|
| `deploy_system` | Deploy from YAML manifest |
| `list_systems` | List deployed systems |
| `restart_system` | Restart all system agents |
| `chat_with_agent` | With `parallel=true` for concurrent execution |

---

**Last Updated**: 2026-01-25
