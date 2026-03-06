# Feature: Process Execution

> Core execution engine that orchestrates process steps with parallel execution, retry logic, and event publishing

---

## Overview

The Execution Engine is the core orchestrator for process execution. It manages the execution lifecycle, resolves step dependencies, dispatches steps to appropriate handlers, and emits domain events.

**Key Capabilities:**
- Parallel execution of independent steps
- Retry logic with exponential backoff
- Step-type-specific handlers (agent_task, gateway, approval, timer, notification, sub_process)
- Event publishing for real-time monitoring
- Cost tracking and aggregation
- Compensation handling on failure

---

## Entry Points

- **UI**: `src/frontend/src/views/ProcessList.vue` -> "Start" button -> `POST /api/processes/{id}/execute`
- **UI**: `src/frontend/src/views/ProcessExecutionDetail.vue:140` -> "Retry" button -> `POST /api/executions/{id}/retry`
- **UI**: `src/frontend/src/views/ProcessExecutionDetail.vue:130` -> "Cancel" button -> `POST /api/executions/{id}/cancel`
- **API**: `POST /api/processes/{id}/execute` - Start new execution
- **API**: `POST /api/executions/{id}/cancel` - Cancel running execution
- **API**: `POST /api/executions/{id}/retry` - Retry failed execution
- **Scheduled**: Process schedule triggers via scheduler service

---

## Architecture

```
                              Frontend
  +---------------------------------------------------------------------------+
  |  ProcessList.vue / ProcessExecutionDetail.vue                             |
  |  +-- Start button -> POST /api/processes/{id}/execute                     |
  |  +-- Cancel button -> POST /api/executions/{id}/cancel                    |
  |  +-- Retry button -> POST /api/executions/{id}/retry                      |
  +---------------------------------------------------------------------------+
                                     |
                                     v
                              Backend
  +---------------------------------------------------------------------------+
  |  routers/executions.py                                                    |
  |  +-- start_execution():321      - Create execution, call engine.start()   |
  |  +-- cancel_execution():509     - Call engine.cancel()                    |
  |  +-- retry_execution():555      - Create new execution from failed        |
  +--------------------------------------+------------------------------------+
                                         |
                                         v
  +---------------------------------------------------------------------------+
  |  engine/execution_engine.py - ExecutionEngine:91                          |
  |  +-- start():146               - Create and run new execution             |
  |  +-- resume():194              - Resume paused execution                  |
  |  +-- cancel():230              - Cancel running execution                 |
  |  +-- _run():260                - Main execution loop                      |
  |  +-- _execute_step():386       - Execute single step with retry           |
  |  +-- _execute_steps_parallel():352 - Execute multiple steps concurrently  |
  +--------------------------------------+------------------------------------+
                                         |
                                         v
  +---------------------------------------------------------------------------+
  |  engine/dependency_resolver.py - DependencyResolver:59                    |
  |  +-- get_ready_steps():77      - Steps ready to execute (deps satisfied)  |
  |  +-- is_complete():180         - All steps done?                          |
  |  +-- has_failed_steps():194    - Any failures?                            |
  |  +-- get_parallel_structure():206 - Identify parallel groups              |
  +--------------------------------------+------------------------------------+
                                         |
                                         v
  +---------------------------------------------------------------------------+
  |  engine/handlers/                                                         |
  |  +-- agent_task.py:137         - AgentTaskHandler + AgentGateway          |
  |  +-- human_approval.py:79      - HumanApprovalHandler + ApprovalStore     |
  |  +-- gateway.py:21             - GatewayHandler (conditional routing)     |
  |  +-- timer.py:20               - TimerHandler (delays)                    |
  |  +-- notification.py:24        - NotificationHandler (Slack/email/webhook)|
  |  +-- sub_process.py:39         - SubProcessHandler (nested workflows)     |
  +--------------------------------------+------------------------------------+
                                         |
                                         v
  +---------------------------------------------------------------------------+
  |  events/bus.py - EventBus                                                 |
  |  +-- publish(event)            - Broadcast to subscribers                 |
  |  +-- Publishers:                                                          |
  |      +-- websocket_publisher.py - Real-time UI updates                    |
  |      +-- webhook_publisher.py   - External notifications                  |
  +---------------------------------------------------------------------------+
```

---

## Execution State Machine

### Process Execution Status

```
                                    +------------------+
                                    |     PENDING      |
                                    |  (Initial State) |
                                    +--------+---------+
                                             |
                                             | start()
                                             v
                                    +------------------+
           +------------------------+     RUNNING      +------------------------+
           |                        |                  |                        |
           |                        +--------+---------+                        |
           |                                 |                                  |
           | pause()                         |                                  | cancel()
           | (waiting approval)              |                                  |
           v                                 |                                  v
  +------------------+                       |                        +------------------+
  |      PAUSED      |                       |                        |    CANCELLED     |
  | (Awaiting        |                       |                        |                  |
  |  Approval)       |                       |                        +------------------+
  +--------+---------+                       |
           |                                 |
           | resume()                        |
           | (approval received)             |
           +--------------------+------------+
                                |
                                | complete() / fail()
                                v
              +----------------+----------------+
              |                                 |
              v                                 v
     +------------------+              +------------------+
     |    COMPLETED     |              |      FAILED      |
     |                  |              |                  |
     +------------------+              +------------------+
```

**State Transitions:**

| Current State | Method | New State | Trigger |
|---------------|--------|-----------|---------|
| PENDING | `start()` | RUNNING | Execution begins |
| RUNNING | `complete()` | COMPLETED | All steps done |
| RUNNING | `fail()` | FAILED | Step failure or error |
| RUNNING | `cancel()` | CANCELLED | User cancellation |
| RUNNING | `pause()` | PAUSED | Waiting for approval |
| PAUSED | `resume()` | RUNNING | Approval received |
| PENDING | `cancel()` | CANCELLED | User cancellation |

**Implementation:** `src/backend/services/process_engine/domain/aggregates.py:451-493`

### Step Execution Status

| Status | Description | Enum Value |
|--------|-------------|------------|
| `PENDING` | Not started, waiting for dependencies | `StepStatus.PENDING` |
| `READY` | Dependencies satisfied, ready to run | `StepStatus.READY` |
| `RUNNING` | Currently executing | `StepStatus.RUNNING` |
| `COMPLETED` | Finished successfully with output | `StepStatus.COMPLETED` |
| `FAILED` | Failed after all retries exhausted | `StepStatus.FAILED` |
| `SKIPPED` | Skipped due to condition or error policy | `StepStatus.SKIPPED` |
| `WAITING_APPROVAL` | Human approval step awaiting decision | `StepStatus.WAITING_APPROVAL` |

**Implementation:** `src/backend/services/process_engine/domain/enums.py:37-46`

---

## Core Components

### ExecutionEngine

**File:** `src/backend/services/process_engine/engine/execution_engine.py`

The main orchestrator class that manages the execution lifecycle.

```python
# execution_engine.py:91-145
class ExecutionEngine:
    """
    Orchestrates process execution.

    Responsibilities:
    - Manage execution lifecycle (start, pause, resume, cancel)
    - Resolve step dependencies and determine execution order
    - Dispatch steps to appropriate handlers
    - Update execution state and emit events
    - Handle errors and retries
    """

    def __init__(
        self,
        execution_repo: ProcessExecutionRepository,
        event_bus: Optional[EventBus] = None,
        output_storage: Optional[OutputStorage] = None,
        handler_registry: Optional[StepHandlerRegistry] = None,
        config: Optional[ExecutionConfig] = None,
        informed_notifier: Optional[InformedAgentNotifier] = None,
        cost_alert_service: Optional[CostAlertService] = None,
    ):
        ...
```

**Key Methods:**

| Method | Line | Description |
|--------|------|-------------|
| `start()` | 146 | Create and run new execution |
| `resume()` | 194 | Resume paused execution |
| `cancel()` | 230 | Cancel running execution |
| `_run()` | 260 | Main execution loop |
| `_execute_steps_parallel()` | 352 | Execute multiple steps concurrently |
| `_execute_step()` | 386 | Execute single step with retry |
| `_handle_step_success()` | 545 | Handle successful step completion |
| `_handle_step_waiting()` | 608 | Handle step waiting for input |
| `_handle_step_failure()` | 638 | Handle step failure |
| `_complete_execution()` | 716 | Complete execution successfully |
| `_fail_execution()` | 789 | Fail execution and run compensations |
| `_run_compensations()` | 823 | Execute compensation handlers |

### ExecutionConfig

**File:** `src/backend/services/process_engine/engine/execution_engine.py:67-89`

```python
@dataclass
class ExecutionConfig:
    # Default timeout for steps without explicit timeout
    default_step_timeout: Duration = Duration.from_minutes(5)

    # Stop on first failure or continue with independent steps
    stop_on_failure: bool = True

    # Maximum retries for failed steps (0 = no retries)
    max_retries: int = 0

    # Enable parallel execution of independent steps
    parallel_execution: bool = True

    # Maximum concurrent steps (0 = unlimited)
    max_concurrent_steps: int = 0
```

### DependencyResolver

**File:** `src/backend/services/process_engine/engine/dependency_resolver.py:59-315`

Determines which steps can execute based on dependency satisfaction.

```python
class DependencyResolver:
    def get_ready_steps(self, execution: ProcessExecution) -> list[StepId]:
        """Get steps ready to execute (all deps satisfied)."""
        ready = []
        satisfied = set(execution.get_completed_step_ids())
        satisfied.update(execution.get_skipped_step_ids())

        for step in self.definition.steps:
            if step_exec.status != StepStatus.PENDING:
                continue

            deps_satisfied = all(str(dep) in satisfied for dep in step.dependencies)
            if deps_satisfied:
                ready.append(step.id)

        return ready
```

**Key Methods:**

| Method | Line | Description |
|--------|------|-------------|
| `get_ready_steps()` | 77 | Get steps ready to execute |
| `get_next_step()` | 115 | Get single next step (sequential) |
| `get_execution_order()` | 130 | Full topological sort |
| `get_step_definition()` | 168 | Look up step by ID |
| `is_complete()` | 180 | Check if all steps done |
| `has_failed_steps()` | 194 | Check for failures |
| `get_parallel_structure()` | 206 | Analyze parallel groups |
| `get_running_steps()` | 270 | Get currently running steps |
| `get_waiting_steps()` | 287 | Get steps waiting for approval |

---

## Step Handlers

### Handler Interface

**File:** `src/backend/services/process_engine/engine/step_handler.py`

```python
# step_handler.py:74-109
class StepHandler(ABC):
    """Abstract base class for step handlers."""

    @property
    @abstractmethod
    def step_type(self) -> StepType:
        """The step type this handler processes."""
        ...

    @abstractmethod
    async def execute(
        self,
        context: StepContext,
        config: StepConfig,
    ) -> StepResult:
        """Execute the step."""
        ...
```

### StepResult

**File:** `src/backend/services/process_engine/engine/step_handler.py:24-55`

```python
@dataclass
class StepResult:
    success: bool
    waiting: bool = False
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    @classmethod
    def ok(cls, output: dict) -> "StepResult":
        return cls(success=True, output=output)

    @classmethod
    def fail(cls, error: str, error_code: str = None) -> "StepResult":
        return cls(success=False, error=error, error_code=error_code)

    @classmethod
    def wait(cls, output: dict = None) -> "StepResult":
        return cls(success=False, waiting=True, output=output)
```

### StepContext

**File:** `src/backend/services/process_engine/engine/step_handler.py:58-72`

```python
@dataclass
class StepContext:
    execution: ProcessExecution
    step_definition: StepDefinition
    step_outputs: dict[str, Any]  # step_id -> output
    input_data: dict[str, Any]    # Process input data

    def get_step_output(self, step_id: str) -> Optional[Any]:
        return self.step_outputs.get(step_id)
```

### StepHandlerRegistry

**File:** `src/backend/services/process_engine/engine/step_handler.py:111-163`

```python
class StepHandlerRegistry:
    """Registry for step handlers."""

    def __init__(self):
        self._handlers: dict[StepType, StepHandler] = {}

    def register(self, handler: StepHandler) -> None:
        self._handlers[handler.step_type] = handler

    def get(self, step_type: StepType) -> Optional[StepHandler]:
        return self._handlers.get(step_type)

    def get_for_step(self, step: StepDefinition) -> Optional[StepHandler]:
        return self.get(step.type)
```

**Default Registry Setup:** `src/backend/routers/executions.py:190-208`

```python
def get_handler_registry() -> StepHandlerRegistry:
    registry = StepHandlerRegistry()
    registry.register(AgentTaskHandler())
    registry.register(HumanApprovalHandler())
    registry.register(GatewayHandler())
    registry.register(NotificationHandler())
    registry.register(TimerHandler())
    registry.register(SubProcessHandler(
        definition_repo=get_definition_repo(),
        engine_factory=get_execution_engine,
    ))
    return registry
```

### Handler Implementations

| Handler | File | Line | Step Type | Description |
|---------|------|------|-----------|-------------|
| `AgentTaskHandler` | `handlers/agent_task.py` | 137 | `agent_task` | Send message to Trinity agent |
| `HumanApprovalHandler` | `handlers/human_approval.py` | 79 | `human_approval` | Create approval request, pause execution |
| `GatewayHandler` | `handlers/gateway.py` | 21 | `gateway` | Evaluate conditions, route execution |
| `TimerHandler` | `handlers/timer.py` | 20 | `timer` | Pause execution for specified duration |
| `NotificationHandler` | `handlers/notification.py` | 24 | `notification` | Send Slack/email/webhook notifications |
| `SubProcessHandler` | `handlers/sub_process.py` | 39 | `sub_process` | Execute child process workflow |

---

## Template Variable Substitution

**File:** `src/backend/services/process_engine/services/expression_evaluator.py`

Handlers use `ExpressionEvaluator` to substitute template variables in step configuration fields.

### EvaluationContext

**Line:** 19-96

```python
@dataclass
class EvaluationContext:
    input_data: dict[str, Any]
    step_outputs: dict[str, Any]
    execution_id: Optional[str] = None
    process_name: Optional[str] = None

    def get(self, path: str) -> Any:
        """Get value by dotted path."""
        # input.field -> input_data["field"]
        # steps.X.output -> step_outputs["X"]
        # execution.id -> execution_id
        # process.name -> process_name
```

### ExpressionEvaluator

**Line:** 99-250

```python
class ExpressionEvaluator:
    """Evaluates template expressions in strings."""

    EXPRESSION_PATTERN = re.compile(r"\{\{([^}]+)\}\}")

    def evaluate(self, template: str, context: EvaluationContext, strict: bool = False) -> str:
        """Evaluate all expressions in a template string."""
        ...
```

### ConditionEvaluator

**Line:** 257-383

```python
class ConditionEvaluator:
    """Evaluates boolean conditions for gateway routing."""

    COMPARISON_OPS = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": ..., "<": ..., ">=": ..., "<=": ...
    }

    def evaluate(self, condition: str, context: EvaluationContext) -> bool:
        """Evaluate a boolean condition."""
        # Supports: and, or, not, ==, !=, >, <, >=, <=
```

### Supported Variables

| Pattern | Description | Example |
|---------|-------------|---------|
| `{{input.X}}` | Process input data | `{{input.company_name}}` |
| `{{input.X.Y}}` | Nested input data | `{{input.metadata.priority}}` |
| `{{steps.X.output}}` | Full step output | `{{steps.research.output}}` |
| `{{steps.X.output.Y}}` | Nested field in step output | `{{steps.research.output.summary}}` |
| `{{execution.id}}` | Execution ID | `exec_abc123...` |
| `{{process.name}}` | Process name | `due-diligence-workflow` |

### Handler Template Support

| Handler | Fields with Template Support |
|---------|------------------------------|
| `AgentTaskHandler` | `message`, `agent` |
| `HumanApprovalHandler` | `title`, `description` |
| `NotificationHandler` | `message` |
| `GatewayHandler` | Condition expressions |
| `SubProcessHandler` | `input_mapping` values |

---

## Flow Details

### 1. Start Execution Flow

**User Action:** Click "Start" button on process card

```
ProcessList.vue                   Backend                             Engine
---------------                   -------                             ------
User clicks "Start"
POST /api/processes/{id}/execute
                              ->  start_execution():321
                                  +-- Load definition from repo
                                  +-- Check definition is PUBLISHED
                                  +-- Check execution limits
                                  +-- ProcessExecution.create()
                                  +-- repo.save(execution)
                                  +-- background_tasks.add_task(_run_execution)
                                  +-- Return execution detail
                                                                    ->  _run_execution():391
                                                                        +-- Load definition
                                                                        +-- Load execution
                                                                        +-- engine.resume()
                                                                              -> _run()
                                                                                 [Execution Loop]
```

### 2. Main Execution Loop

**File:** `src/backend/services/process_engine/engine/execution_engine.py:260-350`

```python
async def _run(self, definition, execution):
    resolver = DependencyResolver(definition)

    # Start execution if pending
    if execution.status == ExecutionStatus.PENDING:
        execution.start()
        repo.save(execution)
        await publish(ProcessStarted)

    while True:
        # Check cancelled/paused
        if execution.status == ExecutionStatus.CANCELLED:
            break
        if execution.status == ExecutionStatus.PAUSED:
            logger.info("Execution paused (waiting for approval)")
            break

        # Check for failures
        if resolver.has_failed_steps(execution) and config.stop_on_failure:
            await _fail_execution(execution, "Step execution failed", definition)
            break

        # Get ready steps
        ready_step_ids = resolver.get_ready_steps(execution)

        if not ready_step_ids:
            if resolver.is_complete(execution):
                await _complete_execution(execution, definition)
                break
            elif resolver.has_failed_steps(execution):
                await _fail_execution(execution, "Step execution failed", definition)
                break
            else:
                # Check for running steps (parallel)
                running_steps = resolver.get_running_steps(execution)
                if running_steps:
                    await asyncio.sleep(0.1)
                    continue
                # Deadlock
                await _fail_execution(execution, "Execution deadlock", definition)
                break

        # Execute steps
        if config.parallel_execution and len(ready_step_ids) > 1:
            await _execute_steps_parallel(execution, step_defs, definition)
        else:
            for step_def in step_defs:
                await _execute_step(execution, step_def, definition)
```

### 3. Single Step Execution with Retry

**File:** `src/backend/services/process_engine/engine/execution_engine.py:386-543`

```python
async def _execute_step(self, execution, step_def, definition):
    step_id = step_def.id

    # Get handler
    handler = self.handler_registry.get_for_step(step_def)
    if handler is None:
        execution.step_executions[str(step_id)].skip("No handler")
        await publish(StepSkipped)
        return

    # Evaluate step condition
    if step_def.condition:
        if not evaluator.evaluate(step_def.condition, context):
            execution.step_executions[str(step_id)].skip("Condition not met")
            await publish(StepSkipped)
            return

    # Start step
    execution.start_step(step_id)
    repo.save(execution)
    await publish(StepStarted)

    # Retry loop
    retry_policy = step_def.retry_policy
    max_attempts = retry_policy.max_attempts
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        # Build context
        context = StepContext(execution, step_def, step_outputs, input_data)

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                handler.execute(context, step_def.config),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            result = StepResult.fail("Step timed out", error_code="TIMEOUT")

        # Handle result
        if result.success:
            await _handle_step_success(execution, step_def, result)
            return

        if result.waiting:
            await _handle_step_waiting(execution, step_def, result)
            return

        # Failed - check if retryable
        non_retryable = {"APPROVAL_REJECTED", "VALIDATION_ERROR", "INVALID_CONFIG", "TIMEOUT"}
        if result.error_code in non_retryable:
            await _handle_step_failure(execution, step_def, result, definition)
            return

        if attempt < max_attempts:
            delay = retry_policy.initial_delay.seconds * (backoff ** (attempt - 1))
            await publish(StepRetrying)
            await asyncio.sleep(delay)
        else:
            await _handle_step_failure(execution, step_def, result, definition)
```

### 4. Parallel Execution

**File:** `src/backend/services/process_engine/engine/execution_engine.py:352-384`

```python
async def _execute_steps_parallel(self, execution, step_defs, definition):
    logger.info(f"Executing {len(step_defs)} steps in parallel")

    # Apply concurrency limit if configured
    if config.max_concurrent_steps > 0:
        semaphore = asyncio.Semaphore(config.max_concurrent_steps)

        async def limited_execute(step_def):
            async with semaphore:
                await _execute_step(execution, step_def, definition)

        tasks = [limited_execute(sd) for sd in step_defs]
    else:
        tasks = [_execute_step(execution, sd, definition) for sd in step_defs]

    # Run all concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
```

### 5. Compensation (Rollback)

**File:** `src/backend/services/process_engine/engine/execution_engine.py:823-983`

When a process fails after some steps have completed, compensation handlers run in reverse order.

```python
async def _run_compensations(self, execution, definition):
    # Get completed steps sorted by completion time (most recent first)
    completed_step_ids = []
    for step_id, step_exec in execution.step_executions.items():
        if step_exec.status == StepStatus.COMPLETED and step_exec.completed_at:
            completed_step_ids.append((step_id, step_exec.completed_at))

    completed_step_ids.sort(key=lambda x: x[1], reverse=True)

    # Find steps with compensation defined
    steps_with_compensation = []
    for step_id, _ in completed_step_ids:
        step_def = next((s for s in definition.steps if str(s.id) == step_id), None)
        if step_def and step_def.compensation:
            steps_with_compensation.append(step_def)

    if not steps_with_compensation:
        return

    await publish(CompensationStarted)

    for step_def in steps_with_compensation:
        try:
            await _execute_compensation(execution, step_def)
        except Exception as e:
            await publish(CompensationFailed)
            # Continue with other compensations
```

---

## Domain Events

Events published during execution:

| Event | When | Data | Line |
|-------|------|------|------|
| `ProcessStarted` | Execution begins | execution_id, process_id, triggered_by | 278 |
| `ProcessCompleted` | All steps done | output_data, total_cost, duration | 740 |
| `ProcessFailed` | Step failure or error | error_message, failed_step_id | 809 |
| `ProcessCancelled` | User cancellation | reason, cancelled_by | 248 |
| `StepStarted` | Step execution begins | step_id, step_name, step_type | 445 |
| `StepCompleted` | Step succeeds | output, cost, duration | 587 |
| `StepFailed` | Step fails (final) | error_message, retry_count | 681 |
| `StepRetrying` | Step failed, will retry | attempt, max_attempts, next_retry_at | 524 |
| `StepSkipped` | Step skipped | reason | 404, 430 |
| `StepWaitingApproval` | Awaiting human input | approval_id, assignees | 627 |
| `CompensationStarted` | Rollback begins | compensation_count | 859 |
| `CompensationCompleted` | Rollback succeeds | step_name, type | 926 |
| `CompensationFailed` | Rollback fails | step_name, error_message | 872 |

---

## API Endpoints

**File:** `src/backend/routers/executions.py`

| Method | Path | Description | Line |
|--------|------|-------------|------|
| POST | `/api/processes/{id}/execute` | Start execution | 321 |
| GET | `/api/executions` | List all executions | 418 |
| GET | `/api/executions/{id}` | Get execution detail | 471 |
| POST | `/api/executions/{id}/cancel` | Cancel execution | 509 |
| POST | `/api/executions/{id}/retry` | Retry failed execution | 555 |
| GET | `/api/executions/{id}/events` | Get event history | 618 |
| GET | `/api/executions/{id}/steps/{step_id}/output` | Get step output | 639 |
| GET | `/api/executions/{id}/costs` | Get cost breakdown | 669 |
| GET | `/api/executions/recovery/status` | Get recovery status | 841 |
| GET | `/api/executions/limits/status` | Get execution limits | 881 |

---

## Frontend Layer

### ProcessExecutionDetail.vue

**File:** `src/frontend/src/views/ProcessExecutionDetail.vue`

**Key Methods:**

| Method | Line | Description |
|--------|------|-------------|
| `loadExecution()` | 542 | Fetch execution from API |
| `handleCancel()` | 605 | Cancel running execution |
| `handleRetry()` | 621 | Retry failed execution |
| `handleApprovalDecided()` | 638 | Handle approval decision |
| `buildBreadcrumbs()` | 561 | Build nav for sub-processes |

**WebSocket Integration:**

**Line:** 434-516

```javascript
const { isConnected: wsConnected } = useProcessWebSocket({
  executionId,
  onStepStarted: (event) => {
    // Update step status in UI
    const step = execution.value.steps?.find(s => s.step_id === event.step_id)
    if (step) {
      step.status = 'running'
      step.started_at = event.timestamp
    }
  },
  onStepCompleted: (event) => { ... },
  onStepFailed: (event) => { ... },
  onProcessCompleted: (event) => {
    setTimeout(() => loadExecution(), 500)
  },
  onProcessFailed: (event) => {
    setTimeout(() => loadExecution(), 500)
  },
})
```

---

## Database Schema

**File:** `src/backend/services/process_engine/repositories/sqlite_executions.py`

```sql
CREATE TABLE process_executions (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    process_version TEXT NOT NULL,
    status TEXT NOT NULL,
    input_data TEXT,             -- JSON
    output_data TEXT,            -- JSON
    step_executions TEXT,        -- JSON map: step_id -> StepExecution
    triggered_by TEXT,
    started_at TEXT,
    completed_at TEXT,
    total_cost TEXT,
    retry_of TEXT,               -- Original execution if retry
    parent_execution_id TEXT,    -- For sub-processes
    parent_step_id TEXT,
    child_execution_ids TEXT     -- JSON array
);

CREATE INDEX idx_executions_process ON process_executions(process_id);
CREATE INDEX idx_executions_status ON process_executions(status);
CREATE INDEX idx_executions_started ON process_executions(started_at);
```

---

## Error Handling

### Retry Policy

```yaml
# In step definition
retry:
  max_attempts: 3       # Total attempts (default: 1)
  initial_delay: 10s    # Delay before first retry
  backoff_multiplier: 2 # Exponential backoff
```

### Error Policy

```yaml
on_error:
  action: fail_process  # fail_process | skip_step | goto_step
  target_step: cleanup  # Required if action is goto_step
```

### Non-Retryable Error Codes

| Error Code | Description |
|------------|-------------|
| `APPROVAL_REJECTED` | Human rejected approval |
| `APPROVAL_TIMEOUT` | Approval deadline passed |
| `VALIDATION_ERROR` | Invalid configuration |
| `INVALID_CONFIG` | Handler config error |
| `TIMEOUT` | Step execution timed out |

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- At least one published process definition
- Required agents created and running

### Test Cases

1. **Sequential execution**
   - Action: Start process with linear dependencies (A -> B -> C)
   - Expected: Steps execute in order, events emitted

2. **Parallel execution**
   - Action: Start process with parallel steps (A -> [B, C] -> D)
   - Expected: B and C run concurrently, D waits for both

3. **Retry on failure**
   - Action: Step fails with transient error, retry configured
   - Expected: StepRetrying event, then success or final failure

4. **Cancel execution**
   - Action: Cancel running execution
   - Expected: Status changes to CANCELLED, running steps stop

5. **Compensation on failure**
   - Action: Step with compensation fails after another completes
   - Expected: Compensation runs in reverse order

---

## Related Flows

- [process-definition.md](./process-definition.md) - How definitions are created
- [process-monitoring.md](./process-monitoring.md) - UI for watching executions
- [human-approval.md](./human-approval.md) - Approval step handler details
- [sub-processes.md](./sub-processes.md) - SubProcessHandler details
- [process-analytics.md](./process-analytics.md) - Cost and performance metrics

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | Rebuilt with accurate line numbers and comprehensive documentation |
| 2026-01-23 | Added Template Variable Substitution section with handler support table |
| 2026-01-16 | Initial creation |
