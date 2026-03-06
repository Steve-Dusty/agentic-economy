# Feature: Agent Lifecycle

> **Updated**: 2026-03-03 - **SUB-002: Env-var-based subscription tokens**: Subscription tokens now injected as `CLAUDE_CODE_OAUTH_TOKEN` env var at container creation/recreation, replacing the old SUB-001 post-start `.credentials.json` file injection. Removed `inject_subscription_on_start()` call from `start_agent_internal()`. `check_api_key_env_matches()` now performs three-way env var check (subscription token, API key, or neither). `recreate_container_with_updated_config()` manages `CLAUDE_CODE_OAUTH_TOKEN` env var directly.
>
> **Previous (2026-03-02)**: **Subscription credential priority fix (Issue #57)**: `check_api_key_env_matches()` now detects subscription + API key conflict. Container recreation removes `ANTHROPIC_API_KEY` when subscription assigned. Authentication Model corrected: API key takes precedence over OAuth in Claude Code.
>
> **Previous (2026-03-01)**: **Agent Rename (RENAME-001)**: Added ability to rename agents via UI (pencil icon in AgentHeader) or MCP (`rename_agent` tool). Renames container, updates all 17 database tables atomically, broadcasts WebSocket event. System agents protected.
>
> **Previous (2026-02-24)**: **Async Docker Operations (DOCKER-001)**: All blocking Docker SDK calls now wrapped with `services/docker_utils.py` async wrappers. Prevents event loop freezing during container start/stop/delete. See [async-docker-operations.md](async-docker-operations.md) for full details.
>
> **Previous (2026-01-26)**: **UX: Unified Start/Stop Toggle**: Replaced separate Start/Stop buttons with `RunningStateToggle.vue` component across all pages (AgentHeader.vue, Agents.vue, AgentNode.vue). Added `toggleAgentRunning()` to agents.js and network.js stores.
>
> **Previous (2026-01-14)** - **Security Fixes**:
> - **Auth on Lifecycle Endpoints (HIGH)**: `start_agent_endpoint`, `stop_agent_endpoint`, `get_agent_logs_endpoint` now use `AuthorizedAgentByName` dependency instead of plain `get_current_user` - prevents unauthorized users from starting/stopping agents they don't own
> - **Container Security Consistency (HIGH)**: All container creation paths now ALWAYS apply baseline security (`cap_drop=['ALL']`, AppArmor, noexec tmpfs). Added `RESTRICTED_CAPABILITIES` and `FULL_CAPABILITIES` constants in `lifecycle.py` for consistent security settings.
>
> **Previous (2026-01-12)**: Database Batch Queries (N+1 Fix): `get_accessible_agents()` now uses `db.get_all_agent_metadata()` batch query - reduced from 8-10 queries per agent to 2 total queries. Combined with Docker stats optimization for <50ms response time.
>
> **Previous (2025-12-31)**: Updated for settings service and AgentClient refactoring. API key retrieval now uses `services/settings_service.py`. Trinity injection uses centralized `AgentClient` with built-in retry logic.

## Overview
Complete lifecycle management for Trinity agents: create, start, stop, and delete Docker containers with credential injection (CRED-002), skill injection, network isolation, Trinity meta-prompt injection, and WebSocket broadcasts.

## User Story
As a Trinity platform user, I want to create, start, stop, and delete agents so that I can manage isolated Claude Code execution environments with custom configurations, credentials, and Trinity planning capabilities.

---

## Entry Points

### Create Agent
- **UI**: `src/frontend/src/views/Agents.vue:34-39` - "Create Agent" button
- **API**: `POST /api/agents`

### Start/Stop Agent (Toggle)
- **UI**: Unified toggle control across all pages (all use `size="sm"` as of 2026-02-18):
  - `src/frontend/src/components/AgentHeader.vue:38-43` - Detail page header
  - `src/frontend/src/views/Agents.vue:242-247` - Agents list page
  - `src/frontend/src/components/AgentNode.vue` - Dashboard network view
- **Component**: `src/frontend/src/components/RunningStateToggle.vue` - Reusable toggle (default size changed from 'md' to 'sm')
- **API**: `POST /api/agents/{agent_name}/start` or `POST /api/agents/{agent_name}/stop`

### Delete Agent
- **UI**: `src/frontend/src/views/AgentDetail.vue:137-146` - Delete button (trash icon)
- **API**: `DELETE /api/agents/{agent_name}`

### Rename Agent (RENAME-001)
- **UI**: `src/frontend/src/components/AgentHeader.vue` - Pencil icon next to agent name (visible for owners/admins, not system agents)
- **API**: `PUT /api/agents/{agent_name}/rename`
- **MCP**: `rename_agent` tool with `name` and `new_name` parameters

---

## Frontend Layer

### Components

**Running State Toggle** - `src/frontend/src/components/RunningStateToggle.vue` (NEW 2026-01-26)
- Unified toggle component replacing separate Start/Stop buttons
- Props: `modelValue` (boolean), `loading`, `disabled`, `showLabel`, `size` (sm/md/lg, default: 'sm' as of 2026-02-18)
- Events: `update:modelValue`, `toggle`
- Shows "Running" (green) or "Stopped" (gray) state
- Loading spinner overlay during API calls
- **2026-02-18**: Default size changed from 'md' to 'sm' for consistency across all toggle locations

**Agents List View** - `src/frontend/src/views/Agents.vue`
- Line 34-39: Create Agent button opens modal
- Lines 187-204: RunningStateToggle for each agent card
- Line 391-405: `toggleAgentRunning()` method (unified toggle)

**Agent Detail View** - `src/frontend/src/views/AgentDetail.vue`
- Lines 28-59: AgentHeader with `@toggle="toggleRunning"` event
- Line 275: Default tab is now 'tasks' (changed from 'info' in UI-001)
- Lines 425-434: `toggleRunning()` function (calls start or stop based on status)
- Lines 44-49: Delete button passed to AgentHeader (conditional on `agent.can_delete`)
- Lifecycle methods via composable (see below)

**Agent Header** - `src/frontend/src/components/AgentHeader.vue`
- **Layout (UI-001)**: 3-row structure - Row 1 (Identity + Actions), Row 2 (Settings + Stats), Row 3 (Git)
- Lines 38-43: RunningStateToggle (size: sm) in Row 1 (changed from lg to sm on 2026-02-18)
- Lines 65-70: AutonomyToggle (size: sm) in Row 2 (changed from md to sm on 2026-02-18)
- Lines 74-79: ReadOnlyToggle (size: sm) in Row 2 (changed from md to sm on 2026-02-18)
- Emits `toggle` event instead of separate `start`/`stop`

**Agent Node (Dashboard)** - `src/frontend/src/components/AgentNode.vue`
- Lines 57-65: RunningStateToggle (size: sm, nodrag class)
- Lines 376-385: `handleRunningToggle()` function

**Agent Lifecycle Composable** - `src/frontend/src/composables/useAgentLifecycle.js`
- Line 19-31: `startAgent()` function
- Line 33-45: `stopAgent()` function
- Line 47-62: `deleteAgent()` function with confirmation dialog

**Create Agent Modal** - `src/frontend/src/components/CreateAgentModal.vue`
- Line 9: Form submit calls `createAgent()`
- Line 15-22: Agent name input
- Line 26-137: Template selection (blank, GitHub, local)
- Lines 191-196: `initialTemplate` prop - Pre-selects template when modal opens
- Line 198: `emit('created', agent)` - Emits created agent for navigation
- Lines 207-210: Watch for `initialTemplate` prop changes
- Lines 263-285: `createAgent()` method - emits `created` event on success

### State Management (`src/frontend/src/stores/agents.js`)

```javascript
// Line 90-107: Create agent
async createAgent(config) {
  const response = await axios.post('/api/agents', config, {
    headers: authStore.authHeader
  })
  // Don't push here - WebSocket 'agent_created' event handles adding to list
  return response.data
}

// Line 109-124: Delete agent
async deleteAgent(name) {
  await axios.delete(`/api/agents/${name}`, {
    headers: authStore.authHeader
  })
  this.agents = this.agents.filter(agent => agent.name !== name)
}

// Line 126-140: Start agent
async startAgent(name) {
  const response = await axios.post(`/api/agents/${name}/start`, {}, {
    headers: authStore.authHeader
  })
  const agent = this.agents.find(a => a.name === name)
  if (agent) agent.status = 'running'
  return { success: true, message: response.data?.message || `Agent ${name} started` }
}

// Line 142-156: Stop agent
async stopAgent(name) {
  const response = await axios.post(`/api/agents/${name}/stop`, {}, {
    headers: authStore.authHeader
  })
  const agent = this.agents.find(a => a.name === name)
  if (agent) agent.status = 'stopped'
  return { success: true, message: response.data?.message || `Agent ${name} stopped` }
}

// Line 183-218: Toggle agent running state (NEW 2026-01-26)
async toggleAgentRunning(name) {
  const agent = this.agents.find(a => a.name === name)
  if (!agent) return { success: false, error: 'Agent not found' }

  this.runningToggleLoading[name] = true  // Track loading per agent

  try {
    if (agent.status === 'running') {
      await axios.post(`/api/agents/${name}/stop`, {}, { headers: authStore.authHeader })
      agent.status = 'stopped'
    } else {
      await axios.post(`/api/agents/${name}/start`, {}, { headers: authStore.authHeader })
      agent.status = 'running'
    }
    return { success: true, status: agent.status }
  } catch (error) {
    return { success: false, error: error.response?.data?.detail || 'Failed to toggle agent' }
  } finally {
    this.runningToggleLoading[name] = false
  }
}
```

---

## Backend Layer

### Architecture (Post-Refactoring)

The agent router uses a **thin router + service layer** architecture:

| Layer | File | Purpose |
|-------|------|---------|
| Router | `src/backend/routers/agents.py` (~842 lines) | Endpoint definitions, dependency injection |
| Services | `src/backend/services/agent_service/` | Business logic modules |

**Service Modules:**

| Module | Lines | Key Functions |
|--------|-------|---------------|
| `helpers.py` | ~404 | `get_accessible_agents()` (uses batch query), `get_next_version_name()`, `check_shared_folder_mounts_match()`, `check_api_key_env_matches()` (SUB-002: three-way check for `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` / neither) |
| `lifecycle.py` | ~435 | `inject_trinity_meta_prompt()`, `start_agent_internal()`, `recreate_container_with_updated_config()` (SUB-002: manages `CLAUDE_CODE_OAUTH_TOKEN` and `ANTHROPIC_API_KEY` env vars) |
| `crud.py` | 507 | `create_agent_internal()` |
| `terminal.py` | 342 | `TerminalSessionManager` class |

**Shared Services:**

| Module | Lines | Key Functions |
|--------|-------|---------------|
| `services/settings_service.py` | 124 | `get_anthropic_api_key()`, `get_github_pat()`, `get_ops_setting()` |
| `services/agent_client.py` | 379 | `AgentClient.inject_trinity_prompt()`, `AgentClient.chat()`, `AgentClient.get_session()` |

### Pydantic Models (`src/backend/models.py:10-40`)

```python
class AgentConfig(BaseModel):
    name: str
    type: Optional[str] = "business-assistant"
    base_image: str = "trinity-agent-base:latest"
    resources: Optional[dict] = {"cpu": "2", "memory": "4g"}
    tools: Optional[List[str]] = ["filesystem", "web_search"]
    mcp_servers: Optional[List[str]] = []
    custom_instructions: Optional[str] = None
    port: Optional[int] = None  # SSH port (auto-assigned)
    template: Optional[str] = None
    github_repo: Optional[str] = None  # GitHub-native agent support
    github_credential_id: Optional[str] = None

class AgentStatus(BaseModel):
    name: str
    type: str
    status: str  # "running" | "stopped"
    port: int    # SSH port only
    created: datetime
    resources: dict
    container_id: Optional[str] = None
    template: Optional[str] = None
```

### Endpoints

#### Create Agent (`src/backend/routers/agents.py:189-192`)
```python
@router.post("")
async def create_agent_endpoint(config: AgentConfig, request: Request, current_user: User = Depends(get_current_user)):
    """Create a new agent."""
    return await create_agent_internal(config, current_user, request, skip_name_sanitization=False)
```

**Service Function** (`src/backend/services/agent_service/crud.py:35-507`):

**Imports** (lines 1-32):
```python
from services.settings_service import get_anthropic_api_key  # Line 29 - centralized settings
```

**Business Logic:**
1. **Sanitize name** (line 78-82): Lowercase, replace special chars with hyphens via `sanitize_agent_name()`
2. **Check existence** (line 84-85): Query Docker for existing container via `get_agent_by_name()`
3. **Load template** (line 97-179): GitHub or local template processing, extract shared folder config
4. **Auto-assign port** (line 180-181): Find next available SSH port (2289+) via `get_next_available_port()`
5. **Generate credential files** (line 188-200): Create empty template structure (CRED-002: no longer auto-injects credentials)
6. **Create MCP API key** (line 260-271): Generate agent-scoped Trinity MCP access key
7. **Build env vars** (line 273-344): `ANTHROPIC_API_KEY` via `get_anthropic_api_key()`, GitHub repo/PAT
8. **Create persistent volume** (line 348-360): Per-agent workspace volume for Pillar III compliance
9. **Mount Trinity meta-prompt** (line 374-379): Mount `/trinity-meta-prompt` volume for planning commands
10. **Create container** (line 428-454): Docker SDK `containers.run()` with security options
11. **Register ownership** (line 472): `db.register_agent_owner(current_user.username)`
12. **Grant default permissions** (line 475-480): Same-owner agent permissions (Phase 9.10)
13. **Upsert shared folder config** (line 394-404): Persist config from template BEFORE container creation
14. **Create git config** (line 483-496): For GitHub-native agents (Phase 7)
15. **Broadcast WebSocket** (line 458-470): `agent_created` event
16. **Audit log**: Handled by router after service call

> **CRED-002 (2026-02-05)**: Credentials are NO LONGER auto-injected during agent creation.
> They are added after creation via:
> - Quick Inject (paste .env text in Credentials tab)
> - Import from `.credentials.enc` on startup
> - `inject_credentials` MCP tool
>
> **Bug Fix (2026-02-05)**: Removed orphaned credential injection loop (lines 312-332 in crud.py) that referenced undefined `agent_credentials` variable. This dead code was left behind during the CRED-002 refactor but never executed since the variable was already removed.

#### Delete Agent (`src/backend/routers/agents.py:211-313`)
```python
@router.delete("/{agent_name}")
async def delete_agent_endpoint(agent_name: str, request: Request, current_user: User = Depends(get_current_user)):
    # System agent protection check (line 214-229)
    if db.is_system_agent(agent_name):
        raise HTTPException(403, "System agents cannot be deleted")

    # Authorization check: owner or admin (line 231-241)
    if not db.can_user_delete_agent(current_user.username, agent_name):
        raise HTTPException(403, "Permission denied")

    container = get_agent_container(agent_name)
    container.stop()
    container.remove()

    # Delete persistent volume (line 253-261)
    volume = docker_client.volumes.get(f"agent-{agent_name}-workspace")
    volume.remove()

    # Delete schedules (line 263-267)
    # Delete git config (line 269-270)
    # Delete MCP API key (line 272-276)
    # Delete agent permissions (line 278-282)
    # Delete shared folder config (line 284-294)
    # Delete ownership (line 296) - cascades to shares
    # Broadcast WebSocket (line 298-302), audit log (line 304-311)
```

#### Rename Agent (RENAME-001) (`src/backend/routers/agents.py:1361-1460`)
```python
@router.put("/{agent_name}/rename")
async def rename_agent_endpoint(agent_name: str, body: RenameAgentRequest, ...):
    """
    Rename an agent. System agents cannot be renamed.

    1. Check permission (owner or admin, not system agent)
    2. Validate and sanitize new name (Docker-compatible)
    3. Stop container if running
    4. Rename Docker container (container.rename())
    5. Update all 17 database tables atomically (db.rename_agent())
    6. Broadcast WebSocket 'agent_renamed' event
    7. Return {message, old_name, new_name, was_running}
    """
```

**Database Method** (`src/backend/db/agents.py:620-780`):
```python
def rename_agent(self, old_name: str, new_name: str) -> bool:
    """
    Atomically update agent_name in all tables:
    - agent_ownership (primary)
    - agent_sharing, agent_schedules, schedule_executions
    - chat_sessions, chat_messages, agent_activities
    - agent_permissions (source AND target)
    - agent_shared_folder_config, agent_git_config
    - agent_skills, agent_tags, agent_public_links
    - mcp_api_keys, agent_health_checks, agent_dashboard_values
    - monitoring_alert_cooldowns
    """
```

**MCP Tool** (`src/mcp-server/src/tools/agents.ts:260-295`):
```typescript
renameAgent: {
  name: "rename_agent",
  parameters: z.object({
    name: z.string().describe("Current agent name"),
    new_name: z.string().describe("New agent name"),
  }),
  execute: async ({ name, new_name }) => {
    return apiClient.renameAgent(name, new_name);
  }
}
```

**Frontend** (`src/frontend/src/components/AgentHeader.vue:8-30`):
- Pencil icon button next to agent name (visible when `agent.can_share && !agent.is_system`)
- Inline editing with input field, Enter to save, Escape to cancel
- Emits `rename` event handled by `AgentDetail.vue:renameAgent()`
- On success, navigates to new URL `/agents/{new_name}`

#### Start Agent (`src/backend/routers/agents.py:315-339`)
```python
@router.post("/{agent_name}/start")
async def start_agent_endpoint(agent_name: AuthorizedAgentByName, request: Request, current_user: CurrentUser):
    """
    Start an agent.

    Note: Uses AuthorizedAgentByName dependency which checks user has access to agent
    (owner, shared user, or admin). This prevents unauthorized users from starting
    agents they don't own.
    """
    result = await start_agent_internal(agent_name)
    trinity_status = result.get("trinity_injection", "unknown")

    # Broadcast WebSocket with injection status
    # Return start result with Trinity injection status
```

**Service Function** (`src/backend/services/agent_service/lifecycle.py:198-279`):

**Imports** (lines 1-25):
```python
from services.settings_service import get_anthropic_api_key, get_agent_full_capabilities  # Line 21
from services.agent_client import get_agent_client           # Line 22 - centralized HTTP client
from services.skill_service import skill_service             # Line 23 - skill injection
from .helpers import check_shared_folder_mounts_match, check_api_key_env_matches, check_resource_limits_match, check_full_capabilities_match  # Line 24
```

```python
async def start_agent_internal(agent_name: str) -> dict:
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if container needs recreation for shared folders, API key/token, resources, or capabilities
    # NOTE: check_api_key_env_matches() performs a three-way check (SUB-002):
    #   - Subscription assigned: must have CLAUDE_CODE_OAUTH_TOKEN, must NOT have ANTHROPIC_API_KEY
    #   - Platform key enabled: must have ANTHROPIC_API_KEY, must NOT have CLAUDE_CODE_OAUTH_TOKEN
    #   - Neither: both must be absent
    await container_reload(container)
    needs_recreation = (
        not await check_shared_folder_mounts_match(container, agent_name) or
        not check_api_key_env_matches(container, agent_name) or
        not check_resource_limits_match(container, agent_name) or
        not check_full_capabilities_match(container, agent_name)
    )

    if needs_recreation:
        # Recreate container with updated config
        # (sets CLAUDE_CODE_OAUTH_TOKEN if subscription, removes ANTHROPIC_API_KEY, or vice versa)
        await recreate_container_with_updated_config(agent_name, container, "system")
        container = get_agent_container(agent_name)

    await container_start(container)

    # 1. Inject Trinity meta-prompt via AgentClient
    trinity_result = await inject_trinity_meta_prompt(agent_name)

    # 2. Import credentials from encrypted .credentials.enc file (CRED-002)
    credentials_result = await inject_assigned_credentials(agent_name)

    # 3. Inject assigned skills from the Skills page
    skills_result = await inject_assigned_skills(agent_name)

    # NOTE: Subscription tokens are NO LONGER injected post-start (SUB-002).
    # They are set as CLAUDE_CODE_OAUTH_TOKEN env var at container creation/recreation time.

    return {
        "message": f"Agent {agent_name} started",
        "trinity_injection": trinity_result.get("status", "unknown"),
        "trinity_result": trinity_result,
        "credentials_injection": credentials_result.get("status", "unknown"),
        "credentials_result": credentials_result,
        "skills_injection": skills_result.get("status", "unknown"),
        "skills_result": skills_result
    }
```

**Startup Injection Order** (After container.start()):
1. **Trinity Meta-Prompt** (`inject_trinity_meta_prompt`) - Planning commands and `.trinity/` directory
2. **Credentials** (`inject_assigned_credentials`) - CRED-002: Decrypt `.credentials.enc` and write files
3. **Skills** (`inject_assigned_skills`) - Write skill files to `~/.claude/skills/{name}/SKILL.md`
4. **Read-Only Hooks** (`inject_read_only_hooks`) - If read-only mode enabled

> **SUB-002 Note**: Subscription tokens are no longer injected post-start. They are set as `CLAUDE_CODE_OAUTH_TOKEN` env var at container creation/recreation time, before the container starts.

**Container Recreation Triggers:**
- **Shared folder changes**: Mounts added/removed based on `shared_folder_config`
- **Auth env var changes** (SUB-002): `ANTHROPIC_API_KEY` and/or `CLAUDE_CODE_OAUTH_TOKEN` added/removed based on `use_platform_api_key` AND subscription assignment. Three-way check ensures mutual exclusion.
- **Resource limit changes**: Memory/CPU limits updated in database
- **Capabilities changes**: System-wide full_capabilities setting changed
- API key retrieval uses `get_anthropic_api_key()` from `services/settings_service.py` (line 118)

**Authentication Model** (Updated 2026-03-03 for SUB-002):

Claude Code checks credentials in **priority order** (highest first):

1. **API key**: `ANTHROPIC_API_KEY` environment variable -- if present, Claude Code uses this and **ignores** OAuth
2. **Subscription OAuth** (SUB-002): `CLAUDE_CODE_OAUTH_TOKEN` env var set at container creation/recreation
3. **OAuth session** (manual login): User runs `/login` in web terminal

**Critical**: Because `ANTHROPIC_API_KEY` takes precedence, the env var must be **absent** from the container when a subscription is assigned. The two auth env vars are mutually exclusive. This is enforced by:

- `check_api_key_env_matches()` (`helpers.py:313-351`): Three-way check on every agent start. If subscription assigned: must have `CLAUDE_CODE_OAUTH_TOKEN` with correct value, must NOT have `ANTHROPIC_API_KEY`. If platform key: must have `ANTHROPIC_API_KEY`, must NOT have `CLAUDE_CODE_OAUTH_TOKEN`. If neither: both must be absent. Returns `False` to trigger container recreation on any mismatch.
- `recreate_container_with_updated_config()` (`lifecycle.py:275-434`): When rebuilding the container, checks `db.get_agent_subscription_id()`. If a subscription exists, sets `CLAUDE_CODE_OAUTH_TOKEN` from `db.get_subscription_token()` and removes `ANTHROPIC_API_KEY`. If no subscription but platform key enabled, sets `ANTHROPIC_API_KEY` and removes `CLAUDE_CODE_OAUTH_TOKEN`. Otherwise removes both.
- `assign_subscription_to_agent` endpoint (`subscriptions.py:184-259`): Assigning a subscription to a **running** agent triggers a restart (stop + start) so the container is recreated with `CLAUDE_CODE_OAUTH_TOKEN` env var.
- `clear_agent_subscription` endpoint (`subscriptions.py:262-311`): Clearing a subscription from a **running** agent triggers a restart to remove the token and restore the API key.

The mandatory `ANTHROPIC_API_KEY` check was removed from Claude Code execution functions, allowing headless calls (scheduled tasks, MCP triggers, parallel tasks) to work with subscription authentication.

**Trinity Meta-Prompt Injection** (`src/backend/services/agent_service/lifecycle.py:23-51`)

Now uses centralized `AgentClient` service instead of raw httpx calls:

```python
async def inject_trinity_meta_prompt(agent_name: str, max_retries: int = 5, retry_delay: float = 2.0) -> dict:
    """
    Inject Trinity meta-prompt into an agent via its internal API.
    Uses AgentClient for centralized HTTP communication with retry logic.
    """
    # Fetch system-wide custom prompt setting
    custom_prompt = db.get_setting_value("trinity_prompt", default=None)

    # Use AgentClient for injection (handles retries internally)
    client = get_agent_client(agent_name)  # Line 44
    return await client.inject_trinity_prompt(
        custom_prompt=custom_prompt,
        force=False,
        max_retries=max_retries,
        retry_delay=retry_delay
    )  # Lines 45-50
```

**AgentClient.inject_trinity_prompt()** (`src/backend/services/agent_client.py:278-344`):
- **Built-in retry logic**: Configurable `max_retries` (default 3) and `retry_delay` (default 2.0s)
- **Agent URL construction**: Automatically builds `http://agent-{name}:8000`
- **Error handling**: Returns `{"status": "error", "error": "..."}` on failure
- **Timeout**: Default 10 seconds (`INJECT_TIMEOUT`)

```python
async def inject_trinity_prompt(
    self,
    custom_prompt: Optional[str] = None,
    force: bool = False,
    timeout: float = None,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> Dict[str, Any]:
    """Inject Trinity meta-prompt with retry logic."""
    for attempt in range(max_retries):
        try:
            response = await self.post("/api/trinity/inject", json=payload, timeout=timeout)
            if response.status_code == 200:
                return response.json()
        except AgentNotReachableError:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
```

**Container Recreation** (`src/backend/services/agent_service/lifecycle.py:275-434`):
Handles recreating containers with updated volume mounts and environment variables. Subscription-aware (SUB-002): checks `db.get_agent_subscription_id()` to manage auth env vars. Three cases:
- **Subscription assigned**: Sets `CLAUDE_CODE_OAUTH_TOKEN` from `db.get_subscription_token()`, removes `ANTHROPIC_API_KEY`
- **Platform key enabled (no subscription)**: Sets `ANTHROPIC_API_KEY` from `get_anthropic_api_key()`, removes `CLAUDE_CODE_OAUTH_TOKEN`
- **Neither**: Removes both `ANTHROPIC_API_KEY` and `CLAUDE_CODE_OAUTH_TOKEN`

#### Stop Agent (`src/backend/routers/agents.py:342-360`)
```python
@router.post("/{agent_name}/stop")
async def stop_agent_endpoint(agent_name: AuthorizedAgentByName, request: Request, current_user: CurrentUser):
    """
    Stop an agent.

    Note: Uses AuthorizedAgentByName dependency for authorization check.
    """
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.stop()

    # Broadcast WebSocket, return stop result
```

#### Get Agent Logs (`src/backend/routers/agents.py:367-383`)
```python
@router.get("/{agent_name}/logs")
async def get_agent_logs_endpoint(agent_name: AuthorizedAgentByName, request: Request, tail: int = 100):
    """
    Get agent container logs.

    Note: Uses AuthorizedAgentByName dependency - users can only view logs
    for agents they have access to.
    """
```

### Docker Service (`src/backend/services/docker_service.py`)

**Key Functions:**

| Function | Line | Purpose |
|----------|------|---------|
| `get_agent_container()` | 18-28 | Get container by name from Docker API |
| `get_agent_status_from_container()` | 31-83 | Convert Docker container to AgentStatus model (full metadata) |
| `list_all_agents()` | 86-98 | List all containers with full metadata (slower, uses `container.attrs`) |
| `list_all_agents_fast()` | 101-159 | **Fast listing using labels only** - avoids slow Docker API calls (~50ms vs 2-3s) |
| `get_agent_by_name()` | 162-167 | Get specific agent status |
| `get_next_available_port()` | 182-205 | Find next SSH port (2222+) - uses `list_all_agents_fast()` |

> **Performance Note (2026-01-12)**: `list_all_agents_fast()` was added to optimize agent listing. It extracts data ONLY from container labels, avoiding expensive Docker operations like `container.attrs`, `container.image`, and `container.stats()`. This reduced `/api/agents` response time from ~2-3s to <50ms.

**Status Normalization (line 38-44):**
```python
# Docker statuses: created, running, paused, restarting, removing, exited, dead
docker_status = container.status
if docker_status in ("exited", "dead", "created"):
    normalized_status = "stopped"
elif docker_status == "running":
    normalized_status = "running"
else:
    normalized_status = docker_status  # paused, restarting, etc.
```

---

## Database Layer (`src/backend/db/agents.py`)

### Batch Metadata Query (N+1 Fix) - Added 2026-01-12

**Problem**: `get_accessible_agents()` was making 8-10 database queries PER agent, totaling 160-200 queries for 20 agents.

**Solution**: `get_all_agent_metadata()` (lines 467-529) fetches ALL agent metadata in a SINGLE JOIN query:

```python
def get_all_agent_metadata(self, user_email: str = None) -> Dict[str, Dict]:
    """
    Single query that joins all related tables:
    - agent_ownership (owner, is_system, autonomy_enabled, resource limits)
    - users (owner username/email)
    - agent_git_config (GitHub repo/branch)
    - agent_sharing (share access check)

    Returns dict keyed by agent_name.
    """
```

**Usage in `get_accessible_agents()` (helpers.py:83-153)**:
```python
# Before (N+1 problem):
for agent in all_agents:
    can_access = db.can_user_access_agent(...)     # 2-4 queries
    owner = db.get_agent_owner(...)                 # 1 query
    is_shared = db.is_agent_shared_with_user(...)   # 2 queries
    autonomy = db.get_autonomy_enabled(...)         # 1 query
    git_config = db.get_git_config(...)             # 1 query
    limits = db.get_resource_limits(...)            # 1 query

# After (batch query):
all_metadata = db.get_all_agent_metadata(user_email)  # 1 query for ALL
for agent in all_agents:
    metadata = all_metadata.get(agent_name)           # dict lookup
```

**Result**: Database queries reduced from 160-200 to 2 per `/api/agents` request.

**Exposed on DatabaseManager** (`database.py:845-850`):
```python
def get_all_agent_metadata(self, user_email: str = None):
    return self._agent_ops.get_all_agent_metadata(user_email)
```

### Tables

**agent_ownership**
```sql
CREATE TABLE agent_ownership (
    id INTEGER PRIMARY KEY,
    agent_name TEXT UNIQUE,
    owner_id INTEGER REFERENCES users(id),
    created_at TEXT
)
```

**agent_schedules** (for scheduled tasks)
```sql
CREATE TABLE agent_schedules (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    schedule_type TEXT NOT NULL,
    cron_expression TEXT,
    ...
)
```

**agent_git_configs** (Phase 7 - GitHub-native agents)
```sql
CREATE TABLE agent_git_configs (
    agent_name TEXT PRIMARY KEY,
    github_repo TEXT NOT NULL,
    working_branch TEXT NOT NULL,
    instance_id TEXT NOT NULL,
    ...
)
```

**agent_mcp_api_keys** (Agent-to-Agent collaboration)
```sql
CREATE TABLE agent_mcp_api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT UNIQUE NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    ...
)
```

### Operations (`src/backend/db/agents.py`)

| Method | Line | Purpose |
|--------|------|---------|
| `register_agent_owner()` | 38-55 | Record owner on creation |
| `get_agent_owner()` | 57-70 | Get owner info |
| `delete_agent_ownership()` | 85-94 | Delete ownership + cascade shares |
| `can_user_access_agent()` | 96-115 | Check if user can view agent |
| `can_user_delete_agent()` | 117-132 | Authorization check (owner or admin) |

---

## Docker Configuration

### Container Labels (`src/backend/services/agent_service/crud.py:353-362`)
| Label | Purpose |
|-------|---------|
| `trinity.platform=agent` | Identifies Trinity agents |
| `trinity.agent-name` | Agent name |
| `trinity.agent-type` | Type (business-assistant, etc.) |
| `trinity.ssh-port` | SSH port number |
| `trinity.cpu` | CPU allocation |
| `trinity.memory` | Memory limit |
| `trinity.created` | Creation timestamp (ISO format) |
| `trinity.template` | Template used (empty string if none) |

### Container Security Constants (`src/backend/services/agent_service/lifecycle.py:31-59`)

**2026-01-14 Security Fix**: All container creation paths now use centralized capability constants for consistent security.

```python
# Restricted mode capabilities - minimum for agent operation (default)
RESTRICTED_CAPABILITIES = [
    'NET_BIND_SERVICE',  # Bind to ports < 1024
    'SETGID', 'SETUID',  # Change user/group (for su/sudo)
    'CHOWN',             # Change file ownership
    'SYS_CHROOT',        # Use chroot
    'AUDIT_WRITE',       # Write to audit log
]

# Full capabilities mode - adds package installation support
FULL_CAPABILITIES = RESTRICTED_CAPABILITIES + [
    'DAC_OVERRIDE',      # Bypass file permission checks (needed for apt)
    'FOWNER',            # Bypass permission checks on file owner
    'FSETID',            # Don't clear setuid/setgid bits
    'KILL',              # Send signals to processes
    'MKNOD',             # Create special files
    'NET_RAW',           # Use raw sockets (ping, etc.)
    'SYS_PTRACE',        # Trace processes (debugging)
]
```

### Security Options (Applied Consistently)

All container creation paths (`crud.py`, `lifecycle.py`, `system_agent_service.py`) now apply:

```python
# Always apply AppArmor for additional sandboxing
security_opt=['apparmor:docker-default'],
# Always drop ALL capabilities first (defense in depth)
cap_drop=['ALL'],
# Add back only the capabilities needed for the mode
cap_add=FULL_CAPABILITIES if full_capabilities else RESTRICTED_CAPABILITIES,
read_only=False,
# Always apply noexec,nosuid to /tmp for security
tmpfs={'/tmp': 'noexec,nosuid,size=100m'}
```

**Files Using These Constants**:
| File | Line | Usage |
|------|------|-------|
| `services/agent_service/crud.py` | 464 | Agent creation |
| `services/agent_service/lifecycle.py` | 361 | Container recreation |
| `services/system_agent_service.py` | 260 | System agent creation |

### Network Isolation (line 645)
- Network: `trinity-agent-network` (Docker network)
- Only SSH port (22) mapped externally via `ports={'22/tcp': config.port}`
- UI port (8000) NOT exposed - accessed via backend proxy at `/api/agents/{name}/ui/`

### Resource Limits (line 646-647)
```python
mem_limit=config.resources.get('memory', '4Gi'),
cpu_count=int(config.resources.get('cpu', '2'))
```

### Persistent Volume (line 542-561)
```python
# Create per-agent persistent volume for /home/developer (Pillar III: Persistent Memory)
agent_volume_name = f"agent-{config.name}-workspace"
volumes = {
    ...
    agent_volume_name: {'bind': '/home/developer', 'mode': 'rw'}  # Persistent workspace
}
```

### Trinity Meta-Prompt Volume (line 569-574)
```python
# Mount Trinity meta-prompt for agent collaboration guidance
container_meta_prompt_path = Path("/trinity-meta-prompt")
host_meta_prompt_path = os.getenv("HOST_META_PROMPT_PATH", "./config/trinity-meta-prompt")
if container_meta_prompt_path.exists():
    volumes[host_meta_prompt_path] = {'bind': '/trinity-meta-prompt', 'mode': 'ro'}
```

---

## Side Effects

### WebSocket Broadcasts
| Event | Payload | Trigger |
|-------|---------|---------|
| `agent_created` | `{name, type, status, port, created, resources, container_id}` | After container.run() (line 652-664) |
| `agent_started` | `{name, trinity_injection}` | After container.start() + Trinity injection (line 986-990) |
| `agent_stopped` | `{name}` | After container.stop() (line 1029-1033) |
| `agent_deleted` | `{name}` | After container.remove() (line 803-807) |

### Trinity Connect Filtered Broadcasts (Added 2026-02-05)

Agent start/stop events are now broadcast to both the main WebSocket and the filtered Trinity Connect WebSocket endpoint.

**Location**: `src/backend/routers/agents.py:324-340, 356-368`

```python
# Broadcast agent_started to main UI WebSocket
await manager.broadcast(json.dumps({"type": "agent_started", "name": agent_name, "data": {...}}))

# Broadcast to filtered Trinity Connect WebSocket (server-side filtering)
await filtered_manager.broadcast_filtered({"type": "agent_started", "name": agent_name, "data": {...}})
```

**Events Broadcast to Trinity Connect:**

| Event | Agent Name Field | Use Case |
|-------|------------------|----------|
| `agent_started` | `name` | External Claude Code waits for agent to be ready |
| `agent_stopped` | `name` | External Claude Code detects agent shutdown |

**Related Documentation**: [trinity-connect.md](trinity-connect.md) - Full feature flow for `/ws/events` endpoint

### Audit Logging
```python
await log_audit_event(
    event_type="agent_management",
    action="create|start|stop|delete",
    user_id=current_user.username,
    agent_name=config.name,
    resource=f"agent-{config.name}",
    ip_address=request.client.host if request.client else None,
    result="success|failed|unauthorized",
    details={...}
)
```

### Cascading Deletes (on agent deletion)
1. **Persistent Volume**: Agent workspace volume deleted
2. **Schedules**: All scheduled tasks removed from scheduler and database
3. **Git Config**: GitHub sync configuration deleted
4. **MCP API Key**: Agent's Trinity MCP access key revoked
5. **Permissions**: Agent-to-agent permissions deleted (source and target)
6. **Shared Folders**: Shared folder config and shared volume deleted
7. **Ownership**: Ownership record deleted
8. **Shares**: All shares cascade deleted via foreign key constraint

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Invalid agent name | 400 | "Invalid agent name - must contain at least one alphanumeric character" |
| Agent already exists | 400 | "Agent already exists" |
| Agent not found | 404 | "Agent not found" |
| Permission denied (delete) | 403 | "You don't have permission to delete this agent" |
| Docker error | 500 | "Failed to create/start/stop agent: {error}" |
| Docker unavailable | 503 | "Docker not available - cannot create agents in demo mode" |

---

## Security Considerations

1. **Authentication**: All endpoints require `Depends(get_current_user)`
2. **Authorization**:
   - Delete requires `can_user_delete_agent()` (owner or admin)
   - Access requires `can_user_access_agent()` (owner, shared user, or admin)
3. **Container Security**: CAP_DROP ALL, no-new-privileges, AppArmor
4. **Network Isolation**: Agent UI not exposed externally, accessed via backend proxy
5. **Credential Protection**: Never logged, injected at runtime via environment variables
6. **Agent-scoped MCP Keys**: Each agent gets unique API key for Trinity MCP access

---

## Testing

**Prerequisites**:
- [ ] Backend running at http://localhost:8000
- [ ] Frontend running at http://localhost:3000
- [ ] Docker daemon running
- [ ] Logged in as test@example.com

**Test Steps**:

### 1. Create Agent
**Action**:
- Navigate to http://localhost:3000
- Click "Create Agent" button
- Enter name: "test-lifecycle"
- Select template: "local:default"
- Click "Create"

**Expected**:
- Agent appears in agent list
- Status shows "running"
- SSH port assigned (2290+)
- WebSocket broadcast received

**Verify**:
- [ ] UI shows agent card with name "test-lifecycle"
- [ ] API: `curl http://localhost:8000/api/agents` includes agent
- [ ] Docker: `docker ps | grep test-lifecycle` shows container
- [ ] Database: Query agent_ownership for record
- [ ] Container has correct labels: `docker inspect agent-test-lifecycle | grep trinity`

### 2. Start Agent
**Action**: Click "Start" button on stopped agent

**Expected**:
- Button shows loading spinner
- Status changes to "running"
- Toast notification appears
- WebSocket broadcast received with `trinity_injection` status
- Trinity meta-prompt injected into agent

**Verify**:
- [ ] UI shows "running" badge
- [ ] Docker: `docker inspect agent-test-lifecycle | grep '"Running": true'`
- [ ] Container accessible on internal network
- [ ] Audit log has `agent_management:start` event with `trinity_injection` in details
- [ ] Trinity injection: Agent has `/home/developer/.trinity/` directory structure
- [ ] Trinity injection: Agent has planning commands available (check via chat)

### 3. Stop Agent
**Action**: Click "Stop" button

**Expected**:
- Status changes to "stopped"
- Container stops but remains
- WebSocket broadcast received

**Verify**:
- [ ] UI shows "stopped" status
- [ ] Docker: Container exists but not running
- [ ] Can start again without recreating
- [ ] Audit log has `agent_management:stop` event

### 4. Delete Agent
**Action**: Click trash icon, confirm deletion

**Expected**:
- Agent removed
- Container deleted
- All associated resources cleaned up
- Redirected to dashboard

**Verify**:
- [ ] UI: Agent not in list
- [ ] Docker: `docker ps -a | grep test-lifecycle` returns nothing
- [ ] Database: No ownership record
- [ ] Sharing records cascade deleted
- [ ] Schedules deleted
- [ ] MCP API key deleted
- [ ] Audit log has `agent_management:delete` event

**Edge Cases**:
- [ ] Duplicate name: Try creating "test-lifecycle" twice (should fail with 400)
- [ ] Unauthorized delete: Login as different user, try to delete (should fail with 403)
- [ ] Start running agent: Already running agent start should be idempotent
- [ ] Invalid template: Create with "github:invalid/repo" (should fail gracefully)
- [ ] Name sanitization: Create agent with name "Test Agent!" (should become "test-agent")

**Cleanup**:
- [ ] Delete any remaining test agents
- [ ] `docker ps -a | grep test-` - verify no orphans

---

**Last Updated**: 2026-03-03
**Status**: Working (all CRUD operations functional with Trinity injection)
**Issues**: None - agent lifecycle fully operational with service layer architecture and Trinity meta-prompt injection

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-03-03 | **SUB-002: Env-var-based subscription tokens**: Subscription tokens now injected as `CLAUDE_CODE_OAUTH_TOKEN` env var at container creation/recreation, replacing the old SUB-001 post-start `.credentials.json` file injection. Removed `inject_subscription_on_start()` call and `subscription_result`/`subscription_status` from `start_agent_internal()` return dict. `check_api_key_env_matches()` now performs three-way check: subscription (must have token, no API key), platform key (must have key, no token), neither (both absent). `recreate_container_with_updated_config()` sets/removes `CLAUDE_CODE_OAUTH_TOKEN` alongside `ANTHROPIC_API_KEY`. |
| 2026-03-02 | **Subscription credential priority fix (Issue #57)**: Updated Authentication Model to reflect correct Claude Code credential priority (API key > OAuth). `check_api_key_env_matches()` now subscription-aware -- detects subscription + API key conflict and triggers container recreation to remove `ANTHROPIC_API_KEY`. `recreate_container_with_updated_config()` omits API key when subscription assigned. Updated `start_agent_internal()` code block to match current implementation (includes subscription injection step). Updated container recreation line references. |
| 2026-03-01 | **Agent Rename (RENAME-001)**: Added `PUT /api/agents/{name}/rename` endpoint (agents.py:1370-1510), `rename_agent` MCP tool (agents.ts:263-296), `renameAgent()` client method (client.ts:277-296), `db.rename_agent()` for atomic 17-table update (db/agents.py:624-780), `db.can_user_rename_agent()` permission check (db/agents.py:781-800), `container_rename()` async wrapper (docker_utils.py:82-90). Frontend: Pencil icon in AgentHeader.vue (lines 26-35), inline editing with Enter/Escape, `renameAgent()` handler in AgentDetail.vue (lines 460-494). System agents protected from rename. WebSocket `agent_renamed` event broadcast. |
| 2026-02-24 | **Async Docker Operations (DOCKER-001)**: All blocking Docker SDK calls now use async wrappers from `services/docker_utils.py`. Affected: `start_agent_internal()`, `recreate_container_with_updated_config()`, `delete_agent_endpoint()`, `stop_agent_endpoint()`. Event loop no longer blocks during Docker operations. See [async-docker-operations.md](async-docker-operations.md). |
| 2026-02-22 | **Subscription Injection on Startup (SUB-001)**: ~~Added `inject_subscription_on_start()` to startup injection order between credentials and skills.~~ *Superseded by SUB-002 (2026-03-03): subscription tokens now injected as env var at container creation, not post-start.* Updated Authentication Model section to document 3 auth methods in priority order. Added cross-reference to [subscription-management.md](subscription-management.md). |
| 2026-02-18 17:50 | **Toggle Size Consistency**: All toggles in AgentHeader.vue now use `size="sm"`: RunningStateToggle (line 41), AutonomyToggle (line 68), ReadOnlyToggle (line 77). RunningStateToggle.vue default size changed from 'md' to 'sm' (line 97). This provides visual consistency across all toggle locations (AgentHeader, Agents.vue, AgentNode.vue). |
| 2026-02-18 | **UI-001 Redesign + Tab Restructuring**: Updated AgentHeader structure (3-row layout), RunningStateToggle now at lines 38-43 in Row 1. Default tab changed from 'info' to 'tasks' (line 275). **Logs tab and Files tab removed from visibleTabs. Terminal tab repositioned after Git tab.** New tab order (lines 504-529): Tasks, Dashboard*, Schedules, Credentials, Skills, Sharing*, Permissions*, Git*, Terminal, Folders*, Public Links*, Info. |
| 2026-02-15 | **Claude Max subscription support**: Updated documentation to reflect that agents can now use Claude Max subscription for all executions (including headless). When "Authenticate in Terminal" is enabled and user logs in via `/login`, the OAuth session in `~/.claude.json` is used for scheduled tasks, MCP calls, and parallel tasks instead of requiring `ANTHROPIC_API_KEY`. |
| 2026-02-05 | **Bug fix: Orphaned credential injection loop**: Removed dead code in `crud.py:312-332` that iterated over undefined `agent_credentials` variable. This loop was left behind during CRED-002 refactor when the variable definition (lines ~183-192) was removed. Added comment explaining credentials are injected post-creation. |
| 2026-02-05 | **CRED-002 + Skill Injection on Startup**: Updated `start_agent_internal()` documentation to include full startup injection order: Trinity meta-prompt, credentials (from `.credentials.enc`), skills. Updated lifecycle.py line numbers (now 193-250). Added `check_full_capabilities_match()` to container recreation triggers. |
| 2026-02-05 | **Trinity Connect Integration**: Agent start/stop events now broadcast to filtered WebSocket `/ws/events` for external listeners. Added Trinity Connect Filtered Broadcasts section with code example and event table. Related: trinity-connect.md |
| 2026-01-26 | **UX: Unified Start/Stop Toggle**: Replaced separate Start/Stop buttons with `RunningStateToggle.vue` component. Component supports three sizes (sm/md/lg), loading spinner, dark mode, ARIA attributes. Updated AgentHeader.vue (emits `toggle` instead of `start`/`stop`), Agents.vue (uses `toggleAgentRunning()`), AgentNode.vue (new toggle in Dashboard). Added `toggleAgentRunning()` and `runningToggleLoading` state to agents.js and network.js stores. |
| 2026-01-14 | **Security Bug Fixes (HIGH)**: (1) **Missing Auth on Lifecycle Endpoints**: Changed `start_agent_endpoint`, `stop_agent_endpoint`, `get_agent_logs_endpoint` to use `AuthorizedAgentByName` dependency instead of plain `get_current_user`. This ensures users can only start/stop/view logs for agents they have access to. (2) **Container Security Consistency**: Added `RESTRICTED_CAPABILITIES` and `FULL_CAPABILITIES` constants in `lifecycle.py:31-49`. All container creation paths (`crud.py:464`, `lifecycle.py:361`, `system_agent_service.py:260`) now ALWAYS apply baseline security: `cap_drop=['ALL']`, AppArmor profile, `noexec,nosuid` on tmpfs. Previously some paths had inconsistent security settings. |
| 2026-01-12 | **Database Batch Queries (N+1 Fix)**: Added `get_all_agent_metadata()` in `db/agents.py:467-529` - single JOIN query across `agent_ownership`, `users`, `agent_git_config`, `agent_sharing` tables. Rewrote `get_accessible_agents()` in `helpers.py:83-153` to use batch query instead of 8-10 individual queries per agent. Exposed on `DatabaseManager` (`database.py:845-850`). Database queries reduced from 160-200 to 2 per request. Orphaned agents (Docker-only, no DB record) now only visible to admin. |
| 2026-01-12 | **Docker Stats Optimization**: Added `list_all_agents_fast()` function (docker_service.py:101-159) that extracts data ONLY from container labels, avoiding slow Docker operations (`container.attrs`, `container.image`, `container.stats()`). Updated `get_next_available_port()` to use fast version. Performance: `/api/agents` reduced from ~2-3s to <50ms. |
| 2025-12-31 | **Settings service and AgentClient refactoring**: (1) API key retrieval now uses `services/settings_service.py` instead of importing from `routers/settings.py`. Updated `lifecycle.py:16` and `crud.py:29`. (2) Trinity injection now uses centralized `AgentClient.inject_trinity_prompt()` from `services/agent_client.py:278-344` with built-in retry logic (max_retries=3, retry_delay=2.0s). Updated `lifecycle.py:17,44-50`. (3) Updated line numbers in crud.py (now 507 lines) and lifecycle.py (now 221 lines). |
| 2025-12-30 | **Line number verification**: Updated all line numbers after composable refactoring. Frontend lifecycle methods now in `composables/useAgentLifecycle.js`. Updated router line numbers to match current 842-line agents.py. |
| 2025-12-27 | **Service layer refactoring**: Updated all references to new modular architecture. Business logic moved from `routers/agents.py` to `services/agent_service/` modules (lifecycle.py, crud.py, helpers.py). Router reduced from 2928 to 786 lines. |
| 2025-12-19 | **Line number updates**: Updated all line number references to match current codebase. Added Phase 9.10 (agent permissions) and Phase 9.11 (shared folders) cleanup in delete flow. Updated frontend component references. |
| 2025-12-09 | **Critical Bug Fix - File Persistence**: Added checks in `startup.sh` to skip re-cloning if repo already exists. Git-sync agents check for `.git` directory; non-git-sync agents check for `.trinity-initialized` marker. Files now persist across container restarts (Pillar III compliance). |
| 2025-12-07 | **CreateAgentModal enhancements**: Added `initialTemplate` prop for pre-selection, `created` event for navigation after success. Used by Templates.vue to open modal with template pre-selected and navigate to new agent's detail page. |

---

## Agent Container Startup Flow

### Container Initialization (`docker/base-image/startup.sh`)

When an agent container starts, it follows this initialization flow:

1. **GitHub Repository Handling** (if `GITHUB_REPO` and `GITHUB_PAT` are set):
   - **Git-Sync Enabled** (`GIT_SYNC_ENABLED=true`):
     - Checks if `/home/developer/.git` directory exists (persistent volume)
     - If exists: Skips cloning, runs `git fetch origin` to sync with remote
     - If not exists: Clones full repo, creates working branch, configures git user
     - Restores infrastructure files from base image backup
   - **Git-Sync Disabled**:
     - Checks if `/home/developer/.trinity-initialized` marker exists
     - If exists: Skips cloning, preserves user files on persistent volume
     - If not exists: Shallow clones repo, copies files, creates `.trinity-initialized` marker

2. **Local Template Handling** (if `TEMPLATE_NAME` and `/template` exists):
   - Copies `.claude/`, `CLAUDE.md`, `README.md`, `resources/`, `scripts/`, `memory/`

3. **Credential File Injection** (from `/generated-creds` volume):
   - Copies `.mcp.json`, `.env`, and other generated config files

4. **Service Startup**:
   - SSH server (if `ENABLE_SSH=true`)
   - Agent Web Server on port 8000 (if `ENABLE_AGENT_UI=true`)

### File Persistence (Bug Fix 2025-12-09)

**Problem**: Files created by agents were lost on container restart because `startup.sh` unconditionally re-cloned repositories, overwriting all user-created files.

**Solution**: Added persistence checks before cloning:

```bash
# For git-sync agents: Check for existing .git directory
if [ -d "/home/developer/.git" ]; then
    echo "Repository already exists on persistent volume - skipping clone"
    # Just fetch from remote, don't re-clone
fi

# For non-git-sync agents: Check for initialization marker
if [ -f "/home/developer/.trinity-initialized" ]; then
    echo "Agent workspace already initialized - preserving user files"
    # Skip cloning entirely
fi
```

**Key Files**:
- `docker/base-image/startup.sh:14-124` - Repository initialization with persistence checks
- `.trinity-initialized` - Marker file created after first-time initialization
- Per-agent Docker volume `agent-{name}-workspace` mounted to `/home/developer`

**Pillar III Compliance**: Agent workspace now survives restarts as required by Deep Agency spec (Persistent Memory pillar).

---

## Related Flows

- **Upstream**: Authentication Flow (JWT required via `get_current_user`)
- **Downstream**: Agent Terminal, Credential Injection, Activity Monitoring, Trinity Injection
- **Related**: Agent Sharing (ownership and access control)
- **Related**: Git Sync (GitHub-native agents)
- **Related**: Agent Scheduling (scheduled task management)
- **Related**: Trinity Connect (`trinity-connect.md`) - Filtered event broadcast for external listeners (Added 2026-02-05)
