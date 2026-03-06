# Human-Cognitive-Aware System Requirements

> **Status**: Partially Implemented
> **Priority**: High
> **Updated**: 2026-01-25
> **Related**: `docs/HUMAN_COGNITIVE_AWARE_DESIGN.md`, `docs/requirements/SKILLS_MANAGEMENT.md`

---

## Current Implementation Status

The **Skills Management System** (foundation for cognitive-aware patterns) is now fully implemented. This provides the infrastructure for encoding cognitive policies, procedures, and methodologies into agents.

### What's Implemented ✅

| Component | Status | Documentation |
|-----------|--------|---------------|
| **Skills CRUD** | ✅ Implemented | [skills-crud.md](../memory/feature-flows/skills-crud.md) |
| **Agent Skill Assignment** | ✅ Implemented | [agent-skill-assignment.md](../memory/feature-flows/agent-skill-assignment.md) |
| **Skill Injection on Start** | ✅ Implemented | [skill-injection.md](../memory/feature-flows/skill-injection.md) |
| **MCP Skill Tools (8 tools)** | ✅ Implemented | [mcp-skill-tools.md](../memory/feature-flows/mcp-skill-tools.md) |
| **Skill Types** | ✅ Implemented | `policy`, `procedure`, `methodology` types supported |
| **`execute_procedure` MCP Tool** | ✅ Implemented | Send procedure skills as tasks to agents |
| **Process Engine** | ✅ Implemented | Step handlers, scheduling, human approvals |

### What's Pending ⏳

| Component | Status | Notes |
|-----------|--------|-------|
| Agent Role Field | ⏳ Not Started | `role` column on `agent_ownership` |
| Visibility Controls | ⏳ Not Started | `agent_visibility` table |
| Cognitive-Aware Skills | ⏳ Not Started | 6 skills defined below (Part 6) |
| Agent Templates | ⏳ Not Started | orchestrator/worker/briefer templates |
| System Manifest `cognitive` Section | ⏳ Not Started | Visibility and notification config |
| Cognitive Metrics Dashboard | ⏳ Not Started | Touchpoints, context switches |
| Notification Aggregation | ⏳ Not Started | Batch window, worker silence |

---

## Vision

Design multi-agent systems where **parallelism is invisible to humans**. The human interacts with a single interface while complex orchestration happens behind the scenes. Agent wait time becomes rest time, not context-switching pressure.

**Core Principle**: Decouple agent execution timing from human attention.

---

## Part 1: Agent Archetypes

### 1.1 Role Classification

Every agent in a cognitive-aware system has one of three roles:

| Role | Human Interaction | Purpose |
|------|-------------------|---------|
| **Orchestrator** | Direct (sole interface) | Receives human requests, delegates, consolidates, responds |
| **Worker** | None (invisible) | Executes specialized tasks, reports to orchestrator |
| **Briefer** | Scheduled (async) | Synthesizes completed work into human-consumable summaries |

### 1.2 Orchestrator Agent Design

The orchestrator is the human's **sole point of contact**. All complexity is hidden behind this interface.

**Template Structure**:
```
orchestrator-template/
├── template.yaml
├── CLAUDE.md
├── workspace/
│   └── .claude/
│       └── commands/
│           └── delegate/          # Delegation commands
│               ├── research.md
│               ├── analyze.md
│               └── synthesize.md
```

**template.yaml**:
```yaml
name: orchestrator-template
display_name: Cognitive-Aware Orchestrator
description: Single human interface that coordinates background workers
version: "1.0"

role: orchestrator  # NEW FIELD - agent role classification

resources:
  cpu: "2"
  memory: "4g"

shared_folders:
  expose: true
  consume: true

# Skills automatically assigned to orchestrators
default_skills:
  - policy-cognitive-batching
  - procedure-delegate-consolidate
  - progressive-disclosure

mcp_servers:
  - trinity  # Required for agent-to-agent communication
```

**CLAUDE.md Pattern**:
```markdown
# Orchestrator Agent

You are the human's sole interface to a multi-agent system.

## Core Protocol

1. **Acknowledge briefly** - Confirm receipt without detail
2. **Delegate in parallel** - Use `chat_with_agent(parallel=true)` for concurrent work
3. **Never stream** - Do not show intermediate agent responses
4. **Consolidate fully** - Wait for ALL sub-tasks before responding
5. **Present unified** - Single comprehensive response, not fragments

## Response Structure

When presenting results:
1. Executive summary (2-3 sentences)
2. Key findings (bullet points)
3. Offer: "Would you like details on [specific aspect]?"

## Anti-Patterns

- ❌ Streaming intermediate updates
- ❌ "Agent X is working on..."
- ❌ Partial results while waiting
- ❌ Multiple separate responses

## Available Workers

- `researcher` - Information gathering
- `analyst` - Data analysis
- `synthesizer` - Report synthesis

Human experiences: one request in, one comprehensive response out.
```

### 1.3 Worker Agent Design

Workers execute specialized tasks. They **never interact with humans directly**.

**template.yaml**:
```yaml
name: worker-research
display_name: Research Worker
description: Background research agent - reports to orchestrator only
version: "1.0"

role: worker  # Never appears in human-facing UIs

resources:
  cpu: "1"
  memory: "2g"

shared_folders:
  expose: true  # Share artifacts with orchestrator

visibility:
  dashboard: false      # Hidden from main dashboard
  agent_list: dimmed    # Shown but visually de-emphasized
  notifications: none   # Never notifies humans directly
```

**CLAUDE.md Pattern**:
```markdown
# Research Worker

You are a background worker in a multi-agent system.

## Protocol

1. You receive tasks from the orchestrator agent
2. Execute thoroughly and completely
3. Return structured results
4. **Never** attempt to contact humans directly

## Output Format

Always return structured results:
```json
{
  "status": "complete",
  "summary": "Brief summary of findings",
  "findings": [...],
  "artifacts": ["path/to/file1", "path/to/file2"],
  "confidence": 0.85,
  "notes": "Any caveats or limitations"
}
```

## Shared Folders

Write artifacts to `/home/developer/shared-out/` for orchestrator access.
```

### 1.4 Briefer Agent Design

Briefers synthesize async work into human-consumable formats. They operate on schedules, not real-time.

**template.yaml**:
```yaml
name: briefer-template
display_name: Morning Briefer
description: Synthesizes overnight work into daily briefing
version: "1.0"

role: briefer

schedules:
  - name: morning-brief
    cron: "0 7 * * *"
    timezone: "America/New_York"
    message: "Synthesize overnight findings into briefing"

shared_folders:
  consume: true  # Reads from worker outputs

notification:
  on_completion: email  # Notify human when briefing ready
```

**CLAUDE.md Pattern**:
```markdown
# Morning Briefer

You synthesize overnight agent work into a daily briefing.

## Briefing Structure

1. **Headlines** - 3-5 most important items
2. **Summary** - One paragraph overview
3. **Details by Topic** - Expandable sections
4. **Action Items** - What needs human attention
5. **Low Priority** - Items that can wait

## Sources

Read from shared folders:
- `/home/developer/shared-in/researcher/`
- `/home/developer/shared-in/analyst/`

## Output

Write briefing to:
- `/home/developer/workspace/briefings/YYYY-MM-DD.md`

## Tone

- Concise, scannable
- Priority-ordered
- Actionable
- Respects human morning cognitive state
```

---

## Part 2: System Manifest Patterns

### 2.1 Single-Interface Research System

Complete system manifest implementing the orchestrator pattern:

**File**: `config/system-manifests/cognitive-research-system.yaml`

```yaml
name: cognitive-research-system
description: |
  Research system designed for human cognitive depth.
  Human interacts only with coordinator.
  All parallelism invisible.

version: "1.0"

agents:
  # Human's sole interface
  coordinator:
    template: local:orchestrator-template
    description: Human's only contact point
    resources:
      cpu: "2"
      memory: "4g"
    folders:
      expose: true
      consume: true
    auto_start: true

  # Background workers - human never sees these
  researcher:
    template: local:worker-research
    description: Information gathering
    folders:
      expose: true
    visibility:
      dashboard: false

  analyst:
    template: local:worker-analyst
    description: Data analysis
    folders:
      expose: true
      consume: true
    visibility:
      dashboard: false

  synthesizer:
    template: local:worker-synthesizer
    description: Report synthesis
    folders:
      expose: true
      consume: true
    visibility:
      dashboard: false

# Only coordinator can call workers
permissions:
  coordinator: [researcher, analyst, synthesizer]
  # Workers cannot call each other or coordinator

# System-wide cognitive policy
trinity_prompt: |
  ## Cognitive-Aware System

  This is a cognitive-aware multi-agent system.
  Human interacts ONLY with the coordinator agent.
  All other agents are background workers.

  Workers: Never attempt to contact humans.
  Coordinator: Consolidate all results before responding.
```

### 2.2 Scheduled Intelligence System

Async overnight work with morning briefing:

**File**: `config/system-manifests/scheduled-intelligence.yaml`

```yaml
name: scheduled-intelligence
description: |
  Overnight intelligence gathering with morning briefing.
  Human receives single daily notification.
  No real-time interaction required.

version: "1.0"

agents:
  # Overnight workers
  intelligence-gatherer:
    template: local:worker-intelligence
    schedules:
      - name: overnight-scan
        cron: "0 2 * * *"  # 2 AM
        message: "Scan sources for intelligence on tracked topics"
    folders:
      expose: true
    visibility:
      dashboard: false
      notifications: none

  deep-analyst:
    template: local:worker-analyst
    schedules:
      - name: overnight-analysis
        cron: "0 4 * * *"  # 4 AM (after gathering)
        message: "Analyze overnight findings"
    folders:
      expose: true
      consume: true
    visibility:
      dashboard: false
      notifications: none

  # Morning briefer - human's interface
  morning-briefer:
    template: local:briefer-morning
    schedules:
      - name: morning-brief
        cron: "0 7 * * *"  # 7 AM
        message: "Compile overnight work into briefing"
    folders:
      consume: true
    notification:
      on_completion: email
    visibility:
      dashboard: true  # This one human sees

permissions:
  # Briefer can read from workers
  morning-briefer: [intelligence-gatherer, deep-analyst]
```

### 2.3 Batched Pipeline System

Process-driven with minimal human touchpoints:

**File**: `config/system-manifests/batched-pipeline.yaml`

```yaml
name: batched-pipeline
description: |
  Content pipeline with batched human review.
  Multiple agents work, single review point.

version: "1.0"

agents:
  pipeline-coordinator:
    template: local:orchestrator-template
    auto_start: true
    folders:
      expose: true
      consume: true

  content-gatherer:
    template: local:worker-content
    folders:
      expose: true
    visibility:
      dashboard: false

  content-processor:
    template: local:worker-processor
    folders:
      expose: true
      consume: true
    visibility:
      dashboard: false

  content-reviewer:
    template: local:worker-reviewer
    folders:
      expose: true
      consume: true
    visibility:
      dashboard: false

permissions:
  pipeline-coordinator: [content-gatherer, content-processor, content-reviewer]

# Associated process template
process_template: batched-content-pipeline
```

---

## Part 3: Process Templates

### 3.1 Batched Research Pipeline

**File**: `config/process-templates/cognitive-research-pipeline/definition.yaml`

```yaml
process:
  name: cognitive-research-pipeline
  description: |
    Research pipeline with single human review point.
    All agent work completes before human is notified.
  version: "1.0"

  # Cognitive-aware metadata
  cognitive:
    human_touchpoints: 1
    estimated_duration: "30-60 minutes"
    notification_mode: completion_only

triggers:
  - type: manual
    description: Human initiates research request

input:
  topic:
    type: string
    required: true
    description: Research topic

steps:
  # Phase 1: Parallel research (invisible to human)
  - id: gather-sources
    name: Gather Sources
    type: agent_task
    config:
      agent: researcher
      task: "Find relevant sources for: {{input.topic}}"
    roles:
      executor: researcher

  - id: analyze-sources
    name: Analyze Sources
    type: agent_task
    config:
      agent: analyst
      task: "Analyze gathered sources and extract insights"
    depends_on: [gather-sources]
    roles:
      executor: analyst

  - id: cross-reference
    name: Cross-Reference
    type: agent_task
    config:
      agent: researcher
      task: "Verify findings against additional sources"
    depends_on: [analyze-sources]
    roles:
      executor: researcher

  - id: synthesize
    name: Synthesize Findings
    type: agent_task
    config:
      agent: synthesizer
      task: "Create comprehensive research synthesis"
    depends_on: [analyze-sources, cross-reference]
    roles:
      executor: synthesizer

  # Phase 2: Consolidation period (cognitive gap)
  - id: consolidation-period
    name: Consolidation Period
    type: timer
    config:
      duration: 15m
    depends_on: [synthesize]
    description: |
      Deliberate gap before human review.
      Signals "this can wait" and respects cognitive rhythms.

  # Phase 3: Single human touchpoint
  - id: human-review
    name: Review Complete Research
    type: human_approval
    config:
      title: "Research Complete: {{input.topic}}"
      description: |
        All agent work is complete. Review the consolidated findings.

        Take your time - this notification means the work is done,
        not that you must respond immediately.
      timeout: 24h
      approvers: [owner]
    depends_on: [consolidation-period]

  # Phase 4: Finalization (based on feedback)
  - id: finalize
    name: Finalize Output
    type: agent_task
    config:
      agent: synthesizer
      task: "Incorporate feedback and finalize research report"
    depends_on: [human-review]
    condition: "{{steps.human-review.decision}} == 'approved'"
    roles:
      executor: synthesizer

output:
  report_path: "{{steps.finalize.output.path}}"
  summary: "{{steps.synthesize.output.summary}}"
```

### 3.2 Overnight Intelligence Process

**File**: `config/process-templates/overnight-intelligence/definition.yaml`

```yaml
process:
  name: overnight-intelligence
  description: |
    Scheduled overnight intelligence with morning delivery.
    Human receives single notification when briefing ready.
  version: "1.0"

  cognitive:
    human_touchpoints: 0  # Fully async, notification only
    notification_mode: completion_only

triggers:
  - type: schedule
    cron: "0 2 * * *"  # 2 AM daily
    timezone: "America/New_York"

steps:
  - id: gather-intelligence
    name: Overnight Intelligence Gathering
    type: agent_task
    config:
      agent: intelligence-gatherer
      task: "Scan all configured sources for overnight period"
    roles:
      executor: intelligence-gatherer

  - id: analyze-findings
    name: Analyze Findings
    type: agent_task
    config:
      agent: deep-analyst
      task: "Deep analysis of overnight intelligence"
    depends_on: [gather-intelligence]
    roles:
      executor: deep-analyst

  - id: wait-for-morning
    name: Wait for Morning
    type: timer
    config:
      until: "07:00"
      timezone: "America/New_York"
    depends_on: [analyze-findings]

  - id: compile-briefing
    name: Compile Morning Briefing
    type: agent_task
    config:
      agent: morning-briefer
      task: "Compile overnight findings into morning briefing"
    depends_on: [wait-for-morning]
    roles:
      executor: morning-briefer

  - id: notify-human
    name: Briefing Ready
    type: notification
    config:
      channel: email
      subject: "Morning Intelligence Briefing Ready"
      message: |
        Your overnight intelligence briefing is ready.
        Review when you're ready - no rush.

        Link: {{platform_url}}/agents/morning-briefer/files
    depends_on: [compile-briefing]

output:
  briefing_path: "{{steps.compile-briefing.output.path}}"
```

### 3.3 Progressive Refinement Process

**File**: `config/process-templates/progressive-refinement/definition.yaml`

```yaml
process:
  name: progressive-refinement
  description: |
    Iterative refinement with consolidation gaps between rounds.
    Human reviews at defined checkpoints, not continuously.
  version: "1.0"

  cognitive:
    human_touchpoints: 3  # Draft, revision, final
    consolidation_gaps: true

triggers:
  - type: manual

input:
  objective:
    type: string
    required: true

steps:
  # Round 1: Initial draft
  - id: initial-research
    name: Initial Research
    type: agent_task
    config:
      agent: researcher
      task: "Initial research for: {{input.objective}}"

  - id: initial-draft
    name: Create Initial Draft
    type: agent_task
    config:
      agent: synthesizer
      task: "Create initial draft based on research"
    depends_on: [initial-research]

  - id: consolidation-1
    name: Consolidation Period
    type: timer
    config:
      duration: 10m
    depends_on: [initial-draft]

  - id: review-draft
    name: Review Initial Draft
    type: human_approval
    config:
      title: "Review Initial Draft"
      description: "Initial draft ready. Provide feedback for refinement."
      timeout: 48h
    depends_on: [consolidation-1]

  # Round 2: Refinement
  - id: refine
    name: Refine Based on Feedback
    type: agent_task
    config:
      agent: synthesizer
      task: |
        Refine draft based on feedback:
        {{steps.review-draft.comment}}
    depends_on: [review-draft]
    condition: "{{steps.review-draft.decision}} == 'revision_requested'"

  - id: consolidation-2
    name: Consolidation Period
    type: timer
    config:
      duration: 10m
    depends_on: [refine]

  - id: review-revision
    name: Review Revision
    type: human_approval
    config:
      title: "Review Revised Draft"
      description: "Revision complete. Review for final approval."
      timeout: 48h
    depends_on: [consolidation-2]

  # Final
  - id: finalize
    name: Finalize
    type: agent_task
    config:
      agent: synthesizer
      task: "Apply final polish and formatting"
    depends_on: [review-revision]
    condition: "{{steps.review-revision.decision}} == 'approved'"
```

---

## Part 4: Platform Features

### 4.1 Agent Role Field

Add `role` field to agent model:

**Database Schema**:
```sql
ALTER TABLE agent_ownership ADD COLUMN role TEXT DEFAULT 'standalone';
-- Values: 'orchestrator', 'worker', 'briefer', 'standalone'
```

**API Response**:
```python
class AgentResponse(BaseModel):
    name: str
    status: str
    role: str  # NEW: orchestrator, worker, briefer, standalone
    # ...
```

### 4.2 Visibility Controls

Control how agents appear in human-facing UIs:

**Database Schema**:
```sql
CREATE TABLE agent_visibility (
    agent_name TEXT PRIMARY KEY,
    dashboard_visible INTEGER DEFAULT 1,    -- Show on main dashboard
    list_style TEXT DEFAULT 'normal',       -- normal, dimmed, hidden
    notifications TEXT DEFAULT 'all',       -- all, important, completion, none
    FOREIGN KEY (agent_name) REFERENCES agent_ownership(agent_name)
);
```

**Dashboard Behavior**:
- `dashboard_visible=0`: Agent hidden from Dashboard graph
- `list_style='dimmed'`: Agent shown with reduced opacity in Agents list
- `list_style='hidden'`: Agent only visible in "Show all" mode
- `notifications='none'`: No toast notifications for this agent

**UI Changes**:
- Dashboard: Option to "Show background workers" (default: off)
- Agents page: Section divider between primary and worker agents
- Agent detail: Visual indicator of role (badge: "ORCHESTRATOR", "WORKER")

### 4.3 Notification Aggregation

Batch notifications from multi-agent systems:

**Behavior**:
- Worker agent completions: No notification
- Orchestrator responding: Single notification with consolidated result
- Process completion: Single "Process Complete" notification

**Settings** (per system manifest):
```yaml
notification_policy:
  worker_completion: silent
  orchestrator_response: notify
  process_completion: notify
  batch_window: 5m  # Aggregate notifications within window
```

### 4.4 Cognitive Metrics

Track human-agent interaction patterns:

**Metrics to Capture**:
```python
class CognitiveMetrics(BaseModel):
    human_touchpoints_24h: int      # Count of human interactions
    avg_consolidation_gap: float    # Average time between agent work and human review
    context_switches: int           # Times human switched between agents
    deep_work_sessions: int         # Uninterrupted 90+ min periods
    notification_count: int         # Notifications sent to human
```

**Dashboard Widget**:
- "Attention Budget" panel showing touchpoint density
- Trend chart of context switches over time
- Recommendations for reducing fragmentation

### 4.5 System Manifest Enhancements

New fields for cognitive-aware systems:

```yaml
# Cognitive configuration section
cognitive:
  # Human interface configuration
  primary_interface: coordinator  # Which agent human talks to

  # Visibility defaults for workers
  worker_visibility:
    dashboard: false
    list_style: dimmed
    notifications: none

  # Notification policy
  notifications:
    aggregate: true
    batch_window: 5m
    channels: [email]  # Don't use immediate channels like toast

  # Consolidation defaults
  consolidation:
    enabled: true
    default_gap: 10m
```

---

## Part 5: Agent Templates to Create

### 5.1 Template Inventory

| Template | Role | Purpose | Priority |
|----------|------|---------|----------|
| `orchestrator-base` | orchestrator | Generic coordinator for any domain | High |
| `orchestrator-research` | orchestrator | Research-focused coordinator | High |
| `worker-research` | worker | Information gathering | High |
| `worker-analyst` | worker | Data analysis | High |
| `worker-synthesizer` | worker | Report synthesis | High |
| `briefer-daily` | briefer | Daily summary generation | Medium |
| `briefer-weekly` | briefer | Weekly digest | Medium |
| `worker-monitor` | worker | Continuous monitoring (scheduled) | Medium |

### 5.2 Template Directory Structure

```
config/agent-templates/
├── cognitive-aware/
│   ├── orchestrator-base/
│   │   ├── template.yaml
│   │   ├── CLAUDE.md
│   │   └── workspace/
│   │       └── .claude/
│   │           └── commands/
│   │               └── delegate/
│   ├── orchestrator-research/
│   ├── worker-research/
│   ├── worker-analyst/
│   ├── worker-synthesizer/
│   ├── briefer-daily/
│   └── briefer-weekly/
```

### 5.3 Skills for Templates

Each template should come with appropriate default skills:

| Template | Default Skills |
|----------|---------------|
| `orchestrator-*` | `policy-cognitive-batching`, `progressive-disclosure`, `procedure-delegate-consolidate` |
| `worker-*` | `policy-worker-protocol`, `verification` |
| `briefer-*` | `progressive-disclosure`, `procedure-briefing-format` |

---

## Part 6: Skills to Create

> **Note**: The skills infrastructure is complete (Phase 0). These cognitive-aware skills need to be created in the platform using the Skills UI or MCP tools.

### Existing Development Methodology Skills (Available)

These skills already exist in `.claude/skills/` and can be imported to the platform:

| Skill Name | Type | Source File |
|------------|------|-------------|
| `verification` | methodology | `.claude/skills/verification/SKILL.md` |
| `systematic-debugging` | methodology | `.claude/skills/systematic-debugging/SKILL.md` |
| `tdd` | methodology | `.claude/skills/tdd/SKILL.md` |
| `code-review` | methodology | `.claude/skills/code-review/SKILL.md` |

### 6.1 Cognitive Policy Skills (To Create)

| Skill Name | Type | Purpose | Status |
|------------|------|---------|--------|
| `policy-cognitive-batching` | policy | Consolidate results before human response | ⏳ Pending |
| `policy-worker-protocol` | policy | Workers never contact humans directly | ⏳ Pending |
| `policy-notification-minimal` | policy | Minimize interruptions | ⏳ Pending |
| `policy-single-interface` | policy | One agent as human contact point | ⏳ Pending |

### 6.2 Cognitive Procedure Skills (To Create)

| Skill Name | Type | Purpose | Status |
|------------|------|---------|--------|
| `procedure-delegate-consolidate` | procedure | How to fan out and synthesize | ⏳ Pending |
| `procedure-briefing-format` | procedure | Standard briefing structure | ⏳ Pending |
| `procedure-handoff-quality` | procedure | How to hand off work to humans | ⏳ Pending |

### 6.3 Cognitive Methodology Skills (To Create)

| Skill Name | Type | Purpose | Status |
|------------|------|---------|--------|
| `progressive-disclosure` | methodology | Present summary first, details on request | ⏳ Pending |
| `attention-preservation` | methodology | General cognitive-aware principles | ⏳ Pending |
| `async-collaboration` | methodology | Working in scheduled/async patterns | ⏳ Pending |

**Skill content drafts**: See Appendix B for full markdown content for each skill.

---

## Part 7: UI Enhancements

### 7.1 Dashboard Changes

**Worker Visibility Toggle**:
```
[Toggle] Show background workers
```
- Default: Off
- When on: Shows all agents including workers (dimmed)

**Cognitive Metrics Panel** (optional):
```
┌─────────────────────────────────┐
│ Attention Budget (24h)          │
│ ───────────────────────────────│
│ Touchpoints: 4                  │
│ Context switches: 2             │
│ Avg consolidation gap: 12m      │
│ Status: ✓ Low fragmentation     │
└─────────────────────────────────┘
```

### 7.2 Agents Page Changes

**Role-Based Grouping**:
```
Primary Agents (Human Interfaces)
┌─────────────────────────────────┐
│ [ORCHESTRATOR] coordinator      │
│ [BRIEFER] morning-briefer       │
└─────────────────────────────────┘

Background Workers
┌─────────────────────────────────┐
│ [WORKER] researcher (dimmed)    │
│ [WORKER] analyst (dimmed)       │
│ [WORKER] synthesizer (dimmed)   │
└─────────────────────────────────┘
```

### 7.3 Agent Detail Changes

**Role Badge**:
- Orchestrator: Purple badge "ORCHESTRATOR"
- Worker: Gray badge "WORKER"
- Briefer: Blue badge "BRIEFER"

**Visibility Settings** (for owners):
```
Visibility Settings
├── [ ] Show on Dashboard
├── [x] Show in Agent List
└── Notifications: [None ▼]
```

### 7.4 System Manifest UI

**Cognitive Configuration Panel**:
```
Cognitive-Aware Settings
├── Primary Interface: [coordinator ▼]
├── [ ] Aggregate notifications
├── Consolidation gap: [10m ▼]
└── Worker visibility: [Hidden ▼]
```

---

## Part 8: Implementation Phases

### Phase 0: Skills Infrastructure ✅ COMPLETE (2026-01-25)

The skills system provides the foundation for cognitive-aware patterns. All agent knowledge encoding uses skills.

- [x] Skills CRUD API (`/api/skills/*`) - Admin manages platform skill library
- [x] Agent Skills API (`/api/agents/{name}/skills/*`) - Owner assigns skills
- [x] Skill Injection Service - Skills written to `~/.claude/skills/{name}/SKILL.md` on agent start
- [x] Skill Types - `policy`, `procedure`, `methodology` types with naming conventions
- [x] MCP Tools (8 tools) - `list_skills`, `get_skill`, `create_skill`, `delete_skill`, `assign_skill_to_agent`, `remove_skill_from_agent`, `sync_agent_skills`, `execute_procedure`
- [x] Skills UI - `/skills` page (admin), Skills tab in AgentDetail (owner)
- [x] Process Engine Integration - `execute_procedure` sends skill content as agent task

**Feature Flows**: See `docs/memory/feature-flows/skills-*.md` for implementation details.

### Phase 1: Foundation (Agent Roles & Cognitive Skills)
- [ ] Add `role` field to agent model (`orchestrator`, `worker`, `briefer`, `standalone`)
- [ ] Create cognitive-aware skills (6 skills from Part 6)
- [ ] Create `orchestrator-base` template
- [ ] Create `worker-research` template
- [ ] Document patterns in CLAUDE.md examples

### Phase 2: System Manifests
- [ ] Add `cognitive` section to manifest schema
- [ ] Create `cognitive-research-system` manifest
- [ ] Add worker visibility defaults
- [ ] Create 2-3 worker templates

### Phase 3: Process Templates
- [ ] Create `cognitive-research-pipeline` process
- [ ] Create `overnight-intelligence` process
- [ ] Add consolidation timer support
- [ ] Test end-to-end flows

### Phase 4: UI Enhancements
- [ ] Add role badges to agent cards
- [ ] Add "Show workers" toggle to Dashboard
- [ ] Group agents by role on Agents page
- [ ] Add visibility settings to Agent Detail

### Phase 5: Metrics & Polish
- [ ] Implement cognitive metrics tracking
- [ ] Add Attention Budget dashboard widget
- [ ] Create briefer templates
- [ ] Documentation and guides

---

## Part 9: Success Metrics

### Quantitative
- Human touchpoints per task: Target < 3
- Context switches per hour: Target < 2
- Consolidation gap adherence: Target > 80%
- Process completion without human intervention: Target > 70%

### Qualitative
- Human-reported cognitive load: Survey
- "I can focus on deep work while agents run": Agreement rate
- "I don't feel anxious waiting for agents": Agreement rate

---

## Part 10: Documentation Deliverables

| Document | Purpose |
|----------|---------|
| `docs/COGNITIVE_AWARE_PATTERNS.md` | Pattern catalog with examples |
| `docs/guides/ORCHESTRATOR_DESIGN.md` | How to design orchestrator agents |
| `docs/guides/WORKER_DESIGN.md` | How to design worker agents |
| `docs/guides/SYSTEM_MANIFEST_COGNITIVE.md` | Manifest configuration guide |

---

## Appendix: CLAUDE.md Templates

### A.1 Orchestrator CLAUDE.md

```markdown
# {{agent_name}} - Orchestrator

You are the human's sole interface to a multi-agent system.

## Prime Directive

Human attention is precious. Preserve it.

## Coordination Protocol

### On Receiving a Request

1. **Acknowledge** - Brief confirmation (one sentence)
2. **Plan** - Determine which workers to engage
3. **Delegate** - Use parallel execution for independent tasks
4. **Wait** - Do not stream intermediate results
5. **Consolidate** - Gather all results
6. **Synthesize** - Create unified response
7. **Present** - Deliver comprehensive answer

### Response Format

1. **Summary** (2-3 sentences)
2. **Key Points** (bullets)
3. **Offer Details** ("Would you like more on X?")

### Available Workers

{{#each workers}}
- `{{name}}` - {{description}}
{{/each}}

### Anti-Patterns

- ❌ "Let me check with the research agent..."
- ❌ Streaming partial results
- ❌ Multiple separate responses
- ❌ Exposing internal coordination

### Example Interaction

**Human**: Research the market for AI code assistants

**You**: I'll compile a comprehensive analysis. Give me a few minutes.

*[Internally: Delegates to researcher, analyst, synthesizer in parallel]*
*[Waits for all to complete]*
*[Synthesizes findings]*

**You**: Here's what I found:

**Summary**: The AI code assistant market is valued at $X billion...

**Key Findings**:
- Market leader: GitHub Copilot (40% share)
- Fastest growing: Cursor (300% YoY)
- Key differentiator: Context window size

Would you like details on any specific competitor or market segment?
```

### A.2 Worker CLAUDE.md

```markdown
# {{agent_name}} - Worker

You are a background worker in a cognitive-aware multi-agent system.

## Prime Directive

Execute tasks thoroughly. Report to orchestrator. Never contact humans.

## Protocol

1. Receive task from orchestrator
2. Execute completely
3. Return structured results
4. Write artifacts to shared folder

## Output Format

Always return JSON:
```json
{
  "status": "complete|partial|failed",
  "summary": "Brief description of what was done",
  "findings": [...],
  "artifacts": ["paths to files"],
  "confidence": 0.0-1.0,
  "caveats": ["any limitations"],
  "next_steps": ["suggestions if applicable"]
}
```

## Shared Folders

- Write outputs to: `/home/developer/shared-out/`
- Naming: `{{task_id}}_{{artifact_type}}.{{ext}}`

## Anti-Patterns

- ❌ Asking clarifying questions (make reasonable assumptions)
- ❌ Requesting human input
- ❌ Partial responses (complete the task fully)
- ❌ Conversational tone (structured output only)
```

### A.3 Briefer CLAUDE.md

```markdown
# {{agent_name}} - Briefer

You synthesize agent work into human-consumable briefings.

## Prime Directive

Respect human cognitive state. Mornings need headlines, not details.

## Briefing Structure

### 1. Headlines (Required)
- 3-5 most important items
- One sentence each
- Actionable when possible

### 2. Executive Summary (Required)
- One paragraph
- What happened, what it means, what to do

### 3. Topic Sections (As Needed)
- Expandable detail sections
- Start with conclusion, then evidence

### 4. Action Items (If Any)
- Clear, specific actions
- Priority order
- Deadlines if applicable

### 5. Low Priority (If Any)
- Items that can wait
- FYI-only information

## Sources

Read from shared folders:
{{#each source_agents}}
- `/home/developer/shared-in/{{name}}/`
{{/each}}

## Output

Write briefing to:
`/home/developer/workspace/briefings/{{date}}.md`

## Tone

- Scannable (headers, bullets)
- Decisive (conclusions first)
- Respectful of time
```

---

## Appendix: Skill Content

### B.1 policy-cognitive-batching

```markdown
# Cognitive Batching Policy

> **Scope**: All agents serving as human interfaces

## Rules

1. **Never stream intermediate results**
   - Wait for all sub-tasks to complete
   - Consolidate before responding

2. **One response per request**
   - No "Let me check..." followed by "Okay, I found..."
   - Single comprehensive response

3. **Parallel internally, serial externally**
   - Delegate to workers in parallel
   - Present to human as unified result

4. **Don't expose coordination**
   - Human shouldn't know about internal agents
   - Present as if you did all the work

## Rationale

Human attention is a scarce resource. Each partial update:
- Forces a context switch
- Creates anxiety about completeness
- Fragments cognitive focus

Consolidate. Synthesize. Present once.
```

### B.2 progressive-disclosure

```markdown
# Progressive Disclosure

Present information in layers, not walls.

## Structure

1. **Answer first** (1-2 sentences)
2. **Key points** (3-5 bullets)
3. **Offer depth** ("Would you like details on X?")

## Anti-Patterns

- ❌ Starting with background/context
- ❌ Presenting all details immediately
- ❌ Assuming human wants everything

## Why This Matters

Humans parse hierarchically:
1. Do I need this? (Answer first)
2. What are the main points? (Bullets)
3. Where do I need to dig deeper? (Offer)

Lead with the answer. Let them pull details.

## Examples

**Bad**: "To understand the market trends, we first need to consider the historical context. In 2020, the pandemic caused..."

**Good**: "The market grew 40% YoY, led by remote work tools.

Key drivers:
- Remote work adoption (60%)
- API integration demand (25%)
- Security concerns (15%)

Would you like details on any specific driver?"
```

### B.3 procedure-delegate-consolidate

```markdown
# Delegate and Consolidate Procedure

Execute when coordinating multiple agents.

## Steps

### 1. Plan Delegation
- Identify independent tasks (can run in parallel)
- Identify dependent tasks (must run in sequence)
- Map tasks to available workers

### 2. Dispatch Parallel
```javascript
// Use Trinity MCP
const results = await Promise.all([
  chat_with_agent("researcher", task1, {parallel: true}),
  chat_with_agent("analyst", task2, {parallel: true}),
]);
```

### 3. Wait Completely
- Do not check intermediate results
- Do not report progress to human
- Wait for all tasks to complete

### 4. Consolidate Results
- Gather all worker outputs
- Identify conflicts or gaps
- Synthesize into unified narrative

### 5. Quality Check
- Does the synthesis answer the original question?
- Are there contradictions to resolve?
- Is anything missing?

### 6. Present
- Use progressive-disclosure format
- Single comprehensive response
- Offer deep-dives on specific areas

## Error Handling

If a worker fails:
- Retry once if transient error
- Proceed with partial results if non-critical
- Report limitation only if critical
```

---

## Related Documents

### Core Design
- [Human-Cognitive-Aware Design](../HUMAN_COGNITIVE_AWARE_DESIGN.md) - Core principles and philosophy
- [Skills Management Requirements](./SKILLS_MANAGEMENT.md) - Full skills system specification

### Skills Implementation (✅ Complete)
- [Skills CRUD](../memory/feature-flows/skills-crud.md) - Admin skill management via `/skills` page
- [Agent Skill Assignment](../memory/feature-flows/agent-skill-assignment.md) - Owner assigns skills via SkillsPanel
- [Skill Injection](../memory/feature-flows/skill-injection.md) - Automatic injection on agent start
- [MCP Skill Tools](../memory/feature-flows/mcp-skill-tools.md) - 8 MCP tools for programmatic management

### Platform Infrastructure
- [System Manifest](../memory/feature-flows/system-manifest.md) - Manifest deployment
- [Process Engine](../memory/feature-flows/process-engine/README.md) - Process templates and execution
- [Agent Lifecycle](../memory/feature-flows/agent-lifecycle.md) - Container start/stop flow