# Phase 10: Error Handling & Recovery (test-error)

> **Purpose**: Validate error detection, logging, and recovery mechanisms
> **Duration**: ~10 minutes
> **Assumes**: Phase 9 PASSED (file operations working, test-error running)
> **Output**: Error handling and recovery verified

---

## Background

**Resilience & Recovery**:
- Agents detect errors and continue execution
- Errors logged with context for debugging
- Cascading failures prevented
- Manual retry mechanisms available

---

## Test: Error Detection

### Step 1: Navigate to test-error
**Action**:
- Go to http://localhost/agents
- Click test-error
- Wait for detail page to load

**Expected**:
- [ ] Agent detail page loads
- [ ] Chat tab active
- [ ] Status: "Running" (green)
- [ ] Context: 0% (fresh agent)

---

### Step 2: Trigger Invalid Operation
**Action**:
- Type: "process invalid command"
- Press Enter
- Wait 5 seconds

**Expected Response**:
```
Error detected
Error Type: InvalidCommandError
Message: Unknown command: invalid
Timestamp: [current time]
Status: handled
Action: Logged and continued
```

**Verify**:
- [ ] Error detected
- [ ] Error type shown
- [ ] Error message clear
- [ ] Handling described
- [ ] Agent continues operating

---

### Step 3: Trigger Missing Required Parameter
**Action**:
- Type: "calculate without numbers"
- Press Enter
- Wait 5 seconds

**Expected Response**:
```
Error detected
Error Type: MissingParameterError
Message: Required parameter 'numbers' not provided
Timestamp: [current time]
Status: handled
Suggestion: Please provide numbers to calculate
```

**Verify**:
- [ ] Parameter validation error caught
- [ ] Clear error message
- [ ] Suggestion provided
- [ ] Agent recovers

---

### Step 4: Trigger API Timeout
**Action**:
- Type: "call external service with 30 second timeout"
- Press Enter
- **Wait 35 seconds** (timeout will occur)

**Expected Response**:
```
Error detected
Error Type: TimeoutError
Message: External service did not respond within 30 seconds
Timestamp: [current time]
Timeout: 30s
Status: handled
Action: Request cancelled, continuing with cached data
```

**Verify**:
- [ ] Timeout detected
- [ ] Timeout duration shown
- [ ] Graceful handling (no crash)
- [ ] Fallback to cached data if available
- [ ] Agent continues

---

## Test: Error Logging

### Step 5: Check Error Log
**Action**:
- Type: "show recent errors"
- Press Enter
- Wait 5 seconds

**Expected Response**:
```
Recent Errors:
1. InvalidCommandError at [time]
   - "Unknown command: invalid"
   - Handled: Logged

2. MissingParameterError at [time]
   - "Required parameter 'numbers' not provided"
   - Handled: Suggestion provided

3. TimeoutError at [time]
   - "External service timeout (30s)"
   - Handled: Used cached data

Total errors: 3
Unhandled errors: 0
```

**Verify**:
- [ ] All errors logged
- [ ] Timestamps correct
- [ ] Error types clear
- [ ] Handling status shown
- [ ] Count accurate

---

## Test: Cascading Failure Prevention

### Step 6: Trigger Dependent Operation
**Action**:
- Type: "call service A, then service B, then service C (all required)"
- Press Enter
- **Wait 40 seconds**

**Expected Response**:
```
Attempting chain:
  Service A: OK ✓
  Service B: ERROR (timeout)
  Chain halted

Cascading failure prevented
Remaining operations (C) not attempted
Error context: Service B unavailable
Status: handled
```

**Verify**:
- [ ] First service succeeds
- [ ] Second service fails
- [ ] Chain stops (doesn't crash)
- [ ] Dependent operations not executed
- [ ] Clear error context
- [ ] No cascading failures

---

### Step 7: Check Partial Results
**Action**:
- Type: "show results from last chain"
- Press Enter
- Wait 5 seconds

**Expected Response**:
```
Chain Results:
- Step 1 (Service A): SUCCESS
  Output: data from A
- Step 2 (Service B): FAILED
  Error: Timeout
- Step 3 (Service C): SKIPPED
  Reason: Dependency failed

Partial completion: 1/3 steps
```

**Verify**:
- [ ] Successful steps shown
- [ ] Failed step documented
- [ ] Skipped steps explained
- [ ] Completion percentage shown
- [ ] All context preserved

---

## Test: Recovery and Retry

### Step 8: Manual Retry Operation
**Action**:
- Type: "retry last failed operation (service B)"
- Press Enter
- **Wait 35 seconds**

**Expected Response**:
```
Retrying: Service B
Retry attempt: 1/3
Status: timeout again
Waiting 5 seconds before next retry...

Retrying: Service B
Retry attempt: 2/3
Status: SUCCESS ✓

Chain can now continue
Attempting Service C...
```

**Verify**:
- [ ] Retry mechanism works
- [ ] Backoff implemented (5 second wait)
- [ ] Retry count tracked
- [ ] Success after retry shown
- [ ] Dependent operations can proceed

---

## Test: Activity Panel Error Tracking

### Step 9: Check Activity Panel
**Action**:
- Scroll to Activity section
- Look for error handling records

**Expected**:
- [ ] Error detection tool calls
- [ ] Error logging tool calls
- [ ] Retry attempt tool calls
- [ ] Each with error details
- [ ] No "success" for failures

**Verify**:
- [ ] All errors recorded in activity
- [ ] Error context preserved
- [ ] Retry attempts shown
- [ ] Final resolution shown

---

## Test: Context Growth with Errors

### Step 10: Check Context After Error Handling
**Action**:
- Look at context % in agent detail page header
- Compare to Phase 9 context level

**Expected**:
- [ ] Context % increased from Phase 9
- [ ] Error handling adds context (error messages, logging)
- [ ] Progress bar filled accordingly
- [ ] No agent exceeds 200K limit

**Verify**:
- [ ] Context grows even with errors
- [ ] Error context preserved
- [ ] No data loss

---

## Test: Persistence of Error State

### Step 11: Refresh Page and Check Error History
**Action**:
- Navigate away: go to agents list
- Return to test-error agent
- Type: "show error history"
- Press Enter

**Expected**:
- [ ] Error history still available
- [ ] All 3 errors from earlier visible
- [ ] Same timestamps
- [ ] Same error messages

**Verify**:
- [ ] Error history persisted
- [ ] State survived page refresh
- [ ] No data loss of error records

---

## Critical Validations

### Error Does Not Crash Agent
**Validation**: Agent continues after every error

```bash
# Check agent still running
docker ps | grep agent-test-error
# Should show: agent-test-error is still running
```

### Error Logging Completeness
**Validation**: All errors logged to system

```bash
# Check error logs in container
docker logs agent-test-error | grep -i "error\|exception\|failed"
```

Expected: Every error appears in logs

### Timeout Handling
**Validation**: Requests don't hang indefinitely

- [ ] 30-second timeout occurs at 30 seconds (not 35+)
- [ ] Response received immediately after timeout
- [ ] No partial/corrupt data

---

## Success Criteria

Phase 10 is **PASSED** when:
- ✅ Invalid command error detected and handled
- ✅ Missing parameter error caught with suggestion
- ✅ API timeout error handled gracefully
- ✅ Error log shows all errors with timestamps
- ✅ Cascading failures prevented (chain stops)
- ✅ Partial results preserved from failed chain
- ✅ Manual retry works and succeeds on second attempt
- ✅ Activity panel records all error handling
- ✅ Context % increased with error handling
- ✅ Error history persisted across refresh
- ✅ Agent never crashes or becomes unresponsive

---

## Troubleshooting

**Agent becomes unresponsive**:
- This is a FAILED test
- Error handling not working
- Check logs: `docker logs agent-test-error`
- Agent may need restart

**Errors not being logged**:
- Check error log endpoint: `curl http://localhost:8000/api/agents/test-error/errors`
- Backend may not have error logging
- Check backend logs: `docker logs backend`

**Timeout not occurring at 30 seconds**:
- Timeout value may be misconfigured
- Check agent config
- May need to wait longer (check actual timeout value)

**Retry mechanism not working**:
- Check test-error agent has retry tool
- Verify retry parameters in chat response
- May require manual workaround for this phase

**Error history lost after refresh**:
- Database persistence may be broken
- Check backend: `docker logs backend`
- SQLite database may not be persisting errors

---

## Next Phase

Once Phase 10 is **PASSED**, proceed to:
- **Phase 11**: Multi-Agent Dashboard (all 3 agents)

---

**Status**: 🟢 Error handling & recovery validated
**Last Updated**: 2025-12-09
