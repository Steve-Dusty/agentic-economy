# AgentDetail.vue Refactoring Plan

**STATUS: COMPLETED** (2025-12-27)

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| AgentDetail.vue | 2,193 lines | 1,386 lines | -37% |
| Composables | 0 | 14 files | +14 |
| Total logic | 2,193 lines | ~2,350 lines | +7% (modular) |

> **Target**: Reduce `AgentDetail.vue` from 2,192 lines to ~500 lines
> **Approach**: Extract logic into Vue 3 composables
> **Priority**: Non-breaking - all external interfaces preserved

---

## Overview

**Current State**: `src/frontend/src/views/AgentDetail.vue` (2,192 lines)
- Template: 980 lines (tabs, conditional rendering)
- Script: 1,175 lines (60+ refs, 40+ functions)
- Style: 37 lines

**Target State**:
- `AgentDetail.vue`: ~500 lines (thin orchestrator)
- `composables/`: 12 focused composables (~1,700 lines total)

---

## Analysis: Current Concerns in AgentDetail.vue

| Concern | Lines (est.) | State Refs | Functions | Priority |
|---------|--------------|------------|-----------|----------|
| Agent Lifecycle | 100 | 5 | 4 | High |
| Stats/Telemetry | 100 | 4 | 6 | High |
| Logs | 60 | 5 | 4 | Medium |
| Terminal | 50 | 3 | 4 | Medium |
| Credentials | 100 | 4 | 4 | Medium |
| Sharing | 80 | 4 | 2 | Medium |
| Permissions | 100 | 5 | 5 | Medium |
| Git Sync | 100 | 5 | 5 | Medium |
| File Browser | 150 | 6 | 5 | Medium |
| Chat | 150 | 5 | 3 | Low (deprecated) |
| API Key Settings | 50 | 3 | 2 | Low |
| Model Settings | 50 | 2 | 2 | Low |
| Session Info | 80 | 2 | 2 | Low |
| Notification | 20 | 1 | 1 | Low |

---

## Refactoring Phases

### Phase 1: Setup Infrastructure (Non-breaking)

**Goal**: Create composables directory and helper utilities

**Tasks**:
1. Create `src/frontend/src/composables/` directory
2. Create `useNotification.js` - Simple notification utility
3. Create `useFormatters.js` - Shared formatting functions (bytes, uptime, time, tokens)
4. Verify build still works

**Files Created**:
```
src/frontend/src/composables/
├── index.js           # Central exports
├── useNotification.js # Notification toast
└── useFormatters.js   # formatBytes, formatUptime, formatRelativeTime, formatTokenCount
```

**Verification**:
- Run `npm run build` - should succeed
- Run app - AgentDetail.vue should work unchanged

---

### Phase 2: Extract Agent Lifecycle (High Priority)

**Goal**: Extract agent lifecycle operations (start, stop, delete, confirm dialog)

**Create**: `composables/useAgentLifecycle.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1146-1182
const actionLoading = ref(false)
const confirmDialog = reactive({
  visible: false,
  title: '',
  message: '',
  confirmText: 'Confirm',
  variant: 'danger',
  onConfirm: () => {}
})
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1416-1485
startAgent()      // lines 1416-1428
stopAgent()       // lines 1430-1442
deleteAgent()     // lines 1471-1485
```

**Composable Interface**:
```javascript
// useAgentLifecycle.js
export function useAgentLifecycle(agentRef, agentsStore, router, showNotification) {
  const actionLoading = ref(false)
  const confirmDialog = reactive({ ... })

  const startAgent = async () => { ... }
  const stopAgent = async () => { ... }
  const deleteAgent = () => { ... }  // Opens confirm dialog

  return {
    actionLoading,
    confirmDialog,
    startAgent,
    stopAgent,
    deleteAgent
  }
}
```

**Usage in AgentDetail.vue**:
```javascript
const {
  actionLoading,
  confirmDialog,
  startAgent,
  stopAgent,
  deleteAgent
} = useAgentLifecycle(agent, agentsStore, router, showNotification)
```

**Verification**:
- Start agent from stopped state
- Stop running agent
- Delete agent (with confirm dialog)
- WebSocket broadcasts received
- Toast notifications appear

---

### Phase 3: Extract Stats/Telemetry (High Priority)

**Goal**: Extract container stats polling and formatting

**Create**: `composables/useAgentStats.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1194-1198
const agentStats = ref(null)
const statsLoading = ref(false)
let statsRefreshInterval = null
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1591-1669
loadStats()           // lines 1592-1606
startStatsPolling()   // lines 1608-1611
stopStatsPolling()    // lines 1613-1618
formatBytes()         // lines 1643-1654
formatUptime()        // lines 1656-1669
```

**Composable Interface**:
```javascript
// useAgentStats.js
export function useAgentStats(agentRef, agentsStore) {
  const agentStats = ref(null)
  const statsLoading = ref(false)

  const loadStats = async () => { ... }
  const startStatsPolling = () => { ... }  // 5s interval
  const stopStatsPolling = () => { ... }

  // Lifecycle management
  onUnmounted(() => stopStatsPolling())

  return {
    agentStats,
    statsLoading,
    loadStats,
    startStatsPolling,
    stopStatsPolling
  }
}
```

**Verification**:
- Stats bar shows CPU, memory, network, uptime
- Values update every 5 seconds
- Polling stops when agent stops
- No memory leaks (intervals cleared)

---

### Phase 4: Extract Logs Management

**Goal**: Extract logs fetching and auto-refresh

**Create**: `composables/useAgentLogs.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1147-1159
const logs = ref('')
const logLines = ref(100)
const autoRefreshLogs = ref(false)
const logsContainer = ref(null)
const userScrolledUp = ref(false)
let logsRefreshInterval = null
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1389-1414
refreshLogs()          // lines 1389-1400
scrollLogsToBottom()   // lines 1403-1407
handleLogsScroll()     // lines 1409-1414
```

**Watch to Move**:
```javascript
// FROM AgentDetail.vue lines 1303-1313
watch(autoRefreshLogs, ...)  // Toggle auto-refresh
```

**Composable Interface**:
```javascript
// useAgentLogs.js
export function useAgentLogs(agentRef, agentsStore) {
  const logs = ref('')
  const logLines = ref(100)
  const autoRefreshLogs = ref(false)
  const logsContainer = ref(null)
  const userScrolledUp = ref(false)

  const refreshLogs = async () => { ... }
  const scrollLogsToBottom = () => { ... }
  const handleLogsScroll = () => { ... }

  // Watch for auto-refresh toggle
  watch(autoRefreshLogs, (enabled) => { ... })

  // Cleanup on unmount
  onUnmounted(() => { ... })

  return {
    logs,
    logLines,
    autoRefreshLogs,
    logsContainer,
    userScrolledUp,
    refreshLogs,
    handleLogsScroll
  }
}
```

**Verification**:
- Logs tab shows container logs
- Line count selector works
- Refresh button works
- Auto-refresh toggle works (10s interval)
- Scroll-to-bottom preserved unless user scrolls up

---

### Phase 5: Extract Terminal Handlers

**Goal**: Extract terminal fullscreen and keyboard handling

**Create**: `composables/useAgentTerminal.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1202-1204
const isTerminalFullscreen = ref(false)
const terminalRef = ref(null)
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1487-1513
toggleTerminalFullscreen()  // lines 1488-1495
handleTerminalKeydown()     // lines 1497-1501
onTerminalConnected()       // lines 1503-1505
onTerminalDisconnected()    // lines 1507-1509
onTerminalError()           // lines 1511-1513
```

**Composable Interface**:
```javascript
// useAgentTerminal.js
export function useAgentTerminal(showNotification) {
  const isTerminalFullscreen = ref(false)
  const terminalRef = ref(null)

  const toggleTerminalFullscreen = () => { ... }
  const handleTerminalKeydown = (event) => { ... }
  const onTerminalConnected = () => { ... }
  const onTerminalDisconnected = () => { ... }
  const onTerminalError = (errorMsg) => { ... }

  return {
    isTerminalFullscreen,
    terminalRef,
    toggleTerminalFullscreen,
    handleTerminalKeydown,
    onTerminalConnected,
    onTerminalDisconnected,
    onTerminalError
  }
}
```

**Verification**:
- Terminal connects when agent running
- Fullscreen toggle works
- ESC key exits fullscreen
- Connection/disconnection notifications appear

---

### Phase 6: Extract Credentials

**Goal**: Extract credential loading and hot reload

**Create**: `composables/useAgentCredentials.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1160-1164
const credentialsData = ref(null)
const credentialsLoading = ref(false)
const hotReloadText = ref('')
const hotReloadLoading = ref(false)
const hotReloadResult = ref(null)
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1578-1745
loadCredentials()      // lines 1578-1589
countCredentials()     // lines 1705-1715
performHotReload()     // lines 1717-1745
formatSource()         // lines 1685-1702
```

**Composable Interface**:
```javascript
// useAgentCredentials.js
export function useAgentCredentials(agentRef, agentsStore, showNotification) {
  const credentialsData = ref(null)
  const credentialsLoading = ref(false)
  const hotReloadText = ref('')
  const hotReloadLoading = ref(false)
  const hotReloadResult = ref(null)

  const loadCredentials = async () => { ... }
  const countCredentials = (text) => { ... }
  const performHotReload = async () => { ... }
  const formatSource = (source) => { ... }

  return {
    credentialsData,
    credentialsLoading,
    hotReloadText,
    hotReloadLoading,
    hotReloadResult,
    loadCredentials,
    countCredentials,
    performHotReload,
    formatSource
  }
}
```

**Verification**:
- Credentials tab shows required credentials
- Missing count badge shows correctly
- Hot reload updates credentials in running agent
- Success/error messages display properly

---

### Phase 7: Extract Sharing

**Goal**: Extract agent sharing functionality

**Create**: `composables/useAgentSharing.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1206-1210
const shareEmail = ref('')
const shareLoading = ref(false)
const shareMessage = ref(null)
const unshareLoading = ref(null)
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1801-1848
shareWithUser()   // lines 1802-1830
removeShare()     // lines 1832-1848
```

**Composable Interface**:
```javascript
// useAgentSharing.js
export function useAgentSharing(agentRef, agentsStore, loadAgent, showNotification) {
  const shareEmail = ref('')
  const shareLoading = ref(false)
  const shareMessage = ref(null)
  const unshareLoading = ref(null)

  const shareWithUser = async () => { ... }
  const removeShare = async (email) => { ... }

  return {
    shareEmail,
    shareLoading,
    shareMessage,
    unshareLoading,
    shareWithUser,
    removeShare
  }
}
```

**Verification**:
- Share form accepts email
- Success/error messages appear
- Shared users list updates
- Remove share works
- Shared users can access agent

---

### Phase 8: Extract Permissions

**Goal**: Extract agent-to-agent permissions (Phase 9.10)

**Create**: `composables/useAgentPermissions.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1212-1218
const availableAgents = ref([])
const permissionsLoading = ref(false)
const permissionsSaving = ref(false)
const permissionsDirty = ref(false)
const permissionsMessage = ref(null)
const permittedAgentsCount = computed(...)
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1850-1909
loadPermissions()   // lines 1851-1870
savePermissions()   // lines 1872-1898
allowAllAgents()    // lines 1901-1904
allowNoAgents()     // lines 1906-1909
```

**Composable Interface**:
```javascript
// useAgentPermissions.js
export function useAgentPermissions(agentRef, agentsStore) {
  const availableAgents = ref([])
  const permissionsLoading = ref(false)
  const permissionsSaving = ref(false)
  const permissionsDirty = ref(false)
  const permissionsMessage = ref(null)

  const permittedAgentsCount = computed(() =>
    availableAgents.value.filter(a => a.permitted).length
  )

  const loadPermissions = async () => { ... }
  const savePermissions = async () => { ... }
  const allowAllAgents = () => { ... }
  const allowNoAgents = () => { ... }

  return {
    availableAgents,
    permissionsLoading,
    permissionsSaving,
    permissionsDirty,
    permissionsMessage,
    permittedAgentsCount,
    loadPermissions,
    savePermissions,
    allowAllAgents,
    allowNoAgents
  }
}
```

**Verification**:
- Permissions tab loads available agents
- Checkboxes toggle permitted state
- Allow All/None buttons work
- Save button saves to backend
- "Unsaved changes" indicator appears

---

### Phase 9: Extract Git Sync

**Goal**: Extract git status and sync functionality

**Create**: `composables/useGitSync.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1229-1250
const hasGitSync = computed(...)
const gitStatus = ref(null)
const gitLoading = ref(false)
const gitSyncing = ref(false)
const gitSyncResult = ref(null)
const gitHasChanges = computed(...)
const gitChangesCount = computed(...)
let gitStatusInterval = null
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1911-1967
loadGitStatus()          // lines 1912-1923
refreshGitStatus()       // lines 1925-1928
syncToGithub()           // lines 1930-1954
startGitStatusPolling()  // lines 1956-1960
stopGitStatusPolling()   // lines 1962-1967
```

**Composable Interface**:
```javascript
// useGitSync.js
export function useGitSync(agentRef, agentsStore, showNotification) {
  const hasGitSync = computed(() => true)  // Always show tab
  const gitStatus = ref(null)
  const gitLoading = ref(false)
  const gitSyncing = ref(false)
  const gitSyncResult = ref(null)

  const gitHasChanges = computed(() => ...)
  const gitChangesCount = computed(() => ...)

  const loadGitStatus = async () => { ... }
  const refreshGitStatus = () => { ... }
  const syncToGithub = async () => { ... }
  const startGitStatusPolling = () => { ... }  // 30s interval
  const stopGitStatusPolling = () => { ... }

  onUnmounted(() => stopGitStatusPolling())

  return {
    hasGitSync,
    gitStatus,
    gitLoading,
    gitSyncing,
    gitSyncResult,
    gitHasChanges,
    gitChangesCount,
    loadGitStatus,
    refreshGitStatus,
    syncToGithub,
    startGitStatusPolling,
    stopGitStatusPolling
  }
}
```

**Verification**:
- Git sync button shows in header (for GitHub agents)
- Status refreshes every 30 seconds
- Sync button pushes changes
- Changes count badge updates

---

### Phase 10: Extract File Browser

**Goal**: Extract file tree loading and operations

**Create**: `composables/useFileBrowser.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1252-1294
const fileTree = ref([])
const filesLoading = ref(false)
const filesError = ref(null)
const fileSearchQuery = ref('')
const expandedFolders = ref(new Set())
const totalFileCount = ref(0)
const filteredFileTree = computed(...)
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1969-2023
loadFiles()       // lines 1970-1984
toggleFolder()    // lines 1986-1994
downloadFile()    // lines 1996-2015
formatFileSize()  // lines 2017-2023
```

**Note**: Keep `FileTreeNode` component definition in AgentDetail.vue (or extract to separate component file later).

**Composable Interface**:
```javascript
// useFileBrowser.js
export function useFileBrowser(agentRef, agentsStore, showNotification) {
  const fileTree = ref([])
  const filesLoading = ref(false)
  const filesError = ref(null)
  const fileSearchQuery = ref('')
  const expandedFolders = ref(new Set())
  const totalFileCount = ref(0)

  const filteredFileTree = computed(() => { ... })

  const loadFiles = async () => { ... }
  const toggleFolder = (path) => { ... }
  const downloadFile = async (filePath, fileName) => { ... }

  return {
    fileTree,
    filesLoading,
    filesError,
    fileSearchQuery,
    expandedFolders,
    totalFileCount,
    filteredFileTree,
    loadFiles,
    toggleFolder,
    downloadFile
  }
}
```

**Verification**:
- Files tab shows workspace tree
- Folders expand/collapse
- Search filters files
- Download button triggers browser download
- Refresh button reloads tree

---

### Phase 11: Extract API Key & Model Settings

**Goal**: Extract API key setting and model selection

**Create**: `composables/useAgentSettings.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1184-1191
const apiKeySetting = ref({ use_platform_api_key: true, restart_required: false })
const apiKeySettingLoading = ref(false)
const currentModel = ref('')
const modelLoading = ref(false)
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1444-1469, 2076-2101
loadApiKeySetting()     // lines 1445-1452
updateApiKeySetting()   // lines 1454-1469
loadModelInfo()         // lines 2077-2085
changeModel()           // lines 2088-2101
```

**Composable Interface**:
```javascript
// useAgentSettings.js
export function useAgentSettings(agentRef, agentsStore, showNotification) {
  const apiKeySetting = ref({ use_platform_api_key: true, restart_required: false })
  const apiKeySettingLoading = ref(false)
  const currentModel = ref('')
  const modelLoading = ref(false)

  const loadApiKeySetting = async () => { ... }
  const updateApiKeySetting = async (usePlatformKey) => { ... }
  const loadModelInfo = async () => { ... }
  const changeModel = async () => { ... }

  return {
    apiKeySetting,
    apiKeySettingLoading,
    currentModel,
    modelLoading,
    loadApiKeySetting,
    updateApiKeySetting,
    loadModelInfo,
    changeModel
  }
}
```

**Verification**:
- API key toggle shows correct state
- Setting change shows "restart required"
- Model selection works

---

### Phase 12: Extract Session/Activity

**Goal**: Extract session info and activity polling

**Create**: `composables/useSessionActivity.js`

**State to Move**:
```javascript
// FROM AgentDetail.vue lines 1165-1172, 1220-1227
const sessionInfo = ref({ context_tokens: 0, ... })
const sessionActivity = ref({ status: 'idle', ... })
let activityRefreshInterval = null
```

**Functions to Move**:
```javascript
// FROM AgentDetail.vue lines 1620-1641, 2055-2073
loadSessionActivity()     // lines 1621-1629
startActivityPolling()    // lines 1631-1634
stopActivityPolling()     // lines 1636-1641
loadSessionInfo()         // lines 2056-2073
formatTokenCount()        // lines 2040-2046
getContextBarColor()      // lines 2048-2053
```

**Composable Interface**:
```javascript
// useSessionActivity.js
export function useSessionActivity(agentRef, agentsStore) {
  const sessionInfo = ref({ ... })
  const sessionActivity = ref({ ... })

  const loadSessionInfo = async () => { ... }
  const loadSessionActivity = async () => { ... }
  const startActivityPolling = () => { ... }  // 2s interval
  const stopActivityPolling = () => { ... }

  onUnmounted(() => stopActivityPolling())

  return {
    sessionInfo,
    sessionActivity,
    loadSessionInfo,
    loadSessionActivity,
    startActivityPolling,
    stopActivityPolling
  }
}
```

**Verification**:
- Context usage displays correctly
- Activity status updates
- Polling stops on unmount

---

### Phase 13: Final Cleanup

**Goal**: Clean up AgentDetail.vue and update feature flows

**Tasks**:
1. Remove extracted code from AgentDetail.vue
2. Consolidate imports from composables
3. Update watchers to use composable functions
4. Run full test suite
5. Update feature flow documentation

**Final AgentDetail.vue Structure**:
```javascript
import { useNotification, useFormatters } from '@/composables'
import { useAgentLifecycle } from '@/composables/useAgentLifecycle'
import { useAgentStats } from '@/composables/useAgentStats'
// ... other composable imports

// Composable setup
const { showNotification, notification } = useNotification()
const { formatBytes, formatUptime, formatRelativeTime } = useFormatters()
const { actionLoading, confirmDialog, startAgent, stopAgent, deleteAgent } = useAgentLifecycle(...)
const { agentStats, statsLoading, startStatsPolling, stopStatsPolling } = useAgentStats(...)
// ... other composable destructuring

// Minimal local state
const agent = ref(null)
const loading = ref(true)
const error = ref('')
const activeTab = ref('info')

// Load agent and initialize polling
onMounted(async () => {
  await loadAgent()
  if (agent.value?.status === 'running') {
    startStatsPolling()
    startActivityPolling()
    if (hasGitSync.value) startGitStatusPolling()
  }
})

// Watch agent status for polling management
watch(() => agent.value?.status, (newStatus) => {
  if (newStatus === 'running') {
    startStatsPolling()
    startActivityPolling()
  } else {
    stopStatsPolling()
    stopActivityPolling()
  }
})
```

---

## Composables Directory Structure

```
src/frontend/src/composables/
├── index.js                  # Central exports
├── useNotification.js        # Toast notifications
├── useFormatters.js          # Shared formatters
├── useAgentLifecycle.js      # Start/stop/delete
├── useAgentStats.js          # Container stats
├── useAgentLogs.js           # Log viewing
├── useAgentTerminal.js       # Terminal handling
├── useAgentCredentials.js    # Credential management
├── useAgentSharing.js        # Share with users
├── useAgentPermissions.js    # Agent-to-agent perms
├── useGitSync.js             # Git sync operations
├── useFileBrowser.js         # File tree browsing
├── useAgentSettings.js       # API key, model
└── useSessionActivity.js     # Session info, activity
```

---

## Testing Strategy

### Per-Phase Testing

Each phase must pass before moving to the next:

1. **Build Test**: `npm run build` succeeds
2. **Unit Test**: Component mounts without errors
3. **Feature Test**: Specific feature works as documented
4. **Regression Test**: Other features unaffected

### Feature Flow Verification

After each phase, verify against feature flows:
- `agent-lifecycle.md` - Phase 2
- `agent-terminal.md` - Phase 5
- `file-browser.md` - Phase 10
- `agent-sharing.md` - Phase 7
- `agent-permissions.md` - Phase 8

### Full Regression Test (Phase 13)

1. Agent lifecycle (create, start, stop, delete)
2. Stats display and polling
3. Logs with auto-refresh
4. Terminal connection and fullscreen
5. Credentials and hot reload
6. Sharing with other users
7. Agent-to-agent permissions
8. Git sync operations
9. File browser tree
10. API key and model settings

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Reactivity breaks | High | Keep refs at composable level, return computed for derived state |
| Interval leaks | Medium | Always use `onUnmounted` for cleanup |
| Circular dependencies | Medium | Pass dependencies as arguments, don't import stores in composables |
| Template bindings break | High | Use exact same names in return objects |
| Watch timing issues | Medium | Initialize composables before setting up cross-composable watches |

---

## Non-Goals

**NOT in scope for this refactoring**:
- Template restructuring (keep same template)
- CSS/styling changes
- Adding new features
- Changing API contracts
- Splitting into child components (future work)
- TypeScript conversion (future work)

---

## Success Criteria

1. **AgentDetail.vue < 600 lines** (template + minimal orchestration)
2. **All features work** as documented in feature flows
3. **No regressions** in existing functionality
4. **Build passes** without errors
5. **No memory leaks** (intervals/watchers cleaned up)
6. **Composables are reusable** (could be used by other views)

---

## Timeline Estimate

| Phase | Description | Complexity |
|-------|-------------|------------|
| 1 | Setup infrastructure | Low |
| 2 | Agent lifecycle | Medium |
| 3 | Stats/telemetry | Medium |
| 4 | Logs management | Low |
| 5 | Terminal handlers | Low |
| 6 | Credentials | Medium |
| 7 | Sharing | Low |
| 8 | Permissions | Medium |
| 9 | Git sync | Medium |
| 10 | File browser | Medium |
| 11 | API key/model | Low |
| 12 | Session/activity | Low |
| 13 | Final cleanup | Medium |

---

## References

- **Feature Flows**: `docs/memory/feature-flows/*.md`
- **Vue 3 Composables**: https://vuejs.org/guide/reusability/composables.html
- **Prior Art**: `routers/agents.py` refactoring (2928→785 lines)

---

## Changelog

| Date | Changes |
|------|---------|
| 2025-12-27 | Initial plan created |
