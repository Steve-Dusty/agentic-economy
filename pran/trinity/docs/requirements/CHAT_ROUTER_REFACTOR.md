# Chat Router Refactoring Requirements

**Document ID**: REFACTOR-001
**Created**: 2026-02-24
**Status**: Draft
**Priority**: Critical (P0)

---

## Executive Summary

Refactor `src/backend/routers/chat.py` (1533 lines) into modular components while preserving all 17 API endpoints and zero regression risk. The current file exceeds AI maintainability thresholds with two functions over 300 lines each.

### Metrics Before Refactoring
| Metric | Current | Target |
|--------|---------|--------|
| File size | 1533 lines | <400 lines per module |
| Largest function | 364 lines (`execute_parallel_task`) | <100 lines |
| Second largest | 325 lines (`chat_with_agent`) | <100 lines |
| Total endpoints | 17 | 17 (unchanged) |

---

## Scope

### In Scope
- Split `routers/chat.py` into logical modules
- Extract shared utilities
- Preserve all API endpoint paths and signatures
- Maintain all integration points (activity tracking, execution queue, WebSocket)

### Out of Scope
- Database schema changes
- Frontend changes
- New feature additions
- Performance optimizations beyond modularization

---

## API Endpoints to Preserve

All 17 endpoints must retain identical path, method, parameters, and response format.

### Chat Endpoints (Queue-Based)
| Method | Path | Function | Current Lines |
|--------|------|----------|---------------|
| POST | `/api/agents/{name}/chat` | `chat_with_agent()` | 108-431 |

### Task Execution Endpoints (Stateless)
| Method | Path | Function | Current Lines |
|--------|------|----------|---------------|
| POST | `/api/agents/{name}/task` | `execute_parallel_task()` | 546-906 |
| POST | `/api/agents/{name}/task/streaming` | `execute_task_streaming()` | 909-1015 |

### Chat Session/History Endpoints
| Method | Path | Function | Current Lines |
|--------|------|----------|---------------|
| GET | `/api/agents/{name}/chat/sessions` | `get_chat_sessions()` | 1018-1048 |
| GET | `/api/agents/{name}/chat/sessions/{session_id}` | `get_session_messages()` | 1051-1091 |
| POST | `/api/agents/{name}/chat/sessions` | `create_chat_session()` | 1094-1127 |
| DELETE | `/api/agents/{name}/chat/sessions/{session_id}` | `delete_chat_session()` | 1130-1167 |
| DELETE | `/api/agents/{name}/chat/messages/{message_id}` | `delete_chat_message()` | 1170-1222 |

### Activity Monitoring Endpoints
| Method | Path | Function | Current Lines |
|--------|------|----------|---------------|
| GET | `/api/agents/{name}/chat/activity` | `get_chat_activity()` | 1225-1277 |
| GET | `/api/agents/{name}/chat/current` | `get_current_activity()` | 1280-1349 |

### Model Configuration Endpoints
| Method | Path | Function | Current Lines |
|--------|------|----------|---------------|
| GET | `/api/agents/{name}/models` | `get_agent_models()` | 1352-1389 |
| POST | `/api/agents/{name}/models/test` | `test_agent_model()` | 1392-1466 |

### Execution Control Endpoints
| Method | Path | Function | Current Lines |
|--------|------|----------|---------------|
| POST | `/api/agents/{name}/executions/{execution_id}/terminate` | `terminate_execution()` | 1469-1513 |
| POST | `/api/agents/{name}/task/{execution_id}/terminate` | `terminate_task_execution()` | 1516-1599 |

### Live Streaming Endpoints
| Method | Path | Function | Current Lines |
|--------|------|----------|---------------|
| GET | `/api/agents/{name}/live/{execution_id}` | `stream_live_execution()` | 1602-1656 |
| POST | `/api/agents/{name}/live/{execution_id}/input` | `send_live_input()` | 1659-1710 |

---

## Proposed Module Structure

### Target Directory Layout
```
src/backend/routers/
├── chat/
│   ├── __init__.py          # Router aggregation, exports single `router`
│   ├── queue_chat.py        # Queue-based chat endpoint (1 endpoint)
│   ├── task_execution.py    # Stateless task execution (2 endpoints)
│   ├── sessions.py          # Session/history management (5 endpoints)
│   ├── activity.py          # Activity monitoring (2 endpoints)
│   ├── models.py            # Model configuration (2 endpoints)
│   ├── termination.py       # Execution control (2 endpoints)
│   ├── streaming.py         # Live execution streaming (2 endpoints)
│   └── utils.py             # Shared utilities
└── chat.py                  # DEPRECATED: Re-exports router for backwards compat
```

### Module Responsibilities

#### 1. `chat/__init__.py` (~30 lines)
- Import all sub-routers
- Create aggregate router with prefix `/api/agents/{name}`
- Export single `router` for `main.py` compatibility

#### 2. `chat/queue_chat.py` (~200 lines)
**Endpoints**: `POST /chat`
**Responsibilities**:
- Execution queue integration (Redis SET NX EX)
- Activity tracking (track_activity, complete_activity)
- Agent collaboration headers (X-Source-Agent, X-Via-MCP)
- Session persistence (save_to_session)
- Credential sanitization

**Extracted from**: Lines 108-431 (`chat_with_agent`)

#### 3. `chat/task_execution.py` (~350 lines)
**Endpoints**: `POST /task`, `POST /task/streaming`
**Responsibilities**:
- Stateless parallel execution (no queue)
- Async mode (fire-and-forget with background handler)
- Resume session support (claude_session_id, --resume)
- Schedule execution tracking
- Tool call parsing and storage

**Extracted from**: Lines 546-1015 (`execute_parallel_task`, `_execute_task_background`, `execute_task_streaming`)

#### 4. `chat/sessions.py` (~180 lines)
**Endpoints**: 5 session management endpoints
**Responsibilities**:
- CRUD operations for chat_sessions table
- Message retrieval and deletion
- Session context building

**Extracted from**: Lines 1018-1222

#### 5. `chat/activity.py` (~130 lines)
**Endpoints**: `GET /chat/activity`, `GET /chat/current`
**Responsibilities**:
- Activity service integration
- In-progress execution tracking
- Activity history queries

**Extracted from**: Lines 1225-1349

#### 6. `chat/models.py` (~120 lines)
**Endpoints**: `GET /models`, `POST /models/test`
**Responsibilities**:
- Agent model configuration
- Model availability testing

**Extracted from**: Lines 1352-1466

#### 7. `chat/termination.py` (~150 lines)
**Endpoints**: `POST /executions/{id}/terminate`, `POST /task/{id}/terminate`
**Responsibilities**:
- Execution cancellation
- PTY process termination
- Activity cancellation tracking

**Extracted from**: Lines 1469-1599

#### 8. `chat/streaming.py` (~120 lines)
**Endpoints**: `GET /live/{id}`, `POST /live/{id}/input`
**Responsibilities**:
- SSE proxy from agent container
- Live input forwarding

**Extracted from**: Lines 1602-1710

#### 9. `chat/utils.py` (~100 lines)
**Shared utilities**:
- `get_agent_http_client()` - httpx client factory
- `broadcast_agent_status()` - WebSocket status updates
- `sanitize_execution_log()` - Credential sanitization
- `sanitize_response()` - Response sanitization
- Common error handling patterns

**Extracted from**: Lines 26-104

---

## Function Decomposition

### `chat_with_agent()` (325 lines → 4 functions ~80 lines each)

| New Function | Responsibility | Lines |
|--------------|----------------|-------|
| `_acquire_execution_slot()` | Queue acquisition, lock management | ~40 |
| `_prepare_chat_context()` | Session lookup, message history, context building | ~60 |
| `_execute_agent_chat()` | HTTP call to agent, response parsing | ~80 |
| `_persist_chat_result()` | Save messages, activity tracking, cleanup | ~80 |

**Orchestration**: `chat_with_agent()` becomes ~60 line orchestrator calling these functions in sequence with proper error handling.

### `execute_parallel_task()` (364 lines → 5 functions ~70 lines each)

| New Function | Responsibility | Lines |
|--------------|----------------|-------|
| `_build_task_payload()` | Request validation, payload construction | ~40 |
| `_execute_headless_task()` | HTTP call to agent /api/task | ~60 |
| `_parse_task_response()` | Response parsing, tool call extraction | ~60 |
| `_persist_task_execution()` | Database updates, session storage | ~80 |
| `_handle_async_completion()` | Async mode background handling | ~60 |

**Orchestration**: `execute_parallel_task()` becomes ~50 line orchestrator.

### `_execute_task_background()` (109 lines → 2 functions)

| New Function | Responsibility | Lines |
|--------------|----------------|-------|
| `_background_task_worker()` | Async task execution loop | ~60 |
| `_complete_background_task()` | Result persistence, cleanup | ~40 |

---

## Integration Points

### Must Preserve Exactly

#### 1. Execution Queue (Redis)
**Pattern**: `SET NX EX` for atomic lock acquisition
**Location**: `queue_chat.py`
**Key**: `execution_queue:{agent_name}`
**TTL**: Configurable (default 300s)

```python
# Must maintain this pattern exactly
acquired = await redis.set(
    f"execution_queue:{agent_name}",
    execution_id,
    ex=timeout_seconds,
    nx=True
)
# ... execute ...
# Always release in finally block
await redis.delete(f"execution_queue:{agent_name}")
```

#### 2. Activity Tracking
**Service**: `activity_service` (singleton)
**Start**: `track_activity()` with CHAT_START or SCHEDULE_START
**End**: `complete_activity()` with status and details
**Error**: `complete_activity(status="failed", error=...)`

```python
# Parent activity for chat
activity_id = await activity_service.track_activity(
    agent_name=name,
    activity_type=ActivityType.CHAT_START,
    user_id=current_user.id,
    triggered_by="user",  # or "agent", "mcp", "schedule"
    ...
)
# Child activities for tool calls
for tool in tool_calls:
    await activity_service.track_activity(
        parent_activity_id=activity_id,
        activity_type=ActivityType.TOOL_CALL,
        ...
    )
# Completion
await activity_service.complete_activity(activity_id, status="completed", details={...})
```

#### 3. Agent Collaboration Headers
**Header**: `X-Source-Agent` - Identifies calling agent
**Header**: `X-Via-MCP` - Identifies MCP-proxied requests
**Tracking**: Creates AGENT_COLLABORATION activity

```python
x_source_agent = request.headers.get("X-Source-Agent")
x_via_mcp = request.headers.get("X-Via-MCP")
triggered_by = "agent" if x_source_agent else ("mcp" if x_via_mcp else "user")
```

#### 4. Session Persistence
**Tables**: `chat_sessions`, `chat_messages`
**Parameter**: `save_to_session` (default True)
**Parameter**: `session_id` (optional, creates new if not provided)
**Context**: Last 20 messages for context building

#### 5. Resume Execution (EXEC-023)
**Parameter**: `resume_session_id` - Claude Code session to resume
**Storage**: `claude_session_id` in `schedule_executions` table
**Flag**: `--resume {session_id}` passed to Claude Code

#### 6. Credential Sanitization
**Functions**: `sanitize_execution_log()`, `sanitize_response()`
**Purpose**: Remove credential values from logs and responses
**Pattern**: Uses regex patterns from credential store

#### 7. WebSocket Broadcasting
**Manager**: `websocket_manager` (singleton)
**Events**: `agent_activity`, execution status updates
**Filtered**: `filtered_websocket_manager` for Trinity Connect

---

## Migration Strategy

### Phase 1: Create Module Structure (No Breaking Changes)
1. Create `routers/chat/` directory
2. Create `utils.py` with extracted utilities
3. Create empty module files with imports

### Phase 2: Extract Session Management
1. Move session endpoints to `sessions.py`
2. Update imports in original `chat.py`
3. Verify all tests pass

### Phase 3: Extract Activity & Models
1. Move activity endpoints to `activity.py`
2. Move model endpoints to `models.py`
3. Verify all tests pass

### Phase 4: Extract Termination & Streaming
1. Move termination endpoints to `termination.py`
2. Move streaming endpoints to `streaming.py`
3. Verify all tests pass

### Phase 5: Extract Task Execution (Critical)
1. Decompose `execute_parallel_task()` into helper functions
2. Move to `task_execution.py`
3. Run comprehensive integration tests
4. Verify async mode works correctly

### Phase 6: Extract Queue Chat (Critical)
1. Decompose `chat_with_agent()` into helper functions
2. Move to `queue_chat.py`
3. Run comprehensive integration tests
4. Verify queue behavior with concurrent requests

### Phase 7: Router Aggregation
1. Create `__init__.py` with router aggregation
2. Update `chat.py` to re-export for backwards compatibility
3. Update `main.py` import if needed
4. Verify all endpoints work

### Phase 8: Cleanup
1. Remove deprecated code paths
2. Update documentation
3. Final verification

---

## Testing Requirements

### Pre-Refactoring Test Coverage

Before any changes, ensure test coverage for:

1. **Chat endpoint**: Queue behavior, concurrent requests, activity tracking
2. **Task endpoint**: Async mode, resume mode, tool call parsing
3. **Session endpoints**: CRUD operations, message retrieval
4. **Termination**: Process killing, activity cancellation
5. **Streaming**: SSE proxy, live input forwarding

### Test Files to Create/Update

| Test File | Coverage |
|-----------|----------|
| `tests/routers/test_chat_queue.py` | Queue-based chat endpoint |
| `tests/routers/test_task_execution.py` | Stateless task execution |
| `tests/routers/test_chat_sessions.py` | Session management |
| `tests/routers/test_chat_activity.py` | Activity monitoring |
| `tests/routers/test_chat_models.py` | Model configuration |
| `tests/routers/test_chat_termination.py` | Execution control |
| `tests/routers/test_chat_streaming.py` | Live streaming |

### Regression Test Checklist

For each phase, verify:
- [ ] All 17 endpoints respond correctly
- [ ] HTTP status codes unchanged
- [ ] Response schemas unchanged
- [ ] Queue behavior works for concurrent requests
- [ ] Activity tracking creates correct records
- [ ] WebSocket events broadcast correctly
- [ ] Credential sanitization applied
- [ ] Resume mode works (EXEC-023)
- [ ] Async mode completes background tasks
- [ ] Error handling produces correct status codes

---

## Backwards Compatibility

### Import Compatibility
```python
# Old import (must continue to work)
from routers.chat import router

# Implementation in routers/chat.py
from routers.chat import router  # Re-export from package
```

### API Compatibility
- All endpoint paths unchanged
- All request/response schemas unchanged
- All headers handled identically
- All error responses identical

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Activity tracking breaks | Medium | High | Comprehensive integration tests before each phase |
| Queue race conditions | Medium | High | Test concurrent requests, verify Redis patterns |
| Async mode fails | Low | High | Test fire-and-forget with background completion |
| Resume mode breaks | Low | Medium | Test EXEC-023 flow end-to-end |
| Import errors | Low | Low | Gradual migration with re-exports |

---

## Success Criteria

1. **Zero API changes**: All 17 endpoints work identically
2. **Size targets met**: No module exceeds 400 lines
3. **Function targets met**: No function exceeds 100 lines
4. **All tests pass**: 100% of existing tests pass
5. **No regression**: Manual verification of critical flows

---

## Dependencies

### Required Before Starting
- [ ] Feature flow documentation reviewed (completed)
- [ ] Test coverage baseline established
- [ ] Development environment with Redis running

### External Dependencies
- No external dependencies affected
- No frontend changes required
- No database migrations required

---

## Timeline Estimate

| Phase | Effort |
|-------|--------|
| Phase 1: Module structure | Small |
| Phase 2-4: Simple extractions | Medium |
| Phase 5: Task execution | Large (critical path) |
| Phase 6: Queue chat | Large (critical path) |
| Phase 7-8: Aggregation & cleanup | Small |

---

## Appendix: Current File Structure

### Lines 1-105: Imports and Utilities
```
1-25: Imports
26-78: get_agent_http_client(), agent HTTP client factory
83-104: broadcast_agent_status(), WebSocket utility
```

### Lines 106-431: Queue-Based Chat
```
108-431: chat_with_agent() - 325 lines
  - Lines 150-180: Activity tracking start
  - Lines 185-230: Queue acquisition
  - Lines 235-280: Context building
  - Lines 285-350: Agent HTTP call
  - Lines 355-410: Response parsing, persistence
  - Lines 415-430: Cleanup, queue release
```

### Lines 433-906: Parallel Task Execution
```
433-543: _execute_task_background() - 109 lines (async mode helper)
546-906: execute_parallel_task() - 364 lines
  - Lines 570-620: Request validation
  - Lines 625-700: Agent HTTP call
  - Lines 705-780: Response parsing
  - Lines 785-860: Database persistence
  - Lines 865-900: Activity tracking, cleanup
```

### Lines 909-1015: Streaming Task
```
909-1015: execute_task_streaming() - SSE streaming variant
```

### Lines 1018-1222: Session Management
```
1018-1048: get_chat_sessions()
1051-1091: get_session_messages()
1094-1127: create_chat_session()
1130-1167: delete_chat_session()
1170-1222: delete_chat_message()
```

### Lines 1225-1349: Activity Monitoring
```
1225-1277: get_chat_activity()
1280-1349: get_current_activity()
```

### Lines 1352-1466: Model Configuration
```
1352-1389: get_agent_models()
1392-1466: test_agent_model()
```

### Lines 1469-1599: Execution Control
```
1469-1513: terminate_execution()
1516-1599: terminate_task_execution()
```

### Lines 1602-1710: Live Streaming
```
1602-1656: stream_live_execution()
1659-1710: send_live_input()
```

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-02-24 | Claude | Initial draft |
