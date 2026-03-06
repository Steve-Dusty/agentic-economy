# Parallel Execution

Parallel execution lets multiple steps run simultaneously, dramatically reducing total execution time when steps don't depend on each other.

## The Pattern

```
                    ┌──────────┐
               ┌───►│  Step B  │───┐
               │    └──────────┘   │
┌──────────┐   │    ┌──────────┐   │    ┌──────────┐
│  Step A  │───┼───►│  Step C  │───┼───►│  Step E  │
└──────────┘   │    └──────────┘   │    └──────────┘
               │    ┌──────────┐   │
               └───►│  Step D  │───┘
                    └──────────┘
```

Steps B, C, and D run in parallel after A completes. Step E waits for all three.

## When to Use Parallel Execution

Use parallel execution when:
- Multiple independent tasks can run simultaneously
- You want to reduce total execution time
- Different agents can work on different aspects concurrently
- You need to gather data from multiple sources

## Basic Parallel Pattern

Steps without `depends_on` run immediately in parallel:

```yaml
name: multi-source-research
version: "1.0"

steps:
  # These 3 steps run in parallel (no depends_on)
  - id: research-academic
    type: agent_task
    agent: academic-researcher
    message: Find academic papers about {{input.topic}}

  - id: research-news
    type: agent_task
    agent: news-researcher
    message: Find recent news articles about {{input.topic}}

  - id: research-social
    type: agent_task
    agent: social-researcher
    message: Find social media discussions about {{input.topic}}

  # This step waits for all 3 to complete
  - id: synthesize
    type: agent_task
    agent: synthesizer
    depends_on: [research-academic, research-news, research-social]
    message: |
      Combine research from multiple sources:

      Academic findings:
      {{steps.research-academic.output}}

      News coverage:
      {{steps.research-news.output}}

      Social discussions:
      {{steps.research-social.output}}

      Create a comprehensive summary.
```

## Common Parallel Patterns

### Fan-Out / Fan-In

Start with one step, fan out to many parallel steps, then fan in to combine results.

```
         Fan-Out                    Fan-In
            ↓                          ↓
       ┌─────────┐               ┌─────────┐
       │  Start  │               │ Combine │
       └────┬────┘               └────▲────┘
            │                         │
     ┌──────┼──────┐           ┌──────┴──────┐
     ▼      ▼      ▼           │      │      │
┌────────┐ ┌────────┐ ┌────────┐      │      │
│ Path A │ │ Path B │ │ Path C │──────┴──────┘
└────────┘ └────────┘ └────────┘
```

```yaml
name: fan-out-fan-in
steps:
  - id: start
    type: agent_task
    agent: coordinator
    message: Initialize and prepare data for processing

  # Fan out: 3 parallel paths
  - id: path-a
    depends_on: [start]
    type: agent_task
    agent: specialist-a
    message: Process using method A: {{steps.start.output}}

  - id: path-b
    depends_on: [start]
    type: agent_task
    agent: specialist-b
    message: Process using method B: {{steps.start.output}}

  - id: path-c
    depends_on: [start]
    type: agent_task
    agent: specialist-c
    message: Process using method C: {{steps.start.output}}

  # Fan in: combine all results
  - id: combine
    depends_on: [path-a, path-b, path-c]
    type: agent_task
    agent: coordinator
    message: |
      Merge results from all processing paths:
      - Method A: {{steps.path-a.output}}
      - Method B: {{steps.path-b.output}}
      - Method C: {{steps.path-c.output}}
```

### Diamond Pattern

A specific case where two parallel paths diverge and then converge.

```
         ┌──────────┐
         │  Start   │
         └────┬─────┘
              │
       ┌──────┴──────┐
       ▼             ▼
  ┌─────────┐   ┌─────────┐
  │ Path A  │   │ Path B  │
  └────┬────┘   └────┬────┘
       │             │
       └──────┬──────┘
              ▼
         ┌─────────┐
         │  Merge  │
         └─────────┘
```

```yaml
name: diamond-comparison
steps:
  - id: start
    type: agent_task
    agent: coordinator
    message: Prepare the input for dual analysis

  - id: analysis-a
    depends_on: [start]
    type: agent_task
    agent: analyst-a
    message: |
      Analyze using approach A:
      {{steps.start.output}}

  - id: analysis-b
    depends_on: [start]
    type: agent_task
    agent: analyst-b
    message: |
      Analyze using approach B:
      {{steps.start.output}}

  - id: compare
    depends_on: [analysis-a, analysis-b]
    type: agent_task
    agent: coordinator
    message: |
      Compare the two analysis approaches:

      Approach A concluded:
      {{steps.analysis-a.output}}

      Approach B concluded:
      {{steps.analysis-b.output}}

      Identify agreements, disagreements, and synthesize.
```

### Parallel with Different Completion Times

When parallel steps take different times, the join step waits for ALL to complete:

```
Timeline:
────────────────────────────────────────────►

Step A: [=======]                           (7 min)
Step B: [==================]                (18 min)
Step C: [==========]                        (10 min)
                          |
                          └─ Merge waits until Step B completes

Merge:                    [====]            (starts at 18 min)
```

## Handling Partial Failures

### Default Behavior

If one parallel step fails, other parallel steps continue, but the join step cannot proceed:

```yaml
# If research-news fails:
# - research-academic: completes ✅
# - research-news: fails ❌
# - research-social: completes ✅
# - synthesize: cannot run ⏸️ (missing dependency)
# - Execution: FAILED
```

### With Retry on Individual Steps

```yaml
- id: research-news
  type: agent_task
  agent: news-researcher
  message: Find news articles
  retry:
    max_attempts: 3
    delay: 30s
```

### Using Defaults for Optional Steps

If a step might fail and you want to continue anyway, use conditional logic in the merge:

```yaml
- id: synthesize
  depends_on: [research-academic, research-news, research-social]
  message: |
    Combine available research:
    - Academic: {{steps.research-academic.output | default:"No academic data"}}
    - News: {{steps.research-news.output | default:"No news data"}}
    - Social: {{steps.research-social.output | default:"No social data"}}
```

## Performance Considerations

### Agent Availability

When running parallel steps using the same agent, they queue:

```yaml
# These share the same agent - they'll queue, not parallelize
- id: task-1
  agent: worker
- id: task-2
  agent: worker  # Waits for task-1 if same agent
- id: task-3
  agent: worker  # Waits for task-1 and task-2
```

For true parallelism, use different agents:

```yaml
# True parallel - different agents
- id: task-1
  agent: worker-1
- id: task-2
  agent: worker-2
- id: task-3
  agent: worker-3
```

### Resource Usage

More parallel steps = more concurrent resources. Consider:
- Available agent capacity
- API rate limits on external services
- Memory usage with many concurrent operations

## Best Practices

### 1. Group Related Parallel Work

```yaml
# ✅ Good: Related parallel research
- id: research-tech
- id: research-market
- id: research-competitors
- id: synthesize-research
  depends_on: [research-tech, research-market, research-competitors]

# ❌ Avoid: Unrelated parallel work (confusing)
- id: send-email
- id: analyze-data
- id: generate-report
```

### 2. Keep Fan-Out Manageable

```yaml
# ✅ Good: Reasonable parallelism (3-5 branches)
depends_on: [path-a, path-b, path-c]

# ⚠️ Consider: High parallelism (10+ branches) may strain resources
depends_on: [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10]
```

### 3. Document the Parallel Strategy

```yaml
name: multi-perspective-analysis
description: |
  Analyzes input from 3 perspectives in parallel:
  - Technical feasibility (tech-agent)
  - Market viability (market-agent)
  - Financial impact (finance-agent)
  Results are synthesized into a single recommendation.
```

## Example: Parallel Report Generation

```yaml
name: comprehensive-report
version: "1.0"
description: Generate report sections in parallel, then compile

steps:
  - id: gather-data
    type: agent_task
    agent: data-collector
    message: Gather raw data for the report

  # Parallel section generation
  - id: executive-summary
    depends_on: [gather-data]
    type: agent_task
    agent: executive-writer
    message: Write executive summary from {{steps.gather-data.output}}

  - id: technical-analysis
    depends_on: [gather-data]
    type: agent_task
    agent: technical-analyst
    message: Write technical analysis from {{steps.gather-data.output}}

  - id: financial-projections
    depends_on: [gather-data]
    type: agent_task
    agent: financial-analyst
    message: Create financial projections from {{steps.gather-data.output}}

  - id: recommendations
    depends_on: [gather-data]
    type: agent_task
    agent: strategist
    message: Develop recommendations from {{steps.gather-data.output}}

  # Compile final report
  - id: compile-report
    depends_on: [executive-summary, technical-analysis, financial-projections, recommendations]
    type: agent_task
    agent: report-compiler
    message: |
      Compile the final report from these sections:

      ## Executive Summary
      {{steps.executive-summary.output}}

      ## Technical Analysis
      {{steps.technical-analysis.output}}

      ## Financial Projections
      {{steps.financial-projections.output}}

      ## Recommendations
      {{steps.recommendations.output}}

outputs:
  - name: report
    source: "{{steps.compile-report.output}}"
```

## Related

- [Sequential Workflows](./sequential) — Linear step execution
- [Approval Workflows](./approvals) — Add human checkpoints
- [Understanding Step Types](/processes/docs/getting-started/step-types) — Step type reference
