# Error Handling

Learn how to build resilient processes that handle failures gracefully.

## Understanding Failures

Processes can fail at different levels:

| Level | Example | Impact |
|-------|---------|--------|
| **Step** | Agent timeout, invalid output | Single step fails |
| **Process** | Unhandled step failure | Entire execution fails |
| **System** | Network issues, service down | Multiple processes affected |

---

## Automatic Retry

Configure steps to automatically retry on failure.

### Basic Retry

```yaml
- id: api-call
  type: agent_task
  agent: api-handler
  message: Fetch data from external API
  timeout: 2m
  retry:
    max_attempts: 3
    delay: 30s
```

### Exponential Backoff

For rate-limited APIs, use exponential backoff:

```yaml
- id: rate-limited-api
  type: agent_task
  retry:
    max_attempts: 5
    delay: 10s
    backoff: exponential  # 10s, 20s, 40s, 80s, 160s
```

### Retry Fields

| Field | Type | Description |
|-------|------|-------------|
| `max_attempts` | number | Total attempts including first try |
| `delay` | duration | Wait time between attempts |
| `backoff` | string | `linear` (default) or `exponential` |

---

## Timeouts

Every step should have an appropriate timeout.

### Step Timeouts

```yaml
- id: quick-task
  timeout: 30s  # Fast operations

- id: analysis
  timeout: 10m  # Complex processing

- id: human-review
  type: human_approval
  timeout: 48h  # Human approval
  timeout_action: skip
```

### Timeout Actions (Approval Steps)

What happens when an approval times out:

| Action | Behavior |
|--------|----------|
| `skip` | Skip the step, continue process |
| `approve` | Auto-approve and continue |
| `reject` | Fail the step and process |

```yaml
- id: optional-review
  type: human_approval
  timeout: 4h
  timeout_action: skip  # Continue without approval
```

---

## Error States

### Step States

| State | Meaning |
|-------|---------|
| `PENDING` | Waiting to start |
| `RUNNING` | Currently executing |
| `COMPLETED` | Finished successfully |
| `FAILED` | Encountered error |
| `SKIPPED` | Skipped by gateway or timeout |
| `CANCELLED` | Manually cancelled |

### Process States

| State | Meaning |
|-------|---------|
| `PENDING` | Queued, not started |
| `RUNNING` | At least one step running |
| `PAUSED` | Waiting for human approval |
| `COMPLETED` | All steps finished |
| `FAILED` | A step failed |
| `CANCELLED` | User cancelled execution |

---

## Handling Step Failures

### Default Behavior

By default, a failed step fails the entire process.

### Continue on Failure (via Gateway)

Use gateways to handle failures gracefully:

```yaml
steps:
  - id: risky-operation
    type: agent_task
    message: Try risky operation

  - id: check-result
    type: gateway
    depends_on: [risky-operation]
    conditions:
      - expression: "{{steps.risky-operation.status}} == 'COMPLETED'"
        next: success-path
      - default: true
        next: fallback-path

  - id: success-path
    depends_on: [check-result]
    message: Use the successful result

  - id: fallback-path
    depends_on: [check-result]
    message: Use fallback approach
```

---

## Error Information

Access error details in subsequent steps or conditions:

```yaml
# Check if a step failed
{{steps.risky-step.status}}  # "FAILED"

# Get error message (if available)
{{steps.risky-step.error}}
```

---

## Compensation Pattern

When a failure requires cleanup or rollback:

```yaml
steps:
  # Main workflow
  - id: create-resource
    type: agent_task
    message: Create cloud resource

  - id: configure-resource
    type: agent_task
    depends_on: [create-resource]
    message: Configure the resource

  - id: check-configure
    type: gateway
    depends_on: [configure-resource]
    conditions:
      - expression: "{{steps.configure-resource.status}} == 'COMPLETED'"
        next: finalize
      - default: true
        next: rollback

  # Success path
  - id: finalize
    depends_on: [check-configure]
    message: Finalize setup

  # Compensation path
  - id: rollback
    depends_on: [check-configure]
    message: Delete the resource created in step 1
```

---

## Monitoring & Alerting

### Execution Dashboard

The Process Dashboard shows:
- Failed executions count
- Failure rate trends
- Most common failure points

### Email Notifications (Coming Soon)

Configure notifications for:
- Process failures
- Approval timeouts
- Long-running executions

---

## Best Practices

### 1. Set Realistic Timeouts

Consider:
- Agent response time
- Network latency
- External API limits

```yaml
# Too aggressive
timeout: 10s  # Risk: normal operations timeout

# Too generous
timeout: 24h  # Risk: stuck processes go unnoticed

# Just right
timeout: 5m   # Allows for normal variance + some buffer
```

### 2. Retry Transient Failures

Good candidates for retry:
- Network timeouts
- Rate limit errors
- Temporary service unavailability

Poor candidates:
- Validation errors
- Authentication failures
- Logic errors

### 3. Use Human Checkpoints

For critical workflows, add approval steps before irreversible actions:

```yaml
- id: review-before-delete
  type: human_approval
  title: Confirm Deletion
  description: |
    About to delete: {{input.resource_name}}

    This cannot be undone. Approve to proceed.
```

### 4. Log Important Context

Include context in agent messages to help diagnose failures:

```yaml
message: |
  Processing request ID: {{input.request_id}}
  User: {{input.user_email}}
  Action: Delete account
```

### 5. Test Failure Scenarios

Manually test:
- What happens when an agent times out?
- What happens when input is invalid?
- What happens when dependencies fail?

---

## Debugging Failed Executions

### 1. Check Execution Timeline

View the execution detail page to see:
- Which step failed
- Step execution times
- Error messages

### 2. Review Step Outputs

Each step's output is preserved, even on failure:
- Agent responses
- Error details
- Partial results

### 3. Check Agent Logs

If an agent_task fails, check the agent's logs:
- Agent Activity panel
- Full execution history

### 4. Validate Process Definition

Run validation to check for:
- YAML syntax errors
- Invalid references
- Missing dependencies

## Related

- [YAML Schema Reference](./yaml-schema)
- [Understanding Step Types](/processes/docs/getting-started/step-types)
