# Agent Operating Modes (MODE-001)

> **Status**: Not Started
> **Priority**: HIGH
> **Created**: 2026-02-18

## Overview

Simple three-mode system that controls what agents can do and where they work. Instead of complex tool allowlists, use intuitive modes that map to real-world workflows.

| Mode | Can Edit | Where | Use Case |
|------|----------|-------|----------|
| **Plan** | No | N/A | Research, analysis, review |
| **Dev** | Yes | Feature branch | Implementation (safe) |
| **Prod** | Yes | Main branch | Trusted operations |

## User Stories

| ID | Story |
|----|-------|
| MODE-001 | As an agent owner, I want to set my agent to Plan mode so it can research without making changes |
| MODE-002 | As an agent owner, I want Dev mode so the agent works on a branch and I review before merge |
| MODE-003 | As an agent owner, I want Prod mode for trusted agents that can work directly on main |
| MODE-004 | As a user, I want to override the mode per-task without changing agent defaults |

## Mode Definitions

### Plan Mode (Research Only)

Agent can read, search, analyze, and respond—but cannot modify files or run destructive commands.

**Implementation**: Uses Claude Code `--allowedTools` flag

```bash
--allowedTools "Read,Grep,Glob,WebFetch,WebSearch,Task"
```

**Blocked**: `Write`, `Edit`, `Bash` (except read-only commands)

**Use cases**:
- Code review
- Architecture analysis
- Research tasks
- Answering questions about codebase

### Dev Mode (Branch Isolation)

Agent has full capabilities but works on a feature branch. Changes require PR review before reaching main.

**Implementation**:
1. Agent works on branch: `agents/{agent-name}` or `task/{task-id}`
2. Agent commits and pushes to remote
3. Agent creates PR (optional, configurable)
4. Human reviews and merges

**Branch patterns** (configurable per agent):
```
agents/{agent-name}           # Persistent agent branch
agents/{agent-name}/{task-id} # Per-task branches
feature/{task-id}             # Generic feature branches
```

**Use cases**:
- Feature implementation
- Bug fixes
- Refactoring
- Any code changes that need review

### Prod Mode (Direct Access)

Agent works directly on main/current branch with full capabilities. Use for trusted agents only.

**Implementation**: No restrictions. Standard Claude Code execution.

**Use cases**:
- Hotfixes by trusted agents
- CI/CD automation
- System maintenance agents
- Agents you fully trust

## Database Schema

Add to `agent_ownership` table:

```sql
ALTER TABLE agent_ownership ADD COLUMN operating_mode TEXT DEFAULT 'dev';
-- Values: 'plan', 'dev', 'prod'

ALTER TABLE agent_ownership ADD COLUMN dev_branch_pattern TEXT DEFAULT 'agents/{agent-name}';
-- Pattern for Dev mode branches
```

Task-level override (existing `allowed_tools` in ParallelTaskRequest):

```python
class ParallelTaskRequest(BaseModel):
    message: str
    operating_mode: Optional[str] = None  # Override agent default
    # ... existing fields
```

## API Changes

### GET /api/agents/{name}

Response includes:
```json
{
  "operating_mode": "dev",
  "dev_branch_pattern": "agents/{agent-name}"
}
```

### PUT /api/agents/{name}/mode

Set operating mode:
```json
{
  "mode": "dev",
  "branch_pattern": "agents/{agent-name}/{task-id}"
}
```

### POST /api/agents/{name}/task

Override mode per-task:
```json
{
  "message": "Analyze the auth module",
  "operating_mode": "plan"
}
```

## Implementation

### Plan Mode

In `claude_code.py`, when building command:

```python
if operating_mode == "plan":
    cmd.extend(["--allowedTools", "Read,Grep,Glob,WebFetch,WebSearch,Task"])
```

### Dev Mode

In `claude_code.py` or agent startup:

1. Check current branch
2. If not on designated dev branch, checkout/create it
3. After execution, optionally create PR

```python
if operating_mode == "dev":
    branch = resolve_branch_pattern(agent.dev_branch_pattern, task_id)
    # Ensure agent is on correct branch before execution
    await ensure_branch(agent, branch)
    # After execution, optionally create PR
    if agent.auto_create_pr:
        await create_pull_request(agent, branch)
```

### Prod Mode

No changes to current behavior. Full access.

## UI

### Agent Header

```
┌─────────────────────────────────────────────────────────────┐
│  Agent: code-assistant                         [Running ●]  │
│                                                             │
│  Mode: [Plan ▼]  [Dev ▼]  [Prod ▼]                         │
│         ────                                                │
└─────────────────────────────────────────────────────────────┘
```

Simple segmented control or dropdown. One click to change mode.

### Settings Tab

```
Operating Mode
┌─────────────────────────────────────────────────────────────┐
│  ○ Plan   - Research only, no changes                       │
│  ● Dev    - Works on branch, PR required                    │
│  ○ Prod   - Direct access (trusted)                         │
│                                                             │
│  Branch Pattern: [agents/{agent-name}        ]              │
│  □ Auto-create PR after task completion                     │
└─────────────────────────────────────────────────────────────┘
```

### Task Modal (optional override)

When sending a task, optional mode override:

```
┌─────────────────────────────────────────────────────────────┐
│  New Task                                                   │
│                                                             │
│  Message: [Analyze the authentication flow     ]            │
│                                                             │
│  Mode: [Use agent default (Dev) ▼]                         │
│        ─────────────────────────                            │
│        Use agent default (Dev)                              │
│        Plan (research only)                                 │
│        Dev (branch isolation)                               │
│        Prod (direct access)                                 │
│                                                             │
│                              [Cancel]  [Send Task]          │
└─────────────────────────────────────────────────────────────┘
```

## Execution Flow

### Plan Mode Task

```
1. User sends task with mode=plan
2. Backend adds --allowedTools restriction to Claude Code
3. Agent researches, responds with analysis
4. No files modified
```

### Dev Mode Task

```
1. User sends task with mode=dev
2. Agent checks out/creates feature branch
3. Agent executes task with full capabilities
4. Agent commits changes to branch
5. Agent creates PR (if configured)
6. User reviews PR in GitHub/GitLab
7. User merges when satisfied
```

### Prod Mode Task

```
1. User sends task with mode=prod
2. Agent executes with full capabilities on current branch
3. Changes applied directly
```

## Public Access Enforcement

When an agent is accessed via public link (`/chat/:token`), **Plan mode is enforced automatically** regardless of the agent's default operating mode.

**Rationale**: External users should never be able to trigger code changes, commits, or destructive operations.

| Access Type | Mode Applied |
|-------------|--------------|
| Authenticated user (owner) | Agent's configured mode |
| Authenticated user (shared) | Agent's configured mode |
| Public link (external) | **Plan mode (forced)** |

**Implementation**:

In `routers/public.py`, when calling the agent:

```python
# Public access always uses Plan mode
payload = {
    "message": contextual_message,
    "operating_mode": "plan",  # Forced for public access
    "system_prompt": link.system_prompt_override,
    ...
}
```

**UI Indicator**: Public chat header should show "Research Mode" or a lock icon indicating restricted capabilities.

**Optional Future Enhancement**: Allow owner to explicitly enable Dev/Prod mode for public links (with strong warnings), for use cases like public coding assistants that need to demonstrate changes.

---

## Migration from READ_ONLY_MODE

The existing READ_ONLY_MODE spec (CFG-007) focuses on protecting agent's own code from modification. This is a different concern:

- **READ_ONLY_MODE**: Protect agent instructions/code from the agent itself
- **Operating Modes**: Control what the agent can do during task execution

These can coexist:
- An agent in Dev mode with read_only_mode=true can edit project files but not its own CLAUDE.md
- Plan mode restricts ALL writes, regardless of read_only_mode setting

## Files to Modify

| File | Change |
|------|--------|
| `src/backend/database.py` | Add `operating_mode`, `dev_branch_pattern` columns |
| `src/backend/models.py` | Add `operating_mode` to request models |
| `src/backend/routers/agents.py` | Add mode endpoint |
| `docker/base-image/agent_server/services/claude_code.py` | Apply mode restrictions |
| `src/frontend/src/components/AgentHeader.vue` | Add mode selector |
| `src/frontend/src/views/AgentDetail.vue` | Add mode settings |

## Acceptance Criteria

- [ ] Agent can be set to Plan/Dev/Prod mode via UI
- [ ] Plan mode restricts tools to read-only operations
- [ ] Dev mode works on configured branch pattern
- [ ] Prod mode has no restrictions
- [ ] Mode can be overridden per-task
- [ ] Mode persists across agent restarts
- [ ] Clear visual indicator of current mode in UI
- [ ] Public access enforces Plan mode automatically

## Future Enhancements

- [ ] Auto-create PR with summary of changes
- [ ] PR template configuration per agent
- [ ] Branch cleanup after PR merge
- [ ] Mode scheduling (Plan during review hours, Dev during work hours)
- [ ] Mode-based notifications (alert when Prod mode used)
