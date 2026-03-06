# Process-Driven Platform - Advanced Backlog

> **Phase**: Advanced
> **Goal**: Scheduling, sub-processes, analytics, templates, agent roles
> **Epics**: E9, E10, E11, E12, E16
> **Stories**: 13
> **Prerequisites**: MVP and Core phases complete
> **Reference**: See [`BACKLOG_INDEX.md`](./BACKLOG_INDEX.md) for conventions

---

## Sprint Plan

| Sprint | Stories | Focus | Notes |
|--------|---------|-------|-------|
| **Sprint 12** | E9-01, E9-02, E9-03 | Timer & Scheduling | Extends existing scheduler service |
| **Sprint 13** | E10-01, E10-02, E11-01 | Sub-Processes & Cost | |
| **Sprint 14** | E11-02, E11-03, E12-01, E12-02 | Analytics & Templates | |
| **Sprint 15** | E16-01, E16-02, E16-03 | Agent Roles (EMI) | |

---

## Dependency Graph

```
E8-01 (Trigger Schema - from Core)
  │
  └──► E9-01 (Schedule Trigger) ──► E9-02 (Schedule Integration)

E2-03 (Engine - from MVP)
  │
  └──► E9-03 (Timer Step)  [independent of scheduling]

E2-03 (Engine - from MVP)
  │
  └──► E10-01 (Sub-Process Step) ──► E10-02 (Sub-Process UI)

E2-04 (Agent Handler - from MVP)
  │
  └──► E11-01 (Cost Tracking) ──► E11-02 (Analytics Dashboard)
                              │
                              └──► E11-03 (Cost Alerts)

E1-04 (Process API - from MVP)
  │
  └──► E12-01 (Template Library) ──► E12-02 (Template Creation)

E1-01 (Schema - from MVP) + E15-01 (Event Bus - from MVP)
  │
  └──► E16-01 (Role Definition) ──► E16-02 (Informed Notifications)
                               │
                               └──► E16-03 (Role Matrix UI)
```

---

## Epic E9: Timer & Scheduling

> Run processes on a schedule

**Infrastructure Note (2026-01-13):** A standalone scheduler service (`src/scheduler/`) was implemented with APScheduler, Redis distributed locking, and event publishing. This handles agent task scheduling and can be extended for process scheduling.

---

### E9-01: Schedule Trigger Type

**As a** process designer, **I want** to schedule processes, **so that** they run automatically at specific times.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E8-01 (Core) |
| Status | pending |

**Acceptance Criteria:**
- [ ] `schedule` trigger type in process YAML
- [ ] Cron expression support (5-field format)
- [ ] Human-readable presets: `hourly`, `daily`, `weekly`, `monthly`
- [ ] Timezone configuration per trigger
- [ ] Cron validation in `ProcessValidator`

**Technical Notes:**
- `ScheduleTriggerConfig` stub exists in `step_configs.py`
- Reuse `croniter` library (already in scheduler dependencies)
- Size reduced from M to S - config parsing only, infrastructure exists

**Example:**
```yaml
triggers:
  - type: schedule
    id: daily-report
    cron: "0 9 * * 1-5"  # or preset: "daily"
    timezone: "America/New_York"
    enabled: true
```

---

### E9-02: Schedule Integration

**As a** system, **I want** to register schedules with the scheduler, **so that** processes run on time.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E9-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Extend `src/scheduler/` service with process schedule support
- [ ] Add `process_schedules` table (parallel to `agent_schedules`)
- [ ] Schedules registered on process publish
- [ ] Schedules removed on process archive
- [ ] Next run time visible in process list UI
- [ ] Distributed locking prevents duplicate process executions

**Technical Notes:**
- Extend existing `SchedulerService` rather than creating new gateway
- Reuse Redis locking from `src/scheduler/locking.py`
- Scheduler calls backend `/api/processes/{id}/execute` via HTTP
- Size reduced from L to M - extends existing infrastructure

---

### E9-03: Timer Events Within Process

**As a** process designer, **I want** timer events within a process, **so that** I can add delays.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P3 |
| Phase | Advanced |
| Dependencies | E2-03 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] `timer` step type: wait for duration before continuing
- [ ] `TimerStepHandler` with `asyncio.sleep()`
- [ ] Emits standard `StepStarted`/`StepCompleted` events
- [ ] Duration configurable via `delay` field

**Technical Notes:**
- Independent of scheduler service - runs in-process
- `TimerConfig` stub already exists in `step_configs.py`
- `TIMER` step type already in enums
- Size reduced from M to S - simple async handler
- Timeout on steps already implemented via retry policy

**Example:**
```yaml
steps:
  - id: wait
    name: Wait 5 minutes
    type: timer
    delay: 5m
```

---

## Epic E10: Sub-Processes

> Compose processes from other processes

---

### E10-01: Sub-Process Step Type

**As a** process designer, **I want** to call other processes as steps, **so that** I can compose complex workflows.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E2-03 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] `sub_process` step type
- [ ] Schema: process_name, version (optional), input_mapping
- [ ] Sub-process execution is separate but linked
- [ ] Parent waits for child to complete
- [ ] Child output available to parent

**Technical Notes:**
- Reference: IT2 Section 6.6 (Phase 6 - Sub-processes)

---

### E10-02: Sub-Process UI

**As an** operator, **I want** to navigate between parent and child executions, **so that** I can debug nested processes.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E10-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Sub-process step shows link to child execution
- [ ] Child execution shows "called by" parent link
- [ ] Breadcrumb navigation for nested views

---

## Epic E11: Analytics & Cost Tracking

> Understand process performance and costs

---

### E11-01: Cost Tracking Infrastructure

**As a** system, **I want** to track costs per step, **so that** users understand spending.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E2-04 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] Cost captured from agent responses (token usage)
- [ ] Cost stored per step execution
- [ ] Total cost aggregated per execution
- [ ] Cost estimates for in-progress steps (based on history)

**Technical Notes:**
- Reference: IT3 Section 6 (CostCalculator domain service)

---

### E11-02: Process Analytics Dashboard

**As a** manager, **I want** analytics on my processes, **so that** I can optimize them.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P2 |
| Phase | Advanced |
| Dependencies | E11-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Success rate per process
- [ ] Average duration per process
- [ ] Average cost per process
- [ ] Trend charts (last 7/30 days)
- [ ] Slowest steps identification
- [ ] Most expensive steps identification

**Technical Notes:**
- Reference: IT4 Section 7.2 (Dashboard Metrics)

---

### E11-03: Cost Alerts

**As a** manager, **I want** alerts when costs exceed thresholds, **so that** I can control spending.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P3 |
| Phase | Advanced |
| Dependencies | E11-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Cost threshold configurable per process
- [ ] Alert when single execution exceeds threshold
- [ ] Alert when daily/weekly total exceeds threshold
- [ ] Notification via UI (future: email)

---

## Epic E12: Process Templates

> Pre-built processes users can customize

---

### E12-01: Template Library

**As a** user, **I want** a library of process templates, **so that** I can start quickly.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P3 |
| Phase | Advanced |
| Dependencies | E1-04 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] Template storage (bundled or remote)
- [ ] Template listing with descriptions
- [ ] Preview template before using
- [ ] "Use Template" creates draft process

---

### E12-02: Template Creation

**As a** process designer, **I want** to save my processes as templates, **so that** others can reuse them.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P3 |
| Phase | Advanced |
| Dependencies | E12-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] "Save as Template" action
- [ ] Template metadata: name, description, tags
- [ ] Parameter placeholders for customization
- [ ] Share within organization

---

## Epic E16: Agent Roles (EMI Pattern)

> Executor/Monitor/Informed roles from IT1

---

### E16-01: Role Definition in Process Schema

**As a** process designer, **I want** to assign roles to agents per step, **so that** agents have appropriate involvement.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P3 |
| Phase | Advanced |
| Dependencies | E1-01 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] `roles` field in step schema
- [ ] Role types: executor (does work), monitor (owns outcome), informed (observes)
- [ ] Each step has exactly one executor
- [ ] Multiple monitors and informed allowed
- [ ] Validation: executor agent must exist

**Technical Notes:**
- Reference: IT1 Section 1.2 (Simplified Role Model)

---

### E16-02: Informed Agent Notifications

**As an** "informed" agent, **I want** to receive events from steps I'm observing, **so that** I can build situational awareness.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P3 |
| Phase | Advanced |
| Dependencies | E16-01, E15-01 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] Informed agents receive StepCompleted events
- [ ] Events delivered via MCP or agent memory
- [ ] Agent can filter events by process/step
- [ ] Event includes step output summary

**Technical Notes:**
- Reference: IT1 Section 1.3 (Stateful Agent Philosophy)
- Reference: IT3 Section 5 (InformedAgentNotifier)

---

### E16-03: Role Matrix UI

**As a** process designer, **I want** to see and edit agent roles in a matrix view, **so that** I can manage assignments efficiently.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P3 |
| Phase | Advanced |
| Dependencies | E16-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Matrix view: rows = steps, columns = agents
- [ ] Cell shows role (E/M/I or empty)
- [ ] Click to toggle role
- [ ] Validation: each step must have executor
- [ ] Bulk edit (set agent role for multiple steps)

**Technical Notes:**
- Reference: IT1 Section 2.9 (Role Matrix maintenance concern)

---

## Manual Testing Checkpoints

After completing Advanced, verify:

| Checkpoint | Stories | Verification |
|------------|---------|--------------|
| **Scheduled execution** | E9-01, E9-02 | Process runs at scheduled time |
| **Timer delay** | E9-03 | Process waits before continuing |
| **Sub-process** | E10-01, E10-02 | Parent calls child, links work |
| **Cost tracking** | E11-01 | Costs visible per step |
| **Analytics** | E11-02 | Dashboard shows metrics |
| **Templates** | E12-01, E12-02 | Can create from template |
| **Agent roles** | E16-01 to E16-03 | Informed agent receives events |

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-14 | Extracted Advanced stories from main backlog |
