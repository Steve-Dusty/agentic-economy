# Feature: Sub-Processes

> Calling other processes as steps within a parent workflow, with parent-child linking and breadcrumb navigation

---

## Overview

Sub-Processes enable composable, reusable workflows by allowing one process to call another as a step. The parent process waits for the child to complete and receives its output.

**Key Capabilities:**
- Call any published process as a step
- Map input data from parent to child
- Capture child output in parent context
- Parent-child execution linking
- Breadcrumb navigation in UI
- Cost aggregation

---

## Entry Points

| Entry Point | Location | Description |
|-------------|----------|-------------|
| YAML Definition | `type: sub_process` | Define sub-process step in process YAML |
| Execution Detail UI | `src/frontend/src/views/ProcessExecutionDetail.vue:87-108` | Shows parent/child badges |
| Breadcrumb Navigation | `src/frontend/src/views/ProcessExecutionDetail.vue:9-24` | Parent chain navigation |
| API Response | `GET /api/executions/{id}` | Includes parent/child links |

---

## Architecture

```
+---------------------------------------------------------------------------------+
|                              Parent Process                                      |
|  +-------------------------------------------------------------------------+    |
|  |  steps:                                                                  |    |
|  |    - id: research                                                        |    |
|  |      type: agent_task                                                    |    |
|  |      ...                                                                 |    |
|  |                                                                          |    |
|  |    - id: call-analysis                                                   |    |
|  |      type: sub_process           --------------------------------+       |    |
|  |      process_name: analysis-flow                                 |       |    |
|  |      input_mapping:                                              |       |    |
|  |        data: "{{steps.research.output}}"                         |       |    |
|  |      output_key: analysis_result                                 |       |    |
|  |                                                                  |       |    |
|  |    - id: summarize                                               |       |    |
|  |      type: agent_task                                            |       |    |
|  |      depends_on: [call-analysis]                                 |       |    |
|  |      message: "Summarize: {{steps.call-analysis.analysis_result}}"       |    |
|  +---------------------------------------------------------------+--+------+    |
+------------------------------------------------------------------|--------------+
                                                                   |
                                                                   v
+---------------------------------------------------------------------------------+
|                              Child Process: analysis-flow                        |
|  +-------------------------------------------------------------------------+    |
|  |  input: {data: ...}                                                      |    |
|  |                                                                          |    |
|  |  steps:                                                                  |    |
|  |    - id: analyze                                                         |    |
|  |      type: agent_task                                                    |    |
|  |      ...                                                                 |    |
|  |                                                                          |    |
|  |  output: {result: ...}                                                   |    |
|  +-------------------------------------------------------------------------+    |
|                                                                                  |
|  ProcessExecution                                                                |
|    parent_execution_id: <parent-uuid>                                           |
|    parent_step_id: call-analysis                                                |
+---------------------------------------------------------------------------------+
```

---

## YAML Configuration

### SubProcessConfig

**File:** `src/backend/services/process_engine/domain/step_configs.py:217-264`

```python
@dataclass(frozen=True)
class SubProcessConfig:
    """Configuration for sub_process step type."""
    process_name: str                              # Required: name of process to call
    version: Optional[str] = None                  # Optional: specific version (None = latest)
    input_mapping: dict = field(default_factory=dict)  # Map parent context to child input
    output_key: str = "result"                     # Key for child output in parent context
    wait_for_completion: bool = True               # Sync (True) vs async (False)
    timeout: Duration = field(default_factory=lambda: Duration.from_hours(1))
```

### Basic Sub-Process Step

```yaml
- id: run-analysis
  type: sub_process
  process_name: analysis-flow    # Required: name of published process
  depends_on: [research]
```

### With Input Mapping

```yaml
- id: run-analysis
  type: sub_process
  process_name: analysis-flow
  version: "2"                    # Optional: specific version
  input_mapping:                  # Optional: map parent data to child input
    topic: "{{input.topic}}"
    research_data: "{{steps.research.output}}"
  output_key: analysis            # Optional: key for child output (default: result)
  wait_for_completion: true       # Optional: default true
  timeout: 1h                     # Optional: default 1h
  depends_on: [research]
```

### Full Example: Parent Process

```yaml
name: content-pipeline
version: 1
description: Research, analyze, and write content

steps:
  - id: research
    type: agent_task
    agent: research-agent
    message: Research the topic: {{input.topic}}

  - id: analyze
    type: sub_process
    process_name: analysis-process
    input_mapping:
      data: "{{steps.research.output}}"
    output_key: analysis
    depends_on: [research]

  - id: write
    type: agent_task
    agent: writer-agent
    message: |
      Write based on analysis:
      {{steps.analyze.analysis}}
    depends_on: [analyze]

outputs:
  - name: article
    source: "{{steps.write.output}}"
```

---

## Backend Layer

### SubProcessHandler

**File:** `src/backend/services/process_engine/engine/handlers/sub_process.py:39-283`

```python
class SubProcessHandler(StepHandler):
    """
    Handler for sub_process step type.

    Key features:
    - Load child ProcessDefinition by name/version
    - Create child ProcessExecution with mapped inputs
    - Execute via ExecutionEngine (handles recursive execution)
    - Link parent/child executions for navigation
    - Return child output to parent
    - Aggregate child costs into parent total
    """

    def __init__(
        self,
        definition_repo: Optional[ProcessDefinitionRepository] = None,
        engine_factory: Optional[Callable[[], "ExecutionEngine"]] = None,
        expression_evaluator: Optional[ExpressionEvaluator] = None,
    ):
        self._definition_repo = definition_repo
        self._engine_factory = engine_factory
        self.expression_evaluator = expression_evaluator or ExpressionEvaluator()
```

### Execute Method

**File:** `src/backend/services/process_engine/engine/handlers/sub_process.py:85-197`

```python
async def execute(self, context: StepContext, config: StepConfig) -> StepResult:
    """
    Execute a sub-process step.

    1. Load the child process definition
    2. Map input data from parent context
    3. Create and execute child execution
    4. Return child output to parent
    """
    # 1. Load child process definition
    child_definition = self._load_child_definition(config.process_name, config.version)
    if not child_definition:
        return StepResult.fail(
            f"Sub-process '{config.process_name}' not found or not published",
            error_code="PROCESS_NOT_FOUND",
        )

    # 2. Map input data from parent context to child input
    child_input = self._map_input_data(config.input_mapping, context)

    # 3. Execute child process
    engine = self._engine_factory()
    child_execution = await engine.start(
        definition=child_definition,
        input_data=child_input,
        triggered_by="sub_process",
        parent_execution_id=context.execution.id,
        parent_step_id=context.step_definition.id,
    )

    # 4. Check child execution result
    if child_execution.status.value == "completed":
        output = {
            config.output_key: child_execution.output_data,
            "child_execution_id": str(child_execution.id),
            "child_process_name": child_definition.name,
            "child_process_version": str(child_definition.version),
            "child_duration_seconds": child_execution.duration.seconds if child_execution.duration else 0,
            "child_cost": str(child_execution.total_cost),
        }
        return StepResult.ok(output)

    elif child_execution.status.value == "failed":
        error_msg = child_execution.output_data.get("error", "Unknown error")
        return StepResult.fail(
            f"Sub-process '{config.process_name}' failed: {error_msg}",
            error_code="SUB_PROCESS_FAILED",
        )

    elif child_execution.status.value == "paused":
        # Child is waiting for approval - propagate waiting state
        return StepResult.wait({
            "child_execution_id": str(child_execution.id),
            "child_process_name": child_definition.name,
            "waiting_reason": "Child process waiting for approval",
        })
```

### Input Mapping

**File:** `src/backend/services/process_engine/engine/handlers/sub_process.py:236-283`

```python
def _map_input_data(
    self,
    input_mapping: dict[str, str],
    context: StepContext,
) -> dict[str, Any]:
    """
    Map parent context data to child input.

    Input mapping uses expressions like:
    - "{{input.topic}}" - Map from parent input
    - "{{steps.research.output.summary}}" - Map from previous step output
    """
    if not input_mapping:
        # If no mapping specified, pass parent input as-is
        return context.input_data.copy()

    child_input = {}
    eval_context = EvaluationContext(
        input_data=context.input_data,
        step_outputs=context.step_outputs,
        execution_id=str(context.execution.id),
        process_name=context.execution.process_name,
    )

    for child_key, expression in input_mapping.items():
        if isinstance(expression, str) and "{{" in expression:
            # Evaluate expression
            try:
                value = self.expression_evaluator.evaluate(expression, eval_context)
                child_input[child_key] = value
            except Exception as e:
                logger.warning(
                    f"Failed to evaluate input mapping '{child_key}': {e}, "
                    f"using raw expression"
                )
                child_input[child_key] = expression
        else:
            # Literal value
            child_input[child_key] = expression

    return child_input
```

### Load Child Definition

**File:** `src/backend/services/process_engine/engine/handlers/sub_process.py:199-234`

```python
def _load_child_definition(
    self,
    process_name: str,
    version_str: Optional[str],
) -> Optional[ProcessDefinition]:
    """
    Load the child process definition.
    Returns None if process doesn't exist or isn't published.
    """
    if version_str:
        # Load specific version
        version = Version.from_string(version_str)
        definition = self._definition_repo.get_by_name(process_name, version)
    else:
        # Load latest published version
        definition = self._definition_repo.get_latest_version(process_name)

    # Verify definition is published
    if definition and definition.status != DefinitionStatus.PUBLISHED:
        logger.warning(
            f"Process '{process_name}' found but not published "
            f"(status={definition.status.value})"
        )
        return None

    return definition
```

---

## Parent-Child Linking

### ProcessExecution Fields

**File:** `src/backend/services/process_engine/domain/aggregates.py:389-436`

```python
@dataclass
class ProcessExecution:
    # ... other fields ...

    # Sub-process tracking (parent/child relationships)
    parent_execution_id: Optional[ExecutionId] = None  # Parent execution if this is a child
    parent_step_id: Optional[StepId] = None            # Step in parent that spawned this
    child_execution_ids: list[ExecutionId] = field(default_factory=list)  # Child executions

    def add_child_execution(self, child_id: ExecutionId) -> None:
        """Add a child execution ID to track sub-process calls."""
        if child_id not in self.child_execution_ids:
            self.child_execution_ids.append(child_id)

    def is_sub_process(self) -> bool:
        """Check if this execution is a sub-process (has a parent)."""
        return self.parent_execution_id is not None

    def has_children(self) -> bool:
        """Check if this execution has spawned child processes."""
        return len(self.child_execution_ids) > 0
```

### Linking During Execution

**File:** `src/backend/services/process_engine/engine/execution_engine.py:146-192`

```python
async def start(
    self,
    definition: ProcessDefinition,
    input_data: Optional[dict[str, Any]] = None,
    triggered_by: str = "manual",
    parent_execution_id: Optional[ExecutionId] = None,
    parent_step_id: Optional[StepId] = None,
) -> ProcessExecution:
    # Create execution with parent reference
    execution = ProcessExecution.create(
        definition=definition,
        input_data=input_data or {},
        triggered_by=triggered_by,
        parent_execution_id=parent_execution_id,
        parent_step_id=parent_step_id,
    )

    # Save initial state
    self.execution_repo.save(execution)

    # If this is a sub-process, update parent to track child
    if parent_execution_id:
        parent_execution = self.execution_repo.get_by_id(parent_execution_id)
        if parent_execution:
            parent_execution.add_child_execution(execution.id)
            self.execution_repo.save(parent_execution)
            logger.info(
                f"Sub-process execution {execution.id} linked to parent {parent_execution_id}"
            )
```

### Handler Registration

**File:** `src/backend/routers/executions.py:190-208`

```python
def get_handler_registry() -> StepHandlerRegistry:
    """Get the step handler registry."""
    global _handler_registry
    if _handler_registry is None:
        _handler_registry = StepHandlerRegistry()
        # Register default handlers
        _handler_registry.register(AgentTaskHandler())
        _handler_registry.register(HumanApprovalHandler())
        _handler_registry.register(GatewayHandler())
        _handler_registry.register(NotificationHandler())
        _handler_registry.register(TimerHandler())

        # Register SubProcessHandler with required dependencies
        sub_process_handler = SubProcessHandler(
            definition_repo=get_definition_repo(),
            engine_factory=get_execution_engine,
        )
        _handler_registry.register(sub_process_handler)
    return _handler_registry
```

---

## Frontend Layer

### Breadcrumb Navigation

**File:** `src/frontend/src/views/ProcessExecutionDetail.vue:9-24`

```vue
<!-- Breadcrumb navigation for nested executions -->
<nav v-if="breadcrumbs.length > 1" class="flex items-center space-x-2 text-sm mb-4" aria-label="Breadcrumb">
  <HomeIcon class="w-4 h-4 text-gray-400" />
  <template v-for="(crumb, index) in breadcrumbs" :key="crumb.id">
    <ChevronRightIcon class="w-4 h-4 text-gray-400" />
    <router-link
      v-if="index < breadcrumbs.length - 1"
      :to="`/executions/${crumb.id}`"
      class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
    >
      {{ crumb.process_name }}
    </router-link>
    <span v-else class="text-gray-700 dark:text-gray-300 font-medium">
      {{ crumb.process_name }}
    </span>
  </template>
</nav>
```

### Building Breadcrumbs

**File:** `src/frontend/src/views/ProcessExecutionDetail.vue:561-595`

```javascript
async function buildBreadcrumbs() {
  const crumbs = []
  let currentExec = execution.value

  // Start with current execution
  if (currentExec) {
    crumbs.unshift({
      id: currentExec.id,
      process_name: currentExec.process_name,
    })
  }

  // Traverse up the parent chain (max 10 levels to prevent infinite loops)
  let depth = 0
  while (currentExec?.parent_execution_id && depth < 10) {
    try {
      const parentExec = await executionsStore.getExecution(currentExec.parent_execution_id)
      if (parentExec) {
        crumbs.unshift({
          id: parentExec.id,
          process_name: parentExec.process_name,
        })
        currentExec = parentExec
      } else {
        break
      }
    } catch (e) {
      console.warn('Failed to load parent execution:', e)
      break
    }
    depth++
  }

  breadcrumbs.value = crumbs
}
```

### Parent/Child Badges

**File:** `src/frontend/src/views/ProcessExecutionDetail.vue:87-108`

```vue
<!-- Sub-process relationship badge (Called by parent) -->
<p v-if="execution.parent_execution_id" class="mt-1 text-sm">
  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300">
    <ArrowUpIcon class="w-3 h-3" />
    Called by:
    <router-link
      :to="`/executions/${execution.parent_execution_id}`"
      class="underline hover:text-indigo-900 dark:hover:text-indigo-100"
    >
      {{ execution.parent_execution_id.substring(0, 8) }}...
    </router-link>
    <span v-if="execution.parent_step_id" class="text-indigo-500 dark:text-indigo-400">
      (step: {{ execution.parent_step_id }})
    </span>
  </span>
</p>

<!-- Child executions indicator -->
<p v-if="execution.child_execution_ids && execution.child_execution_ids.length > 0" class="mt-1 text-sm">
  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300">
    <ArrowDownIcon class="w-3 h-3" />
    {{ execution.child_execution_ids.length }} child execution{{ execution.child_execution_ids.length > 1 ? 's' : '' }}
  </span>
</p>
```

### Store API Call

**File:** `src/frontend/src/stores/executions.js:102-113`

```javascript
async function getExecution(id) {
  if (!id) {
    console.warn('getExecution called with no ID')
    return null
  }
  const token = localStorage.getItem('token')
  const response = await axios.get(`/api/executions/${id}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  currentExecution.value = response.data
  return response.data
}
```

---

## API Response

### ExecutionDetail Model

**File:** `src/backend/routers/executions.py:96-117`

```python
class ExecutionDetail(BaseModel):
    """Detailed view of an execution."""
    id: str
    process_id: str
    process_version: str
    process_name: str
    status: str
    triggered_by: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    total_cost: Optional[str] = None
    # ... other fields ...
    # Sub-process relationships
    parent_execution_id: Optional[str] = None  # Parent execution if this is a sub-process
    parent_step_id: Optional[str] = None       # Step that spawned this sub-process
    child_execution_ids: List[str] = Field(default_factory=list)  # Child executions
```

### Response Mapping

**File:** `src/backend/routers/executions.py:760-832`

```python
def _to_detail(
    execution: ProcessExecution,
    definition: Optional[ProcessDefinition] = None,
) -> ExecutionDetail:
    # ... step processing ...

    return ExecutionDetail(
        id=str(execution.id),
        process_id=str(execution.process_id),
        # ... other fields ...
        # Sub-process relationships
        parent_execution_id=str(execution.parent_execution_id) if execution.parent_execution_id else None,
        parent_step_id=str(execution.parent_step_id) if execution.parent_step_id else None,
        child_execution_ids=[str(cid) for cid in (execution.child_execution_ids or [])],
    )
```

### Example Response

```json
{
  "id": "child-execution-uuid",
  "process_id": "analysis-process-uuid",
  "process_name": "analysis-process",
  "status": "completed",
  "triggered_by": "sub_process",
  "parent_execution_id": "parent-execution-uuid",
  "parent_step_id": "call-analysis",
  "child_execution_ids": [],
  "input_data": {"data": "..."},
  "output_data": {"result": "..."},
  "total_cost": "$0.15"
}
```

---

## Cost Aggregation

Child costs are included in step output and can be aggregated by the parent:

```python
# SubProcessHandler returns cost info in output
output = {
    config.output_key: child_execution.output_data,
    "child_execution_id": str(child_execution.id),
    "child_process_name": child_definition.name,
    "child_process_version": str(child_definition.version),
    "child_duration_seconds": child_execution.duration.seconds if child_execution.duration else 0,
    "child_cost": str(child_execution.total_cost),
}
```

---

## Error Handling

| Error | Code | Cause | Handler Location |
|-------|------|-------|------------------|
| Process not found | `PROCESS_NOT_FOUND` | Child process doesn't exist or isn't published | sub_process.py:129-132 |
| Configuration error | `CONFIGURATION_ERROR` | Handler not properly configured (missing repo/factory) | sub_process.py:104-114 |
| Invalid config | `INVALID_CONFIG` | Config is not SubProcessConfig | sub_process.py:98-102 |
| Sub-process failed | `SUB_PROCESS_FAILED` | Child execution failed | sub_process.py:172-177 |
| Unexpected state | `UNEXPECTED_STATE` | Child ended in unexpected status | sub_process.py:187-191 |

---

## Validation

### Recursive Detection

The validator detects direct self-recursion when publishing a process:

```python
# Validation should detect:
- id: call-self
  type: sub_process
  process_name: my-process  # Same as current process name = error
```

### Sub-Process Existence Check

At runtime, the handler checks:
1. Process exists (`get_by_name` or `get_latest_version`)
2. Process is published (`status == DefinitionStatus.PUBLISHED`)

---

## Testing

### Prerequisites
- Two published processes (parent and child)
- Child process must be published before parent can call it
- Backend running with all handlers registered

### Test Cases

1. **Basic sub-process call**
   - Action: Run parent with sub-process step
   - Expected: Child executes, output returned to parent under `output_key`

2. **Input mapping**
   - Action: Map parent data to child input using `{{...}}` expressions
   - Expected: Child receives evaluated values

3. **Breadcrumb navigation**
   - Action: Navigate to child execution detail page
   - Expected: Breadcrumbs show parent chain with clickable links

4. **Child failure handling**
   - Action: Child process fails
   - Expected: Parent step fails with `SUB_PROCESS_FAILED` error code

5. **Child paused (approval)**
   - Action: Child has human_approval step that pauses
   - Expected: Parent step returns `StepResult.wait()`, parent execution pauses

6. **Version specification**
   - Action: Specify `version: "2"` in config
   - Expected: Loads specific version instead of latest

---

## Related Flows

- [process-definition.md](./process-definition.md) - How to define sub-process steps in YAML
- [process-execution.md](./process-execution.md) - How ExecutionEngine starts child execution
- [process-monitoring.md](./process-monitoring.md) - Breadcrumb UI in execution detail
- [human-approval.md](./human-approval.md) - How child approval steps propagate wait state

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | Rebuilt with accurate line numbers and comprehensive code references |
| 2026-01-16 | Initial creation |
