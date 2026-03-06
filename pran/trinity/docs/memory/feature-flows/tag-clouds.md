# Feature: Tag Clouds Visualization

**Status**: Implemented
**Date**: 2026-02-25
**Priority**: Medium (UX Enhancement)

---

## Overview

Tag Clouds is a visual grouping feature on the Dashboard that renders semi-transparent colored clouds behind agents that share the same tag, making it easy to see organizational groupings at a glance.

---

## User Story

As a Trinity platform user, I want to see visual groupings of agents by their tags on the Dashboard so that I can quickly understand how my agents are organized and identify which agents belong to the same system or team.

---

## Architecture

```
                         +-----------------------------------------------------------+
                         |                     FRONTEND                              |
                         |                                                           |
                         |  Dashboard.vue                                            |
                         |       |                                                   |
                         |       +-- "Clouds" toggle button (line 117-132)           |
                         |       |       |                                           |
                         |       |       +-- showTagClouds state (localStorage)      |
                         |       |                                                   |
                         |       +-- VueFlow container (line 266-355)                |
                         |               |                                           |
                         |               +-- TagClouds component (line 306-329)      |
                         |                       |                                   |
                         |                       +-- Receives nodes with tags        |
                         |                       +-- Computes bounding boxes         |
                         |                       +-- Renders SVG clouds              |
                         |                                                           |
                         |  TagClouds.vue (NEW)                                      |
                         |       +-- Groups nodes by tag (line 129-142)              |
                         |       +-- Calculates bounding boxes (line 146-176)        |
                         |       +-- Renders SVG rects with blur (line 1-52)         |
                         |                                                           |
                         +-----------------------------------------------------------+
                                                    |
                                                    v
+-------------------------------------------------------------------------------------------+
|                                   NETWORK STORE                                           |
|                                                                                           |
|  network.js                                                                               |
|       +-- convertAgentsToNodes() (line 308-464)                                           |
|               |                                                                           |
|               +-- Groups agents by primary tag (line 317-331)                             |
|               +-- Bin-packing layout algorithm (line 379-398)                             |
|               +-- Adds tags to node.data (line 455)                                       |
|                                                                                           |
+-------------------------------------------------------------------------------------------+
                                                    |
                                                    v
+-------------------------------------------------------------------------------------------+
|                                    BACKEND API                                            |
|                                                                                           |
|  GET /api/agents                                                                          |
|       +-- Returns agents with tags array (routers/agents.py:160-165)                      |
|                                                                                           |
+-------------------------------------------------------------------------------------------+
```

---

## Entry Points

| Entry Point | Location | Description |
|-------------|----------|-------------|
| **Toggle Button** | `src/frontend/src/views/Dashboard.vue:117-132` | "Clouds" button in Dashboard header |
| **TagClouds Component** | `src/frontend/src/views/Dashboard.vue:306-329` | Rendered inside VueFlow container |

---

## Frontend Layer

### TagClouds.vue (`src/frontend/src/components/TagClouds.vue`)

New component that renders SVG clouds behind agent groups.

| Line | Element | Description |
|------|---------|-------------|
| 1-52 | `<template>` | Container with SVG elements for each tag cloud |
| 4-17 | Cloud SVG | Positioned absolutely, transforms with viewport |
| 19-24 | Blur Filter | Gaussian blur for soft edges (`feGaussianBlur`) |
| 27-37 | Cloud Rect | Rounded rectangle with fill color and opacity |
| 39-50 | Tag Label | Optional `#tag` label in corner |
| 58-102 | Props | `nodes`, `padding`, `cloudOpacity`, `blurAmount`, `cloudBorderRadius`, `showLabels`, `labelPadding`, `nodeWidth`, `nodeHeight` |
| 105-116 | `tagColors` | 10-color palette (blue, emerald, amber, pink, violet, cyan, orange, lime, red, teal) |
| 119-126 | `getTagColor(tag)` | Deterministic color selection based on tag name hash |
| 129-183 | `tagClouds` computed | Groups nodes by tags, calculates bounding boxes, sorts by area |

**Color Palette (10 colors):**

| Index | Color | Hex |
|-------|-------|-----|
| 0 | Blue | `#3b82f6` |
| 1 | Emerald | `#10b981` |
| 2 | Amber | `#f59e0b` |
| 3 | Pink | `#ec4899` |
| 4 | Violet | `#8b5cf6` |
| 5 | Cyan | `#06b6d4` |
| 6 | Orange | `#f97316` |
| 7 | Lime | `#84cc16` |
| 8 | Red | `#ef4444` |
| 9 | Teal | `#14b8a6` |

**Color Assignment Algorithm (lines 119-126):**

```javascript
function getTagColor(tag) {
  let hash = 0
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % tagColors.length
  return tagColors[index]
}
```

The color is deterministic - same tag always gets same color based on string hash.

**Bounding Box Calculation (lines 146-176):**

```javascript
tagGroups.forEach((nodesInTag, tag) => {
  // Calculate bounding box
  let minX = Infinity, minY = Infinity
  let maxX = -Infinity, maxY = -Infinity

  nodesInTag.forEach(node => {
    const x = node.position?.x || 0
    const y = node.position?.y || 0

    minX = Math.min(minX, x)
    minY = Math.min(minY, y)
    maxX = Math.max(maxX, x + props.nodeWidth)
    maxY = Math.max(maxY, y + props.nodeHeight)
  })

  // Add padding
  clouds.push({
    tag,
    x: minX - padding,
    y: minY - padding,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
    color: color.bg,
    textColor: color.text,
    nodeCount: nodesInTag.length
  })
})

// Sort by area (largest first) so smaller clouds render on top
clouds.sort((a, b) => (b.width * b.height) - (a.width * a.height))
```

### Dashboard.vue Integration

#### Toggle Button (lines 117-132)

```vue
<!-- Tag Clouds Toggle -->
<button
  v-if="availableTags.length > 0"
  @click="toggleTagClouds"
  :class="[
    'flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium transition-all',
    showTagClouds
      ? 'bg-purple-600 text-white'
      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
  ]"
  title="Toggle tag grouping clouds"
>
  <svg><!-- cloud icon --></svg>
  <span>Clouds</span>
</button>
```

#### State Management (lines 561-565)

```javascript
// Tag clouds visibility toggle (persisted)
const showTagClouds = ref(localStorage.getItem('trinity-show-tag-clouds') !== 'false')

function toggleTagClouds() {
  showTagClouds.value = !showTagClouds.value
  localStorage.setItem('trinity-show-tag-clouds', showTagClouds.value)
}
```

#### TagClouds Rendering (lines 306-329)

```vue
<!-- Tag Clouds Layer (rendered in viewport coordinates) -->
<div
  v-if="showTagClouds && nodes.length > 0"
  class="vue-flow__tag-clouds"
  :style="{
    position: 'absolute',
    top: 0,
    left: 0,
    transformOrigin: '0 0',
    transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
    pointerEvents: 'none',
    zIndex: 0
  }"
>
  <TagClouds
    :nodes="nodes"
    :padding="50"
    :cloud-opacity="0.12"
    :blur-amount="25"
    :cloud-border-radius="40"
    :show-labels="true"
    :node-height="260"
  />
</div>
```

Key points:
- **Viewport Transform**: Clouds transform with pan/zoom using VueFlow's `viewport` ref
- **Z-Index**: Set to 0 so clouds appear behind nodes (nodes have higher z-index)
- **Pointer Events**: Disabled so clouds don't interfere with node interaction

### network.js Store - Tag-Aware Layout

#### Agent Grouping by Primary Tag (lines 317-331)

```javascript
// Group agents by their primary tag (first tag) for layout
const tagGroups = new Map()
const untaggedAgents = []

regularAgents.forEach(agent => {
  const tags = agent.tags || []
  if (tags.length > 0) {
    const primaryTag = tags[0] // Use first tag for grouping
    if (!tagGroups.has(primaryTag)) {
      tagGroups.set(primaryTag, [])
    }
    tagGroups.get(primaryTag).push(agent)
  } else {
    untaggedAgents.push(agent)
  }
})
```

#### Group Layout Configuration (lines 334-363)

```javascript
// Layout configuration - tighter spacing within groups
const nodeWidth = 320
const nodeHeight = 200
const withinGroupPadding = 30   // Tight padding within a group
const betweenGroupPadding = 150 // Space between different groups

// Sort tags by group size (largest first) for better layout
const sortedTags = Array.from(tagGroups.keys()).sort((a, b) =>
  tagGroups.get(b).length - tagGroups.get(a).length
)

// Calculate group dimensions (compact grid per group)
groupLayouts.forEach(tag => {
  const agents = tagGroups.get(tag)
  const cols = Math.ceil(Math.sqrt(agents.length))  // Prefer square-ish
  const rows = Math.ceil(agents.length / cols)
  // ... calculate width/height
})
```

#### Bin-Packing Algorithm (lines 379-398)

```javascript
// Bin-pack groups into rows to minimize total width
const maxRowWidth = 1800
let currentX = offsetX
let currentY = offsetY
let rowHeight = 0

groupLayouts.forEach(group => {
  // Check if we need to wrap to next row
  if (currentX > offsetX && currentX + group.width > maxRowWidth) {
    currentX = offsetX
    currentY += rowHeight + betweenGroupPadding
    rowHeight = 0
  }

  groupPositions.push({ ...group, x: currentX, y: currentY })
  currentX += group.width + betweenGroupPadding
  rowHeight = Math.max(rowHeight, group.height)
})
```

#### Tags Added to Node Data (lines 454-456)

```javascript
result.push({
  id: agent.name,
  type: 'agent',
  data: {
    // ... other properties
    tags: agent.tags || []  // Tags included for TagClouds component
  },
  position: savedPositions[agent.name] || defaultPosition,
  draggable: true
})
```

---

## Data Flow

```
1. Dashboard.vue mounts
       |
       v
2. networkStore.fetchAgents()
       |
       v
3. GET /api/agents (backend returns agents with tags array)
       |
       v
4. convertAgentsToNodes()
       |
       +-- Groups agents by primary tag
       +-- Bin-packing algorithm arranges groups
       +-- Adds tags to node.data
       |
       v
5. nodes ref updated
       |
       v
6. TagClouds computed property recalculates
       |
       +-- Groups nodes by ALL tags (one node can appear in multiple clouds)
       +-- Calculates bounding boxes per tag
       +-- Sorts clouds by area (largest first)
       |
       v
7. SVG clouds rendered in viewport coordinates
       |
       v
8. User pans/zooms -> viewport ref updates -> clouds transform
```

---

## Configuration Options

| Prop | Default | Description |
|------|---------|-------------|
| `padding` | 50 | Pixels of padding around agent nodes within cloud |
| `cloudOpacity` | 0.12 | Opacity of cloud fill (0-1) |
| `blurAmount` | 25 | Gaussian blur standard deviation |
| `cloudBorderRadius` | 40 | Rounded corner radius in pixels |
| `showLabels` | true | Whether to show `#tag` labels in clouds |
| `labelPadding` | 15 | Distance of label from cloud corner |
| `nodeWidth` | 320 | Assumed width of agent nodes |
| `nodeHeight` | 260 | Assumed height of agent nodes |

---

## localStorage Persistence

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `trinity-show-tag-clouds` | string | `'true'` | Whether clouds are visible |

---

## Visual Behavior

1. **Cloud Positioning**: Clouds are positioned in world coordinates and transform with the VueFlow viewport (pan/zoom)

2. **Multi-Tag Agents**: If an agent has multiple tags, it appears in multiple clouds (one per tag)

3. **Cloud Overlap**: Clouds are sorted by area (largest first) so smaller clouds render on top of larger ones

4. **Reset Layout**: When user clicks "Reset Layout", agents are re-grouped by primary tag and arranged using bin-packing

5. **Dark Mode**: Colors remain consistent (no dark mode variants needed as opacity is low)

6. **Transitions**: Clouds have a 0.3s ease-out transition for smooth position changes

---

## Related Files

| Layer | File | Purpose |
|-------|------|---------|
| **Component** | `src/frontend/src/components/TagClouds.vue` | SVG cloud rendering |
| **Dashboard** | `src/frontend/src/views/Dashboard.vue:117-132,306-329,561-565` | Toggle button, integration, state |
| **Store** | `src/frontend/src/stores/network.js:308-464` | Tag-aware layout algorithm |
| **Backend** | `src/backend/routers/agents.py:160-165` | Tags included in agent response |

---

## Side Effects

- **localStorage**: `trinity-show-tag-clouds` persisted for toggle state
- **No WebSocket broadcasts**: Visual-only feature, no server communication for clouds
- **No audit logging**: Toggle state changes not logged

---

## Error Handling

| Error Case | Behavior |
|------------|----------|
| No tags on agents | TagClouds component returns empty array, no clouds rendered |
| Invalid node positions | Falls back to 0,0 for missing positions |
| Missing node dimensions | Uses default nodeWidth/nodeHeight props |

---

## Performance Considerations

1. **Computed Property**: `tagClouds` is a Vue computed property, recalculates only when nodes change
2. **SVG Rendering**: Each cloud is a separate SVG element for proper z-ordering
3. **Blur Filter**: Gaussian blur is GPU-accelerated in modern browsers
4. **No Re-render on Pan/Zoom**: CSS transform handles viewport changes without recalculating clouds

---

## Testing

### Prerequisites

- Trinity frontend running at `http://localhost`
- At least 2 agents with the same tag

### Test Steps

1. **View clouds**
   - Action: Navigate to Dashboard with tagged agents
   - Expected: Semi-transparent colored clouds visible behind agent groups
   - Verify: Agents with same tag have same-colored cloud

2. **Toggle clouds off**
   - Action: Click "Clouds" button in header
   - Expected: Button turns gray, clouds disappear
   - Verify: localStorage `trinity-show-tag-clouds` is `'false'`

3. **Toggle clouds on**
   - Action: Click "Clouds" button again
   - Expected: Button turns purple, clouds reappear
   - Verify: localStorage `trinity-show-tag-clouds` is `'true'`

4. **Persistence**
   - Action: Toggle clouds off, refresh page
   - Expected: Clouds still hidden after refresh
   - Verify: Button shows gray state

5. **Pan and zoom**
   - Action: Pan and zoom the Dashboard canvas
   - Expected: Clouds move and scale with agent nodes
   - Verify: Cloud positions remain aligned with agent groups

6. **Reset layout**
   - Action: Click "Reset Layout" button
   - Expected: Agents grouped by primary tag, clouds recalculate
   - Verify: Clouds surround their respective tag groups

7. **Multi-tag agents**
   - Action: Create agent with 2+ tags
   - Expected: Agent appears in multiple clouds
   - Verify: Each tag has its own cloud containing that agent

8. **Color consistency**
   - Action: Create multiple agents with same tag
   - Expected: All clouds for same tag use same color
   - Verify: Refreshing page maintains same colors

9. **No tags**
   - Action: View Dashboard with untagged agents
   - Expected: No clouds rendered, toggle button still visible
   - Verify: Untagged agents positioned separately

---

## Related Flows

- **Upstream**: [agent-tags.md](agent-tags.md) - Tags system (ORG-001)
- **Related**: [agent-network.md](agent-network.md) - Dashboard VueFlow integration
- **Related**: [dashboard-timeline-view.md](dashboard-timeline-view.md) - Dashboard views

---

## Revision History

| Date | Change |
|------|--------|
| 2026-02-25 | Initial implementation - TagClouds component, Dashboard integration, tag-aware layout in network.js |
