# Feature Flow: Nevermined x402 Payment Integration (NVM-001)

> **Status**: Implemented (2026-03-04)
> **Spec**: `docs/requirements/NEVERMINED_PAYMENT_INTEGRATION.md`

## Overview

Per-agent monetization via Nevermined's x402 payment protocol. External callers pay per-request through a `payment-signature` HTTP header. Internal fleet traffic (MCP `chat_with_agent`) bypasses payment entirely.

## Flow: Paid Chat Request

```
External Caller
    |
    POST /api/paid/{agent_name}/chat
    + Header: payment-signature: <access_token>
    |
    ├─ No config/not enabled → 404
    ├─ No payment-signature → 402 Payment Required
    │     (includes plan_id, pricing, endpoint)
    ├─ Invalid token → verify_payment() fails → 403
    │     (log: action=reject)
    └─ Valid token
         ├─ verify_payment() → log: action=verify
         ├─ TaskExecutionService.execute_task(triggered_by="paid")
         ├─ Execution failed → skip settle → return error (no charge)
         └─ Execution success
              ├─ settle_payment() (3 retries, exponential backoff)
              ├─ Settle OK → log: action=settle → return response + receipt
              └─ Settle failed → log: action=settle_failed → return response + warning
```

## Flow: Admin Configuration

```
Admin/Owner
    |
    POST /api/nevermined/agents/{name}/config
    + Body: { nvm_api_key, nvm_environment, nvm_agent_id, nvm_plan_id, credits_per_request }
    |
    ├─ NeverminedOperations.create_or_update_config()
    │     ├─ Encrypt nvm_api_key via CredentialEncryptionService (AES-256-GCM)
    │     └─ Upsert nevermined_agent_config row
    |
    PUT /api/nevermined/agents/{name}/config/toggle?enabled=true
    |
    └─ Agent is now accepting paid requests
```

## Files

### Backend
| File | Purpose |
|------|---------|
| `src/backend/db/nevermined.py` | `NeverminedOperations` — config CRUD + payment log |
| `src/backend/services/nevermined_payment_service.py` | `NeverminedPaymentService` — SDK verify/settle |
| `src/backend/routers/paid.py` | Public paid endpoint (`/api/paid/`) |
| `src/backend/routers/nevermined.py` | Admin config endpoints (`/api/nevermined/`) |
| `src/backend/db_models.py` | Pydantic models for config, payment result, payment log |
| `src/backend/db/schema.py` | Table definitions |
| `src/backend/db/migrations.py` | Migration #23 |
| `src/backend/database.py` | Delegate methods |

### Frontend
| File | Purpose |
|------|---------|
| `src/frontend/src/components/NeverminedPanel.vue` | Payments tab component |
| `src/frontend/src/views/AgentDetail.vue` | Tab registration |

### MCP
| File | Purpose |
|------|---------|
| `src/mcp-server/src/tools/nevermined.ts` | 4 MCP tools |
| `src/mcp-server/src/client.ts` | API methods |
| `src/mcp-server/src/server.ts` | Tool registration |

## Database Tables

- **nevermined_agent_config** — Per-agent config with encrypted `NVM_API_KEY`
- **nevermined_payment_log** — Audit trail of verify/settle/reject/settle_failed actions

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/paid/{agent_name}/chat` | x402 | Paid chat (402/403/200) |
| `GET` | `/api/paid/{agent_name}/info` | None | Payment info |
| `POST` | `/api/nevermined/agents/{name}/config` | JWT | Configure |
| `GET` | `/api/nevermined/agents/{name}/config` | JWT | Read config |
| `DELETE` | `/api/nevermined/agents/{name}/config` | JWT | Remove config |
| `PUT` | `/api/nevermined/agents/{name}/config/toggle` | JWT | Enable/disable |
| `GET` | `/api/nevermined/agents/{name}/payments` | JWT | Payment history |
| `GET` | `/api/nevermined/settlement-failures` | Admin | Failed settlements |
| `POST` | `/api/nevermined/retry-settlement/{log_id}` | Admin | Retry settlement |

## MCP Tools

| Tool | Description |
|------|-------------|
| `configure_nevermined` | Set up payment config |
| `get_nevermined_config` | Read config (no key) |
| `toggle_nevermined` | Enable/disable |
| `get_nevermined_payments` | Payment history |

## Isolation Guarantees

1. All changes are additive — no existing code paths modified
2. Lazy SDK imports — `payments-py` never imported at module level
3. Graceful degradation — 501 if SDK not installed
4. No foreign key constraints to existing tables
5. Independent failure domain — bugs affect only `/api/paid/` and `/api/nevermined/`
