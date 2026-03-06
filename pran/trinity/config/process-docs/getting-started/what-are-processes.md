# What are Processes?

Processes are the heart of workflow automation in Trinity. They let you orchestrate multi-step tasks across your AI agents, creating powerful automated pipelines that run with minimal human intervention.

## The Core Concept

Think of a Process as a recipe for your AI agents. Just like a recipe has ingredients and steps, a Process defines:

- **Steps** — Individual tasks that agents perform
- **Dependencies** — Which steps must complete before others can start
- **Data Flow** — How information passes between steps

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Research   │───►│   Analyze   │───►│   Report    │
│   (Agent A) │    │   (Agent B) │    │   (Agent C) │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Why Use Processes?

### 1. Automation at Scale
Instead of manually coordinating agents, define the workflow once and let Trinity handle execution. Run it hundreds of times without additional effort.

### 2. Reliable Execution
Processes handle errors, retries, and edge cases. If something fails, you get clear visibility into what went wrong and where.

### 3. Human-in-the-Loop
Add approval steps where humans review and approve before the process continues. Perfect for quality gates and compliance requirements.

### 4. Reusability
Create process templates for common workflows. Share them across your team and standardize operations.

## Process Components

### Steps
The building blocks of any process. Each step performs a specific action:

| Step Type | Description |
|-----------|-------------|
| `agent_task` | Execute a task using an AI agent |
| `human_approval` | Pause for human review and approval |
| `gateway` | Make decisions based on conditions |
| `timer` | Wait for a specified duration |

### Triggers
How processes start:

- **Manual** — Start on-demand via UI or API
- **Webhook** — Start when receiving an HTTP request
- **Schedule** — Run on a cron schedule (daily, weekly, etc.)

### Variables
Pass data between steps using variable interpolation:

```yaml
message: |
  Analyze this data: {{steps.gather.output}}
```

## Example Use Cases

1. **Content Creation Pipeline**
   Research → Write → Edit → Publish

2. **Data Processing**
   Collect → Transform → Analyze → Report

3. **Customer Support**
   Triage → Route → Respond → Follow-up

4. **Compliance Review**
   Scan → Flag → Human Review → Archive

## Next Steps

Ready to create your first process? Continue to:

- [Your First Process](./first-process.md) — Step-by-step tutorial
- [Understanding Step Types](./step-types.md) — Deep dive into each step type
