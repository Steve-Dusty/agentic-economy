# BUG: Claude Agent Context Window Display Shows Incorrect Values

**Priority:** High
**Type:** Bug Fix
**Component:** Agent Server / Claude Code Runtime
**Created:** 2025-12-28
**Status:** Open

---

## Summary

The context window usage displayed in the UI for Claude Code agents is **significantly understated** (showing ~0.4% when actual usage is ~10-15%). This gives users a false sense of available context and can lead to unexpected context exhaustion.

---

## Problem Description

### What Users See

| Agent Type | Displayed Context | Actual Context (estimated) | Error |
|------------|-------------------|---------------------------|-------|
| Claude Code | 730 / 200K (0.4%) | ~15-20K / 200K (~10%) | **~20-30x understated** |
| Gemini CLI | 21K / 1M (2.1%) | 21K / 1M (2.1%) | Accurate ✓ |

### Evidence

From testing session on 2025-12-28:

**Claude agent (test-claude):**
- UI shows: 730 tokens for 6 messages
- Session cost: $0.1111
- If only 730 tokens were used, cost would be ~$0.002

**Gemini agent (test):**
- UI shows: 21K tokens for 2 messages
- Session cost: $0.0126
- Cost aligns with reported token usage ✓

The **cost proves** Claude is using much more than 730 tokens - the displayed number is just incremental conversation tokens, not full context.

---

## Root Cause Analysis

### Claude Code CLI Output

Claude Code's `stream-json` output provides:

```json
{
  "type": "result",
  "usage": {
    "input_tokens": 730,        // ← Incremental tokens THIS TURN only
    "output_tokens": 150,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0
  },
  "modelUsage": {
    "claude-sonnet-4-20250514": {
      "inputTokens": 730,       // ← Sometimes cumulative, inconsistent
      "outputTokens": 150,
      "contextWindow": 200000
    }
  },
  "total_cost_usd": 0.044
}
```

**The issue:** `usage.input_tokens` reports only the NEW tokens added in this turn, NOT the full context sent to the API.

### Gemini CLI Output

```json
{
  "type": "result",
  "stats": {
    "input_tokens": 10485,      // ← Full context including system/tools
    "output_tokens": 8,
    "cached": 9833,
    "total_tokens": 10516
  }
}
```

**Gemini correctly reports** the full context window usage.

---

## Files to Investigate/Modify

### Primary File
- `docker/base-image/agent_server/services/claude_code.py`
  - Lines 141-159: Token extraction from `result` message
  - The `input_tokens` value is used directly without adjustment

### Related Files
- `docker/base-image/agent_server/state.py` - Stores `session_context_tokens`
- `docker/base-image/agent_server/routers/chat.py` - Uses metadata for response
- `src/frontend/src/views/AgentDetail.vue` - Displays context bar

---

## Proposed Solutions

### Option A: Estimate from Cost (Recommended)

Back-calculate actual tokens from the reported cost:

```python
# Claude Sonnet pricing (approximate)
INPUT_COST_PER_TOKEN = 3.0 / 1_000_000  # $3 per 1M tokens
OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000  # $15 per 1M tokens

def estimate_input_tokens_from_cost(total_cost, output_tokens):
    output_cost = output_tokens * OUTPUT_COST_PER_TOKEN
    input_cost = total_cost - output_cost
    return int(input_cost / INPUT_COST_PER_TOKEN)
```

**Pros:** Accurate reflection of API usage
**Cons:** Requires pricing lookup, may drift if pricing changes

### Option B: Track Cumulative Tokens

Sum all `input_tokens` across the session to approximate context growth:

```python
# In agent_state
session_cumulative_input_tokens = 0

# After each message
session_cumulative_input_tokens += metadata.input_tokens
```

**Pros:** Simple implementation
**Cons:** Still won't capture system prompt/tool definitions (~10K tokens)

### Option C: Add Base Context Constant

Add a known base context amount for Claude Code:

```python
CLAUDE_BASE_CONTEXT = 12000  # System prompt + tool definitions

actual_context = CLAUDE_BASE_CONTEXT + reported_input_tokens
```

**Pros:** Simple
**Cons:** Base context may vary by configuration

### Option D: Hybrid Approach (Best)

Combine cost estimation with cumulative tracking:

```python
def get_actual_context_tokens(metadata, session_state):
    # If we have cost data, estimate from that (most accurate)
    if metadata.cost_usd and metadata.output_tokens:
        return estimate_input_tokens_from_cost(
            metadata.cost_usd,
            metadata.output_tokens
        )

    # Fallback to cumulative + base estimate
    return CLAUDE_BASE_CONTEXT + session_state.cumulative_input_tokens
```

---

## Acceptance Criteria

- [ ] Claude agent context window percentage reflects actual API context usage
- [ ] Context bar in UI shows meaningful progress toward 200K limit
- [ ] Cost and context usage are consistent (higher context = higher cost)
- [ ] Users can trust the context % to know when they're approaching limits
- [ ] No regression in Gemini context reporting (already accurate)

---

## Testing Plan

1. Create a fresh Claude agent
2. Send "hi" message
3. Verify context shows ~10-15K (not 100-200 tokens)
4. Send 10 more messages
5. Verify context grows appropriately
6. Compare context growth with cost growth (should correlate)
7. Verify Gemini still reports correctly

---

## Related Context

### Session Data Endpoint
```
GET /api/chat/session
```
Returns:
```json
{
  "context_tokens": 730,      // ← This is wrong for Claude
  "context_window": 200000,
  "context_percent": 0.4      // ← Derived from above, also wrong
}
```

### How Gemini Gets It Right

In `gemini_runtime.py`, the `stats.input_tokens` field is used directly:
```python
stats = msg.get("stats", {})
if stats:
    metadata.input_tokens = stats.get("input_tokens", 0)
```

Gemini CLI reports full context, so this works correctly.

---

## References

- Claude Code CLI: https://github.com/anthropics/claude-code
- Anthropic API pricing: https://www.anthropic.com/pricing
- Related file: `docker/base-image/agent_server/services/claude_code.py`
- Related file: `docker/base-image/agent_server/services/gemini_runtime.py` (for comparison)

