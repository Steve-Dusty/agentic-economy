# Authenticated Chat Tab (CHAT-001)

> **Status**: NOT STARTED
> **Priority**: HIGH
> **Created**: 2026-02-19

## Overview

Add a dedicated **Chat** tab to the Agent Detail page that provides a simple, clean chat interface for authenticated users. This complements (not replaces) the Terminal tab, which remains available for full Claude Code TUI access.

The Chat tab uses headless execution (like Tasks), so all activity appears in the Dashboard timeline and is tracked in the database.

## User Story

As an authenticated user, I want a simple chat interface with my agents that:
- Has a clean, modern UI (like PublicChat)
- Supports multi-turn conversations with session persistence
- Lets me switch between past sessions
- Shows all activity in the Dashboard (unlike Terminal which is TUI-only)
- Works consistently with how public links work

## Goals

1. **Consistent UX** - Chat tab and PublicChat.vue should share components and look identical
2. **Session Management** - Users can view, switch, and create chat sessions
3. **Dashboard Integration** - All chat activity visible in Dashboard timeline (uses headless execution)
4. **Simple Interface** - Clean bubbles, markdown rendering, no TUI complexity
5. **Coexistence** - Terminal tab remains for power users who want full TUI

## Architecture

### Component Hierarchy

```
AgentDetail.vue
├── [Chat] tab (NEW)
│   └── ChatPanel.vue (NEW)
│       ├── ChatSessionSelector.vue (NEW) - dropdown/sidebar for session switching
│       └── ChatMessages.vue (SHARED) - extracted from PublicChat.vue
│           ├── Message bubbles
│           ├── Markdown rendering
│           └── Input area
├── [Terminal] tab (unchanged)
└── [Tasks] tab (unchanged)
```

### Shared Components (Extract from PublicChat.vue)

Extract reusable chat components to `src/frontend/src/components/chat/`:

| Component | Purpose | Used By |
|-----------|---------|---------|
| `ChatMessages.vue` | Message list with bubbles, markdown, auto-scroll | ChatPanel, PublicChat |
| `ChatInput.vue` | Auto-resize textarea with send button | ChatPanel, PublicChat |
| `ChatBubble.vue` | Individual message bubble (user/assistant styling) | ChatMessages |
| `ChatLoadingIndicator.vue` | Bouncing dots "Thinking..." indicator | ChatMessages |

### Backend Integration

Use existing endpoints - no new backend work required:

| Endpoint | Purpose |
|----------|---------|
| `POST /api/agents/{name}/task` | Send messages (headless, shows in Dashboard) |
| `GET /api/agents/{name}/chat/sessions` | List user's sessions |
| `GET /api/agents/{name}/chat/sessions/{id}` | Get session with messages |
| `POST /api/agents/{name}/chat/sessions/{id}/close` | Close a session |

**Why `/task` not `/chat`?**
- `/task` uses headless execution - activities tracked in Dashboard
- `/chat` uses `--continue` flag for conversation context but doesn't track well in Dashboard
- For Chat tab, we want visibility in Dashboard like Tasks

**Session Handling:**
- Each `/task` call is stateless but we store messages in `chat_messages` table
- Frontend builds conversation context from session history
- Similar to how PublicChat works with `PUB-005`

## UI Design

### Chat Tab Layout

```
┌─────────────────────────────────────────────────────────────┐
│ [Session Selector v] [+ New Chat]               [Sessions] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                   [Messages Area]                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ User message (blue bubble, right-aligned)            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Assistant message (white bubble, left-aligned)       │   │
│  │ With **markdown** support                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ●●● Thinking...                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐    │
│ │ Type your message...                            [▶]  │    │
│ └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Session Selector (Top Bar)

- **Dropdown** showing current session name/date
- **"+ New Chat"** button to start fresh session
- **Sessions list** - click to switch sessions
- Session shows: date, message count, preview of last message

### Styling

Match PublicChat.vue exactly:
- User messages: `bg-indigo-600 text-white` (right-aligned)
- Assistant messages: `bg-white dark:bg-gray-800` with shadow (left-aligned)
- Markdown: `prose prose-sm dark:prose-invert`
- Input: Clean textarea with send button
- Loading: Bouncing dots with "Thinking..."

## Implementation Plan

### Phase 1: Extract Shared Components
1. Create `src/frontend/src/components/chat/` directory
2. Extract `ChatMessages.vue` from PublicChat.vue
3. Extract `ChatInput.vue` from PublicChat.vue
4. Refactor PublicChat.vue to use extracted components
5. Verify PublicChat still works identically

### Phase 2: Create ChatPanel
1. Create `ChatPanel.vue` component
2. Implement session selector UI
3. Integrate ChatMessages and ChatInput
4. Wire up to `/api/task` endpoint
5. Implement session switching

### Phase 3: Integrate into AgentDetail
1. Add "Chat" tab to AgentDetail.vue
2. Position after Tasks tab
3. Load ChatPanel component
4. Pass agent name prop

### Phase 4: Session Management
1. Load user's sessions on mount
2. Switch sessions (load history)
3. Create new session
4. Close session
5. Session persistence in URL (optional)

## API Usage

### Sending a Message

```javascript
// Use /task endpoint for headless execution (Dashboard tracking)
const response = await axios.post(`/api/agents/${agentName}/task`, {
  message: userMessage,
  // Note: No conversation context in request - agent is stateless
  // We'll prepend conversation history in the message itself
}, {
  headers: { Authorization: `Bearer ${token}` }
})
```

### Building Conversation Context

Since `/task` is stateless, we build context like PublicChat does:

```javascript
// Load session history
const history = await axios.get(`/api/agents/${agentName}/chat/sessions/${sessionId}`)

// Build context prompt
const contextPrompt = buildContextFromHistory(history.messages, userMessage)

// Send with context
await axios.post(`/api/agents/${agentName}/task`, {
  message: contextPrompt
})
```

### Session Management

```javascript
// List sessions
const sessions = await axios.get(`/api/agents/${agentName}/chat/sessions`)

// Get session details
const session = await axios.get(`/api/agents/${agentName}/chat/sessions/${sessionId}`)

// Close session
await axios.post(`/api/agents/${agentName}/chat/sessions/${sessionId}/close`)
```

## Data Flow

```
User types message
    │
    ▼
ChatPanel prepends session history to message
    │
    ▼
POST /api/agents/{name}/task
    │
    ├─► schedule_executions table (execution record)
    ├─► agent_activities table (Dashboard tracking)
    └─► Agent container executes headless
            │
            ▼
        Response returned
            │
            ▼
ChatPanel stores message in local state
    │
    ▼
Backend stores in chat_messages table (via session)
    │
    ▼
Dashboard shows activity in timeline
```

## Differences from Terminal Tab

| Aspect | Chat Tab | Terminal Tab |
|--------|----------|--------------|
| Interface | Simple bubbles | Full TUI (xterm.js) |
| Execution | Headless (`/task`) | Interactive (PTY) |
| Dashboard | ✅ Shows in timeline | ❌ Not tracked |
| Session | Switchable, persistent | Single stream |
| Model | Sonnet (default) | Per-session |
| Power | Basic chat | Full Claude Code |

## Differences from Public Chat

| Aspect | Chat Tab | Public Chat |
|--------|----------|-------------|
| Auth | JWT token | Public link token |
| API | `/api/agents/...` | `/api/public/...` |
| Sessions | Full session list | Single session per link |
| Features | Model selection | Basic only |
| Components | **SHARED** | **SHARED** |

## Testing

### Test Cases

1. **Basic Chat**
   - Send message, receive response
   - Messages display correctly (user right, assistant left)
   - Markdown renders properly

2. **Session Management**
   - List existing sessions
   - Switch between sessions
   - Create new session
   - Session history loads correctly

3. **Dashboard Integration**
   - Chat activity appears in Dashboard timeline
   - Execution recorded in Tasks tab

4. **Component Sharing**
   - Verify PublicChat still works after component extraction
   - UI consistency between Chat tab and PublicChat

5. **Edge Cases**
   - Long messages scroll correctly
   - Empty session state
   - Agent not running state
   - Network error handling

## Files to Create/Modify

### New Files
- `src/frontend/src/components/chat/ChatMessages.vue`
- `src/frontend/src/components/chat/ChatInput.vue`
- `src/frontend/src/components/chat/ChatBubble.vue`
- `src/frontend/src/components/chat/ChatLoadingIndicator.vue`
- `src/frontend/src/components/chat/ChatSessionSelector.vue`
- `src/frontend/src/components/ChatPanel.vue`

### Modified Files
- `src/frontend/src/views/PublicChat.vue` - Refactor to use shared components
- `src/frontend/src/views/AgentDetail.vue` - Add Chat tab

### No Backend Changes Required
- Existing endpoints cover all functionality

## Success Criteria

1. ✅ Chat tab appears in AgentDetail after Tasks
2. ✅ Messages display in clean bubble UI identical to PublicChat
3. ✅ Session selector allows switching between conversations
4. ✅ New Chat creates fresh session
5. ✅ All chat activity visible in Dashboard timeline
6. ✅ PublicChat continues to work (uses same components)
7. ✅ Terminal tab unchanged for power users

## Out of Scope

- Model selector (use Tasks for model control)
- File uploads
- Voice input
- Real-time streaming (batch response only)
- Code execution results display (use Tasks/Terminal)

## Related

- **PublicChat.vue** - Source for shared components
- **TasksPanel.vue** - Similar headless execution pattern
- **PUB-005** - Public chat session persistence (reference implementation)
- **docs/memory/feature-flows/persistent-chat-tracking.md** - Session API docs
