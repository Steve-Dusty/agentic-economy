# Model Selection for Tasks & Schedules (MODEL-001)

> **Status**: Ready for Implementation
> **Priority**: P1
> **GitHub Issue**: TBD

## Problem

Tasks and schedules always execute with the agent's default model. Users have no way to specify which model a task or schedule should use from the UI. The backend pipe supports model passthrough (`ParallelTaskRequest.model`), but neither the frontend nor the scheduler reads or sends it.

## Goal

Allow users to select a model when running a task or creating/editing a schedule. Default to `claude-opus-4-5`. Support custom model names for advanced users.

## Model List

Preset options (4.5 and 4.6 families only):

| Display Name | Value | Notes |
|-------------|-------|-------|
| Claude Opus 4.5 | `claude-opus-4-5` | **Default** |
| Claude Opus 4.6 | `claude-opus-4-6` | Latest, most capable |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Fast + smart |
| Claude Sonnet 4.5 | `claude-sonnet-4-5` | Previous gen, fast |
| Claude Haiku 4.5 | `claude-haiku-4-5` | Fastest, cheapest |

Users can also type a custom model name (free text input).

## Scope

### In Scope

1. Model selector in TasksPanel task input
2. Model field in SchedulesPanel create/edit form
3. `model` column in `agent_schedules` table
4. Scheduler passes model through to agent on execution
5. `model` field on backend schedule CRUD models
6. `model_used` column in `schedule_executions` for audit

### Out of Scope

- Changing the Terminal/Chat model selector (already implemented, see CFG-005/CFG-006)
- Gemini model list (only Claude models in presets; custom input handles anything)
- Per-user model restrictions or quotas
- Model cost estimation in UI

## What Already Works

| Component | Status |
|-----------|--------|
| Agent `/api/task` endpoint accepts `model` | Done |
| `ParallelTaskRequest` has `model` field | Done |
| Backend `/api/agents/{name}/task` forwards `model` | Done |
| MCP `chat_with_agent` passes `model` (parallel mode) | Done |
| Claude Code CLI `--model` flag | Done |

## Changes Required

### 1. Database Migration

Add column to `agent_schedules`:

```sql
ALTER TABLE agent_schedules ADD COLUMN model TEXT DEFAULT NULL;
```

Add column to `schedule_executions`:

```sql
ALTER TABLE schedule_executions ADD COLUMN model_used TEXT DEFAULT NULL;
```

NULL means "use agent default".

### 2. Backend Models (`src/backend/models.py`)

Add `model: Optional[str] = None` to:
- `ScheduleCreate`
- `ScheduleUpdate`
- `ScheduleResponse`

Add `model_used: Optional[str] = None` to:
- `ExecutionResponse` / `ExecutionSummary`

### 3. Schedule Database Operations (`src/backend/db/schedules.py`)

- Include `model` in INSERT/UPDATE queries for schedules
- Include `model` in SELECT queries for schedule retrieval
- Write `model_used` when creating execution records

### 4. Scheduler Service

**`src/scheduler/service.py`** — In `_execute_schedule_with_lock()`:
- Read `schedule.model`
- Pass to `client.task(model=schedule.model)`
- Record `model_used` in execution record

**`src/scheduler/agent_client.py`** — In `task()`:
- Add `model: Optional[str] = None` parameter
- Include in payload: `if model: payload["model"] = model`

### 5. Frontend — TasksPanel.vue

Add model selector above the task input area:
- Combobox: dropdown with preset list + editable text for custom values
- Default selection: `claude-opus-4-5`
- Include selected model in POST body: `{ message, model }`
- Persist last-used model in localStorage key `trinity-task-model-{agentName}`

### 6. Frontend — SchedulesPanel.vue

Add model field to schedule create/edit form:
- Same combobox component as TasksPanel
- Default: `claude-opus-4-5`
- Stored in `formData.model`
- Displayed in schedule list (small badge or text)

### 7. Frontend — Model Selector Component

Extract shared `ModelSelector.vue` component:
- Props: `modelValue` (v-model), `default` (default value)
- Preset list as defined in Model List above
- Editable combobox pattern: select from list OR type custom
- Compact size variant for inline use

### 8. Execution Display

Show `model_used` on:
- TasksPanel execution history rows (small label)
- ExecutionDetail page metadata section
- ExecutionList page (optional column)

## UI Mockup

### TasksPanel

```
┌─────────────────────────────────────────────┐
│ Model: [claude-opus-4-5        ▾]           │
│ ┌─────────────────────────────────────────┐ │
│ │ Enter task message...                   │ │
│ └─────────────────────────────────────────┘ │
│                                   [Run Task]│
└─────────────────────────────────────────────┘
```

### SchedulesPanel Form

```
Name:        [___________________________]
Cron:        [___________________________]
Message:     [___________________________]
Model:       [claude-opus-4-5        ▾]
Timezone:    [UTC                    ▾]
Timeout:     [900                      ]
```

## Testing

### Prerequisites
- Backend and frontend running
- Agent running
- User logged in with agent access

### Test Steps

1. **Task with default model**
   - Action: Open Tasks tab, enter message, click Run Task
   - Expected: Task executes with `claude-opus-4-5`
   - Verify: Execution record shows `model_used: claude-opus-4-5`

2. **Task with changed model**
   - Action: Select `claude-opus-4-6` from dropdown, run task
   - Expected: Task executes with `claude-opus-4-6`
   - Verify: Execution record shows `model_used: claude-opus-4-6`

3. **Task with custom model**
   - Action: Type `claude-sonnet-4-5-20250929` in model field, run task
   - Expected: Task executes with the exact model string
   - Verify: Execution record shows typed value

4. **Schedule with model**
   - Action: Create schedule with model set to `claude-opus-4-6`
   - Expected: Schedule saved with model field
   - Verify: GET schedule returns `model: claude-opus-4-6`

5. **Schedule execution uses model**
   - Action: Trigger schedule manually
   - Expected: Execution uses `claude-opus-4-6`
   - Verify: Execution record shows `model_used: claude-opus-4-6`

6. **Schedule with NULL model**
   - Action: Create schedule without selecting model (or clear it)
   - Expected: Execution uses agent default
   - Verify: `model_used` records the effective model used

7. **Model persistence in TasksPanel**
   - Action: Select model, reload page
   - Expected: Previously selected model restored from localStorage
