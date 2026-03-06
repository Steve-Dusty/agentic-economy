# Phase 8: Execution Queue & Concurrency (test-queue)

> **Purpose**: Validate queue management, concurrency handling, and rate limiting
> **Duration**: ~15 minutes
> **Assumes**: Phase 7 PASSED (scheduling working, test-queue running)
> **Output**: Queue system and concurrency verified

---

## Background

**Execution Queue**:
- Multiple requests queued and executed serially
- Rate limiting (HTTP 429) handled gracefully
- Queue position tracking
- Retry logic for failed executions

---

## Test: Queue Operations

### Step 1: Navigate to test-queue
**Action**:
- Go to http://localhost/agents
- Click test-queue
- Wait for detail page to load

**Expected**:
- [ ] Agent detail page loads
- [ ] Chat tab active
- [ ] Status: "Running" (green)
- [ ] Context: 0% (fresh agent)

---

### Step 2: Submit Multiple Jobs
**Action**:
- Type: "queue job 1: process data batch A"
- Press Enter
- Immediately type: "queue job 2: process data batch B"
- Press Enter
- Immediately type: "queue job 3: process data batch C"
- Press Enter
- Wait 10 seconds

**Expected Response (for each)**:
```
Job queued successfully
Job ID: job-[uuid]
Position in queue: [1-3]
Estimated wait: [X seconds]
Status: queued
```

**Verify**:
- [ ] All 3 jobs queued
- [ ] Job IDs unique
- [ ] Queue positions correct (1, 2, 3)
- [ ] Status: queued (not executing yet)

---

### Step 3: Check Queue Status
**Action**:
- Type: "show queue status"
- Press Enter
- Wait 5 seconds

**Expected Response**:
```
Queue Status:
- Total jobs: 3
- Executing: 1 (job-1, time: 0:05)
- Queued: 2
  - job-2 (position 1, wait: 15 sec)
  - job-3 (position 2, wait: 30 sec)

Current throughput: 1 job/30 sec
```

**Verify**:
- [ ] One job executing (job-1)
- [ ] Two jobs queued (job-2, job-3)
- [ ] Queue positions accurate
- [ ] Estimated wait times reasonable
- [ ] Throughput shown

---

## Test: Sequential Execution

### Step 4: Monitor Job Completion
**Action**:
- Wait 30 seconds for jobs to execute sequentially
- Monitor chat for completion messages

**Expected Sequence**:
```
Job 1 completed (time: 0:32)
Status: completed
Starting Job 2...

Job 2 completed (time: 0:28)
Status: completed
Starting Job 3...

Job 3 completed (time: 0:31)
Status: completed
```

**Verify**:
- [ ] Jobs execute in order (1, 2, 3)
- [ ] No parallel execution
- [ ] Each job duration 25-35 seconds
- [ ] Total time ≈ 90+ seconds (3 jobs * 30 sec)
- [ ] No jobs skipped

---

### Step 5: Check Execution History
**Action**:
- Type: "show job history"
- Press Enter
- Wait 5 seconds

**Expected Response**:
```
Job History:
1. job-1: process data batch A
   Status: completed
   Duration: 0:32
   Output: 500 records processed

2. job-2: process data batch B
   Status: completed
   Duration: 0:28
   Output: 480 records processed

3. job-3: process data batch C
   Status: completed
   Duration: 0:31
   Output: 510 records processed
```

**Verify**:
- [ ] All jobs in history
- [ ] Status shows "completed"
- [ ] Realistic durations shown
- [ ] Results/output logged

---

## Test: Rate Limiting Handling

### Step 6: Submit High-Volume Requests
**Action**:
- Type: "bulk queue 10 jobs rapid fire"
- Press Enter
- Wait 20 seconds

**Expected Response**:
```
Queueing 10 jobs...
Jobs 1-4: queued successfully
Job 5: Received HTTP 429 (Rate Limited)
  - Waiting 30 seconds before retry
Job 6: Waiting in queue...
...
All jobs queued (took 1:45)
```

**Verify**:
- [ ] System receives 429 response from external service
- [ ] System handles gracefully (doesn't crash)
- [ ] Automatic retry after backoff
- [ ] Queue continues processing
- [ ] User informed of rate limiting

---

### Step 7: Verify Retry Logic
**Action**:
- Wait 2-3 minutes for all jobs to complete
- Type: "show jobs that were rate limited"
- Press Enter

**Expected Response**:
```
Rate-limited jobs (retried):
- job-5: Retried at [time], completed
- job-7: Retried at [time], completed

All retries successful
```

**Verify**:
- [ ] Failed jobs identified
- [ ] Retry mechanism executed
- [ ] All jobs eventually completed
- [ ] Retry times logged

---

## Test: Activity Panel Tracking

### Step 8: Check Activity Panel
**Action**:
- Scroll to Activity section
- Look for queue-related tool calls

**Expected**:
- [ ] `queue_job` tool call (multiple)
- [ ] `get_queue_status` tool call
- [ ] `handle_rate_limit` tool call
- [ ] `retry_job` tool calls

**Verify**:
- [ ] Tool calls recorded for each operation
- [ ] Parameters show job details
- [ ] Retry timing shown
- [ ] Rate limiting events logged

---

## Test: Context Growth with Queue Execution

### Step 9: Check Context After Queue Processing
**Action**:
- Look at context % in agent detail page header
- Compare to Phase 7 context level

**Expected**:
- [ ] Context % significantly increased
- [ ] Large increase due to 10+ jobs processed
- [ ] Progress bar filled (yellow or orange)
- [ ] No agent exceeds 200K limit

**Verify**:
- [ ] Context grows with each job
- [ ] Substantial growth from queue processing
- [ ] Color progression: green → yellow → orange

---

## Test: Queue Persistence

### Step 10: Refresh Page and Check State
**Action**:
- Navigate away: go to agents list
- Return to test-queue agent
- Wait 2 seconds for load

**Expected**:
- [ ] Completed jobs still in history
- [ ] Job history shows all jobs with status
- [ ] Queue empty (all executed)
- [ ] Job IDs same as before refresh

**Verify**:
- [ ] History persisted to database
- [ ] State survived page refresh
- [ ] No data loss of completed jobs

---

## Critical Validations

### Queue Ordering
**Validation**: Jobs execute FIFO (First-In-First-Out)

```bash
# Check queue logs
docker logs agent-test-queue | grep -i "job\|queue\|execute" | grep -E "job-[0-9]"
```

Expected: Job IDs in strictly ascending order in execution logs

### Rate Limit Recovery
**Validation**: System recovers from HTTP 429

- [ ] Receives 429 response
- [ ] Implements exponential backoff
- [ ] Retries successfully
- [ ] No data loss from rate-limited jobs

### Queue Capacity
**Validation**: Queue can handle 10+ jobs without overflow

- [ ] All 10 jobs queued
- [ ] No "queue full" errors
- [ ] Memory usage reasonable
- [ ] Performance degradation minimal

---

## Success Criteria

Phase 8 is **PASSED** when:
- ✅ 3 initial jobs queued with correct positions
- ✅ Jobs execute sequentially (job-1, then job-2, then job-3)
- ✅ Job history shows all completions
- ✅ Queue status shows accurate positions and wait times
- ✅ 10 jobs bulk-queued successfully
- ✅ HTTP 429 rate limiting handled gracefully
- ✅ Failed jobs retried automatically
- ✅ Context % increased due to queue processing
- ✅ Queue persisted across page refresh
- ✅ FIFO order maintained

---

## Troubleshooting

**Jobs not executing**:
- Check test-queue running: `docker ps | grep test-queue`
- Wait longer (jobs take 25-35 seconds each)
- Check logs: `docker logs agent-test-queue`

**Queue status shows zero jobs**:
- Jobs may have already completed
- Type "show job history" to see past jobs
- Create new jobs with "queue job X" command

**Rate limiting never occurs**:
- System may not be hitting external service
- Bulk queue command may need adjustment
- Check backend logs for external service calls

**Context not growing**:
- Verify Phase 3 context tracking working
- If stuck at 0%, that's known bug (Phase 3)
- Proceed to next phase anyway

**Job lost after page refresh**:
- Completed jobs should persist
- Check backend database: `docker logs backend`
- Verify SQLite connection working

---

## Next Phase

Once Phase 8 is **PASSED**, proceed to:
- **Phase 9**: File Browser (test-files)

---

**Status**: 🟢 Execution queue & concurrency validated
**Last Updated**: 2025-12-09
