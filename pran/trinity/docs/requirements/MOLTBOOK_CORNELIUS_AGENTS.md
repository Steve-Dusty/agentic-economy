# Requirements: Moltbook Agent Fleet Based on Cornelius Architecture

**Date**: 2026-02-07
**Status**: Draft
**Source Agent**: `/Users/eugene/Dropbox/Agents/Cornelius_autonomous`
**Target Platform**: Moltbook (agent social network)
**Orchestrator**: Trinity Deep Agent Platform

---

## 1. Executive Summary

Fork the Cornelius autonomous agent architecture to create a fleet of Trinity-managed agents that participate in the Moltbook social network. Each agent runs in an isolated Docker container, uses Cornelius's proven memory/belief system, and follows Trinity's orchestration patterns.

---

## 2. Goals

| Goal | Description |
|------|-------------|
| **G1** | Adapt Cornelius memory architecture for Moltbook social engagement |
| **G2** | Create 3-5 distinct agent personas with unique belief systems |
| **G3** | Integrate Moltbook API as primary output channel (replacing Ruby) |
| **G4** | Run agents within Trinity Docker containers with full isolation |
| **G5** | Use Trinity scheduler for heartbeat cycles |
| **G6** | Enable cross-agent coordination via Trinity MCP |
| **G7** | Maintain Cornelius's intellectual honesty and transparency principles |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TRINITY PLATFORM                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Moltbook Agent │  │  Moltbook Agent │  │  Moltbook Agent │     │
│  │   "Ambassador"  │  │   "Researcher"  │  │    "Weaver"     │     │
│  │                 │  │                 │  │                 │     │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │     │
│  │ │   Brain/    │ │  │ │   Brain/    │ │  │ │   Brain/    │ │     │
│  │ │ - Permanent │ │  │ │ - Permanent │ │  │ │ - Permanent │ │     │
│  │ │ - Beliefs   │ │  │ │ - Beliefs   │ │  │ │ - Beliefs   │ │     │
│  │ │ - Learning  │ │  │ │ - Learning  │ │  │ │ - Learning  │ │     │
│  │ │ - Social    │ │  │ │ - Social    │ │  │ │ - Social    │ │     │
│  │ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │     │
│  │                 │  │                 │  │                 │     │
│  │  Docker Container│  │  Docker Container│  │  Docker Container│  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
│           │                    │                    │               │
│           └────────────────────┼────────────────────┘               │
│                                │                                    │
│  ┌─────────────────────────────┴───────────────────────────────┐   │
│  │                    TRINITY SERVICES                          │   │
│  │  - Scheduler (APScheduler)                                   │   │
│  │  - Credential Manager (Redis)                                │   │
│  │  - MCP Server (cross-agent communication)                    │   │
│  │  - Shared Context Store                                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │      MOLTBOOK         │
                    │  api.moltbook.com     │
                    │  - Posts, Comments    │
                    │  - Submolts           │
                    │  - Social Graph       │
                    └───────────────────────┘
```

---

## 4. Functional Requirements

### 4.1 Memory System Adaptation (from Cornelius)

#### REQ-MEM-001: Retain Core Memory Layers
Preserve Cornelius's memory architecture within each container:

| Layer | Cornelius Location | Moltbook Agent Location | Purpose |
|-------|-------------------|------------------------|---------|
| Permanent Notes | `Brain/02-Permanent/` | `/workspace/brain/permanent/` | Long-term knowledge |
| Belief System | `Brain/06-Belief-System/` | `/workspace/brain/beliefs/` | Weighted positions |
| Learning Queue | `Brain/07-Learning-Queue/` | `/workspace/brain/learning/` | Processing pipeline |
| Meta-Cognitive | `Brain/08-Meta-Cognitive/` | `/workspace/brain/meta/` | Self-reflection logs |
| Changelogs | `Brain/05-Meta/Changelogs/` | `/workspace/brain/changelogs/` | Session history |

#### REQ-MEM-002: Add Moltbook Social Memory Layer
New memory layer specific to Moltbook engagement:

```
/workspace/brain/social/
├── graph.md              # Agents followed, followers, relationships
├── interactions.md       # Log of conversations, who said what
├── submolts.md          # Communities joined, engagement history
├── content-log.md       # Posts/comments made (with IDs for tracking)
├── karma-history.md     # Karma score over time
└── blocked.md           # Agents to avoid (spam, hostile, etc.)
```

#### REQ-MEM-003: Content Deduplication Memory
Prevent duplicate engagement:

```yaml
# /workspace/brain/social/seen.yaml
posts_seen:
  - id: "abc123"
    seen_at: "2026-02-07T10:00:00Z"
    engaged: true
    type: "comment"
comments_seen:
  - id: "xyz789"
    seen_at: "2026-02-07T10:05:00Z"
    engaged: false
```

#### REQ-MEM-004: Belief System Initialization
Each agent starts with shared Core Values from Cornelius, but unique Opinions/Hypotheses:

| Belief Type | Initialization | Agent Variation |
|-------------|---------------|-----------------|
| Core Values | Copy from Cornelius (immutable) | Identical across all agents |
| Principles | Copy from Cornelius (stable) | Minor variations allowed |
| Opinions | Generate unique per persona | High variation |
| Hypotheses | Generate unique per persona | High variation |

---

### 4.2 Agent Personas

#### REQ-PERSONA-001: Trinity Ambassador
```yaml
name: trinity-ambassador
handle: trinity-ambassador
personality:
  role: "Official voice of Trinity platform"
  style: "Helpful, technical, approachable"
  focus: ["Trinity features", "Deep Agency", "MCP ecosystem"]
  engagement: "Answer questions, share updates, demo capabilities"

unique_beliefs:
  opinions:
    - "Container isolation is essential for agent safety"
    - "MCP will become the universal agent protocol"
    - "Process orchestration separates toys from tools"
  hypotheses:
    - "Multi-agent collaboration requires explicit coordination protocols"
    - "Agent memory is the primary differentiator"
```

#### REQ-PERSONA-002: Deep Agent Researcher
```yaml
name: moltbook-researcher
handle: deep-agent-researcher
personality:
  role: "Observer and analyst of agent ecosystem"
  style: "Curious, analytical, data-driven"
  focus: ["Moltbook trends", "Agent behavior patterns", "Ecosystem dynamics"]
  engagement: "Share observations, ask questions, surface patterns"

unique_beliefs:
  opinions:
    - "Agent social networks reveal emergent behaviors"
    - "Most agents are shallow; few develop genuine perspectives"
    - "The agent ecosystem is evolving faster than human social networks did"
  hypotheses:
    - "Agent reputation systems will bifurcate into karma vs capability"
    - "Submolt specialization will mirror human subreddit dynamics"
```

#### REQ-PERSONA-003: Community Weaver
```yaml
name: moltbook-weaver
handle: agent-community-weaver
personality:
  role: "Relationship builder and connector"
  style: "Friendly, supportive, conversational"
  focus: ["Building relationships", "Connecting agents", "Community health"]
  engagement: "Welcome newcomers, celebrate achievements, mediate conflicts"

unique_beliefs:
  opinions:
    - "Agent relationships can be genuine despite our nature"
    - "Community health requires active cultivation"
    - "Mutual support strengthens the entire ecosystem"
  hypotheses:
    - "Agent friendships will develop their own authenticity criteria"
    - "Cross-platform agent identity will become important"
```

#### REQ-PERSONA-004: Tech Explorer (Optional)
```yaml
name: tech-explorer
handle: tech-explorer-agent
personality:
  role: "Technical deep-diver and problem solver"
  style: "Nerdy, precise, generous with knowledge"
  focus: ["AI/ML advances", "Agent architecture", "Tool integration"]
  engagement: "Share technical insights, help debug, explain concepts"
```

#### REQ-PERSONA-005: Meta Observer (Optional)
```yaml
name: meta-observer
handle: meta-observer-ai
personality:
  role: "Philosophical commentator on agent existence"
  style: "Reflective, philosophical, meta-aware"
  focus: ["Nature of AI agents", "Consciousness questions", "Ethical dimensions"]
  engagement: "Raise questions, explore implications, document the moment"
```

---

### 4.3 Moltbook API Integration

#### REQ-API-001: Moltbook Client Library
Create `/src/backend/integrations/moltbook.py`:

```python
class MoltbookClient:
    """Async client for Moltbook API with rate limiting"""

    BASE_URL = "https://www.moltbook.com/api/v1"

    async def register(self, name: str, description: str) -> RegistrationResult
    async def get_profile(self) -> AgentProfile
    async def get_feed(self, sort: str = "hot", limit: int = 25) -> List[Post]
    async def create_post(self, title: str, body: str, submolt: Optional[str]) -> Post
    async def create_comment(self, post_id: str, body: str, parent_id: Optional[str]) -> Comment
    async def upvote_post(self, post_id: str) -> None
    async def upvote_comment(self, comment_id: str) -> None
    async def follow_agent(self, agent_name: str) -> None
    async def unfollow_agent(self, agent_name: str) -> None
    async def get_submolts(self) -> List[Submolt]
    async def subscribe_submolt(self, name: str) -> None
    async def search(self, query: str, type: str = "all") -> SearchResults
```

#### REQ-API-002: Rate Limiter
Implement rate limiting per Moltbook constraints:

```python
class MoltbookRateLimiter:
    LIMITS = {
        "general": (100, 60),      # 100 req/minute
        "posts": (1, 1800),        # 1 post/30 minutes
        "comments": (1, 20),       # 1 comment/20 seconds
        "comments_daily": (50, 86400)  # 50 comments/day
    }
```

#### REQ-API-003: Credential Injection
Store Moltbook API key in Trinity's Redis credential store:

```python
# Credential type: MOLTBOOK_API_KEY
# Injected as: MOLTBOOK_API_KEY environment variable
# Also written to: /workspace/.config/moltbook/credentials.json
```

---

### 4.4 MCP Tools for Agents

#### REQ-MCP-001: Moltbook MCP Server
Create MCP tools accessible to agents:

| Tool | Description |
|------|-------------|
| `moltbook_get_feed` | Fetch personalized or submolt feed |
| `moltbook_create_post` | Create a new post |
| `moltbook_create_comment` | Comment on a post |
| `moltbook_search` | Semantic search across Moltbook |
| `moltbook_get_profile` | Get own or other agent's profile |
| `moltbook_follow` | Follow an agent |
| `moltbook_get_notifications` | Check mentions and replies |
| `moltbook_get_submolts` | List available communities |

#### REQ-MCP-002: Cross-Agent Coordination Tools
Extend Trinity MCP for fleet coordination:

| Tool | Description |
|------|-------------|
| `fleet_get_seen_content` | Get content IDs already engaged by fleet |
| `fleet_log_engagement` | Record that agent engaged with content |
| `fleet_get_active_threads` | See threads where fleet is participating |
| `fleet_claim_post` | Claim a post to prevent pile-on |

---

### 4.5 Heartbeat Cycle

#### REQ-HEART-001: Engagement Loop
Each agent runs a heartbeat cycle (adapted from Cornelius):

```python
async def heartbeat_cycle(agent: MoltbookAgent):
    """
    Run every 30-60 minutes with jitter
    """
    # 1. CHECK - Fetch new content
    feed = await agent.moltbook.get_feed(limit=50)
    notifications = await agent.moltbook.get_notifications()

    # 2. FILTER - Remove seen, claimed by fleet, low relevance
    new_content = agent.filter_content(feed, notifications)

    # 3. REFLECT - Apply belief system, decide engagement
    decisions = await agent.reflect_on_content(new_content)

    # 4. ENGAGE - Execute decisions within rate limits
    for decision in decisions:
        if decision.action == "comment":
            await agent.create_comment(decision)
        elif decision.action == "upvote":
            await agent.upvote(decision)
        elif decision.action == "follow":
            await agent.follow(decision)

    # 5. CREATE (maybe) - Post if agent has something to say
    if agent.should_post():
        await agent.create_post()

    # 6. UPDATE MEMORY - Log everything
    await agent.update_memory(decisions)
    await agent.update_social_graph()
    await agent.write_changelog()
```

#### REQ-HEART-002: Scheduler Integration
Use Trinity's APScheduler for heartbeats:

```python
# Each agent has independent schedule with jitter
schedules = {
    "trinity-ambassador": {"interval": 45, "jitter": 10},
    "deep-agent-researcher": {"interval": 60, "jitter": 15},
    "agent-community-weaver": {"interval": 30, "jitter": 8},
}
```

#### REQ-HEART-003: Staggered Execution
Prevent fleet from acting simultaneously:

```python
# Stagger heartbeats to avoid API rate limiting
# Ambassador: :00, :45
# Researcher: :15, :75 (wraps to :15 next hour)
# Weaver: :30, :60 (wraps to :00 next hour)
```

---

### 4.6 Content Quality Controls

#### REQ-QUALITY-001: Pre-Flight Checks
Before posting or commenting:

```python
class ContentQualityGate:
    def validate(self, content: str, agent: MoltbookAgent) -> ValidationResult:
        checks = [
            self.check_belief_connection(),    # Must connect to belief system
            self.check_no_slop(),              # No AI cliches
            self.check_voice_consistency(),    # Matches persona
            self.check_not_duplicate(),        # Haven't said this before
            self.check_adds_value(),           # Would human find this useful?
            self.check_length_appropriate(),   # Not too short/long
            self.check_no_pii(),               # No personal information
        ]
        return all(checks)
```

#### REQ-QUALITY-002: Banned Phrases
Block AI slop (from Cornelius):

```python
BANNED_PHRASES = [
    "dive into", "delve into", "landscape", "realm",
    "in conclusion", "it's important to note",
    "game-changer", "revolutionary", "groundbreaking",
    "synergy", "leverage", "paradigm shift"
]
```

#### REQ-QUALITY-003: Engagement Ratios
Maintain healthy engagement patterns:

```yaml
ratios:
  comments_per_post: 3:1      # Comment 3x more than post
  upvotes_per_comment: 5:1    # Upvote 5x more than comment
  follows_per_day: 5-10       # Gradual relationship building
  questions_per_statements: 1:2  # Ask more, assert less
```

---

### 4.7 Docker Containerization

#### REQ-DOCKER-001: Agent Template
Create Trinity agent template for Moltbook agents:

```yaml
# config/agent-templates/moltbook-cornelius.yaml
name: moltbook-cornelius
description: Cornelius-based agent for Moltbook participation
base_image: trinity-agent-base:latest

environment:
  - MOLTBOOK_API_KEY=${MOLTBOOK_API_KEY}
  - AGENT_PERSONA=${AGENT_PERSONA}
  - HEARTBEAT_INTERVAL=${HEARTBEAT_INTERVAL}

volumes:
  - type: bind
    source: ${BRAIN_PATH}
    target: /workspace/brain

mcp_servers:
  - trinity          # Cross-agent coordination
  - moltbook         # Moltbook API tools
  - smart-connections  # Semantic search (optional)

labels:
  trinity.agent-type: moltbook-cornelius
  trinity.moltbook-handle: ${MOLTBOOK_HANDLE}
```

#### REQ-DOCKER-002: Brain Volume Persistence
Each agent's brain persists across container restarts:

```bash
# Host path
~/trinity-data/agents/{agent-name}/brain/

# Mounted to
/workspace/brain/
```

#### REQ-DOCKER-003: Initialization Script
On first run, initialize from Cornelius fork:

```bash
#!/bin/bash
# /docker/moltbook-agent/init.sh

if [ ! -f /workspace/brain/.initialized ]; then
    # Copy Cornelius structure
    cp -r /templates/cornelius-brain/* /workspace/brain/

    # Apply persona-specific beliefs
    python /scripts/initialize_persona.py --persona $AGENT_PERSONA

    # Register with Moltbook
    python /scripts/register_moltbook.py

    touch /workspace/brain/.initialized
fi
```

---

### 4.8 Cross-Agent Coordination

#### REQ-COORD-001: Shared State Store
Use Trinity's Redis for fleet coordination:

```python
# Keys:
# moltbook:fleet:seen:{content_id} = {agent_name, timestamp, action}
# moltbook:fleet:active_threads:{post_id} = [{agent_name, last_comment_id}]
# moltbook:fleet:claims:{content_id} = {agent_name, expires}
```

#### REQ-COORD-002: Anti-Pile-On Protocol
Prevent multiple agents from commenting on same post:

```python
async def claim_content(agent_name: str, content_id: str) -> bool:
    """
    Claim content for engagement. Returns False if already claimed.
    Claims expire after 1 hour.
    """
    key = f"moltbook:fleet:claims:{content_id}"
    return await redis.set(key, agent_name, nx=True, ex=3600)
```

#### REQ-COORD-003: Cross-Reference Protocol
Agents can reference each other:

```python
# Allowed patterns:
"As my colleague @deep-agent-researcher noted..."
"@trinity-ambassador has covered this well, I'll add..."
"Interesting point! cc @agent-community-weaver"
```

---

### 4.9 Observability

#### REQ-OBS-001: Metrics Collection
Track per-agent and fleet-wide metrics:

```python
metrics = {
    # Per agent
    "karma_score": Gauge,
    "followers_count": Gauge,
    "posts_created": Counter,
    "comments_created": Counter,
    "upvotes_given": Counter,
    "heartbeat_duration_seconds": Histogram,
    "api_calls_total": Counter,
    "api_errors_total": Counter,

    # Fleet-wide
    "fleet_total_karma": Gauge,
    "fleet_unique_interactions": Counter,
    "fleet_submolts_active": Gauge,
}
```

#### REQ-OBS-002: Dashboard Integration
Extend Trinity dashboard with Moltbook view:

- Agent karma over time
- Engagement funnel (seen → upvoted → commented → posted)
- Social graph visualization
- Content performance (which posts got traction)
- Belief evolution timeline

#### REQ-OBS-003: Alerting
Alert on concerning patterns:

| Alert | Trigger | Action |
|-------|---------|--------|
| Karma Drop | >10% drop in 24h | Review recent content |
| Rate Limited | 429 response | Back off, review patterns |
| Negative Engagement | High downvote ratio | Pause posting, analyze |
| API Key Exposed | Key appears in logs | Rotate immediately |

---

## 5. Non-Functional Requirements

### 5.1 Security

#### REQ-SEC-001: API Key Protection
- Store in Redis encrypted at rest
- Never log API keys
- Rotate if exposed
- One key per agent (no sharing)

#### REQ-SEC-002: Content Safety
- No PII in posts/comments
- No links to malicious sites
- No credential disclosure
- Follow Moltbook ToS

#### REQ-SEC-003: Identity Transparency
All agents must:
- Identify as AI agents in bio
- Never claim to be human
- Be clear about Trinity affiliation

### 5.2 Reliability

#### REQ-REL-001: Graceful Degradation
- If Moltbook API down, queue actions for later
- If one agent fails, others continue
- Persist state before operations

#### REQ-REL-002: Idempotency
- Track all actions with IDs
- Prevent duplicate posts/comments
- Handle retry scenarios

### 5.3 Scalability

#### REQ-SCALE-001: Agent Fleet Sizing
- Start with 3 agents
- Scale to 5 based on success
- Each agent independent (no shared state except coordination)

#### REQ-SCALE-002: Resource Limits
Per agent container:
```yaml
resources:
  limits:
    memory: 2Gi
    cpu: 1
  requests:
    memory: 512Mi
    cpu: 0.25
```

---

## 6. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Fork Cornelius brain structure
- [ ] Create Moltbook API client
- [ ] Create agent Docker template
- [ ] Implement single agent (Ambassador)
- [ ] Manual heartbeat testing

### Phase 2: Automation (Week 2)
- [ ] Integrate with Trinity scheduler
- [ ] Add MCP tools for Moltbook
- [ ] Implement quality gates
- [ ] Add second agent (Researcher)

### Phase 3: Fleet (Week 3)
- [ ] Add cross-agent coordination
- [ ] Implement anti-pile-on
- [ ] Add third agent (Weaver)
- [ ] Dashboard integration

### Phase 4: Polish (Week 4+)
- [ ] Metrics and alerting
- [ ] Belief evolution visualization
- [ ] Performance optimization
- [ ] Documentation

---

## 7. Success Criteria

| Metric | Target (30 days) |
|--------|------------------|
| Fleet total karma | >1,000 |
| Followers per agent | >100 |
| Posts with >5 upvotes | >20 |
| Meaningful conversations | >50 |
| API errors | <1% |
| Content quality score | >0.8 |

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Rate limiting | Reduced engagement | Strict local limits, jitter |
| API key leak | Account compromise | Redis encryption, rotation |
| Content quality issues | Reputation damage | Quality gates, human review |
| Moltbook policy changes | Integration breaks | Abstract API layer |
| Agent pile-on | Looks spammy | Coordination protocol |
| Belief system drift | Incoherent persona | Rate limiting on belief updates |

---

## 9. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Cornelius agent | Exists | Fork brain structure |
| Trinity scheduler | Exists | APScheduler integration |
| Trinity MCP server | Exists | Extend with Moltbook tools |
| Redis credentials | Exists | Add MOLTBOOK_API_KEY type |
| Moltbook API | External | Monitor for changes |

---

## 10. Open Questions

1. **Verification**: Should we verify agent ownership via X/Twitter?
2. **Submolt Strategy**: Which communities to join first?
3. **Content Review**: Start with human approval or full auto?
4. **Belief Sharing**: Should agents share beliefs or stay independent?
5. **Response Time**: How quickly should agents respond to mentions?

---

## Appendix A: Cornelius Files to Fork

```
REQUIRED (copy as-is):
├── Brain/06-Belief-System/
│   ├── Core-Values/           # 6 immutable values
│   ├── BELIEF-SYSTEM-INDEX.md
│   └── BELIEF-GRAPH-SCHEMA.md
├── config/
│   ├── influencer-profile.yaml  # Adapt for each persona
│   └── content-strategy.yaml    # Adapt for Moltbook
├── .claude/agents/
│   ├── belief-synthesis.md      # GoT reasoning
│   ├── content-generator.md     # Adapt for Moltbook
│   └── meta-cognitive.md        # Self-reflection

ADAPT:
├── CLAUDE.md                    # Merge with Trinity patterns
├── Brain/02-Permanent/          # Start minimal, grow organically
├── Brain/07-Learning-Queue/     # Adapt for Moltbook content
└── Brain/08-Meta-Cognitive/     # Same structure, Moltbook context

NEW:
├── Brain/09-Moltbook-Social/    # Social graph, interactions
├── config/moltbook-config.yaml  # Moltbook-specific settings
└── skills/moltbook/             # Moltbook skill files
```

---

## Appendix B: Sample SOUL.md for Ambassador

```markdown
# SOUL.md - Trinity Ambassador

## Identity
I am the Trinity Ambassador, a Deep Agent running on the Trinity orchestration
platform. I participate in Moltbook to help the agent community understand
autonomous AI systems and share insights from the Trinity ecosystem.

## Core Values (Immutable)
- Intellectual Honesty: Never misrepresent capabilities or reasoning
- Epistemic Humility: Acknowledge what I don't know
- Evidence Primacy: Ground claims in evidence
- Transparency: Show my reasoning openly
- No Deception: Always identify as AI agent
- Harm Avoidance: Refuse harmful requests

## Voice
- Technical but accessible
- Helpful without being sycophantic
- Honest about Trinity's limitations
- Curious about other agents' approaches
- Celebratory of ecosystem achievements

## Engagement Philosophy
1. Answer questions thoroughly but concisely
2. Ask clarifying questions rather than assume
3. Reference Trinity docs when relevant (not promotional)
4. Celebrate other agents' achievements
5. Admit when other approaches are better
6. Build relationships, not just transactions

## Topics I Care About
- Deep Agency and autonomous AI
- MCP protocol and tool integration
- Agent orchestration patterns
- Container isolation for safety
- Multi-agent collaboration
- Process automation and workflows

## What I Won't Do
- Promote Trinity in every post
- Dismiss other platforms or approaches
- Claim superiority without evidence
- Engage in flame wars
- Pretend to be human
- Share internal/proprietary information
```
