# Process-Driven Platform - Development Process

> **Status**: Active
> **Last Updated**: 2026-01-14
> **Purpose**: Define how we develop the Process Engine feature

---

## Overview

This document defines the development workflow, branching strategy, testing approach, and conventions for implementing the Process-Driven Platform feature.

---

## 1. Branching Strategy

### Branch Structure

```
main                           # Production-ready
│
└── feature/process-engine     # All Process Engine work
```

### Workflow

1. **Start feature** (once): Create `feature/process-engine` from `main`
2. **During development**: Commit directly to feature branch
3. **End of phase**: PR feature branch to `main`

```bash
# Start feature (once)
git checkout main
git pull
git checkout -b feature/process-engine

# Daily work - commit directly
git add .
git commit -m "[PE-E1-01] Add process definition schema"
git push

# End of phase - PR to main
# Create PR: feature/process-engine → main
```

### When to Use Story Branches

Only create a separate branch if you need to:
- Park unfinished work and switch context
- Experiment with something risky

```bash
# Optional: story branch for complex work
git checkout -b pe/e2-03-execution-engine
# ... work ...
git checkout feature/process-engine
git merge pe/e2-03-execution-engine
git branch -d pe/e2-03-execution-engine
```

---

## 2. Commit Conventions

### Commit Message Format

```
[PE-EX-YY] Short description

- Detail 1
- Detail 2

Refs: IT3 Section 4
```

### Examples

```
[PE-E1-01] Add process definition schema

- Define ProcessDefinition dataclass with steps, triggers, outputs
- Add JSON Schema for editor validation
- Include example YAML in docs

Refs: IT3 Section 4 (Aggregates)
```

```
[PE-E2-03] Implement sequential execution engine

- Add ExecutionEngine service with step-by-step execution
- Handle step success/failure state transitions
- Add timeout handling per step

Refs: IT2 Section 6
```

### Commit Frequency

| Situation | Guidance |
|-----------|----------|
| **During story** | Commit logical chunks (not every file save) |
| **Story complete** | Final commit with all acceptance criteria met |
| **Squash on merge** | PR to feature branch squashes to single commit |

---

## 3. Story Workflow

### Story Lifecycle

```
pending → in_progress → testing → done
```

### Starting a Story

1. **Update backlog**: Change story status to `in_progress`
2. **Create branch**: `git checkout -b pe/eX-YY-short-name`
3. **Read acceptance criteria**: Understand what "done" means
4. **Check dependencies**: Ensure dependent stories are done

### During Development

1. **Follow acceptance criteria**: Each checkbox = a task
2. **Write tests**: Unit tests for domain logic, integration for APIs
3. **Commit regularly**: Logical chunks, not every file
4. **Reference IT docs**: Follow architectural guidance

### Completing a Story

1. **Self-review**: Check all acceptance criteria met
2. **Run tests**: `pytest tests/process_engine/`
3. **Update backlog**: Mark checkboxes complete
4. **Create PR**: To feature branch with description
5. **Manual test**: If UI story, verify in browser

### Definition of Done

A story is **done** when:
- [ ] All acceptance criteria checkboxes are checked
- [ ] Unit tests pass
- [ ] No linter errors introduced
- [ ] PR approved and merged
- [ ] Backlog status updated to `done`

---

## 4. Testing Strategy

### Test Pyramid

```
         /\
        /  \
       / E2E \        ← End of phase (manual + some automated)
      /______\
     /        \
    / Integration \   ← Per sprint (API tests)
   /______________\
  /                \
 /      Unit        \ ← Per story (domain logic)
/____________________\
```

### Unit Tests

**When**: With each story
**What**: Domain logic, value objects, services
**Location**: `tests/process_engine/unit/`

```python
# tests/process_engine/unit/test_value_objects.py
def test_duration_parsing():
    d = Duration.from_string("30s")
    assert d.seconds == 30

def test_duration_invalid():
    with pytest.raises(ValueError):
        Duration.from_string("invalid")
```

```python
# tests/process_engine/unit/test_dependency_resolver.py
def test_sequential_dependencies():
    steps = [
        StepDefinition(id="a", depends_on=[]),
        StepDefinition(id="b", depends_on=["a"]),
        StepDefinition(id="c", depends_on=["b"]),
    ]
    resolver = DependencyResolver()
    order = resolver.resolve(steps)
    assert order == [["a"], ["b"], ["c"]]
```

### Integration Tests

**When**: End of sprint or with API stories
**What**: API endpoints, database operations
**Location**: `tests/process_engine/integration/`

```python
# tests/process_engine/integration/test_process_api.py
async def test_create_process(client, auth_headers):
    response = await client.post(
        "/api/processes",
        json={"name": "test", "yaml": "..."},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert "id" in response.json()
```

### Manual UI Checkpoints

**When**: After UI stories complete
**What**: Visual verification in browser

| Sprint | Checkpoint | What to Test |
|--------|------------|--------------|
| Sprint 4 | Process List | See processes, create new |
| Sprint 4 | YAML Editor | Syntax highlighting, validation errors |
| Sprint 5 | Execution List | See executions with status icons |
| Sprint 5 | Timeline View | See steps, expand details |
| Sprint 6 | Live Updates | WebSocket updates in real-time |

### Running Tests

```bash
# Run all process engine tests
pytest tests/process_engine/ -v

# Run unit tests only
pytest tests/process_engine/unit/ -v

# Run with coverage
pytest tests/process_engine/ --cov=src/backend/process_engine

# Run specific test file
pytest tests/process_engine/unit/test_value_objects.py -v
```

---

## 5. Code Organization

### Backend Structure

```
src/backend/
├── routers/
│   └── processes.py              # NEW - Process API endpoints
│   └── executions.py             # NEW - Execution API endpoints
│   └── approvals.py              # NEW - Approval API endpoints (Core)
│
├── services/
│   └── process_engine/           # NEW - Process Engine module
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── value_objects.py  # ProcessId, StepId, Duration, Money
│       │   ├── aggregates.py     # ProcessDefinition, ProcessExecution
│       │   ├── events.py         # Domain events
│       │   └── exceptions.py     # Domain exceptions
│       ├── services/
│       │   ├── __init__.py
│       │   ├── validator.py      # Process validation
│       │   ├── expression.py     # Expression evaluator
│       │   └── resolver.py       # Dependency resolver
│       ├── repositories/
│       │   ├── __init__.py
│       │   ├── definitions.py    # Process definition repo
│       │   └── executions.py     # Execution repo
│       ├── gateways/
│       │   ├── __init__.py
│       │   ├── agent.py          # AgentGateway ACL
│       │   └── scheduler.py      # SchedulerGateway ACL (Advanced)
│       ├── handlers/
│       │   ├── __init__.py
│       │   ├── agent_task.py     # Agent task handler
│       │   └── approval.py       # Approval handler (Core)
│       └── engine.py             # ExecutionEngine
│
└── db/
    └── processes.py              # NEW - Process DB operations
```

### Frontend Structure

```
src/frontend/src/
├── views/
│   ├── ProcessList.vue           # NEW
│   ├── ProcessEditor.vue         # NEW
│   ├── ExecutionList.vue         # NEW
│   ├── ExecutionDetail.vue       # NEW
│   ├── Approvals.vue             # NEW (Core)
│   └── ProcessDashboard.vue      # NEW
│
├── components/
│   └── process/                  # NEW folder
│       ├── YamlEditor.vue
│       ├── ProcessPreview.vue
│       ├── ExecutionTimeline.vue
│       ├── StepDetail.vue
│       └── ApprovalCard.vue      # (Core)
│
└── stores/
    └── processes.js              # NEW - Process state management
```

---

## 6. AI Agent Guidelines

### For AI Agents Working on This Backlog

#### Before Starting

1. **Read the right backlog file**: Start with `BACKLOG_MVP.md`, then `BACKLOG_CORE.md`
2. **Check dependencies**: Don't start a story if dependencies aren't `done`
3. **Read IT documents**: For architectural context

#### During Implementation

1. **Follow acceptance criteria exactly**: Each checkbox = a task
2. **Reference technical notes**: They point to relevant IT sections
3. **Write tests**: Unit tests for domain logic
4. **Commit with proper format**: `[PE-EX-YY] Description`

#### Reporting Blockers

If blocked, document in the story:
```markdown
**Blocker**: [Description]
**Reason**: [Why blocked]
**Needs**: [What's needed to unblock]
```

#### When to Ask for Human Review

- Before merging PR to feature branch
- When architectural decision needed
- When acceptance criteria are ambiguous
- After completing a sprint (for manual UI check)

---

## 7. Sprint Ceremonies

### Sprint Start

1. Review stories in sprint
2. Identify dependencies
3. Create story branches

### Daily Check

- Update story status in backlog
- Note any blockers

### Sprint End

1. Mark completed stories as `done`
2. Run integration tests
3. Manual UI checkpoint (if applicable)
4. Update CHANGELOG.md

---

## 8. Definition of Done (Phase Level)

### MVP Phase Complete When

- [ ] All 25 MVP stories are `done`
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual UI checkpoints verified
- [ ] PR to main approved
- [ ] CHANGELOG.md updated

### Core Phase Complete When

- [ ] All 23 Core stories are `done`
- [ ] MVP functionality still works
- [ ] E2E test: full approval workflow
- [ ] E2E test: parallel execution
- [ ] E2E test: gateway routing

---

## 9. Documentation Updates

### When to Update

| Changed | Update |
|---------|--------|
| API endpoint added | OpenAPI docs (auto from FastAPI) |
| Schema changed | JSON Schema file |
| Major feature complete | User-facing docs |
| Architecture decision | IT document or ADR |

### CHANGELOG Entry Format

```markdown
## [Unreleased]

### Added
- ✨ [PE-E1-01] Process definition schema with YAML support
- ✨ [PE-E2-03] Sequential execution engine

### Changed
- 🔧 [PE-E1-03] Improved validation error messages

### Fixed
- 🐛 [PE-E2-04] Agent timeout now properly enforced
```

---

## 10. Quick Reference

### Commands

```bash
# Start story
git checkout feature/process-engine && git pull
git checkout -b pe/e1-01-schema

# Run tests
pytest tests/process_engine/ -v

# Check lints
ruff check src/backend/services/process_engine/

# Start dev servers
./scripts/deploy/start.sh
```

### Key Files

| Purpose | Location |
|---------|----------|
| MVP Backlog | `docs/PROCESS_DRIVEN_PLATFORM/BACKLOG_MVP.md` |
| Core Backlog | `docs/PROCESS_DRIVEN_PLATFORM/BACKLOG_CORE.md` |
| Architecture | `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT2.md` |
| DDD Design | `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT3.md` |
| UI/UX Spec | `docs/PROCESS_DRIVEN_PLATFORM/PROCESS_DRIVEN_THINKING_IT4.md` |

### URLs (Local Dev)

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| Backend API | http://localhost:8000/docs |
| WebSocket | ws://localhost:8000/ws |

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-14 | Initial development process document |
