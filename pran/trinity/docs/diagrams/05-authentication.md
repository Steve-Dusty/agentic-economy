# Trinity Authentication Architecture

> **Last Updated**: 2026-01-25
>
> **What This Diagram Shows**: The multi-layered authentication and authorization system in Trinity. Layer 1 handles human users logging into the web UI. Layer 2 handles MCP API keys for Claude Code clients. Layer 3 handles agent-to-agent permissions. Layer 4 describes the privileged system agent.

## Authentication Layers Overview

```
+----------------------------------------------------------------------------------+
|                      TRINITY AUTHENTICATION LAYERS                               |
|                                                                                  |
|                                                                                  |
|   +------------------------------------------------------------------------+    |
|   |                        LAYER 1: USER AUTHENTICATION                     |    |
|   |                        (Human -> Platform)                              |    |
|   |                                                                         |    |
|   |   +---------------+                      +---------------+              |    |
|   |   |   Dev Mode    |                      |  Email Auth   |              |    |
|   |   |   (local)     |                      |  (default)    |              |    |
|   |   +-------+-------+                      +-------+-------+              |    |
|   |           |                                      |                      |    |
|   |           +------------------+-------------------+                      |    |
|   |                              |                                          |    |
|   |           +------------------|------------------+                       |    |
|   |           |                  |                  |                       |    |
|   |           v                  v                  v                       |    |
|   |   +---------------+  +---------------+  +---------------+               |    |
|   |   |  JWT Token    |  |  JWT Token    |  |  JWT Token    |               |    |
|   |   |  mode: "dev"  |  |  mode: "email"|  |  mode: "admin"|               |    |
|   |   +---------------+  +---------------+  +---------------+               |    |
|   |                                                                         |    |
|   |   Auth0 OAuth REMOVED 2026-01-01 - See email-authentication.md          |    |
|   |                                                                         |    |
|   +------------------------------------------------------------------------+    |
|                                                                                  |
|   +------------------------------------------------------------------------+    |
|   |                        LAYER 2: MCP API KEYS                            |    |
|   |                        (Claude Code Client -> MCP Server)               |    |
|   |                                                                         |    |
|   |   +------------------+                   +------------------+           |    |
|   |   |  User API Key    |                   |  Agent API Key   |           |    |
|   |   |  scope: "user"   |                   |  scope: "agent"  |           |    |
|   |   |                  |                   |  agent_name set  |           |    |
|   |   +--------+---------+                   +--------+---------+           |    |
|   |            |                                      |                     |    |
|   |            +---------------+----------------------+                     |    |
|   |                            |                                            |    |
|   |                            v                                            |    |
|   |                   +-------------------+                                 |    |
|   |                   | Authorization:    |                                 |    |
|   |                   | Bearer trinity_   |                                 |    |
|   |                   | mcp_xxxxx         |                                 |    |
|   |                   +-------------------+                                 |    |
|   |                                                                         |    |
|   +------------------------------------------------------------------------+    |
|                                                                                  |
|   +------------------------------------------------------------------------+    |
|   |                        LAYER 3: AGENT PERMISSIONS                       |    |
|   |                        (Agent -> Agent)                                 |    |
|   |                                                                         |    |
|   |   +-------------------------------------------------------------------+ |    |
|   |   |                    agent_permissions table                         | |    |
|   |   |                                                                    | |    |
|   |   |   source_agent    |  target_agent    |  granted_by                | |    |
|   |   |   --------------------------------------------------------------- | |    |
|   |   |   orchestrator    |  worker-1        |  user-123                  | |    |
|   |   |   orchestrator    |  worker-2        |  user-123                  | |    |
|   |   |   worker-1        |  orchestrator    |  user-123                  | |    |
|   |   |                                                                    | |    |
|   |   +-------------------------------------------------------------------+ |    |
|   |                                                                         |    |
|   +------------------------------------------------------------------------+    |
|                                                                                  |
|   +------------------------------------------------------------------------+    |
|   |                        LAYER 4: SYSTEM AGENT                            |    |
|   |                        (Privileged Access)                              |    |
|   |                                                                         |    |
|   |   +-------------------------------------------------------------------+ |    |
|   |   |                                                                    | |    |
|   |   |   trinity-system agent                                             | |    |
|   |   |   scope: "system"                                                  | |    |
|   |   |                                                                    | |    |
|   |   |   * Bypasses ALL permission checks                                 | |    |
|   |   |   * Can communicate with any agent                                 | |    |
|   |   |   * Cannot be deleted                                              | |    |
|   |   |   * Auto-deployed on startup                                       | |    |
|   |   |                                                                    | |    |
|   |   +-------------------------------------------------------------------+ |    |
|   |                                                                         |    |
|   +------------------------------------------------------------------------+    |
|                                                                                  |
+----------------------------------------------------------------------------------+
```

## Email Authentication Flow

```
+----------------------------------------------------------------------------------+
|                      EMAIL AUTHENTICATION FLOW                                   |
|                                                                                  |
|                                                                                  |
|   +----------+         +----------+         +----------+         +----------+   |
|   |  Browser |         | Frontend |         | Backend  |         |  Email   |   |
|   |          |         |  Vue.js  |         | FastAPI  |         | Provider |   |
|   +----+-----+         +----+-----+         +----+-----+         +----+-----+   |
|        |                    |                    |                    |          |
|        |  Enter email       |                    |                    |          |
|        |------------------->|                    |                    |          |
|        |                    |                    |                    |          |
|        |                    |  POST /api/auth/   |                    |          |
|        |                    |  email/request     |                    |          |
|        |                    |  {email}           |                    |          |
|        |                    |------------------->|                    |          |
|        |                    |                    |                    |          |
|        |                    |                    |  Check whitelist   |          |
|        |                    |                    |  (email_whitelist) |          |
|        |                    |                    |                    |          |
|        |                    |                    |  Rate limit check  |          |
|        |                    |                    |  (3 per 10 min)    |          |
|        |                    |                    |                    |          |
|        |                    |                    |  Generate 6-digit  |          |
|        |                    |                    |  code              |          |
|        |                    |                    |                    |          |
|        |                    |                    |  Store in          |          |
|        |                    |                    |  email_login_codes |          |
|        |                    |                    |                    |          |
|        |                    |                    |  Send email        |          |
|        |                    |                    |------------------->|          |
|        |                    |                    |                    |          |
|        |                    |<-------------------|                    |          |
|        |                    |  {success, expires}|                    |          |
|        |                    |                    |                    |          |
|        |<-------------------|                    |                    |          |
|        |  Show code input   |                    |                    |          |
|        |  + countdown timer |                    |                    |          |
|        |                    |                    |                    |          |
|        |                    |                    |                    |          |
|        |  Enter 6-digit code|                    |                    |          |
|        |------------------->|                    |                    |          |
|        |                    |                    |                    |          |
|        |                    |  POST /api/auth/   |                    |          |
|        |                    |  email/verify      |                    |          |
|        |                    |  {email, code}     |                    |          |
|        |                    |------------------->|                    |          |
|        |                    |                    |                    |          |
|        |                    |                    |  Validate code     |          |
|        |                    |                    |  (not expired,     |          |
|        |                    |                    |   not used)        |          |
|        |                    |                    |                    |          |
|        |                    |                    |  Create/get user   |          |
|        |                    |                    |                    |          |
|        |                    |                    |  Generate JWT      |          |
|        |                    |                    |                    |          |
|        |                    |<-------------------|                    |          |
|        |                    |  {token, user}     |                    |          |
|        |                    |                    |                    |          |
|        |<-------------------|                    |                    |          |
|        |  Redirect to       |                    |                    |          |
|        |  dashboard         |                    |                    |          |
|        |                    |                    |                    |          |
|   +----+-----+         +----+-----+         +----+-----+         +----+-----+   |
|                                                                                  |
|                                                                                  |
|   Whitelist Auto-Population:                                                     |
|   --------------------------                                                     |
|   When user A shares an agent with user B (email):                               |
|   +-- User B automatically added to email_whitelist                              |
|       +-- source: "agent_sharing"                                                |
|                                                                                  |
+----------------------------------------------------------------------------------+
```

## Admin Login Flow

```
+----------------------------------------------------------------------------------+
|                      ADMIN LOGIN FLOW                                            |
+----------------------------------------------------------------------------------+

+-------------+     +-------------+     +-------------+     +-------------+
|  Login.vue  |---->|  auth.js    |---->| POST /token |---->| database.py |
|  UI Form    |     |  store      |     |  FastAPI    |     |  SQLite     |
+-------------+     +-------------+     +-------------+     +-------------+
      |                   |                   |                   |
      | password          | FormData          | authenticate      | SELECT
      | entered           | POST              | _user()           | FROM users
      |                   |                   |                   |
      v                   v                   v                   v
+-------------+     +-------------+     +-------------+     +-------------+
| handleAdmin |---->| loginWith   |---->| verify_     |---->| bcrypt      |
| Login()     |     | Credentials |     | password()  |     | verify      |
+-------------+     +-------------+     +-------------+     +-------------+
                          |                   |
                          | success           | create_access
                          |                   | _token()
                          v                   v
                    +-------------+     +-------------+
                    | localStorage|<----| JWT Token   |
                    | + axios     |     | mode=admin  |
                    | headers     |     | exp=7 days  |
                    +-------------+     +-------------+
                          |
                          | router.push('/')
                          v
                    +-------------+
                    | Dashboard   |
                    | (protected) |
                    +-------------+
```

## MCP Authentication Flow

```
+----------------------------------------------------------------------------------+
|                      MCP SERVER AUTHENTICATION                                   |
|                                                                                  |
|                                                                                  |
|   +--------------+              +--------------+              +--------------+   |
|   | Claude Code  |              |  MCP Server  |              |   Backend    |   |
|   |   Client     |              |   FastMCP    |              |   FastAPI    |   |
|   +------+-------+              +------+-------+              +------+-------+   |
|          |                             |                             |           |
|          |                             |                             |           |
|          |  MCP Request                |                             |           |
|          |  Authorization: Bearer      |                             |           |
|          |  trinity_mcp_xxxxx          |                             |           |
|          |---------------------------->|                             |           |
|          |                             |                             |           |
|          |                             |  POST /api/mcp/validate     |           |
|          |                             |  {api_key}                  |           |
|          |                             |---------------------------->|           |
|          |                             |                             |           |
|          |                             |                             |  Hash     |
|          |                             |                             |  key      |
|          |                             |                             |           |
|          |                             |                             |  Lookup   |
|          |                             |                             |  in DB    |
|          |                             |                             |           |
|          |                             |<----------------------------|           |
|          |                             |  {                          |           |
|          |                             |    valid: true,             |           |
|          |                             |    user_id: "user-123",     |           |
|          |                             |    email: "user@domain.com",|           |
|          |                             |    agent_name: null,        |           |
|          |                             |    scope: "user"            |           |
|          |                             |  }                          |           |
|          |                             |                             |           |
|          |                             |  Create McpAuthContext      |           |
|          |                             |  Store in session           |           |
|          |                             |                             |           |
|          |                             |  Execute tool with          |           |
|          |                             |  auth context               |           |
|          |                             |                             |           |
|          |<----------------------------|                             |           |
|          |  Tool result                |                             |           |
|          |                             |                             |           |
|   +------+-------+              +------+-------+              +------+-------+   |
|                                                                                  |
|                                                                                  |
|   MCP Auth Context Structure:                                                    |
|   ---------------------------                                                    |
|   {                                                                              |
|     userId: "user-123",           // User who owns the key                       |
|     userEmail: "user@domain.com", // User's email                                |
|     keyName: "my-key",            // Name given to the key                       |
|     agentName: "agent-a",         // Only set for agent-scoped keys              |
|     scope: "user"|"agent"|"system"// Permission level                            |
|   }                                                                              |
|                                                                                  |
+----------------------------------------------------------------------------------+
```

## Key Code References

### Layer 1: User Authentication

| Component | File | Lines | Description |
|-----------|------|-------|-------------|
| Email Request Endpoint | `src/backend/routers/auth.py` | 140-198 | Request verification code |
| Email Verify Endpoint | `src/backend/routers/auth.py` | 201-268 | Verify code and get JWT |
| Admin Login Endpoint | `src/backend/routers/auth.py` | 49-78 | POST /api/token |
| Auth Mode Endpoint | `src/backend/routers/auth.py` | 27-46 | GET /api/auth/mode |
| Whitelist Endpoints | `src/backend/routers/settings.py` | 429-503 | GET/POST/DELETE whitelist |
| Email Auth DB Ops | `src/backend/db/email_auth.py` | 27-253 | Whitelist and code operations |
| Password Verification | `src/backend/dependencies.py` | 24-37 | verify_password() |
| JWT Token Creation | `src/backend/dependencies.py` | 50-68 | create_access_token() |
| Login View | `src/frontend/src/views/Login.vue` | 38-123 | Email auth UI |
| Admin Login View | `src/frontend/src/views/Login.vue` | 126-171 | Admin password form |
| Auth Store | `src/frontend/src/stores/auth.js` | 165-212 | requestEmailCode, verifyEmailCode |

### Layer 2: MCP API Keys

| Component | File | Lines | Description |
|-----------|------|-------|-------------|
| Create Key Endpoint | `src/backend/routers/mcp_keys.py` | 14-34 | POST /api/mcp/keys |
| List Keys Endpoint | `src/backend/routers/mcp_keys.py` | 37-51 | GET /api/mcp/keys |
| Validate Key Endpoint | `src/backend/routers/mcp_keys.py` | 144-180 | POST /api/mcp/validate |
| MCP Key DB Operations | `src/backend/db/mcp_keys.py` | 63-236 | create, validate, revoke |
| MCP Server Auth | `src/mcp-server/src/server.ts` | 114-151 | FastMCP authenticate callback |
| API Keys View | `src/frontend/src/views/ApiKeys.vue` | 1-559 | Key management UI |

### Layer 3: Agent Permissions

| Component | File | Lines | Description |
|-----------|------|-------|-------------|
| Permission Endpoints | `src/backend/routers/agents.py` | 642-681 | GET/PUT/POST/DELETE permissions |
| Permission Service | `src/backend/services/agent_service/permissions.py` | 18-168 | Business logic |
| Permission DB Ops | `src/backend/db/permissions.py` | 39-223 | Database operations |
| Database Delegation | `src/backend/database.py` | 1070-1091 | Manager delegation methods |
| list_agents Filtering | `src/mcp-server/src/tools/agents.ts` | 61-74 | Filter visible agents |
| chat_with_agent Check | `src/mcp-server/src/tools/chat.ts` | 29-100 | Permission enforcement |
| Permissions Panel | `src/frontend/src/components/PermissionsPanel.vue` | 1-148 | UI component |

### Layer 4: System Agent

| Component | File | Lines | Description |
|-----------|------|-------|-------------|
| System Scope Check | `src/mcp-server/src/tools/chat.ts` | 26-30 | Bypass permission checks |

---

## Sources

- [Email Authentication Feature Flow](../memory/feature-flows/email-authentication.md) - Complete email auth implementation
- [Admin Login Feature Flow](../memory/feature-flows/admin-login.md) - Admin password authentication
- [MCP API Keys Feature Flow](../memory/feature-flows/mcp-api-keys.md) - API key management
- [Agent Permissions Feature Flow](../memory/feature-flows/agent-permissions.md) - Agent-to-agent access control
- [Architecture Documentation](../memory/architecture.md) - Authentication section (lines 868-1050)
