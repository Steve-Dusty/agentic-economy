# Client/Viewer User Role

> **Requirement ID**: AUTH-002
> **Priority**: HIGH
> **Status**: ⏳ Not Started
> **Created**: 2026-02-05
> **Source**: `docs/planning/WORKFLOW_PRIORITIES_2026-02.md`

---

## Overview

Add a simplified "client" or "viewer" user role that provides read-only or limited access to shared agents. This enables sharing agents with paying clients using existing auth infrastructure without exposing the full platform complexity.

## Business Context

**Problem**: Current platform shows all features to all users. When sharing agents with clients (e.g., "Ruby for Client X"), they see:
- Collaboration Dashboard with complex graph visualization
- Process Engine with BPMN workflows
- Permissions, Shared Folders, and other advanced tabs
- Admin-only features that confuse non-technical users

**Solution**: A "client" role that sees a simplified UI focused on:
- Running their assigned agents
- Viewing execution history and results
- Accessing files produced by agents

**Strategic Value**: Enables Agent-as-a-Service business model without new infrastructure.

---

## Current State Analysis

### Existing Role System

**Database Schema** (`src/backend/database.py:363-376`):
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',  -- Currently: "user" or "admin"
    ...
)
```

**Current Roles**:
| Role | Count | Capabilities |
|------|-------|--------------|
| `admin` | 1 | Full access, settings, user management, all agents |
| `user` | Many | Own agents, shared agents, create agents, full UI |

**Access Control Functions** (`src/backend/db/agents.py:114-289`):
- `can_user_access_agent()` - Checks owner/admin/shared access
- `can_user_share_agent()` - Checks owner/admin only
- `can_user_delete_agent()` - Checks owner/admin (non-system)

**Frontend Role Checks**:
- Router guard (`router/index.js:191-239`) checks `requiresAuth` but NOT role
- Components fetch `/api/users/me` and check `role === 'admin'` manually
- No centralized role-based UI filtering

---

## Requirements

### R1: New "client" Role

**R1.1**: Add `client` as valid role value in users table
- Role hierarchy: `admin` > `user` > `client`
- Clients cannot be promoted to higher roles via UI (admin API only)

**R1.2**: Client role assignment
- Admin can set role when adding to email whitelist
- Admin can change existing user's role in Settings
- Default role remains `user` for backwards compatibility

### R2: Backend Access Control

**R2.1**: Client role permissions matrix

| Action | Admin | User | Client |
|--------|-------|------|--------|
| View shared agents | All | Own + shared | Shared only |
| Create agents | ✅ | ✅ | ❌ |
| Delete agents | All (non-sys) | Own (non-sys) | ❌ |
| Share agents | All | Own | ❌ |
| Execute shared agents | ✅ | ✅ | ✅ |
| View execution history | All | Own + shared | Shared only |
| View execution logs | All | Own + shared | Shared only |
| Access Files tab | All | Own + shared | Shared only |
| Access Terminal | All | Own + shared | ❌ |
| Access Settings | ✅ | ❌ | ❌ |
| Access API Keys | ✅ | ✅ | ❌ |
| Access Collaboration Dashboard | ✅ | ✅ | ❌ |
| Access Process Engine | ✅ | ✅ | ❌ |

**R2.2**: New access control functions
```python
# In db/agents.py
def can_user_execute_agent(username, agent_name) -> bool:
    """Clients can execute shared agents, users can execute own+shared"""

def can_user_access_terminal(username, agent_name) -> bool:
    """Clients cannot access terminal, even for shared agents"""
```

**R2.3**: API endpoint restrictions for clients
- Block: `POST /api/agents` (create)
- Block: `DELETE /api/agents/{name}` (delete)
- Block: `POST /api/agents/{name}/share` (share)
- Block: `GET /api/settings/*` (settings)
- Block: `POST /api/mcp/keys` (create API keys)
- Allow: All read operations on shared agents
- Allow: `POST /api/agents/{name}/task` on shared agents

### R3: Frontend UI Filtering

**R3.1**: Role-based route access
```javascript
// router/index.js - Add role checks
const roleRoutes = {
  '/settings': ['admin'],
  '/api-keys': ['admin', 'user'],
  '/collaboration': ['admin', 'user'],
  '/processes': ['admin', 'user'],
  '/process-dashboard': ['admin', 'user'],
  '/approvals': ['admin', 'user'],
  // ... client can access: /, /agents, /agents/:name, /files, /executions
}
```

**R3.2**: Navigation filtering
- Hide NavBar items based on role
- Client sees: Dashboard (simplified), Agents, Files
- Client doesn't see: Collaboration, Processes, Approvals, API Keys, Settings

**R3.3**: Agent Detail tab filtering for clients
- Show: Tasks, Files
- Hide: Terminal, Schedules, Sharing, Permissions, Folders, Git, Public Links, Info

**R3.4**: Auth store enhancements (`stores/auth.js`)
```javascript
getters: {
  isAdmin: (state) => state.user?.role === 'admin',
  isClient: (state) => state.user?.role === 'client',
  canCreateAgents: (state) => ['admin', 'user'].includes(state.user?.role),
  canAccessTerminal: (state) => ['admin', 'user'].includes(state.user?.role),
  canAccessAdvancedFeatures: (state) => ['admin', 'user'].includes(state.user?.role),
}
```

### R4: Admin User Management

**R4.1**: Role assignment in Settings
- New section in Settings: "User Management"
- List users with email, role, last login
- Dropdown to change role (admin only)
- Cannot demote self from admin

**R4.2**: Role pre-assignment in whitelist
- When adding email to whitelist, optionally specify role
- Default: `user`
- Options: `user`, `client`

---

## Implementation Plan

### Phase 1: Backend Foundation
1. Add `client` role validation in user creation
2. Implement `can_user_execute_agent()` function
3. Add role checks to sensitive endpoints
4. Create `require_user_or_admin` dependency (blocks clients)

### Phase 2: Frontend Role System
1. Add role getters to auth store
2. Implement route guard role checking
3. Filter NavBar based on role
4. Filter Agent Detail tabs based on role

### Phase 3: Admin UI
1. Add User Management section to Settings
2. Implement role change API endpoint
3. Add role field to whitelist management

### Phase 4: Testing
1. Create test user with client role
2. Verify all blocked actions return 403
3. Verify UI hides appropriate elements
4. Test execution flow works for clients

---

## Database Changes

```sql
-- No schema change needed - role column already exists
-- Just need to allow 'client' as valid value

-- For role pre-assignment in whitelist (optional enhancement):
ALTER TABLE email_whitelist ADD COLUMN default_role TEXT DEFAULT 'user';
```

---

## API Changes

### New Endpoints

```
PUT /api/users/{user_id}/role
  Body: { "role": "client" | "user" }
  Auth: Admin only
  Returns: Updated user object
```

### Modified Endpoints

All agent mutation endpoints add role check:
```python
@router.post("/api/agents")
async def create_agent(
    current_user: User = Depends(require_user_or_admin)  # Blocks clients
):
    ...
```

---

## Frontend Changes

### Files to Modify

| File | Change |
|------|--------|
| `stores/auth.js` | Add role getters |
| `router/index.js` | Add role-based route guards |
| `components/NavBar.vue` | Filter menu items by role |
| `views/AgentDetail.vue` | Filter tabs by role |
| `views/Agents.vue` | Hide "Create Agent" for clients |
| `views/Settings.vue` | Add User Management section |

### New Components

- `UserManagement.vue` - Admin panel for role assignment

---

## Security Considerations

1. **Role escalation prevention**: Clients cannot promote themselves
2. **API enforcement**: All restrictions enforced at API level, not just UI
3. **Audit logging**: Log role changes for compliance
4. **Token refresh**: Role changes take effect immediately (role fetched from DB per request)

---

## Testing Checklist

- [ ] Client cannot create agents (UI hidden, API returns 403)
- [ ] Client cannot delete agents (UI hidden, API returns 403)
- [ ] Client cannot share agents (UI hidden, API returns 403)
- [ ] Client cannot access Terminal tab
- [ ] Client cannot access Settings
- [ ] Client CAN execute tasks on shared agents
- [ ] Client CAN view execution history
- [ ] Client CAN download files
- [ ] Admin can change user roles
- [ ] Role changes take effect immediately

---

## Related Documents

- `docs/memory/feature-flows/email-authentication.md` - Current auth flow
- `docs/memory/feature-flows/admin-login.md` - Admin authentication
- `docs/memory/feature-flows/agent-sharing.md` - Sharing mechanism
- `docs/planning/WORKFLOW_PRIORITIES_2026-02.md` - Strategic context

---

## Success Criteria

1. A user with `client` role sees only: Dashboard, Agents list, Agent detail (Tasks/Files tabs)
2. Client can run tasks on shared agents and view results
3. Client cannot access any agent management or platform configuration
4. Admin can assign roles via Settings UI
5. No breaking changes for existing `user` and `admin` roles
