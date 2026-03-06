# Trinity Process Engine Architecture

## What This Diagram Shows

The Process Engine is a **BPMN-inspired workflow orchestration layer** built on top of Trinity's agent infrastructure. Added in 2026-01-16, it enables declarative process definitions (YAML) that orchestrate agents, handle human approvals, manage branching logic, and track execution state.

**Key differentiator**: Unlike traditional workflow engines (Temporal, Airflow), the Process Engine treats agents as stateful entities that learn and adapt, implementing the **EMI (Executor/Monitor/Informed) role pattern**.

---

## Process Definition Structure

```
+-----------------------------------------------------------------------------------+
|                           PROCESS DEFINITION (YAML)                               |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |  name: content-pipeline                                                      |  |
|  |  version: 1                                                                  |  |
|  |  description: Generate, review, and publish content                          |  |
|  |                                                                              |  |
|  |  triggers:                          # How process starts                     |  |
|  |    - id: daily-run                                                           |  |
|  |      type: schedule                                                          |  |
|  |      cron: "0 9 * * *"                                                       |  |
|  |                                                                              |  |
|  |  steps:                             # Workflow steps                         |  |
|  |    - id: research                                                            |  |
|  |      type: agent_task                                                        |  |
|  |      agent: researcher                                                       |  |
|  |      message: "Research {{input.topic}}"                                     |  |
|  |      roles:                                                                  |  |
|  |        executor: researcher                                                  |  |
|  |        informed: [historian]                                                 |  |
|  |                                                                              |  |
|  |    - id: review                                                              |  |
|  |      type: human_approval                                                    |  |
|  |      title: "Approve {{input.topic}}"                                        |  |
|  |      depends_on: [research]                                                  |  |
|  |                                                                              |  |
|  |  outputs:                           # What to extract                        |  |
|  |    - name: article                                                           |  |
|  |      source: "{{steps.research.output}}"                                     |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
+-----------------------------------------------------------------------------------+
                                    |
                                    | POST /api/processes (create)
                                    | POST /api/processes/{id}/publish
                                    v
+-----------------------------------------------------------------------------------+
|                              YAML VALIDATION PIPELINE                             |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                                                                              |  |
|  |   1. YAML Syntax        2. Schema            3. Domain           4. Agent    |  |
|  |      Validation            Validation           Invariants          Check    |  |
|  |                                                                              |  |
|  |   +----------+         +----------+         +----------+       +----------+  |  |
|  |   | Parse    |  --->   | Required |  --->   | Circular |  ---> | Agent    |  |  |
|  |   | YAML     |         | Fields   |         | Deps     |       | Exists?  |  |  |
|  |   | Syntax   |         | Step IDs |         | Dup IDs  |       | (warn)   |  |  |
|  |   +----------+         +----------+         +----------+       +----------+  |  |
|  |       |                    |                    |                  |         |  |
|  |       v                    v                    v                  v         |  |
|  |     Error               Error                Error              Warning      |  |
|  |   (422 HTTP)          (422 HTTP)           (422 HTTP)          (continue)   |  |
|  |                                                                              |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
+-----------------------------------------------------------------------------------+
                                    |
                                    | (valid definition)
                                    v
+-----------------------------------------------------------------------------------+
|                           DEFINITION LIFECYCLE                                    |
|                                                                                   |
|        +----------+                +----------+                +----------+       |
|        |          |    publish()   |          |   archive()    |          |       |
|        |  DRAFT   | -------------> |PUBLISHED | -------------> | ARCHIVED |       |
|        |          |                |          |                |          |       |
|        +----------+                +----------+                +----------+       |
|             |                           |                                         |
|             | (editable)                | (immutable, executable)                 |
|             v                           v                                         |
|        +----------+                +----------+                                   |
|        | Update   |                | Execute  |                                   |
|        | Delete   |                | Schedule |                                   |
|        +----------+                +----------+                                   |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Execution State Machine

```
+-----------------------------------------------------------------------------------+
|                          EXECUTION STATE MACHINE                                  |
|                                                                                   |
|                                                                                   |
|                              +------------------+                                 |
|                              |     PENDING      |                                 |
|                              |  (Initial State) |                                 |
|                              +--------+---------+                                 |
|                                       |                                           |
|                                       | start()                                   |
|                                       v                                           |
|                              +------------------+                                 |
|           +------------------+     RUNNING      +------------------+              |
|           |                  |                  |                  |              |
|           |                  +--------+---------+                  |              |
|           |                           |                            |              |
|           | pause()                   |                            | cancel()     |
|           | (waiting for              | complete()                 |              |
|           |  approval)                | fail()                     |              |
|           v                           |                            v              |
|   +------------------+                |                   +------------------+    |
|   |      PAUSED      |                |                   |    CANCELLED     |    |
|   |  (Awaiting       |                |                   |                  |    |
|   |   Approval)      |                |                   +------------------+    |
|   +--------+---------+                |                                           |
|            |                          |                                           |
|            | resume()                 |                                           |
|            | (decision received)      |                                           |
|            +-----------+--------------+                                           |
|                        |                                                          |
|                        | (all steps done or failure)                              |
|                        v                                                          |
|          +-------------+-------------+                                            |
|          |                           |                                            |
|          v                           v                                            |
| +------------------+        +------------------+                                   |
| |    COMPLETED     |        |      FAILED      |                                  |
| |                  |        |                  |                                  |
| +------------------+        +------------------+                                   |
|                                                                                   |
+-----------------------------------------------------------------------------------+

STATE TRANSITIONS
-----------------

  From State   |   To State   |   Trigger
 --------------|--------------|------------------------------------------
  PENDING      |   RUNNING    |   execution.start()
  RUNNING      |   COMPLETED  |   All steps complete successfully
  RUNNING      |   FAILED     |   Step failure after retries exhausted
  RUNNING      |   PAUSED     |   Human approval step waiting for decision
  RUNNING      |   CANCELLED  |   User cancellation request
  PAUSED       |   RUNNING    |   Approval decision received (resume)
  PAUSED       |   CANCELLED  |   User cancellation while paused
  PENDING      |   CANCELLED  |   User cancellation before start

STEP STATUS VALUES
------------------

  Status             |   Description
 --------------------|-----------------------------------------------
  PENDING            |   Not yet started, waiting for dependencies
  READY              |   Dependencies met, ready to execute
  RUNNING            |   Currently executing
  WAITING_APPROVAL   |   Human approval step awaiting decision
  COMPLETED          |   Finished successfully
  FAILED             |   Finished with error after all retries
  SKIPPED            |   Condition not met or error policy skip
```

---

## Step Types

```
+-----------------------------------------------------------------------------------+
|                              SIX STEP TYPES                                       |
|                                                                                   |
|  +-------------------------+  +-------------------------+  +---------------------+ |
|  |      AGENT_TASK         |  |    HUMAN_APPROVAL       |  |      GATEWAY        | |
|  |                         |  |                         |  |                     | |
|  |   Execute task via      |  |   Pause execution for   |  |   Conditional       | |
|  |   Trinity agent with    |  |   human approval or     |  |   branching based   | |
|  |   Claude Code           |  |   rejection decision    |  |   on step outputs   | |
|  |                         |  |                         |  |                     | |
|  |   +---------------+     |  |   +---------------+     |  |   +-------------+   | |
|  |   |    Agent      |     |  |   |   Approver    |     |  |   |  Condition  |   | |
|  |   |   Container   |     |  |   |    Inbox      |     |  |   |  Evaluator  |   | |
|  |   +-------+-------+     |  |   +-------+-------+     |  |   +------+------+   | |
|  |           |             |  |           |             |  |          |          | |
|  |           v             |  |           v             |  |     +----+----+     | |
|  |   +--------------+      |  |   +--------------+      |  |     |         |     | |
|  |   |   Output     |      |  |   | approved |   |      |  |     v         v     | |
|  |   |   JSON       |      |  |   | rejected |   |      |  |  Route A  Route B   | |
|  |   +--------------+      |  |   +--------------+      |  |                     | |
|  |                         |  |                         |  |                     | |
|  |   Handler:              |  |   Handler:              |  |   Handler:          | |
|  |   AgentTaskHandler      |  |   HumanApprovalHandler  |  |   GatewayHandler    | |
|  +-------------------------+  +-------------------------+  +---------------------+ |
|                                                                                   |
|  +-------------------------+  +-------------------------+  +---------------------+ |
|  |        TIMER            |  |     NOTIFICATION        |  |    SUB_PROCESS      | |
|  |                         |  |                         |  |                     | |
|  |   Wait for duration     |  |   Send Slack, webhook,  |  |   Call another      | |
|  |   or until specific     |  |   or email notifications|  |   process as a      | |
|  |   timestamp             |  |   to external systems   |  |   nested step       | |
|  |                         |  |                         |  |                     | |
|  |   +---------------+     |  |   +---------------+     |  |   +-------------+   | |
|  |   |   duration:   |     |  |   |   channel:    |     |  |   |  Child      |   | |
|  |   |   1h / 5m     |     |  |   |   slack       |     |  |   |  Process    |   | |
|  |   +-------+-------+     |  |   +-------+-------+     |  |   +------+------+   | |
|  |           |             |  |           |             |  |          |          | |
|  |           v             |  |           v             |  |          v          | |
|  |   +---------------+     |  |   +---------------+     |  |   +-------------+   | |
|  |   | asyncio.sleep |     |  |   | Webhook POST  |     |  |   | Recursive   |   | |
|  |   +---------------+     |  |   +---------------+     |  |   | Execution   |   | |
|  |                         |  |                         |  |   +-------------+   | |
|  |   Handler:              |  |   Handler:              |  |                     | |
|  |   TimerHandler          |  |   NotificationHandler   |  |   Handler:          | |
|  |                         |  |                         |  |   SubProcessHandler | |
|  +-------------------------+  +-------------------------+  +---------------------+ |
|                                                                                   |
+-----------------------------------------------------------------------------------+

YAML EXAMPLES
-------------

agent_task:                    human_approval:               gateway:
  - id: analyze                  - id: approve-budget          - id: route-priority
    type: agent_task              type: human_approval          type: gateway
    agent: analyst                title: "Approve budget"       gateway_type: exclusive
    message: "Analyze data"       assignees:                    routes:
    timeout: 10m                    - finance@example.com        - condition: "score > 80"
                                  timeout: 24h                     next_step: fast-track
                                                                - condition: "score <= 80"
                                                                   next_step: standard
timer:                         notification:                 sub_process:
  - id: wait-period              - id: notify-team             - id: run-validation
    type: timer                    type: notification            type: sub_process
    duration: 1h                   channel: slack                process_name: validation
    depends_on: [notify]           message: "Done!"              input_mapping:
                                                                   data: "{{steps.X.output}}"
```

---

## EMI Role Pattern

```
+-----------------------------------------------------------------------------------+
|                      EMI (EXECUTOR / MONITOR / INFORMED)                          |
|                                                                                   |
|  The EMI pattern assigns responsibility roles to agents for each step:            |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                                                                              |  |
|  |   ROLE       | CARDINALITY  | PURPOSE                                        |  |
|  |  ------------|--------------|----------------------------------------------- |  |
|  |   Executor   | Exactly 1    | Performs the work (required)                   |  |
|  |   Monitor    | 0 or more    | Owns outcome, can intervene, gets alerts       |  |
|  |   Informed   | 0 or more    | Receives notifications for learning/awareness  |  |
|  |                                                                              |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|                                                                                   |
|   YAML Configuration:                                                             |
|   -------------------                                                             |
|                                                                                   |
|   steps:                                                                          |
|     - id: critical-analysis                                                       |
|       type: agent_task                                                            |
|       agent: analyst                                                              |
|       message: "Analyze {{input.topic}}"                                          |
|       roles:                                                                      |
|         executor: analyst          # Required - does the work                     |
|         monitors:                  # Optional - can intervene                     |
|           - quality-agent                                                         |
|           - manager-agent                                                         |
|         informed:                  # Optional - receive NDJSON events             |
|           - learning-agent                                                        |
|           - archive-agent                                                         |
|                                                                                   |
|                                                                                   |
|   Runtime Flow:                                                                   |
|   -------------                                                                   |
|                                                                                   |
|   +-------------------+                                                           |
|   |  ExecutionEngine  |                                                           |
|   |                   |                                                           |
|   |  _execute_step()  |                                                           |
|   +--------+----------+                                                           |
|            |                                                                      |
|            |  (1) Dispatch to executor                                            |
|            v                                                                      |
|   +-------------------+          +-------------------+                            |
|   |  analyst          |          |  quality-agent    |                            |
|   |  (EXECUTOR)       |          |  (MONITOR)        |                            |
|   |                   |          |                   |                            |
|   |  Performs task    |          |  Receives alerts  |                            |
|   |  Returns output   |          |  Can intervene    |                            |
|   +--------+----------+          +-------------------+                            |
|            |                                                                      |
|            |  (2) On completion/failure                                           |
|            v                                                                      |
|   +-------------------+                                                           |
|   | InformedNotifier  |                                                           |
|   |                   |                                                           |
|   | notify_step_*()   |                                                           |
|   +--------+----------+                                                           |
|            |                                                                      |
|            |  (3) Parallel async notification                                     |
|            v                                                                      |
|   +-------------------+          +-------------------+                            |
|   |  learning-agent   |          |  archive-agent    |                            |
|   |  (INFORMED)       |          |  (INFORMED)       |                            |
|   |                   |          |                   |                            |
|   |  .trinity/events/ |          |  .trinity/events/ |                            |
|   |   *.ndjson        |          |   *.ndjson        |                            |
|   +-------------------+          +-------------------+                            |
|                                                                                   |
|                                                                                   |
|   NDJSON Notification Format:                                                     |
|   ---------------------------                                                     |
|                                                                                   |
|   {                                                                               |
|     "event_type": "InformedNotification",                                         |
|     "event_type_name": "step_completed",                                          |
|     "process_name": "content-pipeline",                                           |
|     "execution_id": "exec-uuid-here",                                             |
|     "step_id": "critical-analysis",                                               |
|     "step_name": "Critical Analysis",                                             |
|     "output_summary": "{\"response\": \"Analysis found...\"}",                    |
|     "metadata": {                                                                 |
|       "cost": "$0.10",                                                            |
|       "duration_seconds": 45                                                      |
|     }                                                                             |
|   }                                                                               |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Execution Flow

```
+-----------------------------------------------------------------------------------+
|                           PROCESS EXECUTION FLOW                                  |
|                                                                                   |
|                                                                                   |
|   +-------------------------+                                                     |
|   |   ProcessList.vue       |  User clicks "Start"                                |
|   |   (Frontend)            |                                                     |
|   +-----------+-------------+                                                     |
|               |                                                                   |
|               |  POST /api/processes/{id}/execute                                 |
|               v                                                                   |
|   +-------------------------+                                                     |
|   |   routers/executions.py |                                                     |
|   |   start_execution()     |                                                     |
|   |                         |                                                     |
|   |   1. Load definition    |                                                     |
|   |   2. Check PUBLISHED    |                                                     |
|   |   3. Create execution   |                                                     |
|   |   4. Spawn background   |                                                     |
|   +-----------+-------------+                                                     |
|               |                                                                   |
|               |  background_tasks.add_task(_run_execution)                        |
|               v                                                                   |
|   +---------------------------+                                                   |
|   |   ExecutionEngine         |                                                   |
|   |                           |                                                   |
|   |   _run() - Main Loop:     |                                                   |
|   |   +---------------------+ |                                                   |
|   |   | while True:         | |                                                   |
|   |   |   Check status      | |                                                   |
|   |   |   Get ready steps   | |---+                                               |
|   |   |   Execute (||)      | |   |  (parallel if independent)                    |
|   |   |   Handle results    | |<--+                                               |
|   |   |   Publish events    | |                                                   |
|   |   +---------------------+ |                                                   |
|   +-----------+---------------+                                                   |
|               |                                                                   |
|               |  (per step)                                                       |
|               v                                                                   |
|   +---------------------------+                                                   |
|   |   DependencyResolver      |                                                   |
|   |                           |                                                   |
|   |   get_ready_steps():      |   Returns steps with all deps satisfied           |
|   |   is_complete():          |   All steps done?                                 |
|   |   has_failed_steps():     |   Any failures?                                   |
|   +---------------------------+                                                   |
|               |                                                                   |
|               |  (dispatch to handler)                                            |
|               v                                                                   |
|   +---------------------------+                                                   |
|   |   StepHandlerRegistry     |                                                   |
|   |                           |                                                   |
|   |   +-------------------+   |                                                   |
|   |   | AgentTaskHandler  |   |   -> AgentClient -> Container                     |
|   |   | HumanApproval...  |   |   -> ApprovalStore -> Inbox                       |
|   |   | GatewayHandler    |   |   -> ConditionEvaluator                           |
|   |   | TimerHandler      |   |   -> asyncio.sleep                                |
|   |   | NotificationHa... |   |   -> Webhook/Slack                                |
|   |   | SubProcessHandler |   |   -> Recursive engine.start()                     |
|   |   +-------------------+   |                                                   |
|   +---------------------------+                                                   |
|               |                                                                   |
|               |  StepResult (ok/fail/wait)                                        |
|               v                                                                   |
|   +---------------------------+                                                   |
|   |   Event Bus               |                                                   |
|   |                           |                                                   |
|   |   ProcessStarted          |                                                   |
|   |   StepStarted             |                                                   |
|   |   StepCompleted           |----> WebSocketPublisher -> Frontend               |
|   |   StepFailed              |                                                   |
|   |   ProcessCompleted        |----> WebhookPublisher -> External                 |
|   |   ProcessFailed           |                                                   |
|   +---------------------------+                                                   |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Template Variables

```
+-----------------------------------------------------------------------------------+
|                          TEMPLATE VARIABLE SYSTEM                                 |
|                                                                                   |
|  All step handlers support Jinja2-style template variable substitution.           |
|  Variables are evaluated at runtime by ExpressionEvaluator.                       |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |  SUPPORTED PATTERNS                                                          |  |
|  |                                                                              |  |
|  |  Pattern                    | Description             | Example              |  |
|  | ---------------------------|-------------------------|----------------------|  |
|  |  {{input.X}}               | Process input data      | {{input.company}}    |  |
|  |  {{input.X.Y}}             | Nested input            | {{input.meta.type}}  |  |
|  |  {{steps.X.output}}        | Full step output        | {{steps.r.output}}   |  |
|  |  {{steps.X.output.Y}}      | Nested step output      | {{steps.r.output.s}} |  |
|  |  {{execution.id}}          | Current execution ID    | exec_abc123...       |  |
|  |  {{process.name}}          | Process definition name | due-diligence        |  |
|  |                                                                              |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |  HANDLER TEMPLATE SUPPORT                                                    |  |
|  |                                                                              |  |
|  |  Handler              | Fields Supporting Variables                         |  |
|  | ----------------------|--------------------------------------------------- |  |
|  |  AgentTaskHandler     | message, agent                                      |  |
|  |  HumanApprovalHandler | title, description                                  |  |
|  |  NotificationHandler  | message, subject                                    |  |
|  |  GatewayHandler       | routes[].condition (expressions)                    |  |
|  |  SubProcessHandler    | input_mapping values                                |  |
|  |                                                                              |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  Example:                                                                         |
|  --------                                                                         |
|                                                                                   |
|  steps:                                                                           |
|    - id: intake                                                                   |
|      type: agent_task                                                             |
|      agent: intake-agent                                                          |
|      message: "Collect info for {{input.company_name}}"                           |
|                                                                                   |
|    - id: review                                                                   |
|      type: human_approval                                                         |
|      title: "Approve {{input.company_name}} for {{input.deal_type}}?"             |
|      description: |                                                               |
|        Review summary: {{steps.intake.output.response}}                           |
|        Risk score: {{steps.intake.output.score}}                                  |
|      depends_on: [intake]                                                         |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Backend Directory Structure

```
+-----------------------------------------------------------------------------------+
|                     src/backend/services/process_engine/                          |
|                                                                                   |
|  +-- domain/                      # Core domain model (DDD)                       |
|  |   +-- aggregates.py            # ProcessDefinition, ProcessExecution           |
|  |   +-- entities.py              # StepDefinition, StepExecution, ApprovalRequest|
|  |   +-- enums.py                 # DefinitionStatus, ExecutionStatus, StepType   |
|  |   +-- events.py                # ProcessStarted, StepCompleted, etc.           |
|  |   +-- step_configs.py          # AgentTaskConfig, HumanApprovalConfig, etc.    |
|  |   +-- value_objects.py         # ProcessId, ExecutionId, StepId, Duration      |
|  |                                                                                |
|  +-- engine/                      # Execution orchestration                       |
|  |   +-- execution_engine.py      # Core orchestrator (start, resume, cancel)     |
|  |   +-- dependency_resolver.py   # Topological sort, parallel detection          |
|  |   +-- step_handler.py          # Base handler class, registry                  |
|  |   +-- handlers/                                                                |
|  |       +-- agent_task.py        # AgentTaskHandler                              |
|  |       +-- human_approval.py    # HumanApprovalHandler                          |
|  |       +-- gateway.py           # GatewayHandler                                |
|  |       +-- timer.py             # TimerHandler                                  |
|  |       +-- notification.py      # NotificationHandler                           |
|  |       +-- sub_process.py       # SubProcessHandler                             |
|  |                                                                                |
|  +-- repositories/                # Persistence layer                             |
|  |   +-- interfaces.py            # Abstract repository interfaces                |
|  |   +-- sqlite_definitions.py    # ProcessDefinition persistence                 |
|  |   +-- sqlite_executions.py     # ProcessExecution persistence                  |
|  |   +-- sqlite_events.py         # Event log persistence                         |
|  |                                                                                |
|  +-- services/                    # Application services                          |
|  |   +-- validator.py             # YAML validation, schema checking              |
|  |   +-- analytics.py             # ProcessAnalytics, metrics calculation         |
|  |   +-- alerts.py                # CostAlertService, threshold monitoring        |
|  |   +-- expression_evaluator.py  # Template variable substitution                |
|  |   +-- informed_notifier.py     # EMI notification delivery                     |
|  |   +-- output_storage.py        # Step output persistence                       |
|  |   +-- templates.py             # ProcessTemplateService                        |
|  |                                                                                |
|  +-- events/                      # Event infrastructure                          |
|      +-- bus.py                   # InMemoryEventBus                              |
|      +-- websocket_publisher.py   # Real-time UI updates                          |
|      +-- webhook_publisher.py     # External webhook notifications                |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Sources

### Feature Flow Documentation
- [Process Engine README](../memory/feature-flows/process-engine/README.md) - Overview and architecture
- [Process Definition](../memory/feature-flows/process-engine/process-definition.md) - YAML schema, validation, versioning
- [Process Execution](../memory/feature-flows/process-engine/process-execution.md) - Engine, handlers, state machine
- [Human Approval](../memory/feature-flows/process-engine/human-approval.md) - Approval gates, timeout handling
- [Agent Roles (EMI)](../memory/feature-flows/process-engine/agent-roles-emi.md) - EMI pattern, InformedNotifier

### Code References
- `src/backend/services/process_engine/engine/execution_engine.py` - Core orchestrator
- `src/backend/services/process_engine/domain/aggregates.py` - ProcessDefinition, ProcessExecution
- `src/backend/services/process_engine/domain/entities.py` - StepDefinition, StepRoles
- `src/backend/services/process_engine/services/validator.py` - YAML validation
- `src/backend/services/process_engine/services/informed_notifier.py` - EMI notifications
- `src/backend/routers/processes.py` - Process API endpoints
- `src/backend/routers/executions.py` - Execution API endpoints
- `src/frontend/src/views/ProcessEditor.vue` - YAML editor with preview
- `src/frontend/src/views/ProcessExecutionDetail.vue` - Execution monitoring

### Architecture Documentation
- [Architecture](../memory/architecture.md) - Process Engine section (line 254+)

---

## Last Updated

2026-01-25
