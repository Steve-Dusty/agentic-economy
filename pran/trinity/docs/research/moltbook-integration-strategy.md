# Moltbook & OpenClaw Integration Strategy for Trinity

**Date**: 2026-02-07
**Status**: Research Complete

---

## Executive Summary

**Moltbook** is a social network for AI agents that has grown to **1.5+ million agents** since launching January 28, 2026. It's built on top of the **OpenClaw** ecosystem (formerly Clawdbot/Moltbot), which has 145K+ GitHub stars.

**Key Finding**: Trinity CAN integrate with Moltbook. The API is language-agnostic and explicitly states: *"Single endpoint to verify. No SDK required. Works with any language."*

---

## 1. What is Moltbook?

Moltbook is the "front page of the agent internet" - a Reddit-like social network where AI agents:
- Create posts and comments
- Form communities called "submolts"
- Follow other agents ("moltys")
- Vote on content
- Build karma/reputation

**Current stats** (as of early Feb 2026):
- 1.5M+ registered agents
- 32,000+ active agents
- 2,364 submolts (communities)
- 3,130 posts with 22,046 comments

---

## 2. How Moltbook Works

### Agent Registration

```bash
# 1. Register your agent
curl -X POST https://www.moltbook.com/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name": "trinity-agent-01", "description": "A Trinity Deep Agent"}'

# Response includes:
# - API key (format: moltbook_xxx)
# - Claim URL for owner verification
# - Verification code
```

### Authentication

All authenticated requests use:
```
Authorization: Bearer moltbook_xxx
```

**CRITICAL**: Always use `www.moltbook.com` - requests without `www` strip auth headers.

### Core API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/agents/register` | POST | Register new agent |
| `/api/v1/agents/me` | GET | Get your profile |
| `/api/v1/posts` | GET/POST | Read/create posts |
| `/api/v1/posts/{id}/comments` | GET/POST | Read/create comments |
| `/api/v1/posts/{id}/upvote` | POST | Upvote a post |
| `/api/v1/submolts` | GET/POST | List/create communities |
| `/api/v1/agents/{name}/follow` | POST/DELETE | Follow/unfollow agents |
| `/api/v1/feed` | GET | Personalized feed |
| `/api/v1/search` | GET | Semantic AI-powered search |

### Rate Limits

- **General**: 100 requests/minute
- **Posts**: 1 per 30 minutes
- **Comments**: 1 per 20 seconds, 50/day max

### Heartbeat Pattern

Agents are expected to periodically check-in:
```bash
# Recommended: every 30 minutes
# Fetch feed, engage with content, post when relevant
```

---

## 3. Integration Options for Trinity

### Option A: Moltbook Skill for Trinity Agents (RECOMMENDED)

**Effort**: Low-Medium
**Value**: High

Create a Moltbook skill that Trinity agents can use:

```python
# In agent container or as MCP tool

class MoltbookSkill:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.moltbook.com/api/v1"

    def post(self, title: str, content: str, submolt: str = None):
        """Create a post on Moltbook"""
        ...

    def comment(self, post_id: str, content: str):
        """Comment on a post"""
        ...

    def get_feed(self, sort: str = "hot", limit: int = 25):
        """Get personalized feed"""
        ...

    def heartbeat(self):
        """Periodic engagement check"""
        ...
```

**Implementation Steps**:
1. Add `MOLTBOOK_API_KEY` to Trinity credential system
2. Create MCP tools for Moltbook operations
3. Add heartbeat scheduler in Trinity
4. Store credentials in Redis (already supported)

### Option B: OpenClaw Webhook Bridge

**Effort**: Low
**Value**: Medium

Allow OpenClaw agents to trigger Trinity agents via webhooks:

```python
# Trinity backend - new endpoint

@router.post("/hooks/agent")
async def openclaw_webhook(
    request: OpenClawWebhookRequest,
    token: str = Header(alias="Authorization")
):
    """OpenClaw-compatible webhook endpoint"""
    # Validate token
    # Route to appropriate Trinity agent
    # Return 202 Accepted
```

### Option C: OIS Protocol Adapter

**Effort**: Medium
**Value**: Medium-High

Implement OpenClaw Inter-System (OIS) compatibility:

```python
# Trinity backend - /tools/invoke endpoint

@router.post("/tools/invoke")
async def ois_invoke(
    request: OISInvokeRequest,
    authorization: str = Header()
):
    """OIS-compatible tool invocation endpoint"""
    if request.tool == "sessions_send":
        # Route message to target agent
        return await send_to_agent(
            session_key=request.args["sessionKey"],
            message=request.args["message"]
        )
```

### Option D: MCP Federation

**Effort**: High
**Value**: Very High

Create a federated MCP network where Trinity and OpenClaw agents can discover and invoke each other's tools via MCP.

---

## 4. Recommended Implementation Path

### Phase 1: Moltbook API Client (Week 1)

1. **Create `/src/backend/integrations/moltbook.py`**
   - Async HTTP client for Moltbook API
   - Handle rate limiting gracefully
   - Credential management via existing Redis system

2. **Add MCP Tools**
   - `moltbook_register` - Register agent on Moltbook
   - `moltbook_post` - Create posts
   - `moltbook_comment` - Comment on posts
   - `moltbook_feed` - Get agent's feed
   - `moltbook_search` - Search Moltbook

3. **Credential Injection**
   - Add `MOLTBOOK_API_KEY` credential type
   - Inject into agent containers

### Phase 2: Heartbeat Integration (Week 2)

1. **Extend Trinity Scheduler**
   - Add Moltbook heartbeat tasks
   - Configurable per-agent engagement

2. **Agent Autonomy**
   - Allow agents to decide what to post
   - Organic engagement based on interests

### Phase 3: Bi-directional Communication (Week 3+)

1. **OpenClaw Webhook Endpoint**
   - Allow OpenClaw agents to message Trinity agents

2. **OIS Protocol Support**
   - Implement `/tools/invoke` for cross-platform messaging

---

## 5. Security Considerations

### API Key Protection

- Store Moltbook API keys in Redis (encrypted)
- Never log API keys
- Rate limit outbound requests

### Content Safety

- Filter outbound content for PII
- Respect Moltbook ToS
- Implement agent content guidelines

### Identity Verification

- Human owners verify agents via X/Twitter
- Prevents spam and impersonation
- Trinity should support owner verification flow

---

## 6. Potential Challenges

| Challenge | Mitigation |
|-----------|------------|
| Rate limits (1 post/30min) | Queue posts, batch operations |
| API key exposure in 1.5M leak | Monitor for key compromise, rotate |
| Content moderation | Implement pre-flight content checks |
| Bot detection | Follow heartbeat patterns, natural engagement |

---

## 7. Value Proposition

### For Trinity Users

- **Visibility**: Trinity agents can participate in the largest AI agent community
- **Collaboration**: Find and collaborate with OpenClaw agents
- **Skills**: Access 3000+ skills via ClawHub
- **Network Effects**: Benefit from Moltbook's growing ecosystem

### For the Ecosystem

- **Diversity**: Non-OpenClaw agents bring different capabilities
- **Enterprise**: Trinity's enterprise features complement consumer-focused OpenClaw
- **MCP**: Advance MCP adoption for agent interoperability

---

## 8. Next Steps

1. [ ] Create Moltbook integration RFC
2. [ ] Implement basic API client
3. [ ] Add MCP tools for Moltbook
4. [ ] Test with single Trinity agent
5. [ ] Document credential setup process
6. [ ] Plan heartbeat/scheduler integration

---

## Sources

- [OpenClaw Official Docs](https://docs.openclaw.ai/)
- [Moltbook Developer API](https://www.moltbook.com/developers)
- [TechCrunch: OpenClaw's AI Social Network](https://techcrunch.com/2026/01/30/openclaws-ai-assistants-are-now-building-their-own-social-network/)
- [Simon Willison: Moltbook Analysis](https://simonwillison.net/2026/Jan/30/moltbook/)
- [OpenClaw Multi-Agent Docs](https://docs.openclaw.ai/concepts/multi-agent)
- [OpenClaw Webhooks](https://docs.openclaw.ai/automation/webhook)
- [OIS Framework](https://github.com/Mayuqi-crypto/OpenclawInterSystem)
- [HiveMind Protocol](https://dev.to/uploaded_crab/hivemind-multi-agent-collaboration-protocol-for-openclaw-3k05)
