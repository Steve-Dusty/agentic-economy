# Phase 21: Session Management

> **Purpose**: Validate chat session listing, viewing, and closing functionality
> **Duration**: ~15 minutes
> **Assumes**: Phase 2 PASSED (agents running), messages sent to agents
> **Output**: Session management verified

---

## Background

**Session Management** (EXEC-018 to EXEC-021):
- Chat sessions persist across agent restarts
- Users can list all their sessions with an agent
- Sessions show message counts, costs, and timestamps
- Sessions can be closed (archived)
- New session resets context

**User Stories**:
- EXEC-018: Persistent chat history
- EXEC-019: See all chat sessions
- EXEC-020: View specific session messages
- EXEC-021: Close a session

---

## Prerequisites

- [ ] Phase 2 PASSED (agents created and running)
- [ ] At least one agent with chat history
- [ ] Messages sent via Terminal tab

---

## Test: Session Creation

### Step 1: Send Messages to Create Session
**Action**:
- Navigate to agent detail page
- Click Terminal tab
- Send message: "Hello, this is a test message for session tracking"
- Wait for response
- Send another message: "What is 2 + 2?"
- Wait for response

**Expected**:
- [ ] Messages sent successfully
- [ ] Responses received
- [ ] Session created automatically

**Verify**:
- [ ] No session creation UI needed (automatic)
- [ ] Messages accumulate in session

---

### Step 2: Verify Session via API
**Action**:
- Open browser DevTools → Network tab
- Or use curl to check sessions

```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agents/{name}/chat/sessions
```

**Expected Response**:
```json
{
  "sessions": [
    {
      "id": "abc123...",
      "agent_name": "test-echo",
      "started_at": "2026-01-14T10:00:00Z",
      "last_message_at": "2026-01-14T10:05:00Z",
      "message_count": 4,
      "total_cost": 0.0123,
      "status": "active"
    }
  ]
}
```

**Verify**:
- [ ] Session ID generated
- [ ] Message count accurate (user + assistant)
- [ ] Timestamps correct
- [ ] Cost tracked

---

## Test: Session Persistence

### Step 3: Test Session Survives Refresh
**Action**:
- Refresh the page (F5)
- Navigate back to agent Terminal
- Check conversation history

**Expected**:
- [ ] Previous messages still visible
- [ ] Session continues (same session ID)
- [ ] Context maintained

**Verify**:
- [ ] No data loss on refresh
- [ ] Session state persisted

---

### Step 4: Test Session Survives Agent Restart
**Action**:
- Stop the agent (click Stop button)
- Wait 5 seconds
- Start the agent (click Start button)
- Wait for agent to become ready
- Navigate to Terminal tab

**Expected**:
- [ ] Session data still available
- [ ] Chat history accessible
- [ ] Previous messages can be retrieved

**Verify**:
- [ ] Sessions persisted in database (not container)
- [ ] Session survives container recreation

---

## Test: View Session Details

### Step 5: Get Session Details via API
**Action**:
- Get session ID from previous API call
- Request session details

```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agents/{name}/chat/sessions/{session_id}
```

**Expected Response**:
```json
{
  "id": "abc123...",
  "agent_name": "test-echo",
  "started_at": "2026-01-14T10:00:00Z",
  "last_message_at": "2026-01-14T10:05:00Z",
  "message_count": 4,
  "total_cost": 0.0123,
  "total_context_used": 15000,
  "total_context_max": 200000,
  "status": "active",
  "messages": [
    {
      "id": "msg1...",
      "role": "user",
      "content": "Hello, this is a test message...",
      "timestamp": "2026-01-14T10:00:00Z"
    },
    {
      "id": "msg2...",
      "role": "assistant",
      "content": "Hello! I received your test...",
      "timestamp": "2026-01-14T10:00:05Z",
      "cost": 0.005,
      "context_used": 5000
    }
  ]
}
```

**Verify**:
- [ ] All messages included
- [ ] Message order correct (chronological)
- [ ] Role correctly identified (user/assistant)
- [ ] Cost per message (assistant only)
- [ ] Context usage tracked

---

## Test: Multiple Sessions

### Step 6: Create New Session
**Action**:
- Click "New Session" or "Reset Session" button in Terminal
- Or via API: `POST /api/agents/{name}/chat/session/new`
- Confirm if prompted

**Expected**:
- [ ] New session created
- [ ] Previous session marked as closed/archived
- [ ] Chat area cleared
- [ ] Context reset to 0%

**Verify**:
- [ ] New session ID generated
- [ ] Old session preserved (not deleted)

---

### Step 7: Send Messages in New Session
**Action**:
- In new session, send: "This is a new session"
- Wait for response

**Expected**:
- [ ] Message sent in new session
- [ ] Context starts fresh (low percentage)
- [ ] No carryover from previous session

**Verify**:
- [ ] New session has separate message history
- [ ] Old session messages not shown

---

### Step 8: List Multiple Sessions
**Action**:
- Get all sessions for agent

```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agents/{name}/chat/sessions
```

**Expected**:
- [ ] Multiple sessions listed
- [ ] Most recent first
- [ ] Status shows: active (current), closed (previous)

**Verify**:
- [ ] Can distinguish between sessions
- [ ] Each session has unique ID
- [ ] Timestamps help identify sessions

---

## Test: Close Session

### Step 9: Close Current Session
**Action**:
- Close the current session via API

```bash
curl -X POST -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agents/{name}/chat/sessions/{session_id}/close
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Session closed",
  "session_id": "abc123..."
}
```

**Verify**:
- [ ] Session status changed to "closed"
- [ ] Session data preserved (not deleted)
- [ ] Cannot send messages to closed session

---

### Step 10: Verify Closed Session
**Action**:
- Get session details again

**Expected**:
- [ ] Status: "closed"
- [ ] All messages still accessible
- [ ] Timestamps preserved

**Verify**:
- [ ] Closing is soft-delete (archival)
- [ ] Historical data preserved for audit

---

## Test: Session Access Control

### Step 11: Test User Can Only See Own Sessions
**Action**:
- Sessions are user-scoped
- User A cannot see User B's sessions

**Expected**:
- [ ] Sessions filtered by user ID
- [ ] Admin can see all sessions (if implemented)
- [ ] No cross-user session leakage

**Verify**:
- [ ] API enforces user ownership
- [ ] 403 returned for unauthorized access

---

## Critical Validations

### Database Persistence
**Validation**: Sessions stored in SQLite

```bash
sqlite3 ~/trinity-data/trinity.db "SELECT id, agent_name, status, message_count FROM chat_sessions LIMIT 5"
```

### Message Integrity
**Validation**: All messages preserved

```bash
sqlite3 ~/trinity-data/trinity.db "SELECT id, role, content FROM chat_messages WHERE session_id='{session_id}' LIMIT 10"
```

---

## Success Criteria

Phase 21 is **PASSED** when:
- [ ] Sessions created automatically on first message
- [ ] Session lists show all user's sessions
- [ ] Session details include all messages
- [ ] Message metadata (cost, context) tracked
- [ ] Sessions survive page refresh
- [ ] Sessions survive agent restart
- [ ] New session resets context
- [ ] Old sessions preserved when new created
- [ ] Sessions can be closed (archived)
- [ ] Closed sessions remain readable
- [ ] User isolation enforced

---

## Troubleshooting

**Sessions not persisting**:
- Check database file exists
- Verify bind mount for trinity.db
- Check backend logs for database errors

**Message count incorrect**:
- Messages counted as user + assistant pairs
- Check for duplicate message saves
- Verify message insertion logic

**Session cost not updating**:
- Cost only tracked for assistant messages
- Check Claude Code returns cost in response
- Verify cost extraction in backend

**Cannot close session**:
- Check endpoint exists
- Verify session ID is correct
- Check user owns the session

**Cross-user leakage**:
- Critical security issue
- Check user_id filtering in queries
- Review access control logic

---

## UI Notes

**Note**: As of 2026-01-14, Session Management is **backend API only**.
Frontend UI for session listing/viewing is not yet implemented.

Testing should use:
- API calls (curl or browser DevTools)
- Terminal tab for sending messages
- Database queries for verification

Future phases may add frontend UI.

---

## Next Phase

Once Phase 21 is **PASSED**, proceed to:
- **Phase 22**: Logs & Telemetry

---

**Status**: Ready for Testing (API Only)
**Last Updated**: 2026-01-14
**User Stories**: EXEC-018, EXEC-019, EXEC-020, EXEC-021
