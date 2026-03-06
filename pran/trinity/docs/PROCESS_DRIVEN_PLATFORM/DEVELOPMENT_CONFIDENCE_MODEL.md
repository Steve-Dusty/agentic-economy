# Development Confidence Model

> **Purpose**: Define the architectural and testing principles that give developers confidence to ship changes without extensive UI/E2E testing
> **Philosophy**: If the domain is correct and orchestration is correct, the system "just works"
> **Date**: 2026-01-17

---

## Core Principle

In a well-designed DDD system, **confidence flows upward**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONFIDENCE PYRAMID                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  UI / Frontend                                                       │    │
│  │  • Thin presentation layer                                           │    │
│  │  • Can't break business logic                                        │    │
│  │  • Minimal testing needed (smoke tests)                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              ↑                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  API / Routers                                                       │    │
│  │  • Translates HTTP ↔ Domain commands                                 │    │
│  │  • Validates request format (not business rules)                     │    │
│  │  • Contract tests verify shapes                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              ↑                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Application Services (Orchestration)                                │    │
│  │  • Coordinates domain objects                                        │    │
│  │  • NO business logic here                                            │    │
│  │  • Integration tests verify coordination                             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              ↑                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  DOMAIN LAYER (Source of Truth)                                      │    │
│  │  • ALL business rules enforced here                                  │    │
│  │  • Invariants checked at construction                                │    │
│  │  • State transitions validated                                       │    │
│  │  • Exhaustive unit tests                                             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  If Domain is CORRECT + Orchestration is CORRECT = System WORKS             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## The Four Pillars of Confidence

### 1. Invariant Enforcement at Construction

**Principle**: Invalid objects cannot exist. If you can't create an invalid state, you never need to test for it.

```python
# ✅ GOOD: Value object rejects invalid input
class ProcessId:
    def __init__(self, value: str):
        if not value or not value.strip():
            raise ValueError("ProcessId cannot be empty")
        self._value = value

# Usage: You can NEVER have an empty ProcessId
# No downstream code needs to check "is process_id empty?"
```

**Test Philosophy**:
- Test that invalid construction raises exceptions
- After that, trust all `ProcessId` instances are valid

---

### 2. Rich Domain Methods (Tell, Don't Ask)

**Principle**: Domain objects protect themselves. External code cannot put them in invalid states.

```python
# ✅ GOOD: Business logic inside the aggregate
class ProcessExecution:
    def complete_step(self, step_id: StepId, output: dict):
        if self.status == ExecutionStatus.COMPLETED:
            raise InvalidStateTransition("Cannot complete step on finished execution")

        step = self._find_step(step_id)
        step.complete(output)  # Step validates its own transition

        if self._all_steps_done():
            self._complete()

        self._record_event(StepCompleted(step_id, output))

# ❌ BAD: External code manipulates state
execution.status = ExecutionStatus.COMPLETED  # No validation!
step.output = result  # No invariant check!
```

**Test Philosophy**:
- Test each domain method enforces its rules
- Test invalid transitions raise exceptions
- Trust that valid method calls produce valid states

---

### 3. Events as Immutable Facts

**Principle**: Domain events represent "what happened" - they're facts, not requests.

```python
# Events are emitted by domain operations
execution.start()  # → emits ExecutionStarted
execution.complete_step(step_id, output)  # → emits StepCompleted
execution.fail(reason)  # → emits ExecutionFailed

# Tests verify: "Did the right event get emitted?"
# Not: "Did the UI update?" or "Did the database change?"
```

**Test Philosophy**:
- Assert on events, not on external effects
- If the right event was emitted, the system will react correctly
- Event handlers are tested separately

---

### 4. Application Services as Pure Orchestration

**Principle**: Application services coordinate but contain NO business logic.

```python
# ✅ GOOD: Orchestration only
class ExecutionEngine:
    async def start_execution(self, process_id: ProcessId, input_data: dict):
        # Load
        definition = await self.definition_repo.get(process_id)

        # Domain creates and validates
        execution = ProcessExecution.create(definition, input_data)

        # Persist
        await self.execution_repo.save(execution)

        # Publish domain events
        await self.event_bus.publish(execution.events)

        return execution.id

# No business rules here - just coordination
# If domain is correct, this is correct
```

**Test Philosophy**:
- Integration tests verify components work together
- Don't re-test domain rules at this level
- Focus on: "Does data flow correctly?"

---

## Testing Strategy by Layer

| Layer | Test Type | Coverage Goal | Confidence Source |
|-------|-----------|---------------|-------------------|
| **Domain** | Unit tests | Exhaustive (100%) | Invalid states impossible |
| **Application** | Integration tests | Happy paths + key errors | Orchestration correct |
| **API** | Contract tests | Shapes + error codes | HTTP translation correct |
| **UI** | Smoke tests | Critical paths only | Just displays data |

### What We Test Exhaustively

- Every value object rejects invalid input
- Every aggregate method enforces its invariants
- Every state transition that's invalid raises an exception
- Every domain event is emitted at the right time

### What We Test Lightly

- API returns correct HTTP status codes (contract)
- API returns correct response shapes (contract)
- UI displays data from API (smoke test)

### What We Don't Need to Test

- "Does the UI show an error when validation fails?" → Domain enforces it
- "Does saving work?" → Repository tests + integration tests cover it
- "Does the button click work?" → If API works, button works

---

## Process Engine Confidence Assessment

### Current State

| Pillar | Status | Notes |
|--------|--------|-------|
| Invariant Enforcement | ⚠️ Partial | Value objects good, aggregates could be richer |
| Rich Domain Methods | ⚠️ Partial | Some methods exist, some state is externally mutable |
| Events as Facts | ✅ Strong | Good event system with domain events |
| Pure Orchestration | ✅ Strong | ExecutionEngine is clean orchestration |

### Test Coverage

| Layer | Tests | Status |
|-------|-------|--------|
| Domain Unit Tests | ~100+ | ✅ Strong |
| Application Integration | 33 | ✅ Strong |
| Recovery Integration | 12 | ✅ Strong |
| Authorization Unit | 42 | ✅ Strong |
| Audit Unit | 22 | ✅ Strong |
| API Contract | ~5 | ⚠️ Could grow |
| E2E / UI | 0 | ✅ Not needed if above is strong |

### Gaps to Address

1. **Aggregate Richness**: `ProcessExecution` and `StepExecution` allow some direct state mutation. Could be made richer.

2. **Transition Validation**: Not all invalid state transitions are explicitly prevented by the domain.

3. **Construction Invariants**: Some objects could enforce more at creation time.

---

## Path to Full Confidence

### Phase 1: Strengthen Domain Invariants
- Audit all domain objects for missing validation
- Add guard clauses to state transitions
- Make invalid states unrepresentable

### Phase 2: Domain Method Tests
- Test every public domain method
- Test every invalid transition raises
- Test every event emission

### Phase 3: Integration Test Review
- Ensure integration tests don't re-test domain logic
- Focus integration tests on coordination
- Remove redundant assertions

### Phase 4: Minimal Contract Tests
- Add ~10-15 API contract tests
- Verify response shapes
- Verify error code mapping

### Phase 5: Confidence Validation
- Ship a change with only domain + integration tests passing
- Verify it works in production
- Document any gaps discovered

---

## Decision Framework

When deciding whether to write a test, ask:

```
┌─────────────────────────────────────────────────────────────────┐
│  Is this a BUSINESS RULE?                                        │
│  → Test in DOMAIN layer (unit test)                              │
├─────────────────────────────────────────────────────────────────┤
│  Is this about COORDINATION between components?                  │
│  → Test in APPLICATION layer (integration test)                  │
├─────────────────────────────────────────────────────────────────┤
│  Is this about HTTP REQUEST/RESPONSE format?                     │
│  → Test in API layer (contract test)                             │
├─────────────────────────────────────────────────────────────────┤
│  Is this about UI DISPLAY?                                       │
│  → Probably don't test (smoke test at most)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

We'll know we've achieved "confidence" when:

1. **Developers ship with confidence**: "Domain tests pass, integration tests pass, it works"
2. **Bugs are domain bugs**: When something breaks, it's because a domain rule was missing
3. **UI testing is optional**: Manual UI testing finds UX issues, not bugs
4. **Refactoring is safe**: Changing implementation doesn't require new tests if domain unchanged

---

## References

- Domain-Driven Design (Eric Evans)
- Implementing Domain-Driven Design (Vaughn Vernon)
- "Make Invalid States Unrepresentable" (Yaron Minsky)
- Test Pyramid (Martin Fowler)

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-17 | Initial articulation of confidence model |
