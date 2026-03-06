# AgentDetail.vue Refactoring Plan

**Target File:** `src/frontend/src/views/AgentDetail.vue` (1906 lines)
**Goal:** Split into components under 1000 lines each

---

## Current Structure Analysis

| Section | Lines | Description |
|---------|-------|-------------|
| Template | 1-854 | 10 tabs with inline content |
| FileTreeNode | 856-1011 | Inline recursive component |
| Script Setup | 1012-1251 | State, computed, methods |
| Methods | 1252-1906 | Tab-specific logic |

### Current Tabs (in template)
1. **Info** - Agent information display
2. **Chat** - Chat interface with message history
3. **Logs** - Container logs viewer
4. **Credentials** - Credential management (.env, .mcp.json)
5. **Sharing** - Share agent with other users
6. **Schedules** - Schedule management
7. **Executions** - Schedule execution history
8. **Plans** - Workplan display
9. **Git** - Git configuration
10. **Files** - File browser with tree view

---

## Proposed Structure

```
src/frontend/src/
├── views/
│   └── AgentDetail.vue               # Main container (~500 lines)
└── components/agent/
    ├── tabs/
    │   ├── InfoTab.vue               # Agent info display (~150 lines)
    │   ├── ChatTab.vue               # Chat interface (~200 lines)
    │   ├── LogsTab.vue               # Container logs viewer (~150 lines)
    │   ├── CredentialsTab.vue        # Credential management (~200 lines)
    │   ├── SharingTab.vue            # Sharing controls (~150 lines)
    │   ├── SchedulesTab.vue          # Schedule management (~200 lines)
    │   ├── ExecutionsTab.vue         # Execution history (~120 lines)
    │   ├── PlansTab.vue              # Workplans display (~150 lines)
    │   ├── GitTab.vue                # Git configuration (~120 lines)
    │   └── FilesTab.vue              # File browser (~200 lines)
    └── FileTreeNode.vue              # Recursive tree component (~160 lines)
```

---

## Component Details

### 1. AgentDetail.vue (~500 lines)
**Purpose:** Main container, routing, shared state management

**Responsibilities:**
- Route parameter handling (`useRoute`)
- Agent data fetching and state
- Tab navigation logic
- Loading/error states
- Coordination between child components

**Template Structure:**
```vue
<template>
  <div class="agent-detail">
    <!-- Header with agent name, status, actions -->
    <AgentHeader :agent="agent" @start="startAgent" @stop="stopAgent" />

    <!-- Tab navigation -->
    <TabNavigation v-model="activeTab" :tabs="tabs" />

    <!-- Tab content -->
    <component
      :is="currentTabComponent"
      :agent="agent"
      v-bind="tabProps"
      @update="handleUpdate"
    />
  </div>
</template>
```

**State to Keep:**
- `agent` - Current agent data
- `activeTab` - Current tab
- `loading`, `error` - Loading states
- Shared methods for agent operations

---

### 2. InfoTab.vue (~150 lines)
**Purpose:** Display agent information

**Props:**
```typescript
interface Props {
  agent: Agent
}
```

**Template Content:**
- Agent type, status badges
- Port information
- Container ID
- Resource limits
- Creation time

**No events emitted** (read-only display)

---

### 3. ChatTab.vue (~200 lines)
**Purpose:** Chat interface with message history

**Props:**
```typescript
interface Props {
  agent: Agent
  sessions: ChatSession[]
  messages: ChatMessage[]
  currentSessionId: string | null
}
```

**Events:**
```typescript
interface Emits {
  (e: 'send', message: string): void
  (e: 'new-session'): void
  (e: 'select-session', sessionId: string): void
  (e: 'refresh'): void
}
```

**Template Content:**
- Session selector dropdown
- Message list with user/assistant styling
- Input textarea with send button
- Loading indicator for responses

---

### 4. LogsTab.vue (~150 lines)
**Purpose:** Container logs viewer

**Props:**
```typescript
interface Props {
  agent: Agent
  logs: string
  autoRefresh: boolean
}
```

**Events:**
```typescript
interface Emits {
  (e: 'refresh'): void
  (e: 'toggle-auto-refresh'): void
  (e: 'download'): void
}
```

**Template Content:**
- Log output in monospace pre block
- Auto-scroll toggle
- Refresh button
- Download logs button

---

### 5. CredentialsTab.vue (~200 lines)
**Purpose:** Credential management

**Props:**
```typescript
interface Props {
  agent: Agent
  envContent: string
  mcpTemplate: string
  mcpJson: string
  credentialStatus: CredentialStatus
}
```

**Events:**
```typescript
interface Emits {
  (e: 'save-env', content: string): void
  (e: 'save-mcp-template', content: string): void
  (e: 'reload-credentials'): void
  (e: 'refresh-status'): void
}
```

**Template Content:**
- .env editor textarea
- .mcp.json.template editor
- Generated .mcp.json preview (read-only)
- Reload credentials button
- Status indicators

---

### 6. SharingTab.vue (~150 lines)
**Purpose:** Share agent with other users

**Props:**
```typescript
interface Props {
  agent: Agent
  shares: AgentShare[]
  availableUsers: User[]
}
```

**Events:**
```typescript
interface Emits {
  (e: 'share', userId: string, permission: string): void
  (e: 'unshare', shareId: string): void
  (e: 'refresh'): void
}
```

**Template Content:**
- Current shares list with remove button
- Add share form (user selector, permission level)
- Owner display

---

### 7. SchedulesTab.vue (~200 lines)
**Purpose:** Schedule management

**Props:**
```typescript
interface Props {
  agent: Agent
  schedules: Schedule[]
}
```

**Events:**
```typescript
interface Emits {
  (e: 'create', schedule: ScheduleInput): void
  (e: 'update', id: string, schedule: ScheduleInput): void
  (e: 'delete', id: string): void
  (e: 'toggle', id: string, enabled: boolean): void
  (e: 'refresh'): void
}
```

**Template Content:**
- Schedule list with edit/delete buttons
- Create schedule form
- Cron expression input
- Enable/disable toggle

---

### 8. ExecutionsTab.vue (~120 lines)
**Purpose:** Schedule execution history

**Props:**
```typescript
interface Props {
  agent: Agent
  executions: ScheduleExecution[]
}
```

**Events:**
```typescript
interface Emits {
  (e: 'refresh'): void
  (e: 'view-details', executionId: string): void
}
```

**Template Content:**
- Execution history table
- Status badges (success/failed/running)
- Timestamp, duration
- View details link

---

### 9. PlansTab.vue (~150 lines)
**Purpose:** Workplan display

**Props:**
```typescript
interface Props {
  agent: Agent
  plan: WorkPlan | null
  tasks: Task[]
}
```

**Events:**
```typescript
interface Emits {
  (e: 'refresh'): void
  (e: 'clear-plan'): void
}
```

**Template Content:**
- Current plan display (goal, status)
- Task list with status badges
- Progress indicator
- Clear plan button

---

### 10. GitTab.vue (~120 lines)
**Purpose:** Git configuration

**Props:**
```typescript
interface Props {
  agent: Agent
  gitConfig: GitConfig | null
}
```

**Events:**
```typescript
interface Emits {
  (e: 'save', config: GitConfigInput): void
  (e: 'refresh'): void
}
```

**Template Content:**
- Repository URL input
- Branch input
- Credentials (username/token)
- Save button

---

### 11. FilesTab.vue (~200 lines)
**Purpose:** File browser

**Props:**
```typescript
interface Props {
  agent: Agent
  fileTree: FileNode[]
  selectedFile: FileNode | null
  fileContent: string
}
```

**Events:**
```typescript
interface Emits {
  (e: 'select-file', path: string): void
  (e: 'refresh'): void
  (e: 'download', path: string): void
}
```

**Template Content:**
- File tree (uses FileTreeNode)
- File content viewer
- Path breadcrumb
- Download button

---

### 12. FileTreeNode.vue (~160 lines)
**Purpose:** Recursive tree node component

**Props:**
```typescript
interface Props {
  node: FileNode
  depth: number
  selectedPath: string | null
}
```

**Events:**
```typescript
interface Emits {
  (e: 'select', path: string): void
  (e: 'toggle', path: string): void
}
```

**Template Content:**
- Folder/file icon
- Name display
- Expand/collapse for folders
- Recursive children rendering

---

## Migration Strategy

### Phase 1: Extract FileTreeNode (Isolated)
1. Create `components/agent/FileTreeNode.vue`
2. Copy lines 856-1011 from AgentDetail.vue
3. Convert to standalone component with props/emits
4. Import in AgentDetail.vue, verify functionality

### Phase 2: Extract Simple Tabs
1. Start with read-only tabs: `InfoTab`, `LogsTab`, `ExecutionsTab`
2. These have minimal interactivity
3. Create component, pass data via props
4. Test each before proceeding

### Phase 3: Extract Complex Tabs
1. `ChatTab` - Complex state, multiple events
2. `CredentialsTab` - Multiple editors, save operations
3. `FilesTab` - Uses FileTreeNode, file content display
4. `SchedulesTab` - CRUD operations

### Phase 4: Extract Remaining Tabs
1. `SharingTab`
2. `PlansTab`
3. `GitTab`

### Phase 5: Refactor Parent
1. Clean up AgentDetail.vue
2. Remove extracted template sections
3. Keep only coordination logic
4. Use dynamic component for tab switching

---

## Component Communication Pattern

### Props Down, Events Up
```vue
<!-- Parent (AgentDetail.vue) -->
<ChatTab
  :agent="agent"
  :sessions="chatSessions"
  :messages="chatMessages"
  :current-session-id="currentChatSessionId"
  @send="sendChatMessage"
  @new-session="createChatSession"
  @select-session="selectChatSession"
  @refresh="refreshChat"
/>
```

### Shared State via Provide/Inject (Optional)
For deeply nested components like FileTreeNode:
```typescript
// In AgentDetail.vue
provide('agentName', computed(() => agent.value?.name))

// In FileTreeNode.vue
const agentName = inject('agentName')
```

---

## Estimated Line Counts

| File | Lines | Status |
|------|-------|--------|
| `AgentDetail.vue` | ~500 | Container + routing |
| `InfoTab.vue` | ~150 | Read-only display |
| `ChatTab.vue` | ~200 | Chat interface |
| `LogsTab.vue` | ~150 | Logs viewer |
| `CredentialsTab.vue` | ~200 | Credential editors |
| `SharingTab.vue` | ~150 | Sharing controls |
| `SchedulesTab.vue` | ~200 | Schedule CRUD |
| `ExecutionsTab.vue` | ~120 | Execution history |
| `PlansTab.vue` | ~150 | Workplan display |
| `GitTab.vue` | ~120 | Git config |
| `FilesTab.vue` | ~200 | File browser |
| `FileTreeNode.vue` | ~160 | Tree node |
| **Total** | ~2300 | Slight overhead |

---

## Risk Mitigation

1. **State Management**
   - Keep agent state in parent
   - Child components are "dumb" - receive props, emit events
   - Consider Pinia store for complex shared state

2. **Testing Each Extraction**
   - Extract one component at a time
   - Test full tab functionality before proceeding
   - Keep original code commented until verified

3. **Style Scoping**
   - Use `<style scoped>` in all components
   - Move shared styles to a common CSS file
   - Verify no style bleeding after extraction

4. **Event Handling**
   - Document all events for each component
   - Use TypeScript interfaces for event payloads
   - Test event propagation thoroughly

---

## Feature Flows to Update

After refactoring, update references in:
- Any feature flows mentioning `AgentDetail.vue` line numbers
- Component documentation if it exists
