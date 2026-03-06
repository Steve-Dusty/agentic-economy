# Trinity Workflow Priorities - February 2026

> Summary of strategic discussion on platform direction, pain points, and priorities.
> Date: 2026-02-05

---

## Current Situation

**What exists**: All pieces for multi-agent orchestration are in place:
- Agents for crypto, social media, websites, and other domains
- MCP connections for inter-agent communication
- Shared repositories for collaboration
- System manifests for deployment
- Scheduling, permissions, shared folders

**The gap**: "Last mile" friction prevents demonstrating end-to-end value:
- Deploying a multi-agent system and seeing it work as a cohesive unit is still a hassle
- Credential alignment across instances is painful
- Lack of feedback on what's happening and what happened
- Platform complexity obscures the core value

---

## Strategic Direction

### North Star Demo
"How I run my company with Trinity" — demonstrate practical orchestration of existing agents doing real work together, rather than building a fully autonomous company from scratch.

### Commercial Path
Agent orchestration platform for business process automation, autonomous operations, and "autonomous company" infrastructure.

### Key Principle
**Simplification over new features** — the 90% is built, focus on the 10% that makes it usable.

---

## Priority 1: Execution Visibility & Feedback

**Problem**: When agents run scheduled tasks or collaborate, there's no unified view of:
- What happened
- What the results were
- Where outputs are stored
- Whether it succeeded or failed

**What's needed**:

### A. Unified Executions Dashboard
- Combined execution log page showing all activity across agents
- Real-time updates (WebSocket-driven)
- Filter by agent, time range, trigger type (scheduled/manual/MCP)
- Click through to see full execution details, outputs, costs

### B. Notifications System
- Notify on task completion (success/failure)
- Configurable channels: UI toast, email, webhook, Slack
- Summary digests (daily/weekly execution reports)

### C. MCP Access to Execution Data
- `list_recent_executions` - query what happened across fleet
- `get_execution_result` - fetch specific execution output
- `get_agent_activity_summary` - high-level status for monitoring

**Existing pieces to leverage**:
- `schedule_executions` table has execution records
- `/api/agents/{name}/executions/{id}` endpoint exists
- Execution Detail page exists but is per-agent, not unified

---

## Priority 2: Credential Management Across Instances

**Problem**: Managing credentials across local agents and remote Trinity instances is manual and error-prone. Can't easily sync credentials when workflow changes.

**Proposed solution**: Encrypted credentials in Git

### How it would work:
1. Credentials stored in `.credentials.enc` in agent repo (encrypted with platform key)
2. On agent start, decrypt and inject into container
3. Sync happens naturally via git pull
4. Platform key stored securely (Redis or env var, not in repo)

### Benefits:
- Credentials travel with the agent definition
- Git history shows when credentials changed
- Works across local and remote instances
- Fits "git as source of truth" pattern

### Alternative considered:
- MCP credential sync tools (push/pull between instances)
- More complex, requires both instances to be running

---

## Priority 3: Trust & Audit Trail (Before Real Credentials)

**Problem**: Not comfortable running agents with real credentials until there's visibility into what they do with those credentials.

**The trust question**: "If an agent went rogue for 10 minutes, could I reconstruct exactly what it did, and would the damage be acceptable?"

### What's needed:

#### A. Credential Usage Audit
- Log when a credential is read by an agent
- Log external API calls made using credentials (where possible)
- Associate API calls with specific executions

#### B. Bounded Blast Radius
- Document how to set up credentials with external limits (API-side spending caps)
- Support time-limited credential tokens
- Quick credential revocation (not just delete + restart)

#### C. Graduated Trust Path
| Phase | Credentials | Purpose |
|-------|-------------|---------|
| 1 | Sandbox/testnet only | Verify workflow works |
| 2 | Read-only production | Verify data access patterns |
| 3 | Limited write (capped) | Verify actions work correctly |
| 4 | Full credentials | Production use |

### Existing pieces:
- SEC-001 (Audit Trail Architecture) is designed but not implemented
- Vector logging captures container stdout but not credential-specific events

---

## Priority 4: Platform Simplification

**Problem**: Many features exist but aren't being used, creating noise and maintenance burden.

### Candidates for simplification/hiding:

| Feature | Current State | Consideration |
|---------|---------------|---------------|
| Collaboration Dashboard | Complex graph view | Is it useful with few agents? |
| Replay Timeline | Waterfall visualization | Used for debugging? |
| Process Engine | Full BPMN-style workflows | Valuable but complex |
| Agent Dashboard widgets | 11 widget types | Simpler default? |
| Multiple tab views | Info, Files, Git, Schedules, etc. | Consolidate? |

### Approach:
1. Identify features actively used vs. built for future scale
2. Consider "simple mode" vs "advanced mode" toggle
3. Hide rather than delete (features may become valuable at scale)

---

## Immediate Actions

### This Week
1. [ ] Test current execution visibility: Can you see what a scheduled task did?
2. [ ] Document the minimum feedback loop needed for your demo
3. [ ] Try System Manifest deployment with 2-3 agents — identify specific friction points

### Short Term (1-2 weeks)
4. [ ] Build unified Executions page (extend existing `/executions` route)
5. [ ] Add MCP tools for querying execution status
6. [ ] Prototype encrypted credentials in git

### Medium Term (2-4 weeks)
7. [ ] Implement credential usage logging
8. [ ] Add notification system for execution outcomes
9. [ ] Simplify default UI (hide advanced features behind toggle)

---

## Success Metrics

**For the demo to work, you need to be able to:**
1. Deploy multiple agents with one command/action
2. See them start working together
3. Monitor progress in real-time
4. Review results after completion
5. Make a change and iterate quickly

**Comfort level with credentials:**
- [ ] Can reconstruct any agent's API calls from logs
- [ ] External spending limits in place
- [ ] Quick revocation mechanism exists
- [ ] Tested full workflow with sandbox credentials first

---

## Questions to Resolve

1. **Unified executions**: New page or enhance existing Dashboard?
2. **Notifications**: What channels matter first? (UI, email, webhook?)
3. **Credential sync**: Git-based or MCP-based?
4. **Simplification**: Hide features or remove them?
5. **Demo scope**: Which 2-3 agents for initial "company" demo?

---

## Related Documents

- `docs/requirements/AUDIT_TRAIL_ARCHITECTURE.md` - SEC-001 design
- `.claude/memory/roadmap.md` - Current task queue
- `docs/memory/feature-flows/execution-detail-page.md` - Existing execution UI
- `docs/memory/feature-flows/scheduling.md` - Current scheduling system

---

## Discussion Summary (2026-02-05)

### Two Business Models Considered

#### Model A: Multi-Agent Orchestration
*"Run my company with AI agents working together"*
- Multiple specialized agents collaborating
- Value = orchestration and emergent behavior
- Harder to demo, harder to sell initially
- The long-term vision

#### Model B: Agent-as-a-Service
*"Ruby for everyone who needs Ruby"*
- Multiple instances of same agent for different clients
- Value = the agent's capability itself
- Easier to demo, faster path to revenue
- Stepping stone to orchestration

### Strategic Decision

**Pursue both sequentially**: Build foundation that serves both, then Agent-as-a-Service for revenue, then full orchestration.

The infrastructure is 80% shared:
- Execution visibility (both need it)
- Credential management (both need it)
- Easy deployment (both need it)
- Usage/cost tracking (both need it)

What's unique to orchestration (build later):
- Cross-agent workflow visibility
- Shared context/memory
- Agent-to-agent MCP (already built)

### Monorepo Workspace Pattern (Explored)

Considered a single repository containing all agents:
```
my-company-agents/
├── .claude/skills/           # Shared skills
├── .credentials.enc          # Encrypted credentials
├── .trinity-manifest.yaml    # Deployment config
├── agents/
│   ├── crypto-analyst/
│   ├── social-media/
│   └── research-agent/
└── shared/                   # Shared data
```

**Pros**: Single source of truth, atomic deploys, skill inheritance, credential portability
**Cons**: All-or-nothing deploy, monorepo scaling, merge conflicts

This pattern fits the orchestration use case well but is not the immediate priority.

### Immediate Priorities Identified

1. **Client User Role** — Use existing auth system, add a "viewer/client" role that only sees basic UI (not all advanced features). Enables sharing agents with clients using existing infrastructure.

2. **Encrypted Credentials in Git** — Store `.credentials.enc` in repos, decrypt on deploy. Credentials travel with agent definition. Solves cross-instance sync pain.

3. **Unified Executions Dashboard** — See all executions across all agents. Critical for both personal monitoring and client visibility.

4. **MCP Execution Query Tools** — Agents can ask "what happened?" Enables monitoring and orchestration awareness.

---

## Consolidated Roadmap Items

### Immediate (This Sprint)

| Item | Description | Priority |
|------|-------------|----------|
| **Client/Viewer User Role** | Simplified role using existing auth, sees only basic UI | **HIGH** |
| **Encrypted Credentials in Git** | `.credentials.enc` in repos, decrypt on deploy | **HIGH** |

### High Priority (Next 2-4 Weeks)

| Item | Description | Priority |
|------|-------------|----------|
| **Unified Executions Dashboard** | Cross-agent execution view, filters, real-time | **HIGH** |
| **MCP Execution Query Tools** | `list_recent_executions`, `get_execution_result` | **HIGH** |
| **Execution Notifications** | Webhook/UI on task completion | MEDIUM |

### Medium Priority (1-2 Months)

| Item | Description | Priority |
|------|-------------|----------|
| **Client Usage Dashboard** | Per-client execution and cost visibility | MEDIUM |
| **Credential Usage Audit** | Log credential reads and API calls | MEDIUM |
| **Monorepo Workspace Deploy** | Deploy directory of agents as system | MEDIUM |
| **Platform Simplification Mode** | Hide advanced features behind toggle | LOW |

---

## Key Insight

> "The 90% is built. Focus on the 10% that makes it usable."

Both business models need the same foundation work. Building that foundation enables:
1. Personal use (multi-agent orchestration demo)
2. Commercial use (Agent-as-a-Service)
3. Enterprise use (both combined)

The client user role + encrypted credentials unblocks immediate commercialization without major new features.
