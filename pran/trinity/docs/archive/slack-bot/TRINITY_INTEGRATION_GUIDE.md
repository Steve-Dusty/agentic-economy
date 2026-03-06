# Slack Integration - Trinity Platform

## Executive Summary

**Goal**: Integrate Slack capabilities into the Trinity Agent Platform
**Recommended Approach**: **Slack MCP Server** (simplest and most aligned)
**Effort**: 2-4 hours
**Status**: Documentation exists, implementation needed

---

## Current Trinity Architecture

Trinity is a **universal agent platform** where:
- ✅ Backend creates/manages agent containers dynamically
- ✅ Each agent runs isolated in Docker with Claude Code
- ✅ Agents can have MCP servers configured
- ✅ Credentials injected automatically (OAuth2 + Redis storage)
- ✅ Web UI for agent management
- ✅ **Slack credentials already supported** in backend (`credentials.py:55-58`)

### Existing Slack Support

**In `src/backend/credentials.py`:**
```python
"slack": {
    "auth_url": "https://slack.com/oauth/v2/authorize",
    "token_url": "https://slack.com/api/oauth.v2.access",
    "scopes": ["chat:write", "channels:read", "users:read"]
}
```

**Trinity already has Slack OAuth2 configured!** ✅

---

## Three Integration Options

### Option 1: Slack MCP Server ⭐ **RECOMMENDED**

**What it is**: Create a standardized MCP server package that ANY agent can use for Slack integration.

**Architecture:**
```
Trinity Platform
├── Backend API (creates agents)
├── Agent Container (isolated)
│   ├── Claude Code
│   ├── Slack MCP Server ← Add this
│   │   └── Tools: slack_send_message, slack_get_context, etc.
│   └── Other MCP servers (n8n, Google, etc.)
└── Credentials (injected from Redis)
```

**How it works:**
1. User adds Slack credentials via Trinity Web UI (OAuth2 flow)
2. Backend stores in Redis
3. When creating agent, user selects "slack" MCP server
4. Backend injects Slack credentials into agent container
5. Agent's Slack MCP server connects to Slack using credentials
6. Claude Code can use Slack tools: `slack_send_message`, `slack_listen`, etc.

**Implementation Steps:**

1. **Create Slack MCP Server Package** (~2 hours)
   ```bash
   mkdir packages/slack-mcp
   cd packages/slack-mcp
   npm init
   # Implement MCP server following ARCHITECTURE_MCP_PACKAGE.md pattern
   ```

2. **Add to Base Image** (~30 min)
   ```dockerfile
   # In docker/base-image/Dockerfile
   COPY packages/slack-mcp /opt/slack-mcp
   RUN cd /opt/slack-mcp && npm install
   ```

3. **Add to MCP Registry** (~15 min)
   ```python
   # In src/backend/main.py, add to available MCP servers
   AVAILABLE_MCP_SERVERS = {
       "slack": {
           "command": "node",
           "args": ["/opt/slack-mcp/dist/index.js"],
           "env_vars": ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_SIGNING_SECRET"]
       }
   }
   ```

4. **Update Frontend** (~15 min)
   ```javascript
   // In src/frontend/.../CreateAgentModal.vue
   const availableMCPServers = [
       'n8n-mcp',
       'google-workspace',
       'slack',  // ← Already listed!
       'github',
       'notion'
   ]
   ```

**Advantages:**
- ✅ **Simplest integration** - follows existing pattern
- ✅ **Reusable** - any agent can use Slack
- ✅ **Standardized** - MCP protocol, consistent with other tools
- ✅ **No changes to Trinity core** - just adds new MCP server
- ✅ **Credentials already supported** - OAuth2 flow exists
- ✅ **Agent-level control** - each agent decides if it wants Slack
- ✅ **Template-compatible** - can be included in agent templates

**Disadvantages:**
- ⚠️ Each agent uses Slack independently (no central routing)
- ⚠️ Need to implement MCP server (but straightforward)

---

### Option 2: Slack Router (Multi-Agent)

**What it is**: One Slack bot that routes messages to different agents based on content/channel.

**Architecture:**
```
Slack Workspace
    ↓
Slack Router Bot (standalone container)
    ↓
Routes to different agents via agent API
    ↓
Agent 1, Agent 2, Agent 3...
```

**How it works:**
1. Deploy separate Slack router container
2. Router listens to ALL Slack messages
3. Analyzes content/channel and routes to appropriate agent
4. Agents respond via router back to Slack

**Implementation Steps:**
1. Create standalone Slack router service (~4-6 hours)
2. Add agent communication API to agents
3. Implement routing logic
4. Deploy as additional Docker Compose service

**Advantages:**
- ✅ **Centralized routing** - smart message distribution
- ✅ **Single Slack app** - users see one bot
- ✅ **Multi-agent coordination** - agents can collaborate
- ✅ **Channel-based routing** - different channels → different agents

**Disadvantages:**
- ❌ **More complex** - new service to maintain
- ❌ **Single point of failure** - router down = no Slack
- ❌ **Tighter coupling** - agents depend on router
- ❌ **Additional deployment** - separate container
- ❌ **Not agent-level** - system-level integration

---

### Option 3: Slack as Agent Template

**What it is**: Pre-configured agent template with Slack integration built-in.

**Architecture:**
```
Trinity Platform
└── Templates
    └── slack-bot-agent
        ├── .claude/
        ├── slack-handler code
        └── Slack credentials config
```

**How it works:**
1. User creates agent from "Slack Bot" template
2. Template includes Slack handling code
3. Agent runs both Claude Code + Slack bot

**Implementation Steps:**
1. Create `config/agent-templates/slack-bot-agent/`
2. Include Slack bot implementation
3. Add to template registry

**Advantages:**
- ✅ **Pre-configured** - works out of the box
- ✅ **Easy to deploy** - just create agent from template
- ✅ **Complete solution** - everything included

**Disadvantages:**
- ❌ **Not reusable** - one agent = one Slack workspace
- ❌ **Template-specific** - not available to other agents
- ❌ **Redundant** - duplicates Slack code across agents

---

## Comparison Matrix

| Aspect | MCP Server ⭐ | Router | Template |
|--------|--------------|--------|----------|
| **Complexity** | 🟢 Low | 🟡 Medium | 🟢 Low |
| **Integration Effort** | 2-4 hours | 6-8 hours | 4-6 hours |
| **Reusability** | ✅ High | ❌ Low | ❌ None |
| **Follows Trinity Pattern** | ✅ Yes | ⚠️ Partial | ⚠️ Partial |
| **Agent Independence** | ✅ Yes | ❌ No | ✅ Yes |
| **Multi-Agent Routing** | ❌ No | ✅ Yes | ❌ No |
| **Maintenance** | 🟢 Easy | 🟡 Medium | 🟢 Easy |
| **Credentials** | ✅ Built-in | ⚠️ Separate | ⚠️ Per-agent |

---

## Recommended Approach: Slack MCP Server

### Why MCP Server?

1. **Aligns with Trinity Architecture**
   - Trinity is built around MCP servers
   - Slack becomes just another tool, like n8n-mcp
   - No architectural changes needed

2. **Credentials Already Supported**
   - Backend already has Slack OAuth2 configured
   - Redis storage ready
   - Web UI supports adding credentials

3. **Agent-Level Flexibility**
   - Some agents can use Slack, others don't
   - Each agent can have different Slack workspaces
   - Follows Trinity's "agent independence" principle

4. **Template-Ready**
   - Can be included in agent templates
   - Example: "Social Media Agent" template includes Slack MCP
   - Ruby template already has pattern for multiple MCPs

5. **Simplest Implementation**
   - Just create MCP server package
   - Add to base image
   - Register in backend
   - Done!

---

## Implementation Plan

### Phase 1: Create Slack MCP Server (2-3 hours)

**Directory Structure:**
```
packages/slack-mcp/
├── package.json
├── src/
│   ├── index.ts                # MCP server entry
│   ├── slack-client.ts         # Slack SDK wrapper
│   └── tools/
│       ├── send-message.ts
│       ├── get-context.ts
│       ├── listen.ts
│       └── upload-file.ts
├── dist/                       # Compiled output
└── README.md
```

**Tools to Implement:**
- `slack_send_message` - Send message to channel/user
- `slack_get_context` - Get recent messages
- `slack_listen_messages` - Listen for new messages
- `slack_upload_file` - Upload files to Slack

**Reference Implementation:**
See `docs/slack-bot/ARCHITECTURE_MCP_PACKAGE.md` for complete code examples.

### Phase 2: Integrate with Trinity (1 hour)

1. **Add to Base Image:**
   ```dockerfile
   # docker/base-image/Dockerfile
   COPY packages/slack-mcp /opt/mcp-servers/slack-mcp
   RUN cd /opt/mcp-servers/slack-mcp && npm install && npm run build
   ```

2. **Register in Backend:**
   ```python
   # src/backend/main.py
   MCP_SERVER_CONFIGS = {
       "slack": {
           "name": "Slack Integration",
           "command": "node",
           "args": ["/opt/mcp-servers/slack-mcp/dist/index.js"],
           "env_mapping": {
               "SLACK_BOT_TOKEN": "token",
               "SLACK_APP_TOKEN": "app_token",
               "SLACK_SIGNING_SECRET": "signing_secret"
           },
           "credential_service": "slack"
       }
   }
   ```

3. **Frontend already supports it** - "slack" is already in the list!

### Phase 3: Documentation (30 min)

1. Update `README.md` with Slack MCP usage
2. Add example agent configuration
3. Document credential setup

---

## Usage After Implementation

### 1. Add Slack Credentials (Web UI)

1. Go to Trinity Web UI → Credentials
2. Click "Add Credential"
3. Select "Slack" → OAuth2 flow
4. Authorize Slack app
5. Credentials stored in Redis

### 2. Create Agent with Slack

**Via Web UI:**
1. Create Agent → Select "business-assistant"
2. MCP Servers → Check "Slack"
3. Resources → Choose template (optional)
4. Create

**Via API:**
```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "name": "social-media-agent",
    "type": "business-assistant",
    "port": 2290,
    "mcp_servers": ["slack", "n8n-mcp"],
    "resources": {"cpu": "2", "memory": "4g"}
  }'
```

### 3. Use Slack in Agent

SSH into agent or use chat API:
```bash
ssh -p 2290 developer@localhost
claude
```

Then in Claude:
```
User: "Send a message to #general saying hello"
Claude: [uses slack_send_message tool]

User: "What are the recent messages in #engineering?"
Claude: [uses slack_get_context tool]

User: "Listen for new messages and respond to questions"
Claude: [uses slack_listen_messages tool]
```

---

## Alternative: If You Need Centralized Routing

If you need ONE Slack bot that routes to MULTIPLE agents, then use **Option 2: Slack Router** instead.

**When to use Router:**
- ✅ Different channels → different agents
- ✅ Content-based routing (keywords)
- ✅ Single Slack app for users
- ✅ Multi-agent collaboration

**Implementation:**
See `docs/slack-bot/ARCHITECTURE_ROUTER_PATTERN.md` for detailed guide.

---

## File Locations

**Documentation:**
- This file: `/docs/slack-bot/TRINITY_INTEGRATION_GUIDE.md`
- MCP Package architecture: `/docs/slack-bot/ARCHITECTURE_MCP_PACKAGE.md`
- Router architecture: `/docs/slack-bot/ARCHITECTURE_ROUTER_PATTERN.md`

**Implementation (to create):**
- Slack MCP package: `/packages/slack-mcp/`
- Backend MCP registry: `/src/backend/main.py` (add to existing)
- Base image: `/docker/base-image/Dockerfile` (add COPY line)

**Existing:**
- Slack OAuth config: `/src/backend/credentials.py:55-58` ✅
- Frontend MCP list: `/src/frontend/src/views/Templates.vue` ✅
- Credential storage: Redis (already configured) ✅

---

## Next Steps

1. **Decide on approach** - MCP Server (recommended) or Router?
2. **Implement Slack MCP Server** - follow Phase 1
3. **Integrate with Trinity** - follow Phase 2
4. **Test with sample agent** - create agent with Slack MCP
5. **Document usage** - update README

**Estimated Total Effort: 3-4 hours** for MCP Server approach

---

## Questions?

- **Can agents share Slack workspace?** Yes, just use same credentials
- **Can each agent have different Slack?** Yes, inject different credentials
- **Does this break existing agents?** No, Slack is optional MCP server
- **What about existing environments?** They continue working independently
- **Can I add to agent templates?** Yes, include "slack" in template's mcp_servers

---

**Recommendation**: Start with Slack MCP Server approach. It's the simplest, most aligned with Trinity's architecture, and provides maximum flexibility. You can always add Router later if centralized routing is needed.
