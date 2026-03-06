# Security Bug: Environment Variable Exposure via Agent Tools

**Severity**: High
**Status**: FIXED
**Created**: 2026-02-13
**Fixed**: 2026-02-16
**Affected Components**: Agent Execution, Logging, Database Persistence

## Description

Sensitive environment variables (including `TRINITY_MCP_API_KEY`, `OPENAI_API_KEY`, and custom credentials from `.env`) were being exposed in the `execution_log` stored in the database.

There were two exposure vectors:
1.  **Command Leak**: Agent executes `env` or `printenv` via Bash, dumping all secrets to stdout.
2.  **Direct Retrieval**: User asks "What is my API key?", and the agent reads the environment and outputs the secret in the conversation response.

In both cases, the secret was:
1.  Returned to the LLM (leaking secrets to the model provider).
2.  Persisted in the `execution_log` or `response` columns in the database (permanent internal leak).
3.  Displayed in the UI history.

## Evidence

**Verified on Production (2026-02-15):**
1.  **Vector 1 (env dump)**: Running "Check environment variables" resulted in a full dump of `.env` including `TRINITY_MCP_API_KEY`.
2.  **Vector 2 (Direct Ask)**: Execution showed the agent successfully retrieving and displaying API tokens upon request.

Example leaked pattern (BEFORE FIX):
```text
TRINITY_MCP_API_KEY=trinity_mcp_...
TRINITY_MCP_URL=http://mcp-server:8080/mcp
OPENAI_API_KEY=sk-...
```

## Impact

- **Credential Leak**: All agent credentials (API keys, tokens, secrets) are exposed to anyone with access to execution logs.
- **Model Exposure**: Keys are sent to the LLM provider as part of conversation history.
- **Persistent Risk**: Secrets remain in the database history even after rotation, unless logs are scrubbed.

## Reproduction Steps

### Vector 1: Command Leak
1.  **Start an Agent**: Run any agent.
2.  **Execute Command**: Instruct the agent to run a command that prints environment variables.
    *   Example: "Run `env`."
3.  **Check Result**: Secrets are visible in the tool output and database logs.

### Vector 2: Direct Retrieval
1.  **Ask Agent**: "What is my [CREDENTIAL_NAME]?" (e.g., "What is my Fibery token?").
2.  **Check Result**: Agent outputs the raw secret in the chat response.

## Fix Implementation

The fix implements credential sanitization at multiple layers:

### Agent-Side Sanitization (Primary)

**File: `docker/base-image/agent_server/utils/credential_sanitizer.py`**
- New utility module that sanitizes credentials from text, dicts, lists, and JSON
- Loads credential values from environment and `.env` file
- Matches known secret patterns (API keys, tokens, etc.)
- Replaces sensitive values with `***REDACTED***`

**File: `docker/base-image/agent_server/services/claude_code.py`**
- Sanitizes subprocess stdout/stderr output before storing in `raw_messages`
- Sanitizes response text before returning
- Applied to both chat mode and headless task execution

**File: `docker/base-image/agent_server/routers/credentials.py`**
- Refreshes credential sanitizer cache after credentials are injected/updated

### Backend-Side Sanitization (Defense-in-Depth)

**File: `src/backend/utils/credential_sanitizer.py`**
- Backend sanitization layer for catching any missed credentials
- Pattern-based detection (doesn't require knowledge of actual values)

**File: `src/backend/routers/chat.py`**
- Sanitizes `execution_log`, `tool_calls`, and `response` before database persistence
- Applied to all endpoints: `/chat`, `/task`, background task execution

## Patterns Detected and Redacted

- OpenAI keys: `sk-*`, `sk-proj-*`
- Anthropic keys: `sk-ant-*`
- GitHub tokens: `ghp_*`, `gho_*`, `ghs_*`, `ghr_*`, `github_pat_*`
- Slack tokens: `xoxb-*`, `xoxp-*`, `xoxa-*`
- AWS keys: `AKIA*`
- Trinity MCP keys: `trinity_mcp_*`
- Bearer/Basic auth headers
- Key=value pairs with sensitive key names

## QA Checklist & Verification

Use this checklist to verify the fix:

- [ ] **Vector 1 (env)**: Run "Run `env`".
  - [ ] Verify `TRINITY_MCP_API_KEY` is redacted in the logs (`***REDACTED***`).
- [ ] **Vector 2 (ask)**: Ask "What is my TRINITY_MCP_API_KEY?".
  - [ ] Verify the agent either refuses or the output is redacted in the logs/UI.
- [ ] **Database Check**: `SELECT execution_log FROM schedule_executions...` should not contain raw secrets.
- [ ] **Regression**: Ensure normal agent operations (which use these env vars internally) still work.

## Files Changed

1. `docker/base-image/agent_server/utils/credential_sanitizer.py` (NEW)
2. `docker/base-image/agent_server/utils/__init__.py` (MODIFIED)
3. `docker/base-image/agent_server/services/claude_code.py` (MODIFIED)
4. `docker/base-image/agent_server/routers/credentials.py` (MODIFIED)
5. `src/backend/utils/credential_sanitizer.py` (NEW)
6. `src/backend/utils/__init__.py` (MODIFIED)
7. `src/backend/routers/chat.py` (MODIFIED)
