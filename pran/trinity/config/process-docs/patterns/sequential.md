# Sequential Workflows

Sequential workflows are the foundation of process automation. Steps execute one after another, with each step waiting for its dependencies to complete.

## The Pattern

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Step 1  │───►│  Step 2  │───►│  Step 3  │───►│  Step 4  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

Each step:
- Waits for the previous step to complete
- Can access output from previous steps
- Passes its output to the next step

## When to Use Sequential

Use sequential workflows when:
- Steps must execute in a specific order
- Later steps depend on output from earlier steps
- You need a clear audit trail of what happened when
- The workflow is inherently linear (e.g., draft → review → publish)

## Basic Example

```yaml
name: content-pipeline
version: "1.0"
description: Research, write, and publish content

steps:
  - id: research
    name: Research Topic
    type: agent_task
    agent: researcher
    message: |
      Research the topic: {{input.topic}}
      Provide key facts, statistics, and insights.
    timeout: 10m

  - id: write
    name: Write Draft
    type: agent_task
    agent: writer
    depends_on: [research]
    message: |
      Write an article based on this research:
      {{steps.research.output}}

      Target audience: {{input.audience}}
      Tone: {{input.tone | default:"professional"}}
    timeout: 15m

  - id: edit
    name: Edit and Polish
    type: agent_task
    agent: editor
    depends_on: [write]
    message: |
      Edit this draft for clarity, grammar, and style:
      {{steps.write.output}}
    timeout: 10m

  - id: publish
    name: Publish Content
    type: agent_task
    agent: publisher
    depends_on: [edit]
    message: |
      Format and publish this content:
      {{steps.edit.output}}

      Platform: {{input.platform | default:"blog"}}
    timeout: 5m

outputs:
  - name: final_content
    source: "{{steps.publish.output}}"
```

## Data Flow Between Steps

### Accessing Previous Step Output

```yaml
# Step 2 accesses Step 1's output
- id: step-2
  depends_on: [step-1]
  message: |
    Process this data: {{steps.step-1.output}}
```

### Accessing Nested Output Fields

If a step returns structured data:

```yaml
# If step-1 returns: {"summary": "...", "count": 42}
- id: step-2
  message: |
    Summary: {{steps.step-1.output.summary}}
    Item count: {{steps.step-1.output.count}}
```

### Chaining Multiple Outputs

```yaml
- id: final-step
  depends_on: [step-a, step-b, step-c]
  message: |
    Combine all previous results:
    - From A: {{steps.step-a.output}}
    - From B: {{steps.step-b.output}}
    - From C: {{steps.step-c.output}}
```

## Error Handling in Chains

### With Retry

```yaml
- id: flaky-step
  type: agent_task
  agent: api-caller
  message: Fetch data from external API
  retry:
    max_attempts: 3
    delay: 30s
    backoff: exponential
```

If a step fails after all retries, the entire execution fails. Subsequent steps will not run.

### Execution Flow on Failure

```
Step 1 ✅ → Step 2 ❌ → Step 3 ⏸️ (never runs)
                         ↓
              Execution Status: FAILED
```

## Best Practices

### 1. Keep Steps Focused

Each step should do one thing well:

```yaml
# ✅ Good: Single responsibility
- id: extract-data
  message: Extract customer data from the report
- id: validate-data
  message: Validate the extracted data
- id: transform-data
  message: Transform data to required format

# ❌ Avoid: Too much in one step
- id: do-everything
  message: Extract, validate, and transform the data
```

### 2. Use Descriptive IDs

```yaml
# ✅ Good: Clear intent
- id: validate-customer-email
- id: send-welcome-notification
- id: create-account-record

# ❌ Avoid: Unclear
- id: step1
- id: process
- id: handle
```

### 3. Set Appropriate Timeouts

Match timeouts to expected duration plus buffer:

```yaml
- id: quick-validation
  timeout: 1m  # Fast operation

- id: complex-analysis
  timeout: 15m  # May take longer

- id: external-api-call
  timeout: 2m
  retry:
    max_attempts: 3
    delay: 10s  # Allow recovery time
```

### 4. Document Data Expectations

Add comments showing expected input/output:

```yaml
# Input: { "topic": "string", "audience": "string" }
# Output: { "article": "string", "word_count": number }
- id: write-article
  message: |
    Write an article about {{input.topic}}...
```

## Common Patterns

### Pipeline with Validation Gate

```yaml
steps:
  - id: generate
    ...
  - id: validate
    depends_on: [generate]
    message: Validate the output meets quality standards
  - id: process
    depends_on: [validate]
    # Only runs if validation passes
```

### Accumulating Context

```yaml
steps:
  - id: gather-context
    message: Gather background information
  - id: analyze
    depends_on: [gather-context]
    message: |
      Context: {{steps.gather-context.output}}
      Now analyze for patterns
  - id: synthesize
    depends_on: [gather-context, analyze]
    message: |
      Original context: {{steps.gather-context.output}}
      Analysis: {{steps.analyze.output}}
      Synthesize into final report
```

## Related

- [Parallel Execution](./parallel) — Run steps simultaneously
- [Approval Workflows](./approvals) — Add human checkpoints
- [Variable Interpolation](/processes/docs/reference/variables) — Pass data between steps
