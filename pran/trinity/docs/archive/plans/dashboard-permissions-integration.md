# Implementation Plan: Dashboard Permissions Integration

> **Created**: 2025-12-30
> **Status**: Draft
> **Requirement**: Integrate Dashboard edge connections with agent permissions system

---

## Overview

Integrate the Dashboard's visual agent connections with the permissions system so that:
1. **Permission edges** show which agents CAN communicate
2. **Creating an edge** on Dashboard grants permission
3. **Deleting an edge** revokes permission
4. **Collaboration edges** (existing) show actual message flow (animated)

---

## Design Decisions

### Two Edge Types (Visual Distinction)

| Edge Type | Visual Style | Meaning | Source |
|-----------|--------------|---------|--------|
| **Permission** | Dashed, gray/blue | Agent A is permitted to call Agent B | `agent_permissions` table |
| **Collaboration** | Solid, animated, gradient | Agent A sent message to Agent B | `agent_activities` table |

**Rationale**: Keeps the distinction clear - permissions are potential, collaborations are actual.

### Permission Directionality

- **Unidirectional**: Creating A→B edge only grants A permission to call B
- **Matches existing system**: Permissions table is already unidirectional
- **For bidirectional**: User draws two edges (A→B and B→A) - explicit and clear

### Edge Creation Flow

```
User drags from Agent A handle → Agent B handle
    ↓
Immediately: POST /api/agents/{source}/permissions/{target}
    ↓
Dashed blue edge appears on Dashboard
    ↓
Toast notification: "Permission granted: A → B"
```

### Edge Deletion Flow

```
User clicks edge to select it → Edge highlights
    ↓
User presses Delete key (or Backspace)
    ↓
Immediately: DELETE /api/agents/{source}/permissions/{target}
    ↓
Edge removed from Dashboard
    ↓
Toast notification: "Permission revoked: A → B"
```

**No confirmation dialogs** - direct manipulation for fast workflow.

---

## Implementation Steps

### Phase 1: Network Store - Permission Edge Support

**File**: `src/frontend/src/stores/network.js`

**Changes**:

1. Add permission state:
```javascript
const permissionEdges = ref([])  // Edges from permissions
const collaborationEdges = ref([])  // Edges from collaboration history
```

2. Add `fetchPermissions()` action:
```javascript
async function fetchPermissions() {
  // For each agent, fetch its permissions
  // Create permission edges from the data
}
```

3. Add `createPermissionEdge(source, target)`:
```javascript
async function createPermissionEdge(source, target, bidirectional = false) {
  // POST /api/agents/{source}/permissions/{target}
  // If bidirectional, also POST reverse
  // Add edge to permissionEdges
}
```

4. Add `deletePermissionEdge(source, target)`:
```javascript
async function deletePermissionEdge(source, target) {
  // DELETE /api/agents/{source}/permissions/{target}
  // Remove from permissionEdges
}
```

5. Update `edges` computed to merge both types:
```javascript
const edges = computed(() => [
  ...permissionEdges.value,
  ...collaborationEdges.value.filter(e =>
    // Don't duplicate if permission edge exists for same pair
    !permissionEdges.value.some(p => p.source === e.source && p.target === e.target)
  )
])
```

### Phase 2: Dashboard - Enable Edge Creation

**File**: `src/frontend/src/views/Dashboard.vue`

**Changes**:

1. Add Vue Flow connection props:
```vue
<VueFlow
  ...
  :connect-on-click="true"
  @connect="onConnect"
  @edges-change="onEdgesChange"
>
```

2. Add connection handler (immediate, no dialog):
```javascript
import { useToast } from '@/composables/useToast'

const { showToast } = useToast()

async function onConnect(connection) {
  const { source, target } = connection

  // Prevent self-connections
  if (source === target) return

  try {
    await networkStore.createPermissionEdge(source, target)
    showToast(`Permission granted: ${source} → ${target}`, 'success')
  } catch (error) {
    showToast(`Failed to grant permission: ${error.message}`, 'error')
  }
}
```

3. Add edge deletion handler:
```javascript
function onEdgesChange(changes) {
  changes.forEach(async (change) => {
    if (change.type === 'remove') {
      const edge = edges.value.find(e => e.id === change.id)
      // Only delete permission edges (not collaboration edges)
      if (edge?.data?.type === 'permission') {
        try {
          await networkStore.deletePermissionEdge(edge.source, edge.target)
          showToast(`Permission revoked: ${edge.source} → ${edge.target}`, 'info')
        } catch (error) {
          showToast(`Failed to revoke permission: ${error.message}`, 'error')
        }
      }
    }
  })
}
```

4. Enable keyboard delete (Vue Flow built-in with edge selection)

### Phase 3: AgentNode - Handle Styling for Connection Mode

**File**: `src/frontend/src/components/AgentNode.vue`

**Changes**:

1. Style handles for better visibility during connection:
```vue
<Handle
  type="target"
  :position="Position.Top"
  class="w-4 h-4 border-2 bg-blue-400 border-white hover:bg-blue-500 hover:scale-125 transition-all"
/>
```

2. Add connection validation:
```javascript
const isValidConnection = (connection) => {
  // Prevent self-connections
  return connection.source !== connection.target
}
```

### Phase 4: Edge Styling

**File**: `src/frontend/src/stores/network.js` (in edge creation functions)

**Permission Edge Style**:
```javascript
{
  id: `perm-${source}-${target}`,
  source,
  target,
  type: 'smoothstep',
  animated: false,
  style: {
    stroke: '#3b82f6',  // blue-500
    strokeWidth: 2,
    strokeDasharray: '8 4',  // Dashed line
    opacity: 0.6
  },
  markerEnd: {
    type: 'arrowclosed',
    color: '#3b82f6',
    width: 12,
    height: 12
  },
  data: {
    type: 'permission',
    source,
    target
  }
}
```

**Collaboration Edge Style** (existing, with small update):
```javascript
{
  // ... existing style
  data: {
    type: 'collaboration',
    // ... existing data
  }
}
```

---

## File Changes Summary

| File | Changes |
|------|---------|
| `src/frontend/src/stores/network.js` | Add permission edge state/actions, merge edges computed |
| `src/frontend/src/views/Dashboard.vue` | Add @connect handler, confirmation dialogs, edge deletion |
| `src/frontend/src/components/AgentNode.vue` | Style handles, add validation |

**No backend changes required** - existing API is sufficient.

---

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/agents/{name}/permissions` | Fetch | Get permitted agents for one agent |
| `POST /api/agents/{source}/permissions/{target}` | Create | Add single permission |
| `DELETE /api/agents/{source}/permissions/{target}` | Delete | Remove single permission |

---

## Edge Cases

1. **User without share permission**: Hide handles / disable connection for agents user doesn't own
2. **Permission already exists**: Show "already permitted" instead of creating duplicate
3. **Collaboration without permission**: Can happen for user-scoped MCP keys; show collaboration edge but no permission edge
4. **Agent deleted**: Remove all edges involving that agent (already handled)
5. **Self-connection**: Prevent via `isValidConnection` - agents can always call themselves anyway

---

## Testing Checklist

- [ ] Create permission edge by dragging handle to handle
- [ ] Toast shows "Permission granted: A → B"
- [ ] Delete permission edge via Delete key
- [ ] Toast shows "Permission revoked: A → B"
- [ ] Permission edges show as dashed blue
- [ ] Collaboration edges show as solid animated (unchanged)
- [ ] Both edge types can coexist for same agent pair
- [ ] Refreshing page persists permission edges
- [ ] Non-owner cannot create/delete edges for agents they don't own
- [ ] Edge creation syncs to AgentDetail Permissions tab
- [ ] Self-connection prevented (same source and target)

---

## Future Enhancements (Out of Scope)

- Right-click context menu for edge actions
- Bulk permission operations on Dashboard
- Filter to show only permission edges or only collaboration edges
- Edge labels showing permission direction
