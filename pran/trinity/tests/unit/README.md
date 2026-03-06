# Unit Tests for Credential Sanitizers

This directory contains unit tests for the credential sanitization security fix that prevents credential leakage in Trinity.

## Test Files

### `test_credential_sanitizer_agent.py` (56 tests)
Tests the agent-side credential sanitizer that runs inside agent containers.

**Module Under Test:** `docker/base-image/agent_server/utils/credential_sanitizer.py`

**Coverage:**
- Pattern detection for OpenAI, Anthropic, GitHub, Slack, AWS, Trinity MCP keys
- Bearer and Basic auth token detection
- Key=value pair redaction (ANTHROPIC_API_KEY=value)
- Nested dictionary and list sanitization
- JSON string sanitization
- Execution log and subprocess output sanitization
- Credential value caching from environment
- Edge cases (empty, None, unicode, long strings)

### `test_credential_sanitizer_backend.py` (59 tests)
Tests the backend-side credential sanitizer (defense-in-depth layer).

**Module Under Test:** `src/backend/utils/credential_sanitizer.py`

**Coverage:**
- All pattern detection (same as agent-side)
- Key=value pair redaction
- Nested structure sanitization
- JSON string sanitization
- Execution log sanitization (JSON strings)
- Agent response sanitization
- Backend-specific behavior (pattern-based only, no env lookup)
- Defense-in-depth pattern coverage

## Running Tests

### Run All Unit Tests
```bash
cd /Users/eugene/Dropbox/trinity/trinity/tests/unit
source ../.venv/bin/activate
python -m pytest -v
```

### Run Specific Test File
```bash
# Agent-side sanitizer
python -m pytest test_credential_sanitizer_agent.py -v

# Backend-side sanitizer
python -m pytest test_credential_sanitizer_backend.py -v
```

### Run Specific Test
```bash
python -m pytest test_credential_sanitizer_agent.py::TestPatternDetection::test_openai_api_key_pattern -v
```

## Test Results

**Agent-side:** 56/56 tests passing (100%)
**Backend-side:** 59/59 tests passing (100%)
**Total:** 115/115 tests passing (100%)

## Test Patterns

Tests use realistic credential lengths matching actual API key formats:

| Type | Pattern | Min Length | Example |
|------|---------|------------|---------|
| OpenAI | `sk-...` | 20+ chars after prefix | `sk-1234567890abcdefghij1234567890` |
| OpenAI Project | `sk-proj-...` | 20+ chars | `sk-proj-abc123def456ghi789jkl012` |
| Anthropic | `sk-ant-...` | 20+ chars | `sk-ant-api03-1234567890abcdef` |
| GitHub PAT | `ghp_...` | 36+ chars | `ghp_1234567890abcdefghij1234567890abcdef` |
| Slack Bot | `xoxb-...` | Variable with hyphens | `xoxb-1234567890-1234567890123-abc...` |
| AWS | `AKIA...` | 16 chars | `AKIAIOSFODNN7EXAMPLE` |
| Trinity MCP | `trinity_mcp_...` | 16+ chars | `trinity_mcp_1234567890abcdef` |

## Architecture

These tests run in isolation without requiring the Trinity backend or database:

- Located in `tests/unit/` directory with own `conftest.py`
- `pytest.ini` prevents parent conftest interference
- Direct module imports using `sys.path`
- No API fixtures required
- Fast execution (~0.5s each suite)

## Test Categories

### Pattern Detection (15 tests per suite)
Validates that credential patterns are detected and redacted regardless of context.

### Key=Value Pairs (8 tests per suite)
Tests redaction of sensitive key=value pairs where the key name matches sensitive patterns.

### Nested Structures (9 tests per suite)
Tests recursive sanitization of dictionaries, lists, and mixed nested structures.

### JSON Sanitization (5 tests per suite)
Tests sanitization of JSON strings with proper parsing and re-serialization.

### Execution Logs (3-7 tests per suite)
Tests sanitization of Claude Code execution logs and subprocess output.

### Credential Value Cache (4 tests - agent only)
Tests environment variable loading and exact value matching (agent-side feature).

### Edge Cases (9 tests per suite)
Tests handling of empty values, None, unicode, very long strings, special characters.

### Backend-Specific (3 tests - backend only)
Tests backend-specific behavior: pattern-based only (no env lookup), defense-in-depth coverage.

## Security Notes

1. **Pattern-Based Detection:** Both sanitizers use regex patterns to detect known credential formats
2. **Key-Name Matching:** Redacts values in key=value pairs where key matches sensitive patterns
3. **Agent-Side Value Caching:** Agent sanitizer also caches actual credential values from environment
4. **Defense-in-Depth:** Backend provides second layer in case agent-side sanitization is bypassed
5. **REDACTION_PLACEHOLDER:** All redacted values replaced with `***REDACTED***`

## Maintenance

When adding new credential patterns:

1. Add pattern to both sanitizer modules
2. Add test case to both test files
3. Use realistic credential lengths (see table above)
4. Test alphanumeric-only patterns (no underscores in token body)
5. Ensure minimum length requirements are met

## Related Files

- `/Users/eugene/Dropbox/trinity/trinity/docker/base-image/agent_server/utils/credential_sanitizer.py` - Agent-side implementation
- `/Users/eugene/Dropbox/trinity/trinity/src/backend/utils/credential_sanitizer.py` - Backend-side implementation
- `/Users/eugene/Dropbox/trinity/trinity/tests/test_credentials.py` - Integration tests for credential system
