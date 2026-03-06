# Feature: Agent Shared Folders

## Revision History

| Date | Changes |
|------|---------|
| 2025-12-13 | Initial implementation (Requirement 9.11) |
| 2025-12-27 | Refactored to service layer architecture |
| 2025-12-30 | Verified line numbers |
| 2026-01-23 | **Bug Fix**: Template `shared_folders` config now extracted during local template processing and persisted to DB before container creation. Fixed issue where agents created from templates with shared_folders config would not have volumes mounted on first creation. |

## Overview

File-based collaboration between agents via shared Docker volumes. Agents can expose a shared folder that other permitted agents can mount, enabling asynchronous file exchange between agents.

## Requirement Reference

- **Requirement**: 9.11 Agent Shared Folders
- **Status**: Implemented 2025-12-13
- **Pillar**: III (Persistent Memory) + II (Hierarchical Delegation)

## User Story

As an operator, I want agents to share files with each other so that an orchestrator agent can pass documents, data files, or artifacts to worker agents without going through the chat interface.

## Entry Points

- **UI**: `src/frontend/src/views/AgentDetail.vue:444-446` - Shared Folders tab (visible to owners, via `can_share`)
- **API**: `GET/PUT /api/agents/{name}/folders`
- **API**: `GET /api/agents/{name}/folders/available`
- **API**: `GET /api/agents/{name}/folders/consumers`

---

## Frontend Layer

### Components

- `AgentDetail.vue:444-446` - Folders tab added to navigation when `agent.can_share` is true
- `AgentDetail.vue:162-165` - Shared Folders tab content render with FoldersPanel
- `FoldersPanel.vue` - Complete folder configuration UI (239 lines)

### FoldersPanel.vue Features

1. **Configuration Toggles**:
   - Expose Shared Folder toggle (lines 43-67) - Creates shared volume
   - Mount Shared Folders toggle (lines 69-93) - Mounts permitted agent volumes

2. **Exposed Folder Info** (when expose_enabled):
   - Volume name display
   - Path display (`/home/developer/shared-out`)
   - Consumers list (agents that will mount this folder)

3. **Consumed Folders** (when consume_enabled):
   - List of mounted folders with mount status
   - Available folders from permitted agents
   - Pending/mounted status indicators

4. **Restart Required Banner**:
   - Lines 23-36 in FoldersPanel.vue
   - Shown when config changed but agent not restarted

5. **How It Works** Help Section:
   - Lines 193-214 in FoldersPanel.vue

### State Management

- `stores/agents.js:641` - `getAgentFolders(name)` - Fetch folder config
- `stores/agents.js:649` - `updateAgentFolders(name, config)` - Update config
- `stores/agents.js:657` - `getAvailableFolders(name)` - List mountable folders
- `stores/agents.js:665` - `getFolderConsumers(name)` - List agents that will mount

### API Calls

```javascript
// Get folder configuration
await axios.get(`/api/agents/${name}/folders`)

// Update folder configuration
await axios.put(`/api/agents/${name}/folders`, {
  expose_enabled: true,  // optional
  consume_enabled: true  // optional
})

// Get available folders to mount
await axios.get(`/api/agents/${name}/folders/available`)

// Get agents that will mount this folder
await axios.get(`/api/agents/${name}/folders/consumers`)
```

---

## Backend Layer

### Architecture (Service Layer)

The shared folders feature uses a **thin router + service layer** architecture:

| Layer | File | Purpose |
|-------|------|---------|
| Router | `src/backend/routers/agents.py:702-740` | Endpoint definitions |
| Service | `src/backend/services/agent_service/folders.py` (218 lines) | Folder business logic |

### Endpoints

| Method | Path | Router Line | Service Function |
|--------|------|-------------|------------------|
| GET | `/api/agents/{name}/folders` | 702-709 | `get_agent_folders_logic()` |
| PUT | `/api/agents/{name}/folders` | 712-720 | `update_agent_folders_logic()` |
| GET | `/api/agents/{name}/folders/available` | 723-730 | `get_available_shared_folders_logic()` |
| GET | `/api/agents/{name}/folders/consumers` | 733-740 | `get_folder_consumers_logic()` |

### Request/Response Models

```python
# GET /api/agents/{name}/folders response
{
  "agent_name": "agent-a",
  "expose_enabled": true,
  "consume_enabled": false,
  "exposed_volume": "agent-agent-a-shared",
  "exposed_path": "/home/developer/shared-out",
  "consumed_folders": [
    {
      "source_agent": "agent-b",
      "mount_path": "/home/developer/shared-in/agent-b",
      "access_mode": "rw",
      "currently_mounted": true
    }
  ],
  "restart_required": false,
  "status": "running"
}

# PUT /api/agents/{name}/folders request
{
  "expose_enabled": true,  // optional
  "consume_enabled": true  // optional
}

# PUT /api/agents/{name}/folders response
{
  "status": "updated",
  "agent_name": "agent-a",
  "expose_enabled": true,
  "consume_enabled": false,
  "restart_required": true,
  "message": "Configuration updated. Restart the agent to apply changes."
}

# GET /api/agents/{name}/folders/available response
{
  "agent_name": "agent-b",
  "available_folders": [
    {
      "source_agent": "agent-a",
      "volume_name": "agent-agent-a-shared",
      "mount_path": "/home/developer/shared-in/agent-a",
      "source_status": "running"
    }
  ],
  "count": 1
}

# GET /api/agents/{name}/folders/consumers response
{
  "source_agent": "agent-a",
  "consumers": [
    {
      "agent_name": "agent-b",
      "mount_path": "/home/developer/shared-in/agent-a",
      "status": "running"
    }
  ],
  "count": 1
}
```

### Business Logic

#### Agent Creation Flow (`services/agent_service/crud.py`)

**Bug Fix (2026-01-23)**: Previously, when agents were created from local templates with `shared_folders` config in `template.yaml`, the config was parsed but not persisted to the database before container creation. This meant the volume mounting code at lines 406-450 would find no config and skip mounting. The fix ensures template config is extracted and saved to DB first.

**Phase 1: Template Extraction** (Lines 91-92, 173-179)

During local template processing, `shared_folders` config is extracted from `template.yaml`:

```python
# Line 91-92: Initialize tracking variable
template_shared_folders = None

# Lines 173-179: Extract from template.yaml during local template load
shared_folders_config = template_data.get("shared_folders", {})
if shared_folders_config:
    template_shared_folders = {
        "expose": shared_folders_config.get("expose", False),
        "consume": shared_folders_config.get("consume", False)
    }
```

**Phase 2: DB Upsert Before Container Creation** (Lines 394-404)

The template config is persisted to DB **before** volume mounting, ensuring volumes are correctly attached on first container creation:

```python
# Phase 9.11: Agent Shared Folders - mount shared volumes based on config
# First, write template-defined shared folder config to DB (if defined)
if template_shared_folders:
    try:
        db.upsert_shared_folder_config(
            agent_name=config.name,
            expose_enabled=template_shared_folders.get("expose", False),
            consume_enabled=template_shared_folders.get("consume", False)
        )
        logger.info(f"Applied template shared folder config for {config.name}: ...")
    except Exception as e:
        logger.warning(f"Failed to apply template shared folder config for {config.name}: {e}")
```

**Phase 3: Volume Mounting** (Lines 406-450)

1. Check if agent has shared folder config: `db.get_shared_folder_config(config.name)`
2. If `expose_enabled`:
   - Create Docker volume `agent-{name}-shared` with labels (lines 410-422)
   - **Volume ownership fix**: Run alpine container to chown to UID 1000 (lines 424-434)
   - Mount at `/home/developer/shared-out` (rw) (line 436)
3. If `consume_enabled`:
   - Get available shared folders (permission-filtered): `db.get_available_shared_folders(config.name)` (line 440)
   - For each available folder, check if source volume exists (lines 441-450)
   - Mount volume at `/home/developer/shared-in/{agent}` (rw)

#### Agent Start Flow - Container Recreation (`services/agent_service/lifecycle.py:176-225`)

1. Check if shared folder mounts match config: `check_shared_folder_mounts_match(container, agent_name)` (line 196)
2. If mounts don't match, recreate container: `recreate_container_with_updated_config()` (line 205)
3. Start the (possibly new) container (line 208)
4. Inject Trinity meta-prompt and credentials

#### Helper: `check_shared_folder_mounts_match()` (`services/agent_service/helpers.py:267-307`)

Compares container's actual mounts to database config:
1. If no config exists, verify no shared mounts present (lines 272-280)
2. If `expose_enabled`, verify `/home/developer/shared-out` is mounted (lines 286-291)
3. If `consume_enabled`, verify all permitted source volumes are mounted (lines 294-305)
4. Returns `True` if mounts match, `False` if recreation needed

#### Helper: `recreate_container_with_updated_config()` (`services/agent_service/lifecycle.py:227-370`)

Recreates container with updated volume mounts:
1. Extract config from old container (image, env vars, labels, ports, resources)
2. Stop and remove old container (lines 274-278)
3. Build new volume configuration:
   - Preserve all non-shared-folder mounts (bind and volume types) (lines 287-298)
   - Add shared folder mounts based on current config (lines 300-341)
   - Volume ownership fix for newly created volumes (lines 318-328)
4. Create new container with same settings + updated mounts (lines 348-370)
5. Log recreation message

#### Agent Deletion Flow (`routers/agents.py`)

1. Delete shared folder config from database: `db.delete_shared_folder_config(agent_name)`
2. Delete shared volume if exists:
   ```python
   shared_volume = docker_client.volumes.get(shared_volume_name)
   shared_volume.remove()
   ```

#### Config Update Flow (`services/agent_service/folders.py:98-138`)

1. Validate owner permission: `db.can_user_share_agent()` (line 114)
2. Update database config: `db.upsert_shared_folder_config()` (line 125)
3. Return `restart_required: True` (line 136)
4. User restarts agent to apply mounts (triggers container recreation if needed)

---

## Data Layer

### Database Schema

```sql
CREATE TABLE IF NOT EXISTS agent_shared_folder_config (
    agent_name TEXT PRIMARY KEY,
    expose_enabled INTEGER DEFAULT 0,
    consume_enabled INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

### Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_shared_folders_expose ON agent_shared_folder_config(expose_enabled);
CREATE INDEX IF NOT EXISTS idx_shared_folders_consume ON agent_shared_folder_config(consume_enabled);
```

### Pydantic Models (src/backend/db_models.py)

```python
class SharedFolderConfig(BaseModel):
    agent_name: str
    expose_enabled: bool = False
    consume_enabled: bool = False
    created_at: datetime
    updated_at: datetime

class SharedFolderConfigUpdate(BaseModel):
    expose_enabled: Optional[bool] = None
    consume_enabled: Optional[bool] = None

class SharedFolderMount(BaseModel):
    source_agent: str
    mount_path: str
    access_mode: str = "rw"
    currently_mounted: bool = False

class SharedFolderInfo(BaseModel):
    agent_name: str
    expose_enabled: bool
    consume_enabled: bool
    exposed_volume: Optional[str] = None
    exposed_path: str = "/home/developer/shared-out"
    consumed_folders: List[SharedFolderMount] = []
    restart_required: bool = False
```

### Database Operations (src/backend/db/shared_folders.py)

| Method | Line | Description |
|--------|------|-------------|
| `get_shared_folder_config(agent_name)` | 38-54 | Get config or None |
| `upsert_shared_folder_config(agent_name, expose, consume)` | 56-118 | Create/update config |
| `delete_shared_folder_config(agent_name)` | 120-133 | Delete on agent removal |
| `get_agents_exposing_folders()` | 139-152 | List agents with expose=True |
| `get_available_shared_folders(requesting_agent)` | 154-176 | Permission-filtered list |
| `get_consuming_agents(source_agent)` | 178-203 | Agents that will mount source |
| `get_shared_volume_name(agent_name)` | 209-216 | Static: `agent-{name}-shared` |
| `get_shared_mount_path(source_agent)` | 218-225 | Static: `/home/developer/shared-in/{source}` |

### Volume Naming

- Shared volume: `agent-{name}-shared`
- Mount path (expose): `/home/developer/shared-out`
- Mount path (consume): `/home/developer/shared-in/{source_agent}`

---

## Docker Integration

### Volume Creation (services/agent_service/crud.py:412-422)

```python
docker_client.volumes.create(
    name=f"agent-{name}-shared",
    labels={
        'trinity.platform': 'agent-shared',
        'trinity.agent-name': name
    }
)
```

### Volume Ownership Fix (services/agent_service/crud.py:424-434)

Docker creates volumes as root. Fix by running alpine container:

```python
if volume_created:
    docker_client.containers.run(
        'alpine',
        command='chown 1000:1000 /shared',
        volumes={shared_volume_name: {'bind': '/shared', 'mode': 'rw'}},
        remove=True
    )
```

### Volume Mounting

```python
volumes = {
    # Exposed folder (if expose_enabled)
    f"agent-{name}-shared": {'bind': '/home/developer/shared-out', 'mode': 'rw'},
    # Consumed folders (if consume_enabled, for each permitted source)
    f"agent-{source}-shared": {'bind': f'/home/developer/shared-in/{source}', 'mode': 'rw'}
}
```

### Container Recreation

Docker cannot add volumes to existing containers. When config changes:
1. User toggles expose/consume in UI
2. Backend updates database, returns `restart_required: true`
3. User clicks Start/Restart
4. Backend checks if mounts match config
5. If mismatch, container is recreated with correct mounts

---

## Permission Integration

Shared folders respect the Agent Permissions system (Req 9.10):

1. Agent B can only mount Agent A's folder if:
   - Agent A has `expose_enabled=True`
   - Agent B has `consume_enabled=True`
   - Agent B has permission to call Agent A (via `agent_permissions` table)

2. Permission check in `get_available_shared_folders()` (src/backend/db/shared_folders.py:173):
   ```python
   if self._permission_ops.is_permitted(requesting_agent, exposing_agent):
       available.append(exposing_agent)
   ```

3. Consumer discovery in `get_consuming_agents()` (src/backend/db/shared_folders.py:200):
   ```python
   if self._permission_ops.is_permitted(agent, source_agent):
       available.append(agent)
   ```

---

## Side Effects

- **Docker Volumes**: Created/deleted on agent lifecycle
- **Container Recreation**: On start when mounts don't match config
- **No WebSocket**: No real-time updates (config changes require restart)
- **No Audit Log**: Currently not implemented for folder operations

---

## Error Handling

| Error | HTTP Status | Handler Location | Description |
|-------|-------------|------------------|-------------|
| Not owner | 403 | folders.py:115 | Only owner can modify folder sharing |
| Agent not found | 404 | folders.py:119 | Container doesn't exist |
| Volume error | 500 | Container creation | Docker volume operation failed |
| No access | 403 | folders.py:32 | User can't access this agent |

---

## Security Considerations

1. **Permission-Gated**: Only permitted agents can mount folders
2. **Owner-Only Config**: Only agent owner can enable/disable sharing
3. **Read-Write Access**: Currently all mounts are rw; future: add ro option
4. **Isolation**: Each agent's shared-out is a separate volume
5. **No Direct Access**: Users can't directly access shared volumes

---

## Testing

### Prerequisites
- Trinity platform running (`./scripts/deploy/start.sh`)
- At least two agents created (agent-a, agent-b)
- Same owner for both agents (for permission grant)

### Test Steps

1. **Enable Expose on Agent A**:
   - Open Agent A detail page -> Shared Folders tab
   - Toggle "Expose Shared Folder" ON
   - Verify: Config saved, restart required message shown

2. **Enable Consume on Agent B**:
   - Open Agent B detail page -> Shared Folders tab
   - Toggle "Mount Shared Folders" ON
   - Verify: Config saved, restart required message shown

3. **Grant Permission (if not same owner)**:
   - Open Agent B detail page -> Permissions tab
   - Enable permission to call Agent A
   - Verify: Permission granted

4. **Restart Both Agents**:
   - Stop and start Agent A
   - Stop and start Agent B
   - Verify: No errors in container logs

5. **Verify Mounts**:
   - Agent A: `docker exec agent-agent-a ls -la /home/developer/shared-out`
   - Agent B: `docker exec agent-agent-b ls -la /home/developer/shared-in/agent-a`

6. **Test File Sharing**:
   - Agent A: `docker exec agent-agent-a touch /home/developer/shared-out/test.txt`
   - Agent B: `docker exec agent-agent-b ls /home/developer/shared-in/agent-a/`
   - Verify: `test.txt` visible in Agent B

### Edge Cases

1. **Permission Revoked**: Remove permission -> Restart -> Folder should not be mounted
2. **Source Stopped**: Source agent stopped -> Consumer still sees last files
3. **Config Toggle**: Toggle off expose -> Restart -> Volume still exists but not mounted

### Template-Based Agent Test (2026-01-23 Fix)

1. Create template with `shared_folders` config in `template.yaml`:
   ```yaml
   shared_folders:
     expose: true
     consume: false
   ```

2. Create agent from template: `POST /api/agents` with `template: "local:my-template"`

3. Verify volume is mounted on first creation (no restart needed):
   ```bash
   docker exec agent-{name} ls -la /home/developer/shared-out
   ```

### Cleanup

1. Disable expose/consume toggles
2. Restart agents
3. Optionally: `docker volume rm agent-agent-a-shared`

### Status: Tested 2025-12-13, Updated 2026-01-23

---

## Related Flows

- **Upstream**: [agent-permissions.md](agent-permissions.md) - Permission grants control folder access
- **Related**: [agent-lifecycle.md](agent-lifecycle.md) - Volume mounting during create
- **Related**: [file-browser.md](file-browser.md) - Could extend to browse shared folders

---

## Future Enhancements

1. **Read-Only Mode**: Option to mount as read-only
2. **Selective Folders**: Choose specific agents to mount (not all)
3. **File Browser Integration**: Browse shared-in folders in File Manager (`/files`)
4. **Sync Indicators**: Show when files changed in shared folders
5. **Volume Size Limits**: Prevent runaway disk usage
6. **Audit Logging**: Add audit events for folder config changes
