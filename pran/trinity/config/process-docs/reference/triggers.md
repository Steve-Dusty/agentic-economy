# Triggers

Triggers define how and when a process starts. A process can have multiple triggers, allowing different ways to initiate the same workflow.

## Trigger Types

| Type | Description | Use Case |
|------|-------------|----------|
| `manual` | Started via UI or API | Interactive workflows, testing |
| `webhook` | HTTP POST request | External integrations, CI/CD |
| `schedule` | Cron-based timing | Reports, maintenance, monitoring |

---

## Manual Trigger

The simplest trigger type. Users start the process via:
- The "Run" button in the UI
- The API endpoint

### Configuration

```yaml
triggers:
  - type: manual
    id: manual-start
```

### Starting via API

```bash
POST /api/processes/{process-id}/execute
Content-Type: application/json

{
  "input": {
    "topic": "AI trends",
    "depth": 2
  }
}
```

### Response

```json
{
  "execution_id": "exec_abc123",
  "status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## Webhook Trigger

Allows external systems to start processes via HTTP.

### Configuration

```yaml
triggers:
  - type: webhook
    id: github-push
```

### Webhook URL

After publishing your process, the webhook URL is:

```
POST /api/triggers/webhook/{trigger-id}
```

The `{trigger-id}` is the ID you specified in the YAML (e.g., `github-push`).

### Calling the Webhook

```bash
curl -X POST https://your-trinity.com/api/triggers/webhook/github-push \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "my-repo",
    "branch": "main",
    "commit": "abc123"
  }'
```

### Request Body

The entire JSON body is available as `{{input}}` in your process:

```yaml
steps:
  - id: process-commit
    type: agent_task
    message: |
      New commit on {{input.repository}}
      Branch: {{input.branch}}
      Commit: {{input.commit}}
```

### Authentication

Webhooks can be secured using:
- **API Keys** — Include in header: `X-API-Key: your-key`
- **Webhook Secrets** — HMAC signature verification (coming soon)

---

## Schedule Trigger

Run processes automatically on a schedule using cron expressions.

### Configuration

```yaml
triggers:
  - type: schedule
    id: daily-report
    cron: "0 9 * * *"
    timezone: "America/New_York"  # Optional
    input:                        # Optional: Static input
      report_type: "daily"
```

### Cron Expression Format

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6, Sun = 0)
│ │ │ │ │
* * * * *
```

### Common Schedules

| Schedule | Cron | Description |
|----------|------|-------------|
| Every hour | `0 * * * *` | On the hour |
| Every 30 min | `*/30 * * * *` | At :00 and :30 |
| Daily 9 AM | `0 9 * * *` | Once per day |
| Monday 9 AM | `0 9 * * 1` | Weekly |
| 1st of month | `0 9 1 * *` | Monthly |
| Weekdays 9 AM | `0 9 * * 1-5` | Mon-Fri |

### Static Input

Provide fixed input data for scheduled runs:

```yaml
triggers:
  - type: schedule
    id: weekly-backup
    cron: "0 2 * * 0"  # Sunday 2 AM
    input:
      backup_type: "full"
      retention_days: 30
```

### Timezone

By default, schedules use UTC. Specify a timezone:

```yaml
triggers:
  - type: schedule
    id: market-open
    cron: "0 9 * * 1-5"
    timezone: "America/New_York"
```

### Managing Schedules

View and manage schedules in:
- **Dashboard** → Active Schedules
- **Process Detail** → Trigger Info tab

You can:
- Pause/resume schedules
- View next run time
- See execution history

---

## Multiple Triggers

A process can have multiple triggers:

```yaml
triggers:
  # Start manually for testing
  - type: manual
    id: manual-test

  # External systems via webhook
  - type: webhook
    id: api-trigger

  # Automated daily run
  - type: schedule
    id: daily-automation
    cron: "0 6 * * *"
```

All triggers start the same process but may provide different input.

---

## Input Handling

Different triggers provide input differently:

### Manual Trigger
- Input provided in the "Execute" dialog or API body

### Webhook Trigger
- Input is the entire request body

### Schedule Trigger
- Input from `input:` field in YAML
- Or empty if not specified

### Checking Trigger Source

```yaml
# You can identify which trigger started the execution
# (if needed for conditional logic)
steps:
  - id: check-source
    type: agent_task
    message: |
      Process triggered by: {{trigger.type}}
      Trigger ID: {{trigger.id}}
```

---

## Best Practices

### 1. Name Triggers Descriptively

```yaml
# Good
triggers:
  - type: webhook
    id: github-pull-request
  - type: schedule
    id: nightly-cleanup

# Avoid
triggers:
  - type: webhook
    id: wh1
```

### 2. Use Appropriate Timeouts

Scheduled processes should complete well before the next run:

```yaml
# If running every hour, don't let it run longer than ~50 minutes
steps:
  - id: long-task
    timeout: 45m
```

### 3. Handle Missing Input

For schedules with static input, consider defaults elsewhere:

```yaml
steps:
  - id: process
    message: |
      Type: {{input.report_type | default:"standard"}}
```

### 4. Test Before Scheduling

1. First test with manual trigger
2. Verify the process completes successfully
3. Then enable the schedule trigger

---

## Troubleshooting

### Schedule Not Running

1. Check process is **published** (not draft)
2. Verify cron expression is valid
3. Check timezone setting
4. View scheduler logs in Dashboard

### Webhook Not Responding

1. Verify process is published
2. Check trigger ID matches URL
3. Ensure request body is valid JSON
4. Check API key if required

### Duplicate Executions

If a process runs multiple times:
- Check for multiple triggers with same schedule
- Verify webhook isn't being called multiple times

## Related

- [YAML Schema Reference](./yaml-schema)
- [Variable Interpolation](./variables)
