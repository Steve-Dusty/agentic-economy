# Feature: Skill Injection

## Overview

Skill Injection copies assigned skill files (SKILL.md) from the platform's skills library into a running agent's `.claude/skills/` directory and updates the agent's `CLAUDE.md` with a "Platform Skills" section. This enables agents to access methodology guides, procedures, and policies at runtime without restarting, and allows agents to answer questions like "what skills do you have?"

## User Story

As an agent owner, I want to inject assigned skills into a running agent so that the agent can immediately access new methodologies without requiring a restart.

## Entry Points

- **UI**: `src/frontend/src/components/SkillsPanel.vue:16` - "Inject to Agent" button (visible when agent status is "running")
- **API**: `POST /api/agents/{agent_name}/skills/inject`
- **Automatic**: `services/agent_service/lifecycle.py:261` - Called during agent startup after Trinity meta-prompt injection

## Frontend Layer

### Components

**SkillsPanel.vue** - Skills assignment panel in Agent Detail view

| Line | Element | Description |
|------|---------|-------------|
| 14-25 | `<button>` | "Inject to Agent" button, visible only when `agentStatus === 'running'` |
| 17 | `:disabled` | Disabled when `injecting` is true or `assignedSkills.length === 0` |
| 173 | `injecting` | Ref tracking injection in-progress state |
| 268-291 | `injectSkills()` | Async method that triggers skill injection |

### State Management

No Pinia store - component manages local state with Vue refs:

```javascript
// SkillsPanel.vue:173
const injecting = ref(false)

// SkillsPanel.vue:180-181
const assignedSkills = ref([])
const selectedSkills = ref(new Set())
```

### API Calls

```javascript
// SkillsPanel.vue:271-275
const response = await axios.post(
  `/api/agents/${props.agentName}/skills/inject`,
  {},
  { headers: authStore.authHeader }
)
```

**Response handling (lines 277-283)**:
- Success: Shows "Injected X skills" message
- Partial: Shows "Injected X skills, Y failed" message
- Error: Shows error detail from response

## Backend Layer

### Endpoint

**File**: `src/backend/routers/skills.py:134-150`

```python
@router.post("/agents/{agent_name}/skills/inject")
async def inject_skills(
    agent_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Inject assigned skills into a running agent.
    Copies all assigned skills to the agent's .claude/skills/ directory.
    Agent must be running.
    """
    result = await skill_service.inject_skills(agent_name)
    return result
```

### Business Logic

**File**: `src/backend/services/skill_service.py:300-374`

`inject_skills()` method flow:

1. **Get skill names** (line 317-318): If no skill names provided, fetch from DB
   ```python
   skill_names = db.get_agent_skill_names(agent_name)
   ```

2. **Early return if empty** (lines 320-325): Return success with 0 skills if no assignments

3. **Get agent client** (line 327): Create HTTP client for agent container
   ```python
   client = get_agent_client(agent_name)
   ```

4. **Loop through skills** (lines 332-362): For each skill:
   - Get skill content from library (`self.get_skill(skill_name)`)
   - Write to agent via HTTP PUT
   - Track success/failure counts

5. **Update CLAUDE.md** (lines 364-367): If any skills were injected successfully:
   ```python
   if success_count > 0:
       injected_skills = [name for name, res in results.items() if res.get("success")]
       await self._update_claude_md_skills_section(client, injected_skills)
   ```

6. **Return results** (lines 369-374): Summary with counts and per-skill status

### Database Operations

**File**: `src/backend/db/skills.py:55-73`

```python
def get_agent_skill_names(self, agent_name: str) -> List[str]:
    """Get skill names assigned to an agent."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT skill_name
            FROM agent_skills
            WHERE agent_name = ?
            ORDER BY skill_name
        """, (agent_name,))
        return [row["skill_name"] for row in cursor.fetchall()]
```

### Skill Library Operations

**File**: `src/backend/services/skill_service.py:246-265`

```python
def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
    """Get full details for a specific skill including content."""
    skill_file = self.library_path / ".claude" / "skills" / skill_name / "SKILL.md"

    if not skill_file.exists():
        return None

    content = skill_file.read_text()
    info = self._parse_skill_info(skill_name, skill_file)
    info["content"] = content
    return info
```

Skills library path: `/data/skills-library/.claude/skills/{name}/SKILL.md`

## Agent Layer

### AgentClient Methods

**File**: `src/backend/services/agent_client.py`

| Method | Lines | Purpose |
|--------|-------|---------|
| `read_file()` | 470-506 | Read file content from agent workspace (used to read CLAUDE.md) |
| `write_file()` | 508-547 | Write file content to agent workspace |

```python
# read_file() - src/backend/services/agent_client.py:470-506
async def read_file(self, path: str, timeout: float = 30.0) -> dict:
    """Read content from a file in the agent's workspace."""
    encoded_path = urllib.parse.quote(path, safe='')
    response = await self.get(
        f"/api/files/download?path={encoded_path}",
        timeout=timeout
    )
    if response.status_code == 200:
        return {"success": True, "content": response.text}
    elif response.status_code == 404:
        return {"success": True, "content": None, "not_found": True}
    # ... error handling
```

```python
# write_file() - src/backend/services/agent_client.py:508-547
async def write_file(self, path: str, content: str, timeout: float = 30.0) -> dict:
    """Write content to a file in the agent's workspace."""
    encoded_path = urllib.parse.quote(path, safe='')
    response = await self.put(
        f"/api/files?path={encoded_path}",
        json={"content": content},
        timeout=timeout
    )
```

### Agent Server File Endpoints

**File**: `docker/base-image/agent_server/routers/files.py`

| Endpoint | Lines | Purpose |
|----------|-------|---------|
| `GET /api/files/download` | 112-153 | Download file content (used to read CLAUDE.md) |
| `PUT /api/files` | 314-371 | Create/update file content (used for skills and CLAUDE.md) |

```python
# GET /api/files/download - docker/base-image/agent_server/routers/files.py:112-153
@router.get("/api/files/download")
async def download_file(path: str):
    """Download a file from the workspace."""
    allowed_base = Path("/home/developer")
    # ... path resolution and security checks
    content = requested_path.read_text(encoding='utf-8', errors='replace')
    return PlainTextResponse(content=content)
```

```python
# PUT /api/files - docker/base-image/agent_server/routers/files.py:314-371
@router.put("/api/files")
async def update_file(path: str, request: FileUpdateRequest):
    """Update or create a file's content in the workspace."""
    allowed_base = Path("/home/developer")
    # ... path resolution and security checks
    requested_path.parent.mkdir(parents=True, exist_ok=True)
    requested_path.write_text(request.content, encoding='utf-8')
```

**Target paths in agent**:
- Skills: `/home/developer/.claude/skills/{skill_name}/SKILL.md`
- CLAUDE.md: `/home/developer/workspace/CLAUDE.md`

### CLAUDE.md Skills Section Update

**File**: `src/backend/services/skill_service.py:376-435`

After skill files are written, the service updates the agent's `workspace/CLAUDE.md` with a "Platform Skills" section. This enables the agent to answer questions like "what skills do you have?" without scanning the filesystem.

```python
async def _update_claude_md_skills_section(
    self,
    client,
    skill_names: List[str]
) -> None:
    """Update CLAUDE.md with a Platform Skills section."""
    # 1. Read current CLAUDE.md
    result = await client.read_file("workspace/CLAUDE.md")
    content = result.get("content") or ""

    # 2. Build skills section
    skills_list = "\n".join([f"- `/{skill}` - Use with /{skill} command" for skill in sorted(skill_names)])
    skills_section = f"""

## Platform Skills

This agent has the following skills installed in `~/.claude/skills/`:

{skills_list}

Use these skills by invoking their slash commands (e.g., `/{skill_names[0]}`).
"""

    # 3. Remove existing section if present
    if "## Platform Skills" in content:
        # Find and remove existing section
        ...

    # 4. Append new section and write back
    content = content.rstrip() + skills_section
    await client.write_file("workspace/CLAUDE.md", content)
```

**Example CLAUDE.md section**:
```markdown
## Platform Skills

This agent has the following skills installed in `~/.claude/skills/`:

- `/clip-video` - Use with /clip-video command
- `/commit` - Use with /commit command
- `/verification` - Use with /verification command

Use these skills by invoking their slash commands (e.g., `/clip-video`).
```

## Automatic Injection on Startup

### Lifecycle Integration

**File**: `src/backend/services/agent_service/lifecycle.py:174-212`

```python
async def inject_assigned_skills(agent_name: str) -> dict:
    """
    Inject assigned skills into a running agent.
    Called after agent startup to push any skills assigned in the Skills tab.
    """
    from database import db

    # Get assigned skills
    skill_names = db.get_agent_skill_names(agent_name)

    if not skill_names:
        logger.debug(f"No assigned skills for agent {agent_name}")
        return {"status": "skipped", "reason": "no_skills"}

    logger.info(f"Injecting {len(skill_names)} skills into agent {agent_name}: {skill_names}")

    # Inject skills via skill_service
    result = await skill_service.inject_skills(agent_name, skill_names)

    return result
```

### Startup Call Order

**File**: `src/backend/services/agent_service/lifecycle.py:260-272`

```python
# After Trinity meta-prompt and credentials injection:
# Inject assigned skills from the Skills page
skills_result = await inject_assigned_skills(agent_name)
skills_status = skills_result.get("status", "unknown")

return {
    "message": f"Agent {agent_name} started",
    "trinity_injection": trinity_status,
    "credentials_injection": credentials_status,
    "skills_injection": skills_status,
    "skills_result": skills_result
}
```

## Data Flow Diagram

```
User clicks "Inject to Agent"
         |
         v
SkillsPanel.vue:injectSkills()
         |
         v
POST /api/agents/{name}/skills/inject
         |
         v
routers/skills.py:inject_skills()
         |
         v
skill_service.inject_skills()
         |
         +---> db.get_agent_skill_names()    # Get assigned skill names
         |           |
         |           v
         |     agent_skills table
         |
         +---> skill_service.get_skill()     # For each skill
         |           |
         |           v
         |     /data/skills-library/.claude/skills/{name}/SKILL.md
         |
         +---> agent_client.write_file()     # Write SKILL.md to agent
         |           |
         |           v
         |     PUT /api/files?path=.claude/skills/{name}/SKILL.md
         |           |
         |           v
         |     Agent creates /home/developer/.claude/skills/{name}/SKILL.md
         |
         +---> _update_claude_md_skills_section()   # Update CLAUDE.md
                     |
                     +---> agent_client.read_file()      # Read existing CLAUDE.md
                     |           |
                     |           v
                     |     GET /api/files/download?path=workspace/CLAUDE.md
                     |
                     +---> agent_client.write_file()     # Write updated CLAUDE.md
                                 |
                                 v
                           PUT /api/files?path=workspace/CLAUDE.md
                                 |
                                 v
                           Agent updates /home/developer/workspace/CLAUDE.md
                                       with "## Platform Skills" section
```

## Response Format

### Success Response

```json
{
  "success": true,
  "skills_injected": 3,
  "skills_failed": 0,
  "results": {
    "verification": {"success": true},
    "systematic-debugging": {"success": true},
    "tdd": {"success": true}
  }
}
```

### Partial Success Response

```json
{
  "success": false,
  "skills_injected": 2,
  "skills_failed": 1,
  "results": {
    "verification": {"success": true},
    "systematic-debugging": {"success": true},
    "missing-skill": {"success": false, "error": "Skill not found in library"}
  }
}
```

## Error Handling

| Error Case | HTTP Status | Message | Handler |
|------------|-------------|---------|---------|
| Agent not running | 500 | Agent not reachable | `AgentClientError` raised |
| Skill not in library | 200 | Skill not found in library | Per-skill error in results |
| File write fails | 200 | Write failed | Per-skill error in results |
| No skills assigned | 200 | No skills to inject | `skills_injected: 0` |
| Connection timeout | 500 | Request timed out | `AgentNotReachableError` |

## Security Considerations

1. **Authorization**: Requires authenticated user via `get_current_user` dependency
2. **Path Traversal Prevention**: Agent server validates all paths are within `/home/developer`
3. **Protected Paths**: `.trinity`, `.git`, `.env` are edit-protected in agent server
4. **Skills Content**: Only read from trusted skills library, not user input
5. **Agent Access**: Backend communicates with agent via internal Docker network

## Related Flows

| Flow | Relationship |
|------|--------------|
| **Upstream**: [agent-skill-assignment.md](agent-skill-assignment.md) | User assigns skills before injection |
| **Upstream**: [skills-crud.md](skills-crud.md) | Skills must exist in library |
| **Downstream**: [agent-lifecycle.md](agent-lifecycle.md) | Injection called during agent start |
| **Related**: [mcp-skill-tools.md](mcp-skill-tools.md) | MCP `sync_agent_skills` tool uses same service |

## Testing

### Prerequisites
- Trinity platform running locally
- Skills library configured and synced
- At least one agent created
- At least one skill in the library

### Test Steps

1. **Assign Skills to Agent**
   - Navigate to Agent Detail > Skills tab
   - Check one or more skills
   - Click Save
   - **Expected**: "Skills saved successfully" message

2. **Start Agent**
   - Click Start button if agent is stopped
   - **Expected**: Agent starts, skills auto-injected

3. **Verify Auto-Injection**
   - Check agent startup response includes `skills_injection: "success"`
   - SSH into agent or use Files tab
   - Verify `.claude/skills/{name}/SKILL.md` exists
   - **Expected**: All assigned skills present in agent

4. **Manual Injection (Hot Reload)**
   - With agent running, assign new skill
   - Click Save, then "Inject to Agent"
   - **Expected**: "Injected X skills" message
   - **Verify**: New skill file present in agent

5. **Injection with Missing Skill**
   - Assign a skill that doesn't exist in library
   - Click "Inject to Agent"
   - **Expected**: Partial success message, error in results

### Edge Cases
- Inject with 0 skills assigned: Should succeed with `skills_injected: 0`
- Inject to stopped agent: Should fail with connection error
- Inject very large skill file: Should succeed (no size limit in skill service)

### Status
Working (Implemented 2026-01-25)

---

## Revision History

| Date | Change |
|------|--------|
| 2026-01-25 | Added CLAUDE.md "Platform Skills" section update - `_update_claude_md_skills_section()` method, `AgentClient.read_file()` method, updated data flow diagram |
| 2026-01-25 | Initial documentation |
