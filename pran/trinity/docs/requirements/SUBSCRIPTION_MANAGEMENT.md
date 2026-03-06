# Subscription Management (SUB-001)

> **Status**: Pending Implementation
> **Priority**: HIGH
> **Author**: Eugene + Claude
> **Date**: 2026-02-22

---

## Overview

Centralized management of Claude Max/Pro subscriptions in Trinity. Enables assigning OAuth-based subscription credentials to agents instead of API keys, providing control over billing and usage.

## Problem Statement

Currently, agents authenticate via:
1. **API Key** (`ANTHROPIC_API_KEY` in `.env`) - Pay-per-use billing
2. **Subscription** (OAuth via `claude login`) - Included in Claude Max subscription

Issues:
- No centralized view of which agents use which auth method
- Manual per-agent authentication doesn't scale
- Can't share one subscription across multiple agents easily
- No control over which agents bill to which account

## Key Insight

Claude Code stores OAuth credentials in `~/.claude/.credentials.json`:
```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "sk-ant-ort01-...",
    "expiresAt": 1770611688652,
    "subscriptionType": "max",
    "rateLimitTier": "default_claude_max_20x"
  }
}
```

**When both API key and subscription exist, subscription takes precedence.**

Token refresh is handled automatically by Claude Code using the `refreshToken`. Re-authentication is only needed if refresh token is revoked or expires (rare).

---

## Solution: Subscription Registry

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Trinity Subscription Management                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Local Machine (authenticated via `claude login`)                       │
│       │                                                                  │
│       │ MCP: register_subscription("eugene-max", credentials_json)      │
│       ▼                                                                  │
│  ┌─────────────────┐     ┌──────────────────────┐                       │
│  │  Subscription   │     │   Agent Assignment   │                       │
│  │    Registry     │     │                      │                       │
│  │                 │     │  agent-a → sub-1     │                       │
│  │  eugene-max     │────▶│  agent-b → sub-1     │                       │
│  │  ability-max    │     │  agent-c → sub-2     │                       │
│  │                 │     │  agent-d → (none)    │                       │
│  └─────────────────┘     └──────────────────────┘                       │
│           │                        │                                     │
│           │                        ▼                                     │
│           │              ┌─────────────────────┐                        │
│           └─────────────▶│   Credential        │                        │
│                          │   Injection         │                        │
│                          │                     │                        │
│                          │ → ~/.claude/.credentials.json                │
│                          └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Workflow

**1. Authenticate Locally**
```bash
claude login
# Complete OAuth in browser
```

**2. Register Subscription in Trinity (via MCP)**
```
register_subscription(
  name: "eugene-max",
  credentials_json: <contents of ~/.claude/.credentials.json>
)
```

**3. Assign to Agent(s)**
```
assign_subscription(
  agent_name: "ruby-internal",
  subscription_name: "eugene-max"
)
```

**4. Trinity Injects Credentials**
- On agent start: inject `~/.claude/.credentials.json`
- For running agent: hot-inject immediately

**5. Re-authentication (if needed)**
```bash
# Local
claude login
# Re-register with same name (overwrites)
register_subscription("eugene-max", <new credentials>)
```

---

## Data Model

### New Table: `subscription_credentials`

```sql
CREATE TABLE subscription_credentials (
    id TEXT PRIMARY KEY,                  -- UUID
    name TEXT UNIQUE NOT NULL,            -- "eugene-max", "ability-max"
    encrypted_credentials TEXT NOT NULL,  -- AES-256-GCM encrypted JSON
    subscription_type TEXT,               -- "max", "pro", null if unknown
    rate_limit_tier TEXT,                 -- e.g., "default_claude_max_20x"
    owner_id TEXT NOT NULL,               -- User who registered it
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE INDEX idx_subscriptions_name ON subscription_credentials(name);
CREATE INDEX idx_subscriptions_owner ON subscription_credentials(owner_id);
```

### Agent Assignment Column

```sql
ALTER TABLE agent_ownership ADD COLUMN subscription_id TEXT REFERENCES subscription_credentials(id);
-- NULL = use API key from .env
-- non-NULL = use this subscription
```

---

## API Endpoints

### Subscription Registry (Admin Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/subscriptions` | Register new subscription |
| GET | `/api/subscriptions` | List all subscriptions (without secrets) |
| GET | `/api/subscriptions/{id}` | Get subscription details |
| PUT | `/api/subscriptions/{id}` | Update credentials (re-registration) |
| DELETE | `/api/subscriptions/{id}` | Remove subscription |

### Agent Assignment

| Method | Endpoint | Description |
|--------|----------|-------------|
| PUT | `/api/agents/{name}/subscription` | Assign subscription to agent |
| DELETE | `/api/agents/{name}/subscription` | Remove assignment (fall back to API key) |
| GET | `/api/agents/{name}/auth` | Get current auth status |

### Fleet Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ops/auth-report` | All agents with auth mode and subscription info |

---

## MCP Tools

### `register_subscription`

Register or update a subscription in Trinity.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Unique identifier (e.g., "eugene-max") |
| `credentials_json` | string | Yes | Contents of `~/.claude/.credentials.json` |

**Returns:**
```json
{
  "id": "sub_abc123",
  "name": "eugene-max",
  "subscription_type": "max",
  "rate_limit_tier": "default_claude_max_20x",
  "created": true
}
```

**Example:**
```
register_subscription(
  name: "eugene-max",
  credentials_json: '{"claudeAiOauth": {...}}'
)
```

### `assign_subscription`

Assign a subscription to an agent. Injects credentials immediately if agent is running.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_name` | string | Yes | Target agent name |
| `subscription_name` | string | Yes | Subscription to assign (or "none" to clear) |

**Returns:**
```json
{
  "agent_name": "ruby-internal",
  "subscription": "eugene-max",
  "injected": true,
  "previous_auth": "api_key"
}
```

### `list_subscriptions`

List all registered subscriptions.

**Returns:**
```json
{
  "subscriptions": [
    {
      "id": "sub_abc123",
      "name": "eugene-max",
      "subscription_type": "max",
      "rate_limit_tier": "default_claude_max_20x",
      "agent_count": 3,
      "agents": ["ruby-internal", "storypipe", "cornelius-m"]
    }
  ]
}
```

### `get_agent_auth`

Get authentication status for an agent.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `agent_name` | string | Yes | Agent to check |

**Returns:**
```json
{
  "agent_name": "ruby-internal",
  "auth_mode": "subscription",
  "subscription_name": "eugene-max",
  "subscription_type": "max",
  "has_api_key": true,
  "api_key_prefix": "sk-ant-api03-4sN..."
}
```

---

## Injection Logic

### On Agent Start (`lifecycle.py`)

```python
def inject_subscription_credentials(agent_name: str, container):
    """Inject subscription credentials if assigned."""
    subscription_id = db.get_agent_subscription(agent_name)

    if not subscription_id:
        logger.info(f"Agent {agent_name} using API key (no subscription assigned)")
        return

    # Get encrypted credentials from DB
    subscription = db.get_subscription(subscription_id)
    credentials_json = decrypt(subscription.encrypted_credentials)

    # Ensure .claude directory exists
    container.exec_run("mkdir -p /home/developer/.claude")

    # Inject credentials file
    inject_file_to_container(
        container,
        "/home/developer/.claude/.credentials.json",
        credentials_json
    )

    logger.info(f"Injected subscription '{subscription.name}' into {agent_name}")
```

### Hot-Injection for Running Agents

When subscription is assigned to a running agent:
1. Write `.credentials.json` to container
2. No restart needed - Claude Code reads fresh credentials on next API call

### Injection Order (Updated)

Current injection order in `start_agent_internal()`:
1. Trinity meta-prompt injection
2. Credential injection (`.env`, `.mcp.json`)
3. Skill injection
4. **NEW: Subscription injection** (after credentials, before skills)

---

## Auth Detection

Detect which authentication method an agent is actually using.

### Detection Logic

```python
def get_agent_auth_mode(agent_name: str) -> dict:
    """
    Priority: subscription > api_key > not_configured
    """
    result = {
        "auth_mode": "not_configured",
        "has_api_key": False,
        "has_subscription": False,
        "subscription_name": None,
        "subscription_type": None,
        "api_key_prefix": None,
    }

    # Check database assignment first
    subscription_id = db.get_agent_subscription(agent_name)
    if subscription_id:
        subscription = db.get_subscription(subscription_id)
        result["subscription_name"] = subscription.name

    # Check container for actual files
    container = get_container(agent_name)

    # Check API key
    exit_code, output = container.exec_run("printenv ANTHROPIC_API_KEY")
    if exit_code == 0 and output.strip():
        result["has_api_key"] = True
        result["api_key_prefix"] = output.decode().strip()[:20] + "..."

    # Check subscription credentials
    exit_code, output = container.exec_run(
        "cat /home/developer/.claude/.credentials.json"
    )
    if exit_code == 0 and output.strip():
        creds = json.loads(output.decode())
        if "claudeAiOauth" in creds:
            result["has_subscription"] = True
            result["subscription_type"] = creds["claudeAiOauth"].get("subscriptionType")

    # Determine effective mode (subscription wins)
    if result["has_subscription"]:
        result["auth_mode"] = "subscription"
    elif result["has_api_key"]:
        result["auth_mode"] = "api_key"

    return result
```

### Auth States

| API Key | Subscription | Effective Auth |
|---------|--------------|----------------|
| No | No | `not_configured` |
| Yes | No | `api_key` |
| No | Yes | `subscription` |
| Yes | Yes | `subscription` (wins) |

---

## Security Considerations

### Credential Storage
- Credentials encrypted with AES-256-GCM (same as CRED-002)
- Encryption key from `SECRET_KEY` environment variable
- Never log or expose raw credentials

### Access Control
- Only admins can register/delete subscriptions
- Agent owners can assign subscriptions to their agents
- Subscription credentials never returned in API responses

### Token Handling
- `accessToken` and `refreshToken` are sensitive
- Refresh is automatic by Claude Code
- If tokens fail, user re-authenticates locally and re-registers

---

## UI (Optional - Phase 2)

### Settings → Subscriptions Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│ Subscriptions                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ ⭐ eugene-max                                                │  │
│  │    Type: Claude Max  •  Tier: default_claude_max_20x        │  │
│  │    Agents: storypipe, cornelius-m, ruby-public (3)          │  │
│  │                                                    [Delete]  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ ⭐ ability-max                                               │  │
│  │    Type: Claude Max  •  Tier: default_claude_max_20x        │  │
│  │    Agents: trinity-system, dd-orchestrator (2)              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Header Auth Indicator

In AgentHeader.vue, show auth mode:
- 🔑 API Key
- ⭐ Subscription (eugene-max)
- ⚠️ Not Configured

### Fleet Auth Report (Ops)

Dashboard card or `/ops` endpoint showing:
- X agents on Subscription
- Y agents on API Key
- Z agents not configured

---

## Implementation Phases

### Phase 1: Backend Foundation
- [ ] Database migration: `subscription_credentials` table
- [ ] Database migration: `subscription_id` column on `agent_ownership`
- [ ] `db/subscriptions.py`: CRUD operations
- [ ] `routers/subscriptions.py`: REST endpoints
- [ ] Encryption: reuse `CredentialEncryptionService`

### Phase 2: MCP Tools
- [ ] `register_subscription` tool
- [ ] `assign_subscription` tool
- [ ] `list_subscriptions` tool
- [ ] `get_agent_auth` tool

### Phase 3: Injection
- [ ] `subscription_service.py`: injection logic
- [ ] Update `lifecycle.py`: inject on agent start
- [ ] Hot-injection endpoint for running agents

### Phase 4: Auth Detection
- [ ] `GET /api/agents/{name}/auth` endpoint
- [ ] `GET /api/ops/auth-report` fleet endpoint

### Phase 5: UI (Optional)
- [ ] Settings → Subscriptions page
- [ ] Agent header auth indicator
- [ ] Agent detail subscription selector

---

## Rate Limit Considerations

One subscription shared across multiple agents = **shared rate limits**.

Claude Max limits are per-account, not per-agent. When multiple agents use the same subscription:
- They compete for the same rate limit bucket
- High-activity agents may throttle others

**Mitigation:**
- Display agent count per subscription
- Consider warning when assigning to many agents
- For high-throughput needs, use separate subscriptions or API key

---

## Edge Cases

### 1. Subscription Deleted While Assigned
- Remove assignment from all agents
- Agents fall back to API key on next execution

### 2. Agent Stopped
- Can still assign subscription (stored in DB)
- Injection happens on next start

### 3. Container Recreated
- Subscription injected fresh on container creation
- No persistence issues

### 4. Multiple Users with Same Subscription
- Subscriptions are global (not per-user)
- Any admin can manage
- Agent owners can assign to their agents

### 5. Credentials Become Invalid
- Agent falls back to API key
- Error logged
- User re-authenticates and re-registers

---

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `src/backend/db/subscriptions.py` | Database operations |
| `src/backend/routers/subscriptions.py` | REST endpoints |
| `src/backend/services/subscription_service.py` | Injection logic |
| `src/mcp-server/tools/subscriptions.ts` | MCP tools |

### Modified Files
| File | Change |
|------|--------|
| `src/backend/database.py` | Add migration, wrapper methods |
| `src/backend/main.py` | Mount subscriptions router |
| `src/backend/services/agent_service/lifecycle.py` | Add injection call |
| `src/mcp-server/index.ts` | Register subscription tools |

---

## Success Criteria

1. **Subscription Registration**: User can register subscription via MCP from local machine
2. **Agent Assignment**: User can assign subscription to agent via MCP
3. **Automatic Injection**: Agent receives credentials on start
4. **Auth Detection**: Can verify which auth method agent is using
5. **Fleet Visibility**: Can see auth status across all agents
6. **No Manual Per-Agent Auth**: Never need to `claude login` inside agent containers

---

## References

- [Agent Auth Detection Research](/Users/eugene/Dropbox/trinity/trinity-ops-agent/instances/ability-services/RESEARCH-agent-auth-detection.md)
- [CRED-002: Credential System Refactor](CREDENTIAL_SYSTEM_REFACTOR.md)
- [Claude Code Authentication Docs](https://docs.anthropic.com/en/docs/claude-code/cli-usage#authentication)
- [GitHub Issue #1651: API key not used when logged in](https://github.com/anthropics/claude-code/issues/1651)
