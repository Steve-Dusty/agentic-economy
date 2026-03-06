# Your Second Process: Parallel Execution

In [Your First Process](/processes/docs/getting-started/first-process), you created a simple sequential workflow. Now let's level up by running steps in parallel to gather information from multiple sources simultaneously.

## What You'll Learn

- How to run steps in parallel (no `depends_on`)
- How to aggregate results from multiple parallel steps
- How to pass data between parallel branches

## Prerequisites

Before starting:
- ✅ Completed "Your First Process" tutorial
- ✅ At least one agent running
- ✅ Understanding of `depends_on` for sequential steps

## What We'll Build

A multi-perspective analysis process that:
1. Gathers data from 3 different angles **simultaneously**
2. Combines all perspectives into a final report

```
                    ┌─────────────────┐
               ┌───►│ Technical View  │───┐
               │    └─────────────────┘   │
┌───────────┐  │    ┌─────────────────┐   │    ┌─────────────┐
│  Prepare  │──┼───►│  Market View    │───┼───►│  Synthesize │
└───────────┘  │    └─────────────────┘   │    └─────────────┘
               │    ┌─────────────────┐   │
               └───►│ Financial View  │───┘
                    └─────────────────┘
```

**Time saved**: Instead of ~15 minutes (sequential), parallel execution takes ~6 minutes!

## Step 1: Create the Process

Navigate to **Processes** → **Create Process** and enter this YAML:

```yaml
name: multi-perspective-analysis
version: "1.0"
description: Analyze a topic from technical, market, and financial perspectives

triggers:
  - type: manual
    id: start-analysis

steps:
  # Step 1: Prepare the analysis context
  - id: prepare
    name: Prepare Context
    type: agent_task
    agent: your-agent-name  # Replace with your agent
    message: |
      Prepare an analysis brief for: {{input.topic}}

      Identify:
      - Key questions to answer
      - Relevant data points to gather
      - Success criteria for the analysis
    timeout: 3m

  # Steps 2-4: Run in PARALLEL (no depends_on linking them to each other)
  - id: technical-analysis
    name: Technical Perspective
    type: agent_task
    depends_on: [prepare]  # Waits for prepare, but not for other analyses
    agent: your-agent-name
    message: |
      Analyze from a TECHNICAL perspective:

      Context: {{steps.prepare.output}}
      Topic: {{input.topic}}

      Focus on:
      - Technical feasibility
      - Implementation complexity
      - Technology risks and opportunities
    timeout: 5m

  - id: market-analysis
    name: Market Perspective
    type: agent_task
    depends_on: [prepare]  # Also waits only for prepare
    agent: your-agent-name
    message: |
      Analyze from a MARKET perspective:

      Context: {{steps.prepare.output}}
      Topic: {{input.topic}}

      Focus on:
      - Market size and trends
      - Competitive landscape
      - Customer needs and pain points
    timeout: 5m

  - id: financial-analysis
    name: Financial Perspective
    type: agent_task
    depends_on: [prepare]  # Same - waits only for prepare
    agent: your-agent-name
    message: |
      Analyze from a FINANCIAL perspective:

      Context: {{steps.prepare.output}}
      Topic: {{input.topic}}

      Focus on:
      - Cost estimates
      - Revenue potential
      - ROI projections
    timeout: 5m

  # Step 5: Synthesize - waits for ALL three parallel steps
  - id: synthesize
    name: Synthesize Report
    type: agent_task
    depends_on: [technical-analysis, market-analysis, financial-analysis]
    agent: your-agent-name
    message: |
      Create a comprehensive analysis report combining all perspectives:

      ## Technical Analysis
      {{steps.technical-analysis.output}}

      ## Market Analysis
      {{steps.market-analysis.output}}

      ## Financial Analysis
      {{steps.financial-analysis.output}}

      Synthesize into:
      1. Executive summary (3 sentences)
      2. Key findings from each perspective
      3. Overall recommendation
      4. Risk factors
    timeout: 5m

outputs:
  - name: report
    source: "{{steps.synthesize.output}}"
  - name: technical
    source: "{{steps.technical-analysis.output}}"
  - name: market
    source: "{{steps.market-analysis.output}}"
  - name: financial
    source: "{{steps.financial-analysis.output}}"
```

> **Important**: Replace `your-agent-name` with your actual agent name.

## Step 2: Understand Parallel Execution

Notice how the three analysis steps are configured:

```yaml
- id: technical-analysis
  depends_on: [prepare]     # Only depends on 'prepare'

- id: market-analysis
  depends_on: [prepare]     # Only depends on 'prepare'

- id: financial-analysis
  depends_on: [prepare]     # Only depends on 'prepare'
```

**Key insight**: Because none of these steps depend on each other, Trinity runs them **simultaneously** as soon as `prepare` completes.

If they were sequential:
```
prepare → technical → market → financial → synthesize
(3 min)   (5 min)     (5 min)   (5 min)     (5 min) = 23 minutes
```

With parallel execution:
```
prepare → [technical, market, financial] → synthesize
(3 min)   (5 min - all at once)            (5 min) = 13 minutes
```

## Step 3: Validate and Save

1. Click **Validate** to check for errors
2. Click **Save** to save as draft
3. Click **Publish** to make it runnable

## Step 4: Run Your Process

1. Click the **Play** button
2. Enter input data:

```json
{
  "topic": "Launching a mobile app for local restaurant delivery"
}
```

3. Click **Execute**

## Step 5: Watch Parallel Execution

In the execution view, you'll see:

```
Timeline:
─────────────────────────────────────────────────────►
prepare:           [====]
technical-analysis:      [========]
market-analysis:         [========]   ← Running simultaneously!
financial-analysis:      [========]
synthesize:                       [====]
```

All three analysis steps show as "Running" at the same time.

## Understanding the Results

Click on each completed step to see its output:

- **prepare**: The analysis brief
- **technical-analysis**: Technical perspective insights
- **market-analysis**: Market perspective insights
- **financial-analysis**: Financial perspective insights
- **synthesize**: Combined report with all perspectives

## Key Concepts Learned

### 1. Parallel Execution is Implicit

Steps run in parallel when they don't depend on each other:

```yaml
# These run in parallel:
- id: step-a
  depends_on: [start]
- id: step-b
  depends_on: [start]  # Same dependency = parallel
- id: step-c
  depends_on: [start]
```

### 2. Aggregation with Multiple Dependencies

The synthesize step waits for ALL specified dependencies:

```yaml
- id: synthesize
  depends_on: [technical-analysis, market-analysis, financial-analysis]
  # Only runs when ALL THREE complete
```

### 3. Accessing Multiple Outputs

In the message, reference each step's output:

```yaml
message: |
  Technical: {{steps.technical-analysis.output}}
  Market: {{steps.market-analysis.output}}
  Financial: {{steps.financial-analysis.output}}
```

## Try It Yourself

Modify the process to add a 4th parallel perspective:

```yaml
- id: competitive-analysis
  name: Competitive Perspective
  type: agent_task
  depends_on: [prepare]
  agent: your-agent-name
  message: |
    Analyze competitors for: {{input.topic}}
  timeout: 5m
```

Don't forget to add it to the synthesize step's `depends_on`!

## What's Next?

Now that you can run parallel processes, learn to add human checkpoints:

→ [Adding Human Checkpoints](./human-checkpoints) — Add approval gates to your workflows

## Related

- [Parallel Execution Pattern](/processes/docs/patterns/parallel) — Deep dive into parallel patterns
- [Variable Interpolation](/processes/docs/reference/variables) — Accessing step outputs
