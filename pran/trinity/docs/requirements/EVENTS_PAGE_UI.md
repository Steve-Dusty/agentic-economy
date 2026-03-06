# Events Page UI (NOTIF-002)

> **Status**: Not Started
> **Priority**: HIGH
> **Created**: 2026-02-20
> **Depends On**: NOTIF-001 (Agent Notifications Backend) - COMPLETED

## Overview

Add a dedicated "Events" page to the Trinity UI for viewing, filtering, and managing agent notifications. The page provides a unified stream of all agent events with real-time updates via WebSocket.

## User Stories

1. As a **platform user**, I want to see all notifications from my agents in one place so I can quickly identify what needs attention.

2. As a **platform user**, I want to filter notifications by agent, priority, or type so I can focus on what's relevant.

3. As a **platform user**, I want to acknowledge or dismiss notifications so I can track what I've reviewed.

4. As a **platform user**, I want to see new notifications appear in real-time so I don't miss urgent alerts.

5. As a **platform user**, I want a badge showing unread notification count so I know when something needs attention.

---

## UI Components

### 1. Navigation Entry

**Location**: Main sidebar navigation

```
Dashboard
Agents
Events       <-- NEW (with badge for pending count)
Processes
Settings
```

**Badge Behavior**:
- Show count of pending (unacknowledged) notifications
- Badge color: Red for urgent/high priority pending, otherwise default
- Hide badge when count is 0
- Update in real-time via WebSocket

---

### 2. Events Page Layout

**Route**: `/events`

```
┌─────────────────────────────────────────────────────────────────┐
│  Events                                          [Refresh] [⚙]  │
├─────────────────────────────────────────────────────────────────┤
│  Filters:                                                       │
│  [All Agents ▼] [All Types ▼] [All Priorities ▼] [Status ▼]    │
│                                                                 │
│  [ ] Show dismissed                              X Clear filters│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🔴 HIGH  competitor-analyzer              2 minutes ago │   │
│  │ High CPU usage detected                                  │   │
│  │ Agent competitor-analyzer is using 95% CPU               │   │
│  │ Category: health                    [Acknowledge] [Dismiss]│ │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ✅ COMPLETE  storypipe                      5 minutes ago│   │
│  │ Daily report generated                                   │   │
│  │ Processed 15,000 records successfully                    │   │
│  │ Category: progress                  [Acknowledge] [Dismiss]│ │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ❓ QUESTION  research-agent                 10 minutes ago│  │
│  │ Clarification needed                                     │   │
│  │ Found 3 duplicate entries. Should I merge or skip?       │   │
│  │ Category: input                     [Acknowledge] [Dismiss]│ │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Load more...]                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. Event Card Component

Each notification displays as a card with:

**Header Row**:
- Priority indicator (icon + color)
- Notification type icon
- Agent name (clickable → agent detail page)
- Relative timestamp ("2 minutes ago")
- Status indicator (pending/acknowledged/dismissed)

**Body**:
- Title (bold)
- Message (if present, truncated with "show more")
- Category tag (if present)
- Metadata preview (if present, expandable)

**Actions**:
- Acknowledge button (for pending notifications)
- Dismiss button (always available)
- Expand/collapse for long messages or metadata

**Visual States**:
| Status | Appearance |
|--------|------------|
| Pending | Full opacity, action buttons visible |
| Acknowledged | Slightly muted, checkmark indicator |
| Dismissed | Muted/grayed out, hidden by default |

---

### 4. Priority Indicators

| Priority | Icon | Color | Badge |
|----------|------|-------|-------|
| Urgent | 🚨 | Red (#EF4444) | Pulsing |
| High | 🔴 | Orange (#F97316) | Solid |
| Normal | 🔵 | Blue (#3B82F6) | None |
| Low | ⚪ | Gray (#6B7280) | None |

---

### 5. Notification Type Icons

| Type | Icon | Description |
|------|------|-------------|
| Alert | ⚠️ | Urgent issues needing attention |
| Info | ℹ️ | General information |
| Status | 📊 | Progress/status updates |
| Completion | ✅ | Task/job completions |
| Question | ❓ | User input needed |

---

### 6. Filter Controls

**Agent Filter** (Dropdown):
- "All Agents" (default)
- List of agents with notifications
- Show notification count per agent

**Type Filter** (Dropdown):
- "All Types" (default)
- Alert, Info, Status, Completion, Question

**Priority Filter** (Multi-select):
- "All Priorities" (default)
- Urgent, High, Normal, Low

**Status Filter** (Dropdown):
- "Pending" (default)
- "Acknowledged"
- "All"

**Show Dismissed** (Checkbox):
- Hidden by default
- When checked, includes dismissed notifications

**Clear Filters** (Button):
- Resets all filters to defaults

---

### 7. Real-Time Updates

**WebSocket Integration**:
- Connect to `/ws` with auth token
- Listen for `agent_notification` events
- On new notification:
  - Prepend to list (if matches current filters)
  - Show toast notification for urgent/high priority
  - Update nav badge count
  - Play sound (optional, configurable)

**Toast Notification**:
```
┌────────────────────────────────────┐
│ 🔴 competitor-analyzer             │
│ High CPU usage detected            │
│                        [View] [✕]  │
└────────────────────────────────────┘
```

---

### 8. Bulk Actions

**Select Mode**:
- Checkbox on each card for multi-select
- "Select All" checkbox in header
- Bulk action buttons appear when items selected:
  - "Acknowledge Selected"
  - "Dismiss Selected"

---

### 9. Empty States

**No Notifications**:
```
┌─────────────────────────────────────────┐
│                                         │
│         📭 No events yet                │
│                                         │
│   Notifications from your agents will   │
│   appear here when they send them.      │
│                                         │
└─────────────────────────────────────────┘
```

**No Matching Filters**:
```
┌─────────────────────────────────────────┐
│                                         │
│         🔍 No matching events           │
│                                         │
│   Try adjusting your filters or         │
│   [Clear all filters]                   │
│                                         │
└─────────────────────────────────────────┘
```

---

## API Integration

### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/notifications` | GET | List notifications with filters |
| `/api/notifications/{id}/acknowledge` | POST | Acknowledge notification |
| `/api/notifications/{id}/dismiss` | POST | Dismiss notification |
| `/ws` | WebSocket | Real-time notification events |

### Query Parameters

```
GET /api/notifications?agent_name=<agent>&status=pending&priority=high,urgent&limit=50
```

### WebSocket Event

```json
{
  "type": "agent_notification",
  "notification_id": "notif_abc123",
  "agent_name": "research-agent",
  "notification_type": "completion",
  "title": "Analysis complete",
  "priority": "normal",
  "category": "progress",
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

## State Management

### Pinia Store: `useEventsStore`

```javascript
// stores/events.js
export const useEventsStore = defineStore('events', {
  state: () => ({
    notifications: [],
    filters: {
      agent_name: null,
      notification_type: null,
      priority: [],
      status: 'pending',
      showDismissed: false
    },
    loading: false,
    hasMore: true,
    pendingCount: 0,
    selectedIds: []
  }),

  actions: {
    async fetchNotifications(append = false),
    async acknowledgeNotification(id),
    async dismissNotification(id),
    async bulkAcknowledge(ids),
    async bulkDismiss(ids),
    addNotification(notification),  // For WebSocket
    updatePendingCount()
  },

  getters: {
    filteredNotifications: (state) => ...,
    hasUrgentPending: (state) => ...,
    agentCounts: (state) => ...
  }
})
```

---

## Component Structure

```
src/views/
  EventsView.vue              # Main events page

src/components/events/
  EventCard.vue               # Single notification card
  EventFilters.vue            # Filter controls
  EventActions.vue            # Acknowledge/Dismiss buttons
  EventBadge.vue              # Priority/type badges
  EventMetadata.vue           # Expandable metadata display
  EventToast.vue              # Real-time notification toast
  EventEmptyState.vue         # Empty/no-results states

src/stores/
  events.js                   # Events Pinia store

src/composables/
  useEventNotifications.js    # WebSocket subscription hook
```

---

## Navigation Badge Component

**Location**: `src/components/layout/NavBadge.vue`

```vue
<template>
  <span v-if="count > 0"
        :class="['badge', { 'badge-urgent': hasUrgent }]">
    {{ count > 99 ? '99+' : count }}
  </span>
</template>
```

**Integration**: Add to sidebar nav item for Events

---

## Accessibility

- Keyboard navigation for all actions
- ARIA labels for status indicators
- Screen reader announcements for new notifications
- Focus management when acknowledging/dismissing
- High contrast mode support for priority colors

---

## Mobile Responsiveness

**Breakpoints**:
- Desktop (>1024px): Full layout with sidebar filters
- Tablet (768-1024px): Collapsible filter panel
- Mobile (<768px): Bottom sheet filters, stacked cards

**Mobile Card Layout**:
- Swipe left to dismiss
- Swipe right to acknowledge
- Tap to expand details

---

## Performance Considerations

- Virtual scrolling for large notification lists (>100 items)
- Pagination with "Load more" (default 50 per page)
- Debounce filter changes (300ms)
- Cache notification data in store
- Optimistic UI updates for acknowledge/dismiss

---

## Implementation Phases

### Phase 1: Core Page
1. Create EventsView.vue with basic list
2. Create EventCard.vue component
3. Create events.js Pinia store
4. Add route and navigation entry
5. Implement list/filter API calls

### Phase 2: Actions & Filters
6. Add acknowledge/dismiss functionality
7. Implement filter controls
8. Add bulk actions
9. Add empty states

### Phase 3: Real-Time
10. Integrate WebSocket subscription
11. Add toast notifications
12. Add navigation badge with count
13. Implement sound notifications (optional)

### Phase 4: Polish
14. Add virtual scrolling
15. Mobile responsive layout
16. Accessibility audit
17. Performance optimization

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/views/EventsView.vue` | Create | Main events page |
| `src/components/events/EventCard.vue` | Create | Notification card |
| `src/components/events/EventFilters.vue` | Create | Filter controls |
| `src/components/events/EventActions.vue` | Create | Action buttons |
| `src/components/events/EventToast.vue` | Create | Toast component |
| `src/stores/events.js` | Create | Pinia store |
| `src/composables/useEventNotifications.js` | Create | WebSocket hook |
| `src/router/index.js` | Modify | Add /events route |
| `src/components/layout/Sidebar.vue` | Modify | Add Events nav item |
| `src/App.vue` | Modify | Add toast container |

---

## Success Criteria

1. User can view all notifications on dedicated Events page
2. Notifications appear in real-time via WebSocket
3. User can filter by agent, type, priority, status
4. User can acknowledge and dismiss notifications
5. Navigation badge shows pending count
6. Toast notifications appear for urgent/high priority
7. Page is responsive and accessible
8. Performance acceptable with 100+ notifications

---

## Design References

- Follow existing Trinity UI patterns (Tailwind CSS)
- Use existing color palette and component styles
- Reference: AgentDetail.vue for card layouts
- Reference: ActivitiesPanel.vue for timeline patterns

---

## Related Documents

- `docs/requirements/AGENT_NOTIFICATIONS.md` - Backend implementation
- `docs/memory/feature-flows/agent-notifications.md` - Feature flow
- `docs/memory/feature-flows/activity-stream.md` - Similar UI patterns
