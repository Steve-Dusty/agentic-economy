# Manual Test Run Results

> **Date**: YYYY-MM-DD
> **Tester**: [Name]
> **Environment**: [Local / Staging / Production]
> **Backend Version**: [git commit or tag]

---

## Test Environment Setup

### Agents Deployed
- [ ] process-echo
- [ ] process-worker
- [ ] process-failer

### Backend Status
- [ ] Backend running
- [ ] API accessible at http://localhost:8000
- [ ] Database initialized

---

## Tier 1: Critical Path (4 tests)

| ID | Test | Status | Notes |
|----|------|--------|-------|
| T1.1 | Single agent step | ⬜ | |
| T1.2 | Two sequential steps | ⬜ | |
| T1.3 | Three steps with dependencies | ⬜ | |
| T1.4 | Step with structured output | ⬜ | |

### T1.1 - Single Agent Step
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Steps completed**: /1
- **Output verified**: ⬜
- **Notes**:

### T1.2 - Two Sequential Steps
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Template substitution worked**: ⬜
- **Notes**:

### T1.3 - Three Steps with Dependencies
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Dependency order correct**: ⬜
- **Notes**:

### T1.4 - Structured Output
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Nested paths worked**: ⬜
- **Notes**:

---

## Tier 2: Conditional Logic (4 tests)

| ID | Test | Status | Notes |
|----|------|--------|-------|
| T2.1 | Exclusive gateway (XOR) | ⬜ | |
| T2.2 | Gateway with default route | ⬜ | |
| T2.3 | Parallel execution (fork/join) | ⬜ | |
| T2.4 | Conditional skip | ⬜ | |

### T2.1 - Exclusive Gateway
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Tested routes**: high / medium / low
- **Correct route taken**: ⬜
- **Notes**:

### T2.2 - Gateway Default
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Default route triggered**: ⬜
- **Notes**:

### T2.3 - Parallel Execution
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Branches ran in parallel**: ⬜ (check timestamps)
- **Join waited for all**: ⬜
- **Notes**:

### T2.4 - Conditional Skip
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Step skipped when condition false**: ⬜
- **Downstream still ran**: ⬜
- **Notes**:

---

## Tier 3: Human Approval (4 tests)

| ID | Test | Status | Notes |
|----|------|--------|-------|
| T3.1 | Approval - approved | ⬜ | |
| T3.2 | Approval - rejected | ⬜ | |
| T3.3 | Approval timeout | ⬜ | |
| T3.4 | Approval with artifacts | ⬜ | |

### T3.1 - Approval Approved
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Paused at approval**: ⬜
- **Continued after approve**: ⬜
- **Approval metadata available**: ⬜
- **Notes**:

### T3.2 - Approval Rejected
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Rejection path taken**: ⬜
- **Process completed (not failed)**: ⬜
- **Notes**:

### T3.3 - Approval Timeout
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Timeout triggered**: ⬜
- **on_timeout action worked**: ⬜
- **Notes**:

### T3.4 - Approval with Artifacts
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Artifacts visible in approval**: ⬜
- **Notes**:

---

## Tier 4: Error Handling (5 tests)

| ID | Test | Status | Notes |
|----|------|--------|-------|
| T4.1 | Agent returns error | ⬜ | |
| T4.2 | Agent timeout | ⬜ | |
| T4.3 | Retry policy works | ⬜ | |
| T4.4 | Skip on error | ⬜ | |
| T4.5 | Cancel running execution | ⬜ | |

### T4.1 - Agent Error
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Error propagated to step**: ⬜
- **Execution status FAILED**: ⬜
- **Error message captured**: ⬜
- **Notes**:

### T4.2 - Agent Timeout
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Timeout triggered at ~15s**: ⬜
- **Error code is TIMEOUT**: ⬜
- **Notes**:

### T4.3 - Retry Policy
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Failed attempts**: /2
- **Final attempt succeeded**: ⬜
- **Backoff delays observed**: ⬜
- **Notes**:

### T4.4 - Skip on Error
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Failed step marked SKIPPED**: ⬜
- **Process completed (not failed)**: ⬜
- **Notes**:

### T4.5 - Cancel Execution
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Cancel API worked**: ⬜
- **Execution status CANCELLED**: ⬜
- **Notes**:

---

## Tier 5: Edge Cases (5 tests)

| ID | Test | Status | Notes |
|----|------|--------|-------|
| T5.1 | 10-step sequential | ⬜ | |
| T5.2 | Diamond pattern | ⬜ | |
| T5.3 | Deeply nested expressions | ⬜ | |
| T5.4 | Concurrent executions (3x) | ⬜ | |
| T5.5 | Recovery after backend restart | ⬜ | |

### T5.1 - Ten Step Chain
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **All 10 steps completed**: ⬜
- **Total execution time**: 
- **Notes**:

### T5.2 - Diamond Pattern
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Both diamonds executed correctly**: ⬜
- **Parallel branches verified**: ⬜
- **Notes**:

### T5.3 - Nested Expressions
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Deep paths resolved**: ⬜
- **No expression errors**: ⬜
- **Notes**:

### T5.4 - Concurrent Executions
- **Execution IDs**: #1: / #2: / #3: / #4:
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **3 concurrent started**: ⬜
- **4th returned 429**: ⬜
- **Limit status endpoint worked**: ⬜
- **Notes**:

### T5.5 - Recovery Test
- **Execution ID**: 
- **Status**: ⬜ Pass / ⬜ Fail / ⬜ Skip
- **Backend restarted during execution**: ⬜
- **Recovery service resumed**: ⬜
- **Process completed after recovery**: ⬜
- **Notes**:

---

## Summary

| Tier | Passed | Failed | Skipped | Target |
|------|--------|--------|---------|--------|
| Tier 1 | /4 | | | 4/4 (blocking) |
| Tier 2 | /4 | | | 3/4 |
| Tier 3 | /4 | | | 2/4 |
| Tier 4 | /5 | | | 3/5 |
| Tier 5 | /5 | | | 2/5 |
| **Total** | **/22** | | | **14/22** |

---

## Bugs Discovered

### Bug #1: [Title]
- **Test**: T?.?
- **Severity**: Critical / High / Medium / Low
- **Description**:
- **Steps to reproduce**:
- **Expected**:
- **Actual**:
- **Screenshots/Logs**:

### Bug #2: [Title]
...

---

## Observations

### Performance
- 

### UX Issues
- 

### Architecture Concerns
- 

### Recommended Improvements
- 

---

## Next Steps
- [ ] 
- [ ] 
- [ ] 
