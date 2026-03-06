# Common Errors

Solutions for frequently encountered issues when working with processes.

## Validation Errors

### "Step ID 'x' is not defined"

**Cause:** A `depends_on` reference points to a step that doesn't exist.

**Solution:**
```yaml
# Wrong - step-a doesn't exist
- id: step-b
  depends_on: [step-a]  # Error!

# Correct - define the dependency
- id: step-a
  type: agent_task
  ...

- id: step-b
  depends_on: [step-a]  # ✓ Now valid
```

### "Circular dependency detected"

**Cause:** Steps form a dependency loop (A → B → C → A).

**Solution:** Review your `depends_on` chains and remove the cycle:

```yaml
# Wrong - circular dependency
- id: a
  depends_on: [c]
- id: b
  depends_on: [a]
- id: c
  depends_on: [b]  # Creates A → B → C → A cycle!

# Correct - linear flow
- id: a
  # No dependencies - starts first
- id: b
  depends_on: [a]
- id: c
  depends_on: [b]
```

### "Agent 'x' not found"

**Cause:** The specified agent doesn't exist or has a typo.

**Solution:**
1. Check agent name is spelled correctly (case-sensitive)
2. Verify agent exists in the Agents page
3. Ensure agent is created before publishing the process

```yaml
# Agent names are case-sensitive
agent: my-agent    # Correct
agent: My-Agent    # Different agent!
agent: MY-AGENT    # Different agent!
```

### "Invalid cron expression"

**Cause:** The schedule trigger has an invalid cron pattern.

**Solution:** Use a valid 5-field cron expression:

```yaml
# Wrong
cron: "every hour"
cron: "0 9"  # Missing fields

# Correct
cron: "0 * * * *"    # Every hour
cron: "0 9 * * *"    # Daily at 9 AM
```

---

## Runtime Errors

### Step Timeout

**Symptom:** Step shows "FAILED" with timeout error.

**Causes:**
- Timeout too short for the operation
- Agent is slow or unresponsive
- External API is slow

**Solutions:**

1. **Increase timeout:**
```yaml
- id: slow-operation
  timeout: 15m  # Increase from default
```

2. **Add retry logic:**
```yaml
- id: flaky-step
  timeout: 5m
  retry:
    max_attempts: 3
    delay: 30s
```

3. **Check agent status** in the Agents page

### Agent Not Responding

**Symptom:** Step stuck in "RUNNING" or times out.

**Causes:**
- Agent container stopped
- Agent overloaded with tasks
- Network issues

**Solutions:**

1. Check agent status in **Agents** page
2. View agent logs for errors
3. Restart the agent if needed
4. Consider load balancing across multiple agents

### Variable Not Resolved

**Symptom:** You see literal `{{variable}}` in outputs instead of values.

**Causes:**
- Typo in variable path
- Step hasn't completed yet
- Referenced step was skipped

**Solutions:**

1. **Check spelling:** Variable paths are case-sensitive
```yaml
# Wrong
{{steps.Research.output}}  # Capital R

# Correct
{{steps.research.output}}
```

2. **Verify dependencies:** The referenced step must complete first
```yaml
- id: use-result
  depends_on: [research]  # Must include the dependency!
  message: Using {{steps.research.output}}
```

3. **Use defaults for optional steps:**
```yaml
{{steps.optional.output | default:"No data"}}
```

### Human Approval Timeout

**Symptom:** Approval step times out without action.

**Cause:** No one approved/rejected within the timeout period.

**Solutions:**

1. **Extend timeout:**
```yaml
- id: review
  type: human_approval
  timeout: 48h  # Give more time
```

2. **Set appropriate timeout_action:**
```yaml
timeout_action: skip    # Continue without approval
timeout_action: approve # Auto-approve
timeout_action: reject  # Fail the process
```

3. **Set up notifications** to alert reviewers (coming soon)

---

## Process Execution Issues

### Process Stuck in PENDING

**Symptom:** Execution shows PENDING but never starts.

**Causes:**
- Execution queue is full
- Scheduler service issues
- Resource constraints

**Solutions:**

1. Check **Dashboard** for queue status
2. Review system logs
3. Verify scheduler service is running

### All Steps Running in Parallel

**Symptom:** Steps that should be sequential run at the same time.

**Cause:** Missing `depends_on` declarations.

**Solution:** Add explicit dependencies:
```yaml
steps:
  - id: first
    ...

  - id: second
    depends_on: [first]  # Won't start until 'first' completes

  - id: third
    depends_on: [second]
```

### Gateway Always Takes Default Path

**Symptom:** Conditions never match, always goes to default.

**Causes:**
- Condition expression has wrong syntax
- Variable type mismatch
- Data structure different than expected

**Solutions:**

1. **Check data types:**
```yaml
# If output.count is a string "10", not number 10
expression: "{{steps.x.output.count}} == 10"      # Fails
expression: "{{steps.x.output.count}} == '10'"    # Works
```

2. **Debug by logging output:**
```yaml
- id: debug
  type: agent_task
  message: |
    Debug info:
    Value: {{steps.x.output.status}}
    Type: (check in execution detail)
```

3. **Simplify conditions:**
```yaml
# Start simple, then add complexity
expression: "{{steps.x.output.success}} == true"
```

---

## Publishing Issues

### Can't Publish Draft

**Symptom:** Publish button is disabled or fails.

**Causes:**
- Validation errors exist
- Required fields missing
- Agent references invalid

**Solutions:**

1. Run **Validate** and fix all errors
2. Ensure all agent names reference existing agents
3. Check for valid triggers configuration

### Can't Edit Published Process

**Symptom:** Save button doesn't appear for published process.

**Cause:** Published processes are immutable (by design).

**Solution:** Create a new version:
1. Click **New Version** button
2. Edit the new draft
3. Publish when ready

---

## Best Practices to Avoid Errors

### 1. Validate Often

Run validation after every change, not just before publishing.

### 2. Start Simple

Begin with a 2-3 step process, then add complexity:
```yaml
# Start with this
steps:
  - id: step-1
    ...
  - id: step-2
    depends_on: [step-1]

# Then expand
```

### 3. Use Descriptive IDs

Makes debugging easier:
```yaml
# Hard to debug
steps:
  - id: s1
  - id: s2
  - id: s3

# Easy to debug
steps:
  - id: fetch-data
  - id: analyze-data
  - id: generate-report
```

### 4. Test with Manual Trigger First

Before setting up schedules or webhooks:
1. Use manual trigger
2. Test with sample input
3. Verify all steps complete
4. Then enable other triggers

### 5. Monitor Early Executions

Watch the first few automated runs to catch issues early.

## Getting Help

If you're stuck:

1. Check the **Execution Detail** page for error messages
2. Review **Agent Logs** for more context
3. Verify your **Process YAML** against the schema reference
4. Test individual steps in isolation

## Related

- [Error Handling](../reference/error-handling)
- [YAML Schema Reference](../reference/yaml-schema)
- [Understanding Step Types](../getting-started/step-types)
