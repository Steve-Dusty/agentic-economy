# Playbooks Tab (PLAYBOOK-001)

> **Status**: ✅ Implemented
> **Priority**: P1
> **Created**: 2026-02-27
> **Implemented**: 2026-02-27
> **Requirement ID**: PLAYBOOK-001
> **Flow**: `docs/memory/feature-flows/playbooks-tab.md`

---

## Overview

Replace the Skills tab in Agent Detail with a **Playbooks** tab that displays the agent's local skills collection and provides easy one-click or instruction-based invocation.

### What Are Playbooks?

In Trinity's approach, **playbooks** are business processes implemented as Claude Code skills. They are structured, reliable automation scripts that follow a transactional pattern:

```
READ FRESH STATE → PROCESS → WRITE STATE → VERIFY
```

Playbooks (skills) live in the agent's `.claude/skills/` directory and are self-contained, portable, traceable, and recoverable. See the [playbook-builder plugin](https://github.com/abilityai/abilities/tree/main/plugins/playbook-builder) for the full specification.

---

## User Story

As an agent operator, I want to see and invoke the agent's available skills directly from the UI so that I can trigger playbooks without needing to access the terminal or know slash command syntax.

---

## Requirements

### R1: Hide Skills Tab

**Description**: Hide the existing "Skills" tab from Agent Detail page.

**Changes**:
- Remove `{ id: 'skills', label: 'Skills' }` from `visibleTabs` computed property in `AgentDetail.vue`
- Keep `SkillsPanel.vue` component in codebase (for potential admin-only access later)

**Rationale**: The current Skills tab is for platform-level skill library management (assigning skills from a GitHub library). The new Playbooks tab is for invoking the agent's local skills.

---

### R2: Create Playbooks Tab

**Description**: Add a new "Playbooks" tab to Agent Detail page.

**Tab Position**: After "Schedules" tab (before Credentials)

**Tab Properties**:
- `id: 'playbooks'`
- `label: 'Playbooks'`
- Always visible (not conditional)

---

### R3: Agent Skills API Endpoint

**Description**: Create a new endpoint on the agent server to list available skills from the agent's `.claude/skills/` directory.

**Endpoint**: `GET /api/skills`

**Location**: `docker/base-image/agent_server/routers/skills.py` (new file)

**Response Model**:
```json
{
  "skills": [
    {
      "name": "commit",
      "description": "Commit, push, and link to GitHub Issues",
      "path": ".claude/skills/commit/SKILL.md",
      "user_invocable": true,
      "automation": null,
      "allowed_tools": ["Bash"],
      "argument_hint": "[message] [--issue #N]",
      "has_schedule": false
    },
    {
      "name": "security-analysis",
      "description": "Perform OWASP-based security analysis of the codebase",
      "path": ".claude/skills/security-analysis/SKILL.md",
      "user_invocable": true,
      "automation": "manual",
      "allowed_tools": ["Read", "Grep", "Write"],
      "argument_hint": null,
      "has_schedule": false
    }
  ],
  "count": 2,
  "skill_paths": [".claude/skills", "~/.claude/skills"]
}
```

**Implementation Details**:
1. Scan `.claude/skills/` directory for subdirectories containing `SKILL.md`
2. Parse YAML frontmatter from each `SKILL.md` to extract:
   - `name` (defaults to directory name)
   - `description`
   - `user-invocable` (boolean, default true)
   - `automation` (autonomous/gated/manual/null)
   - `allowed-tools` (array)
   - `argument-hint` (string)
3. Also scan `~/.claude/skills/` (personal skills)
4. Return sorted list by name

---

### R4: Backend Proxy Endpoint

**Description**: Create a backend proxy endpoint to fetch skills from agent container.

**Endpoint**: `GET /api/agents/{name}/playbooks`

**Location**: `src/backend/routers/agents.py` or new `src/backend/routers/playbooks.py`

**Access Control**: `AuthorizedAgentByName` (owner, shared, or admin)

**Response**: Proxy response from agent's `GET /api/skills`

**Error Handling**:
- 503 if agent not running
- 404 if agent not found

---

### R5: PlaybooksPanel Component

**Description**: Create a new Vue component for the Playbooks tab.

**File**: `src/frontend/src/components/PlaybooksPanel.vue`

**Props**:
```typescript
{
  agentName: string (required)
  agentStatus: string (default: 'stopped')
}
```

**Emits**:
```typescript
{
  'run-with-instructions': (skillName: string, prefillText: string) => void
}
```

**Features**:

#### 5.1 Skills List Display
- Grid layout (responsive: 1 col mobile, 2 cols tablet, 3 cols desktop)
- Each skill card shows:
  - **Name** (bold, monospace with `/` prefix: `/commit`)
  - **Description** (gray text, 2-line clamp)
  - **Automation badge** (if present: "autonomous" amber, "gated" purple, "manual" blue)
  - **Action buttons** (see R6)

#### 5.2 Search/Filter
- Search input to filter skills by name or description
- Toggle to show/hide non-user-invocable skills (default: hidden)

#### 5.3 Empty State
- When agent stopped: "Start agent to view playbooks"
- When no skills: "No playbooks found. Skills are loaded from .claude/skills/"

#### 5.4 Loading State
- Spinner while fetching skills
- Auto-refresh when agent status changes to "running"

---

### R6: Skill Invocation Actions

**Description**: Two ways to invoke a skill from the Playbooks tab.

#### 6.1 One-Click Run (Play Button)

**UI**: Green play button icon on skill card

**Behavior**:
1. Click opens confirmation modal (optional, can be skipped via user preference)
2. Sends POST request to `/api/agents/{name}/task` with message `/{skill-name}`
3. Navigates to Tasks tab with the execution highlighted (via `?execution={id}` query param)

**Disabled When**:
- Agent not running
- `user_invocable: false`

#### 6.2 Run with Instructions (Edit Button)

**UI**: Pencil/edit icon button on skill card

**Behavior**:
1. Click emits `run-with-instructions` event with `/{skill-name} `
2. Parent (`AgentDetail.vue`) handles by:
   - Setting `taskPrefillMessage` to `/{skill-name} `
   - Switching to Tasks tab (`activeTab = 'tasks'`)
3. User can add arguments/instructions after the skill name
4. User presses Enter or clicks Run

**Always Available** (even when agent stopped - user can prepare the message)

---

### R7: AgentDetail Integration

**Description**: Wire up the PlaybooksPanel in AgentDetail.vue.

**Changes**:

1. Import `PlaybooksPanel` component
2. Add tab definition:
   ```javascript
   { id: 'playbooks', label: 'Playbooks' }
   ```
3. Position after 'schedules', before 'credentials'
4. Add tab content:
   ```vue
   <div v-if="activeTab === 'playbooks'" class="p-6">
     <PlaybooksPanel
       :agent-name="agent.name"
       :agent-status="agent.status"
       @run-with-instructions="handleRunWithInstructions"
     />
   </div>
   ```
5. Add handler:
   ```javascript
   function handleRunWithInstructions(prefillText) {
     taskPrefillMessage.value = prefillText
     activeTab.value = 'tasks'
   }
   ```
6. Remove 'skills' from visibleTabs

---

### R8: TasksPanel Initial Message Support

**Description**: Ensure TasksPanel properly handles the `initialMessage` prop for prefilling.

**Current State**: `TasksPanel.vue` already has `initialMessage` prop at line 77.

**Verification**:
- Ensure `newTaskMessage` is set from `initialMessage` on mount
- Ensure textarea receives focus when `initialMessage` is set

---

## Non-Requirements (Out of Scope)

1. **Skill editing** - Skills are edited via terminal/IDE
2. **Skill creation** - Use `/create-playbook` skill in terminal
3. **Schedule creation from skills** - Use "Make Repeatable" in Tasks tab
4. **Platform skill library** - Keep existing SkillsPanel for admin use (just hidden)
5. **Skill content preview** - Full SKILL.md viewing not in V1

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Playbooks Tab Flow                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────┐     GET /api/agents/{name}/playbooks                   │
│  │ PlaybooksPanel│ ─────────────────────────────────────►  ┌───────────┐ │
│  │   (Vue)      │                                           │  Backend  │ │
│  └──────┬───────┘ ◄─────────────────────────────────────── │  FastAPI  │ │
│         │                   skills list                     └─────┬─────┘ │
│         │                                                         │       │
│         │  Click "Run"                                            │       │
│         ▼                                                         ▼       │
│  POST /api/agents/{name}/task                              GET /api/skills│
│    { message: "/skill-name" }                                     │       │
│         │                                                         │       │
│         │  execution_id                                   ┌───────┴──────┐│
│         │                                                 │ Agent Server ││
│         ▼                                                 │   (Python)   ││
│  Navigate to Tasks tab                                    └──────────────┘│
│  ?execution={id}                                                          │
│                                                                           │
│         │  Click "Run with Instructions"                                  │
│         ▼                                                                 │
│  Emit 'run-with-instructions'                                            │
│    { prefillText: "/skill-name " }                                       │
│         │                                                                 │
│         ▼                                                                 │
│  Switch to Tasks tab                                                     │
│  Prefill textarea                                                        │
│  User adds instructions, clicks Run                                      │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Files to Create

| File | Description |
|------|-------------|
| `docker/base-image/agent_server/routers/skills.py` | Agent-side skills listing endpoint |
| `src/frontend/src/components/PlaybooksPanel.vue` | Main Playbooks tab component |
| `docs/memory/feature-flows/playbooks-tab.md` | Feature flow documentation |

## Files to Modify

| File | Changes |
|------|---------|
| `docker/base-image/agent_server/routers/__init__.py` | Import and mount skills router |
| `src/backend/routers/agents.py` | Add `/api/agents/{name}/playbooks` proxy endpoint |
| `src/frontend/src/views/AgentDetail.vue` | Add Playbooks tab, remove Skills tab, wire up events |

---

## UI Mockup

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Playbooks                                                              │
│  Invoke agent skills directly. Skills are loaded from .claude/skills/  │
├─────────────────────────────────────────────────────────────────────────┤
│  [🔍 Search playbooks...]                                              │
│                                                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐ │
│  │ /commit             │  │ /security-analysis  │  │ /read-docs      │ │
│  │                     │  │                     │  │                 │ │
│  │ Commit, push, and   │  │ Perform OWASP-based │  │ Load all project│ │
│  │ link to GitHub...   │  │ security analysis   │  │ documentation   │ │
│  │                     │  │                     │  │ into context... │ │
│  │ [▶️ Run] [✏️ Edit]  │  │ [▶️ Run] [✏️ Edit]  │  │ [▶️ Run] [✏️]   │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────┘ │
│                                                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐                      │
│  │ /update-docs        │  │ /validate-pr        │                      │
│  │                     │  │ [autonomous]        │                      │
│  │ Update project docs │  │ Validate a pull     │                      │
│  │ after making...     │  │ request against...  │                      │
│  │                     │  │                     │                      │
│  │ [▶️ Run] [✏️ Edit]  │  │ [▶️ Run] [✏️ Edit]  │                      │
│  └─────────────────────┘  └─────────────────────┘                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Testing

### Prerequisites
- Trinity platform running
- Agent created and running
- Agent has skills in `.claude/skills/` directory

### Test Cases

#### TC1: View Playbooks List
1. Navigate to Agent Detail
2. Click "Playbooks" tab
3. **Expected**: Skills grid loads with all user-invocable skills

#### TC2: One-Click Run
1. Click ▶️ (Run) on any skill
2. **Expected**:
   - POST to `/api/agents/{name}/task` with `/{skill-name}`
   - Navigate to Tasks tab
   - Execution appears in list

#### TC3: Run with Instructions
1. Click ✏️ (Edit) on any skill
2. **Expected**:
   - Switches to Tasks tab
   - Textarea prefilled with `/{skill-name} `
   - Cursor at end of text
3. Add instructions: `fix the login bug`
4. Press Enter
5. **Expected**: Task runs with `/{skill-name} fix the login bug`

#### TC4: Agent Not Running
1. Stop agent
2. View Playbooks tab
3. **Expected**: "Start agent to view playbooks" message
4. Run button disabled

#### TC5: Search
1. Type "commit" in search
2. **Expected**: Only skills matching "commit" shown

### Edge Cases
- Agent with no skills (empty .claude/skills/)
- Skills with missing frontmatter (graceful fallback)
- Very long descriptions (truncation)
- Many skills (scrolling)

---

## Security Considerations

1. **Access Control**: `/api/agents/{name}/playbooks` uses same auth as other agent endpoints
2. **Skill Invocation**: Uses existing `/task` endpoint with standard access control
3. **No Arbitrary Code**: Skills are pre-defined; users can only invoke existing skills

---

## Implementation Phases

### Phase 1: Agent Skills Endpoint
- Create `docker/base-image/agent_server/routers/skills.py`
- Parse `.claude/skills/` directory
- Extract YAML frontmatter
- Test endpoint locally

### Phase 2: Backend Proxy
- Add `/api/agents/{name}/playbooks` endpoint
- Proxy to agent container
- Handle error cases

### Phase 3: PlaybooksPanel Component
- Create component with skills grid
- Implement search/filter
- Add loading/empty states

### Phase 4: Integration & Polish
- Wire up AgentDetail.vue
- Test one-click run
- Test run with instructions
- Hide Skills tab

---

## Related Documents

- [playbook-builder plugin](https://github.com/abilityai/abilities/tree/main/plugins/playbook-builder) - Playbook specification
- [Claude Code Skills Documentation](https://docs.anthropic.com/en/docs/claude-code/skills) - Official skills spec
- [tasks-tab.md](../memory/feature-flows/tasks-tab.md) - Task execution flow
- [parallel-headless-execution.md](../memory/feature-flows/parallel-headless-execution.md) - `/task` endpoint

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-27 | 1.0 | Initial requirements document |
