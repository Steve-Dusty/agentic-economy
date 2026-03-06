# Implementation Requirements: Agent Credential Assignment

**Status**: Draft
**Author**: Claude
**Date**: 2025-12-30

---

## Problem Statement

Currently, all credentials (API keys and file-type) are automatically injected into every agent a user creates. There is no way to control which credentials go to which agents.

**Current behavior:**
- `get_file_credentials(user_id)` returns ALL file credentials
- `get_agent_credentials(agent_name, mcp_servers, user_id)` returns ALL user credentials
- No assignment mechanism exists for selecting specific credentials per agent

**Desired behavior:**
- User explicitly assigns credentials to specific agents
- No credentials assigned by default
- Full control via UI (and later MCP)

---

## Scope

### In Scope
- API key credentials (`type: api_key, token`)
- File-type credentials (`type: file`)
- OAuth2 credentials (`type: oauth2`) - included if implementation is straightforward

### Out of Scope
- MCP server credential assignment (already exists, different pattern)
- Credential creation/editing (already works)
- Agent creation flow changes (assignment happens post-creation)

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | Redis keys | Consistent with existing MCP assignment pattern |
| Default behavior | No credentials assigned | Explicit user control required |
| Backward compatibility | Not required | Clean slate approach |
| UI location | Replace Hot Reload tab | Single unified Credentials tab |
| Assignment granularity | Per-credential | User selects individual credentials |

---

## Data Model

### Redis Key Pattern

```
# Credential assignment (new)
agent:{agent_name}:credentials → SET of credential IDs

# Existing patterns (unchanged)
credentials:{cred_id}:metadata → HASH
credentials:{cred_id}:secret → STRING
user:{user_id}:credentials → SET of credential IDs
```

### Assignment Record

No separate metadata needed - just the SET membership indicates assignment.

---

## API Endpoints

### New Endpoints

#### 1. List Available & Assigned Credentials
```
GET /api/agents/{agent_name}/credentials/assignments

Response:
{
  "agent_name": "my-agent",
  "assigned": [
    {
      "id": "abc123",
      "name": "OPENAI_API_KEY",
      "service": "openai",
      "type": "api_key",
      "file_path": null
    },
    {
      "id": "def456",
      "name": "GCP Service Account",
      "service": "google",
      "type": "file",
      "file_path": ".config/gcloud/service-account.json"
    }
  ],
  "available": [
    {
      "id": "ghi789",
      "name": "HEYGEN_API_KEY",
      "service": "heygen",
      "type": "api_key",
      "file_path": null
    }
  ]
}
```

#### 2. Assign Credential to Agent
```
POST /api/agents/{agent_name}/credentials/assign

Request:
{
  "credential_id": "abc123"
}

Response:
{
  "message": "Credential assigned to agent",
  "credential_id": "abc123",
  "agent_name": "my-agent"
}
```

#### 3. Unassign Credential from Agent
```
DELETE /api/agents/{agent_name}/credentials/assign/{credential_id}

Response:
{
  "message": "Credential unassigned from agent",
  "credential_id": "abc123",
  "agent_name": "my-agent"
}
```

#### 4. Bulk Assign Credentials
```
POST /api/agents/{agent_name}/credentials/assign/bulk

Request:
{
  "credential_ids": ["abc123", "def456", "ghi789"]
}

Response:
{
  "message": "Credentials assigned to agent",
  "assigned_count": 3,
  "credential_ids": ["abc123", "def456", "ghi789"]
}
```

#### 5. Apply Credentials to Running Agent
```
POST /api/agents/{agent_name}/credentials/apply

Response:
{
  "message": "Credentials applied to running agent",
  "credential_count": 3,
  "updated_files": [".env", ".mcp.json", ".config/gcloud/service-account.json"],
  "note": "MCP servers may need restart"
}
```

### Modified Endpoints

#### Hot-Reload (Repurposed)
The existing hot-reload endpoint remains but is enhanced:
- Still accepts KEY=VALUE text for quick ad-hoc additions
- Creates credentials in Redis AND assigns them to this agent
- Calls apply automatically after assignment

### Deprecated Endpoints
None - existing endpoints continue to work.

---

## Backend Changes

### File: `src/backend/credentials.py`

Add to `CredentialManager` class:

```python
def assign_credential(self, agent_name: str, cred_id: str, user_id: str) -> bool:
    """Assign a credential to an agent."""
    # Verify credential exists and belongs to user
    cred = self.get_credential(cred_id, user_id)
    if not cred:
        return False

    # Add to agent's credential set
    agent_creds_key = f"agent:{agent_name}:credentials"
    self.redis_client.sadd(agent_creds_key, cred_id)
    return True

def unassign_credential(self, agent_name: str, cred_id: str) -> bool:
    """Unassign a credential from an agent."""
    agent_creds_key = f"agent:{agent_name}:credentials"
    removed = self.redis_client.srem(agent_creds_key, cred_id)
    return removed > 0

def get_assigned_credentials(self, agent_name: str, user_id: str) -> List[Credential]:
    """Get credentials assigned to an agent."""
    agent_creds_key = f"agent:{agent_name}:credentials"
    cred_ids = self.redis_client.smembers(agent_creds_key)

    credentials = []
    for cred_id in cred_ids:
        cred = self.get_credential(cred_id, user_id)
        if cred:
            credentials.append(cred)
    return credentials

def get_assigned_credential_values(self, agent_name: str, user_id: str) -> Dict[str, str]:
    """Get credential key-value pairs for assigned credentials only."""
    assigned = self.get_assigned_credentials(agent_name, user_id)
    values = {}

    for cred in assigned:
        if cred.type == "file":
            continue  # File credentials handled separately

        secret = self.get_credential_secret(cred.id, user_id)
        if secret:
            for key, value in secret.items():
                values[key.upper()] = value

    return values

def get_assigned_file_credentials(self, agent_name: str, user_id: str) -> Dict[str, str]:
    """Get file credentials assigned to an agent.
    Returns: {file_path: file_content}
    """
    assigned = self.get_assigned_credentials(agent_name, user_id)
    file_creds = {}

    for cred in assigned:
        if cred.type != "file" or not cred.file_path:
            continue

        secret = self.get_credential_secret(cred.id, user_id)
        if secret and "content" in secret:
            file_creds[cred.file_path] = secret["content"]

    return file_creds

def cleanup_agent_credentials(self, agent_name: str) -> int:
    """Remove all credential assignments for an agent (called on agent deletion)."""
    agent_creds_key = f"agent:{agent_name}:credentials"
    count = self.redis_client.scard(agent_creds_key)
    self.redis_client.delete(agent_creds_key)
    return count
```

### File: `src/backend/routers/credentials.py`

Add new endpoints (see API section above).

Modify existing credential retrieval to use assigned credentials:
- `reload_agent_credentials`: Use `get_assigned_credential_values()` and `get_assigned_file_credentials()`
- `hot_reload_credentials`: Keep text parsing, but also assign created credentials to agent

### File: `src/backend/services/agent_service/crud.py`

Modify `create_agent_internal()`:

```python
# Line ~175: Change from getting ALL credentials to assigned only
# OLD:
# agent_credentials = credential_manager.get_agent_credentials(config.name, config.mcp_servers, current_user.username)

# NEW:
agent_credentials = credential_manager.get_assigned_credential_values(config.name, current_user.username)

# Line ~193: Change from getting ALL file credentials to assigned only
# OLD:
# file_credentials = credential_manager.get_file_credentials(current_user.username)

# NEW:
file_credentials = credential_manager.get_assigned_file_credentials(config.name, current_user.username)
```

---

## Frontend Changes

### File: `src/frontend/src/stores/agents.js`

Add new actions:

```javascript
// Get credentials with assignment status
async getCredentialAssignments(agentName) {
  const response = await axios.get(
    `/api/agents/${agentName}/credentials/assignments`,
    { headers: authStore.authHeader }
  )
  return response.data
},

// Assign credential to agent
async assignCredential(agentName, credentialId) {
  const response = await axios.post(
    `/api/agents/${agentName}/credentials/assign`,
    { credential_id: credentialId },
    { headers: authStore.authHeader }
  )
  return response.data
},

// Unassign credential from agent
async unassignCredential(agentName, credentialId) {
  const response = await axios.delete(
    `/api/agents/${agentName}/credentials/assign/${credentialId}`,
    { headers: authStore.authHeader }
  )
  return response.data
},

// Apply credentials to running agent
async applyCredentials(agentName) {
  const response = await axios.post(
    `/api/agents/${agentName}/credentials/apply`,
    {},
    { headers: authStore.authHeader }
  )
  return response.data
}
```

### File: `src/frontend/src/composables/useAgentCredentials.js`

Rewrite to support new functionality:

```javascript
export function useAgentCredentials(agentRef, agentsStore, showNotification) {
  const assignedCredentials = ref([])
  const availableCredentials = ref([])
  const loading = ref(false)
  const applying = ref(false)
  const hasChanges = ref(false)

  // Quick-add functionality (replaces hot-reload)
  const quickAddText = ref('')
  const quickAddLoading = ref(false)

  const loadCredentials = async () => {
    if (!agentRef.value) return
    loading.value = true
    try {
      const data = await agentsStore.getCredentialAssignments(agentRef.value.name)
      assignedCredentials.value = data.assigned
      availableCredentials.value = data.available
    } finally {
      loading.value = false
    }
  }

  const assignCredential = async (credentialId) => {
    await agentsStore.assignCredential(agentRef.value.name, credentialId)
    hasChanges.value = true
    await loadCredentials()
  }

  const unassignCredential = async (credentialId) => {
    await agentsStore.unassignCredential(agentRef.value.name, credentialId)
    hasChanges.value = true
    await loadCredentials()
  }

  const applyToAgent = async () => {
    if (agentRef.value?.status !== 'running') return
    applying.value = true
    try {
      const result = await agentsStore.applyCredentials(agentRef.value.name)
      hasChanges.value = false
      showNotification('Credentials applied successfully', 'success')
      return result
    } finally {
      applying.value = false
    }
  }

  const quickAddCredentials = async () => {
    // Parse, create, assign, and apply in one step
    // Uses existing hot-reload endpoint which now also assigns
    if (!quickAddText.value.trim()) return
    quickAddLoading.value = true
    try {
      await agentsStore.hotReloadCredentials(agentRef.value.name, quickAddText.value)
      quickAddText.value = ''
      await loadCredentials()
      showNotification('Credentials added and applied', 'success')
    } finally {
      quickAddLoading.value = false
    }
  }

  return {
    assignedCredentials,
    availableCredentials,
    loading,
    applying,
    hasChanges,
    quickAddText,
    quickAddLoading,
    loadCredentials,
    assignCredential,
    unassignCredential,
    applyToAgent,
    quickAddCredentials
  }
}
```

### File: `src/frontend/src/views/AgentDetail.vue`

Replace the Credentials tab content (lines ~529-710):

```vue
<!-- Credentials Tab Content -->
<div v-if="activeTab === 'credentials'" class="p-6 space-y-6">

  <!-- Assigned Credentials Section -->
  <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
    <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
      <h3 class="text-lg font-medium text-gray-900 dark:text-white">
        Assigned Credentials
        <span class="ml-2 text-sm text-gray-500">({{ assignedCredentials.length }})</span>
      </h3>
      <button
        v-if="hasChanges && agent.status === 'running'"
        @click="applyToAgent"
        :disabled="applying"
        class="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
      >
        {{ applying ? 'Applying...' : 'Apply to Agent' }}
      </button>
    </div>

    <div v-if="loading" class="p-4 text-center text-gray-500">Loading...</div>

    <div v-else-if="assignedCredentials.length === 0" class="p-4 text-center text-gray-500">
      No credentials assigned to this agent.
    </div>

    <div v-else class="divide-y divide-gray-200 dark:divide-gray-700">
      <div
        v-for="cred in assignedCredentials"
        :key="cred.id"
        class="px-4 py-3 flex items-center justify-between"
      >
        <div>
          <div class="font-medium text-gray-900 dark:text-white">{{ cred.name }}</div>
          <div class="text-sm text-gray-500">
            {{ cred.service }} · {{ cred.type }}
            <span v-if="cred.file_path" class="ml-2 font-mono text-xs">
              → {{ cred.file_path }}
            </span>
          </div>
        </div>
        <button
          @click="unassignCredential(cred.id)"
          class="text-red-600 hover:text-red-700 text-sm"
        >
          Remove
        </button>
      </div>
    </div>
  </div>

  <!-- Available Credentials Section -->
  <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
    <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
      <h3 class="text-lg font-medium text-gray-900 dark:text-white">
        Available Credentials
        <span class="ml-2 text-sm text-gray-500">({{ availableCredentials.length }})</span>
      </h3>
    </div>

    <div v-if="availableCredentials.length === 0" class="p-4 text-center text-gray-500">
      All credentials are assigned.
      <router-link to="/credentials" class="text-blue-600 hover:underline">
        Create more credentials
      </router-link>
    </div>

    <div v-else class="divide-y divide-gray-200 dark:divide-gray-700">
      <div
        v-for="cred in availableCredentials"
        :key="cred.id"
        class="px-4 py-3 flex items-center justify-between"
      >
        <div>
          <div class="font-medium text-gray-900 dark:text-white">{{ cred.name }}</div>
          <div class="text-sm text-gray-500">
            {{ cred.service }} · {{ cred.type }}
            <span v-if="cred.file_path" class="ml-2 font-mono text-xs">
              → {{ cred.file_path }}
            </span>
          </div>
        </div>
        <button
          @click="assignCredential(cred.id)"
          class="text-blue-600 hover:text-blue-700 text-sm"
        >
          + Add
        </button>
      </div>
    </div>
  </div>

  <!-- Quick Add Section (formerly Hot Reload) -->
  <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
    <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
      <h3 class="text-lg font-medium text-gray-900 dark:text-white">Quick Add</h3>
      <p class="text-sm text-gray-500">
        Paste KEY=VALUE pairs to create and assign credentials in one step
      </p>
    </div>
    <div class="p-4 space-y-3">
      <textarea
        v-model="quickAddText"
        :disabled="agent.status !== 'running' || quickAddLoading"
        rows="4"
        placeholder="OPENAI_API_KEY=sk-...&#10;ANTHROPIC_API_KEY=sk-ant-..."
        class="w-full font-mono text-sm rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700"
      ></textarea>
      <div class="flex justify-between items-center">
        <span class="text-sm text-gray-500">
          {{ countLines(quickAddText) }} credentials detected
        </span>
        <button
          @click="quickAddCredentials"
          :disabled="agent.status !== 'running' || quickAddLoading || !quickAddText.trim()"
          class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
        >
          {{ quickAddLoading ? 'Adding...' : 'Add & Apply' }}
        </button>
      </div>
    </div>
  </div>

</div>
```

---

## Agent Deletion Cleanup

When an agent is deleted, clean up credential assignments:

### File: `src/backend/services/agent_service/crud.py`

In the agent deletion function, add:

```python
# Clean up credential assignments
credential_manager.cleanup_agent_credentials(agent_name)
```

---

## Testing

### Unit Tests

1. `test_assign_credential` - Verify credential can be assigned
2. `test_unassign_credential` - Verify credential can be unassigned
3. `test_get_assigned_credentials` - Verify only assigned credentials returned
4. `test_get_assigned_file_credentials` - Verify only assigned file credentials returned
5. `test_cleanup_on_delete` - Verify assignments cleaned up when agent deleted

### Integration Tests

1. Create agent with no credentials → Verify empty injection
2. Assign credentials → Verify stored in Redis
3. Apply credentials → Verify files written to agent
4. Unassign credential → Verify removed from agent on next apply
5. Delete agent → Verify assignments cleaned up

### Manual Tests

1. Create credentials in Credentials page
2. Create agent (verify no credentials injected)
3. Go to agent Credentials tab
4. Assign credentials from Available list
5. Click "Apply to Agent"
6. Verify agent has credentials (check .env, .mcp.json)
7. Use Quick Add to add new credential
8. Verify new credential created AND assigned

---

## Migration Notes

**No migration required.**

Existing agents will have no credentials assigned. Users must explicitly assign credentials after this change is deployed.

This is intentional per the requirement: "No backward compatibility needed."

---

## Implementation Order

1. **Backend: CredentialManager methods** (`credentials.py`)
   - `assign_credential()`
   - `unassign_credential()`
   - `get_assigned_credentials()`
   - `get_assigned_credential_values()`
   - `get_assigned_file_credentials()`
   - `cleanup_agent_credentials()`

2. **Backend: API endpoints** (`routers/credentials.py`)
   - `GET /agents/{name}/credentials/assignments`
   - `POST /agents/{name}/credentials/assign`
   - `DELETE /agents/{name}/credentials/assign/{cred_id}`
   - `POST /agents/{name}/credentials/apply`

3. **Backend: Update injection** (`crud.py`)
   - Modify `create_agent_internal()` to use assigned credentials only

4. **Backend: Cleanup on delete**
   - Add `cleanup_agent_credentials()` call to deletion

5. **Frontend: Store actions** (`agents.js`)
   - Add new API methods

6. **Frontend: Composable** (`useAgentCredentials.js`)
   - Rewrite for assignment-based flow

7. **Frontend: UI** (`AgentDetail.vue`)
   - Replace Credentials tab content

8. **Testing**
   - Unit tests
   - Integration tests
   - Manual verification

---

## Open Questions

1. **Should credentials be automatically applied when assigned?**
   - Current design: No, user clicks "Apply to Agent"
   - Alternative: Auto-apply on assignment (if agent running)

2. **Should Quick Add also save to credential store?**
   - Current design: Yes (reuses hot-reload which saves to Redis)
   - Alternative: Quick Add is ephemeral (agent-only, not stored)

3. **Credential visibility across agents?**
   - Current design: All user credentials visible to all their agents (for assignment)
   - Alternative: Credential groups/folders for organization

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-30 | Claude | Initial draft |
