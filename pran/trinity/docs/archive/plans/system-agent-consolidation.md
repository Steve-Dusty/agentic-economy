# Plan: System Agent UI Consolidation

> **Goal**: Remove the separate `/system-agent` page and integrate the system agent into the regular agents interface, giving it access to Schedules and other standard tabs.
>
> **Created**: 2026-01-13
> **Status**: Draft

---

## Summary

Currently, `trinity-system` has its own dedicated page (`SystemAgent.vue`) with fleet stats, OTel metrics, quick actions, and a terminal. However, it lacks the Schedules tab available to regular agents.

This plan consolidates the system agent into the regular agent interface:
- System agent appears in the Agents list (pinned at top, admin-only visibility)
- System agent uses `AgentDetail.vue` with full tab access (including Schedules)
- System-specific features (fleet stats, OTel, quick actions) move to Dashboard/Settings
- Remove the dedicated `/system-agent` route and `SystemAgent.vue`

---

## Current State

### SystemAgent.vue Features
| Feature | Current Location | Future Location |
|---------|------------------|-----------------|
| Fleet status bar | SystemAgent.vue header | Dashboard page (future) |
| OTel metrics | Collapsible section | Settings page (future) |
| Quick actions (Emergency Stop, Restart All, Pause/Resume Schedules) | Terminal header | Settings page (future) |
| System terminal | SystemAgentTerminal.vue | AgentDetail TerminalPanelContent |

### Files Involved
| File | Lines | Purpose |
|------|-------|---------|
| `src/frontend/src/views/SystemAgent.vue` | 782 | Dedicated system agent page |
| `src/frontend/src/components/SystemAgentTerminal.vue` | ~350 | WebSocket terminal for system agent |
| `src/frontend/src/router/index.js:78-82` | 5 | `/system-agent` route |
| `src/frontend/src/components/NavBar.vue:53-60` | 8 | "System" link (admin-only) |
| `src/frontend/src/stores/agents.js:20-23` | 4 | Filters out system agent |
| `src/frontend/src/views/AgentDetail.vue:414-443` | 30 | `visibleTabs` computed property |

---

## Changes Required

### 1. Router - Remove System Agent Route
**File**: `src/frontend/src/router/index.js`

```javascript
// REMOVE this route (lines 78-82):
{
  path: '/system-agent',
  name: 'SystemAgent',
  component: () => import('../views/SystemAgent.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
},
```

No redirect needed - the `/system-agent` URL will naturally 404 and fall through to dashboard.

### 2. NavBar - Remove System Link
**File**: `src/frontend/src/components/NavBar.vue`

```html
<!-- REMOVE this link (lines 53-60): -->
<router-link
  v-if="isAdmin"
  to="/system-agent"
  class="..."
>
  System
</router-link>
```

### 3. Agents Store - Show System Agent for Admins
**File**: `src/frontend/src/stores/agents.js`

**Current behavior** (line 22):
```javascript
userAgents() {
  return this.agents.filter(agent => !agent.is_system)
}
```

**New behavior** - Add a getter that includes system agent for admins:
```javascript
// Keep existing userAgents for backward compatibility
userAgents() {
  return this.agents.filter(agent => !agent.is_system)
},

// New: All agents including system (for admin views)
allAgentsWithSystem() {
  return this.agents
},

// Modify sortedAgents to optionally include system agent
sortedAgents(includeSystem = false) {
  // ... existing sort logic
}
```

**Or simpler approach**: Just remove the filter and let the UI decide:
```javascript
// Change sortedAgents (lines 30-53) to pin system agent at top:
sortedAgents() {
  const systemAgent = this.agents.find(a => a.is_system)
  const regularAgents = this.agents.filter(a => !a.is_system)

  // Sort regular agents as before
  const sorted = [...regularAgents]
  switch (this.sortBy) {
    // ... existing sort cases
  }

  // Pin system agent at top if exists
  return systemAgent ? [systemAgent, ...sorted] : sorted
}
```

### 4. Agents.vue - Show System Agent (Admin Only)
**File**: `src/frontend/src/views/Agents.vue`

Add admin check and visual distinction for system agent in the grid:

```javascript
// Add in script setup:
const isAdmin = ref(false)

onMounted(async () => {
  // Check admin status
  try {
    const response = await axios.get('/api/users/me')
    isAdmin.value = response.data.role === 'admin'
  } catch (e) {
    isAdmin.value = false
  }
})

// Computed to filter system agent for non-admins:
const displayAgents = computed(() => {
  if (isAdmin.value) {
    return agentsStore.sortedAgents  // Includes system agent pinned at top
  }
  return agentsStore.sortedAgents.filter(a => !a.is_system)
})
```

In template, add visual distinction:
```html
<div
  v-for="agent in displayAgents"
  :key="agent.name"
  :class="[
    // ... existing classes
    agent.is_system ? 'ring-2 ring-purple-500/50' : ''
  ]"
>
  <!-- Add SYSTEM badge next to name for system agent -->
  <span
    v-if="agent.is_system"
    class="ml-2 px-1.5 py-0.5 text-xs font-semibold bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300 rounded"
  >
    SYSTEM
  </span>
</div>
```

### 5. AgentDetail.vue - Hide Tabs for System Agent
**File**: `src/frontend/src/views/AgentDetail.vue`

Modify `visibleTabs` computed (lines 414-443):

```javascript
const visibleTabs = computed(() => {
  const isSystem = agent.value?.is_system

  const tabs = [
    { id: 'info', label: 'Info' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'terminal', label: 'Terminal' },
    { id: 'logs', label: 'Logs' },
    { id: 'credentials', label: 'Credentials' }
  ]

  // Sharing/Permissions - hide for system agent
  if (agent.value?.can_share && !isSystem) {
    tabs.push({ id: 'sharing', label: 'Sharing' })
    tabs.push({ id: 'permissions', label: 'Permissions' })
  }

  // Schedules - show for all agents including system
  tabs.push({ id: 'schedules', label: 'Schedules' })

  if (hasGitSync.value) {
    tabs.push({ id: 'git', label: 'Git' })
  }

  tabs.push({ id: 'files', label: 'Files' })

  // Folders and Public Links - hide for system agent
  if (agent.value?.can_share && !isSystem) {
    tabs.push({ id: 'folders', label: 'Folders' })
    tabs.push({ id: 'public-links', label: 'Public Links' })
  }

  return tabs
})
```

**Tabs Hidden for System Agent**:
- Sharing (system agent shouldn't be shared)
- Permissions (system agent has full access)
- Folders (system agent manages folders, doesn't consume them)
- Public Links (system agent shouldn't be publicly accessible)

**Tabs Shown for System Agent**:
- Info, Tasks, Dashboard, Terminal, Logs, Credentials, Schedules, Git, Files

### 6. AgentHeader.vue - Already Handles System Agent
**File**: `src/frontend/src/components/AgentHeader.vue`

Already has:
- SYSTEM badge display (line 16-22)
- Autonomy toggle hidden for system agents (line 135)
- Delete controlled by `can_delete` prop

No changes needed here.

---

## Files to Delete (After Verification)

After the migration is complete and tested:

| File | Reason |
|------|--------|
| `src/frontend/src/views/SystemAgent.vue` | Replaced by AgentDetail |
| `src/frontend/src/components/SystemAgentTerminal.vue` | Uses standard TerminalPanelContent |

---

## Future Work (Out of Scope)

These features from SystemAgent.vue should be migrated elsewhere in future work:

### Dashboard Page
- Fleet status overview (total agents, running, stopped, issues)
- Quick actions (Emergency Stop, Restart All)

### Settings Page
- OTel metrics visualization
- Schedule management (Pause All, Resume All)

---

## Implementation Order

1. **Agents Store** - Modify `sortedAgents` to pin system agent at top
2. **Agents.vue** - Add admin check, show system agent with visual distinction
3. **AgentDetail.vue** - Hide irrelevant tabs for system agent
4. **NavBar.vue** - Remove "System" link
5. **Router** - Remove `/system-agent` route
6. **Test** - Verify system agent accessible via `/agents/trinity-system`
7. **Cleanup** - Delete SystemAgent.vue and SystemAgentTerminal.vue

---

## Testing Checklist

### Prerequisites
- [ ] Admin user logged in
- [ ] System agent deployed and running

### Test Steps

| # | Action | Expected |
|---|--------|----------|
| 1 | Login as admin | Dashboard loads |
| 2 | Navigate to /agents | System agent visible at top with SYSTEM badge |
| 3 | Click system agent | Opens /agents/trinity-system |
| 4 | Check tabs | Info, Tasks, Dashboard, Terminal, Logs, Credentials, Schedules, Git, Files visible |
| 5 | Check tabs NOT shown | Sharing, Permissions, Folders, Public Links hidden |
| 6 | Go to Schedules tab | Can create/edit/delete schedules for system agent |
| 7 | Go to Terminal tab | Terminal works (same as before) |
| 8 | Login as non-admin | Dashboard loads |
| 9 | Navigate to /agents | System agent NOT visible |
| 10 | Navigate directly to /agents/trinity-system | Should show 403 or redirect (backend enforces admin-only) |

### Edge Cases
- [ ] System agent not deployed: Agents page still works
- [ ] Direct URL access by non-admin: Properly blocked
- [ ] NavBar no longer shows "System" link
- [ ] Old /system-agent URL returns 404 (or redirects to /)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing system agent access | Low | Medium | Test before removing old route |
| Non-admin sees system agent | Low | Low | Backend already enforces access |
| Missing quick actions | Medium | Low | Document for future Settings page work |
| Regression in agent list | Low | Medium | System agent was already filtered out |

---

## Rollback Plan

If issues arise:
1. Restore `/system-agent` route in router
2. Restore "System" link in NavBar
3. Revert agents store changes
4. Keep SystemAgent.vue files

The changes are isolated to frontend only - no backend changes required.
