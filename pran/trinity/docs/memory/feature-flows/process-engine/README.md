# Process Engine Feature Flows

> **Status**: Implemented (Sprints 12-16)
> **Location**: `src/backend/services/process_engine/`
> **Frontend**: `src/frontend/src/views/Process*.vue`

---

## Overview

The Process Engine is a **BPMN-inspired workflow orchestration layer** built on top of Trinity's agent infrastructure. It enables declarative process definitions (YAML) that orchestrate agents, handle approvals, manage branching logic, and track execution state.

**Key Differentiator**: Unlike traditional workflow engines (Temporal, Airflow), the Process Engine treats agents as stateful entities that learn and adapt, implementing the **EMI (Executor/Monitor/Informed) role pattern**.

---

## Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                              Frontend (Vue.js)                                     |
|  +----------------+  +------------------+  +------------------+  +--------------+  |
|  | ProcessList.vue|  |ProcessEditor.vue |  |ProcessDashboard  |  |ProcessExecution|
|  | List processes |  | YAML + Preview   |  |.vue Analytics    |  |Detail.vue      |
|  +-------+--------+  +--------+---------+  +--------+---------+  +-------+------+  |
+----------|--------------------|---------------------|--------------------|---------+
           |                    |                     |                    |
           v                    v                     v                    v
+-----------------------------------------------------------------------------------+
|                              Backend (FastAPI)                                     |
|  +-------------------------------------------------------------------------+      |
|  |  routers/processes.py          routers/executions.py                    |      |
|  |  - CRUD for definitions        - Start, cancel, retry executions        |      |
|  |  - Validate, publish, archive  - Get status, list by process            |      |
|  |  - Analytics endpoints         - Approval management                    |      |
|  +-------------------------------------------------------------------------+      |
|                                     |                                              |
|                                     v                                              |
|  +-------------------------------------------------------------------------+      |
|  |                        services/process_engine/                          |      |
|  |  +-------------+  +-------------+  +-------------+  +------------------+ |      |
|  |  |   domain/   |  |   engine/   |  | repositories|  |     services/    | |      |
|  |  | - aggregates|  | - execution |  | - sqlite_*  |  | - validator      | |      |
|  |  | - entities  |  |   _engine   |  | - interfaces|  | - analytics      | |      |
|  |  | - events    |  | - handlers/ |  +-------------+  | - alerts         | |      |
|  |  | - enums     |  | - dependency|                   | - informed_notif | |      |
|  |  | - value_obj |  |   _resolver |                   | - output_storage | |      |
|  |  +-------------+  +-------------+                   +------------------+ |      |
|  +-------------------------------------------------------------------------+      |
|                                     |                                              |
|  +----------------------------------+--------------------------------------+       |
|  |                         events/                                          |       |
|  |  +-------------+  +-------------------+  +-----------------+             |       |
|  |  |    bus.py   |  |websocket_pub.py   |  | webhook_pub.py  |             |       |
|  |  | InMemory    |  | Real-time UI      |  | External notify |             |       |
|  |  +-------------+  +-------------------+  +-----------------+             |       |
|  +-------------------------------------------------------------------------+       |
+-----------------------------------------------------------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------------------+
|                            Agent Containers                                        |
|  +-------------+  +-------------+  +-------------+  +-------------+               |
|  |  Agent A    |  |  Agent B    |  |  Agent C    |  |  Agent N    |               |
|  | (Executor)  |  | (Executor)  |  | (Informed)  |  | (Monitor)   |               |
|  +-------------+  +-------------+  +-------------+  +-------------+               |
+-----------------------------------------------------------------------------------+
```

---

## The Six Step Types

The Process Engine supports six step types, each handled by a dedicated handler:

| Type | Handler | File | Description |
|------|---------|------|-------------|
| `agent_task` | `AgentTaskHandler` | `engine/handlers/agent_task.py` | Execute task via Trinity agent with Claude Code |
| `human_approval` | `HumanApprovalHandler` | `engine/handlers/human_approval.py` | Gate requiring human approval/rejection decision |
| `gateway` | `GatewayHandler` | `engine/handlers/gateway.py` | Conditional branching (exclusive or parallel routes) |
| `timer` | `TimerHandler` | `engine/handlers/timer.py` | Wait for duration or until specific timestamp |
| `notification` | `NotificationHandler` | `engine/handlers/notification.py` | Send Slack, webhook, or email notifications |
| `sub_process` | `SubProcessHandler` | `engine/handlers/sub_process.py` | Call another process definition as a nested step |

### Step Type YAML Examples

```yaml
# agent_task - Execute with AI agent
- id: analyze
  type: agent_task
  agent: analyst
  message: "Analyze this data: {{input.data}}"
  timeout: 10m

# human_approval - Gate for human decision
- id: approve-budget
  type: human_approval
  title: "Approve budget for {{input.project}}"
  description: "Review the proposed budget of ${{steps.calculate.output.amount}}"
  assignees: ["finance@example.com"]
  timeout: 24h

# gateway - Conditional routing
- id: route-priority
  type: gateway
  gateway_type: exclusive
  routes:
    - condition: "steps.analyze.output.score > 80"
      next_step: fast-track
    - condition: "steps.analyze.output.score <= 80"
      next_step: standard-review
  default_route: standard-review

# timer - Wait before proceeding
- id: wait-period
  type: timer
  duration: 1h
  depends_on: [notify-stakeholders]

# notification - Send alerts
- id: notify-team
  type: notification
  channel: slack
  webhook_url: "${SLACK_WEBHOOK}"
  message: "Process completed: {{process.name}}"

# sub_process - Nested process call
- id: run-validation
  type: sub_process
  process_name: data-validation
  input_mapping:
    dataset: "{{steps.prepare.output.data}}"
  output_key: validation_result
```

---

## Execution State Machine

```
                            +------------------+
                            |                  |
                            v                  |
    +----------+      +-----------+      +----------+
    |          |      |           |      |          |
    | PENDING  +----->+  RUNNING  +----->+ COMPLETED|
    |          |      |           |      |          |
    +----------+      +-----+-----+      +----------+
                            |
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
        +----------+  +----------+  +----------+
        |          |  |          |  |          |
        |  PAUSED  |  |  FAILED  |  | CANCELLED|
        | (waiting |  |          |  |          |
        | approval)|  +----------+  +----------+
        +----+-----+
             |
             | (approval received)
             |
             v
       Back to RUNNING
```

### State Transitions

| From State | To State | Trigger |
|------------|----------|---------|
| `PENDING` | `RUNNING` | `execution.start()` |
| `RUNNING` | `COMPLETED` | All steps complete successfully |
| `RUNNING` | `FAILED` | Step failure after retries exhausted |
| `RUNNING` | `PAUSED` | Human approval step waiting for decision |
| `RUNNING` | `CANCELLED` | User cancellation request |
| `PAUSED` | `RUNNING` | Approval decision received (resume) |
| `PAUSED` | `CANCELLED` | User cancellation while paused |

### Step Status Values

| Status | Description |
|--------|-------------|
| `PENDING` | Not yet started, waiting for dependencies |
| `READY` | Dependencies met, ready to execute |
| `RUNNING` | Currently executing |
| `WAITING_APPROVAL` | Human approval step awaiting decision |
| `COMPLETED` | Finished successfully |
| `FAILED` | Finished with error after all retries |
| `SKIPPED` | Condition not met or error policy skip |

---

## EMI Role Pattern

The EMI (Executor/Monitor/Informed) pattern assigns responsibility roles to agents for each step:

| Role | Purpose | Cardinality | Behavior |
|------|---------|-------------|----------|
| **Executor** | Performs the work | Exactly 1 | Required; the agent that runs the task |
| **Monitor** | Owns outcome | 0 or more | Can intervene; receives alerts on failure |
| **Informed** | Learns from events | 0 or more | Receives notifications written to agent memory |

### EMI YAML Configuration

```yaml
steps:
  - id: research
    type: agent_task
    agent: researcher
    message: "Research: {{input.topic}}"
    roles:
      executor: researcher      # Who does the work
      monitors:                 # Who can intervene
        - supervisor
        - qa-lead
      informed:                 # Who gets notified
        - team-lead
        - historian
```

### InformedNotifier Service

The `InformedAgentNotifier` service (`services/informed_notifier.py`) handles notification delivery:

1. **MCP Delivery**: Sends notification via Trinity MCP `chat_with_agent` tool
2. **Memory Write**: Writes event to agent's `~/agent_memory/events/` directory
3. **Parallel Delivery**: Runs asynchronously to avoid blocking execution

---

## Template Variables

All step handlers support template variable substitution using Jinja2-style syntax. Variables are evaluated at runtime by `ExpressionEvaluator` (`services/expression_evaluator.py`).

### Supported Variable Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `{{input.X}}` | Process input data field | `{{input.topic}}` |
| `{{steps.X.output}}` | Full output from step X | `{{steps.research.output}}` |
| `{{steps.X.output.Y}}` | Nested field in step output | `{{steps.analyze.output.score}}` |
| `{{execution.id}}` | Current execution ID | `exec_abc123...` |
| `{{process.name}}` | Process definition name | `content-pipeline` |

### Handler Template Field Support

| Handler | Fields Supporting Variables |
|---------|----------------------------|
| `agent_task` | `message` |
| `human_approval` | `title`, `description` |
| `notification` | `message`, `subject` |
| `gateway` | `routes[].condition` |
| `sub_process` | `input_mapping` values |

---

## Feature Flow Index

| Document | Priority | Description |
|----------|----------|-------------|
| [process-definition.md](./process-definition.md) | High | YAML schema, validation, versioning |
| [process-execution.md](./process-execution.md) | High | Engine, step handlers, state machine, compensation |
| [process-monitoring.md](./process-monitoring.md) | High | UI views, WebSocket events, dashboards |
| [human-approval.md](./human-approval.md) | Medium | Approval gates, inbox, timeout handling, variable substitution |
| [process-scheduling.md](./process-scheduling.md) | Medium | Cron triggers, timer steps, schedule registration |
| [process-analytics.md](./process-analytics.md) | Medium | Cost tracking, alerts, metrics, trends |
| [sub-processes.md](./sub-processes.md) | Medium | Parent-child linking, breadcrumbs, input/output mapping |
| [agent-roles-emi.md](./agent-roles-emi.md) | Medium | EMI pattern, InformedNotifier, memory writes |
| [process-templates.md](./process-templates.md) | Low | Bundled templates, user templates, management |
| [onboarding-documentation.md](./onboarding-documentation.md) | Low | Empty state, docs tab, help panel, wizard |

---

## Key Entry Points

### UI Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/processes` | `ProcessList.vue` | List all process definitions with status filter |
| `/processes/new` | `ProcessEditor.vue` | Create new process (YAML editor) |
| `/processes/:id` | `ProcessEditor.vue` | Edit existing draft process |
| `/process-dashboard` | `ProcessDashboard.vue` | Analytics metrics and trend charts |
| `/executions` | `ExecutionList.vue` | List all executions with filters |
| `/executions/:id` | `ProcessExecutionDetail.vue` | Execution timeline and step status |
| `/approvals` | `Approvals.vue` | Pending approval inbox |

### API Endpoints

| Method | Endpoint | Router | Description |
|--------|----------|--------|-------------|
| `POST` | `/api/processes` | `processes.py:209` | Create new definition |
| `GET` | `/api/processes` | `processes.py:262` | List definitions with filters |
| `GET` | `/api/processes/{id}` | `processes.py:310` | Get single definition |
| `PUT` | `/api/processes/{id}` | `processes.py:343` | Update draft definition |
| `DELETE` | `/api/processes/{id}` | `processes.py:423` | Delete draft/archived definition |
| `POST` | `/api/processes/{id}/publish` | `processes.py:508` | Publish draft to immutable |
| `POST` | `/api/processes/{id}/archive` | `processes.py:573` | Archive published definition |
| `POST` | `/api/processes/validate` | `processes.py:492` | Validate YAML without saving |
| `GET` | `/api/processes/{id}/analytics` | `processes.py:935` | Get process metrics |
| `POST` | `/api/executions/{process_id}/start` | `executions.py` | Start new execution |
| `GET` | `/api/executions` | `executions.py` | List executions |
| `GET` | `/api/executions/{id}` | `executions.py` | Get execution details |
| `POST` | `/api/executions/{id}/cancel` | `executions.py` | Cancel running execution |
| `POST` | `/api/executions/{id}/retry` | `executions.py` | Retry failed execution |
| `GET` | `/api/approvals` | `executions.py` | List pending approvals |
| `POST` | `/api/approvals/{id}/decide` | `executions.py` | Approve or reject |
| `GET` | `/api/process-templates` | `process_templates.py:106` | List available templates |
| `GET` | `/api/process-templates/{id}` | `process_templates.py:277` | Get template details |
| `POST` | `/api/process-templates/{id}/use` | `process_templates.py:172` | Create process from template |

---

## Backend Service Directory Structure

```
src/backend/services/process_engine/
|-- __init__.py                     # Package exports
|-- domain/
|   |-- __init__.py                 # Domain exports
|   |-- aggregates.py               # ProcessDefinition, ProcessExecution
|   |-- entities.py                 # StepDefinition, StepExecution, ApprovalRequest
|   |-- enums.py                    # DefinitionStatus, ExecutionStatus, StepType, AgentRole
|   |-- events.py                   # ProcessStarted, StepCompleted, etc.
|   |-- exceptions.py               # ProcessValidationError, CircularDependencyError
|   |-- step_configs.py             # AgentTaskConfig, HumanApprovalConfig, etc.
|   +-- value_objects.py            # ProcessId, ExecutionId, Money, Duration, RetryPolicy
|
|-- engine/
|   |-- __init__.py                 # Engine exports
|   |-- execution_engine.py         # Core orchestrator (1086 lines)
|   |-- dependency_resolver.py      # Topological sort, parallel detection
|   |-- step_handler.py             # Base handler class, registry
|   +-- handlers/
|       |-- __init__.py             # Handler exports
|       |-- agent_task.py           # AgentTaskHandler
|       |-- human_approval.py       # HumanApprovalHandler
|       |-- gateway.py              # GatewayHandler
|       |-- timer.py                # TimerHandler
|       |-- notification.py         # NotificationHandler
|       +-- sub_process.py          # SubProcessHandler
|
|-- repositories/
|   |-- __init__.py                 # Repository exports
|   |-- interfaces.py               # Abstract repository interfaces
|   |-- sqlite_definitions.py       # ProcessDefinition persistence
|   |-- sqlite_executions.py        # ProcessExecution persistence
|   |-- sqlite_events.py            # Event log persistence
|   +-- audit.py                    # Audit trail repository
|
|-- services/
|   |-- __init__.py                 # Service exports
|   |-- validator.py                # YAML validation, schema checking
|   |-- analytics.py                # ProcessAnalytics, metrics calculation
|   |-- alerts.py                   # CostAlertService, threshold monitoring
|   |-- expression_evaluator.py     # Template variable substitution
|   |-- informed_notifier.py        # EMI notification delivery
|   |-- output_storage.py           # Step output persistence
|   |-- event_logger.py             # Event stream logging
|   |-- templates.py                # ProcessTemplateService
|   |-- authorization.py            # ProcessAuthorizationService
|   |-- limits.py                   # ExecutionLimitService
|   |-- recovery.py                 # Execution recovery service
|   +-- audit.py                    # Audit service
|
+-- events/
    |-- __init__.py                 # Event bus exports
    |-- bus.py                      # InMemoryEventBus
    |-- websocket_publisher.py      # Real-time UI updates
    +-- webhook_publisher.py        # External webhook notifications
```

---

## Database Tables

### Process Definitions Database (`trinity_processes.db`)

```sql
CREATE TABLE process_definitions (
    id TEXT PRIMARY KEY,              -- ProcessId (UUID)
    name TEXT NOT NULL,               -- Human-readable name
    description TEXT,                 -- Process description
    version TEXT NOT NULL,            -- Version string (e.g., "1.0.0")
    status TEXT NOT NULL,             -- draft | published | archived
    yaml_content TEXT NOT NULL,       -- Original YAML source
    steps_json TEXT,                  -- Serialized StepDefinition[]
    outputs_json TEXT,                -- Serialized OutputConfig[]
    triggers_json TEXT,               -- Serialized TriggerConfig[]
    created_by TEXT,                  -- User email
    created_at TEXT NOT NULL,         -- ISO timestamp
    updated_at TEXT NOT NULL,         -- ISO timestamp
    published_at TEXT                 -- ISO timestamp (when published)
);
```

### Process Executions Database (`trinity_executions.db`)

```sql
CREATE TABLE process_executions (
    id TEXT PRIMARY KEY,              -- ExecutionId (UUID)
    process_id TEXT NOT NULL,         -- ProcessId reference
    process_name TEXT NOT NULL,       -- Denormalized for queries
    process_version TEXT NOT NULL,    -- Version at execution time
    status TEXT NOT NULL,             -- pending | running | completed | failed | cancelled | paused
    input_data TEXT,                  -- JSON input payload
    output_data TEXT,                 -- JSON output result
    step_executions TEXT,             -- JSON map: step_id -> StepExecution
    triggered_by TEXT,                -- manual | schedule | api | sub_process
    started_at TEXT,                  -- ISO timestamp
    completed_at TEXT,                -- ISO timestamp
    total_cost TEXT,                  -- Cost string (e.g., "$1.23")
    retry_of TEXT,                    -- Original ExecutionId if retry
    parent_execution_id TEXT,         -- Parent if sub-process
    parent_step_id TEXT,              -- Step that spawned this sub-process
    child_execution_ids TEXT          -- JSON array of child ExecutionIds
);

CREATE TABLE approval_requests (
    id TEXT PRIMARY KEY,              -- ApprovalRequest UUID
    execution_id TEXT NOT NULL,       -- ExecutionId reference
    step_id TEXT NOT NULL,            -- StepId reference
    title TEXT NOT NULL,              -- Approval title
    description TEXT,                 -- Approval description
    assignees TEXT,                   -- JSON array of user emails
    status TEXT NOT NULL,             -- pending | approved | rejected | expired
    deadline TEXT,                    -- ISO timestamp
    created_at TEXT NOT NULL,         -- ISO timestamp
    decided_at TEXT,                  -- ISO timestamp
    decided_by TEXT,                  -- User email
    decision_comment TEXT             -- Optional comment
);
```

### Process Schedules (`trinity.db`)

```sql
CREATE TABLE IF NOT EXISTS process_schedules (
    id TEXT PRIMARY KEY,              -- Schedule UUID
    process_id TEXT NOT NULL,         -- ProcessId reference
    process_name TEXT NOT NULL,       -- Denormalized name
    trigger_id TEXT NOT NULL,         -- Trigger ID from definition
    cron_expression TEXT NOT NULL,    -- Cron schedule
    enabled INTEGER DEFAULT 1,        -- 0 or 1
    timezone TEXT DEFAULT 'UTC',      -- Timezone name
    description TEXT,                 -- Schedule description
    created_at TEXT NOT NULL,         -- ISO timestamp
    updated_at TEXT NOT NULL,         -- ISO timestamp
    last_run_at TEXT,                 -- ISO timestamp
    next_run_at TEXT,                 -- ISO timestamp (computed)
    UNIQUE(process_id, trigger_id)
);
```

---

## Domain-Driven Design Concepts

The Process Engine follows DDD principles:

| Concept | Implementation | Purpose |
|---------|----------------|---------|
| **Aggregates** | `ProcessDefinition`, `ProcessExecution` | Consistency boundaries, root entities |
| **Entities** | `StepDefinition`, `StepExecution`, `ApprovalRequest` | Objects with identity within aggregates |
| **Value Objects** | `ProcessId`, `ExecutionId`, `StepId`, `Money`, `Duration` | Immutable, identity-less objects |
| **Domain Events** | `ProcessStarted`, `StepCompleted`, `ProcessFailed` | Record state changes |
| **Repositories** | `SqliteProcessDefinitionRepository`, `SqliteProcessExecutionRepository` | Persistence abstraction |

---

## Related Flows (Outside Process Engine)

| Flow | Relation |
|------|----------|
| [scheduling.md](../scheduling.md) | Process triggers use scheduler infrastructure |
| [agent-terminal.md](../agent-terminal.md) | Agent task steps communicate via same AgentClient |
| [execution-queue.md](../execution-queue.md) | Agent tasks respect queue system for parallel prevention |
| [mcp-orchestration.md](../mcp-orchestration.md) | EMI notifications can use MCP for agent communication |
| [activity-stream.md](../activity-stream.md) | Process events recorded in activity stream |

---

## Implementation References

| Document | Purpose |
|----------|---------|
| `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT1.md` | Initial analysis and EMI pattern design |
| `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT2.md` | Step types and YAML schema design |
| `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT3.md` | DDD architecture and domain model |
| `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT4.md` | UI/UX design and frontend flows |
| `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT5.md` | Authorization and access control |
| `docs/PROCESS_DRIVEN_PLATFORM/BACKLOG_*.md` | Epic/story breakdown and sprint planning |

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | Complete rebuild: Added architecture diagram, six step types table with examples, state machine diagram, EMI role pattern section, template variables documentation, comprehensive entry points, database schema details |
| 2026-01-23 | Added Template Variables section documenting expression evaluator support |
| 2026-01-16 | Initial creation with architecture overview |
