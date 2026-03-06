# Agent Start/Stop Toggle Control

> **Status**: ✅ IMPLEMENTED (2026-01-26)
> **Priority**: MEDIUM (UX Enhancement)
> **Created**: 2026-01-26
> **Author**: Claude Code

## Summary

Replace separate Start/Stop buttons with a unified toggle control (radio button or toggle switch) that clearly shows agent running state and allows easy control across all three agent-displaying pages.

## Problem Statement

### Current State

**1. Dashboard (`AgentNode.vue`)**
- Shows status dot (green=active/idle, gray=offline)
- Shows "Active/Idle/Offline" label
- **No start/stop control** - users must navigate to Agent Detail page

**2. Agents Page (`Agents.vue`)**
- Separate Start button (when stopped) - `lines 104-115`
- Separate Stop button (when running) - `lines 116-127`
- Buttons are conditional - only one shows at a time
- Not immediately obvious which action is available

**3. Agent Detail Page (`AgentDetail.vue`)**
- Start button in header (when stopped) - `lines 54-65`
- Stop button in header (when running) - `lines 66-77`
- Conditional display - one button replaces the other

### Problems

1. **Inconsistent controls**: Different UI patterns across pages
2. **Navigation required**: Dashboard users must click through to control agents
3. **State unclear**: Button label shows action (Start/Stop), not current state
4. **Cognitive load**: Users must interpret button to understand current state

## Proposed Solution

### Toggle Switch Design

Replace all Start/Stop buttons with a **unified toggle switch** that:
- Shows current state visually (ON = Running, OFF = Stopped)
- Has clear labels ("Running" / "Stopped")
- Uses consistent styling across all three pages
- Matches the existing Autonomy toggle design for visual consistency

### Visual Design

```
┌─────────────────────────────────────────┐
│  Running State Toggle                    │
├─────────────────────────────────────────┤
│                                          │
│  OFF (Stopped):                          │
│  ┌────────────────┐                      │
│  │ ○──────        │  Stopped            │
│  └────────────────┘                      │
│  (Gray toggle, gray dot, gray label)     │
│                                          │
│  ON (Running):                           │
│  ┌────────────────┐                      │
│  │        ──────● │  Running            │
│  └────────────────┘                      │
│  (Green toggle, green dot, green label)  │
│                                          │
│  Transitioning (Loading):                │
│  ┌────────────────┐                      │
│  │    ◌ ─────     │  Starting...        │
│  └────────────────┘                      │
│  (Muted colors, spinner, animated)       │
│                                          │
└─────────────────────────────────────────┘
```

### Toggle Dimensions

Match existing Autonomy toggle for consistency:
- Toggle track: 44px × 24px (slightly larger than autonomy toggle for importance)
- Toggle knob: 20px diameter
- Label font: 12px semibold
- Colors:
  - Running: Green (`bg-green-500`, knob `bg-white`)
  - Stopped: Gray (`bg-gray-300`, knob `bg-white`)
  - Loading: Muted version of target state with spinner overlay

---

## Implementation Locations

### 1. Dashboard - AgentNode.vue

**Location**: `src/frontend/src/components/AgentNode.vue`

**Current** (lines 52-61):
```vue
<!-- Activity state label -->
<div class="text-xs font-medium" :class="activityStateColor">
  {{ activityStateLabel }}
</div>
```

**Proposed**:
Add toggle switch below status display, above context bar.

```vue
<!-- Running State Toggle (NEW) -->
<div class="flex items-center justify-between mt-2">
  <span class="text-xs" :class="isRunning ? 'text-green-600' : 'text-gray-500'">
    {{ isRunning ? 'Running' : 'Stopped' }}
  </span>
  <button
    @click.stop="toggleRunningState"
    :disabled="isToggling"
    role="switch"
    :aria-checked="isRunning"
    class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors nodrag"
    :class="isRunning ? 'bg-green-500' : 'bg-gray-300'"
  >
    <span
      class="inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform"
      :class="isRunning ? 'translate-x-5' : 'translate-x-0.5'"
    />
    <!-- Loading spinner overlay -->
    <span v-if="isToggling" class="absolute inset-0 flex items-center justify-center">
      <svg class="animate-spin h-4 w-4 text-white" ...></svg>
    </span>
  </button>
</div>
```

**Store Method** (`network.js`):
```javascript
async toggleAgentRunningState(agentName) {
  const node = nodes.value.find(n => n.id === agentName)
  const isRunning = node.data.status === 'running'

  if (isRunning) {
    await axios.post(`/api/agents/${agentName}/stop`)
    node.data.status = 'stopped'
  } else {
    await axios.post(`/api/agents/${agentName}/start`)
    node.data.status = 'running'
  }
}
```

### 2. Agents Page - Agents.vue

**Location**: `src/frontend/src/views/Agents.vue`

**Current** (lines 104-127):
```vue
<!-- Separate Start/Stop buttons -->
<button v-if="agent.status !== 'running'" @click="startAgent(agent.name)">
  Start
</button>
<button v-else @click="stopAgent(agent.name)">
  Stop
</button>
```

**Proposed**:
Replace with toggle switch matching Dashboard design.

```vue
<!-- Running State Toggle -->
<div class="flex items-center space-x-2">
  <span class="text-xs font-medium" :class="agent.status === 'running' ? 'text-green-600' : 'text-gray-500'">
    {{ agent.status === 'running' ? 'Running' : 'Stopped' }}
  </span>
  <button
    @click="handleRunningToggle(agent)"
    :disabled="agent.isToggling"
    role="switch"
    :aria-checked="agent.status === 'running'"
    class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
    :class="agent.status === 'running' ? 'bg-green-500' : 'bg-gray-300'"
  >
    <!-- Toggle knob and loading spinner -->
  </button>
</div>
```

### 3. Agent Detail Page - AgentDetail.vue

**Location**: `src/frontend/src/views/AgentDetail.vue`

**Current** (lines 54-77):
```vue
<!-- Header with conditional Start/Stop buttons -->
<button v-if="agent.status === 'stopped'" @click="startAgent">
  <PlayIcon /> Start
</button>
<button v-if="agent.status === 'running'" @click="stopAgent">
  <StopIcon /> Stop
</button>
```

**Proposed**:
Replace buttons with toggle switch in header area.

```vue
<!-- Running State Toggle in Header -->
<div class="flex items-center space-x-3 ml-4">
  <span class="text-sm font-medium" :class="isRunning ? 'text-green-600' : 'text-gray-500'">
    {{ isRunning ? 'Running' : 'Stopped' }}
  </span>
  <button
    @click="toggleRunningState"
    :disabled="isToggling"
    role="switch"
    :aria-checked="isRunning"
    class="relative inline-flex h-7 w-14 items-center rounded-full transition-colors"
    :class="isRunning ? 'bg-green-500' : 'bg-gray-300'"
  >
    <!-- Larger toggle for header prominence -->
  </button>
</div>
```

---

## Component Extraction

### Shared Toggle Component

Create a reusable component for consistency:

**File**: `src/frontend/src/components/RunningStateToggle.vue`

```vue
<template>
  <div class="flex items-center" :class="containerClass">
    <span
      v-if="showLabel"
      class="font-medium mr-2"
      :class="[
        labelSizeClass,
        modelValue ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'
      ]"
    >
      {{ modelValue ? 'Running' : 'Stopped' }}
    </span>
    <button
      @click="toggle"
      :disabled="disabled || loading"
      role="switch"
      :aria-checked="modelValue"
      :aria-label="`Agent is ${modelValue ? 'running' : 'stopped'}. Click to ${modelValue ? 'stop' : 'start'}.`"
      class="relative inline-flex items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2"
      :class="[
        sizeClasses,
        modelValue ? 'bg-green-500 focus:ring-green-500' : 'bg-gray-300 dark:bg-gray-600 focus:ring-gray-400',
        (disabled || loading) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
      ]"
    >
      <span
        class="inline-block transform rounded-full bg-white shadow transition-transform"
        :class="[
          knobSizeClasses,
          modelValue ? translateOnClass : 'translate-x-0.5'
        ]"
      />
      <!-- Loading spinner overlay -->
      <span
        v-if="loading"
        class="absolute inset-0 flex items-center justify-center"
      >
        <svg
          class="animate-spin text-white"
          :class="spinnerSizeClass"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: Boolean,      // true = running, false = stopped
  disabled: Boolean,
  loading: Boolean,
  showLabel: { type: Boolean, default: true },
  size: { type: String, default: 'md' },  // 'sm', 'md', 'lg'
})

const emit = defineEmits(['update:modelValue', 'toggle'])

// Size variants
const sizeClasses = computed(() => ({
  sm: 'h-5 w-9',
  md: 'h-6 w-11',
  lg: 'h-7 w-14'
}[props.size]))

const knobSizeClasses = computed(() => ({
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-6 w-6'
}[props.size]))

const translateOnClass = computed(() => ({
  sm: 'translate-x-4',
  md: 'translate-x-5',
  lg: 'translate-x-7'
}[props.size]))

const labelSizeClass = computed(() => ({
  sm: 'text-xs',
  md: 'text-xs',
  lg: 'text-sm'
}[props.size]))

const spinnerSizeClass = computed(() => ({
  sm: 'h-3 w-3',
  md: 'h-4 w-4',
  lg: 'h-5 w-5'
}[props.size]))

const containerClass = computed(() => props.size === 'lg' ? 'space-x-3' : 'space-x-2')

function toggle() {
  if (!props.disabled && !props.loading) {
    emit('update:modelValue', !props.modelValue)
    emit('toggle', !props.modelValue)
  }
}
</script>
```

---

## Store Changes

### agents.js

Add unified toggle method:

```javascript
// State
runningToggleLoading: {},  // Map of agent name -> boolean

// Actions
async toggleAgentRunning(agentName) {
  const agent = this.agents.find(a => a.name === agentName)
  if (!agent) return { success: false, error: 'Agent not found' }

  this.runningToggleLoading[agentName] = true

  try {
    if (agent.status === 'running') {
      await axios.post(`/api/agents/${agentName}/stop`, {}, {
        headers: authStore.authHeader
      })
      agent.status = 'stopped'
    } else {
      const response = await axios.post(`/api/agents/${agentName}/start`, {}, {
        headers: authStore.authHeader
      })
      agent.status = 'running'
    }
    return { success: true, status: agent.status }
  } catch (error) {
    return { success: false, error: error.response?.data?.detail || error.message }
  } finally {
    this.runningToggleLoading[agentName] = false
  }
},

isToggling(agentName) {
  return this.runningToggleLoading[agentName] || false
}
```

### network.js

Add toggle method for Dashboard:

```javascript
// State
runningToggleLoading: {},  // Map of agent name -> boolean

// Actions
async toggleAgentRunning(agentName) {
  const node = nodes.value.find(n => n.id === agentName)
  if (!node) return { success: false }

  this.runningToggleLoading[agentName] = true

  try {
    const isRunning = node.data.status === 'running'

    if (isRunning) {
      await axios.post(`/api/agents/${agentName}/stop`)
      node.data.status = 'stopped'
      node.data.activityState = 'offline'
    } else {
      await axios.post(`/api/agents/${agentName}/start`)
      node.data.status = 'running'
      node.data.activityState = 'idle'
    }

    return { success: true }
  } catch (error) {
    return { success: false, error: error.message }
  } finally {
    this.runningToggleLoading[agentName] = false
  }
}
```

---

## Accessibility

### ARIA Attributes

- `role="switch"` - Indicates toggle switch semantic
- `aria-checked` - Reflects current state (true/false)
- `aria-label` - Descriptive label for screen readers
- `aria-disabled` - When loading or disabled

### Keyboard Navigation

- `Space` or `Enter` to toggle
- Focus ring visible on keyboard navigation
- Tab order follows document flow

### Screen Reader Announcements

- State change: "Agent now running" / "Agent now stopped"
- Loading: "Starting agent..." / "Stopping agent..."
- Error: "Failed to start/stop agent: {reason}"

---

## Dark Mode Support

Toggle colors adapt to dark mode:

| State | Light Mode | Dark Mode |
|-------|------------|-----------|
| Running (track) | `bg-green-500` | `bg-green-500` |
| Running (label) | `text-green-600` | `text-green-400` |
| Stopped (track) | `bg-gray-300` | `bg-gray-600` |
| Stopped (label) | `text-gray-500` | `text-gray-400` |
| Knob | `bg-white` | `bg-white` |
| Focus ring | `ring-green-500` / `ring-gray-400` | Same |

---

## Error Handling

### Toast Notifications

On toggle failure, show toast notification:

```javascript
async handleToggle(agent) {
  const result = await agentsStore.toggleAgentRunning(agent.name)

  if (!result.success) {
    showToast({
      type: 'error',
      title: `Failed to ${agent.status === 'running' ? 'stop' : 'start'} agent`,
      message: result.error || 'Unknown error occurred'
    })
  }
}
```

### Optimistic vs Pessimistic Updates

**Recommended: Pessimistic Update**
- Don't update UI until API confirms success
- Show loading spinner during request
- Revert on failure with error message

Rationale: Start/Stop operations are critical and may fail for various reasons (Docker issues, permission problems, resource constraints).

---

## Testing Plan

### Unit Tests

1. **Component renders correctly** with running=true and running=false
2. **Loading state** shows spinner and disables interaction
3. **Click handler** emits correct events
4. **Keyboard navigation** works (Space/Enter)
5. **ARIA attributes** are correct for each state

### Integration Tests

1. **Dashboard toggle** starts/stops agent and updates node
2. **Agents page toggle** starts/stops agent and updates list
3. **Agent Detail toggle** starts/stops agent and updates header
4. **WebSocket update** reflects in all visible pages
5. **Error handling** shows toast on failure

### Manual Testing

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open Dashboard with stopped agent | Toggle shows gray, label shows "Stopped" |
| 2 | Click toggle | Spinner appears, API called |
| 3 | Wait for response | Toggle turns green, label shows "Running" |
| 4 | Open Agents page | Same agent shows green toggle |
| 5 | Open Agent Detail | Header shows green toggle |
| 6 | Click toggle to stop | All pages update to gray/Stopped |
| 7 | Simulate API failure | Toast shows error, toggle reverts |

---

## Migration Notes

### Backward Compatibility

- No API changes required - uses existing `POST /api/agents/{name}/start` and `POST /api/agents/{name}/stop`
- WebSocket events unchanged - `agent_started` and `agent_stopped` still broadcast

### Files to Modify

| File | Changes |
|------|---------|
| `src/frontend/src/components/RunningStateToggle.vue` | NEW - Reusable component |
| `src/frontend/src/components/AgentNode.vue` | Add toggle, remove status-only display |
| `src/frontend/src/views/Agents.vue` | Replace Start/Stop buttons with toggle |
| `src/frontend/src/views/AgentDetail.vue` | Replace header buttons with toggle |
| `src/frontend/src/stores/agents.js` | Add `toggleAgentRunning()` action |
| `src/frontend/src/stores/network.js` | Add `toggleAgentRunning()` action |

### Files to Delete

None - existing buttons are replaced, not removed.

---

## Implementation Order

1. **Phase 1: Create shared component**
   - Create `RunningStateToggle.vue`
   - Add unit tests
   - Document props and events

2. **Phase 2: Agent Detail Page**
   - Replace header buttons with toggle
   - Test start/stop functionality
   - Verify loading and error states

3. **Phase 3: Agents Page**
   - Replace Start/Stop buttons with toggle
   - Add store method if not already present
   - Test grid layout with toggle

4. **Phase 4: Dashboard**
   - Add toggle to AgentNode.vue
   - Add store method to network.js
   - Test with `nodrag` class to prevent drag interference

5. **Phase 5: Polish**
   - Dark mode verification
   - Accessibility audit
   - Cross-browser testing

---

## Success Criteria

- [ ] Toggle shows current state clearly (Running/Stopped)
- [ ] Toggle works on all three pages (Dashboard, Agents, Agent Detail)
- [ ] Loading state visible during API call
- [ ] Error handling with user feedback
- [ ] Consistent visual design matching Autonomy toggle
- [ ] Dark mode support
- [ ] Keyboard accessible
- [ ] Screen reader compatible
- [ ] No regression in existing functionality

---

## References

### Existing Patterns

- **Autonomy Toggle**: `AgentNode.vue:62-96` - Reference for toggle styling
- **Start/Stop Buttons**: `Agents.vue:104-127`, `AgentDetail.vue:54-77`
- **Store Methods**: `agents.js:126-156` - `startAgent()`, `stopAgent()`

### Feature Flows

- [agent-network.md](../memory/feature-flows/agent-network.md) - Dashboard AgentNode
- [agents-page-ui-improvements.md](../memory/feature-flows/agents-page-ui-improvements.md) - Agents page
- [agent-lifecycle.md](../memory/feature-flows/agent-lifecycle.md) - Start/Stop API

### Design System

- Toggle switch follows Tailwind UI switch pattern
- Colors from existing Trinity palette
- Matches Autonomy toggle dimensions and behavior
