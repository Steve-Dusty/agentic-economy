# Understanding Step Types

Steps are the building blocks of every process. Each step type serves a different purpose in your workflow.

## Overview

| Step Type | Purpose | Use When |
|-----------|---------|----------|
| `agent_task` | Execute work via an AI agent | You need an agent to process, generate, or analyze |
| `human_approval` | Pause for human review | Quality gates, compliance, or decisions needed |
| `gateway` | Make conditional decisions | Branching logic based on previous outputs |
| `timer` | Wait for a duration | Rate limiting, scheduled delays, or coordination |
| `notification` | Send alerts to channels | Notify teams via Slack, email, or other channels |
| `sub_process` | Invoke nested workflows | Reusable process modules, complex compositions |

---

## Agent Task

The most common step type. Sends a message to an AI agent and waits for the response.

### Basic Structure

```yaml
- id: analyze-data
  name: Analyze Data
  type: agent_task
  agent: analyst
  message: |
    Analyze the following data and identify key trends:
    {{input.data}}
  timeout: 10m
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier for the step |
| `type` | Must be `agent_task` |
| `agent` | Name of the agent to execute the task |
| `message` | The prompt/instructions sent to the agent |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `name` | Human-readable name | Same as `id` |
| `depends_on` | List of step IDs that must complete first | `[]` |
| `timeout` | Maximum execution time | `30m` |
| `retry` | Retry configuration on failure | No retry |

### Timeout Format

Timeouts use duration strings:
- `30s` — 30 seconds
- `5m` — 5 minutes
- `1h` — 1 hour
- `1d` — 1 day

### Retry Configuration

```yaml
- id: flaky-api-call
  type: agent_task
  agent: api-agent
  message: Fetch data from external API
  timeout: 2m
  retry:
    max_attempts: 3
    delay: 30s
```

---

## Human Approval

Pauses the process until a human approves or rejects.

### Basic Structure

```yaml
- id: manager-review
  name: Manager Review
  type: human_approval
  depends_on: [draft-report]
  title: Review Report Draft
  description: |
    Please review the draft report:
    {{steps.draft-report.output}}

    Approve to proceed with publication.
  timeout: 24h
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `type` | Must be `human_approval` |
| `title` | Short title shown in approval UI |
| `description` | Detailed description of what to review |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `timeout` | Time to wait before timeout action | `24h` |
| `timeout_action` | What happens on timeout: `approve`, `reject`, or `skip` | `skip` |

### Accessing Approval Decisions

After approval, you can access the decision in subsequent steps:

```yaml
- id: next-step
  depends_on: [manager-review]
  message: |
    The manager {{steps.manager-review.output.decision}}.
    Comments: {{steps.manager-review.output.comments}}
```

---

## Gateway

Makes decisions based on conditions. Routes execution to different paths.

### Basic Structure

```yaml
- id: check-severity
  name: Check Severity
  type: gateway
  depends_on: [triage]
  conditions:
    - expression: "{{steps.triage.output.severity}} == 'high'"
      next: escalate
    - expression: "{{steps.triage.output.severity}} == 'medium'"
      next: standard-handling
    - default: true
      next: archive
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `type` | Must be `gateway` |
| `conditions` | List of condition/next pairs |

### Condition Expressions

Conditions use simple comparison expressions:

```yaml
# Equality
"{{steps.x.output.status}} == 'approved'"

# Numeric comparison
"{{steps.x.output.score}} > 80"

# Contains (for strings/arrays)
"{{steps.x.output.tags}} contains 'urgent'"

# Boolean
"{{steps.x.output.is_valid}} == true"
```

### Default Case

Always include a default condition to handle unexpected values:

```yaml
conditions:
  - expression: "..."
    next: path-a
  - default: true
    next: fallback-path
```

---

## Timer

Pauses execution for a specified duration.

### Basic Structure

```yaml
- id: cooldown
  name: Rate Limit Cooldown
  type: timer
  depends_on: [api-call]
  duration: 1m
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `type` | Must be `timer` |
| `duration` | How long to wait (e.g., `30s`, `5m`, `1h`) |

### Use Cases

1. **Rate Limiting**
   ```yaml
   - id: wait-between-calls
     type: timer
     duration: 2s
   ```

2. **Scheduled Delays**
   ```yaml
   - id: wait-for-processing
     type: timer
     duration: 5m
   ```

3. **Business Hours Wait**
   Combined with gateways to handle time-based logic.

---

## Notification

Sends alerts and messages to external channels like Slack, email, or PagerDuty.

### Basic Structure

```yaml
- id: alert-team
  name: Alert Team
  type: notification
  depends_on: [analysis]
  channels: [slack]
  message: |
    🚨 Analysis Complete

    Results: {{steps.analysis.output.summary}}
    Priority: {{steps.analysis.output.priority}}
  recipients: ["#engineering-alerts"]
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `type` | Must be `notification` |
| `channels` | List of channels: `slack`, `email`, `pagerduty` |
| `message` | The notification content |
| `recipients` | List of recipients (channel IDs, emails, etc.) |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `name` | Human-readable name | Same as `id` |
| `depends_on` | Steps that must complete first | `[]` |
| `urgency` | For PagerDuty: `low`, `high`, `critical` | `low` |

### Channel-Specific Examples

**Slack:**
```yaml
- id: slack-notify
  type: notification
  channels: [slack]
  message: "Process completed: {{steps.final.output}}"
  recipients: ["#general", "@john.doe"]
```

**Email:**
```yaml
- id: email-report
  type: notification
  channels: [email]
  message: |
    Subject: Weekly Report Ready

    The weekly report has been generated.
    See attached: {{steps.report.output.url}}
  recipients: ["team@company.com", "manager@company.com"]
```

**PagerDuty (for urgent alerts):**
```yaml
- id: critical-alert
  type: notification
  channels: [pagerduty]
  message: "Critical: Process {{input.process_name}} failed"
  recipients: ["engineering-oncall"]
  urgency: critical
```

### Multiple Channels

```yaml
- id: broadcast-completion
  type: notification
  channels: [slack, email]
  message: |
    ✅ Campaign Launch Complete

    Campaign: {{input.campaign_name}}
    Status: Live
  recipients:
    - "#marketing-team"
    - "stakeholders@company.com"
```

### Use Cases

1. **Completion Alerts**
   Notify when a long-running process finishes

2. **Error Escalation**
   Alert on-call teams when processes fail

3. **Status Updates**
   Keep stakeholders informed of progress

4. **Handoff Notifications**
   Alert humans when their approval is needed

---

## Sub-Process

Invokes another process as a nested workflow. Enables process composition and reusability.

### Basic Structure

```yaml
- id: setup-account
  name: Setup Customer Account
  type: sub_process
  depends_on: [validate-customer]
  process: account-setup-workflow
  input_mapping:
    customer_id: "{{steps.validate-customer.output.id}}"
    tier: "{{input.subscription_tier}}"
```

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `type` | Must be `sub_process` |
| `process` | Name of the process to invoke |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `name` | Human-readable name | Same as `id` |
| `depends_on` | Steps that must complete first | `[]` |
| `input_mapping` | Map parent data to child process input | `{}` |
| `timeout` | Max time for sub-process to complete | `1h` |

### Input Mapping

Pass data from the parent process to the child:

```yaml
# Parent process
- id: call-child
  type: sub_process
  process: data-processor
  input_mapping:
    # Child receives these as {{input.data}} and {{input.format}}
    data: "{{steps.gather.output}}"
    format: "{{input.output_format}}"
```

### Accessing Sub-Process Output

The child process output is available in subsequent parent steps:

```yaml
# After sub-process completes
- id: use-result
  depends_on: [setup-account]
  message: |
    Account created: {{steps.setup-account.output.account_id}}
    Email: {{steps.setup-account.output.email}}
```

### Example: Parent and Child Processes

**Parent Process:**
```yaml
name: customer-onboarding
version: "1.0"

steps:
  - id: validate
    type: agent_task
    agent: validator
    message: Validate customer data: {{input.customer}}

  - id: create-account
    type: sub_process
    depends_on: [validate]
    process: account-creation
    input_mapping:
      customer_id: "{{steps.validate.output.customer_id}}"
      plan: "{{input.plan}}"

  - id: send-welcome
    type: agent_task
    depends_on: [create-account]
    agent: communicator
    message: |
      Send welcome email to: {{steps.create-account.output.email}}
      Account ID: {{steps.create-account.output.account_id}}

outputs:
  - name: account
    source: "{{steps.create-account.output}}"
```

**Child Process (account-creation):**
```yaml
name: account-creation
version: "1.0"
description: Creates and configures a customer account

steps:
  - id: create
    type: agent_task
    agent: account-manager
    message: Create account for customer {{input.customer_id}}

  - id: configure
    type: agent_task
    depends_on: [create]
    agent: configurator
    message: |
      Configure account {{steps.create.output.account_id}}
      Plan: {{input.plan}}

outputs:
  - name: account_id
    source: "{{steps.create.output.account_id}}"
  - name: email
    source: "{{steps.create.output.email}}"
```

### Nested Sub-Processes

Sub-processes can call other sub-processes (up to 3 levels deep):

```
Parent Process
  └── Sub-Process A
        └── Sub-Process B
              └── Sub-Process C (max depth)
```

### Navigation and Breadcrumbs

When viewing execution details, sub-processes show as expandable nodes:

```
customer-onboarding (Running)
├── validate ✅
├── create-account (Running) ──► [View Sub-Process]
│   └── account-creation
│       ├── create ✅
│       └── configure (Running)
└── send-welcome ⏸️ (waiting)
```

### Use Cases

1. **Reusable Modules**
   Define common workflows once, use in multiple parent processes

2. **Complex Compositions**
   Break large workflows into manageable, testable pieces

3. **Team Boundaries**
   Different teams own different sub-processes

4. **Version Control**
   Update sub-processes independently of parents

### Best Practices

```yaml
# ✅ Good: Clear input mapping
input_mapping:
  customer_id: "{{steps.validate.output.id}}"
  subscription: "{{input.plan}}"

# ❌ Avoid: Passing entire objects when only fields needed
input_mapping:
  everything: "{{steps.validate.output}}"
```

---

## Step Dependencies

Dependencies control execution order. Steps without dependencies run in parallel at process start.

### Sequential Execution

```yaml
steps:
  - id: step-a
    ...
  - id: step-b
    depends_on: [step-a]  # Waits for step-a
  - id: step-c
    depends_on: [step-b]  # Waits for step-b
```

### Parallel Execution

```yaml
steps:
  - id: task-1
    ...  # Runs immediately
  - id: task-2
    ...  # Runs in parallel with task-1
  - id: combine
    depends_on: [task-1, task-2]  # Waits for both
```

### Fan-out / Fan-in

```yaml
steps:
  - id: start
    ...

  - id: path-a
    depends_on: [start]
  - id: path-b
    depends_on: [start]
  - id: path-c
    depends_on: [start]

  - id: merge
    depends_on: [path-a, path-b, path-c]
```

---

## Best Practices

### 1. Use Descriptive IDs
```yaml
# Good
- id: validate-customer-email

# Avoid
- id: step1
```

### 2. Set Appropriate Timeouts
Match timeouts to expected duration plus buffer:
- Quick API calls: `30s` - `2m`
- Complex analysis: `5m` - `15m`
- Human approval: `1h` - `48h`

### 3. Add Human Checkpoints
For critical workflows, add approval steps before irreversible actions.

### 4. Handle Errors
Configure retries for steps that may fail transiently.

## Next Steps

- [YAML Schema Reference](/processes/docs/reference/yaml-schema) — Complete schema documentation
- [Variable Interpolation](/processes/docs/reference/variables) — Advanced variable usage
