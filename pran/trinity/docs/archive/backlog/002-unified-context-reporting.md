# IMPROVEMENT: Unified Context Reporting Across Runtimes

**Priority:** Medium
**Type:** Enhancement
**Component:** Agent Server / Runtime Adapter
**Created:** 2025-12-28
**Status:** Open
**Depends On:** #001 (Claude Context Window Display Bug)

---

## Summary

Create a unified context reporting interface that provides consistent, accurate context window information regardless of the underlying runtime (Claude Code, Gemini CLI, or future runtimes).

---

## Current State

Each runtime reports context differently:

| Runtime | Field Used | What It Reports | Accuracy |
|---------|------------|-----------------|----------|
| Claude Code | `usage.input_tokens` | Incremental turn tokens | ❌ Misleading |
| Gemini CLI | `stats.input_tokens` | Full context | ✅ Accurate |

This inconsistency means:
- Users can't compare context usage between agents
- The context bar means different things for different agents
- Future runtimes will need ad-hoc handling

---

## Proposed Design

### New Interface in Runtime Adapter

Add to `docker/base-image/agent_server/services/runtime_adapter.py`:

```python
class AgentRuntime(ABC):
    # ... existing methods ...

    @abstractmethod
    def get_context_metrics(self, metadata: ExecutionMetadata) -> ContextMetrics:
        """
        Get standardized context metrics for this runtime.

        Returns:
            ContextMetrics with:
            - total_context_tokens: Full context sent to API
            - conversation_tokens: Just the conversation portion
            - system_tokens: System prompt + tool definitions
            - cached_tokens: Tokens served from cache (if applicable)
            - context_window: Maximum context for this model
            - utilization_percent: Accurate % of window used
        """
        pass
```

### New Data Model

```python
@dataclass
class ContextMetrics:
    total_context_tokens: int      # Full context (what matters for limits)
    conversation_tokens: int       # User + assistant messages only
    system_tokens: int            # System prompt + tools
    cached_tokens: int            # Tokens that were cached
    context_window: int           # Model's max context
    utilization_percent: float    # total / window * 100

    # Optional breakdown
    tool_definition_tokens: int = 0
    instruction_file_tokens: int = 0
```

### Implementation Per Runtime

**Claude Code:**
```python
def get_context_metrics(self, metadata: ExecutionMetadata) -> ContextMetrics:
    # Estimate total from cost if available
    if metadata.cost_usd:
        total = estimate_from_cost(metadata.cost_usd, metadata.output_tokens)
    else:
        # Fallback: assume base + incremental
        total = CLAUDE_BASE_CONTEXT + metadata.input_tokens

    return ContextMetrics(
        total_context_tokens=total,
        conversation_tokens=metadata.input_tokens,
        system_tokens=total - metadata.input_tokens,
        cached_tokens=metadata.cache_read_tokens,
        context_window=metadata.context_window,
        utilization_percent=(total / metadata.context_window) * 100
    )
```

**Gemini CLI:**
```python
def get_context_metrics(self, metadata: ExecutionMetadata) -> ContextMetrics:
    # Gemini reports accurately, use directly
    return ContextMetrics(
        total_context_tokens=metadata.input_tokens,
        conversation_tokens=metadata.input_tokens - GEMINI_BASE_CONTEXT,
        system_tokens=GEMINI_BASE_CONTEXT,
        cached_tokens=metadata.cached_tokens or 0,
        context_window=metadata.context_window,
        utilization_percent=(metadata.input_tokens / metadata.context_window) * 100
    )
```

---

## Files to Modify

1. **`docker/base-image/agent_server/services/runtime_adapter.py`**
   - Add `get_context_metrics()` abstract method
   - Add `ContextMetrics` dataclass

2. **`docker/base-image/agent_server/services/claude_code.py`**
   - Implement `get_context_metrics()` with cost-based estimation

3. **`docker/base-image/agent_server/services/gemini_runtime.py`**
   - Implement `get_context_metrics()` using direct values

4. **`docker/base-image/agent_server/routers/chat.py`**
   - Use new `get_context_metrics()` for responses

5. **`docker/base-image/agent_server/models.py`**
   - Add `ContextMetrics` model

6. **`src/frontend/src/views/AgentDetail.vue`**
   - Update to display additional context breakdown (optional)

---

## API Changes

### Updated Session Endpoint Response

```json
{
  "session_started": true,
  "message_count": 6,
  "total_cost_usd": 0.1111,
  "context": {
    "total_tokens": 18500,
    "conversation_tokens": 730,
    "system_tokens": 17770,
    "cached_tokens": 15000,
    "context_window": 200000,
    "utilization_percent": 9.25
  },
  "model": "claude-sonnet-4-20250514"
}
```

---

## Benefits

1. **Consistent UX** - Context bar means the same thing for all agents
2. **Accurate planning** - Users know when they're approaching limits
3. **Better debugging** - See where context is being consumed
4. **Future-proof** - New runtimes just implement the interface

---

## Acceptance Criteria

- [ ] `ContextMetrics` provides consistent data across runtimes
- [ ] UI context bar reflects `total_context_tokens` (not incremental)
- [ ] Session endpoint returns detailed context breakdown
- [ ] Existing functionality unchanged (backward compatible)
- [ ] Documentation updated

---

## Out of Scope

- Automatic context management/pruning (separate feature)
- Context optimization suggestions (separate feature)
- Historical context tracking (separate feature)

