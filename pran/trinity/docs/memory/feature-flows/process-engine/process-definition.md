# Feature: Process Definition

> YAML-based process definition with validation, versioning, and publishing workflow

---

## Overview

Process definitions are declarative YAML documents that describe workflows. They specify steps, dependencies, triggers, and outputs. Definitions follow a lifecycle: **Draft** -> **Published** -> **Archived**.

**Key Capabilities:**
- YAML-based schema with step types (agent_task, gateway, human_approval, timer, notification, sub_process)
- Multi-level validation (YAML syntax, schema, semantic, agent existence)
- Version management with immutable published versions
- Live preview in editor with role matrix for EMI pattern

---

## User Story

As a **process designer**, I want to **define workflows in YAML** so that I can **automate multi-step agent orchestration with validation and version control**.

---

## Entry Points

| Type | Location | Description |
|------|----------|-------------|
| **UI** | `ProcessList.vue:51-57` | "Create Process" button |
| **UI** | `ProcessList.vue:105-111` | Click process card to edit |
| **UI** | `ProcessEditor.vue:1-738` | YAML editor with live preview |
| **API** | `POST /api/processes` | Create new process definition |
| **API** | `PUT /api/processes/{id}` | Update draft process |
| **API** | `POST /api/processes/{id}/publish` | Publish draft |

---

## Frontend Layer

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `ProcessList.vue` | `src/frontend/src/views/ProcessList.vue` | List all processes with filtering |
| `ProcessEditor.vue` | `src/frontend/src/views/ProcessEditor.vue` | YAML editor with validation |
| `YamlEditor.vue` | `src/frontend/src/components/YamlEditor.vue` | Monaco-based YAML editor |
| `ProcessFlowPreview.vue` | `src/frontend/src/components/ProcessFlowPreview.vue` | Visual flow diagram |
| `RoleMatrix.vue` | `src/frontend/src/components/process/RoleMatrix.vue` | EMI role assignment |
| `TemplateSelector.vue` | `src/frontend/src/components/process/TemplateSelector.vue` | Process template picker |

### State Management

**File:** `src/frontend/src/stores/processes.js`

```javascript
// Key actions
fetchProcesses()       // Line 51-68 - GET /api/processes
getProcess(id)         // Line 70-76 - GET /api/processes/{id}
createProcess(yaml)    // Line 78-86 - POST /api/processes
updateProcess(id,yaml) // Line 88-96 - PUT /api/processes/{id}
deleteProcess(id)      // Line 98-104 - DELETE /api/processes/{id}
publishProcess(id)     // Line 106-113 - POST /api/processes/{id}/publish
validateYaml(yaml)     // Line 133-140 - POST /api/processes/validate
createNewVersion(id)   // Line 124-131 - POST /api/processes/{id}/new-version
```

### API Calls

```javascript
// Create process (ProcessEditor.vue:1279-1320)
const created = await processesStore.createProcess(yamlContent.value)
// -> POST /api/processes { yaml_content: string }

// Validate YAML (ProcessEditor.vue:1261-1277)
const result = await processesStore.validateYaml(yamlContent.value)
// -> POST /api/processes/validate { yaml_content: string }

// Publish process (ProcessEditor.vue:1322-1333)
await processesStore.publishProcess(route.params.id)
// -> POST /api/processes/{id}/publish
```

---

## Backend Layer

### Router Endpoints

**File:** `src/backend/routers/processes.py`

| Method | Path | Handler | Line |
|--------|------|---------|------|
| POST | `/api/processes` | `create_process()` | 209-259 |
| GET | `/api/processes` | `list_processes()` | 262-307 |
| GET | `/api/processes/{id}` | `get_process()` | 310-340 |
| PUT | `/api/processes/{id}` | `update_process()` | 343-420 |
| DELETE | `/api/processes/{id}` | `delete_process()` | 423-462 |
| POST | `/api/processes/{id}/validate` | `validate_process()` | 465-489 |
| POST | `/api/processes/validate` | `validate_yaml()` | 492-505 |
| POST | `/api/processes/{id}/publish` | `publish_process()` | 508-570 |
| POST | `/api/processes/{id}/archive` | `archive_process()` | 573-614 |
| POST | `/api/processes/{id}/new-version` | `create_new_version()` | 617-644 |

### Create Process Flow

```python
# processes.py:209-259 - create_process()
async def create_process(request: ProcessCreateRequest, current_user: CurrentUser):
    # 1. Authorization check (IT5 P1)
    auth = get_auth_service()
    auth_result = auth.can_create_process(current_user)

    # 2. Validate YAML content
    validator = get_validator()
    result = validator.validate_yaml(request.yaml_content, created_by=current_user.email)

    # 3. Create ProcessDefinition aggregate
    definition = result.definition  # Already parsed by validator

    # 4. Save to repository
    repo = get_repository()
    repo.save(definition)

    # 5. Emit domain event
    await publish_event(ProcessCreated(...))

    return _to_detail(definition, request.yaml_content)
```

### Publish Process Flow

```python
# processes.py:508-570 - publish_process()
async def publish_process(process_id: str, current_user: CurrentUser):
    # 1. Authorization check
    auth_result = auth.can_publish_process(current_user)

    # 2. Load definition
    definition = repo.get_by_id(pid)

    # 3. Check status is DRAFT
    if definition.status != DefinitionStatus.DRAFT:
        raise HTTPException(400, "Cannot publish non-draft")

    # 4. Validate and publish (domain method)
    published = definition.publish()  # Raises ProcessValidationError if invalid

    # 5. Save published version
    repo.save(published)

    # 6. Register schedule triggers
    schedule_count = _register_process_schedules(published)

    # 7. Emit domain event
    await publish_event(ProcessPublished(...))
```

---

## Domain Layer

### ProcessDefinition Aggregate

**File:** `src/backend/services/process_engine/domain/aggregates.py:34-362`

```python
@dataclass
class ProcessDefinition:
    id: ProcessId                      # UUID wrapped in value object
    name: str                          # Process name (unique with version)
    description: str
    version: Version                   # Semantic versioning (major.minor)
    status: DefinitionStatus           # draft | published | archived
    steps: list[StepDefinition]        # Step entities
    outputs: list[OutputConfig]        # Output extraction config
    triggers: list[TriggerConfig]      # manual | webhook | schedule
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    @classmethod
    def create(cls, name, description, steps, outputs, triggers, created_by):
        """Factory method - creates new DRAFT definition"""
        # Line 84-109

    @classmethod
    def from_yaml_dict(cls, data: dict, created_by: Optional[str]):
        """Parse YAML dictionary into aggregate"""
        # Line 111-159

    def validate(self) -> list[str]:
        """Domain invariant checks - returns list of errors"""
        # Line 203-239
        # - Duplicate step IDs
        # - Invalid dependency references
        # - Circular dependencies
        # - Empty name
        # - No steps

    def publish(self) -> ProcessDefinition:
        """Validate and transition to PUBLISHED status"""
        # Line 279-297 - raises ProcessValidationError

    def archive(self) -> ProcessDefinition:
        """Transition to ARCHIVED status"""
        # Line 299-308

    def create_new_version(self) -> ProcessDefinition:
        """Clone with incremented version and new ID"""
        # Line 310-323
```

### StepDefinition Entity

**File:** `src/backend/services/process_engine/domain/entities.py:76-266`

```python
@dataclass
class StepDefinition:
    id: StepId                         # Validated identifier (lowercase, a-z0-9_-)
    name: str                          # Display name
    type: StepType                     # agent_task | human_approval | gateway | ...
    config: StepConfig                 # Type-specific configuration
    dependencies: list[StepId]         # Steps that must complete first
    condition: Optional[str]           # Expression for conditional execution
    retry_policy: RetryPolicy          # max_attempts, initial_delay, backoff
    error_policy: ErrorPolicy          # fail_process | skip_step | goto_step
    compensation: Optional[CompensationConfig]  # Rollback action
    roles: Optional[StepRoles]         # EMI pattern (executor/monitor/informed)
```

### Value Objects

**File:** `src/backend/services/process_engine/domain/value_objects.py`

| Value Object | Line | Purpose |
|--------------|------|---------|
| `ProcessId` | 25-51 | UUID wrapper with validation |
| `ExecutionId` | 53-80 | Execution UUID wrapper |
| `StepId` | 82-112 | Step identifier with format validation |
| `Version` | 120-189 | Semantic versioning (major.minor) |
| `Duration` | 197-340 | Time duration (supports "5m", "1h", "100ms") |
| `Money` | 347-456 | Currency amount with Decimal precision |
| `TokenUsage` | 464-528 | LLM token tracking |
| `RetryPolicy` | 536-568 | Retry configuration |
| `ErrorPolicy` | 571-612 | Error handling configuration |

### Step Configurations

**File:** `src/backend/services/process_engine/domain/step_configs.py`

| Config Class | Line | Step Type |
|--------------|------|-----------|
| `AgentTaskConfig` | 19-61 | agent_task |
| `HumanApprovalConfig` | 64-107 | human_approval |
| `GatewayConfig` | 110-138 | gateway |
| `TimerConfig` | 141-162 | timer |
| `NotificationConfig` | 165-214 | notification |
| `SubProcessConfig` | 217-264 | sub_process |
| `CompensationConfig` | 276-339 | Rollback action |

### Trigger Configurations

| Config Class | Line | Trigger Type |
|--------------|------|--------------|
| `ManualTriggerConfig` | 384-411 | manual |
| `WebhookTriggerConfig` | 347-380 | webhook |
| `ScheduleTriggerConfig` | 440-493 | schedule (cron) |

---

## Validation Service

**File:** `src/backend/services/process_engine/services/validator.py`

### Validation Pipeline

```python
class ProcessValidator:
    def validate_yaml(self, yaml_content: str, created_by: Optional[str]):
        # Line 181-247
        result = ValidationResult()

        # Level 1: YAML Syntax (Line 199-213)
        data = yaml.safe_load(yaml_content)

        # Level 2: Schema Validation (Line 216-217)
        self._validate_schema(data, result)

        # Level 3: Parse to Domain Object (Line 221-228)
        definition = ProcessDefinition.from_yaml_dict(data, created_by)

        # Level 4: Domain Invariant Checks (Line 231-233)
        domain_errors = definition.validate()

        # Level 5: Agent Existence (Warnings) (Line 236-237)
        self._check_agents(definition, result)

        # Level 6: Sub-process Existence (Warnings) (Line 240-241)
        self._check_sub_processes(definition, result)

        # Level 7: Recursive Sub-process Detection (Line 244-245)
        self._check_recursive_sub_processes(definition, result)

        return result
```

### Schema Validation Rules

**File:** `validator.py:284-353`

| Field | Rule | Error |
|-------|------|-------|
| `name` | Required, string, not empty | "Missing required field: 'name'" |
| `steps` | Required, list, min 1 item | "Process must have at least one step" |
| `step.id` | Required per step | "Step at index N missing required field: 'id'" |
| `step.type` | Required, valid enum | "Invalid step type 'foo'" |
| `step.agent` | Required if type=agent_task | "agent_task step missing required field: 'agent'" |
| `step.message` | Required if type=agent_task | "agent_task step missing required field: 'message'" |

### Cron Validation

```python
# validator.py:592-622
CRON_PRESETS = {
    "hourly": "0 * * * *",
    "daily": "0 9 * * *",
    "weekly": "0 9 * * 1",
    "monthly": "0 9 1 * *",
    "weekdays": "0 9 * * 1-5",
}

def _validate_cron_expression(self, cron: str) -> Optional[str]:
    # Accepts presets or standard 5-field cron expressions
    # Uses croniter library for detailed validation
```

---

## Repository Layer

### SQLite Repository

**File:** `src/backend/services/process_engine/repositories/sqlite_definitions.py`

```python
class SqliteProcessDefinitionRepository:
    def __init__(self, db_path: str | Path):
        # Line 40-51 - Initialize with schema creation

    def save(self, definition: ProcessDefinition) -> None:
        # Line 154-168 - INSERT OR REPLACE

    def get_by_id(self, id: ProcessId) -> Optional[ProcessDefinition]:
        # Line 170-181

    def get_by_name(self, name: str, version: Optional[Version]) -> Optional[ProcessDefinition]:
        # Line 183-210 - Returns latest published if no version specified

    def list_all(self, status, limit, offset) -> list[ProcessDefinition]:
        # Line 216-240 - Paginated list with optional status filter

    def delete(self, id: ProcessId) -> bool:
        # Line 253-261

    def count(self, status: Optional[DefinitionStatus]) -> int:
        # Line 272-284
```

### Database Schema

```sql
-- sqlite_definitions.py:69-101

CREATE TABLE process_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    description TEXT,
    definition_json TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT
);

CREATE INDEX idx_process_definitions_name ON process_definitions(name);
CREATE INDEX idx_process_definitions_status ON process_definitions(status);
CREATE UNIQUE INDEX idx_process_definitions_name_version
    ON process_definitions(name, version_major, version_minor);
```

---

## JSON Schema

**File:** `src/backend/services/process_engine/schemas/process-definition.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Process Definition",
  "type": "object",
  "required": ["name", "steps"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9-]*$",
      "minLength": 1,
      "maxLength": 64
    },
    "version": {
      "oneOf": [
        { "type": "integer", "minimum": 1 },
        { "type": "string", "pattern": "^\\d+(\\.\\d+)?$" }
      ]
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/definitions/step" }
    }
  }
}
```

---

## YAML Examples

### Minimal Process

```yaml
name: simple-task
version: 1
description: Execute a single agent task

steps:
  - id: task
    type: agent_task
    agent: my-agent
    message: Do something useful
```

### Full-Featured Process

```yaml
name: content-pipeline
version: 1
description: Generate, review, and publish content

triggers:
  - id: daily-run
    type: schedule
    cron: daily
    timezone: America/New_York

steps:
  - id: research
    name: Research Topic
    type: agent_task
    agent: research-agent
    message: Research the topic: {{input.topic}}
    timeout: 10m
    retry:
      max_attempts: 3
      initial_delay: 10s
    roles:
      executor: research-agent
      informed: [analyst-agent]

  - id: write
    name: Write Draft
    type: agent_task
    agent: writer-agent
    message: |
      Write an article based on:
      {{steps.research.output}}
    depends_on: [research]
    roles:
      executor: writer-agent
      monitors: [editor-agent]

  - id: review
    name: Human Review
    type: human_approval
    title: Review Draft
    description: Please review the generated content
    assignees: [editor@example.com]
    timeout: 48h
    depends_on: [write]

outputs:
  - name: article
    source: "{{steps.write.output}}"
```

---

## Side Effects

### WebSocket Events

```python
# processes.py:195-202 - publish_event()
# Domain events broadcast via InMemoryEventBus -> WebSocketPublisher

ProcessCreated(process_id, process_name, version, created_by)
ProcessUpdated(process_id, process_name, version, updated_by)
ProcessPublished(process_id, process_name, version, published_by)
ProcessArchived(process_id, process_name, version, archived_by)
```

### Schedule Registration

```python
# processes.py:734-826 - _register_process_schedules()
# When publishing, schedule triggers are written to process_schedules table

INSERT INTO process_schedules (
    id, process_id, process_name, trigger_id, cron_expression,
    enabled, timezone, description, created_at, updated_at, next_run_at
) VALUES (...)
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Invalid YAML syntax | 422 | "Invalid YAML syntax: {details}" |
| Missing required field | 422 | "Missing required field: 'name'" |
| Invalid step type | 422 | "Invalid step type 'foo'" |
| Circular dependency | 422 | "Circular dependency detected: a -> b -> a" |
| Update non-draft | 400 | "Cannot update process in 'published' status" |
| Publish non-draft | 400 | "Cannot publish process in 'archived' status" |
| Delete published | 400 | "Cannot delete PUBLISHED processes. Archive first." |
| Not found | 404 | "Process not found" |
| Permission denied | 403 | Auth failure reason |

---

## Security Considerations

### Authorization Service

**File:** `src/backend/services/process_engine/services/authorization.py`

```python
# processes.py:156-177 - Authorization checks

class ProcessAuthorizationService:
    def can_create_process(self, user) -> AuthResult
    def can_read_process(self, user) -> AuthResult
    def can_update_process(self, user) -> AuthResult
    def can_delete_process(self, user) -> AuthResult
    def can_publish_process(self, user) -> AuthResult

    def log_authorization_failure(self, user, action, resource_type, resource_id, reason)
```

### Required Permissions

| Action | Permission | Checked At |
|--------|------------|------------|
| Create process | PROCESS_CREATE | processes.py:221-228 |
| List processes | PROCESS_READ | processes.py:277-284 |
| Get process | PROCESS_READ | processes.py:319-327 |
| Update process | PROCESS_UPDATE | processes.py:356-363 |
| Delete process | PROCESS_DELETE | processes.py:435-442 |
| Publish process | PROCESS_PUBLISH | processes.py:519-527 |

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- Valid JWT token
- At least one agent created (for agent existence warnings)

### Test Cases

1. **Create minimal process**
   - POST `/api/processes` with minimal YAML
   - Expected: 201, status=draft

2. **Validation errors**
   - POST `/api/processes/validate` with invalid YAML
   - Expected: 422 with specific error messages

3. **Circular dependency detection**
   - Create steps where A depends on B, B depends on A
   - Expected: "Circular dependency detected"

4. **Publish workflow**
   - Save draft -> Publish
   - Expected: Status changes to published, becomes immutable

5. **Version management**
   - Create new version from published process
   - Expected: New draft with incremented version number

---

## Related Flows

- [process-execution.md](./process-execution.md) - How definitions are executed
- [agent-roles-emi.md](./agent-roles-emi.md) - EMI role validation details
- [process-scheduling.md](./process-scheduling.md) - Trigger configuration
- [process-templates.md](./process-templates.md) - Process template system
- [sub-processes.md](./sub-processes.md) - Child process invocation

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-16 | Initial creation |
| 2026-01-23 | Rebuilt with accurate line numbers and comprehensive details |
