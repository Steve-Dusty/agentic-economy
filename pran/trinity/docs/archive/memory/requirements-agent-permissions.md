# Requirements: Agent-to-Agent Permissions System

> **Status**: ✅ Complete
> **Created**: 2025-12-10
> **Completed**: 2025-12-10
> **Priority**: High
> **Requirement ID**: 9.10

## Overview

Centralized permission system controlling which agents can communicate with other agents. Permissions are configured per-agent and enforced at the MCP layer.

## Problem Statement

Currently, any agent can call any other agent (subject only to user-level sharing rules). We need:
1. Fine-grained control over agent-to-agent communication
2. Agents to be aware of their permitted collaborators at startup
3. Centralized configuration in the UI

## Requirements

### 9.10.1 Agent Permission Configuration (UI)

**Status**: ✅ Complete

**Description**: Configure which agents an agent can access, via the agent detail page.

**Acceptance Criteria**:
- [x] New "Permissions" tab on AgentDetail.vue
- [x] List all other agents (same owner + shared) with checkboxes
- [x] Toggle to enable/disable access to each agent
- [x] Save permissions via API
- [x] Show agent status (running/stopped) and type in the list
- [x] Bulk actions: "Allow All" / "Allow None"

**UI Mockup**:
```
┌─────────────────────────────────────────────────────────┐
│ Permissions                                              │
├─────────────────────────────────────────────────────────┤
│ This agent can communicate with:                         │
│                                                          │
│ ☑ ruby-social-media-agent    🟢 Running   [Social Media] │
│ ☑ code-reviewer              🟢 Running   [Code Review]  │
│ ☐ data-analyst               ⚪ Stopped   [Analytics]    │
│ ☑ research-assistant         🟢 Running   [Research]     │
│                                                          │
│ [Allow All]  [Allow None]                    [Save]      │
└─────────────────────────────────────────────────────────┘
```

### 9.10.2 Agent Permissions Database Schema

**Status**: ✅ Complete

**Description**: Store agent-to-agent permissions in SQLite.

**Acceptance Criteria**:
- [x] New table `agent_permissions`
- [x] Schema: `(source_agent, target_agent, created_at, created_by)`
- [x] Primary key on `(source_agent, target_agent)`
- [x] Foreign key constraints to ensure valid agent names
- [x] Cascade delete when either agent is deleted

**Schema**:
```sql
CREATE TABLE agent_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_agent TEXT NOT NULL,      -- The agent making calls
    target_agent TEXT NOT NULL,      -- The agent being called
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,        -- User who set permission
    UNIQUE(source_agent, target_agent)
);

CREATE INDEX idx_agent_permissions_source ON agent_permissions(source_agent);
CREATE INDEX idx_agent_permissions_target ON agent_permissions(target_agent);
```

### 9.10.3 Agent Permissions API

**Status**: ✅ Complete

**Description**: CRUD API for managing agent permissions.

**Acceptance Criteria**:
- [x] `GET /api/agents/{name}/permissions` - List permitted agents
- [x] `PUT /api/agents/{name}/permissions` - Set permitted agents (full replacement)
- [x] `POST /api/agents/{name}/permissions/{target}` - Add single permission
- [x] `DELETE /api/agents/{name}/permissions/{target}` - Remove single permission
- [x] Only owner/admin can modify permissions
- [x] Validate target agents exist and are accessible to owner

**Request/Response**:
```json
// GET /api/agents/my-agent/permissions
{
  "source_agent": "my-agent",
  "permitted_agents": [
    {"name": "ruby-social-media-agent", "status": "running", "type": "social-media"},
    {"name": "code-reviewer", "status": "running", "type": "code-review"}
  ],
  "available_agents": [
    {"name": "data-analyst", "status": "stopped", "type": "analytics", "permitted": false}
  ]
}

// PUT /api/agents/my-agent/permissions
{
  "permitted_agents": ["ruby-social-media-agent", "code-reviewer"]
}
```

### 9.10.4 MCP `list_agents` Filtering

**Status**: ✅ Complete

**Description**: Filter `list_agents` results based on caller's permissions.

**Acceptance Criteria**:
- [x] When called by agent-scoped key, filter results to permitted agents only
- [x] When called by user-scoped key, return all accessible agents (no change)
- [x] Include caller's own agent in results (self-reference)
- [x] Log filtered vs total count for debugging

**Implementation Location**: `src/mcp-server/src/tools/agents.ts`

**Logic**:
```
If auth.scope == "agent":
    permitted = query agent_permissions WHERE source_agent = auth.agent_name
    return agents.filter(a => a.name in permitted OR a.name == auth.agent_name)
Else:
    return all accessible agents (existing behavior)
```

### 9.10.5 MCP `chat_with_agent` Enforcement

**Status**: ✅ Complete

**Description**: Block calls to non-permitted agents.

**Acceptance Criteria**:
- [x] Before proxying chat, verify target is in caller's permitted list
- [x] Return 403 with clear error message if not permitted
- [x] Audit log denied attempts
- [x] User-scoped keys bypass this check (existing behavior)

**Error Response**:
```json
{
  "error": "Permission denied",
  "message": "Agent 'my-agent' is not permitted to communicate with 'target-agent'",
  "code": "AGENT_PERMISSION_DENIED"
}
```

### 9.10.6 Startup Injection of Permitted Agents

**Status**: ✅ Complete (simplified)

**Description**: Inject list of permitted agents into agent prompt at startup.

**Acceptance Criteria**:
- [x] Extend Trinity injection to include permitted agents list
- [x] ~~Generate `.trinity/PERMITTED_AGENTS.md` with agent summaries~~ (Simplified: Added Agent Collaboration section to CLAUDE.md)
- [x] Append section to CLAUDE.md referencing MCP tools
- [x] ~~Include: agent name, type/description, status, example use case~~ (Agents discover via list_agents)
- [ ] Refresh on `/team-refresh` command (optional, Phase 2)

**Injected Content** (`.trinity/PERMITTED_AGENTS.md`):
```markdown
# Permitted Agents

You can communicate with the following agents using `mcp__trinity__chat_with_agent`.

## ruby-social-media-agent
- **Type**: Social Media Content Manager
- **Status**: Running
- **Use for**: Creating social media posts, scheduling content, media management

## code-reviewer
- **Type**: Code Review Assistant
- **Status**: Running
- **Use for**: PR reviews, security checks, code quality analysis

---
*To call an agent*: `mcp__trinity__chat_with_agent(agent_name="...", message="...")`
*To refresh this list*: `/team-refresh`
```

**CLAUDE.md Append**:
```markdown
## Agent Collaboration

You can collaborate with other agents. See `.trinity/PERMITTED_AGENTS.md` for your permitted collaborators.

Use `mcp__trinity__chat_with_agent(agent_name, message)` to delegate tasks.
```

### 9.10.7 Default Permission Behavior

**Status**: ✅ Complete

**Description**: Define default permissions for new agents.

**Options** (choose one):
- [ ] **Option A**: No agents permitted by default (most secure)
- [x] **Option B**: All same-owner agents permitted by default (most practical) ✅ IMPLEMENTED
- [ ] **Option C**: Configurable default in platform settings

**Recommendation**: Option B (same-owner agents) for better UX, with explicit opt-out.

**Implementation**:
- On agent creation, auto-populate `agent_permissions` with all same-owner agents (bidirectional)
- Owner can then remove unwanted permissions via the Permissions tab

---

## Non-Functional Requirements

### Security
- Only owner/admin can modify agent permissions
- Audit log all permission changes
- Audit log denied communication attempts

### Performance
- Permission check should add < 10ms to MCP calls
- Cache permissions in MCP server (invalidate on change)

### UX
- Clear visual indication of permitted vs blocked agents
- Confirmation before removing all permissions
- Show impact when deleting an agent (breaks permissions)

---

## Out of Scope (Future)

- Consolidated permissions management page (all agents in one view)
- Permission groups/roles (e.g., "research team" includes agents X, Y, Z)
- Time-based permissions (temporary access)
- Rate limiting per agent-to-agent pair
- Hierarchical permissions (orchestrator → workers)

---

## Implementation Order

1. **Database schema** (9.10.2) - Foundation
2. **Backend API** (9.10.3) - Enable configuration
3. **MCP enforcement** (9.10.4, 9.10.5) - Security first
4. **UI** (9.10.1) - User-facing configuration
5. **Startup injection** (9.10.6) - Agent awareness
6. **Defaults** (9.10.7) - Polish

---

## Testing

### API Tests
- [x] Create/read/update/delete permissions
- [x] Verify only owner can modify
- [x] Verify cascade delete on agent deletion

### MCP Tests
- [x] `list_agents` returns only permitted agents for agent-scoped keys
- [x] `chat_with_agent` blocked for non-permitted targets
- [x] User-scoped keys bypass filtering

### Integration Tests
- [x] Agent A (permitted to B) can chat with B
- [x] Agent A (not permitted to C) gets 403 when calling C
- [x] Startup injection includes correct permitted list

---

## Related Requirements

- 9.4 Agent-to-Agent Collaboration (existing, adds permissions layer)
- 9.8 Task DAG System (workplans may reference permitted agents)
- 2.5 Agent Sharing (user-level, separate from agent-level permissions)
