# Process Engine Roadmap

> **Purpose**: Test the Process Engine with diverse real-world processes to identify architectural and UX bottlenecks
> **Reference**: `PROCESS_DRIVEN_THINKING_IT5.md` (scale, reliability, enterprise considerations)
> **Date**: 2026-01-16

---

## Strategy

Rather than theoretical improvements, we'll **build real processes** across different domains and patterns to:
1. **Discover architectural limits** — Where does the engine struggle?
2. **Expose UX friction** — Where do users get confused?
3. **Validate assumptions** — Do our step types cover real needs?
4. **Stress test at scale** — What breaks with concurrent execution?

**Each process category tests specific aspects of the platform.**

---

## Phase 1: Foundation Processes (Sequential + Basic)

These processes validate core functionality works correctly before adding complexity.

### P1.1 — Simple Content Pipeline

| Aspect | Value |
|--------|-------|
| **Steps** | 3 sequential agent_task steps |
| **Agents** | 3 different agents |
| **Duration** | ~5-10 minutes |
| **Tests** | Basic orchestration, output passing |

```yaml
name: simple-content-pipeline
steps:
  - id: research
    type: agent_task
    agent: researcher
    message: "Research the topic: {{input.topic}}"

  - id: write
    type: agent_task
    agent: writer
    depends_on: [research]
    message: "Write article using: {{steps.research.output}}"

  - id: review
    type: agent_task
    agent: editor
    depends_on: [write]
    message: "Review and improve: {{steps.write.output}}"
```

**Bottlenecks to Watch**:
- [ ] Output variable passing between steps (template syntax)
- [ ] Error messages when agent is unavailable
- [ ] Progress visibility during long agent tasks

---

### P1.2 — Approval Gate Pipeline

| Aspect | Value |
|--------|-------|
| **Steps** | 2 agent_task + 1 human_approval + 1 conditional |
| **Duration** | Variable (depends on human) |
| **Tests** | Human approval flow, timeout handling, conditional logic |

```yaml
name: content-with-approval
steps:
  - id: draft
    type: agent_task
    agent: writer
    message: "Write first draft about {{input.topic}}"

  - id: review-gate
    type: human_approval
    depends_on: [draft]
    title: "Content Review Required"
    description: "Please review the draft for quality and accuracy"
    timeout: 24h
    approvers: ["editor@company.com"]

  - id: publish
    type: agent_task
    depends_on: [review-gate]
    agent: publisher
    condition: "{{steps.review-gate.decision}} == 'approved'"
    message: "Publish: {{steps.draft.output}}"

  - id: revise
    type: agent_task
    depends_on: [review-gate]
    agent: writer
    condition: "{{steps.review-gate.decision}} == 'rejected'"
    message: "Revise based on feedback: {{steps.review-gate.comment}}"
```

**Bottlenecks to Watch**:
- [ ] Approval notification delivery (how do approvers know?)
- [ ] Timeout behavior (does execution fail gracefully?)
- [ ] Conditional branching UX (is it clear why a step was skipped?)
- [ ] Approval inbox findability

---

### P1.3 — Scheduled Daily Report

| Aspect | Value |
|--------|-------|
| **Trigger** | Cron schedule (daily 9am) |
| **Steps** | 3 sequential |
| **Tests** | Scheduling, timezone handling, unattended execution |

```yaml
name: daily-metrics-report
trigger:
  type: schedule
  cron: "0 9 * * *"
  timezone: "America/New_York"

steps:
  - id: gather
    type: agent_task
    agent: data-collector
    message: "Gather yesterday's metrics from all sources"

  - id: analyze
    type: agent_task
    agent: analyst
    depends_on: [gather]
    message: "Analyze trends and anomalies in: {{steps.gather.output}}"

  - id: report
    type: agent_task
    agent: reporter
    depends_on: [analyze]
    message: "Generate executive summary from: {{steps.analyze.output}}"
```

**Bottlenecks to Watch**:
- [ ] Schedule UI (is cron readable? timezone picker UX?)
- [ ] Unattended failure handling (who gets notified?)
- [ ] Execution history for scheduled processes
- [ ] Disabling/pausing schedules

---

## Phase 2: Parallel & Complex Patterns

Test advanced orchestration capabilities.

### P2.1 — Parallel Research Pipeline

| Aspect | Value |
|--------|-------|
| **Steps** | 4 parallel + 1 aggregation |
| **Agents** | 4 researcher agents running simultaneously |
| **Tests** | Parallel execution, result aggregation, resource contention |

```yaml
name: multi-source-research
steps:
  # These 4 run in parallel (no dependencies)
  - id: research-academic
    type: agent_task
    agent: academic-researcher
    message: "Find academic papers about {{input.topic}}"

  - id: research-news
    type: agent_task
    agent: news-researcher
    message: "Find recent news about {{input.topic}}"

  - id: research-social
    type: agent_task
    agent: social-researcher
    message: "Find social media discussions about {{input.topic}}"

  - id: research-industry
    type: agent_task
    agent: industry-researcher
    message: "Find industry reports about {{input.topic}}"

  # Aggregation step waits for all parallel steps
  - id: synthesize
    type: agent_task
    agent: synthesizer
    depends_on: [research-academic, research-news, research-social, research-industry]
    message: |
      Synthesize findings from:
      - Academic: {{steps.research-academic.output}}
      - News: {{steps.research-news.output}}
      - Social: {{steps.research-social.output}}
      - Industry: {{steps.research-industry.output}}
```

**Bottlenecks to Watch**:
- [ ] UI visualization of parallel branches
- [ ] Progress indication (4 things at once)
- [ ] Memory/resource usage with 4 concurrent agents
- [ ] What happens if 1 of 4 fails? (partial results?)
- [ ] Aggregation step message length limits

---

### P2.2 — Diamond Dependency Pattern

| Aspect | Value |
|--------|-------|
| **Pattern** | Fork → parallel → join |
| **Tests** | Complex dependency resolution, timing |

```yaml
name: diamond-pattern
steps:
  - id: start
    type: agent_task
    agent: coordinator
    message: "Initialize workflow for {{input.request}}"

  # Fork: two parallel paths
  - id: path-a
    type: agent_task
    agent: specialist-a
    depends_on: [start]
    message: "Process via method A: {{steps.start.output}}"

  - id: path-b
    type: agent_task
    agent: specialist-b
    depends_on: [start]
    message: "Process via method B: {{steps.start.output}}"

  # Join: wait for both
  - id: merge
    type: agent_task
    agent: coordinator
    depends_on: [path-a, path-b]
    message: |
      Merge results:
      - Method A: {{steps.path-a.output}}
      - Method B: {{steps.path-b.output}}
```

**Bottlenecks to Watch**:
- [ ] Dependency graph visualization clarity
- [ ] Join timing (what if path-a takes 10x longer than path-b?)
- [ ] UI showing "waiting for other branch"

---

### P2.3 — Nested Sub-Process

| Aspect | Value |
|--------|-------|
| **Depth** | Parent calls child process |
| **Tests** | Sub-process invocation, input/output mapping, breadcrumbs |

**Parent Process:**
```yaml
name: customer-onboarding-main
steps:
  - id: validate-customer
    type: agent_task
    agent: validator
    message: "Validate customer data: {{input.customer_data}}"

  - id: setup-account
    type: sub_process
    depends_on: [validate-customer]
    process: account-setup-subprocess
    input_mapping:
      customer_id: "{{steps.validate-customer.output.customer_id}}"
      tier: "{{input.subscription_tier}}"

  - id: welcome
    type: agent_task
    depends_on: [setup-account]
    agent: communicator
    message: "Send welcome to {{steps.setup-account.output.email}}"
```

**Child Process:**
```yaml
name: account-setup-subprocess
steps:
  - id: create-account
    type: agent_task
    agent: account-creator
    message: "Create account for customer {{input.customer_id}}"

  - id: configure-tier
    type: agent_task
    agent: configurator
    depends_on: [create-account]
    message: "Configure {{input.tier}} tier for {{steps.create-account.output.account_id}}"
```

**Bottlenecks to Watch**:
- [ ] Sub-process discovery (where do I define the child?)
- [ ] Input/output mapping UX (complex template syntax)
- [ ] Breadcrumb navigation clarity
- [ ] Cost aggregation (parent includes child costs?)
- [ ] Error propagation (child fails → parent status?)

---

## Phase 3: Real-World Business Processes

Test realistic scenarios that exercise multiple features simultaneously.

### P3.1 — Marketing Campaign Launch

| Aspect | Value |
|--------|-------|
| **Steps** | 8 steps with mixed types |
| **Duration** | Hours to days |
| **Complexity** | Multiple approvals, conditional branching, notifications |

```yaml
name: marketing-campaign-launch
trigger:
  type: manual

steps:
  - id: brief-analysis
    type: agent_task
    agent: marketing-strategist
    message: "Analyze campaign brief: {{input.brief}}"

  - id: creative-development
    type: agent_task
    agent: creative-director
    depends_on: [brief-analysis]
    message: "Develop creative concepts based on: {{steps.brief-analysis.output}}"
    roles:
      informed: [marketing-manager]

  - id: creative-approval
    type: human_approval
    depends_on: [creative-development]
    title: "Creative Approval"
    description: "Review creative concepts for brand alignment"
    timeout: 48h
    approvers: ["brand-manager@company.com"]

  - id: budget-calculation
    type: agent_task
    depends_on: [creative-approval]
    condition: "{{steps.creative-approval.decision}} == 'approved'"
    agent: financial-analyst
    message: "Calculate budget for campaign"

  - id: budget-approval
    type: human_approval
    depends_on: [budget-calculation]
    title: "Budget Approval - ${{steps.budget-calculation.output.total}}"
    timeout: 24h
    approvers: ["finance-director@company.com"]

  - id: asset-creation
    type: agent_task
    depends_on: [budget-approval]
    condition: "{{steps.budget-approval.decision}} == 'approved'"
    agent: content-creator
    message: "Create campaign assets"
    roles:
      monitors: [quality-reviewer]

  - id: launch-notification
    type: notification
    depends_on: [asset-creation]
    channels: [slack, email]
    message: "Campaign '{{input.campaign_name}}' ready for launch!"
    recipients: ["marketing-team"]

  - id: schedule-posts
    type: agent_task
    depends_on: [asset-creation]
    agent: social-scheduler
    message: "Schedule social media posts for {{input.launch_date}}"
```

**Bottlenecks to Watch**:
- [ ] Long-running process visibility (hours/days)
- [ ] Multiple approval sequence (approval fatigue?)
- [ ] Conditional branching after rejection (restart vs revise)
- [ ] Notification delivery reliability
- [ ] Process cancellation mid-flight
- [ ] Cost tracking across many steps

---

### P3.2 — Customer Support Escalation

| Aspect | Value |
|--------|-------|
| **Pattern** | Event-driven feel, rapid iteration |
| **Complexity** | Gateway conditions, timer delays, multiple outcomes |

```yaml
name: support-ticket-escalation
steps:
  - id: initial-analysis
    type: agent_task
    agent: support-ai
    message: "Analyze support ticket: {{input.ticket}}"

  - id: complexity-check
    type: gateway
    depends_on: [initial-analysis]
    conditions:
      - condition: "{{steps.initial-analysis.output.complexity}} == 'simple'"
        next_step: auto-resolve
      - condition: "{{steps.initial-analysis.output.complexity}} == 'medium'"
        next_step: human-review
      - condition: "{{steps.initial-analysis.output.complexity}} == 'complex'"
        next_step: specialist-escalation

  - id: auto-resolve
    type: agent_task
    agent: support-ai
    message: "Generate and send resolution for: {{input.ticket}}"
    roles:
      informed: [support-lead]

  - id: human-review
    type: human_approval
    title: "Support Ticket Review"
    timeout: 2h
    approvers: ["support-team"]

  - id: specialist-escalation
    type: agent_task
    agent: escalation-coordinator
    message: "Escalate to specialist team: {{input.ticket}}"

  - id: wait-for-resolution
    type: timer
    depends_on: [specialist-escalation]
    duration: 4h

  - id: check-resolution
    type: agent_task
    depends_on: [wait-for-resolution]
    agent: support-ai
    message: "Check if ticket {{input.ticket_id}} has been resolved"

  - id: resolution-gate
    type: gateway
    depends_on: [check-resolution]
    conditions:
      - condition: "{{steps.check-resolution.output.resolved}} == true"
        next_step: close-ticket
      - condition: "{{steps.check-resolution.output.resolved}} == false"
        next_step: manager-escalation

  - id: close-ticket
    type: agent_task
    agent: support-ai
    message: "Close ticket and send satisfaction survey"

  - id: manager-escalation
    type: notification
    channels: [slack, pagerduty]
    message: "URGENT: Ticket {{input.ticket_id}} unresolved after 4 hours"
    recipients: ["support-manager"]
```

**Bottlenecks to Watch**:
- [ ] Gateway visualization (multiple branches)
- [ ] Timer UX (is it clear process is waiting?)
- [ ] Loop detection (what if check-resolution loops?)
- [ ] Short timeout approvals (2h vs 48h)
- [ ] Multiple end points in a process

---

### P3.3 — Financial Report Generation

| Aspect | Value |
|--------|-------|
| **Complexity** | Data-heavy, compliance-sensitive |
| **Tests** | Cost tracking, error handling, audit trail |

```yaml
name: quarterly-financial-report
config:
  data_classification: confidential
  max_cost: 50.00

trigger:
  type: schedule
  cron: "0 6 1 */3 *"  # First day of each quarter at 6am
  timezone: "UTC"

steps:
  - id: data-extraction
    type: agent_task
    agent: data-engineer
    message: "Extract Q{{input.quarter}} financial data from all systems"
    retry:
      max_attempts: 3
      backoff: exponential

  - id: validation
    type: agent_task
    agent: data-validator
    depends_on: [data-extraction]
    message: "Validate data integrity and flag anomalies"
    roles:
      monitors: [finance-lead]

  - id: analysis
    type: agent_task
    agent: financial-analyst
    depends_on: [validation]
    message: "Perform financial analysis and generate insights"

  - id: report-draft
    type: agent_task
    agent: report-writer
    depends_on: [analysis]
    message: "Generate quarterly report draft"

  - id: compliance-review
    type: human_approval
    depends_on: [report-draft]
    title: "Compliance Review - Q{{input.quarter}} Report"
    description: "Verify regulatory compliance of financial statements"
    timeout: 72h
    approvers: ["compliance-officer@company.com"]

  - id: cfo-approval
    type: human_approval
    depends_on: [compliance-review]
    condition: "{{steps.compliance-review.decision}} == 'approved'"
    title: "CFO Final Approval"
    timeout: 48h
    approvers: ["cfo@company.com"]

  - id: publish
    type: agent_task
    depends_on: [cfo-approval]
    condition: "{{steps.cfo-approval.decision}} == 'approved'"
    agent: publisher
    message: "Publish Q{{input.quarter}} report to stakeholders"
    roles:
      informed: [board-members, investors]
```

**Bottlenecks to Watch**:
- [ ] Cost limit enforcement (stops at $50?)
- [ ] Data classification handling (confidential label effects?)
- [ ] Audit trail completeness
- [ ] Retry configuration UX
- [ ] Multi-level approval chain
- [ ] Informed notification to external parties

---

## Phase 4: Stress & Edge Cases

Push the platform to find breaking points.

### P4.1 — High-Concurrency Batch

| Aspect | Value |
|--------|-------|
| **Pattern** | 10 parallel agent tasks |
| **Tests** | Resource limits, queue behavior, UI performance |

```yaml
name: parallel-stress-test
steps:
  # 10 parallel steps using the same agent (queue test)
  - id: task-01
    type: agent_task
    agent: worker
    message: "Process item 1"
  - id: task-02
    type: agent_task
    agent: worker
    message: "Process item 2"
  # ... (8 more identical steps)
  - id: task-10
    type: agent_task
    agent: worker
    message: "Process item 10"

  - id: aggregate
    type: agent_task
    agent: aggregator
    depends_on: [task-01, task-02, task-03, task-04, task-05,
                 task-06, task-07, task-08, task-09, task-10]
    message: "Aggregate all results"
```

**Bottlenecks to Watch**:
- [ ] Agent queue behavior (fairness, ordering)
- [ ] UI performance with 10+ active steps
- [ ] WebSocket event flood
- [ ] Memory usage
- [ ] Timeout handling (what if one hangs?)

---

### P4.2 — Long-Running Timer Process

| Aspect | Value |
|--------|-------|
| **Duration** | 24+ hours |
| **Tests** | Timer reliability, state persistence, recovery |

```yaml
name: long-timer-test
steps:
  - id: start
    type: agent_task
    agent: coordinator
    message: "Initialize long-running process"

  - id: wait-12h
    type: timer
    depends_on: [start]
    duration: 12h

  - id: checkpoint-1
    type: agent_task
    agent: coordinator
    depends_on: [wait-12h]
    message: "12-hour checkpoint"

  - id: wait-12h-more
    type: timer
    depends_on: [checkpoint-1]
    duration: 12h

  - id: final
    type: agent_task
    agent: coordinator
    depends_on: [wait-12h-more]
    message: "Process complete after 24h"
```

**Bottlenecks to Watch**:
- [ ] Timer survives backend restart?
- [ ] UI shows time remaining?
- [ ] Execution list shows "waiting" status clearly?
- [ ] What happens if server clock drifts?

---

### P4.3 — Deep Nesting (3 Levels)

| Aspect | Value |
|--------|-------|
| **Depth** | Parent → Child → Grandchild |
| **Tests** | Deep sub-process navigation, cost roll-up |

**Grandparent:**
```yaml
name: level-1-parent
steps:
  - id: call-child
    type: sub_process
    process: level-2-child
```

**Child:**
```yaml
name: level-2-child
steps:
  - id: work
    type: agent_task
    agent: worker
    message: "Do work at level 2"
  - id: call-grandchild
    type: sub_process
    depends_on: [work]
    process: level-3-grandchild
```

**Grandchild:**
```yaml
name: level-3-grandchild
steps:
  - id: deep-work
    type: agent_task
    agent: worker
    message: "Do work at level 3"
```

**Bottlenecks to Watch**:
- [ ] Breadcrumb navigation at 3 levels
- [ ] Cost aggregation accuracy
- [ ] Error propagation chain
- [ ] Execution list showing hierarchy
- [ ] Performance with nested queries

---

### P4.4 — Error Recovery Test

| Aspect | Value |
|--------|-------|
| **Pattern** | Intentionally failing steps |
| **Tests** | Retry behavior, error UX, recovery options |

```yaml
name: error-recovery-test
steps:
  - id: will-fail
    type: agent_task
    agent: unreliable-agent  # This agent will fail sometimes
    message: "This might fail"
    retry:
      max_attempts: 3
      backoff: exponential
      initial_delay: 5s

  - id: after-failure
    type: agent_task
    agent: worker
    depends_on: [will-fail]
    message: "Continue after failure handling"
```

**Bottlenecks to Watch**:
- [ ] Retry countdown visibility
- [ ] Error message clarity
- [ ] Manual retry option after exhaustion
- [ ] Partial execution state clarity

---

## Phase 5: Multi-Process Scenarios

Test processes running simultaneously and interacting.

### P5.1 — Competing for Same Agent

| Aspect | Value |
|--------|-------|
| **Pattern** | 3 different processes, all need same agent |
| **Tests** | Queue fairness, starvation prevention |

**Run simultaneously:**
1. `simple-content-pipeline` (uses writer agent)
2. `content-with-approval` (uses writer agent)
3. `daily-metrics-report` (uses reporter agent)

**Bottlenecks to Watch**:
- [ ] Does one process starve another?
- [ ] Is queue position visible?
- [ ] Can user prioritize one execution?

---

### P5.2 — Cascading Schedules

| Aspect | Value |
|--------|-------|
| **Pattern** | 5 scheduled processes all trigger at same time |
| **Tests** | Schedule collision handling, resource contention |

Configure 5 different processes all scheduled for "0 9 * * *" (9am daily).

**Bottlenecks to Watch**:
- [ ] Do they all start or queue?
- [ ] Is there schedule jitter option?
- [ ] Dashboard shows schedule collision warning?

---

## Phase 6: In-App Documentation & Onboarding

Build user guidance directly into the Processes UI.

> **Reference**: IT5 Section 3 — User Onboarding Patterns

### P6.1 — Documentation Tab

Add a **"Docs" tab** in the Processes navigation alongside List, Dashboard, Approvals.

| Component | Description |
|-----------|-------------|
| **Location** | `/processes/docs` as new route |
| **Content** | Markdown-rendered guides |
| **Search** | Full-text search across docs |

**Content Structure:**

```
Docs Tab
├── Getting Started
│   ├── What are Processes?
│   ├── Your First Process (5-minute tutorial)
│   └── Understanding Step Types
├── Step Type Reference
│   ├── agent_task — AI agent execution
│   ├── human_approval — Approval gates
│   ├── gateway — Conditional branching
│   ├── timer — Delays and waits
│   ├── notification — Alerts and messages
│   └── sub_process — Nested workflows
├── YAML Reference
│   ├── Process Definition Schema
│   ├── Variable Interpolation ({{...}})
│   ├── Trigger Configuration
│   └── Retry & Error Handling
├── Patterns & Examples
│   ├── Sequential Pipeline
│   ├── Parallel Execution
│   ├── Approval Workflows
│   ├── Scheduled Reports
│   └── Multi-Level Sub-Processes
└── Troubleshooting
    ├── Common Errors
    ├── Why is my step stuck?
    └── Cost Optimization Tips
```

**Implementation Notes:**
- Store docs as `.md` files in `config/process-docs/` or similar
- Render with `vue-markdown` or similar library
- Include copy-paste YAML snippets
- Link from error messages to relevant troubleshooting docs

**Bottlenecks to Watch**:
- [ ] Docs discoverability (do users find the tab?)
- [ ] Search effectiveness
- [ ] Code snippet copy UX
- [ ] Keeping docs in sync with features

---

### P6.2 — Contextual Help

Add **inline help** throughout the Process Editor and Execution views.

| Location | Help Type | Content |
|----------|-----------|---------|
| Step type dropdown | Tooltip | Brief description of each type |
| YAML editor | Sidebar hints | Schema hints based on cursor position |
| Validation errors | Links | "Learn more" links to docs |
| Execution detail | Explainers | "Why is this step waiting?" |

**Examples:**

```
┌─────────────────────────────────────────────────────────────────┐
│ Step Type: [gateway ▾]                                          │
│            ┌──────────────────────────────────────────────────┐ │
│            │ Gateway                                          │ │
│            │ ────────                                         │ │
│            │ Routes execution to different paths based on     │ │
│            │ conditions. Like an "if/else" in code.           │ │
│            │                                                  │ │
│            │ [See examples →]                                 │ │
│            └──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**YAML Editor Sidebar:**
```
┌─────────────────────────┬──────────────────────────────────────┐
│ YAML Editor             │ Help                                 │
├─────────────────────────┼──────────────────────────────────────┤
│ steps:                  │ ℹ️ depends_on                         │
│   - id: analyze         │ ──────────────                       │
│     type: agent_task    │ List of step IDs that must complete  │
│     depends_on: [fetch] │ before this step starts.             │
│     agent: analyst      │                                      │
│     message: |          │ Example:                             │
│       Analyze the...    │   depends_on: [step-a, step-b]       │
│                    ▲    │                                      │
│              cursor     │ Steps without depends_on run in      │
│                         │ parallel at process start.           │
│                         │                                      │
│                         │ [Full reference →]                   │
└─────────────────────────┴──────────────────────────────────────┘
```

**Bottlenecks to Watch**:
- [ ] Help doesn't obstruct workflow
- [ ] Cursor-position detection accuracy in YAML
- [ ] Help panel dismissability
- [ ] Mobile/narrow screen layout

---

### P6.3 — Empty State Guidance

Provide clear guidance when users encounter empty states.

| Empty State | Current | Improved |
|-------------|---------|----------|
| No processes | Generic "No processes" | "Create your first process" CTA + template cards |
| No executions | "No executions" | "Run this process" button + what to expect |
| No approvals | "No pending approvals" | Explanation + how approvals work |

**First Process Empty State:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                         🚀 Create Your First Process                         │
│                                                                              │
│  Processes automate multi-step workflows using your AI agents.              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │   Quick Start Templates                                             │    │
│  │   ─────────────────────                                             │    │
│  │                                                                     │    │
│  │   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │    │
│  │   │ Content       │  │ Data          │  │ Support       │          │    │
│  │   │ Pipeline      │  │ Report        │  │ Escalation    │          │    │
│  │   │               │  │               │  │               │          │    │
│  │   │ Write→Review  │  │ Gather→       │  │ Triage→       │          │    │
│  │   │ →Publish      │  │ Analyze→Report│  │ Route→Resolve │          │    │
│  │   │               │  │               │  │               │          │    │
│  │   │ [Use →]       │  │ [Use →]       │  │ [Use →]       │          │    │
│  │   └───────────────┘  └───────────────┘  └───────────────┘          │    │
│  │                                                                     │    │
│  │   Or: [Create from Scratch]  [Import YAML]                         │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  📖 New to Processes? [Read the 5-minute guide →]                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Never-Run Process State:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  weekly-sales-report                                          [Edit] [Run]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                      ⏸️ This process hasn't been run yet                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │   What will happen when you run it:                                 │    │
│  │                                                                     │    │
│  │   1. 📥 Gather Data (researcher) ─────────────── ~2-5 min          │    │
│  │   2. 📊 Analyze Trends (analyst) ─────────────── ~5-10 min         │    │
│  │   3. 📝 Generate Report (writer) ─────────────── ~3-5 min          │    │
│  │                                                                     │    │
│  │   Estimated total: 10-20 minutes                                    │    │
│  │   Estimated cost: $2-4                                              │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│                    [▶ Run Now]    [Schedule First Run]                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Bottlenecks to Watch**:
- [ ] Template cards lead to success (not confusion)
- [ ] Time/cost estimates accuracy
- [ ] Users understand "Run" vs "Schedule"

---

### P6.4 — Onboarding Wizard

Optional guided wizard for first-time process creation.

**Trigger**: First visit to Processes section, or "Create Process" with no prior processes.

**Flow:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 1 of 4: What do you want to automate?                      [Skip →]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Choose the type of workflow you want to create:                            │
│                                                                              │
│  ○ Content Creation                                                          │
│    Research → Write → Review → Publish                                       │
│                                                                              │
│  ○ Data Processing                                                           │
│    Collect → Transform → Analyze → Report                                    │
│                                                                              │
│  ○ Approval Workflow                                                         │
│    Request → Review → Approve/Reject → Notify                                │
│                                                                              │
│  ○ Customer Operations                                                       │
│    Receive → Triage → Process → Respond                                      │
│                                                                              │
│  ○ Something else (start from scratch)                                       │
│                                                                              │
│                                              [Back]  [Next: Choose Agents →] │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 2 of 4: Select your agents                                 [Skip →]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Which agents will perform each step?                                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Step: Research                                                     │    │
│  │  Agent: [▾ Select agent...]                                         │    │
│  │         ┌────────────────────────────────┐                          │    │
│  │         │ researcher        ✓ Running    │                          │    │
│  │         │ content-agent     ✓ Running    │                          │    │
│  │         │ data-analyst      ○ Stopped    │                          │    │
│  │         │ + Create new agent...          │                          │    │
│  │         └────────────────────────────────┘                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ⚠️ Some agents are stopped. Processes work best with running agents.        │
│                                                                              │
│                                        [Back]  [Next: Add Approvals? →]      │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 3 of 4: Human checkpoints                                  [Skip →]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Do you need human approval at any point?                                    │
│                                                                              │
│  ☑ Yes, add an approval step                                                 │
│                                                                              │
│    Where should the approval happen?                                         │
│    ○ After first draft (before publish)                                      │
│    ○ At the end (final review)                                               │
│    ○ Let me customize later                                                  │
│                                                                              │
│    Who can approve?                                                          │
│    [editor@company.com                                    ] [+ Add more]     │
│                                                                              │
│  ☐ No, fully automated                                                       │
│                                                                              │
│                                            [Back]  [Next: Review & Create →] │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 4 of 4: Review your process                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Name: [my-content-pipeline                    ]                             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Your workflow:                                                     │    │
│  │                                                                     │    │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │    │
│  │  │ Research │ →  │  Write   │ →  │ Approval │ →  │ Publish  │      │    │
│  │  │researcher│    │  writer  │    │  Human   │    │publisher │      │    │
│  │  └──────────┘    └──────────┘    └──────────┘    └──────────┘      │    │
│  │                                                                     │    │
│  │  Estimated time: 15-25 minutes                                      │    │
│  │  Estimated cost: $3-5 (plus approval wait time)                     │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ☑ Run immediately after creation                                           │
│  ☐ Set up a schedule                                                        │
│                                                                              │
│                                              [Back]  [Create Process →]      │
│                                                                              │
│  💡 You can always edit the YAML directly after creation for more options.  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Bottlenecks to Watch**:
- [ ] Wizard completion rate
- [ ] Users skip wizard (is it too long?)
- [ ] Generated YAML quality
- [ ] Transition from wizard to YAML editor

---

### P6.5 — Interactive Tutorials

In-app interactive tutorials that guide through real actions.

| Tutorial | Trigger | Duration |
|----------|---------|----------|
| First Process | New user clicks "Create" | ~3 min |
| Understanding Execution | First execution completes | ~1 min |
| Reading Analytics | First visit to Dashboard | ~1 min |

**Implementation**: Spotlight/tooltip system highlighting UI elements.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ProcessEditor.vue                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                         ┌───────────────────┐
│  ┌────────────────────────────────────────────────┐    │ Tutorial 1/5     │
│  │                                                │    │ ───────────────── │
│  │  name: my-first-process                        │ ←──│ This is where you │
│  │  steps:                                        │    │ define your       │
│  │    - id: step-1                    ═══════════════▶ │ process in YAML.  │
│  │      type: agent_task                          │    │                   │
│  │      agent: my-agent                           │    │ Try changing the  │
│  │      message: "Hello world"                    │    │ agent name to one │
│  │                                                │    │ of your agents.   │
│  │                                                │    │                   │
│  │                                                │    │ [Next →]          │
│  └────────────────────────────────────────────────┘    └───────────────────┘
│                                                                              │
│  [Validate]  [Save Draft]  [Publish]                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Bottlenecks to Watch**:
- [ ] Tutorial interrupts workflow
- [ ] Can't dismiss/skip easily
- [ ] Tutorial state persists incorrectly
- [ ] Mobile/touch support

---

### Implementation Priority

| Item | Priority | Effort | Impact |
|------|----------|--------|--------|
| P6.3 Empty States | **P0** | Low | High |
| P6.1 Docs Tab | **P1** | Medium | High |
| P6.2 Contextual Help | **P1** | Medium | Medium |
| P6.4 Onboarding Wizard | **P2** | High | Medium |
| P6.5 Interactive Tutorials | **P3** | High | Low |

**Rationale**: Empty states are quick wins that immediately help new users. Docs tab provides reference material. Contextual help reduces confusion. Wizard and tutorials are nice-to-have polish.

---

## Bottleneck Categories

### Architecture Bottlenecks

| ID | Category | Description | Discovered By |
|----|----------|-------------|---------------|
| A1 | Agent Contention | Same agent requested by multiple processes | P4.1, P5.1 |
| A2 | Database Locks | SQLite write contention under load | P4.1 |
| A3 | Memory Usage | Many concurrent executions | P4.1, P5.2 |
| A4 | Timer Reliability | Long timers surviving restarts | P4.2 |
| A5 | Event Storm | WebSocket flood with parallel steps | P4.1 |
| A6 | Nested Queries | Deep sub-process performance | P4.3 |
| A7 | Recovery Gaps | State not properly persisted | P4.2, P4.4 |

### UX Bottlenecks

| ID | Category | Description | Discovered By |
|----|----------|-------------|---------------|
| U1 | Approval Discovery | Users don't know they have approvals | P1.2, P3.1 |
| U2 | Parallel Visualization | Hard to understand concurrent steps | P2.1, P4.1 |
| U3 | Conditional Clarity | Why was a step skipped? | P1.2, P3.2 |
| U4 | Timer Visibility | Is it waiting or stuck? | P3.2, P4.2 |
| U5 | Error Understanding | What went wrong and how to fix? | P4.4 |
| U6 | Sub-process Navigation | Lost in nested executions | P2.3, P4.3 |
| U7 | Long Process Status | Process runs for days, status unclear | P3.1, P4.2 |
| U8 | Cost Awareness | Total cost not visible until done | P3.3 |
| U9 | Template Syntax | Variable interpolation confusing | P2.1, P2.3 |
| U10 | Schedule UX | Cron syntax intimidating | P1.3, P5.2 |
| U11 | Docs Discoverability | Users don't find the documentation | P6.1 |
| U12 | Empty State Confusion | No guidance when starting fresh | P6.3 |
| U13 | Wizard Completion | Users abandon onboarding wizard | P6.4 |
| U14 | Help Intrusiveness | Contextual help disrupts workflow | P6.2, P6.5 |

---

## Implementation Tracking

### Pre-Phase: Integration Test Coverage ✅

> **Completed**: 2026-01-17
> **Reference**: `BACKLOG_RELIABILITY_IMPROVEMENTS.md`

Before running manual test processes, we established **33 Application Service Integration Tests** covering:

| Area | Tests | Coverage |
|------|-------|----------|
| Execution Lifecycle | 4 | Start, complete, fail, cancel |
| Sequential Execution | 4 | Multi-step, output passing, failure handling |
| Parallel Execution | 5 | Fork/join, diamond pattern, failure behavior |
| Error Handling & Retry | 5 | Retry policies, skip_step, backoff |
| Gateway Routing | 4 | Exclusive routing, conditions, defaults |
| Timer Steps | 3 | Timer completion, output, dependencies |
| Event Publishing | 5 | Event sequence, failure events, context |
| Output Persistence | 3 | Storage, substitution, multi-reference |

**Key**: Tests use real SQLite repos, real handlers, real event bus - only mock external agent HTTP calls.

---

### Phase 1 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P1.1 Simple Content Pipeline | ⏳ | ⏳ | - |
| P1.2 Approval Gate Pipeline | ⏳ | ⏳ | - |
| P1.3 Scheduled Daily Report | ⏳ | ⏳ | - |

### Phase 2 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P2.1 Parallel Research | ⏳ | ⏳ | - |
| P2.2 Diamond Pattern | ⏳ | ⏳ | - |
| P2.3 Nested Sub-Process | ⏳ | ⏳ | - |

### Phase 3 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P3.1 Marketing Campaign | ⏳ | ⏳ | - |
| P3.2 Support Escalation | ⏳ | ⏳ | - |
| P3.3 Financial Report | ⏳ | ⏳ | - |

### Phase 4 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P4.1 High Concurrency | ⏳ | ⏳ | - |
| P4.2 Long Timer | ⏳ | ⏳ | - |
| P4.3 Deep Nesting | ⏳ | ⏳ | - |
| P4.4 Error Recovery | ⏳ | ⏳ | - |

### Phase 5 Status

| Process | Created | Tested | Issues Found |
|---------|---------|--------|--------------|
| P5.1 Agent Competition | ⏳ | ⏳ | - |
| P5.2 Schedule Collision | ⏳ | ⏳ | - |

### Phase 6 Status (Documentation & Onboarding)

| Item | Designed | Implemented | Issues Found |
|------|----------|-------------|--------------|
| P6.1 Docs Tab | ✅ | ✅ | - |
| P6.2 Contextual Help | ⏳ | ⏳ | - |
| P6.3 Empty States | ✅ | ✅ | - |
| P6.4 Onboarding Wizard | ⏳ | ⏳ | - |
| P6.5 Interactive Tutorials | ⏳ | ⏳ | - |

> **Progress Note** (2026-01-18): Implemented BACKLOG_ONBOARDING.md Sprint 7 and Sprint 8
> - E20-01, E20-02: Enhanced empty state with templates + onboarding checklist
> - E21-01, E21-02, E21-04, E21-05, E21-06: Docs tab with full reference content

---

## Issue Log

Track discovered bottlenecks as processes are tested.

| ID | Process | Type | Severity | Description | Status |
|----|---------|------|----------|-------------|--------|
| - | - | - | - | - | - |

**Severity**: Critical / High / Medium / Low
**Type**: Architecture / UX / Bug / Enhancement

---

## Success Criteria

Phase completion requires:

1. **Phase 1**: All 3 processes execute successfully end-to-end
2. **Phase 2**: Parallel execution works, dependencies resolve correctly
3. **Phase 3**: Business processes complete with all step types working
4. **Phase 4**: Stress tests complete, issues documented
5. **Phase 5**: Multi-process scenarios don't deadlock or starve
6. **Phase 6**: Users can self-serve documentation, empty states guide action

**Overall Goal**: Identify and document at least 10 actionable bottlenecks for future improvement.

---

---

## Completed: Execution Recovery (IT5 P0) ✅

> **Reference**: `PROCESS_DRIVEN_THINKING_IT5.md` Section 2.3
> **Implementation**: `BACKLOG_RELIABILITY_IMPROVEMENTS.md` (RI-10 to RI-14)

Execution Recovery on Startup has been implemented and tested:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Recovery Flow (runs on backend startup)                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Scan for active executions (RUNNING, PENDING, PAUSED)                   │
│                                                                              │
│  2. For each execution:                                                      │
│     ├── Age > 24h?        → MARK_FAILED                                      │
│     ├── Step RUNNING?     → RETRY_STEP (reset & resume)                      │
│     └── Otherwise         → RESUME (continue from next step)                 │
│                                                                              │
│  3. Emit events and log summary                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Implementation Details:**
| Component | Location |
|-----------|----------|
| `ExecutionRecoveryService` | `services/process_engine/services/recovery.py` |
| Recovery events | `services/process_engine/domain/events.py` |
| Startup integration | `main.py` lifespan handler |
| Status endpoint | `GET /api/executions/recovery/status` |
| Integration tests | `tests/process_engine/integration/test_execution_recovery.py` (12 tests) |

**IT5 P0 Reliability Foundation Status:**
| Feature | Status |
|---------|--------|
| Per-step retry | ✅ (Integration tests verify) |
| State persistence before transitions | ✅ (Integration tests verify) |
| Execution recovery on startup | ✅ (This implementation) |

---

## Completed: IT5 P1 - Access & Audit ✅

> **Reference**: `PROCESS_DRIVEN_THINKING_IT5.md` Section 5 (Access Management)
> **Implementation**: `BACKLOG_ACCESS_AUDIT.md` (E17, E18, E19)

Access control, audit logging, and execution governance have been implemented:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  IT5 P1 - Access & Audit Architecture                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Authorization Flow:                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  API Request → ProcessAuthorizationService → Role-based check        │    │
│  │                        ↓                                             │    │
│  │  Roles: DESIGNER | OPERATOR | VIEWER | APPROVER | ADMIN              │    │
│  │                        ↓                                             │    │
│  │  Allow or Deny (403 Forbidden)                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Audit Trail:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  All state changes → AuditService → SqliteAuditRepository           │    │
│  │  Query via GET /api/audit (admin only)                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Execution Limits:                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  ExecutionLimitService → Global: 50 concurrent | Per-process: 3      │    │
│  │  Returns 429 Too Many Requests when exceeded                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Implementation Details:**
| Component | Location |
|-----------|----------|
| `ProcessPermission` enum | `services/process_engine/domain/enums.py` |
| `ProcessRole` enum + mappings | `services/process_engine/domain/enums.py` |
| `ProcessAuthorizationService` | `services/process_engine/services/authorization.py` |
| `AuditService` + `AuditEntry` | `services/process_engine/services/audit.py` |
| `SqliteAuditRepository` | `services/process_engine/repositories/audit.py` |
| `ExecutionLimitService` | `services/process_engine/services/limits.py` |
| Audit API router | `routers/audit.py` |
| Unit tests | `tests/process_engine/unit/test_authorization.py` (42 tests) |
| Unit tests | `tests/process_engine/unit/test_audit.py` (22 tests) |

**IT5 P1 Status:**
| Feature | Status |
|---------|--------|
| Role-based permissions | ✅ (5 roles, 13 permissions) |
| API authorization middleware | ✅ (All process/execution endpoints protected) |
| Audit logging | ✅ (Append-only with filters) |
| Audit query API | ✅ (`GET /api/audit` admin-only) |
| Execution concurrency limits | ✅ (Global: 50, Per-process: 3) |
| Limits status endpoint | ✅ (`GET /api/executions/limits/status`) |
| Basic rate limiting | ⏳ (E19-02 - P2 priority, deferred) |

---

## Next Priority: Phase 1 Manual Testing or IT5 P2

With P0 (Reliability) and P1 (Access & Audit) complete, the next options are:

**Option A: Phase 1 Manual Testing** ✅ Infrastructure Ready
Test cases and agents are prepared in `docs/PROCESS_DRIVEN_PLATFORM/manual_run/`:
- 22 test cases across 5 tiers (Critical Path, Conditional, Approval, Error, Edge Cases)
- 3 test agent templates (process-echo, process-worker, process-failer)
- Results tracking template ready

Steps to execute:
1. Deploy test agents
2. Run T1.x through T5.x tests
3. Document findings in `manual_run/results/`

**Option B: IT5 P2 - Performance & Scale**
1. Checkpointing for recovery
2. Performance monitoring
3. Database optimization

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-17 | Add manual testing infrastructure (22 test cases, 3 test agents) |
| 2026-01-17 | Mark IT5 P1 (Access & Audit) as complete |
| 2026-01-17 | Update Next Priority section with Phase 1 or IT5 P2 options |
| 2026-01-17 | Mark Execution Recovery (IT5 P0) as complete |
| 2026-01-17 | Update Next Priority section with options |
| 2026-01-17 | Add Pre-Phase integration test summary (33 tests) |
| 2026-01-17 | Add Next Priority section linking to IT5 P0 |
| 2026-01-16 | Add Phase 6: In-app documentation and onboarding (5 items) |
| 2026-01-16 | Initial roadmap with 5 phases, 14 test processes |
