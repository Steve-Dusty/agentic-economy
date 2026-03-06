# Public Chat Session Persistence (PUB-005)

> **Status**: Proposed
> **Priority**: Medium
> **Complexity**: Medium
> **Created**: 2026-02-17

## Problem Statement

Currently, public chat (`/chat/:token`) uses the stateless `/api/task` endpoint for each message. This means:

1. **No conversation continuity** - Each message is independent with no context from previous exchanges
2. **No memory of prior interactions** - Returning users start fresh every time
3. **No way to clear context** - Users cannot reset the conversation if it goes off track

### Current Architecture

```
PublicChat.vue
    |
    v
POST /api/public/chat/{token}
    |
    v
Backend (public.py)
    |
    v
POST http://agent-{name}:8000/api/task   <-- Stateless, no history
    |
    v
Claude Code (no --continue flag)
```

**Comparison with Authenticated Chat:**

| Feature | Authenticated Chat | Public Chat (Current) |
|---------|-------------------|----------------------|
| Endpoint | `/api/chat` | `/api/task` |
| Context preservation | Yes (`--continue`) | No |
| Session persistence | SQLite (`chat_sessions`) | None |
| Multi-turn conversation | Yes | No |
| Cost tracking | Per-session | None |

## Requirements

### Functional Requirements

#### FR1: Session Identification
- **FR1.1**: For email-verified links, session is identified by `link_id + verified_email`
- **FR1.2**: For no-email links, session is identified by `link_id + session_id` (stored in localStorage)
- **FR1.3**: Session identifier must be stable across page refreshes

#### FR2: Conversation Persistence
- **FR2.1**: All public chat messages (user + assistant) must be stored in the database
- **FR2.2**: History must survive browser refresh and page close
- **FR2.3**: History must be retrievable when user returns with same session identifier

#### FR3: Conversation Context
- **FR3.1**: When sending a message, include previous messages as context
- **FR3.2**: Context should be limited to a reasonable number of turns (e.g., last 10 exchanges)
- **FR3.3**: Agent should respond aware of conversation history

#### FR4: New Conversation Button
- **FR4.1**: Provide "New Conversation" button in the chat header
- **FR4.2**: Clicking resets the session - clears history and starts fresh
- **FR4.3**: For email-verified links, creates new session with same email
- **FR4.4**: For no-email links, generates new session_id

#### FR5: Session Metadata (Nice-to-have)
- **FR5.1**: Track message count per session
- **FR5.2**: Track session start time and last activity
- **FR5.3**: Track total cost per session (if available)

### Non-Functional Requirements

#### NFR1: Performance
- Adding history context should not significantly increase response time
- Database queries should be indexed efficiently

#### NFR2: Privacy
- Sessions for different users must be completely isolated
- No cross-link session leakage

#### NFR3: Storage
- Old sessions should be prunable (e.g., after 30 days of inactivity)

## Proposed Solution

### Approach: Platform-Side Session Management

Store conversation history at the platform level (backend database) and inject it as context when sending messages to the agent. This approach:

- Requires no agent-server changes
- Uses existing database infrastructure
- Works with any agent template
- Enables analytics and cost tracking

### Architecture

```
PublicChat.vue
    |
    | session_id (localStorage or from email verification)
    v
POST /api/public/chat/{token}
    |
    | { message, session_id }
    v
Backend (public.py)
    |
    | 1. Get or create public_chat_session
    | 2. Store user message
    | 3. Fetch last N messages for context
    | 4. Build contextual prompt
    v
POST http://agent-{name}:8000/api/task
    |
    | { message: <with context prefix>, system_prompt: <optional> }
    v
Claude Code (stateless but with injected context)
    |
    v
Backend
    |
    | 5. Store assistant response
    | 6. Return to frontend
    v
PublicChat.vue
```

### Database Schema

#### public_chat_sessions

```sql
CREATE TABLE public_chat_sessions (
    id TEXT PRIMARY KEY,                    -- Unique session ID (token_urlsafe(16))
    link_id TEXT NOT NULL,                  -- FK to agent_public_links
    session_identifier TEXT NOT NULL,       -- email or generated session_id
    identifier_type TEXT NOT NULL,          -- 'email' or 'anonymous'
    created_at TEXT NOT NULL,               -- ISO timestamp
    last_message_at TEXT NOT NULL,          -- ISO timestamp
    message_count INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0.0,
    FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE,
    UNIQUE(link_id, session_identifier)
);

CREATE INDEX idx_public_sessions_link ON public_chat_sessions(link_id);
CREATE INDEX idx_public_sessions_identifier ON public_chat_sessions(session_identifier);
CREATE INDEX idx_public_sessions_last_message ON public_chat_sessions(last_message_at);
```

#### public_chat_messages

```sql
CREATE TABLE public_chat_messages (
    id TEXT PRIMARY KEY,                    -- Unique message ID
    session_id TEXT NOT NULL,               -- FK to public_chat_sessions
    role TEXT NOT NULL,                     -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,                -- ISO timestamp
    cost REAL,                              -- Cost for assistant messages
    FOREIGN KEY (session_id) REFERENCES public_chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_public_messages_session ON public_chat_messages(session_id);
CREATE INDEX idx_public_messages_timestamp ON public_chat_messages(timestamp);
```

### API Changes

#### Modified: POST /api/public/chat/{token}

**Request Body** (updated):
```json
{
    "message": "User's message",
    "session_token": "abc123...",           // For email-verified links
    "session_id": "xyz789..."               // For no-email links (from localStorage)
}
```

**Backend Logic**:
1. Validate link token
2. Determine session identifier:
   - If `require_email`: use verified email from session_token
   - If no email required: use provided `session_id` or generate new one
3. Get or create `public_chat_session`
4. Store user message in `public_chat_messages`
5. Fetch last 10 message pairs for context
6. Build contextual prompt:
   ```
   Previous conversation:
   User: [message 1]
   Assistant: [response 1]
   ...

   Current message:
   User: [new message]
   ```
7. Send to agent's `/api/task` endpoint
8. Store assistant response
9. Update session metadata
10. Return response with session info

**Response** (updated):
```json
{
    "response": "Agent's response",
    "session_id": "xyz789...",              // Return for localStorage storage
    "message_count": 5,
    "usage": { ... }
}
```

#### New: DELETE /api/public/session/{token}

Clears the current session (for "New Conversation" button).

**Request Body**:
```json
{
    "session_token": "abc123...",           // For email-verified links
    "session_id": "xyz789..."               // For no-email links
}
```

**Response**:
```json
{
    "status": "cleared",
    "new_session_id": "new123..."           // For no-email links
}
```

### Frontend Changes

#### PublicChat.vue Updates

1. **Session ID Management**:
   ```javascript
   // For no-email links, get/create session_id in localStorage
   const sessionId = ref(localStorage.getItem(`public_chat_session_${token.value}`) || '')

   // Store session_id from response
   const handleResponse = (response) => {
       if (response.session_id && !linkInfo.value.require_email) {
           sessionId.value = response.session_id
           localStorage.setItem(`public_chat_session_${token.value}`, response.session_id)
       }
   }
   ```

2. **New Conversation Button**:
   ```vue
   <button @click="newConversation" class="...">
       <RefreshIcon class="w-4 h-4 mr-1" />
       New Conversation
   </button>
   ```

3. **Clear Session Handler**:
   ```javascript
   const newConversation = async () => {
       if (confirm('Start a new conversation? This will clear the current chat history.')) {
           await axios.delete(`/api/public/session/${token.value}`, {
               data: {
                   session_token: sessionToken.value,
                   session_id: sessionId.value
               }
           })
           messages.value = []
           sessionId.value = ''  // Will get new one on next message
           localStorage.removeItem(`public_chat_session_${token.value}`)
           await fetchIntro()  // Re-fetch intro for fresh start
       }
   }
   ```

### Context Injection Strategy

When building the prompt for the agent:

```python
def build_contextual_prompt(message: str, history: List[dict], max_turns: int = 10) -> str:
    """Build prompt with conversation history context."""

    if not history:
        return message

    # Take last N turns (user + assistant pairs)
    recent = history[-(max_turns * 2):]

    context_parts = ["Previous conversation:"]
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        context_parts.append(f"{role}: {msg['content']}")

    context_parts.append("")
    context_parts.append("Current message:")
    context_parts.append(f"User: {message}")

    return "\n".join(context_parts)
```

**Alternative: System Prompt Injection**

Instead of prefixing the message, use the `system_prompt` parameter of `/api/task`:

```python
system_prompt = f"""You are continuing a conversation. Here is the history:

{format_history(history)}

Continue the conversation naturally. Respond to the user's latest message."""
```

## Implementation Plan

### Phase 1: Database & Backend (Backend-only)
1. Create database tables (`public_chat_sessions`, `public_chat_messages`)
2. Add database operations class (`db/public_chat.py`)
3. Modify `POST /api/public/chat/{token}` to persist messages
4. Add `DELETE /api/public/session/{token}` endpoint
5. Implement context injection

### Phase 2: Frontend Updates
1. Add session_id management for no-email links
2. Update chat request to include session info
3. Add "New Conversation" button
4. Handle session_id in responses

### Phase 3: Testing & Polish
1. Test email-verified flow
2. Test anonymous flow
3. Test session persistence across refresh
4. Test new conversation button
5. Test context injection quality

## Alternatives Considered

### Alternative A: Agent-Side Multi-Session Support

**Approach**: Modify `agent_server/state.py` to support multiple isolated sessions:
```python
class AgentState:
    sessions: Dict[str, SessionState] = {}

    def get_session(self, session_id: str) -> SessionState:
        ...
```

**Pros**:
- True context window tracking
- Proper `--continue` flag support
- Lower token usage (no repeated history)

**Cons**:
- Requires agent-server changes (affects all agents)
- More complex memory management
- Session cleanup complexity

**Decision**: Deferred. Platform-side approach is simpler for MVP. Can evolve later if needed.

### Alternative B: Use Authenticated Chat Endpoint

**Approach**: Create temporary platform users for public sessions and use existing `/api/agents/{name}/chat`.

**Pros**:
- Reuses existing infrastructure completely
- Full observability

**Cons**:
- User table pollution
- Complex cleanup
- Security concerns (fake users)

**Decision**: Rejected. Too hacky and creates maintenance burden.

## Security Considerations

1. **Session Isolation**: Different session_ids must have completely separate histories
2. **Rate Limiting**: Existing rate limits apply per IP
3. **Session Hijacking**: session_ids are cryptographically random (`token_urlsafe(16)`)
4. **Link Scope**: Sessions are scoped to specific links (link_id FK)
5. **Cascade Delete**: Deleting a link deletes all its sessions and messages

## Testing Requirements

| Test Case | Steps | Expected |
|-----------|-------|----------|
| Session creation (email) | Verify email, send message | Session created with email identifier |
| Session creation (anon) | Send message without email | Session created, session_id returned |
| Session persistence | Send messages, refresh page, send more | History maintained |
| New conversation | Click "New Conversation" | History cleared, new session started |
| Context in response | Send follow-up question | Agent responds aware of context |
| Session isolation | Two users same link | Each has own history |
| Link deletion | Delete public link | Sessions cascade deleted |

## Related Documents

- [public-agent-links.md](../memory/feature-flows/public-agent-links.md) - Current public chat implementation
- [persistent-chat-tracking.md](../memory/feature-flows/persistent-chat-tracking.md) - Authenticated chat sessions
- [parallel-headless-execution.md](../memory/feature-flows/parallel-headless-execution.md) - `/api/task` endpoint
- [execution-queue.md](../memory/feature-flows/execution-queue.md) - Queue bypass for public chat

## Open Questions

1. **Context limit**: How many turns of history to include? (Proposed: 10)
2. **Session expiry**: Auto-expire sessions after N days of inactivity? (Proposed: 30 days)
3. **Cost tracking**: Include cost in response for transparency? (Proposed: Optional)
4. **History export**: Allow users to download their conversation? (Proposed: Future)

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-02-17 | Claude | Initial requirements document |
