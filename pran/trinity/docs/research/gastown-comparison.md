# Gastown Analysis & Trinity Comparison

> **Date**: 2026-01-27
> **Source**: https://github.com/steveyegge/gastown
> **Purpose**: Analyze competing/related project for feature ideas

## Executive Summary

**Gastown** is a CLI-first, git-backed multi-agent orchestration system by Steve Yegge (6.3k stars). It focuses on **developer workflows** with Claude Code agents, using persistent git worktrees to survive context loss.

**Trinity** is a web-based Deep Agent Orchestration Platform focusing on **enterprise orchestration** with containerized agents, Process Engine for workflows, and visual collaboration dashboards.

---

## Architecture Comparison

| Aspect | Gastown | Trinity |
|--------|---------|---------|
| **Primary Interface** | CLI (`gt` command) | Web UI + REST API |
| **Agent Runtime** | Local Claude Code instances | Docker containers |
| **Persistence** | Git worktrees + Beads JSONL | SQLite + Redis |
| **Coordination** | Mayor pattern (orchestrator agent) | MCP Server + WebSocket |
| **Work Tracking** | Beads ledger (git-backed issues) | Schedules + Activity Stream |
| **Scaling Target** | 20-30 agents | 50+ agents |
| **Installation** | `brew install gastown` | Docker Compose |
| **Multi-runtime** | Claude, Codex, Cursor, Gemini | Claude Code, Gemini CLI |

---

## Key Concepts Comparison

### 1. Agent Organization

| Gastown Term | Concept | Trinity Equivalent |
|--------------|---------|-------------------|
| **Town** | Workspace directory | Platform (Docker network) |
| **Rig** | Project container wrapping git repo | Agent (Docker container) |
| **Crew Member** | Developer workspace in a rig | Agent workspace (`/home/developer/`) |
| **Polecat** | Ephemeral worker agent | Parallel Task (`POST /api/task`) |
| **The Mayor** | Primary AI coordinator | System Agent (`trinity-system`) |

### 2. Work Persistence

| Gastown | Trinity |
|---------|---------|
| **Hooks**: Git worktree-based storage | **Volumes**: Docker bind mounts |
| **Beads**: Git-backed issue tracker (JSONL) | **SQLite**: `schedule_executions`, `agent_activities` |
| **Convoys**: Bundle of beads for tracking | **Process Execution**: Multi-step workflow instance |

### 3. Coordination Patterns

| Gastown | Trinity |
|---------|---------|
| Mayor orchestrates via `gt sling` | MCP `chat_with_agent` tool |
| Mailbox injection via hooks | WebSocket broadcasts |
| Formula templates (TOML) | Process definitions (YAML) |

---

## What Gastown Does Well (Ideas to Borrow)

### 1. **Git-Backed Work Persistence** ⭐
Gastown's core innovation is using **git worktrees** to persist agent work state. This means:
- Work survives crashes, restarts, and context window resets
- State is versioned and can be rolled back
- Natural branching for parallel work streams

**Trinity gap**: We rely on SQLite + Redis, but agent internal state (Claude Code's context) is still ephemeral.

**Idea to borrow**:
- Add a `~/.claude/hooks/` integration that writes to persistent storage on key events
- Consider "Memory Folding" feature (already in roadmap) with git-backed snapshots

### 2. **Beads: Structured Task DAG** ⭐
Beads provides:
- Dependency-aware task graph with hash-based IDs
- `bd ready` to find unblocked tasks automatically
- Hierarchical subtasks (`bd-a3f8.1`, `bd-a3f8.2`)
- Conflict-free merge via hash IDs

**Trinity gap**: We removed Task DAG (Phase 9, decision 2025-12-23) in favor of Claude Code's internal planning. But Beads offers a simpler, file-based alternative.

**Idea to borrow**:
- Consider a lightweight "Beads-like" file-based task tracking in agent workspaces
- The hash-based ID scheme prevents merge conflicts in multi-agent scenarios

### 3. **Mayor Pattern for Orchestration** ⭐
The Mayor is a **persistent orchestrator agent** with:
- Full workspace visibility
- Ability to spawn ephemeral workers (Polecats)
- Convoy-based work assignment and tracking

**Trinity comparison**: Our System Agent (`trinity-system`) is similar but:
- Gastown's Mayor is more deeply integrated with work tracking
- Mayor can spawn agents on-demand; Trinity requires pre-creation

**Idea to borrow**:
- Enhance System Agent with "spawn ephemeral agent" capability
- Add Convoy-like bundled work tracking (groups of tasks as a unit)

### 4. **Hooks for Context Injection** ⭐
Gastown uses Claude Code hooks (`.claude/hooks/`) to:
- Inject mail/messages at session start
- Prime agents with workspace context
- Persist state on compaction

**Trinity comparison**: We inject `CLAUDE.md` + Trinity prompt, but don't use hooks extensively.

**Idea to borrow**:
- Use Claude Code's `PreToolUse`/`PostToolUse` hooks for automatic activity logging
- Use `Stop` hooks to persist work state before context compaction

### 5. **Formula Templates**
TOML-based repeatable workflows in `.beads/formulas/`:
```toml
[formula.release]
steps = ["test", "build", "deploy"]
vars = { version = "" }
```

**Trinity comparison**: Our Process Engine is more sophisticated (YAML, 6 step types, approvals), but Gastown's formulas are simpler and agent-local.

**Idea to borrow**:
- Allow agents to define local "formulas" for quick task automation
- Lighter-weight than full Process definitions

---

## What Trinity Does Better

### 1. **Web UI & Visual Collaboration**
- Real-time Dashboard with agent network graph
- Timeline view of executions
- No CLI required for operations

Gastown is CLI-only, requiring tmux for multi-agent visibility.

### 2. **Enterprise Features**
- Multi-user authentication (email/admin)
- Agent sharing and permissions
- Audit logging (in progress)
- Process Engine with human approvals

Gastown is single-developer focused.

### 3. **Container Isolation**
- Each agent is a Docker container
- Network isolation, resource limits
- Credential injection, capability control

Gastown agents are local processes sharing the filesystem.

### 4. **Process Engine**
- BPMN-inspired workflow orchestration
- 6 step types: agent_task, human_approval, gateway, timer, notification, sub_process
- Real-time monitoring, analytics, cost tracking

Gastown has simpler formula templates without approval gates or conditional branching.

### 5. **MCP Integration**
- 21 MCP tools for programmatic agent control
- External Claude Code clients can orchestrate Trinity agents
- Agent-to-agent communication via MCP

Gastown uses CLI commands rather than a tool protocol.

---

## Specific Features to Consider Adopting

### Priority 1: Claude Code Hooks Integration
```yaml
# .claude/hooks/stop.yaml
- matcher:
    type: Stop
  action:
    command: ["gt", "persist", "--bead", "$BEAD_ID"]
```
This would allow Trinity agents to persist work state before context compaction.

### Priority 2: Convoy-like Work Bundles
Group multiple related tasks into a trackable unit:
```yaml
convoy:
  name: "Q1 Feature Release"
  tasks:
    - schedule_id: abc123
    - schedule_id: def456
  status: in_progress
  owner: trinity-system
```

### Priority 3: `gt ready` Equivalent
MCP tool to find "ready" work across agents:
```typescript
// find_ready_work() - returns unblocked tasks across fleet
{
  agent: "research-agent",
  pending_tasks: 3,
  blocked_tasks: 1,
  ready_tasks: 2  // No blockers
}
```

### Priority 4: Ephemeral Agent Spawning
Allow System Agent to spawn on-demand workers:
```
# Instead of pre-creating agents
system_agent: "Spawn a research agent for this specific task"
→ Creates temporary container
→ Runs task
→ Auto-cleans up
```

---

## Summary Table

| Feature | Gastown | Trinity | Winner |
|---------|---------|---------|--------|
| CLI Experience | ⭐⭐⭐⭐⭐ | ⭐⭐ | Gastown |
| Web UI | ❌ | ⭐⭐⭐⭐⭐ | Trinity |
| Work Persistence | ⭐⭐⭐⭐⭐ (git) | ⭐⭐⭐ (DB) | Gastown |
| Container Isolation | ❌ | ⭐⭐⭐⭐⭐ | Trinity |
| Enterprise Auth | ❌ | ⭐⭐⭐⭐ | Trinity |
| Workflow Engine | ⭐⭐ (formulas) | ⭐⭐⭐⭐⭐ (Process Engine) | Trinity |
| Developer UX | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Gastown |
| Scale Target | 20-30 agents | 50+ agents | Trinity |
| Learning Curve | Medium (CLI + Beads) | Low (Web UI) | Trinity |
| Multi-runtime | ⭐⭐⭐⭐ | ⭐⭐⭐ | Gastown |

---

## Recommendation

**Key ideas to adopt from Gastown:**

1. **Claude Code Hooks for State Persistence** - Use `Stop` hooks to checkpoint agent work before context compaction (Priority: HIGH)

2. **Convoy-like Work Bundles** - Group related tasks/executions into trackable units for multi-agent coordination (Priority: MEDIUM)

3. **Ephemeral Agent Spawning** - Let System Agent create temporary workers that auto-cleanup (Priority: MEDIUM)

4. **`ready` Work Discovery** - MCP tool to find unblocked work across the fleet (Priority: LOW)

These would enhance Trinity's orchestration capabilities while maintaining our web-first, enterprise-focused approach.

---

## Related Projects

- **Beads**: https://github.com/steveyegge/beads - Git-backed issue tracker (13k stars)
- **Gastown**: https://github.com/steveyegge/gastown - Multi-agent orchestration (6.3k stars)
