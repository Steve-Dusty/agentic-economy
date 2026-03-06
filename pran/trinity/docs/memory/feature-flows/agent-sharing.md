# Feature: Agent Sharing

## Overview
Collaboration feature enabling agent owners to share agents with team members via email. Supports three access levels: Owner (full control), Shared (limited access), and Admin (full control over all agents). The Sharing tab now includes both Team Sharing and Public Links in a unified interface.

## User Story
As an agent owner, I want to share my agents with team members so that they can use the agents without having full ownership permissions.

## Entry Points
- **UI**: `src/frontend/src/views/AgentDetail.vue:429-432` - Sharing tab (owners only, hidden for system agents)
- **API**: `POST /api/agents/{name}/share` - Share agent
- **API**: `DELETE /api/agents/{name}/share/{email}` - Remove share
- **API**: `GET /api/agents/{name}/shares` - List shares

---

## Frontend Layer

### SharingPanel.vue (`src/frontend/src/components/SharingPanel.vue`)

The sharing UI is implemented as a dedicated component with two sections: Team Sharing and Public Links.

**Component Structure** (132 lines total):
- Lines 3-77: Team Sharing section (header, form, user list)
- Lines 79-80: Divider between sections
- Lines 82-83: Embedded `PublicLinksPanel` component
- Line 92: Import of `PublicLinksPanel`

**Team Sharing Section** (lines 3-77):
```vue
<div>
  <h3 class="text-lg font-medium ...">Team Sharing</h3>
  <!-- Share form (lines 11-30) -->
  <!-- Shared users list (lines 40-76) -->
</div>
```

**Public Links Integration** (lines 79-83):
```vue
<!-- Divider -->
<div class="border-t border-gray-200 dark:border-gray-700"></div>

<!-- Public Links Section -->
<PublicLinksPanel :agent-name="agentName" />
```

**Component Props** (lines 94-103):
```javascript
const props = defineProps({
  agentName: { type: String, required: true },
  shares: { type: Array, default: () => [] }
})
```

### Composable (`src/frontend/src/composables/useAgentSharing.js`)

Encapsulates sharing logic with reactive state management.

**shareWithUser** (lines 13-41):
```javascript
const shareWithUser = async () => {
  const result = await agentsStore.shareAgent(agentRef.value.name, shareEmail.value.trim())
  shareMessage.value = { type: 'success', text: `Agent shared with ${shareEmail.value.trim()}` }
  await loadAgent()
}
```

**removeShare** (lines 43-59):
```javascript
const removeShare = async (email) => {
  await agentsStore.unshareAgent(agentRef.value.name, email)
  showNotification(`Sharing removed for ${email}`, 'success')
  await loadAgent()
}
```

### State Management (`src/frontend/src/stores/agents.js:310-332`)
```javascript
// Agent Sharing Actions
async shareAgent(name, email) {
  const authStore = useAuthStore()
  const response = await axios.post(`/api/agents/${name}/share`,
    { email },
    { headers: authStore.authHeader }
  )
  return response.data
}

async unshareAgent(name, email) {
  const authStore = useAuthStore()
  await axios.delete(`/api/agents/${name}/share/${encodeURIComponent(email)}`, {
    headers: authStore.authHeader
  })
}

async getAgentShares(name) {
  const authStore = useAuthStore()
  const response = await axios.get(`/api/agents/${name}/shares`, {
    headers: authStore.authHeader
  })
  return response.data
}
```

### Tab Visibility (`src/frontend/src/views/AgentDetail.vue:506-509`)

The Sharing tab is only shown to users who can share and hidden for system agents:
```javascript
if (agent.value?.can_share && !isSystem) {
  tabs.push({ id: 'sharing', label: 'Sharing' })
  tabs.push({ id: 'permissions', label: 'Permissions' })
}
```

> **Note (2026-02-18)**: The "Public Links" tab was consolidated into the "Sharing" tab. SharingPanel.vue now renders PublicLinksPanel at the bottom of the panel, separated by a divider.

---

## Backend Layer

### Endpoints (`src/backend/routers/sharing.py`)

| Line | Endpoint | Method | Purpose |
|------|----------|--------|---------|
| 23-64 | `/api/agents/{agent_name}/share` | POST | Share agent with email |
| 67-89 | `/api/agents/{agent_name}/share/{email}` | DELETE | Remove share |
| 92-103 | `/api/agents/{agent_name}/shares` | GET | List shares |

### Authorization via Dependencies (`src/backend/dependencies.py:258-285`)

The sharing router uses `OwnedAgentByName` dependency for authorization:
```python
def get_owned_agent_by_name(
    agent_name: str = Path(...),
    current_user: User = Depends(get_current_user)
) -> str:
    """Validates user owns or can share an agent."""
    if not db.get_agent_owner(agent_name):
        raise HTTPException(404, "Agent not found")
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(403, "Owner access required")
    return agent_name

OwnedAgentByName = Annotated[str, Depends(get_owned_agent_by_name)]
```

### Share Agent (`routers/sharing.py:23-64`)
```python
@router.post("/{agent_name}/share", response_model=AgentShare)
async def share_agent_endpoint(
    agent_name: OwnedAgentByName,  # Authorization via dependency
    share_request: AgentShareRequest,
    request: Request,
    current_user: CurrentUser
):
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Prevent self-sharing
    current_user_data = db.get_user_by_username(current_user.username)
    current_user_email = (current_user_data.get("email") or "") if current_user_data else ""
    if current_user_email and current_user_email.lower() == share_request.email.lower():
        raise HTTPException(status_code=400, detail="Cannot share an agent with yourself")

    share = db.share_agent(agent_name, current_user.username, share_request.email)
    if not share:
        raise HTTPException(status_code=409, detail=f"Agent is already shared with {share_request.email}")

    # Auto-add email to whitelist if email auth is enabled (Phase 12.4)
    from config import EMAIL_AUTH_ENABLED
    email_auth_setting = db.get_setting_value("email_auth_enabled", str(EMAIL_AUTH_ENABLED).lower())
    if email_auth_setting.lower() == "true":
        try:
            db.add_to_whitelist(share_request.email, current_user.username, source="agent_sharing")
        except Exception:
            pass  # Already whitelisted or error - continue anyway

    if manager:
        await manager.broadcast(json.dumps({
            "event": "agent_shared",
            "data": {"name": agent_name, "shared_with": share_request.email}
        }))

    return share
```

### Remove Share (`routers/sharing.py:67-89`)
```python
@router.delete("/{agent_name}/share/{email}")
async def unshare_agent_endpoint(
    agent_name: OwnedAgentByName,
    email: str,
    request: Request,
    current_user: CurrentUser
):
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    success = db.unshare_agent(agent_name, current_user.username, email)
    if not success:
        raise HTTPException(status_code=404, detail=f"No sharing found for {email}")

    if manager:
        await manager.broadcast(json.dumps({
            "event": "agent_unshared",
            "data": {"name": agent_name, "removed_user": email}
        }))

    return {"message": f"Sharing removed for {email}"}
```

### Access Control in Get Agent (`routers/agents.py:187-201`)

Access levels are computed when fetching a single agent:
```python
owner = db.get_agent_owner(agent_name)
agent_dict["owner"] = owner["owner_username"] if owner else None
agent_dict["is_owner"] = owner and owner["owner_username"] == current_user.username
agent_dict["is_shared"] = not agent_dict["is_owner"] and not is_admin and \
                           db.is_agent_shared_with_user(agent_name, current_user.username)
agent_dict["is_system"] = owner.get("is_system", False) if owner else False
agent_dict["can_share"] = db.can_user_share_agent(current_user.username, agent_name)
agent_dict["can_delete"] = db.can_user_delete_agent(current_user.username, agent_name)

if agent_dict["can_share"]:
    shares = db.get_agent_shares(agent_name)
    agent_dict["shares"] = [s.dict() for s in shares]
```

### Agent List Access Control (`services/agent_service/helpers.py:83-153`)

Uses optimized batch query to avoid N+1 problem:
```python
def get_accessible_agents(current_user: User) -> list:
    # Single batch query for ALL agent metadata
    all_metadata = db.get_all_agent_metadata(user_email)

    for agent in all_agents:
        metadata = all_metadata.get(agent_name)
        is_owner = owner_username == current_user.username
        is_shared = bool(metadata.get("is_shared_with_user"))

        # Skip if no access (not admin, not owner, not shared)
        if not (is_admin or is_owner or is_shared):
            continue

        agent_dict["is_owner"] = is_owner
        agent_dict["is_shared"] = is_shared and not is_owner and not is_admin
```

---

## Database Layer (`src/backend/db/agents.py`)

Database operations are in the `AgentOperations` class.

### Schema
```sql
CREATE TABLE IF NOT EXISTS agent_sharing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    shared_with_email TEXT NOT NULL,
    shared_by_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(agent_name, shared_with_email),
    FOREIGN KEY (shared_by_id) REFERENCES users(id)
)
```

### Operations (`db/agents.py`)

| Method | Line | Purpose |
|--------|------|---------|
| `share_agent()` | 169-212 | Create share record |
| `unshare_agent()` | 214-227 | Remove share record |
| `get_agent_shares()` | 229-241 | List shares for agent |
| `get_shared_agents()` | 243-258 | Get agents shared with user |
| `is_agent_shared_with_user()` | 260-276 | Access check by email |
| `can_user_share_agent()` | 278-288 | Authorization check |
| `delete_agent_shares()` | 290-296 | Cascade delete shares |
| `get_all_agent_metadata()` | 467-529 | Batch metadata query (N+1 fix) |

### Share Agent (`db/agents.py:169-212`)
```python
def share_agent(self, agent_name: str, owner_username: str, share_with_email: str) -> Optional[AgentShare]:
    owner = self._user_ops.get_user_by_username(owner_username)
    if not owner:
        return None

    # Check if user can share (owner or admin)
    if not self.can_user_share_agent(owner_username, agent_name):
        return None

    # Prevent self-sharing
    owner_email = owner.get("email") or ""
    if owner_email and owner_email.lower() == share_with_email.lower():
        return None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO agent_sharing (agent_name, shared_with_email, shared_by_id, created_at)
                VALUES (?, ?, ?, ?)
            """, (agent_name, share_with_email.lower(), owner["id"], now))
            conn.commit()
            return AgentShare(...)
        except sqlite3.IntegrityError:
            return None  # Already shared
```

### Cascade Delete (`db/agents.py:290-296`)
When an agent is deleted, all sharing records are removed via `delete_agent_ownership()` (line 103-112):
```python
def delete_agent_ownership(self, agent_name: str) -> bool:
    """Remove agent ownership record and all sharing records."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Delete sharing records first (cascade)
        cursor.execute("DELETE FROM agent_sharing WHERE agent_name = ?", (agent_name,))
        # Delete ownership record
        cursor.execute("DELETE FROM agent_ownership WHERE agent_name = ?", (agent_name,))
```

---

## Access Levels

| Level | View | Start/Stop | Delete | Share | Git Pull | Git Sync/Init |
|-------|------|------------|--------|-------|----------|---------------|
| Owner | Yes | Yes | Yes | Yes | Yes | Yes |
| Shared | Yes | Yes | No | No | Yes | No |
| Admin | Yes | Yes | Yes (non-system) | Yes | Yes | Yes |

> **Note (2026-01-30)**: Git Pull was changed from Owner-only to Authorized (owner/shared/admin). See [github-sync.md](github-sync.md) for details.

---

## Side Effects

### WebSocket Broadcasts
| Event | Payload |
|-------|---------|
| `agent_shared` | `{name, shared_with}` |
| `agent_unshared` | `{name, removed_user}` |

### Auto-Whitelist (Phase 12.4)
When email auth is enabled, shared emails are automatically added to the whitelist (`routers/sharing.py:44-56`):
```python
if email_auth_setting.lower() == "true":
    try:
        db.add_to_whitelist(share_request.email, current_user.username, source="agent_sharing")
    except Exception:
        pass  # Already whitelisted or error - continue anyway
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Agent not found | 404 | "Agent not found" |
| Not authorized to share | 403 | "Owner access required" |
| Share not found | 404 | "No sharing found for {email}" |
| Already shared | 409 | "Agent is already shared with {email}" |
| Self-sharing | 400 | "Cannot share an agent with yourself" |

---

## Security Considerations

1. **Email-Based Sharing**: Shares with users who haven't registered yet (future-proofing)
2. **Owner-Only Sharing**: Only owners and admins can share (`OwnedAgentByName` dependency)
3. **Cascade Delete**: Shares removed when agent deleted
4. **Access Validation**: Every endpoint validates via `OwnedAgentByName` dependency
5. **Auto-Whitelist**: When email auth is enabled, shared emails are auto-added to whitelist
6. **System Agent Protection**: System agents cannot be shared (tab hidden in UI)

---

## Testing

### Manual Testing
```bash
# Share an agent
curl -X POST http://localhost:8000/api/agents/my-agent/share \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "colleague@example.com"}'

# List shares
curl http://localhost:8000/api/agents/my-agent/shares \
  -H "Authorization: Bearer $TOKEN"

# Remove share
curl -X DELETE http://localhost:8000/api/agents/my-agent/share/colleague@example.com \
  -H "Authorization: Bearer $TOKEN"

# Verify shared user can see agent
curl http://localhost:8000/api/agents \
  -H "Authorization: Bearer $SHARED_USER_TOKEN"
```

---

## Status
Working - Agent sharing fully functional with email-based collaboration

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-02-18 | **Public Links tab consolidated**: Public Links tab removed from AgentDetail.vue. SharingPanel.vue now includes PublicLinksPanel as embedded component (lines 79-83, 92). Updated tab visibility line numbers (506-509). Single "Sharing" tab now contains both Team Sharing and Public Links sections. |
| 2026-01-30 | **Git Pull permission update**: Added Git Pull and Git Sync/Init columns to Access Levels table. Shared users can now pull from GitHub (was owner-only). |
| 2026-01-23 | **Full verification**: Updated to use SharingPanel.vue component (not inline in AgentDetail.vue). Updated line numbers for routers/sharing.py (23-64, 67-89, 92-103). Added useAgentSharing.js composable documentation. Updated db/agents.py line numbers for sharing methods. Added OwnedAgentByName dependency documentation from dependencies.py. Documented tab visibility logic at AgentDetail.vue:428-432. Updated helpers.py reference for batch metadata query. |
| 2025-12-30 | Flow verification: Updated line numbers for routers/sharing.py. Updated database layer to reference db/agents.py. Added auto-whitelist feature note. |

---

## Related Flows

- **Upstream**: Authentication (user identity)
- **Downstream**: Public Agent Links (embedded in same tab via PublicLinksPanel)
- **Related**: Agent Lifecycle (delete cascades shares), MCP Orchestration (agent-to-agent access control), Email Authentication (auto-whitelist)
