# Agent Detail Page Redesign (UI-001)

> **Status**: ✅ IMPLEMENTED (2026-02-18)
> **Priority**: MEDIUM
> **Created**: 2026-02-18
> **Author**: Eugene + Claude

## Problem Statement

The Agent Detail page (`AgentDetail.vue`) has accumulated features over time, resulting in a cluttered UI that's difficult to scan and navigate:

1. **Header row overload**: 12+ elements crammed into one row (name, badges, toggles, git buttons, delete)
2. **Poor visual hierarchy**: Agent name is small (text-xl) relative to all the controls
3. **Inefficient space usage**: Tags row takes full width for minimal content
4. **Default tab is Info**: Users land on metadata instead of where the action is (Tasks)
5. **Tab order not optimized**: Most-used tabs not first

## Goals

1. Improve visual hierarchy - agent identity should be prominent
2. Reduce cognitive load - group related controls together
3. Make Tasks the default landing tab
4. Optimize tab order for common workflows
5. Maintain all existing functionality (no feature removal)

---

## Specification

### 1. Default Tab Change

**Current**: `const activeTab = ref('info')` (line 275)
**New**: `const activeTab = ref('tasks')`

**Rationale**: Tasks tab is where users interact with the agent (run tasks, view history, monitor executions). Info tab is reference material rarely needed on first visit.

**Edge case**: If URL has `?tab=xyz` query param, respect that instead of default.

---

### 2. Header Reorganization

#### 2.1 Current Header Structure (AgentHeader.vue)

```
Row 1: [Name] [running] [Claude] [type] [GitHub icon] [commit] | [Toggle] [Pull] [Push] [Refresh] [Autonomy] [ReadOnly] [Delete]
Row 2: Tags: [+ Add]
Row 3: CPU | MEM | NET | UP | [⚙️]  (when running)
```

#### 2.2 New Header Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ROW 1: Identity + Primary Action                                             │
│ ┌──────────────────────────────────────────────────────────────────────────┐│
│ │                                                                          ││
│ │  dataroom-agent                              [Toggle: Running] [🗑️]      ││
│ │  🟢 running   ✦ Claude   business-assistant                              ││
│ │                                                                          ││
│ └──────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ ROW 2: Settings Row (Mode Toggles + Tags)                                    │
│ ┌──────────────────────────────────────────────────────────────────────────┐│
│ │  ↻ Manual    🔒 Read-Only: Off    Tags: [tag1] [tag2] [+ Add]    [⚙️]    ││
│ └──────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ ROW 3: Git Controls (ONLY when hasGitSync=true AND running)                  │
│ ┌──────────────────────────────────────────────────────────────────────────┐│
│ │  🔗 github.com/org/repo   main   8f87ebd   [↓ Pull] [↑ Push (13)] [↻]    ││
│ └──────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ ROW 4: Telemetry (ONLY when running)                                         │
│ ┌──────────────────────────────────────────────────────────────────────────┐│
│ │  CPU [▁▂▃] 0.1%/2   MEM [▃▄▅] 921.7MB/4G   NET ↓24.4MB ↑58.3MB   UP 20h ││
│ └──────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.3 Row 1: Identity + Primary Action

**Left side - Agent Identity:**
- Agent name: **text-2xl font-bold** (was text-xl)
- Status badges on second line below name:
  - Running/Stopped badge (colored pill)
  - Runtime badge (Claude/Gemini) - existing `RuntimeBadge.vue`
  - Agent type (muted text, e.g., "business-assistant")
  - SYSTEM badge (if `agent.is_system`)
  - "Shared by X" badge (if `agent.is_shared`)

**Right side - Primary Actions:**
- Running state toggle (`RunningStateToggle.vue`, size: lg)
- Delete button (trash icon, only if `agent.can_delete`)

**Rationale**: The running toggle is the most important action. Isolating it with delete makes it easy to find.

#### 2.4 Row 2: Settings Row

**Contents (left to right):**
1. **Autonomy toggle** - `AutonomyToggle.vue` with label "Manual" or "AUTO"
2. **Read-Only toggle** - `ReadOnlyToggle.vue` with label
3. **Divider** (vertical line)
4. **Tags** - `TagsEditor.vue` inline (compact mode)
5. **Resource settings gear** (only if `agent.can_share`) - opens ResourceModal

**Visibility**: Always visible (not conditional on running state)

**Rationale**: Groups all "configuration" controls together. Tags are a form of configuration/organization.

#### 2.5 Row 3: Git Controls

**Visibility**: Only when `hasGitSync === true` AND `agent.status === 'running'`

**Contents:**
- GitHub icon (links to repo)
- Branch name (e.g., "main")
- Commit hash (short, e.g., "8f87ebd")
- Pull button - blue when behind, gray otherwise
- Push button - orange when has changes, gray otherwise
- Refresh button (circular arrow)

**When stopped with git**: Show minimal indicator "Git enabled" (existing behavior)

**Rationale**: Git controls are only relevant when agent is running and has git sync. Separating them reduces clutter for agents without git.

#### 2.6 Row 4: Telemetry

**Visibility**: Only when `agent.status === 'running'`

**Contents**: Unchanged from current implementation:
- CPU with sparkline + percentage + limit
- MEM with sparkline + usage + limit
- NET with download/upload bytes
- UP with uptime

**Stopped state info**: Show "Created X ago | 2 CPU | 4G RAM" (existing behavior)

---

### 3. Tab Reordering

#### 3.1 Current Tab Order

```
Info | Tasks | Terminal | Logs | Credentials | Skills | Sharing | Permissions | Schedules | Git | Files | Folders | Public Links
```

#### 3.2 New Tab Order (Optimized for Workflow)

```
Tasks | Terminal | Logs | Files | Schedules | Credentials | Skills | Sharing | Permissions | Git | Folders | Public Links | Info
```

**Rationale for order:**
1. **Tasks** - Primary interaction point, now default
2. **Terminal** - Interactive Claude Code access
3. **Logs** - Debugging, frequently accessed
4. **Files** - View/download workspace files
5. **Schedules** - Automation setup
6. **Credentials** - Setup/configuration
7. **Skills** - Setup/configuration
8. **Sharing** - Access control
9. **Permissions** - Access control (agent-to-agent)
10. **Git** - Version control (if enabled)
11. **Folders** - Shared folders (rarely used)
12. **Public Links** - Public access (rarely used)
13. **Info** - Reference/metadata (moved to end)

#### 3.3 Conditional Tabs (Unchanged)

These tabs are conditionally shown based on permissions/state:
- **Dashboard**: Only if `hasDashboard === true`
- **Sharing, Permissions, Folders, Public Links**: Only if `agent.can_share && !agent.is_system`
- **Git**: Only if `hasGitSync === true`

---

### 4. Implementation Details

#### 4.1 Files to Modify

| File | Changes |
|------|---------|
| `src/frontend/src/views/AgentDetail.vue` | Change default tab to 'tasks', reorder tabs in `visibleTabs` computed |
| `src/frontend/src/components/AgentHeader.vue` | Restructure template into 4 rows, adjust styling |

#### 4.2 AgentDetail.vue Changes

**Line 275** - Change default tab:
```javascript
// Before
const activeTab = ref('info')

// After
const activeTab = ref('tasks')
```

**Lines 490-532** - Reorder `visibleTabs` computed:
```javascript
const visibleTabs = computed(() => {
  const isSystem = agent.value?.is_system

  // Primary tabs (always visible)
  const tabs = [
    { id: 'tasks', label: 'Tasks' },
    { id: 'terminal', label: 'Terminal' },
    { id: 'logs', label: 'Logs' },
    { id: 'files', label: 'Files' },
    { id: 'schedules', label: 'Schedules' },
    { id: 'credentials', label: 'Credentials' },
    { id: 'skills', label: 'Skills' }
  ]

  // Dashboard - only if agent has dashboard.yaml
  if (hasDashboard.value) {
    tabs.splice(1, 0, { id: 'dashboard', label: 'Dashboard' })  // After Tasks
  }

  // Access control tabs - hide for system agent
  if (agent.value?.can_share && !isSystem) {
    tabs.push({ id: 'sharing', label: 'Sharing' })
    tabs.push({ id: 'permissions', label: 'Permissions' })
  }

  // Git tab - only if git sync enabled
  if (hasGitSync.value) {
    tabs.push({ id: 'git', label: 'Git' })
  }

  // Folders and Public Links - hide for system agent
  if (agent.value?.can_share && !isSystem) {
    tabs.push({ id: 'folders', label: 'Folders' })
    tabs.push({ id: 'public-links', label: 'Public Links' })
  }

  // Info at the end
  tabs.push({ id: 'info', label: 'Info' })

  return tabs
})
```

#### 4.3 AgentHeader.vue Restructure

**Current structure** (single flex row + tags row + stats row):
```vue
<div class="bg-white ...">
  <!-- Top row: Name, status, and actions -->
  <div class="flex justify-between items-center">
    <div>Name + badges</div>
    <div>All action buttons</div>
  </div>

  <!-- Tags Row -->
  <div class="mt-2">Tags</div>

  <!-- Stats Row (when running) -->
  <div v-if="running" class="mt-3">Stats</div>
</div>
```

**New structure** (4 distinct rows):
```vue
<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
  <!-- ROW 1: Identity + Primary Action -->
  <div class="p-4 pb-2">
    <div class="flex justify-between items-start">
      <!-- Left: Agent Identity -->
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ agent.name }}</h1>
        <div class="flex items-center space-x-2 mt-1">
          <!-- Status badge, Runtime badge, Type, System/Shared badges -->
        </div>
      </div>
      <!-- Right: Primary Actions -->
      <div class="flex items-center space-x-2">
        <RunningStateToggle ... />
        <button v-if="agent.can_delete" @click="$emit('delete')" ...>🗑️</button>
      </div>
    </div>
  </div>

  <!-- ROW 2: Settings (Toggles + Tags) -->
  <div class="px-4 py-2 border-t border-gray-100 dark:border-gray-700 flex items-center space-x-4">
    <AutonomyToggle v-if="!agent.is_system && agent.can_share" ... />
    <ReadOnlyToggle v-if="!agent.is_system && agent.can_share" ... />
    <div class="h-4 w-px bg-gray-300 dark:bg-gray-600"></div>
    <div class="flex items-center flex-1">
      <span class="text-xs text-gray-400 mr-2">Tags:</span>
      <TagsEditor ... />
    </div>
    <button v-if="agent.can_share" @click="$emit('open-resource-modal')" ...>⚙️</button>
  </div>

  <!-- ROW 3: Git Controls (conditional) -->
  <div v-if="hasGitSync && agent.status === 'running'" class="px-4 py-2 border-t border-gray-100 dark:border-gray-700">
    <!-- GitHub link, branch, commit, Pull, Push, Refresh -->
  </div>

  <!-- ROW 4: Telemetry (conditional) -->
  <div v-if="agent.status === 'running'" class="px-4 py-2 border-t border-gray-100 dark:border-gray-700">
    <!-- CPU, MEM, NET, UP stats -->
  </div>

  <!-- Stopped state info -->
  <div v-else class="px-4 py-2 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-400">
    Created {{ formatRelativeTime(agent.created) }} | {{ cpu }} CPU | {{ memory }} RAM
  </div>
</div>
```

---

### 5. Visual Design Specifications

#### 5.1 Typography

| Element | Current | New |
|---------|---------|-----|
| Agent name | `text-xl font-bold` | `text-2xl font-bold` |
| Status badges | `text-xs` | `text-xs` (unchanged) |
| Section labels | N/A | `text-xs text-gray-400` |

#### 5.2 Spacing

| Element | Value |
|---------|-------|
| Row padding | `px-4 py-2` |
| Between rows | `border-t border-gray-100 dark:border-gray-700` |
| Card padding (first row) | `p-4 pb-2` |
| Between badges | `space-x-2` |
| Between sections in row | `space-x-4` |

#### 5.3 Colors (Dark Mode Compatible)

All existing color schemes maintained:
- Running badge: `bg-green-100 text-green-800` / `dark:bg-green-900/50 dark:text-green-300`
- Stopped badge: `bg-gray-100 text-gray-800` / `dark:bg-gray-700 dark:text-gray-300`
- Dividers: `bg-gray-300` / `dark:bg-gray-600`
- Borders: `border-gray-100` / `dark:border-gray-700`

---

### 6. Testing Checklist

#### 6.1 Default Tab

- [ ] Navigate to `/agents/{name}` - should land on Tasks tab
- [ ] Navigate to `/agents/{name}?tab=terminal` - should land on Terminal tab
- [ ] Navigate to `/agents/{name}?tab=info` - should land on Info tab
- [ ] Refresh page while on Logs tab - should return to Tasks (default)

#### 6.2 Header Layout

- [ ] Running agent: All 4 rows visible (Identity, Settings, Git if enabled, Telemetry)
- [ ] Stopped agent: 2-3 rows visible (Identity, Settings, Git indicator if enabled)
- [ ] Agent without git: Git row not shown
- [ ] System agent: Autonomy/ReadOnly toggles hidden, Sharing/Permissions tabs hidden
- [ ] Shared agent: "Shared by X" badge visible

#### 6.3 Tab Order

- [ ] Verify new tab order matches specification
- [ ] Dashboard tab appears after Tasks when agent has dashboard.yaml
- [ ] Conditional tabs appear/hide correctly based on permissions

#### 6.4 Responsive Behavior

- [ ] Test at 1024px width - tabs should not overflow excessively
- [ ] Test at 1440px width - comfortable spacing
- [ ] Header rows should stack gracefully on narrow screens

#### 6.5 Dark Mode

- [ ] All rows have correct dark mode styling
- [ ] Dividers visible in dark mode
- [ ] Badges maintain contrast

---

### 7. Migration Notes

- No database changes required
- No API changes required
- No backend changes required
- Frontend-only change
- Backward compatible (all features preserved)

---

### 8. Success Criteria

1. Users land on Tasks tab by default
2. Header is visually cleaner with clear grouping
3. Git controls only visible when relevant
4. Most-used tabs are easier to reach
5. No regression in existing functionality
6. Page loads and renders in same time or faster

---

### 9. Future Considerations (Out of Scope)

These ideas were discussed but deferred:
- **Tab dropdown for secondary tabs**: Would reduce tab bar width but adds interaction cost
- **Tab icons**: Could reduce width but may reduce discoverability
- **Sidebar navigation**: Major layout change, would need separate design review

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-02-18 | Eugene + Claude | Initial specification |
