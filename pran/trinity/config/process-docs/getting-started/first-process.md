# Your First Process

In this 5-minute tutorial, you'll create a simple two-step process that demonstrates the core concepts of workflow automation in Trinity.

## What We'll Build

A basic content summarization process:
1. **Step 1**: Research a topic using an AI agent
2. **Step 2**: Summarize the research findings

```
┌─────────────┐    ┌─────────────┐
│  Research   │───►│  Summarize  │
└─────────────┘    └─────────────┘
```

## Prerequisites

Before starting, ensure you have:
- [ ] At least one agent created and running
- [ ] Access to the Processes section in Trinity

## Step 1: Navigate to Process Creation

1. Click **Processes** in the main navigation
2. Click the **Create Process** button (or use a Quick Start template)
3. You'll see the YAML editor with a basic template

## Step 2: Define Your Process

Replace the default template with this YAML:

```yaml
name: content-summarizer
version: "1.0"
description: Research a topic and create a summary

triggers:
  - type: manual
    id: start-manually

steps:
  - id: research
    name: Research Topic
    type: agent_task
    agent: your-agent-name  # Replace with your actual agent name
    message: |
      Research the following topic:
      {{input.topic}}

      Provide 3-5 key facts and insights.
    timeout: 5m

  - id: summarize
    name: Create Summary
    type: agent_task
    depends_on: [research]
    agent: your-agent-name  # Can be the same or different agent
    message: |
      Based on this research:
      {{steps.research.output}}

      Create a concise summary in 2-3 sentences.
    timeout: 3m

outputs:
  - name: summary
    source: "{{steps.summarize.output}}"
```

> **Important**: Replace `your-agent-name` with the actual name of your running agent.

## Step 3: Validate

Click the **Validate** button to check your YAML. Trinity will verify:
- ✅ Valid YAML syntax
- ✅ All required fields present
- ✅ Step dependencies are valid
- ✅ Referenced agents exist

Fix any errors shown in red before proceeding.

## Step 4: Save Your Process

1. Click **Save** to save as a draft
2. Your process appears in the Processes list with "draft" status

## Step 5: Run Your Process

1. From the Processes list, click the **Play** button on your process
2. Enter input data in the dialog:

```json
{
  "topic": "The benefits of renewable energy"
}
```

3. Click **Execute**

## Step 6: Monitor Execution

1. You'll be redirected to the Executions view
2. Watch the timeline as each step progresses:
   - 🔵 **Running** — Step is executing
   - ✅ **Completed** — Step finished successfully
   - ❌ **Failed** — Step encountered an error

3. Click on a step to see its output

## Understanding the YAML

Let's break down what each section does:

### Metadata
```yaml
name: content-summarizer
version: "1.0"
description: Research a topic and create a summary
```
Basic information about your process.

### Triggers
```yaml
triggers:
  - type: manual
    id: start-manually
```
How the process can be started. `manual` means you start it via the UI or API.

### Steps
```yaml
steps:
  - id: research
    name: Research Topic
    type: agent_task
    agent: your-agent-name
    message: |
      ...
    timeout: 5m
```
Each step has:
- `id` — Unique identifier for the step
- `name` — Human-readable name
- `type` — What kind of step (agent_task, human_approval, etc.)
- `agent` — Which agent executes the task
- `message` — The prompt/instructions for the agent
- `timeout` — Maximum time to wait for completion

### Dependencies
```yaml
depends_on: [research]
```
This step waits for the "research" step to complete before starting.

### Variable Interpolation
```yaml
{{input.topic}}           # Reference input data
{{steps.research.output}} # Reference output from another step
```

### Outputs
```yaml
outputs:
  - name: summary
    source: "{{steps.summarize.output}}"
```
Defines what the process returns when complete.

## What's Next?

Congratulations! You've created and run your first process. Here are some ideas to explore:

1. **Add more steps** — Create longer chains of tasks
2. **Add parallel steps** — Run steps simultaneously with no `depends_on`
3. **Add human approval** — Insert a review step before summarizing
4. **Set up a schedule** — Run your process automatically

Continue learning:
- [Understanding Step Types](./step-types.md)
- [YAML Schema Reference](/processes/docs/reference/yaml-schema)
