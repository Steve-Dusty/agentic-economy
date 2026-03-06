# Skills Management System

> **Status**: Requirements Draft (Revised 2026-01-25)
> **Priority**: Medium
> **Complexity**: Low (simplified from previous design)

## Overview

Platform-level skill management using **GitHub as the source of truth**. Skills are directories containing `SKILL.md` files (Claude Code's native format) that teach agents how to perform specific tasks.

**Key Principles**:
1. **GitHub is the library** - A GitHub repository contains all skills
2. **Simple copy injection** - Assigned skills are copied to agent's `~/.claude/skills/`
3. **Git for versioning** - No custom version control needed
4. **Database tracks assignments only** - Not skill content or metadata

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                  SKILLS ARCHITECTURE (GitHub-Based)                 │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   GitHub Repository (Source of Truth)                               │
│   e.g., github.com/org/trinity-skills-library                       │
│   ├── verification/                                                 │
│   │   ├── SKILL.md                                                  │
│   │   └── scripts/                                                  │
│   ├── tdd/                                                          │
│   │   └── SKILL.md                                                  │
│   ├── systematic-debugging/                                         │
│   │   └── SKILL.md                                                  │
│   ├── policy-code-review/                                           │
│   │   └── SKILL.md                                                  │
│   └── procedure-incident-response/                                  │
│       └── SKILL.md                                                  │
│                                                                     │
│   ─────────────────────────────────────────────────────────────    │
│                         git clone / pull                            │
│   ─────────────────────────────────────────────────────────────    │
│                                                                     │
│   Trinity Backend                                                   │
│   /data/skills-library/  (local clone)                              │
│   ├── verification/                                                 │
│   ├── tdd/                                                          │
│   └── ...                                                           │
│                                                                     │
│   ─────────────────────────────────────────────────────────────    │
│                    copy assigned skills                             │
│   ─────────────────────────────────────────────────────────────    │
│                                                                     │
│   Agent Containers                                                  │
│   ~/.claude/skills/           ← Only assigned skills                │
│   ├── verification/                                                 │
│   └── tdd/                                                          │
│                                                                     │
│   SQLite (Assignments Only)                                         │
│   ┌──────────────────────────────────────────────────────────────┐ │
│   │  agent_skills: agent_name, skill_name, assigned_at            │ │
│   │  (No skill content or metadata - GitHub is source of truth)   │ │
│   └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Skill Directory Structure

Skills follow Claude Code's native format - directories with a `SKILL.md` file:

```
verification/
├── SKILL.md              # Required - main instructions
├── scripts/              # Optional - bundled utilities
│   └── verify-output.py
├── prompts/              # Optional - reusable templates
│   └── checklist.md
└── examples/             # Optional - reference material
    └── good-verification.md
```

### SKILL.md Format

```yaml
---
name: verification
description: Ensures claims are backed by evidence. Use when completing tasks, reviewing work, or when asked to verify something.
allowed-tools: Read, Bash, Grep  # Optional - restrict tool access
---

# Verification Methodology

## Iron Rule
Never claim "done" without evidence...

## Process
1. Run the command
2. Show the output
3. Verify expected behavior
```

**Key fields**:
- `name` - Skill identifier (lowercase, hyphens)
- `description` - Claude uses this to decide when to apply the skill
- `allowed-tools` - Optional tool restrictions when skill is active

---

## Skill Types (by Convention)

Skills can serve different purposes based on naming convention:

| Type | Naming | Behavior | Example |
|------|--------|----------|---------|
| **Policy** | `policy-*` | Always-active rules | `policy-code-review`, `policy-data-retention` |
| **Procedure** | `procedure-*` | Step-by-step instructions | `procedure-incident-response` |
| **Methodology** | (no prefix) | Guidance on approach | `verification`, `tdd`, `systematic-debugging` |

Claude Code automatically discovers and applies skills based on their `description` field - no explicit invocation needed.

---

## Configuration

### Platform Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `skills_library_url` | GitHub repository URL | None (feature disabled) |
| `skills_library_branch` | Branch to track | `main` |
| `skills_auto_sync` | Auto-pull frequency | `on_demand` |

**Settings UI** (Admin → Settings):
```
Skills Library
├── Repository URL: [github.com/org/trinity-skills-library]
├── Branch: [main]
├── Auto-sync: [On-demand ▼] (On-demand / Hourly / Daily / On agent start)
└── [Sync Now] [Test Connection]
```

### Authentication

Uses existing GitHub PAT from platform settings for private repositories.

---

## Data Model

### Table: `agent_skills`

Tracks which skills are assigned to which agents. **Does not store skill content** - content lives in GitHub.

```sql
CREATE TABLE agent_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    skill_name TEXT NOT NULL,         -- Directory name in library
    assigned_by TEXT NOT NULL,        -- User ID
    assigned_at TEXT NOT NULL,
    UNIQUE(agent_name, skill_name)
);

CREATE INDEX idx_agent_skills_agent ON agent_skills(agent_name);
CREATE INDEX idx_agent_skills_skill ON agent_skills(skill_name);
```

### No Skills Metadata Table

Unlike the previous design, we don't store skill metadata in the database. The GitHub repository **is** the source of truth. Available skills are discovered by scanning the local clone.

---

## API Endpoints

### Skills Library

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/skills` | List available skills (scans library directory) | User |
| GET | `/api/skills/{name}` | Get skill details + SKILL.md content | User |
| POST | `/api/skills/sync` | Git pull to update library | Admin |
| GET | `/api/skills/status` | Library sync status (last sync, commit) | User |

### Agent Skill Assignment

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/agents/{name}/skills` | List assigned skills | Owner/Shared |
| PUT | `/api/agents/{name}/skills` | Update assigned skills (bulk) | Owner |
| POST | `/api/agents/{name}/skills/inject` | Re-copy skills to running agent | Owner |

### Request/Response Models

```python
# Available skill (from library scan)
class SkillInfo(BaseModel):
    name: str                    # Directory name
    description: str             # From SKILL.md frontmatter
    has_scripts: bool            # Has scripts/ directory
    skill_type: str              # Inferred: policy/procedure/methodology

# Skill with content
class SkillDetail(SkillInfo):
    content: str                 # Full SKILL.md content
    files: List[str]             # List of files in skill directory

# Agent skills update
class AgentSkillsUpdate(BaseModel):
    skills: List[str]            # List of skill names to assign

# Agent skills response
class AgentSkillsResponse(BaseModel):
    agent_name: str
    assigned_skills: List[str]
    available_skills: List[SkillInfo]
```

---

## Skill Injection

### When Injection Occurs

1. **Agent Start** - Copy assigned skills to container
2. **Manual Sync** - "Inject Skills" button in UI
3. **Bulk Sync** - Admin action to update all agents

### Injection Process

```python
async def inject_skills_to_agent(agent_name: str) -> int:
    """
    Copy assigned skills from library to agent's ~/.claude/skills/.
    Returns count of skills injected.
    """
    library_path = Path("/data/skills-library")
    assigned_skills = db.get_agent_skills(agent_name)

    # Clear existing skills directory
    await exec_in_container(
        agent_name,
        "rm -rf /home/developer/.claude/skills && mkdir -p /home/developer/.claude/skills"
    )

    injected = 0
    for skill_name in assigned_skills:
        skill_path = library_path / skill_name
        if skill_path.exists() and (skill_path / "SKILL.md").exists():
            # Copy entire skill directory to agent
            await copy_directory_to_agent(
                agent_name,
                skill_path,
                f"/home/developer/.claude/skills/{skill_name}"
            )
            injected += 1
        else:
            logger.warning(f"Skill {skill_name} not found in library")

    # Fix ownership
    await exec_in_container(
        agent_name,
        "chown -R developer:developer /home/developer/.claude/skills"
    )

    return injected
```

### Library Sync Process

```python
async def sync_skills_library() -> dict:
    """
    Git pull to update local skills library.
    Returns sync status.
    """
    library_path = Path("/data/skills-library")
    settings = get_settings()

    if not settings.skills_library_url:
        raise ValueError("Skills library URL not configured")

    if not library_path.exists():
        # First time: clone
        await run_git([
            "clone",
            "--branch", settings.skills_library_branch,
            "--single-branch",
            settings.skills_library_url,
            str(library_path)
        ])
        return {"action": "cloned", "commit": get_head_commit(library_path)}
    else:
        # Update: pull
        old_commit = get_head_commit(library_path)
        await run_git(["pull"], cwd=library_path)
        new_commit = get_head_commit(library_path)

        return {
            "action": "pulled",
            "old_commit": old_commit,
            "new_commit": new_commit,
            "changed": old_commit != new_commit
        }
```

---

## UI Components

### Skills Tab in Agent Detail

```
┌─────────────────────────────────────────────────────────────────┐
│  Skills                                      [Inject to Agent]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Assigned Skills:                                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ [✓] verification                                         │    │
│  │     Ensures claims are backed by evidence                │    │
│  │                                                          │    │
│  │ [✓] systematic-debugging                                 │    │
│  │     Root cause investigation methodology                 │    │
│  │                                                          │    │
│  │ [✓] tdd                                                  │    │
│  │     Test-driven development cycle                        │    │
│  │                                                          │    │
│  │ [ ] code-review                                          │    │
│  │     Receiving and applying code review feedback          │    │
│  │                                                          │    │
│  │ [ ] policy-code-review                                   │    │
│  │     [POLICY] Code review requirements                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  [Save]                                                          │
│                                                                  │
│  ℹ️ Skills from: github.com/org/trinity-skills-library           │
│     Last synced: 2 hours ago (abc1234)                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Settings → Skills Library (Admin)

```
┌─────────────────────────────────────────────────────────────────┐
│  Skills Library                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Repository URL:                                                 │
│  [github.com/org/trinity-skills-library                    ]    │
│                                                                  │
│  Branch:                                                         │
│  [main                                                     ]    │
│                                                                  │
│  Auto-sync:                                                      │
│  [On agent start ▼]                                             │
│   • On-demand only                                               │
│   • On agent start                                               │
│   • Hourly                                                       │
│   • Daily                                                        │
│                                                                  │
│  Status: ✅ Connected                                            │
│  Last sync: 2026-01-25 14:30 UTC                                │
│  Commit: abc1234 - "Add incident response procedure"            │
│  Skills available: 12                                            │
│                                                                  │
│  [Test Connection]  [Sync Now]  [Save]                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## MCP Tools (Simplified)

Reduced from 10 tools to 4 essential ones:

### `list_skills`
```typescript
{
  name: "list_skills",
  description: "List available skills from the library",
  parameters: {},
  returns: "Array of skill objects with name, description, skill_type"
}
```

### `get_skill`
```typescript
{
  name: "get_skill",
  description: "Get skill details including SKILL.md content",
  parameters: {
    skill_name: { type: "string", required: true }
  },
  returns: "Skill object with content"
}
```

### `assign_skill_to_agent`
```typescript
{
  name: "assign_skill_to_agent",
  description: "Assign a skill to an agent",
  parameters: {
    agent_name: { type: "string", required: true },
    skill_name: { type: "string", required: true }
  },
  returns: "Assignment confirmation"
}
```

### `sync_agent_skills`
```typescript
{
  name: "sync_agent_skills",
  description: "Re-inject assigned skills to agent container",
  parameters: {
    agent_name: { type: "string", required: true }
  },
  returns: "Sync confirmation with skill count"
}
```

**Removed tools** (handled by GitHub):
- `create_skill` → Create via GitHub PR
- `update_skill` → Edit via GitHub
- `delete_skill` → Delete via GitHub
- `scan_skills_library` → Automatic on sync
- `execute_procedure` → Use agent scheduling instead

---

## Auto-Update Strategies

| Strategy | Trigger | Best For |
|----------|---------|----------|
| **On-demand** | Admin clicks "Sync Now" | Controlled environments |
| **On agent start** | Each agent start pulls latest | Always-fresh skills |
| **Hourly/Daily** | Scheduled background job | Balance of freshness and load |

### Update Flow

```
1. Admin updates skill in GitHub (commit/PR)
2. Trinity syncs library (manual or scheduled)
3. Admin triggers "Sync All Agents" or individual "Inject"
4. Running agents get updated skills
```

**Note**: Unlike the previous symlink approach, skill updates require re-injection to take effect. This is a reasonable trade-off for simpler architecture.

---

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Add `skills_library_url`, `skills_library_branch` to system settings
- [ ] Implement `sync_skills_library()` - git clone/pull
- [ ] Implement `list_available_skills()` - scan library directory
- [ ] Add `agent_skills` table (assignments only)

### Phase 2: API Endpoints
- [ ] `GET /api/skills` - list available skills
- [ ] `GET /api/skills/{name}` - get skill content
- [ ] `POST /api/skills/sync` - trigger library sync
- [ ] `GET/PUT /api/agents/{name}/skills` - assignments
- [ ] `POST /api/agents/{name}/skills/inject` - copy to agent

### Phase 3: Injection
- [ ] Copy skill directories on agent start
- [ ] Manual inject endpoint for running agents
- [ ] Bulk inject for all agents (admin action)

### Phase 4: UI
- [ ] Skills Library settings in Admin → Settings
- [ ] Skills tab in Agent Detail (checkbox assignment)
- [ ] "Inject to Agent" button

### Phase 5: MCP Tools (Optional)
- [ ] `list_skills`, `get_skill`
- [ ] `assign_skill_to_agent`, `sync_agent_skills`

---

## Migration from Current Implementation

The current implementation uses Docker volumes and symlinks. To migrate:

1. **Export current skills**: Copy from volume to GitHub repo
2. **Configure library URL**: Point to new GitHub repo
3. **Update agents**: Re-inject skills using new system
4. **Remove old infrastructure**: Delete volume, symlink code

**Files to modify**:
- Remove `trinity-skills-library` volume from docker-compose.yml
- Simplify `skill_service.py` - remove symlink logic
- Simplify `lifecycle.py` - use copy instead of symlink
- Update database schema - remove `skills` metadata table

---

## Security Considerations

1. **GitHub PAT** - Use existing credential for private repos
2. **Read-only injection** - Agents cannot modify the library
3. **Owner-only assignment** - Only agent owners can assign skills
4. **Path validation** - Prevent directory traversal in skill names
5. **Content sanitization** - Skills are markdown, no executable injection risk

---

## File Structure

```
# Backend
src/backend/
├── routers/
│   └── skills.py              # Skills API endpoints (simplified)
├── services/
│   └── skill_service.py       # Library sync, injection (simplified)
├── db/
│   └── skills.py              # Agent skill assignments only

# Frontend
src/frontend/src/
├── components/
│   └── SkillsPanel.vue        # Agent skills tab (simplified)

# MCP Server
src/mcp-server/src/tools/
└── skills.ts                  # 4 MCP tools (reduced from 10)

# Local library clone (created on first sync)
/data/skills-library/
├── verification/
├── tdd/
└── ...
```

---

## What's NOT in This Design

Intentionally excluded for simplicity:

- **Skills metadata table** - GitHub is the source of truth
- **System Agent as curator** - Use GitHub PRs instead
- **Docker volume** - Simple directory clone
- **Symlinks** - Direct copy is simpler
- **Version tracking in DB** - Git handles this
- **Skill categories/types in DB** - Inferred from naming convention
- **Default skills auto-assignment** - Configure per-agent explicitly
- **Process Engine integration** - Future enhancement if needed

---

## Related Documentation

- [Claude Code Skills](https://docs.anthropic.com/en/docs/claude-code/skills) - Native skill format
- [Trinity Agent Lifecycle](docs/memory/feature-flows/agent-lifecycle.md)
- [GitHub Sync](docs/memory/feature-flows/github-sync.md) - Similar pattern for agent templates
