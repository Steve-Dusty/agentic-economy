# Feature: Agent Roles (EMI Pattern)

> Executor/Monitor/Informed role assignments for process steps enabling multi-agent collaboration

---

## Overview

The EMI (Executor/Monitor/Informed) pattern defines agent roles within process steps:

| Role | Cardinality | Purpose |
|------|-------------|---------|
| **Executor** | Exactly one | The agent that performs the actual work |
| **Monitor** | Zero or more | Agents that own the outcome and can intervene |
| **Informed** | Zero or more | Agents that receive events for learning/awareness via NDJSON files |

This pattern enables multi-agent collaboration where specialized agents work together while maintaining clear accountability.

---

## User Story

As a process designer, I want to assign different roles to agents for each step so that I can implement delegation patterns where executors do the work, monitors supervise, and informed agents learn from outcomes.

---

## Entry Points

| Location | File | Line | Description |
|----------|------|------|-------------|
| **YAML Editor** | Process YAML | - | `roles:` block in step definition |
| **Roles Tab** | ProcessEditor.vue | 234-246 | "Roles" tab in tab navigation |
| **Role Matrix** | RoleMatrix.vue | - | Visual role assignment grid |
| **Backend Validation** | validator.py | 426-511 | `_validate_step_roles()` method |
| **Notification Trigger** | execution_engine.py | 598-604 | `_notify_informed_agents()` on step completion |

---

## Architecture

```
+-----------------------------------------------------------------------------+
|                              Frontend                                        |
|  +-----------------------------------------------------------------------+  |
|  |  ProcessEditor.vue                                                     |  |
|  |  +-- activeTab = 'roles'  (line 234-246)                              |  |
|  |  +-- parsedSteps computed (line 838-853)                              |  |
|  |  +-- handleRolesUpdate() (line 1529-1573)                             |  |
|  |      +-- Updates YAML with roles block                                |  |
|  +-----------------------------------------------------------------------+  |
|  |  RoleMatrix.vue                                                        |  |
|  |  +-- Grid UI: steps (rows) x agents (columns)                         |  |
|  |  +-- toggleRole() cycles: null -> E -> M -> I -> null (line 345-377)  |  |
|  |  +-- Validation warnings for missing executor (line 266-281)          |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+
                                    |
                                    | POST /api/processes (YAML with roles)
                                    v
+-----------------------------------------------------------------------------+
|                              Backend                                         |
|  +-----------------------------------------------------------------------+  |
|  |  services/validator.py - ProcessValidator                              |  |
|  |  +-- _validate_step_roles() (line 426-511)                            |  |
|  |      +-- Executor required if roles specified                          |  |
|  |      +-- Monitors must be list of strings                              |  |
|  |      +-- Informed must be list of strings                              |  |
|  |      +-- Warn if agent in multiple roles                               |  |
|  +-----------------------------------------------------------------------+  |
|  |  domain/entities.py - StepRoles                                        |  |
|  |  +-- StepRoles dataclass (line 34-73)                                 |  |
|  |      +-- executor: str (required)                                      |  |
|  |      +-- monitors: list[str]                                           |  |
|  |      +-- informed: list[str]                                           |  |
|  +-----------------------------------------------------------------------+  |
|  |  domain/enums.py - AgentRole                                           |  |
|  |  +-- EXECUTOR, MONITOR, INFORMED enum (line 63-74)                    |  |
|  +-----------------------------------------------------------------------+  |
|  |  engine/execution_engine.py                                            |  |
|  |  +-- _handle_step_success() calls _notify_informed_agents() (line 598-604)
|  |  +-- _handle_step_failure() calls _notify_informed_agents_failure() (line 693-699)
|  +-----------------------------------------------------------------------+  |
|  |  services/informed_notifier.py - InformedAgentNotifier                 |  |
|  |  +-- notify_step_completed() (line 91-125)                            |  |
|  |  +-- notify_step_failed() (line 127-162)                              |  |
|  |  +-- _deliver_via_mcp() (line 242-267)                                |  |
|  |  +-- _write_to_memory() NDJSON (line 269-316)                         |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|                              Agent Containers                                |
|  +-------------------+  +-------------------+  +-------------------+        |
|  |  executor-agent   |  |  monitor-agent    |  |  informed-agent   |        |
|  |  (does work)      |  |  (can intervene)  |  |  (learns)         |        |
|  |                   |  |                   |  |                   |        |
|  |                   |  |                   |  |  .trinity/        |        |
|  |                   |  |                   |  |   events/         |        |
|  |                   |  |                   |  |    *.ndjson       |        |
|  +-------------------+  +-------------------+  +-------------------+        |
+-----------------------------------------------------------------------------+
```

---

## Frontend Layer

### ProcessEditor.vue

**File**: `src/frontend/src/views/ProcessEditor.vue`

| Line | Code | Purpose |
|------|------|---------|
| 234-246 | `activeTab === 'roles'` | Tab selection for Roles view |
| 367-374 | `<RoleMatrix .../>` | Role Matrix component mount |
| 838-853 | `parsedSteps` computed | Parse steps from YAML for matrix |
| 1529-1573 | `handleRolesUpdate()` | Update YAML when roles change |

```javascript
// ProcessEditor.vue:1529-1573
function handleRolesUpdate(rolesMap) {
  try {
    const parsed = jsyaml.load(yamlContent.value)
    if (!parsed?.steps) return

    // Update each step's roles
    let modified = false
    for (const step of parsed.steps) {
      const newRoles = rolesMap[step.id]
      if (newRoles) {
        if (newRoles.executor) {
          step.roles = {
            executor: newRoles.executor,
          }
          if (newRoles.monitors && newRoles.monitors.length > 0) {
            step.roles.monitors = newRoles.monitors
          }
          if (newRoles.informed && newRoles.informed.length > 0) {
            step.roles.informed = newRoles.informed
          }
          modified = true
        } else if (step.roles) {
          delete step.roles
          modified = true
        }
      }
    }

    if (modified) {
      yamlContent.value = jsyaml.dump(parsed, { indent: 2, lineWidth: -1 })
      hasUnsavedChanges.value = true
    }
  } catch (error) {
    showNotification('Failed to update roles', 'error')
  }
}
```

### RoleMatrix.vue

**File**: `src/frontend/src/components/process/RoleMatrix.vue`

| Line | Code | Purpose |
|------|------|---------|
| 37-49 | Legend | E/M/I color-coded legend |
| 63-145 | Matrix table | Steps x Agents grid |
| 119-139 | Role cell | Click to toggle role |
| 229-241 | `localRoles` watch | Initialize from step props |
| 266-281 | `validationWarnings` | Missing executor warnings |
| 289-296 | `getRole()` | Determine role for step/agent |
| 345-377 | `toggleRole()` | Cycle: null -> E -> M -> I -> null |
| 392-402 | `emitUpdate()` | Emit roles map to parent |

**Role Cycling Logic**:
```javascript
// RoleMatrix.vue:345-377
function toggleRole(stepId, agent) {
  if (!editMode.value) return

  const roles = localRoles.value[stepId]
  const currentRole = getRole(stepId, agent)

  // Remove from current role
  if (currentRole === 'executor') {
    roles.executor = ''
  } else if (currentRole === 'monitor') {
    roles.monitors = roles.monitors.filter(m => m !== agent)
  } else if (currentRole === 'informed') {
    roles.informed = roles.informed.filter(i => i !== agent)
  }

  // Add to next role in cycle: null -> E -> M -> I -> null
  switch (currentRole) {
    case null:
      roles.executor = agent
      break
    case 'executor':
      roles.monitors.push(agent)
      break
    case 'monitor':
      roles.informed.push(agent)
      break
    // 'informed' -> null (already removed above)
  }

  emitUpdate()
}
```

---

## Backend Layer

### Domain Model

#### StepRoles Entity

**File**: `src/backend/services/process_engine/domain/entities.py:34-73`

```python
@dataclass
class StepRoles:
    """
    EMI role assignments for a process step.

    Reference: IT1 Section - EMI Pattern (Executor/Monitor/Informed)

    - Executor: The agent that performs the work (exactly one per step)
    - Monitor: Agents that own the outcome and can intervene
    - Informed: Agents that receive events for learning/awareness
    """
    executor: str  # Required - agent name that performs the work
    monitors: list[str] = field(default_factory=list)  # Agents that can intervene
    informed: list[str] = field(default_factory=list)  # Agents that receive notifications

    @classmethod
    def from_dict(cls, data: dict) -> "StepRoles":
        """Create from dictionary (YAML parsing)."""
        return cls(
            executor=data.get("executor", ""),
            monitors=data.get("monitors", []),
            informed=data.get("informed", []),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {"executor": self.executor}
        if self.monitors:
            result["monitors"] = self.monitors
        if self.informed:
            result["informed"] = self.informed
        return result

    def all_agents(self) -> list[str]:
        """Return all agents involved in this step."""
        agents = [self.executor] if self.executor else []
        agents.extend(self.monitors)
        agents.extend(self.informed)
        return agents
```

#### AgentRole Enum

**File**: `src/backend/services/process_engine/domain/enums.py:63-74`

```python
class AgentRole(str, Enum):
    """
    Role that an agent plays in a process step.

    EMI Pattern from IT1:
    - Executor: The agent that performs the work (exactly one per step)
    - Monitor: Agent that owns the outcome and can intervene (zero or more)
    - Informed: Agent that receives events for learning/awareness (zero or more)
    """
    EXECUTOR = "executor"
    MONITOR = "monitor"
    INFORMED = "informed"
```

#### InformedNotification Event

**File**: `src/backend/services/process_engine/domain/events.py:510-537`

```python
@dataclass(frozen=True)
class InformedNotification(DomainEvent):
    """
    Notification sent to informed agents about step events.

    Part of the EMI (Executor/Monitor/Informed) pattern.
    Informed agents receive these notifications for awareness
    and learning but don't need to take action.
    """
    event_type_name: str  # "step_completed", "step_failed"
    process_name: str
    execution_id: ExecutionId
    step_id: StepId
    step_name: str
    output_summary: str  # Truncated output for context
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "event_type_name": self.event_type_name,
            "process_name": self.process_name,
            "execution_id": str(self.execution_id),
            "step_id": str(self.step_id),
            "step_name": self.step_name,
            "output_summary": self.output_summary,
            "metadata": self.metadata,
        }
```

### Validation

**File**: `src/backend/services/process_engine/services/validator.py:426-511`

```python
def _validate_step_roles(
    self,
    step: dict,
    index: int,
    step_type: str,
    result: ValidationResult,
) -> None:
    """Validate EMI roles for a step."""
    path_prefix = f"steps[{index}].roles"
    roles = step.get("roles", {})

    if not isinstance(roles, dict):
        result.add_error(message="Field 'roles' must be an object", path=path_prefix)
        return

    # Executor is required if roles are specified
    executor = roles.get("executor")
    if not executor:
        result.add_error(
            message="Roles must include an 'executor' agent",
            path=f"{path_prefix}.executor",
            suggestion="Add 'executor: agent-name' to specify which agent executes this step",
        )
    elif not isinstance(executor, str):
        result.add_error(
            message="Field 'executor' must be a string (agent name)",
            path=f"{path_prefix}.executor",
        )
    else:
        # For agent_task, executor should match step's agent field
        if step_type == "agent_task":
            step_agent = step.get("agent")
            if step_agent and executor != step_agent:
                result.add_warning(
                    message=f"Role executor '{executor}' differs from step agent '{step_agent}'",
                    path=f"{path_prefix}.executor",
                )

    # Validate monitors list
    monitors = roles.get("monitors", [])
    if not isinstance(monitors, list):
        result.add_error(message="Field 'monitors' must be a list of agent names", path=f"{path_prefix}.monitors")
    else:
        for i, monitor in enumerate(monitors):
            if not isinstance(monitor, str):
                result.add_error(message=f"Monitor at index {i} must be a string", path=f"{path_prefix}.monitors[{i}]")
            elif executor and monitor == executor:
                result.add_warning(message=f"Agent '{monitor}' is both executor and monitor (redundant)", path=f"{path_prefix}.monitors[{i}]")

    # Validate informed list
    informed = roles.get("informed", [])
    if not isinstance(informed, list):
        result.add_error(message="Field 'informed' must be a list of agent names", path=f"{path_prefix}.informed")
    else:
        for i, agent in enumerate(informed):
            if not isinstance(agent, str):
                result.add_error(message=f"Informed agent at index {i} must be a string", path=f"{path_prefix}.informed[{i}]")
            elif executor and agent == executor:
                result.add_warning(message=f"Agent '{agent}' is both executor and informed (redundant)", path=f"{path_prefix}.informed[{i}]")
            elif isinstance(monitors, list) and agent in monitors:
                result.add_warning(message=f"Agent '{agent}' is in both monitors and informed lists", path=f"{path_prefix}.informed[{i}]")
```

---

## InformedAgentNotifier Service

**File**: `src/backend/services/process_engine/services/informed_notifier.py`

### Class Overview

```python
class InformedAgentNotifier:
    """
    Delivers step events to informed agents.

    Supports two delivery mechanisms:
    1. MCP message delivery (for running agents) - real-time notification
    2. Agent memory file (for persistence) - agent can read on next activation
    """

    def __init__(
        self,
        mcp_client: Optional[MCPClient] = None,
        agent_data_path: Optional[Path] = None,
        agent_checker: Optional[Callable[[str], tuple[bool, bool]]] = None,
    ):
        self._mcp_client = mcp_client
        self._agent_data_path = agent_data_path
        self._agent_checker = agent_checker
```

### Key Methods

| Line | Method | Purpose |
|------|--------|---------|
| 91-125 | `notify_step_completed()` | Notify on successful step completion |
| 127-162 | `notify_step_failed()` | Notify on step failure |
| 164-191 | `_notify_agents()` | Concurrent notification to multiple agents |
| 193-240 | `_notify_single_agent()` | Notify one agent via MCP + memory |
| 242-267 | `_deliver_via_mcp()` | Real-time MCP message delivery |
| 269-316 | `_write_to_memory()` | NDJSON file persistence |
| 318-333 | `_summarize_output()` | Truncate output for notification |

### Notification Flow

```python
# informed_notifier.py:91-125
async def notify_step_completed(
    self,
    step: StepDefinition,
    event: StepCompleted,
    execution_context: dict,
) -> list[NotificationResult]:
    """Notify all informed agents about step completion."""
    if not step.roles or not step.roles.informed:
        return []

    notification = InformedNotification(
        event_type_name="step_completed",
        process_name=execution_context.get("process_name", "unknown"),
        execution_id=event.execution_id,
        step_id=event.step_id,
        step_name=event.step_name,
        output_summary=self._summarize_output(event.output),
        metadata={
            "cost": str(event.cost),
            "duration_seconds": event.duration.seconds if event.duration else 0,
        },
    )

    return await self._notify_agents(step.roles.informed, notification)
```

### Delivery Mechanisms

```python
# informed_notifier.py:193-240
async def _notify_single_agent(
    self,
    agent_name: str,
    notification: InformedNotification,
) -> NotificationResult:
    """Send notification to a single agent via MCP and/or memory file."""
    result = NotificationResult(agent_name=agent_name)

    # Check if agent exists and is running
    is_running = False
    if self._agent_checker:
        try:
            exists, is_running = self._agent_checker(agent_name)
            if not exists:
                logger.warning(f"Informed agent '{agent_name}' does not exist")
        except Exception as e:
            logger.warning(f"Could not check agent '{agent_name}': {e}")

    # Try MCP delivery if agent is running
    if is_running and self._mcp_client:
        try:
            result.mcp_delivered = await self._deliver_via_mcp(agent_name, notification)
        except Exception as e:
            logger.warning(f"MCP delivery to '{agent_name}' failed: {e}")
            result.error = f"MCP delivery failed: {e}"

    # Always try memory persistence
    if self._agent_data_path:
        try:
            result.memory_written = await self._write_to_memory(agent_name, notification)
        except Exception as e:
            logger.warning(f"Memory write for '{agent_name}' failed: {e}")
            result.error = f"Memory write failed: {e}"

    return result
```

### NDJSON Memory Persistence

```python
# informed_notifier.py:269-316
async def _write_to_memory(
    self,
    agent_name: str,
    notification: InformedNotification,
) -> bool:
    """
    Write notification to agent's memory file.
    Uses NDJSON format (newline-delimited JSON) for easy parsing.
    """
    if not self._agent_data_path:
        return False

    # Create events directory for agent
    events_dir = self._agent_data_path / agent_name / ".trinity" / "events"

    # Run file I/O in executor to avoid blocking
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, self._write_to_memory_sync, events_dir, notification)

def _write_to_memory_sync(self, events_dir: Path, notification: InformedNotification) -> bool:
    """Synchronous memory write operation."""
    try:
        events_dir.mkdir(parents=True, exist_ok=True)

        # Use date-based file naming for organization
        today = _utcnow().strftime("%Y-%m-%d")
        events_file = events_dir / f"notifications_{today}.ndjson"

        # Append to NDJSON file
        with open(events_file, "a") as f:
            f.write(json.dumps(notification.to_dict()) + "\n")

        logger.debug(f"Wrote notification to '{events_file}'")
        return True
    except Exception as e:
        logger.error(f"Failed to write notification to memory: {e}")
        return False
```

---

## ExecutionEngine Integration

**File**: `src/backend/services/process_engine/engine/execution_engine.py`

### Notification on Step Success

```python
# execution_engine.py:598-604
# In _handle_step_success()
await self._publish_event(step_completed_event)

# Notify informed agents (EMI pattern) - run async, don't block
if self.informed_notifier and step_def.roles and step_def.roles.informed:
    asyncio.create_task(self._notify_informed_agents(
        step_def,
        step_completed_event,
        execution,
    ))
```

### Notification on Step Failure

```python
# execution_engine.py:693-699
# In _handle_step_failure()
await self._publish_event(step_failed_event)

# Notify informed agents (EMI pattern) - run async, don't block
if self.informed_notifier and step_def.roles and step_def.roles.informed:
    asyncio.create_task(self._notify_informed_agents_failure(
        step_def,
        step_failed_event,
        execution,
    ))
```

### Helper Methods

```python
# execution_engine.py:989-1036
async def _notify_informed_agents(
    self,
    step_def: StepDefinition,
    event: StepCompleted,
    execution: ProcessExecution,
) -> None:
    """
    Notify informed agents about step completion.
    Runs asynchronously to avoid blocking execution.
    Part of the EMI (Executor/Monitor/Informed) pattern.
    """
    if not self.informed_notifier:
        return

    try:
        execution_context = {
            "process_name": execution.process_name,
            "execution_id": str(execution.id),
            "triggered_by": execution.triggered_by,
        }

        results = await self.informed_notifier.notify_step_completed(
            step_def,
            event,
            execution_context,
        )

        # Log results
        for result in results:
            if result.error:
                logger.warning(f"Failed to notify informed agent '{result.agent_name}': {result.error}")
            else:
                delivery_methods = []
                if result.mcp_delivered:
                    delivery_methods.append("MCP")
                if result.memory_written:
                    delivery_methods.append("memory")
                if delivery_methods:
                    logger.debug(f"Notified '{result.agent_name}' via {', '.join(delivery_methods)}")

    except Exception as e:
        # Don't let notification failures affect execution
        logger.error(f"Error notifying informed agents: {e}")
```

---

## YAML Configuration

### Basic Role Assignment

```yaml
steps:
  - id: research
    type: agent_task
    agent: research-agent
    message: Research the topic
    roles:
      executor: research-agent  # Required
```

### Full EMI Pattern

```yaml
steps:
  - id: critical-analysis
    type: agent_task
    agent: analyst-agent
    message: Perform critical analysis of {{input.topic}}
    roles:
      executor: analyst-agent        # Required - does the work
      monitors:                      # Optional - can intervene
        - quality-agent
        - manager-agent
      informed:                      # Optional - receive NDJSON events
        - learning-agent
        - archive-agent
```

### Human Approval with Roles

```yaml
steps:
  - id: approval
    type: human_approval
    title: Manager Approval
    description: Please review the analysis
    roles:
      executor: approval-system      # Can be system/process name
      monitors:
        - manager-agent
      informed:
        - audit-agent
```

---

## NDJSON Notification Format

**File Path**: `{agent_data_path}/{agent_name}/.trinity/events/notifications_YYYY-MM-DD.ndjson`

### Step Completed Event

```json
{"event_type":"InformedNotification","timestamp":"2026-01-23T10:30:00.000000+00:00","event_type_name":"step_completed","process_name":"content-pipeline","execution_id":"exec-uuid-here","step_id":"research","step_name":"Research Topic","output_summary":"{\"response\":\"The research found...\"}","metadata":{"cost":"$0.10","duration_seconds":45}}
```

### Step Failed Event

```json
{"event_type":"InformedNotification","timestamp":"2026-01-23T10:31:00.000000+00:00","event_type_name":"step_failed","process_name":"content-pipeline","execution_id":"exec-uuid-here","step_id":"write","step_name":"Write Draft","output_summary":"Agent timeout after 300s","metadata":{"error_code":"TIMEOUT","retry_count":3,"will_retry":false}}
```

### Reading Notifications (Agent Side)

```python
import json
from pathlib import Path

events_dir = Path.home() / ".trinity" / "events"
for events_file in sorted(events_dir.glob("notifications_*.ndjson")):
    with open(events_file) as f:
        for line in f:
            event = json.loads(line)
            if event["event_type_name"] == "step_completed":
                print(f"Step {event['step_name']} completed in {event['metadata']['duration_seconds']}s")
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Roles not an object | 400 | Field 'roles' must be an object |
| Missing executor | 400 | Roles must include an 'executor' agent |
| Executor not a string | 400 | Field 'executor' must be a string |
| Monitors not a list | 400 | Field 'monitors' must be a list |
| Informed not a list | 400 | Field 'informed' must be a list |
| Agent not found | warn | Logged, notification skipped |
| MCP delivery failed | warn | Falls back to memory only |
| Memory write failed | warn | Logged, execution continues |

---

## Security Considerations

1. **Notification isolation**: Informed agents only see output summaries (truncated to 500 chars), not full execution data
2. **Non-blocking**: Notifications run as async tasks; failures don't affect process execution
3. **Agent validation**: Notifier checks if target agent exists before attempting delivery
4. **File permissions**: NDJSON files created in agent's `.trinity/` directory with standard permissions

---

## Testing

### Prerequisites
- Backend running at `localhost:8000`
- Multiple agents created (e.g., `executor-agent`, `monitor-agent`, `learning-agent`)
- Process with roles defined and published

### Test Cases

| # | Test | Action | Expected |
|---|------|--------|----------|
| 1 | Role validation - missing executor | Create step with `roles: {monitors: [x]}` | Validation error |
| 2 | Role validation - redundant roles | Set same agent as executor and monitor | Validation warning |
| 3 | RoleMatrix UI toggle | Click empty cell for agent | Cell shows "E", updates to Executor |
| 4 | RoleMatrix UI cycle | Click "E" cell | Changes to "M" (Monitor) |
| 5 | YAML update from matrix | Assign roles via matrix | YAML shows `roles:` block |
| 6 | NDJSON creation | Run process with informed agent | Check `~/.trinity/events/` |
| 7 | Notification content | Parse NDJSON file | Contains correct step_id, output_summary |
| 8 | MCP delivery (running agent) | Run with informed agent running | Agent receives real-time message |

### Verification Commands

```bash
# Check NDJSON files created
ls -la ~/trinity-data/agents/learning-agent/.trinity/events/

# View notifications
cat ~/trinity-data/agents/learning-agent/.trinity/events/notifications_$(date +%Y-%m-%d).ndjson | jq .

# Count notifications
wc -l ~/trinity-data/agents/learning-agent/.trinity/events/*.ndjson
```

---

## Related Flows

- **Upstream**: [process-definition.md](./process-definition.md) - Role schema in YAML
- **Downstream**: [process-execution.md](./process-execution.md) - Notification triggering
- **Related**: [agent-to-agent-collaboration.md](../agent-to-agent-collaboration.md) - Inter-agent communication

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | Complete rewrite with accurate line numbers and full code references |
| 2026-01-16 | Initial creation |
