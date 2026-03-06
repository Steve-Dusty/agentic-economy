# Dashboard Execution Timeline

## What This Diagram Shows

The Dashboard Timeline View provides a waterfall-style visualization of agent activities over time. It displays:

- **Agent rows**: Each agent appears as a horizontal lane
- **Execution boxes**: Color-coded bars showing task duration and trigger type
- **Collaboration arrows**: Lines connecting agents when one triggers another
- **Time axis**: Horizontal scale with 15-minute grid intervals
- **NOW marker**: Green dashed line showing current time (in live mode)

This view enables operators to analyze multi-agent workflow patterns, identify busy periods, and understand execution sequences across the fleet.

---

## Timeline Layout

```
+-----------------------------------------------------------------------------------------+
|                        DASHBOARD TIMELINE VIEW                                          |
|                                                                                         |
|  +-- Controls --+                                        +-- Legend --+                 |
|  | [-] [====] [+] Zoom   [ ] Active only  [Jump to Now] | Manual     Scheduled        |
|  |                                                       | MCP        Agent-Triggered  |
|  +------------------+                                    +-----------------------------+
|                                                                                         |
|  +-- Agent Labels --+  +-- Time Grid (15-min intervals) ----------------------- NOW -> |
|  |                   |  |                                                               |
|  | +--------------+  |  |  09:00        09:15        09:30        09:45        10:00   |
|  | | agent-lead   |  |  |    |           |           |           |           |         |
|  | | [*] Running  |  |  | ====[GREEN]====                                              |
|  | | AUTO: ON     |  |  |                                                    |         |
|  | | Ctx: 45%     |  |  |                                                    |         |
|  | +--------------+  |  |                                                    |         |
|  |                   |  |    |           |           |           |           |         |
|  | +--------------+  |  |                    ====[PURPLE]====                          |
|  | | agent-worker |  |  |                         |                          |         |
|  | | [ ] Idle     |  |  |                         |                          |         |
|  | | AUTO: OFF    |  |  |                         |                          |         |
|  | | Ctx: 12%     |  |  |                         v                          |         |
|  | +--------------+  |  |                    ====[CYAN]====                  |         |
|  |                   |  |                                                    |         |
|  | +--------------+  |  |    |           |           |           |           |         |
|  | | agent-data   |  |  |                                    ====[PINK]===             |
|  | | [*] Running  |  |  |                                                    |         |
|  | | AUTO: ON     |  |  |                                                    |         |
|  | +--------------+  |  |                                                    | [NOW]   |
|  |                   |  |                                                    |         |
|  +-------------------+  +----------------------------------------------------+---------+
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## Detailed Component Layout

```
+-----------------------------------------------------------------------------------------+
|                         TIMELINE COMPONENT ANATOMY                                      |
|                                                                                         |
|                                                                                         |
|   +---------------------------------------------------------------------------------+   |
|   |  HEADER BAR                                                                     |   |
|   |                                                                                 |   |
|   |  +-- Zoom Controls --+  +-- Toggle --+  +-- Jump Button --+  +-- Legend ----+  |   |
|   |  | [-] [slider] [+]  |  | [ ] Active |  | [clock] Jump    |  | * Manual     |  |   |
|   |  | 100%              |  |     only   |  |    to Now       |  | * MCP        |  |   |
|   |  +-------------------+  +------------+  +-----------------+  | * Scheduled  |  |   |
|   |                                                              | * Agent-Trig |  |   |
|   |                                                              +--------------+  |   |
|   +---------------------------------------------------------------------------------+   |
|                                                                                         |
|   +---------------------------------------------------------------------------------+   |
|   |  SCROLLABLE TIMELINE AREA                                                       |   |
|   |                                                                                 |   |
|   |  +-- Sticky Labels (240px) --+  +-- Time Scale Header (sticky top) -------+    |   |
|   |  |                           |  |                                          |    |   |
|   |  |  (spacer for header)      |  |  09:00   09:15   09:30   09:45   10:00  |    |   |
|   |  |                           |  |    |       |       |       |       |    |    |   |
|   |  +---------------------------+  +------------------------------------------+    |   |
|   |  |                           |  |                                          |    |   |
|   |  |  +-- Agent Tile --------+ |  |  +-- Activity Row ----------------------+|    |   |
|   |  |  | [dot] agent-name SYS | |  |  |                                      ||    |   |
|   |  |  | [toggle] AUTO        | |  |  |  [====BAR====]         [==BAR==]    ||    |   |
|   |  |  | [===---] 45% ctx     | |  |  |        \                             ||    |   |
|   |  |  | 12 tasks, 95%, $0.45 | |  |  |         \                            ||    |   |
|   |  |  | Mem: 128MB/512MB     | |  |  |          \    (arrow)                ||    |   |
|   |  |  +----------------------+ |  |  |           \                          ||    |   |
|   |  |                           |  |  +------------\-------------------------+|    |   |
|   |  |  +-- Agent Tile --------+ |  |  +-------------\------------------------+|    |   |
|   |  |  | [dot] agent-worker   | |  |  |              v                       ||    |   |
|   |  |  | [toggle] MANUAL      | |  |  |            [===CYAN===]              ||    |   |
|   |  |  | [=-----] 12% ctx     | |  |  |                                      ||    |   |
|   |  |  | No tasks             | |  |  |                                      ||    |   |
|   |  |  +----------------------+ |  |  +--------------------------------------+|    |   |
|   |  |                           |  |                                          |    |   |
|   |  +---------------------------+  +------------------------------------------+    |   |
|   |                                                                                 |   |
|   +---------------------------------------------------------------------------------+   |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## Color Coding Legend

```
+-----------------------------------------------------------------------------------------+
|                         EXECUTION BAR COLOR CODING                                      |
|                                                                                         |
|   Colors are determined by TRIGGER TYPE, not activity type:                             |
|                                                                                         |
|   +------------------+-------------+-------------+-------------------------------------+ |
|   | Trigger Type     | Active      | Inactive    | Description                         | |
|   +------------------+-------------+-------------+-------------------------------------+ |
|   | Error            | #ef4444     | -           | Any failed execution (red)          | |
|   |                  | (red-500)   |             |                                     | |
|   +------------------+-------------+-------------+-------------------------------------+ |
|   | In Progress      | #f59e0b     | -           | Currently running task (amber)      | |
|   |                  | (amber-500) |             | Bar grows in real-time              | |
|   +------------------+-------------+-------------+-------------------------------------+ |
|   | Manual/User      | #22c55e     | #86efac     | User triggered via UI               | |
|   |                  | (green-500) | (green-300) |                                     | |
|   +------------------+-------------+-------------+-------------------------------------+ |
|   | MCP              | #ec4899     | #f9a8d4     | Triggered via Claude Code MCP       | |
|   |                  | (pink-500)  | (pink-300)  |                                     | |
|   +------------------+-------------+-------------+-------------------------------------+ |
|   | Schedule         | #8b5cf6     | #c4b5fd     | Cron-scheduled execution            | |
|   |                  | (purple-500)| (purple-300)|                                     | |
|   +------------------+-------------+-------------+-------------------------------------+ |
|   | Agent            | #06b6d4     | #67e8f9     | Called by another agent             | |
|   |                  | (cyan-500)  | (cyan-300)  |                                     | |
|   +------------------+-------------+-------------+-------------------------------------+ |
|   | Default          | #3b82f6     | #93c5fd     | Unknown trigger type (blue)         | |
|   |                  | (blue-500)  | (blue-300)  |                                     | |
|   +------------------+-------------+-------------+-------------------------------------+ |
|                                                                                         |
|   Visual Examples:                                                                      |
|                                                                                         |
|   Manual task:      [========GREEN========]                                             |
|   MCP call:         [========PINK=========]                                             |
|   Scheduled:        [=======PURPLE========]                                             |
|   Agent-triggered:  [========CYAN=========]                                             |
|   In progress:      [====AMBER====>        (growing)                                    |
|   Error:            [========RED==========]                                             |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## Collaboration Arrows

```
+-----------------------------------------------------------------------------------------+
|                         COLLABORATION ARROW RENDERING                                   |
|                                                                                         |
|   When Agent A calls Agent B, the visualization shows:                                  |
|                                                                                         |
|   Agent A row:   [======GREEN======]  (A's execution - manual trigger)                  |
|                           \                                                             |
|                            \    Arrow drawn from A to B                                 |
|                             \   Color: #06b6d4 (cyan)                                   |
|                              \                                                          |
|                               v                                                         |
|   Agent B row:               [=====CYAN=====]  (B's execution - agent trigger)          |
|                                                                                         |
|                                                                                         |
|   Arrow Validation Rules:                                                               |
|   -----------------------                                                               |
|   1. Arrows ONLY drawn when target agent has an execution box                           |
|   2. 30-second tolerance window for matching collaboration to execution                 |
|   3. No "floating arrows" pointing to empty space                                       |
|   4. Self-calls (agent calls itself) draw arrow to same row                             |
|                                                                                         |
|                                                                                         |
|   Source-Target Mapping:                                                                |
|   ----------------------                                                                |
|                                                                                         |
|   +-- Collaboration Event --+     +-- Resulting Display --+                             |
|   | source_agent: agent-a   | --> | Arrow FROM: agent-a    |                            |
|   | target_agent: agent-b   |     | Arrow TO: agent-b      |                            |
|   | timestamp: 09:23:45     |     | X position: at 09:23   |                            |
|   +-------------------------+     +------------------------+                            |
|                                                                                         |
|   +-- Execution Events --+        +-- Resulting Display --+                             |
|   | agent: agent-a       | -----> | Box on agent-a row    |                             |
|   | triggered_by: manual |        | Color: GREEN          |                             |
|   +----------------------+        +-----------------------+                             |
|   | agent: agent-b       | -----> | Box on agent-b row    |                             |
|   | triggered_by: agent  |        | Color: CYAN           |                             |
|   +----------------------+        +-----------------------+                             |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## Activity Types on Timeline

```
+-----------------------------------------------------------------------------------------+
|                         ACTIVITY TYPES DISPLAYED                                        |
|                                                                                         |
|   The timeline displays these activity types as execution boxes:                        |
|                                                                                         |
|   +--------------------+--------------------------------------------------+-------------+
|   | Activity Type      | Description                                      | Creates Box |
|   +--------------------+--------------------------------------------------+-------------+
|   | chat_start         | Chat message processing started                  | Yes         |
|   | chat_end           | Chat processing completed                        | Extends box |
|   | schedule_start     | Scheduled task execution started                 | Yes         |
|   | schedule_end       | Scheduled execution completed                    | Extends box |
|   | agent_collaboration| Agent-to-agent call (source side)                | Arrow only  |
|   +--------------------+--------------------------------------------------+-------------+
|                                                                                         |
|   Key Distinction:                                                                      |
|   ----------------                                                                      |
|   - Execution events (chat_*, schedule_*) --> Create boxes on the executing agent's row|
|   - Collaboration events --> Only create arrows, NOT boxes                              |
|   - The target agent's box comes from their own chat_start event with triggered_by=agent|
|                                                                                         |
|                                                                                         |
|   Box Width Calculation:                                                                |
|   ----------------------                                                                |
|   - Width = (duration_ms / total_timeline_ms) * grid_width                              |
|   - Minimum width: 12px (for visibility)                                                |
|   - In-progress tasks: Width grows in real-time as duration increases                   |
|                                                                                         |
|                                                                                         |
|   Filtering Rules (what NOT to show):                                                   |
|   -----------------------------------                                                   |
|   - Regular user chat sessions (triggered_by='user' without parallel_mode)              |
|   - These are interactive conversations, not autonomous task executions                 |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## NOW Marker Positioning

```
+-----------------------------------------------------------------------------------------+
|                         NOW MARKER AND AUTO-SCROLL                                      |
|                                                                                         |
|   In live mode, the NOW marker shows current time:                                      |
|                                                                                         |
|   +-- Timeline Viewport (100% width) ------------------------------------------+        |
|   |                                                                            |        |
|   |   [=====past events=====]                    [NOW]     [10% padding]       |        |
|   |                                                |                           |        |
|   |   <------------------ 90% -------------------->|<-------- 10% ------------>|        |
|   |                                                |                           |        |
|   +------------------------------------------------|---------------------------+        |
|                                                    |                                    |
|                                                    | Green dashed line (#10b981)        |
|                                                    | Updates every second               |
|                                                                                         |
|   Auto-Scroll Behavior:                                                                 |
|   ---------------------                                                                 |
|   - NOW marker positioned at 90% of viewport width (not far right edge)                 |
|   - 10% empty space to right for visual breathing room                                  |
|   - Users cannot scroll past NOW into the future                                        |
|   - "Jump to Now" button appears when user scrolls away                                 |
|   - Clicking "Jump to Now" re-enables auto-scroll                                       |
|                                                                                         |
|                                                                                         |
|   Default Zoom on Load:                                                                 |
|   ---------------------                                                                 |
|   - Default zoom = timeRangeHours / 2                                                   |
|   - For 24h range: zoom 12x (shows ~2 hours of activity)                                |
|   - Auto-scrolls to NOW position on initial load                                        |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## Agent Tile Layout

```
+-----------------------------------------------------------------------------------------+
|                         AGENT TILE (COMPACT VIEW)                                       |
|                                                                                         |
|   Each agent row has a sticky left tile (240px width):                                  |
|                                                                                         |
|   +-- Agent Tile (240px x rowHeight) --------------------------------------------+      |
|   |                                                                              |      |
|   |  Row 1: [status dot] Agent Name [SYS badge]                                  |      |
|   |         ^            ^           ^                                           |      |
|   |         |            |           +-- Purple badge for system agents          |      |
|   |         |            +-- Click to navigate to agent detail                   |      |
|   |         +-- Color: green (running), gray (stopped), pulse (active)           |      |
|   |                                                                              |      |
|   |  Row 2: [toggle switch] AUTO / MANUAL                                        |      |
|   |         ^                                                                    |      |
|   |         +-- Emits 'toggle-autonomy' event on click                           |      |
|   |                                                                              |      |
|   |  Row 3: [======----] 45% context                                             |      |
|   |         ^                                                                    |      |
|   |         +-- Progress bar showing context window usage                        |      |
|   |                                                                              |      |
|   |  Row 4: 12 tasks, 95% success, $0.45  (or "No tasks" if none)               |      |
|   |         ^                                                                    |      |
|   |         +-- Execution stats from the selected time range                     |      |
|   |                                                                              |      |
|   |  Row 5: Mem: 128MB / 512MB                                                   |      |
|   |         ^                                                                    |      |
|   |         +-- Memory limit display                                             |      |
|   |                                                                              |      |
|   +------------------------------------------------------------------------------+      |
|                                                                                         |
|   Status Dot Colors:                                                                    |
|   ------------------                                                                    |
|   - Green (#22c55e) + pulse: Active execution in progress                               |
|   - Green (#22c55e): Running, no current execution                                      |
|   - Gray (#9ca3af): Stopped                                                             |
|   - Red (#ef4444): Error state                                                          |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## Real-Time Bar Extension

```
+-----------------------------------------------------------------------------------------+
|                         IN-PROGRESS BAR ANIMATION                                       |
|                                                                                         |
|   In-progress tasks show real-time bar growth:                                          |
|                                                                                         |
|   T=0s:   [===]                          (minimum width, amber)                         |
|   T=5s:   [======]                       (bar extends)                                  |
|   T=10s:  [==========]                   (bar continues growing)                        |
|   T=15s:  [==============]               (still in progress)                            |
|   T=20s:  [==================]           (task completes)                               |
|   Final:  [==================]           (color changes to final state)                 |
|                                                                                         |
|                                                                                         |
|   Implementation Details:                                                               |
|   -----------------------                                                               |
|   - currentNow ref updates every 1 second                                               |
|   - effectiveDuration = currentNow - startTimestamp                                     |
|   - Bar width recalculated on each update                                               |
|   - Tooltip shows live elapsed time: "In Progress - 15.2s"                              |
|   - On completion: bar snaps to final width from actual duration_ms                     |
|                                                                                         |
|                                                                                         |
|   Tooltip Examples:                                                                     |
|   -----------------                                                                     |
|   - In progress: "MCP Task (In Progress) - 12.5s"                                       |
|   - Completed:   "Scheduled: Daily Report - 45.3s"                                      |
|   - Error:       "Manual Task (Error) - 8.1s"                                           |
|   - Estimated:   "Agent-Triggered Task - ~30.0s" (tilde for estimated duration)         |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## Data Flow

```
+-----------------------------------------------------------------------------------------+
|                         TIMELINE DATA FLOW                                              |
|                                                                                         |
|                                                                                         |
|   +-------------------+    +------------------+    +------------------------+           |
|   |   Dashboard.vue   |--->| network.js store |--->| ReplayTimeline.vue     |           |
|   |   (Parent)        |    |                  |    | (Component)            |           |
|   +-------------------+    +------------------+    +------------------------+           |
|           |                        |                         |                          |
|           |                        |                         v                          |
|           |                        |               +------------------------+           |
|           |                        |               | Agent Tiles (240px)    |           |
|           |                        |               | - Name, status         |           |
|           |                        |               | - Autonomy toggle      |           |
|           |                        |               | - Context bar          |           |
|           |                        |               | - Execution stats      |           |
|           |                        |               +------------------------+           |
|           |                        v                                                    |
|           |              +------------------+                                            |
|           |              | WebSocket        |                                            |
|           |              | (Live events)    |                                            |
|           |              +--------+---------+                                            |
|           |                       |                                                      |
|           v                       v                                                      |
|   +-------------------+    +------------------+                                          |
|   | setViewMode()     |    | contextStats     |                                          |
|   | - graph           |    | executionStats   |                                          |
|   | - timeline        |    | (5s polling)     |                                          |
|   +-------------------+    +------------------+                                          |
|                                                                                         |
|                                                                                         |
|   Props Passed to ReplayTimeline:                                                       |
|   --------------------------------                                                       |
|   | Prop             | Source                          | Purpose                    |  |
|   |------------------|--------------------------------|----------------------------|  |
|   | agents           | networkStore.agents            | Agent list with status     |  |
|   | nodes            | VueFlow nodes array            | Full node data for tiles   |  |
|   | events           | networkStore.historicalCollab  | Timeline events            |  |
|   | contextStats     | networkStore.contextStats      | Context usage per agent    |  |
|   | executionStats   | networkStore.executionStats    | Task stats per agent       |  |
|   | isLiveMode       | Hardcoded true                 | Enables live features      |  |
|   | timeRangeHours   | selectedTimeRange              | For default zoom calc      |  |
|   +---------------------------------------------------------------------------------+   |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## Sources

| Document | Path |
|----------|------|
| Dashboard Timeline View (feature flow) | `docs/memory/feature-flows/dashboard-timeline-view.md` |
| Replay Timeline (feature flow) | `docs/memory/feature-flows/replay-timeline.md` |
| Activity Stream (feature flow) | `docs/memory/feature-flows/activity-stream.md` |
| ReplayTimeline Component | `src/frontend/src/components/ReplayTimeline.vue` |
| Network Store | `src/frontend/src/stores/network.js` |
| Dashboard View | `src/frontend/src/views/Dashboard.vue` |

---

## Last Updated

**2026-01-25**

Key features documented:
- Trigger-based color coding (Manual, MCP, Scheduled, Agent-Triggered)
- Collaboration arrow validation (30-second tolerance, no floating arrows)
- NOW marker at 90% viewport position
- Real-time in-progress bar extension
- Agent tile compact layout with 5 rows of information
- Activity types that create boxes vs arrows
