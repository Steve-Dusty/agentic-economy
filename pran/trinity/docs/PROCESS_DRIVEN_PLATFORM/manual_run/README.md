# Process Engine Manual Testing Agenda

> **Purpose**: Validate the Process Engine with real agent execution
> **Date**: 2026-01-17
> **Status**: In Progress

---

## Overview

This folder contains all artifacts for manual testing of the Process Engine. We have 109+ automated tests covering unit and integration layers with mocked agents. Manual testing validates real-world behavior.

### What We're Testing

| Category | Focus |
|----------|-------|
| **Agent Task Execution** | MCP communication, real agent invocation |
| **Output Passing** | Template substitution `{{steps.X.output}}` |
| **Conditional Logic** | Gateway routing, conditional steps |
| **Human Approval** | End-to-end approval workflow |
| **Error Handling** | Failures, timeouts, retries |
| **Edge Cases** | Long chains, concurrent executions, recovery |

---

## Folder Structure

```
manual_run/
├── README.md                 # This file
├── agents/                   # Test agent templates
│   ├── process-echo/         # Minimal agent for basic tests
│   ├── process-worker/       # Standard agent for realistic tests
│   └── process-failer/       # Agent for error testing
├── processes/                # Process definition YAML files
│   ├── onboarding/          # Onboarding feature tests (O1-O6)
│   ├── tier1/               # Critical path tests (T1.1-T1.4)
│   ├── tier2/               # Conditional logic tests (T2.1-T2.4)
│   ├── tier3/               # Human approval tests (T3.1-T3.4)
│   ├── tier4/               # Error handling tests (T4.1-T4.5)
│   └── tier5/               # Edge case tests (T5.1-T5.5)
└── results/                  # Test execution logs
```

---

## Test Agents

Three test agents are provided:

### 1. `process-echo` (Minimal)
- Returns predictable output for template testing
- Fast response (< 5 seconds)
- Use for: T1.x, T2.x basic tests

### 2. `process-worker` (Standard)
- Performs actual "work" (writes files, returns structured JSON)
- Realistic agent behavior
- Use for: T1.4, T2.x, T5.x complex tests

### 3. `process-failer` (Error Testing)
- Configurable failure modes
- Use for: T4.x error handling tests

---

## Test Tiers

### Tier 1: Critical Path (Must Pass)

| ID | Test Case | Validates |
|----|-----------|-----------|
| T1.1 | Single agent step | Basic execution |
| T1.2 | Two sequential steps | Output passing |
| T1.3 | Three steps with dependencies | Dependency resolution |
| T1.4 | Step with structured output | JSON output, nested refs |

### Tier 2: Conditional Logic

| ID | Test Case | Validates |
|----|-----------|-----------|
| T2.1 | Exclusive gateway (XOR) | First matching route |
| T2.2 | Gateway with default route | Fallback behavior |
| T2.3 | Parallel execution (fork/join) | Concurrent steps |
| T2.4 | Conditional skip | `condition:` evaluation |

### Tier 3: Human Approval

| ID | Test Case | Validates |
|----|-----------|-----------|
| T3.1 | Approval - approved | Approval flow |
| T3.2 | Approval - rejected | Rejection handling |
| T3.3 | Approval with timeout | Timeout behavior |
| T3.4 | Approval with artifacts | File references |

### Tier 4: Error Handling

| ID | Test Case | Validates |
|----|-----------|-----------|
| T4.1 | Agent returns error | Error propagation |
| T4.2 | Agent timeout | Timeout handling |
| T4.3 | Retry policy works | Exponential backoff |
| T4.4 | Skip on error | Error boundary |
| T4.5 | Cancel running execution | Cancellation flow |

### Tier 5: Edge Cases

| ID | Test Case | Validates |
|----|-----------|-----------|
| T5.1 | 10-step sequential | Long chains |
| T5.2 | Diamond pattern | Complex dependency graph |
| T5.3 | Deeply nested expressions | `{{steps.a.output.b.c.d}}` |
| T5.4 | Concurrent executions (3x) | Execution limits |
| T5.5 | Recovery after restart | ExecutionRecoveryService |

---

## How to Run Tests

### Prerequisites

1. Backend running: `docker-compose up -d backend`
2. Test agents deployed (see Agent Setup below)
3. API accessible at `http://localhost:8000`

### Agent Setup

```bash
# Create agents from templates
# Navigate to Trinity UI and create agents using the templates in agents/
```

### Test Execution

For each test case:

```bash
# 1. Create process
curl -X POST http://localhost:8000/api/processes \
  -H "Content-Type: application/json" \
  -d @processes/tier1/t1.1-single-step.yaml

# 2. Publish process
curl -X POST http://localhost:8000/api/processes/{id}/publish

# 3. Execute process
curl -X POST http://localhost:8000/api/processes/{id}/execute \
  -H "Content-Type: application/json" \
  -d '{"input": {}}'

# 4. Monitor execution
curl http://localhost:8000/api/executions/{execution_id}

# 5. Check step outputs
curl http://localhost:8000/api/executions/{execution_id}/steps/{step_id}/output
```

---

## Success Criteria

| Tier | Target | Minimum |
|------|--------|---------|
| Tier 1 | 4/4 | 4/4 (blocking) |
| Tier 2 | 4/4 | 3/4 |
| Tier 3 | 4/4 | 2/4 |
| Tier 4 | 5/5 | 3/5 |
| Tier 5 | 5/5 | 2/5 |

**Total**: 22 test cases, minimum 14 passing.

---

## Results

See `results/` folder for test execution logs.
