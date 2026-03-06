# Process-Driven Thinking - Iteration 4

> **Status**: UI/UX Design Philosophy & Specifications
> **Date**: 2026-01-14
> **Previous**: `PROCESS_DRIVEN_THINKING_IT3.md`
> **Purpose**: Define UI/UX approach for the Trinity Process Engine

---

## Executive Summary

This iteration defines the **UI/UX philosophy and specifications** for Trinity's Process Engine. Just as we chose BPMN for process modeling patterns and DDD for architectural structure, we need principled approaches for the user interface.

**Core Philosophy**:
- **Activity-Centered Design** — Organize by user jobs, not data objects
- **OODA Loop** — Observe → Orient → Decide → Act for operational UIs
- **Progressive Disclosure** — Reveal complexity on demand
- **Calm Technology** — Quiet when healthy, loud when broken

**Key Decisions**:
- Process Definition: YAML editor + live visual preview
- Timeline View: Balanced sophistication with horizontal bars
- Approvals: Dedicated inbox + inline in execution view
- Real-Time: WebSocket for active views, polling for lists

---

## 1. UI/UX Philosophy

### 1.1 Activity-Centered Design

**Principle**: Organize interface around user activities, not data objects.

| Traditional (Object-Centered) | Activity-Centered |
|------------------------------|-------------------|
| Processes \| Executions \| Agents \| Approvals | Design \| Monitor \| Approve \| Analyze |

**Application**: Navigation and page structure should reflect what users are trying to accomplish.

### 1.2 OODA Loop for Operational UIs

**Principle**: Structure monitoring interfaces for rapid decision-making.

```
Observe  →  Orient       →  Decide     →  Act
See state   Understand why   Choose fix   Execute
```

| Phase | UI Element |
|-------|------------|
| **Observe** | Status icons, progress bars, metrics |
| **Orient** | Error details, context, history |
| **Decide** | Options presented (retry, skip, escalate) |
| **Act** | One-click actions with confirmation |

### 1.3 Progressive Disclosure

**Principle**: Show only what's needed at each level.

```
Level 1: Overview       →    Level 2: Details       →    Level 3: Deep Dive
"3 processes running"        "Step 4/7, Analyze"         "Agent activity log"
```

### 1.4 Calm Technology

**Principle**: Minimize attention when things are fine, demand it when needed.

| State | UI Behavior |
|-------|-------------|
| **Healthy** | Calm, minimal visual noise, green/neutral colors |
| **Warning** | Yellow accents, subtle badges |
| **Problem** | Red highlights, notifications, action prompts |

### 1.5 Jobs to Be Done

| User Role | Primary Job |
|-----------|-------------|
| **Process Designer** | "Help me define a reliable workflow without errors" |
| **Operator** | "Show me what's happening and let me fix problems fast" |
| **Approver** | "Let me make decisions quickly with enough context" |
| **Manager** | "Tell me if my processes are healthy and cost-effective" |

---

## 2. Design System Approach

### 2.1 Foundation

**Technology**: Continue with Tailwind CSS (existing Trinity foundation)

**Pattern Inspiration**:
- **Atlassian Design System** — Workflow/collaboration patterns (Jira, Trello)
- **IBM Carbon** — Enterprise data-heavy applications
- **BPMN Visual Conventions** — Process element representation

### 2.2 Visual Language for Process State

#### Process Elements (BPMN-inspired)

| Element | Visual | Meaning |
|---------|--------|---------|
| **Start** | ⬤ (circle) | Process entry point |
| **End** | ⬛ (bold circle) | Process completion |
| **Task** | ▭ (rounded rect) | Executable step |
| **Gateway** | ◇ (diamond) | Decision point |
| **Flow** | → (arrow) | Sequence |
| **Parallel** | ═══ (double line) | Concurrent paths |

#### Status Indicators

| Status | Icon | Color | Meaning |
|--------|------|-------|---------|
| **Completed** | ✅ | Green | Successfully finished |
| **Running** | 🔄 | Blue | Currently executing |
| **Waiting** | ⏳ | Gray | Pending dependencies |
| **Paused** | ⏸️ | Yellow | Waiting (approval, etc.) |
| **Failed** | ❌ | Red | Error occurred |
| **Skipped** | ⏭️ | Gray strikethrough | Condition not met |

### 2.3 Key UI Patterns

| Pattern | Source | Application |
|---------|--------|-------------|
| **Wizard** | Common | Step-by-step process creation |
| **Code Editor + Preview** | GitHub/GitLab | YAML editing |
| **Timeline/Status Rail** | CI/CD pipelines | Execution progress |
| **Inbox** | Email | Approval queue |
| **Expandable Rows** | Data tables | Detail on demand |
| **KPI Cards** | Dashboards | Key metrics |
| **Lozenges/Badges** | Atlassian | Status indicators |

---

## 3. Process Definition UI

### 3.1 Decision: YAML + Live Preview

**Rationale**:
- Developer-friendly
- Version-controllable
- Full power of the schema
- Visual feedback without building full designer

### 3.2 Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Edit Process: Weekly Market Report                   [Save] [Test] │
├─────────────────────────┬───────────────────────────────────────────┤
│  YAML Editor (60%)      │  Live Preview (40%)                       │
│  ─────────────────────  │  ─────────────────────────────────────── │
│                         │                                           │
│  name: weekly-report    │   ┌──────────┐                           │
│  version: 1             │   │ Research │                           │
│                         │   └────┬─────┘                           │
│  steps:                 │        │                                  │
│    - id: research       │        ▼                                  │
│      type: agent_task   │   ┌──────────┐                           │
│      agent: researcher  │   │ Analyze  │                           │
│      message: "..."     │   └────┬─────┘                           │
│                         │        │                                  │
│    - id: analyze        │        ▼                                  │
│      depends_on:        │      ◇ Gateway                           │
│        - research       │      ╱ ╲                                  │
│                         │     ▼   ▼                                 │
│  ────────────────────── │  [Write] [Deep]                          │
│  ⚠️ Line 12: Unknown    │        ╲ ╱                                │
│     agent "analystx"    │         ▼                                 │
│                         │   ┌──────────┐                           │
│                         │   │ Review   │ ← Human Approval          │
│                         │   └──────────┘                           │
└─────────────────────────┴───────────────────────────────────────────┘
```

### 3.3 Editor Features

| Feature | Priority | Description |
|---------|----------|-------------|
| **Syntax highlighting** | MVP | YAML color coding |
| **Inline validation** | MVP | Errors shown as you type |
| **Live preview** | MVP | Flow diagram updates on edit |
| **Auto-complete** | Phase 2 | Agent names, step IDs, types |
| **Step templates** | Phase 2 | Insert common patterns |
| **Import/Export** | MVP | Download YAML, upload existing |

### 3.4 Validation Feedback

```
┌─────────────────────────────────────────────────────────────────────┐
│  Validation                                                         │
├─────────────────────────────────────────────────────────────────────┤
│  ❌ Line 12: Unknown agent "analystx" - did you mean "analyst"?     │
│  ⚠️ Line 24: Step "publish" has no error handler defined            │
│  ✅ 7 steps validated                                               │
│  ✅ No circular dependencies                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Execution Timeline UI

### 4.1 Design: Balanced Sophistication

Not too simple (just a list), not too complex (full Gantt). A horizontal bar view with:
- Relative duration visualization
- Status icons for quick scanning
- Brief output summaries (expandable)
- Cost tracking per step
- Parallel execution indication

### 4.2 Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Execution #47                                    Running (4/7)     │
│  Started: 3m 24s ago | Cost: $2.65 | ETA: ~12 min                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Timeline                                              Total: 3m 24s│
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  ✅ Research       ████████░░░░░░░░░░░░░░░░░░░░░░░  12s    $0.32   │
│     researcher     └─ "Found 23 competitor articles"                │
│                                                                     │
│  ✅ Research-B     ████░░░░░░░░░░░░░░░░░░░░░░░░░░░   8s    $0.18   │
│     researcher     └─ "Analyzed social sentiment"                   │
│                                                       ↓ parallel    │
│  ✅ Analyze        ░░░░████████████░░░░░░░░░░░░░░░  45s    $0.95   │
│     analyst        └─ "Identified 5 key trends"                     │
│                                                                     │
│  ◇  Gateway        ░░░░░░░░░░░░░░░█░░░░░░░░░░░░░░░  <1s     —      │
│     Took: "high-quality" path (score: 85)                          │
│                                                                     │
│  🔄 Write          ░░░░░░░░░░░░░░░░████████▒▒▒▒▒▒▒  1m 12s  $1.20  │
│     writer         └─ Drafting section 3/5...          [View Live] │
│                                                                     │
│  ⏳ Review         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  —       —      │
│     (waiting for: Write)                                            │
│                                                                     │
│  ⏳ Publish        ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  —       —      │
│     (waiting for: Review)                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Timeline Features

| Feature | Priority | Description |
|---------|----------|-------------|
| **Status icons** | MVP | ✅ ❌ 🔄 ⏳ ⏸️ for quick scanning |
| **Duration bars** | MVP | Horizontal bars showing relative time |
| **Cost per step** | MVP | Right-aligned cost column |
| **Output summary** | MVP | Brief text, truncated |
| **Expand/collapse** | MVP | Click row to see full details |
| **Parallel indication** | MVP | Visual marker for concurrent steps |
| **Gateway decisions** | MVP | Show which path and why |
| **Live activity link** | MVP | "View Live" for running steps |
| **Agent activity stream** | Phase 2 | Inline expandable activity log |

### 4.4 Expanded Step View

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔄 Write                                                           │
│  ───────────────────────────────────────────────────────────────── │
│                                                                     │
│  Agent: writer                                                      │
│  Started: 1m 12s ago                                                │
│  Cost so far: $1.20                                                 │
│  Context: 45K / 200K tokens                                         │
│                                                                     │
│  Input:                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ analysis_path: /shared/market-analysis/analysis/            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Activity:                                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 10:32:15  Read: analysis.json                               │   │
│  │ 10:32:18  Write: sections/intro.md                          │   │
│  │ 10:32:45  Read: competitor_data.json                        │   │
│  │ 10:33:02  Write: sections/competitors.md                    │   │
│  │ 10:33:25  Thinking...                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [View Full Logs]  [Stop Step]                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Approval UI

### 5.1 Decision: Dual Placement

Approvals appear in **two places**:
1. **Dedicated Inbox** — For approvers managing multiple pending items
2. **Inline in Execution** — For contextual approval while viewing a process

### 5.2 Approval Inbox

```
┌─────────────────────────────────────────────────────────────────────┐
│  📥 My Approvals                                              (3)   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Filter: [All ▾]  [Process ▾]  [Due Date ▾]                        │
│                                                                     │
│  ┌─ ⚠️ Urgent ──────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  Contract Review Required                       Due in 2h     │  │
│  │  Process: Customer Onboarding #892                            │  │
│  │  Step: Legal Compliance                                       │  │
│  │  Requested: 46h ago by sales-ops agent                        │  │
│  │                                                               │  │
│  │  📄 contract_draft.pdf                          [Preview]     │  │
│  │                                                               │  │
│  │  [✅ Approve] [↩️ Request Changes] [❌ Reject] [→ Delegate]   │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─ Normal ─────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  Report Review                                  Due in 23h    │  │
│  │  Process: Weekly Market Report #47                            │  │
│  │  Step: Final Review                                           │  │
│  │                                                               │  │
│  │  📄 report_draft.pdf                            [Preview]     │  │
│  │                                                               │  │
│  │  [✅ Approve] [↩️ Request Changes] [❌ Reject] [→ Delegate]   │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─ Normal ─────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  Budget Sign-off                                Due in 47h    │  │
│  │  Process: Marketing Campaign #156                             │  │
│  │  Amount: $15,000                                              │  │
│  │                                                               │  │
│  │  [✅ Approve] [↩️ Request Changes] [❌ Reject] [→ Delegate]   │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 Inline Approval (in Execution View)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ...                                                                │
│  ✅ Write          ...                                              │
│                                                                     │
│  ⏸️ Review         ─────────────────────────────────────────────── │
│  │                                                                  │
│  │  ┌─────────────────────────────────────────────────────────┐   │
│  │  │ 🔔 Waiting for your approval                            │   │
│  │  │                                                         │   │
│  │  │ Approvers: you, sarah@company.com                       │   │
│  │  │ Due: Tomorrow 10:00 AM (23h remaining)                  │   │
│  │  │                                                         │   │
│  │  │ Artifacts:                                              │   │
│  │  │ 📄 report_draft.pdf                       [Preview]     │   │
│  │  │                                                         │   │
│  │  │ Comment (required for reject):                          │   │
│  │  │ ┌─────────────────────────────────────────────────┐    │   │
│  │  │ │                                                 │    │   │
│  │  │ └─────────────────────────────────────────────────┘    │   │
│  │  │                                                         │   │
│  │  │ [✅ Approve] [↩️ Request Changes] [❌ Reject]           │   │
│  │  └─────────────────────────────────────────────────────────┘   │
│  │                                                                  │
│                                                                     │
│  ⏳ Publish        (waiting for: Review)                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.4 Approval Features

| Feature | Priority | Description |
|---------|----------|-------------|
| **Approval list** | MVP | Cards with key info and actions |
| **Quick actions** | MVP | Approve/Reject without opening detail |
| **Artifact preview** | MVP | View files without download |
| **Required comments** | MVP | For reject/changes |
| **Deadline visibility** | MVP | Due time, urgency indicator |
| **Inline in execution** | MVP | Approve while viewing process |
| **Delegation** | Phase 2 | Reassign to another approver |
| **Batch approval** | Phase 2 | Select multiple, approve all |
| **Email quick actions** | Phase 2 | Approve directly from email |

---

## 6. Real-Time Updates

### 6.1 Strategy: Balanced Approach

| Data Type | Update Method | Frequency | Rationale |
|-----------|---------------|-----------|-----------|
| **Process list** | Polling | 30s | Many items, low urgency |
| **Active execution** | WebSocket | Real-time | Users are watching |
| **Step activity** | WebSocket | When expanded | Only when focused |
| **Approval inbox** | Polling + Push | 60s + on new | Balance freshness vs load |
| **Dashboard metrics** | Polling | 60s | Aggregate data |

### 6.2 WebSocket Events

```typescript
// Events sent via WebSocket
interface ProcessEvents {
  // Execution state changes
  "execution:started": { executionId, processName }
  "execution:completed": { executionId, duration, cost }
  "execution:failed": { executionId, stepId, error }
  
  // Step state changes
  "step:started": { executionId, stepId, stepName }
  "step:completed": { executionId, stepId, output, cost, duration }
  "step:failed": { executionId, stepId, error }
  
  // Live activity (when subscribed)
  "step:activity": { executionId, stepId, activity }
  
  // Approval events
  "approval:requested": { executionId, stepId, approvers, deadline }
  "approval:decided": { executionId, stepId, decision, decidedBy }
}
```

### 6.3 Visual Indicators

```
┌─────────────────────────────────────────────────────────────────────┐
│  Execution #47                               🔴 Live    [⟳ Refresh] │
└─────────────────────────────────────────────────────────────────────┘

🔴 Live    = WebSocket connected, real-time updates active
⚪ Auto    = Auto-refreshing every Xs (polling)
⟳ Refresh = Manual refresh button always available
```

### 6.4 Notification Strategy

| Event | Notification |
|-------|-------------|
| **New approval assigned** | Badge update + optional toast |
| **Execution failed** | Toast notification |
| **Approval deadline < 4h** | Highlighted in inbox |
| **Approval deadline < 1h** | Push notification (if enabled) |
| **Process completed** | Silent (unless explicitly watched) |

---

## 7. Dashboard UI

### 7.1 Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Processes                                        [+ Create Process]│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ Quick Stats ────────────────────────────────────────────────┐  │
│  │  Active: 3  │  Pending Approval: 2  │  Failed (24h): 1       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Active Executions                                                  │
│  ───────────────────                                                │
│  🔄 Weekly Market Report #47        Step 4/7    $1.24    2m ago     │
│  🔄 Customer Onboarding #892        Step 2/5    $0.45    5m ago     │
│  ⏸️ Content Pipeline #34            Approval    $2.10    Waiting    │
│                                                                     │
│  Process Health                                                     │
│  ──────────────                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Weekly Report    │  │ Onboarding       │  │ Content Pipeline │ │
│  │ ✅ 94% success   │  │ ✅ 100% success  │  │ ⚠️ 78% success   │ │
│  │ Avg: 45m, $3.20  │  │ Avg: 12m, $1.10  │  │ Avg: 2h, $8.50   │ │
│  │ Next: Mon 8am    │  │ Event-triggered  │  │ Daily 6am        │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                     │
│  Needs Attention                                                    │
│  ─────────────────                                                  │
│  ❌ Content Pipeline #33    Failed: Image Gen    2h ago    [Debug] │
│  ⏰ Report Review           Approval due in 2h            [Review] │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Dashboard Metrics

| Metric | Purpose | Display |
|--------|---------|---------|
| **Active Executions** | Current workload | Count + list |
| **Pending Approvals** | Human bottlenecks | Count + badge |
| **Success Rate** | Overall health | Percentage per process |
| **Avg Duration** | Performance baseline | Time display |
| **Avg Cost** | Budget tracking | Currency display |
| **Recent Failures** | Needs attention | List with actions |

---

## 8. Error Handling & Debugging UI

### 8.1 Failed Execution View

```
┌─────────────────────────────────────────────────────────────────────┐
│  Execution #33: Content Pipeline                     ❌ FAILED      │
│  Started: 2h ago | Failed at: Image Generation | Cost: $5.20       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Execution Timeline                                                 │
│  ──────────────────                                                 │
│  ✅ 06:00:00  Research Topics         12s    $0.45                 │
│  ✅ 06:00:12  Write Draft             89s    $1.80                 │
│  ✅ 06:01:41  Edit Draft              45s    $0.95                 │
│                                                                     │
│  ❌ 06:02:26  Generate Images         FAILED (after 3 attempts)    │
│      │                                                              │
│      └─► Error Details:                                             │
│          ┌──────────────────────────────────────────────────────┐  │
│          │ Agent: image-creator                                  │  │
│          │ Error Code: API_RATE_LIMIT                            │  │
│          │ Message: API rate limit exceeded (429)                │  │
│          │                                                       │  │
│          │ Attempts: 3/3 (with exponential backoff)              │  │
│          │                                                       │  │
│          │ Last agent output:                                    │  │
│          │ "Attempted to generate 5 images but received 429     │  │
│          │  Too Many Requests from the API..."                   │  │
│          │                                                       │  │
│          │ [View Full Logs]                                      │  │
│          └──────────────────────────────────────────────────────┘  │
│                                                                     │
│  ⏭️ 06:02:26  Publish                 SKIPPED (upstream failed)    │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Actions:                                                           │
│  [🔄 Retry Failed Step]  [🔄 Retry Entire Process]  [🗑️ Dismiss]   │
│                                                                     │
│  💡 Suggestion: The image API has rate limits. Consider adding a   │
│     delay between image requests or reducing batch size.            │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.2 Error UX Principles

| Principle | Implementation |
|-----------|----------------|
| **Never show error without action** | Always provide retry/dismiss options |
| **Show context** | Error message + agent output + attempts |
| **Suggest fixes** | AI-powered suggestions when possible |
| **Clear next steps** | Retry step vs retry process vs dismiss |
| **Preserve state** | Easy to resume from failure point |

---

## 9. Edge Cases & UX Solutions

| Edge Case | UX Solution |
|-----------|-------------|
| **Very long process (50+ steps)** | Collapsible sections, search/filter, "jump to" |
| **Deep parallel branching** | Horizontal scroll or branch selector dropdown |
| **Multiple pending approvals** | Batch approval UI, select multiple |
| **Process definition error** | Inline validation, prevent save until fixed |
| **Agent unavailable** | Clear error + "Start Agent" action |
| **Approval timeout imminent** | Escalating visual urgency (yellow → orange → red) |
| **Process stuck (potential infinite loop)** | "Running for 2h+" warning, manual stop button |
| **Large output data** | Truncate with "View full" link, lazy loading |
| **Concurrent editors** | Optimistic locking, "Someone else is editing" warning |

---

## 10. Navigation Structure

### 10.1 Primary Navigation

```
┌─────────────────────────────────────────────────────────────────────┐
│  Trinity    [Agents ▾]  [Processes ▾]  [Approvals (3)]  [Settings]  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Dashboard       │
                    │ All Processes   │
                    │ Create Process  │
                    └─────────────────┘
```

### 10.2 Page Structure

| Page | Purpose | Key Components |
|------|---------|----------------|
| **Process Dashboard** | Overview of all processes | Stats, active list, health cards |
| **Process List** | Browse all definitions | Table with status, last run, actions |
| **Process Detail** | View/edit single process | YAML editor, preview, triggers |
| **Execution Detail** | View single execution | Timeline, step details, actions |
| **Approval Inbox** | Manage pending approvals | Cards with actions |

---

## 11. MVP Scope

### Phase 1: MVP

| Component | Scope |
|-----------|-------|
| **Process List** | Cards with status, last run, next run |
| **Process Editor** | YAML editor with syntax highlighting + simple flow preview |
| **Execution View** | Timeline with status bars, expandable steps |
| **Approval Inbox** | Simple list with quick actions |
| **Dashboard** | Basic metrics (active, success rate, pending approvals) |
| **Real-Time** | WebSocket for active execution, polling for lists |

### Phase 2: Polish

| Component | Addition |
|-----------|----------|
| **Process Editor** | Auto-complete, better validation, step templates |
| **Execution View** | Live agent activity stream |
| **Approvals** | Email/Slack quick actions, delegation |
| **Dashboard** | Trend charts, cost analytics |
| **Debugging** | AI-powered error suggestions |

### Phase 3: Advanced

| Component | Addition |
|-----------|----------|
| **Visual Designer** | Drag-drop process creation (if demand warrants) |
| **Process Templates** | Library of pre-built processes |
| **Advanced Analytics** | Cost optimization, bottleneck detection |
| **Batch Operations** | Bulk retry, bulk approval |

---

## 12. Open Questions

1. **Mobile support**: How important is mobile approval workflow?
2. **Accessibility**: WCAG compliance level target?
3. **Internationalization**: Multi-language support needed?
4. **Theming**: Dark mode support for process views?

---

## 13. Next Steps

1. [ ] Create wireframes for MVP components
2. [ ] Design component library (Tailwind-based)
3. [ ] Prototype YAML editor with preview
4. [ ] Prototype execution timeline view
5. [ ] Create IT5 with implementation specifications

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-14 | UI/UX philosophy and specifications (IT4) |
