# Process-Driven Platform - Core Backlog

> **Phase**: Core
> **Goal**: Parallel execution, human approvals, conditional logic, triggers
> **Epics**: E5, E6, E7, E8, E13, E14
> **Stories**: 23
> **Prerequisites**: MVP phase complete
> **Reference**: See [`BACKLOG_INDEX.md`](./BACKLOG_INDEX.md) for conventions

---

## Sprint Plan

| Sprint | Stories | Focus |
|--------|---------|-------|
| **Sprint 7** | E13-01, E13-02, E13-04 | Error Handling |
| **Sprint 8** | E5-01, E5-02, E5-03 | Parallel Execution |
| **Sprint 9** | E6-01, E6-02, E6-03, E6-04 | Human Approval |
| **Sprint 10** | E7-01, E7-02, E7-03, E8-01, E8-02 | Gateways & Triggers |
| **Sprint 11** | E14-01, E14-02, E6-05, E8-03, E15-03, E13-03 | Notifications & Polish |

---

## Dependency Graph

```
E2-03 (Engine - from MVP)
  │
  ├──► E5-01 (Parallel Resolution) ──► E5-02 (Concurrent Exec) ──► E5-03 (Parallel UI)
  │
  ├──► E7-01 (Gateway Step) ──► E7-02 (Expression Eval) ──► E7-03 (Gateway UI)
  │
  ├──► E13-01 (Retry Policy) ──► E13-02 (Error Boundary) ──► E13-03 (Compensation)
  │                                      │
  │                                      └──► E13-04 (Error Debug UI)
  │
  └──► E14-01 (Notification Step) ──► E14-02 (Notification Config)

E1-01 (Schema - from MVP)
  │
  ├──► E6-01 (Approval Step) ──► E6-02 (Approval State) ──► E6-03 (Approval API)
  │                                                              │
  │                                                              ├──► E6-04 (Approval Inbox)
  │                                                              │
  │                                                              └──► E6-05 (Inline Approval)
  │
  └──► E8-01 (Trigger Schema) ──► E8-02 (Webhook Trigger) ──► E8-03 (Trigger UI)
```

---

## Epic E5: Parallel Execution

> Execute independent steps concurrently

---

### E5-01: Parallel Dependency Resolution

**As a** system, **I want** to identify steps that can run in parallel, **so that** processes complete faster.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E2-03 (MVP) |
| Status | done |

**Acceptance Criteria:**
- [x] `DependencyResolver` identifies parallelizable steps
- [x] Steps with no shared dependencies run concurrently
- [x] Execution order respects all `depends_on` constraints
- [x] Visual indication in UI of parallel branches

**Technical Notes:**
- Reference: IT3 Section 6 (Domain Services - DependencyResolver)
- Topological sort with parallel grouping

---

### E5-02: Concurrent Step Execution

**As a** system, **I want** to execute multiple steps at once, **so that** parallel branches run simultaneously.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P1 |
| Phase | Core |
| Dependencies | E5-01 |
| Status | done |

**Acceptance Criteria:**
- [x] Execution engine runs parallel steps concurrently
- [x] Uses asyncio for concurrent agent calls
- [x] All parallel steps must complete before dependents start
- [x] One failure doesn't immediately stop siblings (configurable via `stop_on_failure`)
- [x] Execution state tracks parallel step progress

**Technical Notes:**
- Reference: IT2 Section 6.2 (Phase 2 - Parallel Execution)

---

### E5-03: Parallel UI Visualization

**As an** operator, **I want** to see parallel steps visually, **so that** I understand concurrent execution.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E5-02, E4-02 (MVP) |
| Status | done |

**Acceptance Criteria:**
- [x] Timeline shows parallel steps with visual marker (⫘ icon)
- [ ] Preview diagram shows fork/join points (deferred - requires diagram library)
- [x] Duration bars show overlap for concurrent steps

**Technical Notes:**
- Reference: IT4 Section 4.2 (Layout - parallel indication)

---

## Epic E6: Human Approval

> Pause execution for human decisions

---

### E6-01: Approval Step Type

**As a** process designer, **I want** to define approval steps, **so that** humans can review before continuing.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E1-01 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] `human_approval` step type fully implemented
- [ ] Schema supports: approvers (list), message, deadline, artifacts
- [ ] Validation ensures at least one approver
- [ ] Deadline parsed as duration ("24h", "3d")

**Technical Notes:**
- Reference: IT3 Section 8 (ApprovalGateway)

---

### E6-02: Approval State Management

**As a** system, **I want** to track approval state, **so that** I know when to proceed.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E6-01, E2-01 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] `ApprovalRequest` entity with: id, execution_id, step_id, approvers, deadline, status
- [ ] Status: pending, approved, rejected, changes_requested, expired
- [ ] Decision records: who, when, comment
- [ ] Domain events: ApprovalRequested, ApprovalDecided

**Technical Notes:**
- Reference: IT3 Section 5 (Domain Events)

---

### E6-03: Approval API Endpoints

**As a** frontend developer, **I want** API endpoints for approvals, **so that** the UI can manage them.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E6-02 |
| Status | pending |

**Acceptance Criteria:**
- [ ] `GET /api/approvals` - List pending approvals (for current user)
- [ ] `GET /api/approvals/{id}` - Get approval detail
- [ ] `POST /api/approvals/{id}/approve` - Approve with optional comment
- [ ] `POST /api/approvals/{id}/reject` - Reject with required comment
- [ ] `POST /api/approvals/{id}/request-changes` - Request changes with comment
- [ ] Notifications triggered on new approval (future: email/Slack)

**Technical Notes:**
- Location: `src/backend/routers/approvals.py`

---

### E6-04: Approval Inbox UI

**As an** approver, **I want** an inbox of pending approvals, **so that** I can manage my review queue.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P1 |
| Phase | Core |
| Dependencies | E6-03 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Dedicated approvals page/section
- [ ] Cards showing: process name, step, deadline, artifacts
- [ ] Quick actions: Approve, Reject, Request Changes
- [ ] Urgency indication (deadline approaching)
- [ ] Badge count in navigation

**Technical Notes:**
- Reference: IT4 Section 5.2 (Approval Inbox)
- Location: `src/frontend/src/views/Approvals.vue`

---

### E6-05: Inline Approval in Execution View

**As an** operator viewing an execution, **I want** to approve inline, **so that** I don't leave context.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Core |
| Dependencies | E6-03, E4-02 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] Approval step in timeline shows approval form
- [ ] Same actions as inbox: Approve, Reject, Request Changes
- [ ] Shows who else can approve
- [ ] Shows deadline countdown

**Technical Notes:**
- Reference: IT4 Section 5.3 (Inline Approval)

---

## Epic E7: Conditional Logic (Gateways)

> Branch execution based on conditions

---

### E7-01: Gateway Step Type

**As a** process designer, **I want** to define conditional branches, **so that** processes can make decisions.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E1-01 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] `gateway` step type (exclusive - XOR)
- [ ] Schema: conditions as list of {expression, target_step}
- [ ] Default path if no conditions match
- [ ] Expressions can reference previous step outputs

**Technical Notes:**
- Reference: IT2 Section 4 (BPMN Concepts - Gateways)

---

### E7-02: Expression Evaluator

**As a** system, **I want** to evaluate gateway conditions, **so that** the correct path is chosen.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P1 |
| Phase | Core |
| Dependencies | E7-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] `ExpressionEvaluator` domain service
- [ ] Supports basic comparisons: ==, !=, >, <, >=, <=
- [ ] Supports accessing step outputs: `steps.analyze.output.score`
- [ ] Supports basic logic: and, or, not
- [ ] Safe evaluation (no arbitrary code execution)
- [ ] Clear error messages for invalid expressions

**Technical Notes:**
- Reference: IT3 Section 6 (Domain Services - ExpressionEvaluator)
- Consider: Simple parser or restricted Python eval

---

### E7-03: Gateway UI Visualization

**As an** operator, **I want** to see which path was taken, **so that** I understand the decision.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P2 |
| Phase | Core |
| Dependencies | E7-02, E4-02 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] Gateway step shows condition evaluated and result
- [ ] Preview diagram shows all branches
- [ ] Execution view highlights taken path
- [ ] Shows skipped branches (grayed out)

**Technical Notes:**
- Reference: IT4 Section 4.2 (Gateway decisions)

---

## Epic E8: Event Triggers

> Start processes automatically from external events

---

### E8-01: Trigger Definition Schema

**As a** process designer, **I want** to define triggers for my process, **so that** it starts automatically.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E1-01 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] `triggers` field in process definition
- [ ] Trigger types: `manual`, `webhook`, `schedule` (stub)
- [ ] Webhook trigger: generates unique URL
- [ ] Trigger can pass payload as input to first step

**Technical Notes:**
- Reference: Original PROCESS_DRIVEN_AGENTS.md Section 5

---

### E8-02: Webhook Trigger Endpoint

**As an** external system, **I want** to trigger processes via webhook, **so that** I can integrate with other tools.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E8-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] `POST /api/triggers/webhook/{trigger_id}` - Trigger execution
- [ ] Accepts JSON payload
- [ ] Payload available as `trigger.payload` in process
- [ ] Returns execution ID
- [ ] Optional: webhook secret for authentication

**Technical Notes:**
- Location: `src/backend/routers/triggers.py`

---

### E8-03: Trigger Management UI

**As a** process designer, **I want** to manage triggers in the UI, **so that** I can configure how processes start.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Core |
| Dependencies | E8-01, E8-02 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Triggers section in process editor
- [ ] Shows webhook URL (copy button)
- [ ] Enable/disable triggers
- [ ] Trigger history (recent invocations)

---

## Epic E13: Error Handling & Retry

> Robust error handling with retry policies and compensation

---

### E13-01: Retry Policy Configuration

**As a** process designer, **I want** to configure retry policies for steps, **so that** transient failures don't break processes.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E2-03 (MVP) |
| Status | done |

**Acceptance Criteria:**
- [x] `retry` field in step schema
- [x] Configurable: max_attempts, initial_delay, backoff_multiplier
- [x] Default retry policy (3 attempts, exponential backoff)
- [x] Step-level override
- [x] Retry count tracked in step execution state

**Technical Notes:**
- Reference: IT1 Section 2.1 (failure modes concern)
- Reference: IT2 Section 3 (Temporal patterns - retry policies)

---

### E13-02: Error Boundary Step

**As a** process designer, **I want** to define error handlers for steps, **so that** I can recover gracefully from failures.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P2 |
| Phase | Core |
| Dependencies | E13-01 |
| Status | done |

**Acceptance Criteria:**
- [x] `on_error` field in step schema
- [x] Options: fail_process, skip_step, goto_step (goto_step partial - logs warning and falls back)
- [x] Error handler can be another step or inline action (deferred to Advanced phase)
- [x] Error context passed to handler

**Technical Notes:**
- Reference: IT2 Section 2 (BPMN Error Boundary concept)

---

### E13-03: Compensation Handler

**As a** process designer, **I want** to define rollback actions, **so that** partial failures don't leave inconsistent state.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P3 |
| Phase | Core |
| Dependencies | E13-02 |
| Status | pending |

**Acceptance Criteria:**
- [ ] `compensation` field in step schema
- [ ] Compensation triggered on process failure after step completed
- [ ] Compensation steps run in reverse order
- [ ] Compensation history tracked

**Technical Notes:**
- Reference: IT2 Section 2 (BPMN Compensation concept)

---

### E13-04: Error Debugging UI

**As an** operator, **I want** detailed error information and suggested fixes, **so that** I can resolve issues quickly.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | Core |
| Dependencies | E4-03 (MVP) |
| Status | done |

**Acceptance Criteria:**
- [x] Error detail panel shows: error code, message, stack trace
- [x] Shows retry attempts with timestamps
- [x] Shows agent output before failure (via "Load output" in timeline)
- [ ] AI-powered fix suggestions (future enhancement - deferred)
- [x] One-click actions: Retry Step, Retry Process, Dismiss

**Technical Notes:**
- Reference: IT4 Section 8 (Error Handling & Debugging UI)

---

## Epic E14: Notification Step

> Send notifications to external channels

---

### E14-01: Notification Step Type

**As a** process designer, **I want** to send notifications as part of my process, **so that** stakeholders are informed.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Core |
| Dependencies | E2-03 (MVP) |
| Status | pending |

**Acceptance Criteria:**
- [ ] `notification` step type
- [ ] Channels: slack, email (start with one)
- [ ] Template message with `{{...}}` substitution
- [ ] Configuration: channel, recipients, message

**Technical Notes:**
- Reference: IT2 Section 4 (Architecture - NotificationHandler)

---

### E14-02: Notification Configuration

**As a** process designer, **I want** to configure notification channels, **so that** messages go to the right places.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | Core |
| Dependencies | E14-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Slack webhook URL configuration (per process or global)
- [ ] Email SMTP configuration (global)
- [ ] Channel validation (test notification)
- [ ] Notification templates library

---

## Manual Testing Checkpoints

After completing Core, verify:

| Checkpoint | Stories | Verification |
|------------|---------|--------------|
| **Parallel execution** | E5-01 to E5-03 | 3 steps run in parallel |
| **Approval workflow** | E6-01 to E6-05 | Process pauses, approver approves |
| **Gateway routing** | E7-01 to E7-03 | Condition routes to correct step |
| **Webhook trigger** | E8-01, E8-02 | External POST starts process |
| **Retry on failure** | E13-01 | Step retries 3x before failing |
| **Slack notification** | E14-01, E14-02 | Message arrives in Slack |

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-14 | Extracted Core stories from main backlog |
