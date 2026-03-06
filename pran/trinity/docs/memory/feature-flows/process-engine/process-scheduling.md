# Feature: Process Scheduling

> Cron-based schedule triggers for automated process execution and timer steps for delays within processes

---

## Overview

Process Scheduling provides two complementary features:
1. **Schedule Triggers** - Automatically start process executions on a cron schedule
2. **Timer Steps** - Add delays within a process workflow

**Key Capabilities:**
- Cron expression support with human-readable presets (hourly, daily, weekly, monthly, weekdays)
- Timezone-aware scheduling with IANA timezone names
- Timer steps for in-process delays (ms, s, m, h, d)
- Schedule registration on process publish, removal on archive
- Frontend display of next/last run times for schedules

---

## User Story

As a process designer, I want to schedule processes to run automatically so that recurring workflows execute without manual intervention.

As a process designer, I want to add delays between steps so that I can wait for external systems to complete before proceeding.

---

## Entry Points

| Layer | Location | Action |
|-------|----------|--------|
| **UI** | `src/frontend/src/views/ProcessEditor.vue:392-480` | Display triggers section for published processes |
| **UI** | `src/frontend/src/views/ProcessEditor.vue:828-835` | Parse triggers from YAML content |
| **Backend** | `src/backend/routers/processes.py:557-560` | Register schedules on process publish |
| **Backend** | `src/backend/routers/processes.py:601-604` | Unregister schedules on process archive |
| **Backend** | `src/backend/routers/triggers.py:267-308` | List schedule triggers API |
| **Engine** | `src/backend/services/process_engine/engine/handlers/timer.py:40-74` | Timer step execution |

---

## Architecture

```
                                Process Definition (YAML)
                                         |
                                         | triggers:
                                         |   - type: schedule
                                         |     cron: daily
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                              Backend Layer                                         |
|                                                                                    |
|   POST /api/processes/{id}/publish                                                |
|                                                                                    |
|   +-- routers/processes.py:508-570 (publish_process) --+                          |
|   |                                                     |                          |
|   |   1. Validate definition status == DRAFT           |                          |
|   |   2. Call definition.publish()                      |                          |
|   |   3. Save to repository                             |                          |
|   |   4. _register_process_schedules(published)  -------+                          |
|   |                                                     |                          |
|   +-----------------------------------------------------+                          |
|                                                                                    |
|   +-- _register_process_schedules (lines 734-827) ------+                          |
|   |                                                     |                          |
|   |   For each ScheduleTriggerConfig:                   |                          |
|   |     - Expand cron preset (expand_cron_preset)       |                          |
|   |     - Calculate next_run_at (croniter + pytz)       |                          |
|   |     - INSERT INTO process_schedules table           |                          |
|   |                                                     |                          |
|   +-----------------------------------------------------+                          |
|                                                                                    |
|   +-- Database: process_schedules --------------------------+                      |
|   | id, process_id, process_name, trigger_id                |                      |
|   | cron_expression, timezone, enabled, description          |                      |
|   | created_at, updated_at, last_run_at, next_run_at        |                      |
|   +---------------------------------------------------------+                      |
|                                                                                    |
+-----------------------------------------------------------------------------------+

                                         |
                                         | (Future: Scheduler reads and triggers)
                                         v

+-----------------------------------------------------------------------------------+
|                              Timer Step Execution                                  |
|                                                                                    |
|   ExecutionEngine._execute_step()                                                 |
|                |                                                                   |
|                v                                                                   |
|   handlers/timer.py:TimerHandler.execute()                                        |
|       - Get delay from TimerConfig                                                |
|       - await asyncio.sleep(delay_seconds)                                        |
|       - Return StepResult.ok({waited_seconds, delay_formatted})                   |
|                                                                                    |
+-----------------------------------------------------------------------------------+
```

---

## Frontend Layer

### ProcessEditor.vue - Triggers Display

**Location**: `src/frontend/src/views/ProcessEditor.vue`

The frontend displays schedule triggers for published processes with their status and timing information.

#### Trigger Section Display (lines 392-480)

```vue
<!-- Triggers section (for published processes with triggers) -->
<div v-if="!isNew && process?.status === 'published' && parsedTriggers.length > 0">
  <div v-for="trigger in parsedTriggers" :key="trigger.id">
    <!-- Schedule trigger details -->
    <div v-if="trigger.type === 'schedule'" class="mt-2 space-y-1">
      <code>{{ trigger.cron }}</code>
      <span v-if="getCronPresetLabel(trigger.cron)">
        ({{ getCronPresetLabel(trigger.cron) }})
      </span>
      <div v-if="trigger.timezone && trigger.timezone !== 'UTC'">
        {{ trigger.timezone }}
      </div>
      <div v-if="scheduleTriggerInfo[trigger.id]?.next_run_at">
        Next run: {{ formatScheduleTime(scheduleTriggerInfo[trigger.id].next_run_at) }}
      </div>
    </div>
  </div>
</div>
```

#### Trigger Parsing (lines 828-835)

```javascript
const parsedTriggers = computed(() => {
  try {
    const parsed = jsyaml.load(yamlContent.value)
    return parsed?.triggers || []
  } catch {
    return []
  }
})
```

#### Cron Preset Labels (lines 865-880)

```javascript
const cronPresetLabels = {
  'hourly': 'Every hour',
  'daily': 'Daily at 9 AM',
  'weekly': 'Weekly (Mondays at 9 AM)',
  'monthly': 'Monthly (1st at 9 AM)',
  'weekdays': 'Weekdays at 9 AM',
  '0 * * * *': 'Every hour',
  '0 9 * * *': 'Daily at 9 AM',
  '0 9 * * 1': 'Weekly (Mondays)',
  '0 9 1 * *': 'Monthly (1st)',
  '0 9 * * 1-5': 'Weekdays at 9 AM',
}

function getCronPresetLabel(cron) {
  return cronPresetLabels[cron] || null
}
```

#### Schedule Info Loading (lines 1228-1240)

```javascript
async function loadScheduleTriggerInfo(processId) {
  try {
    const response = await api.get(`/api/triggers/process/${processId}/schedules`)
    const infoMap = {}
    for (const schedule of response.data) {
      infoMap[schedule.trigger_id] = schedule
    }
    scheduleTriggerInfo.value = infoMap
  } catch (error) {
    console.warn('Failed to load schedule trigger info:', error)
  }
}
```

---

## Backend Layer

### Domain: ScheduleTriggerConfig

**Location**: `src/backend/services/process_engine/domain/step_configs.py:440-494`

```python
@dataclass(frozen=True)
class ScheduleTriggerConfig:
    """
    Configuration for scheduled triggers.
    Supports human-readable presets or standard 5-field cron expressions.
    """
    id: str
    cron: str = ""  # Cron expression or preset (e.g., "daily", "0 9 * * 1-5")
    enabled: bool = True
    timezone: str = "UTC"
    description: str = ""

    @property
    def cron_expression(self) -> str:
        """Get the full cron expression (expands presets)."""
        return expand_cron_preset(self.cron)

    @property
    def is_preset(self) -> bool:
        """Check if using a preset rather than explicit cron."""
        return self.cron in CRON_PRESETS
```

### Domain: Cron Presets

**Location**: `src/backend/services/process_engine/domain/step_configs.py:418-437`

```python
CRON_PRESETS: dict[str, str] = {
    "hourly": "0 * * * *",      # Every hour at :00
    "daily": "0 9 * * *",       # Every day at 9:00 AM
    "weekly": "0 9 * * 1",      # Every Monday at 9:00 AM
    "monthly": "0 9 1 * *",     # 1st of each month at 9:00 AM
    "weekdays": "0 9 * * 1-5",  # Weekdays at 9:00 AM
}

def expand_cron_preset(cron: str) -> str:
    """Expand cron preset to full expression."""
    return CRON_PRESETS.get(cron, cron)
```

### Domain: TimerConfig

**Location**: `src/backend/services/process_engine/domain/step_configs.py:141-162`

```python
@dataclass(frozen=True)
class TimerConfig:
    """
    Configuration for timer step type.
    Defines delays or scheduled execution.
    """
    delay: Duration = field(default_factory=lambda: Duration.from_minutes(1))

    @classmethod
    def from_dict(cls, data: dict) -> TimerConfig:
        """Create from dictionary (YAML parsing)."""
        delay = data.get("delay", "1m")
        if isinstance(delay, str):
            delay = Duration.from_string(delay)
        elif isinstance(delay, int):
            delay = Duration.from_seconds(delay)
        return cls(delay=delay)
```

### Domain: Duration Value Object

**Location**: `src/backend/services/process_engine/domain/value_objects.py:197-314`

```python
@dataclass(frozen=True)
class Duration:
    """
    Represents a time duration for timeouts, delays, etc.

    Supports parsing from human-readable strings:
    - "100ms" = 0.1 seconds
    - "30s" = 30 seconds
    - "5m" = 5 minutes
    - "2h" = 2 hours
    - "1d" = 1 day
    """
    seconds: float

    _PATTERN = re.compile(r"^(\d+)(ms|s|m|h|d)$")
    _UNITS = {
        "ms": 0.001,
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }

    @classmethod
    def from_string(cls, value: str) -> Duration:
        """Parse duration from string."""
        match = cls._PATTERN.match(value.strip().lower())
        if not match:
            raise ValueError(f"Invalid duration format '{value}'")
        amount = int(match.group(1))
        unit = match.group(2)
        multiplier = cls._UNITS[unit]
        return cls(seconds=amount * multiplier)
```

### Timer Step Handler

**Location**: `src/backend/services/process_engine/engine/handlers/timer.py:20-74`

```python
class TimerHandler(StepHandler):
    """
    Handler for timer step type.
    Pauses execution for a specified duration.

    Example YAML:
    ```yaml
    steps:
      - id: wait
        name: Wait 5 minutes
        type: timer
        delay: 5m
    ```
    """

    @property
    def step_type(self) -> StepType:
        return StepType.TIMER

    async def execute(
        self,
        context: StepContext,
        config: StepConfig,
    ) -> StepResult:
        """Execute a timer step - pauses for the configured delay duration."""
        if not isinstance(config, TimerConfig):
            return StepResult.fail(
                f"Invalid config type: {type(config).__name__}",
                error_code="INVALID_CONFIG",
            )

        delay_seconds = config.delay.seconds

        logger.info(
            f"Timer step starting: waiting {delay_seconds}s "
            f"(execution={context.execution.id}, step={context.step_definition.id})"
        )

        # Wait for the specified duration
        await asyncio.sleep(delay_seconds)

        logger.info(
            f"Timer step completed: waited {delay_seconds}s "
            f"(execution={context.execution.id}, step={context.step_definition.id})"
        )

        return StepResult.ok({
            "waited_seconds": delay_seconds,
            "delay_formatted": str(config.delay),
        })
```

### Schedule Registration on Publish

**Location**: `src/backend/routers/processes.py:734-827`

```python
def _register_process_schedules(definition: ProcessDefinition) -> int:
    """
    Register schedule triggers for a published process.
    Writes to the process_schedules table that the scheduler service reads.
    Returns the number of schedules registered.
    """
    # Filter for schedule triggers
    schedule_triggers = [
        t for t in definition.triggers
        if isinstance(t, ScheduleTriggerConfig)
    ]

    if not schedule_triggers:
        return 0

    db_path = _get_scheduler_db_path()
    count = 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS process_schedules (
            id TEXT PRIMARY KEY,
            process_id TEXT NOT NULL,
            process_name TEXT NOT NULL,
            trigger_id TEXT NOT NULL,
            cron_expression TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            timezone TEXT DEFAULT 'UTC',
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_run_at TEXT,
            next_run_at TEXT,
            UNIQUE(process_id, trigger_id)
        )
    """)

    now = datetime.utcnow().isoformat()

    for trigger in schedule_triggers:
        if not trigger.enabled:
            continue

        # Expand cron preset if needed
        cron_expr = expand_cron_preset(trigger.cron)

        # Calculate next run time
        try:
            tz = pytz.timezone(trigger.timezone) if trigger.timezone else pytz.UTC
            cron = croniter(cron_expr, datetime.now(tz))
            next_run = cron.get_next(datetime).isoformat()
        except Exception as e:
            logger.warning(f"Failed to calculate next run time: {e}")
            next_run = None

        schedule_id = secrets.token_urlsafe(16)

        cursor.execute("""
            INSERT OR REPLACE INTO process_schedules (
                id, process_id, process_name, trigger_id, cron_expression,
                enabled, timezone, description, created_at, updated_at, next_run_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule_id, str(definition.id), definition.name, trigger.id,
            cron_expr, 1, trigger.timezone, trigger.description, now, now, next_run
        ))
        count += 1

    conn.commit()
    conn.close()

    return count
```

### Schedule Unregistration on Archive

**Location**: `src/backend/routers/processes.py:829-858`

```python
def _unregister_process_schedules(process_id: ProcessId) -> int:
    """
    Unregister all schedule triggers for a process.
    Called when a process is archived.
    Returns the number of schedules removed.
    """
    db_path = _get_scheduler_db_path()
    count = 0

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM process_schedules WHERE process_id = ?",
            (str(process_id),)
        )
        count = cursor.rowcount

        conn.commit()
        conn.close()

        if count > 0:
            logger.info(f"Unregistered {count} schedule(s) for process {process_id}")

    except Exception as e:
        logger.error(f"Failed to unregister process schedules: {e}")

    return count
```

---

## API Endpoints

### Schedule Trigger Endpoints

**Location**: `src/backend/routers/triggers.py:267-404`

| Method | Path | Description | Line |
|--------|------|-------------|------|
| GET | `/api/triggers/schedules` | List all schedule triggers | 267 |
| GET | `/api/triggers/schedules/{schedule_id}` | Get specific schedule | 311 |
| GET | `/api/triggers/process/{process_id}/schedules` | List schedules for process | 360 |

#### List Schedule Triggers

```python
@router.get("/schedules", response_model=List[ScheduleTriggerInfo])
async def list_schedule_triggers():
    """List all schedule triggers across all processes."""
    repo = get_process_repo()
    triggers = []

    # Get schedule triggers from process definitions
    published_processes = repo.list_all(status=DefinitionStatus.PUBLISHED)

    # Get runtime info from database
    db_schedules = {
        f"{s['process_id']}:{s['trigger_id']}": s
        for s in _get_schedule_triggers_from_db()
    }

    for process in published_processes:
        for trigger in process.triggers:
            if isinstance(trigger, ScheduleTriggerConfig):
                key = f"{process.id}:{trigger.id}"
                db_info = db_schedules.get(key, {})

                triggers.append(ScheduleTriggerInfo(
                    id=db_info.get("id", trigger.id),
                    type="schedule",
                    process_name=process.name,
                    process_id=str(process.id),
                    trigger_id=trigger.id,
                    cron=trigger.cron,
                    cron_expression=trigger.cron_expression,
                    timezone=trigger.timezone,
                    enabled=trigger.enabled,
                    description=trigger.description,
                    next_run_at=db_info.get("next_run_at"),
                    last_run_at=db_info.get("last_run_at"),
                ))

    return triggers
```

### Response Model

```python
class ScheduleTriggerInfo(BaseModel):
    """Information about a schedule trigger."""
    id: str
    type: str = "schedule"
    process_name: str
    process_id: str
    trigger_id: str
    cron: str
    cron_expression: str
    timezone: str
    enabled: bool
    description: str
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
```

---

## Database Schema

### process_schedules Table

**Created in**: `src/backend/routers/processes.py:758-773`

```sql
CREATE TABLE IF NOT EXISTS process_schedules (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL,
    process_name TEXT NOT NULL,
    trigger_id TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    timezone TEXT DEFAULT 'UTC',
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_run_at TEXT,
    next_run_at TEXT,
    UNIQUE(process_id, trigger_id)
);
```

---

## YAML Configuration Examples

### Schedule Triggers

```yaml
name: daily-report
version: 1
description: Generate daily report at 9 AM

triggers:
  # Using a preset
  - id: morning-run
    type: schedule
    cron: daily              # Expands to "0 9 * * *"
    timezone: America/New_York
    enabled: true
    description: "Generate report at 9 AM EST"

  # Using explicit cron
  - id: evening-backup
    type: schedule
    cron: "0 18 * * 1-5"     # 6 PM weekdays
    timezone: UTC
    enabled: true

steps:
  - id: generate
    type: agent_task
    agent: report-agent
    message: Generate the daily report
```

### Timer Steps

```yaml
steps:
  - id: start-task
    type: agent_task
    agent: task-agent
    message: Start the background task

  - id: wait-5min
    type: timer
    delay: 5m                # Wait 5 minutes
    depends_on: [start-task]

  - id: check-result
    type: agent_task
    agent: check-agent
    message: Check if the background task completed
    depends_on: [wait-5min]
```

### Duration Formats

| Format | Example | Seconds |
|--------|---------|---------|
| Milliseconds | `100ms` | 0.1 |
| Seconds | `30s` | 30 |
| Minutes | `5m` | 300 |
| Hours | `2h` | 7200 |
| Days | `1d` | 86400 |

---

## Side Effects

### On Process Publish

- **Database**: INSERT into `process_schedules` for each enabled schedule trigger
- **Log**: `"Registered {count} schedule trigger(s) for '{process.name}'"`

### On Process Archive

- **Database**: DELETE from `process_schedules` WHERE process_id = X
- **Log**: `"Unregistered {count} schedule(s) for process {process_id}"`

### On Timer Step Execute

- **Log**: `"Timer step starting: waiting {delay}s (execution=X, step=Y)"`
- **Log**: `"Timer step completed: waited {delay}s (execution=X, step=Y)"`

---

## Error Handling

| Error | Cause | HTTP Status | Resolution |
|-------|-------|-------------|------------|
| Invalid cron expression | Malformed cron syntax | 422 | Use preset or valid 5-field cron |
| Unknown timezone | Invalid IANA timezone name | Warning | Falls back to UTC |
| Schedule not registering | Process not published | - | Publish the process first |
| Timer step timeout | Delay exceeds step timeout | 500 | Increase step timeout |
| Invalid duration format | Malformed delay string | 422 | Use format like "5m", "30s" |

---

## Timezone Support

### IANA Timezone Names

All timezone configuration uses standard IANA timezone names:

```yaml
triggers:
  - id: tokyo-morning
    type: schedule
    cron: "0 9 * * *"
    timezone: Asia/Tokyo

  - id: london-evening
    type: schedule
    cron: "0 18 * * *"
    timezone: Europe/London

  - id: utc-default
    type: schedule
    cron: hourly
    # timezone defaults to UTC if not specified
```

### Timezone Validation

The backend validates timezone names using pytz. Invalid timezones generate a warning and fall back to UTC.

---

## Flow Details

### 1. Schedule Registration Flow

```
Process Publish                    Backend                         Database
---------------                    -------                         --------
POST /api/processes/{id}/publish
                                   publish_process()
                                   └── definition.publish()
                                   └── repo.save(published)
                                   └── _register_process_schedules()
                                       ├── Filter ScheduleTriggerConfig
                                       ├── expand_cron_preset()
                                       ├── croniter.get_next()
                                       └── INSERT process_schedules ---------> process_schedules table
                                   └── publish_event(ProcessPublished)
```

### 2. Timer Step Execution Flow

```
ExecutionEngine                    TimerHandler
---------------                    ------------
_execute_step()
├── Get handler for TIMER type
└── handler.execute(context, config)
                                   execute()
                                   ├── config.delay.seconds
                                   ├── await asyncio.sleep(delay)
                                   └── return StepResult.ok({...})
_handle_step_success()
└── Continue to dependent steps
```

### 3. Frontend Schedule Display Flow

```
ProcessEditor.vue                  Backend API                     Database
-----------------                  -----------                     --------
loadProcess()
└── loadScheduleTriggerInfo()
    └── GET /api/triggers/process/{id}/schedules
                                   list_process_schedule_triggers()
                                   └── _get_schedule_triggers_from_db() ---> SELECT * FROM process_schedules
    └── scheduleTriggerInfo = {...}
Display in template:
  - next_run_at
  - last_run_at
  - cron expression
  - timezone
```

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- At least one process with schedule trigger or timer step

### Test Cases

| Test | Action | Expected Result |
|------|--------|-----------------|
| Schedule registration | Publish process with schedule trigger | Entry appears in process_schedules table with next_run_at |
| Cron preset expansion | Use preset like "daily" | Expands to "0 9 * * *" |
| Timezone calculation | Schedule at 9 AM Asia/Tokyo | next_run_at reflects correct UTC offset |
| Timer step execution | Run process with 10s timer step | Step waits 10s, outputs `{waited_seconds: 10}` |
| Archive removes schedules | Archive a published process | Schedule entries deleted from database |
| Invalid timezone | Use "Invalid/Timezone" | Warning logged, falls back to UTC |

---

## Related Flows

- [process-definition.md](./process-definition.md) - Trigger configuration in YAML schema
- [process-execution.md](./process-execution.md) - How scheduled executions run
- [../scheduler-service.md](../scheduler-service.md) - Agent-level scheduler (separate from process scheduling)

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-23 | Rebuilt with accurate line numbers and comprehensive code analysis |
| 2026-01-16 | Initial creation |
