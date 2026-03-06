# YAML Schema Reference

Complete reference for process definition YAML files.

## Root Structure

```yaml
name: string           # Required: Process identifier (lowercase, hyphens)
version: string        # Required: Semantic version (e.g., "1.0")
description: string    # Optional: Human-readable description

triggers: []           # Optional: How the process can be started
steps: []              # Required: List of workflow steps
outputs: []            # Optional: What the process returns
```

## Naming Conventions

- **Process name**: lowercase letters, numbers, and hyphens. Examples: `content-review`, `data-pipeline-v2`
- **Step IDs**: Same rules. Must be unique within the process.
- **Agent names**: Must match exactly (case-sensitive) with an existing agent name.

---

## Triggers

Triggers define how a process can be started.

### Manual Trigger

Started via UI button or API call.

```yaml
triggers:
  - type: manual
    id: manual-start
```

### Webhook Trigger

Started by an HTTP POST request.

```yaml
triggers:
  - type: webhook
    id: webhook-trigger
```

**Webhook URL**: `POST /api/triggers/webhook/{trigger-id}`

**Request body** is passed as `{{input}}` to the process.

### Schedule Trigger

Started automatically on a cron schedule.

```yaml
triggers:
  - type: schedule
    id: daily-report
    cron: "0 9 * * *"  # Daily at 9 AM
```

**Common cron patterns:**
| Pattern | Description |
|---------|-------------|
| `0 * * * *` | Every hour |
| `0 9 * * *` | Daily at 9 AM |
| `0 9 * * 1` | Weekly (Monday) at 9 AM |
| `0 9 1 * *` | Monthly (1st) at 9 AM |
| `0 9 * * 1-5` | Weekdays at 9 AM |

---

## Steps

### Common Step Fields

All step types share these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier |
| `name` | string | No | Human-readable name (defaults to id) |
| `type` | string | Yes | Step type: `agent_task`, `human_approval`, `gateway`, `timer` |
| `depends_on` | string[] | No | Step IDs that must complete first |

### Agent Task Step

```yaml
- id: analyze
  name: Analyze Data
  type: agent_task
  agent: analyst             # Required: Agent name
  message: |                  # Required: Prompt to send
    Analyze this: {{input.data}}
  timeout: 10m               # Optional: Max execution time
  retry:                     # Optional: Retry configuration
    max_attempts: 3
    delay: 30s
```

### Human Approval Step

```yaml
- id: manager-review
  type: human_approval
  title: Review Required           # Required: Short title
  description: |                   # Required: What to review
    Please review the analysis:
    {{steps.analyze.output}}
  timeout: 24h                     # Optional: Max wait time
  timeout_action: skip             # Optional: approve|reject|skip
```

### Gateway Step

```yaml
- id: route-decision
  type: gateway
  conditions:
    - expression: "{{steps.triage.output.priority}} == 'high'"
      next: urgent-path
    - expression: "{{steps.triage.output.priority}} == 'medium'"
      next: normal-path
    - default: true
      next: low-priority-path
```

### Timer Step

```yaml
- id: rate-limit-pause
  type: timer
  duration: 30s              # Required: Wait duration
```

---

## Duration Formats

Durations use these suffixes:

| Suffix | Meaning | Example |
|--------|---------|---------|
| `s` | Seconds | `30s` |
| `m` | Minutes | `5m` |
| `h` | Hours | `2h` |
| `d` | Days | `1d` |

Can combine: `1h30m` (1 hour 30 minutes)

---

## Retry Configuration

Configure automatic retries for failed steps:

```yaml
retry:
  max_attempts: 3      # Total attempts (including first)
  delay: 30s           # Wait between attempts
  backoff: exponential # Optional: linear|exponential
```

**Backoff modes:**
- `linear`: Constant delay between retries
- `exponential`: Delay doubles each retry (30s → 60s → 120s)

---

## Outputs

Define what the process returns when complete:

```yaml
outputs:
  - name: summary
    source: "{{steps.summarize.output}}"
  - name: metadata
    source: "{{steps.analyze.output.metadata}}"
```

Outputs are available in:
- Execution detail view
- API response
- Webhook callbacks

---

## Complete Example

```yaml
name: content-review-pipeline
version: "1.0"
description: Review and publish content with human approval

triggers:
  - type: manual
    id: start-review
  - type: webhook
    id: submit-content

steps:
  - id: analyze
    name: Content Analysis
    type: agent_task
    agent: content-analyzer
    message: |
      Analyze this content for quality and issues:
      {{input.content}}
    timeout: 5m

  - id: review-gate
    name: Editorial Review
    type: human_approval
    depends_on: [analyze]
    title: Content Review Required
    description: |
      Analysis: {{steps.analyze.output}}

      Original content: {{input.content}}
    timeout: 48h
    timeout_action: skip

  - id: publish
    name: Publish Content
    type: agent_task
    depends_on: [review-gate]
    agent: publisher
    message: |
      Publish this approved content:
      {{input.content}}
    timeout: 2m

outputs:
  - name: analysis
    source: "{{steps.analyze.output}}"
  - name: publish_result
    source: "{{steps.publish.output}}"
```

## Validation Rules

Trinity validates your YAML for:

1. **Syntax** — Valid YAML structure
2. **Required fields** — All mandatory fields present
3. **Step IDs** — Unique within process
4. **Dependencies** — All `depends_on` references exist
5. **Agents** — Referenced agents exist (warning if stopped)
6. **Circular dependencies** — No step depends on itself (directly or indirectly)

## Next Steps

- [Variable Interpolation](./variables) — Dynamic data in your processes
- [Triggers](./triggers) — Detailed trigger documentation
- [Error Handling](./error-handling) — Handle failures gracefully
