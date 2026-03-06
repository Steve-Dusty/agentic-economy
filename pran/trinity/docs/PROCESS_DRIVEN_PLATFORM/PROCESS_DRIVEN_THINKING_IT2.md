# Process-Driven Thinking - Iteration 2

> **Status**: Architecture Direction
> **Date**: 2026-01-14
> **Previous**: `PROCESS_DRIVEN_THINKING_IT1.md`
> **Purpose**: Define the technical approach for Trinity's process engine

---

## Executive Summary

Following IT1's analysis of the process-driven vision, this iteration focuses on **how to build it**. Key decisions:

1. **BPMN as inspiration** — Learn from 20+ years of workflow patterns
2. **Home-grown engine** — Build Trinity-native, avoid licensing constraints
3. **Incremental delivery** — Phased approach, each phase independently useful
4. **AI-assisted development** — Leverage AI coding assistants for complex logic

---

## 1. Decision: Home-Grown Process Engine

### Why Not Use Existing Libraries?

| Option | Issue |
|--------|-------|
| **SpiffWorkflow** | LGPL license — requires sharing modifications, some enterprises avoid |
| **Camunda/Flowable** | Java-based, separate service, operational overhead |
| **Temporal** | Separate service, Go/Java SDKs primarily |
| **Prefect** | Data pipeline focus, not business process oriented |

### Why Home-Grown is Viable

1. **Existing Infrastructure**: Trinity already has Redis, SQLite, APScheduler, MCP, execution queue
2. **AI-Assisted Development**: Claude/GPT can help implement complex state machine logic
3. **Focused Scope**: Don't need enterprise features (multi-tenancy, clustering)
4. **Full Control**: Can optimize for AI agent-specific patterns
5. **No Licensing Constraints**: Clean for enterprise sales

### Licensing Consideration

Trinity uses **Polyform Noncommercial** with commercial licensing available. A home-grown engine ensures:
- No LGPL/GPL dependencies that complicate enterprise deals
- No "some enterprises avoid GPL variants" conversations
- Clean IP ownership

---

## 2. BPMN as Inspiration (Not Implementation)

### What to Adopt from BPMN

| BPMN Concept | Trinity Adaptation | Why It Matters |
|--------------|-------------------|----------------|
| **Start Event** | Trigger (schedule, webhook, manual) | Clear process initiation |
| **End Event** | Completion + output delivery | Clear success criteria |
| **Service Task** | Agent task execution | Core automation unit |
| **User Task** | Human approval step | Enterprise requirement |
| **Exclusive Gateway (XOR)** | If/else branching | Conditional flows |
| **Parallel Gateway (AND)** | Fan-out/fan-in | Multi-agent parallelism |
| **Timer Event** | Wait/delay step | Scheduling needs |
| **Error Boundary** | Per-step error handling | Graceful failures |
| **Sub-Process** | Nested/reusable processes | Composition |
| **Compensation** | Rollback on failure | State consistency |

### What NOT to Adopt

- Full BPMN 2.0 XML schema (100+ element types, overkill)
- Visual notation standards (YAML is developer-friendly)
- Pools/Lanes as primary concept (agents are the natural boundary)

### Trinity-Specific Extensions Beyond BPMN

| Extension | Purpose |
|-----------|---------|
| **Agent State Binding** | Track which stateful agent executes each task |
| **Cost Tracking** | Budget limits per process/step |
| **Context Checkpoints** | Save/restore agent context |
| **Learning Events** | Capture feedback for improvement |
| **Informed Subscriptions** | Which agents observe which steps |

---

## 3. Learning from Existing Tools

### From SpiffWorkflow (Architecture Patterns)

```
Key takeaways:
├── Workflow state as serializable object (→ Redis storage)
├── Task handlers as pluggable components (→ handler registry)
├── Step-by-step execution with state persistence
└── Custom task specifications for extensibility
```

### From Temporal (Reliability Patterns)

```
Key takeaways:
├── Event sourcing for durability (consider for audit trail)
├── Activity heartbeats for long-running tasks (agent health checks)
├── Retry policies with exponential backoff
└── Workflow versioning strategy (immutable definitions)
```

### From Prefect (Developer Experience)

```
Key takeaways:
├── Python-native flow definitions (YAML equivalent for Trinity)
├── Task dependency as declarative config
├── State management abstraction
└── Built-in observability (WebSocket updates)
```

### From Camunda (BPMN Patterns)

```
Key takeaways:
├── Gateway semantics (XOR: first match, AND: all paths, OR: condition-based)
├── Compensation handlers (undo pattern)
├── Timer events (delay, deadline, cycle)
└── Message correlation (match events to process instances)
```

---

## 4. Proposed Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│  Trinity Process Engine                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Process         │  │ Execution       │  │ State           │ │
│  │ Definition      │  │ Coordinator     │  │ Manager         │ │
│  │ Parser          │  │                 │  │                 │ │
│  │                 │  │ • Dependency    │  │ • Redis runtime │ │
│  │ • YAML → Model  │  │   resolution    │  │ • SQLite history│ │
│  │ • Validation    │  │ • Step dispatch │  │ • Serialization │ │
│  │ • Versioning    │  │ • Event handling│  │                 │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │           │
│           └────────────────────┼────────────────────┘           │
│                                │                                │
│  ┌─────────────────────────────┴─────────────────────────────┐ │
│  │                    Task Handlers (Registry)               │ │
│  │                                                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │ AgentTask    │  │ HumanApproval│  │ WaitTimer    │    │ │
│  │  │ Handler      │  │ Handler      │  │ Handler      │    │ │
│  │  │              │  │              │  │              │    │ │
│  │  │ → MCP chat   │  │ → Approval   │  │ → APScheduler│    │ │
│  │  │ → Cost track │  │   queue      │  │   delay      │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  │                                                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │ Gateway      │  │ SubProcess   │  │ Notification │    │ │
│  │  │ Handler      │  │ Handler      │  │ Handler      │    │ │
│  │  │              │  │              │  │              │    │ │
│  │  │ → XOR/AND/OR │  │ → Nested     │  │ → Slack/Email│    │ │
│  │  │   logic      │  │   execution  │  │   delivery   │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Integration Layer                      │ │
│  │                                                           │ │
│  │  • Existing MCP for agent communication                   │ │
│  │  • Existing execution queue for sequential tasks          │ │
│  │  • Existing WebSocket for real-time updates               │ │
│  │  • Existing scheduler service for timers                  │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Process Definition Parser** | YAML → internal model, validation, versioning |
| **Execution Coordinator** | Resolve dependencies, dispatch steps, handle events |
| **State Manager** | Persist/restore execution state, crash recovery |
| **Task Handlers** | Execute specific step types (agent, approval, timer, etc.) |
| **Integration Layer** | Connect to existing Trinity infrastructure |

---

## 5. Phased Implementation Plan

### Phase 1: Sequential Execution (Foundation)

**Goal**: Execute linear processes with agent tasks

**Scope**:
- YAML parser for simple process definitions
- Sequential step execution
- State persistence (Redis)
- Agent task handler (calls existing MCP)
- Basic execution history (SQLite)

**Example Process**:
```yaml
process:
  name: simple-report
  version: 1
  
  steps:
    - id: research
      type: agent_task
      agent: researcher
      message: "Research market trends"
    
    - id: write
      type: agent_task
      agent: writer
      message: "Write report based on: {{steps.research.output}}"
      depends_on: [research]

  output:
    on_success:
      - type: log
        message: "Process completed successfully"
```

**Deliverables**:
- `ProcessDefinition` model
- `ProcessExecution` model
- `ExecutionCoordinator` class
- `AgentTaskHandler` class
- `StateManager` class (Redis)
- API endpoints: create, trigger, status, history

**Estimated Effort**: 1-2 weeks

---

### Phase 2: Parallel Execution (Fan-out/Fan-in)

**Goal**: Execute independent steps in parallel

**Scope**:
- Dependency graph resolution
- Parallel step dispatch
- Fan-in (wait for all dependencies)
- Cost aggregation across parallel branches

**Example Process**:
```yaml
process:
  name: multi-competitor-research
  
  steps:
    - id: research-alpha
      type: agent_task
      agent: researcher
      message: "Research Company Alpha"
    
    - id: research-beta
      type: agent_task
      agent: researcher
      message: "Research Company Beta"
    
    - id: research-gamma
      type: agent_task
      agent: researcher
      message: "Research Company Gamma"
    
    - id: merge-findings
      type: agent_task
      agent: analyst
      message: "Merge and analyze findings"
      depends_on: [research-alpha, research-beta, research-gamma]
```

**Deliverables**:
- `DependencyResolver` class
- Parallel execution logic in coordinator
- Fan-in wait mechanism
- Updated state model for parallel branches

**Estimated Effort**: 1-2 weeks

---

### Phase 3: Human Approval Gates

**Goal**: Pause processes for human decisions

**Scope**:
- Human approval step type
- Approval queue/inbox
- Timeout handling
- Decision routing (approve → continue, reject → stop)
- Email/Slack notifications

**Example Process**:
```yaml
process:
  name: reviewed-report
  
  steps:
    - id: draft
      type: agent_task
      agent: writer
      message: "Write draft report"
    
    - id: review
      type: human_approval
      depends_on: [draft]
      config:
        approvers: [manager@company.com]
        timeout: 48h
        on_timeout: notify
        artifacts:
          - "{{steps.draft.output_path}}"
    
    - id: publish
      type: agent_task
      agent: writer
      message: "Publish approved report"
      depends_on: [review]
      condition: "{{steps.review.decision}} == 'approved'"
```

**Deliverables**:
- `HumanApprovalHandler` class
- Approval database tables
- Approval API endpoints
- Notification integration
- UI: approval inbox

**Estimated Effort**: 2 weeks

---

### Phase 4: Conditional Branching (Gateways)

**Goal**: Dynamic flow based on conditions

**Scope**:
- Exclusive gateway (XOR) — first matching path
- Conditional step execution
- Expression evaluation engine
- Skip/branch logic

**Example Process**:
```yaml
process:
  name: conditional-flow
  
  steps:
    - id: analyze
      type: agent_task
      agent: analyst
      message: "Analyze data quality"
    
    - id: gateway-quality
      type: gateway
      gateway_type: exclusive
      depends_on: [analyze]
      routes:
        - condition: "{{steps.analyze.output.quality_score}} >= 80"
          next: publish
        - condition: "{{steps.analyze.output.quality_score}} >= 50"
          next: review
        - default: true
          next: reprocess
    
    - id: publish
      type: agent_task
      agent: writer
      message: "Publish high-quality report"
    
    - id: review
      type: human_approval
      approvers: [manager@company.com]
    
    - id: reprocess
      type: agent_task
      agent: researcher
      message: "Gather more data"
```

**Deliverables**:
- `GatewayHandler` class
- Expression evaluator
- Route resolution logic
- Conditional step skipping

**Estimated Effort**: 1-2 weeks

---

### Phase 5: Timer Events & Scheduling

**Goal**: Time-based process control

**Scope**:
- Wait/delay steps
- Deadline handling
- Integration with existing scheduler service
- Timeout enforcement

**Example**:
```yaml
steps:
  - id: wait-for-market-open
    type: timer
    config:
      wait_until: "09:30"
      timezone: America/New_York
  
  - id: execute-trade
    type: agent_task
    depends_on: [wait-for-market-open]
```

**Estimated Effort**: 1 week

---

### Phase 6: Sub-Processes & Composition

**Goal**: Reusable process components

**Scope**:
- Nested process execution
- Process templates
- Parameter passing
- Shared step libraries

**Estimated Effort**: 2 weeks

---

## 6. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Definition Format** | YAML | Human-readable, version-controllable, existing pattern in Trinity |
| **State Storage** | Redis (runtime) + SQLite (history) | Fast runtime, durable history |
| **Execution Model** | Async with existing queue | Reuse infrastructure, proven pattern |
| **Versioning** | Immutable definitions | Safe updates, audit trail |
| **Expression Language** | Jinja2-style `{{...}}` | Familiar, Python-native |
| **Handler Architecture** | Pluggable registry | Extensible, testable |

---

## 7. Integration Points with Existing Trinity

| Existing Component | Integration |
|--------------------|-------------|
| **MCP Server** | `chat_with_agent` for agent tasks |
| **Execution Queue** | Sequential task dispatch |
| **Scheduler Service** | Timer events, process triggers |
| **WebSocket** | Real-time execution updates |
| **Redis** | Runtime state, distributed locking |
| **SQLite** | Process definitions, execution history |
| **Activity Service** | Execution tracking, observability |

---

## 8. Open Questions for Future Iterations

1. **Process Designer UI**: Visual editor or YAML-only initially?
2. **Compensation/Rollback**: How complex should undo logic be?
3. **Cost Budgets**: Process-level vs step-level enforcement?
4. **Agent Context Passing**: How to share context between steps?
5. **Process Templates**: Inheritance or composition model?
6. **Event Bus Integration**: Required for Phase 2+?

---

## 9. Success Criteria

| Metric | Target |
|--------|--------|
| **Phase 1 delivery** | 2 weeks |
| **Sequential process execution** | Working end-to-end |
| **State persistence** | Survives backend restart |
| **Agent task integration** | Uses existing MCP |
| **Observability** | Execution visible in UI |

---

## 10. Next Steps

1. [ ] Design minimal YAML schema (Phase 1 scope only)
2. [ ] Implement `ProcessDefinition` model
3. [ ] Implement `ExecutionCoordinator` with sequential logic
4. [ ] Implement `AgentTaskHandler`
5. [ ] Add API endpoints
6. [ ] Create IT3 with detailed implementation specs

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-14 | Initial architecture direction (IT2) |
