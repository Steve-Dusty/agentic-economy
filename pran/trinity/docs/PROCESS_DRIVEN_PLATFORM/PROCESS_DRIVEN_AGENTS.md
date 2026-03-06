# Process-Driven Multi-Agent Systems

> **Status**: Concept Document (Draft)
> **Created**: 2026-01-06
> **Author**: Eugene / Claude
> **Related Requirements**: 14.1, 14.2

---

## Executive Summary

This document outlines the vision for evolving Trinity from an **agent management platform** into a **business process orchestration platform**. The key insight is that the system should be designed around **business processes first**, with agents serving as the execution engines for those processes.

Instead of managing individual agents and hoping they collaborate effectively, we define:
1. **What business outcomes we want** (processes)
2. **Who does what** (RACI matrix)
3. **How work flows** (events and triggers)
4. **How we improve** (human-in-the-loop evaluation)

The Trinity System Agent becomes the primary interface for designing, testing, deploying, and monitoring these process-driven multi-agent systems.

---

## 1. The Problem with Agent-First Design

### Current State
Today, Trinity excels at:
- Creating and managing individual agents
- Agent-to-agent communication via MCP
- Scheduling tasks on agents
- Permissions between agents

### The Gap
But users still need to:
- Manually design which agents should exist
- Manually configure how agents should collaborate
- Mentally track which processes are running and their state
- Hope that the agent constellation achieves business outcomes

### The Insight
**Business processes should drive agent design, not the other way around.**

When you start with "I need a research agent and a writer agent," you're solving the wrong problem first. When you start with "I need a weekly market analysis report delivered to Slack," you can derive the agents, their configurations, and their collaboration patterns.

---

## 2. Core Concepts

### 2.1 Business Process Definition

A **Business Process** is a named, repeatable workflow that:
- Has a clear **objective** (what outcome do we want?)
- Has defined **inputs** (what information/triggers start it?)
- Has defined **outputs** (where do results go?)
- Has **steps** (what tasks need to happen, in what order?)
- Has **policies** (what constraints and guidelines apply?)

```yaml
process:
  name: weekly-market-analysis
  description: Generate weekly market analysis report for leadership

  objective: |
    Produce a comprehensive market analysis covering competitor moves,
    industry trends, and strategic recommendations.

  trigger:
    type: schedule
    cron: "0 8 * * 1"  # Every Monday at 8 AM
    timezone: America/New_York

  inputs:
    - name: competitors
      source: config
      value: ["CompanyA", "CompanyB", "CompanyC"]
    - name: industry_keywords
      source: config
      value: ["AI", "enterprise", "automation"]

  outputs:
    - name: report
      destination: slack
      channel: "#leadership-updates"
    - name: raw_data
      destination: shared_folder
      path: /reports/market-analysis/

  policies:
    - Only use publicly available information
    - Include confidence levels for predictions
    - Flag any significant competitive threats for immediate review
    - Maximum budget: $5 per execution
```

### 2.2 Agent Roles in Processes

Agents in Trinity are **stateful entities** that evolve over time—building memory, developing beliefs, and refining their judgment based on experience. For this reason, agents benefit from awareness of what's happening in the system, not just their own tasks.

We use a simplified role model (inspired by RACI but adapted for AI agents):

| Role | Definition | In Trinity |
|------|------------|------------|
| **Executor** | Does the work | Agent executes the task, produces outputs |
| **Monitor** | Owns the outcome | Agent watches for failures, handles escalations, reports status |
| **Informed** | Learns from events | Agent receives events about step completions—may update beliefs, trigger actions, or simply observe |

**Why "Informed" Matters for Stateful Agents:**
- Agents build **situational awareness** by observing process events
- Informed agents can **proactively trigger** other parts of the process if they notice something relevant
- Over time, agents develop **better judgment** about when to intervene vs. observe
- Alternative approach: broadcast all events to all permitted agents and let them decide relevance

**Why We Dropped "Consulted":**
The traditional RACI "Consulted" role implies synchronous input-gathering. In Trinity, this is just an agent-to-agent call within a step—the Executor agent handles it internally. No need for a separate role.

Example for the market analysis process:

| Step | Researcher | Analyst | Writer | Reviewer |
|------|------------|---------|--------|----------|
| Gather competitor data | **Executor** | Informed | - | - |
| Analyze trends | Informed | **Executor** | Informed | - |
| Write report draft | - | Informed | **Executor** | Informed |
| Review and approve | - | - | Informed | **Executor**, **Monitor** |
| Publish to Slack | - | - | **Executor** | Informed |

### 2.3 Process Steps as Agent Tasks

Each step in a process maps to:
- An **agent** (or agent pool) that executes it
- A **command** (slash command or task message) to run
- **Inputs**: Where to find data from previous steps or external sources
- **Outputs**: Where the agent saves results (files, external systems)

**Output Storage Philosophy:**
- Outputs are stored by the **Executor agent** (not the platform)
- Storage location depends on the process design:
  - **Shared folders**: `/shared/{process-name}/{step-id}/output.json`
  - **External systems**: Google Drive, CRM, database, S3, etc.
- If a step succeeds, it means the agent has saved its output somewhere accessible
- The next step's agent is responsible for **ingesting the input** from that location

```yaml
steps:
  - id: gather-data
    name: Gather Competitor Data
    agent: researcher
    role: executor
    command: /research-competitors
    inputs:
      competitors: ${process.inputs.competitors}
      keywords: ${process.inputs.industry_keywords}
    outputs:
      location: /shared/market-analysis/research/
      files: [competitor_data.json, sources.md]
    timeout: 30m

  - id: analyze
    name: Analyze Market Trends
    agent: analyst
    role: executor
    depends_on: [gather-data]
    command: /analyze-market
    inputs:
      data_path: /shared/market-analysis/research/competitor_data.json
    outputs:
      location: /shared/market-analysis/analysis/
      files: [trends.md, insights.json]

  - id: write-report
    name: Write Report
    agent: writer
    role: executor
    depends_on: [analyze]
    command: /write-report
    inputs:
      analysis_path: /shared/market-analysis/analysis/
    outputs:
      location: /shared/market-analysis/drafts/
      files: [report_draft.md]

  - id: review
    name: Review Report
    agent: reviewer
    role: [executor, monitor]  # Monitor for the overall process
    depends_on: [write-report]
    command: /review
    inputs:
      draft_path: /shared/market-analysis/drafts/report_draft.md
    outputs:
      location: /shared/market-analysis/final/
      files: [approved_report.md]
      # Also updates: approval_status in process execution record
```

### 2.4 Human Approval Steps

Some steps require human judgment before the process can continue. These are critical for business processes involving legal review, budget approval, quality sign-off, etc.

```yaml
steps:
  - id: legal-review
    name: Legal Compliance Review
    type: human_approval  # Special step type
    depends_on: [draft-contract]

    approval_config:
      approvers:
        - legal@company.com
        - compliance-team  # Can be email or role
      required_approvals: 1  # How many must approve
      timeout: 48h

      on_timeout: notify_escalate  # Options: fail, skip, notify_escalate, auto_approve
      escalate_to: legal-manager@company.com

      # What the approver sees
      review_context:
        title: "Contract Review Required"
        description: "Please review the draft contract for compliance"
        artifacts:
          - /shared/contracts/draft.pdf
          - /shared/contracts/risk_assessment.md

      # Approval options
      decisions:
        - id: approved
          label: "Approve"
          continues_to: next_step
        - id: needs_changes
          label: "Request Changes"
          continues_to: revision_step
          requires_comment: true
        - id: rejected
          label: "Reject"
          terminates_process: true
          requires_comment: true
```

**Human Approval Interface Requirements:**
- Dedicated approval queue/inbox for human operators
- Mobile-friendly for on-the-go approvals
- Context display: what process, what step, relevant artifacts
- Audit trail: who approved, when, with what comments
- Delegation support: reassign approval to another person
- SLA tracking: time to approval, timeout warnings

### 2.5 Event-Driven Execution

Processes can be triggered by:

1. **Schedule** (cron expression)
2. **Event** (another process completes, external webhook)
3. **Manual** (user request via System Agent)
4. **Condition** (threshold reached, anomaly detected)

Steps within a process communicate via **events**:

```
[Step A completes]
    → Emits event: process_step_completed
    → Event contains: step_id, outputs, status

[Step B subscribed to Step A]
    → Receives event
    → Extracts outputs
    → Begins execution
```

This maps directly to the Event Bus infrastructure (Req 13.2).

---

## 3. Roles in Practice

### 3.1 Role Mapping to Agent Behavior

| Role | Agent Behavior |
|-----------|----------------|
| **Executor** | Runs the task command, saves outputs to designated location |
| **Monitor** | Watches step/process progress, handles failures, triggers escalations |
| **Informed** | Receives events, builds situational awareness, may trigger follow-up actions |

### 3.2 Configuration Example

```yaml
process:
  name: customer-onboarding

  agents:
    - name: sales-ops
      roles: [executor, monitor]  # Executes steps and monitors overall process
    - name: data-entry
      roles: [executor]           # Executes specific steps
    - name: compliance
      roles: [executor]           # Executes compliance verification
    - name: account-manager
      roles: [informed]           # Learns about onboarding completions

  role_matrix:
    create_account:
      sales-ops: monitor
      data-entry: executor
    verify_compliance:
      sales-ops: monitor
      compliance: executor
    setup_integrations:
      sales-ops: executor
    notify_completion:
      sales-ops: executor
      account-manager: informed
```

### 3.3 Monitor Role Patterns

The **Monitor** agent (one per process, typically) has special responsibilities:
- Watches for step failures and timeouts
- Receives escalations from failed steps
- Can trigger retries or skip decisions
- Reports overall process health
- Notifies humans when intervention is needed

The Monitor is usually a domain-specific orchestrator agent (e.g., `sales-ops` for customer processes). The Trinity System Agent handles **platform operations**, not process monitoring.

### 3.4 Informed Agents as Active Participants

Because agents are stateful and evolve over time, the "Informed" role is more than passive notification:

```
Event: step_completed (analyze-market)
       ↓
Informed Agent (researcher) receives event
       ↓
Agent decides:
  - Just observe? → Update internal beliefs about market state
  - Take action? → Proactively share additional data it discovered
  - Trigger step? → Start a follow-up research task based on insights
```

**Event Broadcasting Options:**
1. **Selective**: Only agents with `informed` role for that step receive events
2. **Broadcast**: All permitted agents receive all events; they filter locally
3. **Hybrid**: Broadcast within process, selective cross-process

The right choice depends on:
- Agent context limits (too many events = noise)
- Whether agents need holistic awareness or focused attention
- How sophisticated agent event filtering becomes over time

---

## 4. Process Lifecycle

### 4.1 Design Phase

```
User → System Agent: "I need a process for weekly market analysis"

System Agent:
1. Asks clarifying questions about objectives, inputs, outputs
2. Proposes process structure and steps
3. Identifies required agent capabilities
4. Suggests existing agents or creates new ones
5. Generates process definition YAML
6. Creates RACI matrix
```

### 4.2 Configuration Phase

```
System Agent:
1. Creates/configures agents based on process needs
2. Sets up event subscriptions between agents
3. Configures permissions (agents can only talk to process peers)
4. Sets up triggers (schedule, events, webhooks)
5. Deploys as a "system" (uses existing System Manifest)
```

### 4.3 Testing Phase

```
User → System Agent: "Test the market analysis process"

System Agent:
1. Triggers process with test inputs
2. Monitors each step execution
3. Captures outputs and timing
4. Identifies failures or bottlenecks
5. Reports test results
6. Suggests improvements
```

### 4.4 Production Phase

```
Process runs automatically based on triggers

System Agent (as monitor):
1. Tracks all process executions
2. Alerts on failures
3. Provides execution reports
4. Tracks cost per process run
5. Suggests optimizations
```

### 4.5 Improvement Phase (Human-in-the-Loop)

```
After each process run:
1. System Agent summarizes results
2. Human reviews output quality
3. Human provides feedback (approved, needs improvement, rejected)
4. System Agent proposes changes to agent prompts/commands
5. Human approves changes
6. Agents updated automatically
7. Process improves over time
```

---

## 5. Integration with Existing Trinity Features

### 5.1 System Manifest (Req 10.7)
Process definitions **generate** system manifests:
```
Process Definition → System Manifest YAML → Agent Deployment
```

The process definition is the **source of truth**; the manifest is derived.

### 5.2 Agent Permissions (Req 9.10)
RACI matrix **generates** permission rules:
- Agents in the same process get mutual permissions
- Permissions scoped to process context
- Prevents agents from unintended cross-process communication

### 5.3 Event Bus (Req 13.2)
Process steps communicate via events:
- `process_started`, `step_completed`, `process_completed`
- Events carry correlation IDs linking to process execution
- Agents subscribe to events from their process peers

### 5.4 Scheduling (Req 9.1)
Process triggers map to:
- Schedules for time-based triggers
- Event handlers for event-based triggers
- API endpoints for manual triggers

### 5.5 Shared Folders (Req 9.11)
Process outputs use shared folders:
- Intermediate outputs between steps
- Final outputs for process consumers
- Audit trail of all process artifacts

### 5.6 Trinity System Agent (Req 11.1)
The System Agent remains focused on **platform operations** (infrastructure, health, costs):
- Does NOT orchestrate business processes
- Does NOT monitor process execution (that's the Monitor agent's job)
- CAN report on process infrastructure health (containers, queues)
- CAN provide fleet-wide statistics across all processes

**Process orchestration is handled by:**
- The **Process Execution Engine** (platform component, not an agent)
- The **Monitor agent** (domain-specific, per-process)
- **Human operators** (via approval interface for escalations)

---

## 6. Data Model

### 6.1 Database Tables

```sql
-- Process definitions
CREATE TABLE process_definitions (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    definition TEXT NOT NULL,  -- YAML content
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'draft',  -- draft, active, archived
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Process executions
CREATE TABLE process_executions (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    triggered_by TEXT NOT NULL,  -- schedule, event, manual, condition
    trigger_details TEXT,  -- JSON with trigger context
    status TEXT NOT NULL,  -- pending, running, completed, failed
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER,
    total_cost REAL DEFAULT 0,
    error TEXT,
    FOREIGN KEY (process_id) REFERENCES process_definitions(id)
);

-- Process step executions
CREATE TABLE process_step_executions (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,  -- pending, running, completed, failed, skipped
    started_at TEXT,
    completed_at TEXT,
    duration_ms INTEGER,
    cost REAL,
    inputs TEXT,  -- JSON
    outputs TEXT,  -- JSON
    error TEXT,
    FOREIGN KEY (execution_id) REFERENCES process_executions(id)
);

-- Role assignments (Executor, Monitor, Informed)
CREATE TABLE process_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_id TEXT NOT NULL,
    step_id TEXT,  -- NULL means process-level role
    agent_name TEXT NOT NULL,
    role TEXT NOT NULL,  -- executor, monitor, informed
    UNIQUE(process_id, step_id, agent_name, role),
    FOREIGN KEY (process_id) REFERENCES process_definitions(id)
);

-- Human approval requests
CREATE TABLE process_approvals (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- pending, approved, rejected, timed_out
    approvers TEXT NOT NULL,  -- JSON array of emails/roles
    required_approvals INTEGER DEFAULT 1,
    received_approvals INTEGER DEFAULT 0,
    timeout_at TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    decision TEXT,  -- approved, needs_changes, rejected
    decided_by TEXT,  -- email of approver
    comment TEXT,
    FOREIGN KEY (execution_id) REFERENCES process_executions(id)
);
```

### 6.2 API Endpoints

```
# Process definitions
GET    /api/processes              # List all processes
POST   /api/processes              # Create process from YAML
GET    /api/processes/{id}         # Get process details
PUT    /api/processes/{id}         # Update process
DELETE /api/processes/{id}         # Archive process
POST   /api/processes/{id}/deploy  # Deploy process (create agents, permissions)

# Process executions
POST   /api/processes/{id}/trigger          # Manual trigger
GET    /api/processes/{id}/executions       # Execution history
GET    /api/processes/{id}/executions/{eid} # Execution details

# Process monitoring
GET    /api/processes/{id}/status           # Current status
GET    /api/processes/{id}/metrics          # Aggregated metrics

# Role assignments
GET    /api/processes/{id}/roles            # Get role matrix
PUT    /api/processes/{id}/roles            # Update role matrix

# Human approvals
GET    /api/approvals                       # List pending approvals (for current user)
GET    /api/approvals/{id}                  # Get approval details with context
POST   /api/approvals/{id}/decide           # Submit approval decision
POST   /api/approvals/{id}/delegate         # Reassign to another approver
```

---

## 7. User Interface Vision

### 7.1 Process Designer

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Process: Weekly Market Analysis                              [Save] [Test] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐       │
│  │ Trigger  │ ──── │ Research │ ──── │ Analyze  │ ──── │  Write   │       │
│  │ Schedule │      │ [Agent]  │      │ [Agent]  │      │ [Agent]  │       │
│  │ Mon 8AM  │      │ researcher│      │ analyst  │      │ writer   │       │
│  └──────────┘      └──────────┘      └──────────┘      └──────────┘       │
│                                             │                    │         │
│                                             │                    ▼         │
│                                             │              ┌──────────┐    │
│                                             └────────────► │ Review   │    │
│                                                            │ [Agent]  │    │
│                                                            │ reviewer │    │
│                                                            └──────────┘    │
│                                                                   │        │
│                                                                   ▼        │
│                                                            ┌──────────┐    │
│                                                            │ Publish  │    │
│                                                            │ → Slack  │    │
│                                                            └──────────┘    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Role Matrix                                                                │
│  ┌────────────────┬────────────┬─────────┬────────┬──────────┐            │
│  │ Step           │ Researcher │ Analyst │ Writer │ Reviewer │            │
│  ├────────────────┼────────────┼─────────┼────────┼──────────┤            │
│  │ Research       │ Executor   │ Informed│ -      │ -        │            │
│  │ Analyze        │ Informed   │ Executor│ Informed│ -        │            │
│  │ Write          │ -          │ Informed│ Executor│ Informed │            │
│  │ Review         │ -          │ -       │ Informed│ Exec+Mon │            │
│  └────────────────┴────────────┴─────────┴────────┴──────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Process Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Processes                                        [+ New Process]           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Weekly Market Analysis                                    [Running] │   │
│  │ Last run: 2h ago • Avg duration: 45m • Success rate: 94%           │   │
│  │ Next run: Mon 8:00 AM                                               │   │
│  │ Agents: researcher, analyst, writer, reviewer                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Customer Onboarding                                       [Active]  │   │
│  │ Executions today: 12 • Avg duration: 15m • Success rate: 100%      │   │
│  │ Trigger: Event (new_customer_signup)                                │   │
│  │ Agents: sales-ops, data-entry, compliance                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Daily Social Media                                        [Paused]  │   │
│  │ Last run: 3d ago • Reason: Awaiting content approval               │   │
│  │ Agents: content-creator, scheduler                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Process Execution View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Execution: Weekly Market Analysis #47                    Jan 6, 2026 8:00  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Status: ● Running (Step 3/5)                     Duration: 23m 45s         │
│  Cost: $1.24                                      Context: 45K tokens       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ✓ Research         researcher     8:00 - 8:12    $0.45    Done      │   │
│  │ ✓ Analyze          analyst        8:12 - 8:28    $0.38    Done      │   │
│  │ ● Write            writer         8:28 - ...     $0.41    Running   │   │
│  │ ○ Review           reviewer       Pending                            │   │
│  │ ○ Publish          writer         Pending                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Current Step: Write Report                                                 │
│  Agent: writer                                                              │
│  Command: /write-report                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ [Live Activity Stream]                                              │   │
│  │ 8:28:15  Read: market_analysis.md                                   │   │
│  │ 8:28:23  Write: draft_sections/intro.md                             │   │
│  │ 8:28:45  Read: competitor_data.json                                 │   │
│  │ 8:29:02  Write: draft_sections/competitors.md                       │   │
│  │ ...                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Human Approval Interface

A dedicated interface for human operators to review and approve pending process steps:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Pending Approvals                                        eugene@company.com │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ⏰ Contract Review Required                          Due in 23h     │   │
│  │ Process: Customer Onboarding #847                                    │   │
│  │ Step: Legal Compliance Review                                        │   │
│  │ Requested by: sales-ops agent                                        │   │
│  │                                                                       │   │
│  │ Artifacts:                                                           │   │
│  │ 📄 draft_contract.pdf                           [View]               │   │
│  │ 📋 risk_assessment.md                           [View]               │   │
│  │                                                                       │   │
│  │ [✓ Approve]  [↩ Request Changes]  [✗ Reject]   [→ Delegate]        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ⏰ Budget Approval Needed                            Due in 4h      │   │
│  │ Process: Marketing Campaign #234                                     │   │
│  │ Step: Budget Sign-off                                                │   │
│  │ Amount: $15,000                                                      │   │
│  │                                                                       │   │
│  │ [✓ Approve]  [✗ Reject]   [→ Delegate]                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  History (last 7 days):                                                     │
│  ✓ Approved: Contract #843 - 2 days ago                                    │
│  ✓ Approved: Budget #231 - 3 days ago                                      │
│  ✗ Rejected: Contract #841 - 5 days ago (compliance issue)                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Mobile-responsive for approvals on-the-go
- Email/Slack notifications with direct approve/reject links
- Artifact preview without leaving the interface
- Comment required for rejections/change requests
- Delegation to colleagues with notification
- Audit trail with timestamps and reasons

---

## 8. Conversational Process Design

Process design can be assisted by any capable agent (including a dedicated Process Designer agent):

### Example Conversation

```
User: I want to create a process for generating weekly market analysis reports

Agent: I'll help you design a market analysis process. Let me ask a few questions:

1. **Objective**: What should the final report include?
   - Competitor updates?
   - Industry trends?
   - Strategic recommendations?

User: All of the above, plus any significant news about our competitors

Agent: Got it. Now about the workflow:

2. **Data Sources**: Where should the research come from?
   - Public news and filings?
   - Social media monitoring?
   - Internal sales data?

User: Public news and social media. We don't have internal data feeds yet.

Agent: Understood.

3. **Output**: Where should the report go?
   - Slack channel?
   - Email?
   - Saved to file?

User: Post to #leadership-updates on Slack, and save a copy to our shared drive

Agent: Perfect. Let me propose a process structure:

**Weekly Market Analysis Process**

| Step | Agent | Description |
|------|-------|-------------|
| 1. Research | researcher | Gather competitor news and social mentions |
| 2. Analyze | analyst | Identify trends and insights |
| 3. Write | writer | Create formatted report |
| 4. Review | reviewer | Quality check and approval |
| 5. Publish | writer | Post to Slack and save file |

**Role Matrix:**
- Researcher: Executor for research, Informed for analysis
- Analyst: Executor for analysis, Informed for writing
- Writer: Executor for writing and publishing
- Reviewer: Executor + Monitor for final approval

**Trigger:** Every Monday at 8 AM EST

Should I create this process? I can also create the agents if they don't exist.

User: Yes, create it. Use my existing researcher agent but create new ones for the others.

Agent: Creating process "weekly-market-analysis"...

✓ Process definition created
✓ Using existing agent: researcher
✓ Created agent: market-analyst
✓ Created agent: report-writer
✓ Created agent: report-reviewer
✓ Configured permissions between agents
✓ Set up Monday 8 AM schedule
✓ Configured Slack integration

Process is ready! Would you like to run a test execution now?

User: Yes, run a test

Agent: Starting test execution...
[Shows live progress of each step]

Test completed in 42 minutes. Total cost: $3.21

Results:
- Research: ✓ Found 23 relevant articles
- Analysis: ✓ Identified 5 key trends
- Report: ✓ 2,400 word report generated
- Review: ✓ Approved with minor suggestions
- Publish: ✓ Posted to Slack

The report has been posted to #leadership-updates.
Would you like to review the output quality before activating the schedule?
```

---

## 9. Human-in-the-Loop Improvement

### 9.1 Feedback Loop

After each process execution, the Monitor agent (or UI) can prompt for feedback:

```
Monitor Agent: Process "weekly-market-analysis" completed.

📊 Execution Summary:
- Duration: 45 minutes
- Cost: $2.87
- All steps completed successfully

📄 Report Preview:
[Shows first 500 chars of report]

How would you rate this output?
[ 👍 Good ] [ 👎 Needs Work ] [ 🚫 Reject ]
```

### 9.2 Improvement Actions

Based on feedback:

```
User: [clicks 👎 Needs Work]

Monitor Agent: What could be improved?
1. Research depth
2. Analysis quality
3. Writing style
4. Report format
5. Other

User: The analysis was too surface-level. I want more specific insights.

Monitor Agent: I'll propose updates to the analyst agent's instructions:
- Require at least 3 specific, actionable insights per competitor
- Include confidence levels for each insight
- Cross-reference multiple sources before making claims

Updated instructions:
```
When analyzing market data, you MUST:
1. Provide at least 3 specific, actionable insights per major competitor
2. Include a confidence level (High/Medium/Low) for each insight
3. Cross-reference at least 2 sources before making claims
4. Explicitly flag any insight based on a single source
```

Apply these changes? [Yes] [Modify] [Cancel]
```

### 9.3 Continuous Improvement Metrics

Track improvement over time:

```
Process: weekly-market-analysis

Quality Trend (last 10 runs):
👍 Good:       ████████░░  80%
👎 Needs Work: ██░░░░░░░░  20%
🚫 Rejected:   ░░░░░░░░░░   0%

Improvements Applied: 3
- Dec 15: Enhanced research depth
- Dec 22: Improved insight specificity
- Jan 5: Added competitor comparison tables

Average Quality Score: 4.2/5 (up from 3.1 six weeks ago)
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Prerequisites)
- [ ] Event Bus Infrastructure (Req 13.2)
- [ ] Event Handlers & Reactions (Req 13.3)
- [ ] Horizontal Scalability basics (Req 13.1) — optional but helpful

### Phase 2: Process Core
- [ ] Process definition YAML schema and parser
- [ ] Process storage (database tables)
- [ ] Process execution coordination (architecture TBD)
- [ ] Step-to-agent task mapping (uses existing `/api/task` endpoint)
- [ ] Role enforcement (Executor, Monitor, Informed)

### Phase 3: Human Approval (Critical)
- [ ] `type: human_approval` step execution
- [ ] Approval database tables and API endpoints
- [ ] Human Approval Interface (dedicated UI)
- [ ] Email/Slack notifications with action links
- [ ] Timeout handling and escalation

### Phase 4: Feedback & Improvement
- [ ] Execution feedback collection (👍/👎 rating)
- [ ] Feedback-driven instruction suggestions
- [ ] Quality trend tracking per process
- [ ] Improvement history

### Phase 5: UI & Polish
- [ ] Process Dashboard (list, status, metrics)
- [ ] Process Execution View (live step progress)
- [ ] Process Designer (visual editor) — nice to have
- [ ] Role matrix editor

---

## 11. Open Questions

### Resolved

1. ~~**Human approval steps**: How do we handle steps that require human approval before proceeding?~~
   → **Resolved**: Dedicated `type: human_approval` step type with approvers, timeout, escalation. Separate approval interface for human operators. (See Section 2.4)

2. ~~**Output storage**: How do outputs pass between steps?~~
   → **Resolved**: Agent responsibility. Executors save to shared folders or external systems. Next step's agent ingests from that location. Platform doesn't manage output transfer. (See Section 2.3)

3. ~~**System Agent role**: Should System Agent orchestrate processes?~~
   → **Resolved**: No. System Agent stays focused on platform operations. Process orchestration is handled by the Process Execution Engine (platform) and Monitor agents (domain-specific). (See Section 5.6)

4. ~~**RACI roles**: Are all four roles necessary?~~
   → **Resolved**: Simplified to three: Executor, Monitor, Informed. Dropped "Consulted" (just an agent call). Kept "Informed" because stateful agents benefit from situational awareness. (See Section 2.2)

### Still Open

1. **Process versioning**: How do we handle process definition changes while executions are running?
   - Option A: Running executions use old version until complete
   - Option B: Abort and restart with new version
   - Option C: User chooses per-update

2. **Failure recovery**: If step 3 of 5 fails, do we restart from step 3 or from the beginning?
   - Configurable per-process: `on_failure: retry_step | restart_process | pause_for_human`
   - Need to consider idempotency of steps

3. **Parallel steps**: Can steps run in parallel if they don't have dependencies?
   - Yes, if `depends_on` graph allows
   - Need DAG validation at process creation time
   - Resource limits (max concurrent agents?)

4. **Cross-process dependencies**: Can one process trigger another, or should they be combined?
   - Event bus allows this naturally (process_completed event)
   - Risk of complex dependency chains
   - Maybe: soft-link via events, hard-link discouraged

5. **Cost budgets**: How do we enforce cost limits per process vs. per step vs. per agent?
   - Process-level budget seems most useful
   - Step-level for expensive operations (e.g., research)
   - Agent-level already exists in Trinity

6. **Template library**: Should we provide pre-built process templates for common workflows?
   - Yes, would accelerate adoption
   - Examples: content-pipeline, customer-onboarding, incident-response
   - Templates should be customizable, not rigid

7. **Event broadcasting strategy**: Selective vs. broadcast for Informed agents?
   - See Section 3.4 for trade-offs
   - May depend on agent sophistication and context limits

---

## 12. Success Metrics

When this vision is realized, we measure success by:

| Metric | Target |
|--------|--------|
| Process creation time | < 30 minutes via conversation |
| Process reliability | > 95% success rate |
| Time to first improvement | < 3 executions |
| User satisfaction | 4+ stars on process outputs |
| Cost predictability | < 10% variance from estimates |
| Agent reuse | > 60% of processes share agents |

---

## 13. Relationship to Existing Vision

This concept builds on Trinity's Four Pillars:

| Pillar | Current | With Process-Driven |
|--------|---------|---------------------|
| **Explicit Planning** | Per-agent task DAGs | Process-level execution plans |
| **Hierarchical Delegation** | Agent-to-agent calls | Role-based assignment (Executor, Monitor, Informed) |
| **Persistent Memory** | Per-agent memory | Process-level state + agent situational awareness |
| **Extreme Context Engineering** | Per-agent prompts | Process-aware agent instructions |

The evolution is natural: Trinity already orchestrates agents; now we orchestrate **business processes** that happen to be executed by agents.

**Key Principle: Agents as Stateful Entities**

Unlike stateless microservices, Trinity agents:
- Build memory over time
- Develop beliefs and judgment
- Benefit from situational awareness
- Can proactively intervene when they observe relevant events

The "Informed" role acknowledges this: agents aren't just notified—they *learn* from events and may take autonomous action based on evolving understanding.

---

## Next Steps

1. **Review this document** with stakeholders
2. **Prototype** the process definition schema and parser
3. **Implement** Event Bus (Req 13.2) as prerequisite
4. **Design** Process Execution Engine architecture (leave flexible for now)
5. **Build** Human Approval Interface
6. **Create** process templates for common workflows

---

## Appendix A: Complete Process Definition YAML Schema

This schema is the **single source of truth** for a process definition. From this YAML, the system can:
- Render the designer view and workflow diagram
- Generate the role matrix
- Validate all agents/credentials exist
- Deploy and execute the process

```yaml
# ============================================================
# PROCESS DEFINITION SCHEMA v1.0
# ============================================================

version: "1.0"

# === METADATA ===
metadata:
  name: weekly-market-report
  description: |
    Automated weekly market analysis with human review
    before publishing to stakeholders.
  owner: user@example.com
  tags: [reporting, market-analysis, weekly]

# === AGENTS ===
# All agents involved in this process
# Used for: validation, deployment, role matrix columns
agents:
  - name: research-assistant
    role: Data gathering and web research
    capabilities: [web-search, document-analysis]
    # If template specified, agent will be created if missing
    # template: github:company/research-agent

  - name: market-analyst
    role: Trend analysis and visualization
    capabilities: [data-analysis, chart-generation]

  - name: report-writer
    role: Content generation and formatting
    capabilities: [content-generation, markdown, pdf-export]

# === WORKFLOW ===
# Ordered steps with explicit dependencies and role assignments
# Used for: workflow diagram, role matrix rows, execution order
steps:
  - id: gather
    name: Gather Market Data
    description: Collect latest market data from configured sources
    agent: research-assistant

    inputs:
      - name: data_sources
        from: config                    # From process config

    outputs:
      - name: raw_data
        path: /shared/data/market.json

    timeout: 30m

    roles:
      executor: research-assistant      # Implicit from 'agent', but explicit for clarity
      monitors: [market-analyst]        # Can observe progress
      informed: []                      # Notified on completion

  - id: analyze
    name: Analyze Trends
    agent: market-analyst
    depends_on: [gather]

    inputs:
      - name: market_data
        from: step:gather.raw_data      # Output from previous step

    outputs:
      - name: analysis
        path: /shared/data/analysis.json
      - name: charts
        path: /shared/charts/

    roles:
      monitors: [research-assistant]
      informed: [report-writer]

  - id: draft
    name: Draft Report
    agent: report-writer
    depends_on: [analyze]

    inputs:
      - name: analysis
        from: step:analyze.analysis
      - name: charts
        from: step:analyze.charts

    outputs:
      - name: draft_report
        path: /shared/reports/draft.md

    roles:
      monitors: []
      informed: [market-analyst]

  - id: review
    name: Human Review
    type: approval                      # Special step type
    depends_on: [draft]

    approval:
      approvers:
        - manager@example.com
        - stakeholder@example.com
      required: 1                       # Approvals needed (1 of N)
      timeout: 48h
      on_timeout: notify                # notify | reject | auto-approve

    review_artifacts:                   # What approvers see
      - from: step:draft.draft_report

    roles:
      monitors: []
      informed: [report-writer]         # Author notified of decision

  - id: publish
    name: Publish Report
    agent: report-writer
    depends_on: [review]
    condition: review.approved          # Only runs if approved

    inputs:
      - name: draft
        from: step:draft.draft_report

    outputs:
      - name: final_report
        path: /shared/reports/final.pdf

    roles:
      monitors: []
      informed: [market-analyst, research-assistant]

# === RESOURCES ===
# Shared folders and required credentials
# Used for: validation, deployment, data flow visualization
resources:
  shared_folders:
    - name: data
      path: /shared/data
      access:
        read: [research-assistant, market-analyst, report-writer]
        write: [research-assistant, market-analyst]

    - name: reports
      path: /shared/reports
      access:
        read: [report-writer]
        write: [report-writer]

  credentials:
    - name: MARKET_API_KEY
      agent: research-assistant
      required: true

    - name: SLACK_WEBHOOK
      agent: report-writer
      required: true

# === PERMISSIONS ===
# Agent-to-agent communication rules
# Used for: validation, security, network diagram
permissions:
  preset: linear                        # full-mesh | linear | hub-spoke | custom
  # If custom:
  # rules:
  #   - from: research-assistant
  #     to: market-analyst
  #     allow: [message, file-transfer]

# === TRIGGER ===
# How the process is initiated
# Used for: scheduler integration, UI display
trigger:
  type: schedule                        # schedule | manual | event

  schedule:
    cron: "0 8 * * 1"                   # Every Monday 8am
    timezone: America/New_York

  # type: event
  # event:
  #   source: webhook
  #   path: /api/processes/weekly-market-report/trigger

# === OUTPUT ===
# Where results are delivered
# Used for: notification config, success criteria
output:
  on_success:
    - type: slack
      channel: "#market-reports"
      include: [step:publish.final_report]

    - type: email
      to: [stakeholders@example.com]
      subject: "Weekly Market Report - {{date}}"

  on_failure:
    - type: slack
      channel: "#alerts"
      message: "Process failed at step: {{failed_step}}"

# === MONITORING ===
# Global observation and notification settings
# Used for: role matrix (global monitors), alerting
monitoring:
  global_monitors:                      # Agents that monitor ALL steps
    - orchestrator-agent

  global_informed:                      # Always notified of completion
    - admin@example.com

# === ERROR HANDLING ===
# Default retry and failure behavior
# Used for: execution engine, validation
error_handling:
  default_retry:
    attempts: 2
    delay: 5m
    backoff: exponential                # fixed | linear | exponential

  on_step_failure: pause                # pause | abort | skip | notify

  fallback_notification:
    - type: email
      to: admin@example.com
```

### Schema-to-Feature Mapping

| YAML Section | Enables |
|--------------|---------|
| `metadata` | Process list, search, ownership |
| `agents` | Agent validation, deployment, role matrix columns |
| `steps` | Workflow diagram, execution order, role matrix rows |
| `steps[].roles` | Role matrix cells (executor/monitor/informed) |
| `resources.shared_folders` | Data flow visualization, folder provisioning |
| `resources.credentials` | Pre-deployment validation |
| `permissions` | Security validation, network diagram |
| `trigger` | Scheduler integration, manual trigger UI |
| `output` | Notification routing, success criteria |
| `monitoring.global_monitors` | Role matrix global row |
| `error_handling` | Retry logic, failure behavior |

### Validation Rules

The system can enforce these rules at process creation/update time:

1. All `agent` references in steps exist in `agents` list
2. All `depends_on` references point to valid step IDs
3. All `from: step:X.Y` inputs reference existing step outputs
4. All required credentials exist in credential store
5. No circular dependencies in step graph
6. Approval steps have at least one approver
7. Cron expressions are valid
8. Referenced shared folders have appropriate access permissions
