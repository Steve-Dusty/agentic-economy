# Process-Driven Platform - MVP Backlog

> **Phase**: MVP
> **Goal**: Define and run simple sequential multi-agent processes
> **Epics**: E1, E2, E3, E4, E15
> **Stories**: 26
> **Reference**: See [`BACKLOG_INDEX.md`](./BACKLOG_INDEX.md) for conventions

---

## Sprint Plan

| Sprint | Stories | Focus |
|--------|---------|-------|
| **Sprint 1** | E1-01, E1-06, E1-02, E1-03, E15-01 | Foundation (Backend) |
| **Sprint 2** | E1-04, E2-01, E2-02, E2-06 | API & Basic Execution |
| **Sprint 3** | E2-03, E2-04, E2-07, E2-05 | Execution Engine |
| **Sprint 4** | E3-01, E3-02, E3-04 | Definition UI |
| **Sprint 5** | E4-01, E4-02, E4-03, E4-05 | Monitoring UI |
| **Sprint 6** | E3-03, E4-04, E15-02, E1-05 | Real-Time & Polish |
| **Sprint 6.5** | E15-03, E15-04 | Unfinished Business (MVP) |

---

## Dependency Graph

```
E1-01 (Schema)
  │
  ├──► E1-02 (Repo) ──► E1-04 (API) ──► E3-01 (List UI)
  │                          │
  ├──► E1-03 (Validation) ───┘
  │         │
  │         └──► E3-02 (Editor) ──► E3-03 (Preview) ──► E3-04 (Editor Page)
  │
  └──► E1-06 (Value Objects)
            │
            └──► E2-01 (Execution State)
                      │
                      └──► E2-02 (Exec Repo)
                                │
                                └──► E2-03 (Engine) ──► E2-04 (Agent Handler)
                                          │                    │
                                          │                    └──► E2-06 (Output Storage)
                                          │                              │
                                          │                              └──► E2-07 (Expression Sub)
                                          │
                                          └──► E2-05 (Exec API)
                                                    │
                                                    └──► E4-01 (List) ──► E4-05 (Dashboard)
                                                              │
                                                              └──► E4-02 (Timeline)
                                                                        │
                                                                        ├──► E4-03 (Step Detail)
                                                                        │
                                                                        └──► E4-04 (WebSocket)

E15-01 (Event Bus) ──► E15-02 (WebSocket Publisher)
                 │
                 ├──► E15-03 (Webhook Publisher)
                 │
                 └──► E15-04 (Event Log)
```

---

## Epic E1: Process Definition & Storage

> Foundation for defining, validating, and storing process definitions

---

### E1-01: Process Definition Schema

**As a** process designer, **I want** a clear YAML schema for defining processes, **so that** I can create valid, well-structured process definitions.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | None |
| Status | done |

**Acceptance Criteria:**
- [x] YAML schema supports: name, version, description, steps, outputs
- [x] Step schema supports: id, type, agent, message, depends_on, timeout
- [x] Step types defined: `agent_task`, `human_approval` (stub), `gateway` (stub)
- [x] Schema documented with examples
- [x] JSON Schema file created for editor validation

**Technical Notes:**
- Reference: IT3 Section 4 (Aggregates - ProcessDefinition)
- Location: `src/backend/process_engine/domain/`

---

### E1-02: Process Definition Repository

**As a** backend developer, **I want** a repository for storing process definitions, **so that** definitions persist across restarts.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E1-01 |
| Status | done |

**Acceptance Criteria:**
- [x] `ProcessDefinitionRepository` interface defined
- [x] SQLite implementation stores definitions
- [x] CRUD operations: create, get_by_id, get_by_name, list_all, update, delete
- [x] Version tracking: multiple versions per process name
- [x] Status field: draft, published, archived

**Technical Notes:**
- Reference: IT3 Section 7 (Repositories)
- Table: `process_definitions`

---

### E1-03: Process Definition Validation

**As a** process designer, **I want** my process definitions validated before saving, **so that** I catch errors early.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E1-01 |
| Status | done |

**Acceptance Criteria:**
- [x] Schema validation (required fields, types)
- [x] Semantic validation:
  - [x] No duplicate step IDs
  - [x] All `depends_on` references exist
  - [x] No circular dependencies
  - [x] Referenced agents exist (warning if not running)
- [x] Clear error messages with line numbers
- [x] Validation service callable from API and UI

**Technical Notes:**
- Reference: IT3 Section 6 (Domain Services - DependencyResolver)
- Implement as `ProcessValidator` service

---

### E1-04: Process Definition API Endpoints

**As a** frontend developer, **I want** REST API endpoints for process definitions, **so that** the UI can manage processes.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E1-02, E1-03 |
| Status | done |

**Acceptance Criteria:**
- [x] `POST /api/processes` - Create new process definition
- [x] `GET /api/processes` - List all process definitions
- [x] `GET /api/processes/{id}` - Get single definition
- [x] `PUT /api/processes/{id}` - Update definition
- [x] `DELETE /api/processes/{id}` - Delete definition
- [x] `POST /api/processes/{id}/validate` - Validate without saving
- [x] `POST /api/processes/{id}/publish` - Publish a draft
- [x] All endpoints require authentication
- [x] OpenAPI documentation complete

**Technical Notes:**
- Location: `src/backend/routers/processes.py`
- Follow existing Trinity API patterns

---

### E1-05: Process Definition Domain Events

**As a** system architect, **I want** domain events emitted on process definition changes, **so that** other components can react.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P2 |
| Phase | MVP |
| Dependencies | E1-02, E15-01 |
| Status | done |

**Acceptance Criteria:**
- [x] Events defined: `ProcessCreated`, `ProcessUpdated`, `ProcessPublished`, `ProcessArchived`
- [x] Events include: process_id, timestamp, user_id, version
- [x] Event bus integration (initially just logging, extensible)

**Technical Notes:**
- Reference: IT3 Section 5 (Domain Events)
- Keep simple for MVP - just emit and log

---

### E1-06: Process Definition Value Objects

**As a** backend developer, **I want** proper value objects for process concepts, **so that** the code is type-safe and expressive.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Phase | MVP |
| Dependencies | None |
| Status | done |

**Acceptance Criteria:**
- [x] `ProcessId` - UUID wrapper with validation
- [x] `StepId` - String identifier with format validation
- [x] `Version` - Semantic version (1, 2, 3...)
- [x] `Duration` - Timeout representation with parsing ("30s", "5m")
- [x] `Money` - Cost representation (amount, currency)
- [x] All value objects are immutable (frozen dataclasses)

**Technical Notes:**
- Reference: IT3 Section 4.3 (Value Objects)
- Location: `src/backend/process_engine/domain/value_objects.py`

---

## Epic E2: Sequential Execution Engine

> Execute processes step-by-step, one step at a time

---

### E2-01: Execution State Model

**As a** backend developer, **I want** a model for tracking execution state, **so that** I can persist and resume executions.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E1-06 |
| Status | done |

**Acceptance Criteria:**
- [x] `ProcessExecution` aggregate defined with:
  - [x] execution_id, process_id, process_version
  - [x] status: pending, running, completed, failed, cancelled
  - [x] step_executions: dict of StepId → StepExecution
  - [x] started_at, completed_at, total_cost, total_duration
- [x] `StepExecution` entity defined with:
  - [x] step_id, status, started_at, completed_at
  - [x] input, output, error, cost, duration
- [x] State transitions are validated (e.g., can't complete a non-running step)

**Technical Notes:**
- Reference: IT3 Section 4.2 (ProcessExecution Aggregate)
- Execution is the aggregate root

---

### E2-02: Execution Repository

**As a** backend developer, **I want** a repository for storing executions, **so that** execution state persists.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E2-01 |
| Status | done |

**Acceptance Criteria:**
- [x] `ExecutionRepository` interface defined
- [x] SQLite implementation with tables:
  - [x] `process_executions` - Main execution record
  - [x] `step_executions` - Per-step state
- [x] Operations: create, get_by_id, update, list_by_process, list_active
- [x] Optimistic locking for concurrent updates

**Technical Notes:**
- Reference: IT3 Section 7 (Repositories)
- Consider Redis for active executions (future optimization)

---

### E2-03: Sequential Step Executor

**As a** system, **I want** to execute steps sequentially based on dependencies, **so that** processes run in the correct order.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E2-01, E2-02, E1-03 |
| Status | done |

**Acceptance Criteria:**
- [x] `ExecutionEngine` service that:
  - [x] Starts execution from a process definition
  - [x] Resolves step dependencies to determine order
  - [x] Executes steps one at a time (sequential MVP)
  - [x] Updates execution state after each step
  - [x] Handles step success → marks complete, captures output
  - [x] Handles step failure → marks failed, captures error
- [x] Execution is resumable (can restart from last state)
- [x] Timeout handling per step

**Technical Notes:**
- Reference: IT2 Section 6 (Phased Implementation - Phase 1)
- Location: `src/backend/process_engine/application/execution_engine.py`

---

### E2-04: Agent Task Step Handler

**As a** system, **I want** to execute `agent_task` steps by sending messages to agents, **so that** agents do work within processes.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E2-03 |
| Status | done |

**Acceptance Criteria:**
- [x] `AgentGateway` anti-corruption layer created
- [x] Gateway wraps existing Trinity MCP client
- [x] Sends message to specified agent
- [x] Waits for response (with timeout)
- [x] Captures response as step output
- [x] Handles agent errors gracefully
- [x] Supports context passing (previous step outputs available)

**Technical Notes:**
- Reference: IT3 Section 8 (Anti-Corruption Layers - AgentGateway)
- Reuse existing `chat_with_agent` MCP tool

---

### E2-05: Execution API Endpoints

**As a** frontend developer, **I want** REST API endpoints for executions, **so that** the UI can start and monitor processes.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E2-03 |
| Status | done |

**Acceptance Criteria:**
- [x] `POST /api/processes/{id}/execute` - Start new execution
- [x] `GET /api/executions` - List executions (with filters)
- [x] `GET /api/executions/{id}` - Get execution detail
- [x] `POST /api/executions/{id}/cancel` - Cancel running execution
- [x] `POST /api/executions/{id}/retry` - Retry failed execution
- [x] All endpoints require authentication
- [x] OpenAPI documentation complete (via FastAPI auto-docs)

**Technical Notes:**
- Location: `src/backend/routers/executions.py`

---

### E2-06: Step Output Storage

**As a** system, **I want** standardized storage for step outputs, **so that** data flows reliably between steps.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | MVP |
| Dependencies | E2-03 |
| Status | done |

**Acceptance Criteria:**
- [x] Step outputs stored in standardized location (not agent responsibility)
- [x] Output path pattern: `/executions/{exec_id}/steps/{step_id}/output`
- [x] Outputs persisted to SQLite (small) or filesystem (large)
- [x] Previous step outputs accessible via `{{steps.X.output}}` syntax
- [x] Output cleanup policy (TTL or on execution archive)

**Technical Notes:**
- Reference: IT1 Section 2.4 (Output Storage as "Agent Responsibility" concern)
- Platform-managed, not agent-managed

---

### E2-07: Expression Substitution in Messages

**As a** process designer, **I want** to reference previous step outputs in messages, **so that** data flows between steps.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E2-06 |
| Status | done |

**Acceptance Criteria:**
- [x] `{{steps.X.output}}` syntax supported in step messages
- [x] `{{input.X}}` for process input data (trigger.payload maps to input)
- [x] `{{execution.id}}` and other context variables
- [x] Jinja2-style templating (familiar syntax)
- [x] Clear errors for undefined references (strict mode)

**Technical Notes:**
- Reference: IT2 Section 6 (Expression Language choice)
- Reference: IT3 Section 6 (ExpressionEvaluator)

---

## Epic E3: Process Definition UI

> UI for creating and editing process definitions

---

### E3-01: Process List View

**As a** process designer, **I want** to see all my processes in a list, **so that** I can manage them.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E1-04 |
| Status | done |

**Acceptance Criteria:**
- [x] Table/card view showing all processes
- [x] Columns: Name, Version, Status, Last Run, Created
- [x] Status badges: Draft, Published, Archived
- [x] Actions: Edit, Delete, Execute, View Executions
- [x] Sorting and filtering
- [x] Empty state with "Create Process" CTA

**Technical Notes:**
- Reference: IT4 Section 10 (Navigation Structure)
- Location: `src/frontend/src/views/ProcessList.vue`

---

### E3-02: YAML Editor Component

**As a** process designer, **I want** a code editor for writing process YAML, **so that** I can define processes efficiently.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E1-03 |
| Status | done |

**Acceptance Criteria:**
- [x] Monaco editor or CodeMirror integration
- [x] YAML syntax highlighting
- [x] Line numbers
- [x] Inline validation errors (from E1-03)
- [x] Error markers on specific lines
- [x] Basic auto-indent

**Technical Notes:**
- Reference: IT4 Section 3 (Process Definition UI)
- Consider: vue-codemirror or monaco-editor

---

### E3-03: Live Process Preview

**As a** process designer, **I want** a visual preview of my process as I edit, **so that** I can verify the flow.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P1 |
| Phase | MVP |
| Dependencies | E3-02 |
| Status | done |

**Acceptance Criteria:**
- [x] Simple flow diagram rendering
- [x] Shows: steps as boxes, arrows for dependencies
- [x] Updates as YAML changes (debounced)
- [x] Highlights validation errors on diagram
- [x] Horizontal or vertical layout option

**Technical Notes:**
- Reference: IT4 Section 3.2 (Layout - Live Preview)
- Options: D3.js, Mermaid, or custom SVG

---

### E3-04: Process Editor Page

**As a** process designer, **I want** a full editor page with YAML and preview, **so that** I can create and edit processes.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E3-02, E3-03 |
| Status | done |

**Acceptance Criteria:**
- [x] Split view: Editor (60%) + Preview (40%) - (MVP: editor with validation panel)
- [x] Validation panel at bottom
- [x] Save button (creates/updates definition)
- [x] Publish button (for drafts)
- [x] Discard changes confirmation
- [x] Keyboard shortcuts (Cmd+S to save)

**Technical Notes:**
- Reference: IT4 Section 3.2 (Layout)
- Location: `src/frontend/src/views/ProcessEditor.vue`

---

## Epic E4: Execution Monitoring UI

> UI for viewing and managing process executions

---

### E4-01: Execution List View

**As an** operator, **I want** to see all executions, **so that** I can monitor process health.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E2-05 |
| Status | done |

**Acceptance Criteria:**
- [x] Table showing executions
- [x] Columns: Process Name, Status, Started, Duration, Cost
- [x] Status icons: ✅ ❌ 🔄 ⏳
- [x] Filters: by process, by status, date range
- [x] Click to view detail
- [x] Auto-refresh (polling 30s)

**Technical Notes:**
- Reference: IT4 Section 7 (Dashboard UI)
- Location: `src/frontend/src/views/ExecutionList.vue`

---

### E4-02: Execution Timeline View

**As an** operator, **I want** to see execution progress as a timeline, **so that** I understand what's happening.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P0 |
| Phase | MVP |
| Dependencies | E2-05 |
| Status | done |

**Acceptance Criteria:**
- [x] Horizontal timeline showing all steps
- [x] Each step shows: name, status icon, duration bar, cost
- [x] Completed steps show output summary (truncated)
- [x] Running step highlighted
- [x] Failed step shows error summary
- [x] Click step to expand details

**Technical Notes:**
- Reference: IT4 Section 4 (Execution Timeline UI)
- Location: `src/frontend/src/components/ExecutionTimeline.vue`

---

### E4-03: Step Detail Panel

**As an** operator, **I want** to see full step details, **so that** I can debug issues.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | MVP |
| Dependencies | E4-02 |
| Status | done |

**Acceptance Criteria:**
- [x] Expandable panel within timeline
- [x] Shows: agent name, full input, full output
- [x] Shows: start time, end time, duration, cost
- [x] For failed steps: full error message, stack trace
- [x] Copy output/error to clipboard

**Technical Notes:**
- Reference: IT4 Section 4.4 (Expanded Step View)

---

### E4-04: Execution WebSocket Updates

**As an** operator, **I want** real-time updates when viewing an execution, **so that** I see changes immediately.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | MVP |
| Dependencies | E4-02, E15-02 |
| Status | done |

**Acceptance Criteria:**
- [x] WebSocket connection when viewing execution detail
- [x] Events: step_started, step_completed, step_failed, execution_completed
- [x] UI updates without refresh
- [x] Connection indicator ("Live" badge)
- [x] Graceful reconnection on disconnect

**Technical Notes:**
- Reference: IT4 Section 6 (Real-Time Updates)
- Reuse existing Trinity WebSocket infrastructure if available

---

### E4-05: Process Dashboard

**As a** manager, **I want** a dashboard showing process health at a glance, **so that** I can identify issues quickly.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P1 |
| Phase | MVP |
| Dependencies | E4-01 |
| Status | done |

**Acceptance Criteria:**
- [x] Quick stats bar: Active, Pending Approval, Failed (24h)
- [x] Active executions list with progress
- [x] Process health cards showing:
  - [x] Success rate (%)
  - [x] Average duration
  - [x] Average cost
  - [x] Next scheduled run
- [x] "Needs Attention" section: recent failures, overdue approvals
- [x] Click-through to details

**Technical Notes:**
- Reference: IT4 Section 7 (Dashboard UI)
- Distinct from E4-01 (execution list) - this is the landing page

---

## Epic E15: Event Publishing Infrastructure

> Domain events for UI updates, webhooks, and agent awareness

---

### E15-01: Domain Event Bus

**As a** system architect, **I want** a central event bus for domain events, **so that** components can react to changes.

| Attribute | Value |
|-----------|-------|
| Size | L |
| Priority | P1 |
| Phase | MVP |
| Dependencies | None |
| Status | done |

**Acceptance Criteria:**
- [x] `EventPublisher` interface defined
- [x] In-memory implementation for MVP
- [x] Events: ProcessStarted, ProcessCompleted, ProcessFailed, StepStarted, StepCompleted, StepFailed, ApprovalRequested, ApprovalDecided
- [x] Subscribe pattern for handlers
- [x] Async event dispatch (non-blocking)

**Technical Notes:**
- Reference: IT3 Section 5 (Domain Events)
- Reference: IT1 Section 2.8 (Event Bus dependency)

---

### E15-02: WebSocket Event Publisher

**As a** frontend developer, **I want** domain events published via WebSocket, **so that** the UI updates in real-time.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Phase | MVP |
| Dependencies | E15-01 |
| Status | done |

**Acceptance Criteria:**
- [x] WebSocket handler subscribes to relevant events
- [x] Events broadcast to connected clients
- [x] Client can subscribe to specific executions
- [x] Event format matches IT4 Section 6.2 specification

**Technical Notes:**
- Reference: IT4 Section 6 (Real-Time Updates)
- Reference: IT3 Section 5 (WebSocketEventPublisher)

---

### E15-03: Webhook Event Publisher

**As an** integrator, **I want** to receive process events via webhook, **so that** external systems can react.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | MVP |
| Dependencies | E15-01 |
| Status | pending |

**Acceptance Criteria:**
- [ ] Webhook URLs configurable per process
- [ ] Events: process_completed, process_failed, approval_requested
- [ ] Webhook payload includes execution context
- [ ] Retry on webhook failure (3 attempts)
- [ ] Webhook signature for security

**Technical Notes:**
- Reference: IT3 Section 5 (WebhookPublisher)

---

### E15-04: Execution Event Log

**As an** operator, **I want** a complete audit log of execution events, **so that** I can debug issues and maintain compliance.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Phase | MVP |
| Dependencies | E15-01 |
| Status | done |

**Acceptance Criteria:**
- [x] `execution_events` table stores all domain events
- [x] Events stored with: event_type, execution_id, step_id, payload, timestamp
- [x] Events persisted before handlers are called (reliable)
- [x] Query API: `GET /api/executions/{id}/events`
- [x] Events retained for configurable period (default: 30 days)
- [x] UI: Event history tab in execution detail view

**Technical Notes:**
- Reference: IT3 Section 12 (Open Questions - Event Sourcing)
- This is audit logging, NOT full event sourcing
- State is still stored directly; events are for history/debugging
- Enables future migration to event sourcing if needed

---

## Manual Testing Checkpoints

After completing MVP, verify:

| Checkpoint | Stories | Verification |
|------------|---------|--------------|
| **Can create process** | E1-01 to E1-04, E3-01 to E3-04 | Create a 3-step process via UI |
| **Can run process** | E2-01 to E2-05 | Execute process, see it complete |
| **Can view execution** | E4-01 to E4-03 | View timeline, expand steps |
| **Real-time updates** | E15-01, E15-02, E4-04 | See step updates live |
| **Data flows between steps** | E2-06, E2-07 | Step 2 receives Step 1 output |
| **Event audit log** | E15-04 | View event history for execution |

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-14 | Extracted MVP stories from main backlog |
