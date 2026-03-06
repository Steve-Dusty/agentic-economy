# Process-Driven Platform - Backlog Index

> **Status**: Draft
> **Last Updated**: 2026-01-14
> **Source Documents**: IT1, IT2, IT3, IT4

---

## Backlog Structure

The backlog is split into phase-based files for easier AI agent consumption:

| File | Phase | Epics | Stories | Focus |
|------|-------|-------|---------|-------|
| [`BACKLOG_MVP.md`](./BACKLOG_MVP.md) | MVP | E1-E4, E15 | 26 | Sequential processes with basic UI |
| [`BACKLOG_CORE.md`](./BACKLOG_CORE.md) | Core | E5-E8, E13-E14 | 23 | Parallel, approvals, gateways, triggers |
| [`BACKLOG_ADVANCED.md`](./BACKLOG_ADVANCED.md) | Advanced | E9-E12, E16 | 13 | Scheduling, sub-processes, analytics |
| [`BACKLOG_RELIABILITY_IMPROVEMENTS.md`](./BACKLOG_RELIABILITY_IMPROVEMENTS.md) | Reliability | - | 14 | Integration tests, execution recovery |
| [`BACKLOG_ACCESS_AUDIT.md`](./BACKLOG_ACCESS_AUDIT.md) | Governance | E17-E19 | 9 | RBAC, audit logging, execution limits |
| [`BACKLOG_ONBOARDING.md`](./BACKLOG_ONBOARDING.md) | MVP+/Core | E20-E24 | 17 | Onboarding, documentation, guided tours |

**Total**: 24 Epics, 102 Stories

---

## Epic Overview

| Epic | Description | Phase | Stories |
|------|-------------|-------|---------|
| **E1** | Process Definition & Storage | MVP | 6 |
| **E2** | Sequential Execution Engine | MVP | 7 |
| **E3** | Process Definition UI | MVP | 4 |
| **E4** | Execution Monitoring UI | MVP | 5 |
| **E5** | Parallel Execution | Core | 3 |
| **E6** | Human Approval | Core | 5 |
| **E7** | Conditional Logic (Gateways) | Core | 3 |
| **E8** | Event Triggers | Core | 3 |
| **E9** | Timer & Scheduling | Advanced | 3 |
| **E10** | Sub-Processes | Advanced | 2 |
| **E11** | Analytics & Cost Tracking | Advanced | 3 |
| **E12** | Process Templates | Advanced | 2 |
| **E13** | Error Handling & Retry | Core | 4 |
| **E14** | Notification Step | Core | 2 |
| **E15** | Event Publishing Infrastructure | MVP | 4 |
| **E16** | Agent Roles (EMI Pattern) | Advanced | 3 |
| **E17** | Access Control (RBAC) | Governance | 4 |
| **E18** | Audit Logging | Governance | 3 |
| **E19** | Execution Governance | Governance | 2 |
| **E20** | Empty States & Quick Wins | MVP+ | 4 |
| **E21** | Documentation Tab | MVP+ | 6 |
| **E22** | Contextual Help | Core | 3 |
| **E23** | Guided Tours | Core | 3 |
| **E24** | First Process Wizard | Advanced | 4 |

---

## Backlog Conventions

### Story Format

```markdown
### [EPIC-ID]-[STORY-ID]: Story Title
**As a** [role], **I want** [goal], **so that** [benefit].

| Attribute | Value |
|-----------|-------|
| Size | XS / S / M / L / XL |
| Priority | P0 (Critical) / P1 (High) / P2 (Medium) / P3 (Low) |
| Phase | MVP / Core / Advanced |
| Dependencies | List of blocking stories |
| Status | pending / in_progress / done |

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
```

### Size Reference

| Size | Effort | Example |
|------|--------|---------|
| **XS** | < 2 hours | Add a field, simple UI change |
| **S** | 2-4 hours | Simple endpoint, basic component |
| **M** | 4-8 hours | Feature with multiple parts |
| **L** | 1-2 days | Complex feature, integration |
| **XL** | 2-5 days | Major subsystem, needs breakdown |

### Priority Definitions

| Priority | Definition |
|----------|------------|
| **P0** | Blocking. Cannot ship phase without this. |
| **P1** | Important. Core functionality. |
| **P2** | Valuable. Enhances experience. |
| **P3** | Nice to have. Can defer. |

### Status Values

| Status | Definition |
|--------|------------|
| **pending** | Not started |
| **in_progress** | Currently being worked on |
| **done** | Completed and verified |

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| [`DEVELOPMENT_CONFIDENCE_MODEL.md`](./DEVELOPMENT_CONFIDENCE_MODEL.md) | DDD-based testing philosophy for shipping with confidence |
| [`DEVELOPMENT_PROCESS.md`](./DEVELOPMENT_PROCESS.md) | Development workflow and conventions |
| [`PROCESS_ENGINE_ROADMAP.md`](./PROCESS_ENGINE_ROADMAP.md) | Testing phases and implementation tracking |
| [`BPMN_RESEARCH.md`](./BPMN_RESEARCH.md) | Deep dive into BPMN 2.0 specification and industry landscape |
| **Manual Testing** | |
| [`manual_run/README.md`](./manual_run/README.md) | Manual testing agenda with 22 test cases across 5 tiers |
| [`manual_run/results/`](./manual_run/results/) | Test execution logs and findings |
| **Thinking Iterations** | |
| [`PROCESS_DRIVEN_THINKING_IT1.md`](./PROCESS_DRIVEN_THINKING_IT1.md) | IT1: Initial analysis of process-driven vision |
| [`PROCESS_DRIVEN_THINKING_IT2.md`](./PROCESS_DRIVEN_THINKING_IT2.md) | IT2: Architecture direction (home-grown, BPMN-inspired) |
| [`PROCESS_DRIVEN_THINKING_IT3.md`](./PROCESS_DRIVEN_THINKING_IT3.md) | IT3: DDD integration (aggregates, events, services) |
| [`PROCESS_DRIVEN_THINKING_IT4.md`](./PROCESS_DRIVEN_THINKING_IT4.md) | IT4: UI/UX design philosophy |
| [`PROCESS_DRIVEN_THINKING_IT5.md`](./PROCESS_DRIVEN_THINKING_IT5.md) | IT5: Scale, reliability, enterprise architecture |
| [`PROCESS_DRIVEN_THINKING_IT6.md`](./PROCESS_DRIVEN_THINKING_IT6.md) | IT6: Maturity assessment & strategic direction |

---

## Design Principles (from IT4)

These principles should guide all UI/UX decisions:

### Activity-Centered Design
Organize interface around user activities, not data objects.
- Navigation reflects jobs: Design | Monitor | Approve | Analyze
- Not: Processes | Executions | Agents | Approvals

### OODA Loop for Operations
Structure monitoring UIs for rapid decision-making:
- **Observe**: Status icons, progress bars, metrics
- **Orient**: Error details, context, history
- **Decide**: Options presented (retry, skip, escalate)
- **Act**: One-click actions with confirmation

### Progressive Disclosure
Show only what's needed at each level:
- Level 1: "3 processes running"
- Level 2: "Step 4/7, Analyze"
- Level 3: "Agent activity log"

### Calm Technology
- **Healthy**: Calm, minimal visual noise, green/neutral
- **Warning**: Yellow accents, subtle badges
- **Problem**: Red highlights, notifications, action prompts

### Error UX Principles
- Never show error without action
- Show context: error + agent output + attempts
- Suggest fixes (AI-powered when possible)
- Clear next steps: retry step vs retry process vs dismiss
- Preserve state: easy to resume from failure

---

## Traceability Matrix

| Source Document | Concept | Covered By |
|-----------------|---------|------------|
| **IT1** | Process-first paradigm | E1 (Process Definition) |
| **IT1** | Executor/Monitor/Informed roles | E16 (Agent Roles) |
| **IT1** | Human-in-the-loop | E6 (Human Approval) |
| **IT1** | Event broadcasting | E15 (Event Publishing), E16-02 |
| **IT1** | Output storage concerns | E2-06 (Step Output Storage) |
| **IT1** | Cost estimation | E11 (Analytics & Cost) |
| **IT1** | Process templates | E12 (Templates) |
| **IT2** | Sequential execution | E2 (Sequential Engine) |
| **IT2** | Parallel execution | E5 (Parallel Execution) |
| **IT2** | Human approval gates | E6 (Human Approval) |
| **IT2** | Conditional branching | E7 (Gateways) |
| **IT2** | Timer events | E9 (Timer & Scheduling) |
| **IT2** | Sub-processes | E10 (Sub-Processes) |
| **IT2** | Error boundaries | E13-02 (Error Boundary) |
| **IT2** | Compensation | E13-03 (Compensation) |
| **IT2** | Retry policies | E13-01 (Retry Policy) |
| **IT2** | Notification handler | E14 (Notification Step) |
| **IT3** | Value Objects | E1-06 |
| **IT3** | Aggregates | E1-01, E2-01 |
| **IT3** | Domain Events | E1-05, E15 |
| **IT3** | Event Sourcing (audit log approach) | E15-04 |
| **IT3** | DependencyResolver | E5-01 |
| **IT3** | ExpressionEvaluator | E7-02, E2-07 |
| **IT3** | GatewayRouter | E7-02 |
| **IT3** | CostCalculator | E11-01 |
| **IT3** | AgentGateway ACL | E2-04 |
| **IT3** | ApprovalGateway ACL | E6-02 |
| **IT3** | SchedulerGateway ACL | E9-02 |
| **IT4** | YAML + Live Preview | E3 (Definition UI) |
| **IT4** | Timeline view | E4-02 |
| **IT4** | Approval inbox + inline | E6-04, E6-05 |
| **IT4** | WebSocket updates | E4-04, E15-02 |
| **IT4** | Process Dashboard | E4-05 |
| **IT4** | Error debugging UI | E13-04 |
| **IT4** | UI/UX Principles | Design Principles section |

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-14 | Split backlog into phase-based files |
| 2026-01-14 | Created index with conventions and traceability |
| 2026-01-17 | Added BACKLOG_RELIABILITY_IMPROVEMENTS.md and BACKLOG_ACCESS_AUDIT.md |
| 2026-01-17 | Added E17-E19 epics for IT5 P1 features |
| 2026-01-17 | Added Reference Documents section with DEVELOPMENT_CONFIDENCE_MODEL.md |
| 2026-01-17 | Added BPMN_RESEARCH.md and all Thinking Iteration documents (IT1-IT6) |
| 2026-01-17 | Added manual_run folder with 22 test cases and 3 test agent templates |
| 2026-01-18 | Added BACKLOG_ONBOARDING.md with E20-E24 epics (17 stories) for onboarding and documentation |
