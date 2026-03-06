# Complex Workflows: Gateways and Branching

You've mastered sequential, parallel, and approval workflows. Now let's combine everything to build sophisticated workflows with conditional branching, multiple paths, and intelligent routing.

## What You'll Learn

- How to use `gateway` steps for conditional routing
- How to combine multiple patterns in one workflow
- How to handle multiple end states
- Best practices for complex process design

## Prerequisites

Before starting:
- ✅ Completed "Your First Process" tutorial
- ✅ Completed "Your Second Process: Parallel Execution"
- ✅ Completed "Adding Human Checkpoints"

## What We'll Build

A support ticket handling system that:
1. Analyzes incoming tickets
2. Routes based on complexity (simple, medium, complex)
3. Handles each type differently
4. Includes human escalation for complex cases

```
                            ┌─────────────────┐
                       ┌───►│  Auto-Resolve   │───┐
                       │    │    (Simple)     │   │
┌──────────┐    ┌──────┴──┐ └─────────────────┘   │    ┌─────────────┐
│ Analyze  │───►│ GATEWAY │                       ├───►│   Close     │
│  Ticket  │    │  Route  │ ┌─────────────────┐   │    │   Ticket    │
└──────────┘    └──────┬──┘ │  Human Review   │───┤    └─────────────┘
                       │    │   (Medium)      │   │
                       │    └─────────────────┘   │
                       │    ┌─────────────────┐   │
                       └───►│   Escalate      │───┘
                            │   (Complex)     │
                            └─────────────────┘
```

## Step 1: Create the Process

Navigate to **Processes** → **Create Process** and enter:

```yaml
name: intelligent-ticket-routing
version: "1.0"
description: Smart support ticket handling with complexity-based routing

triggers:
  - type: manual
    id: submit-ticket
  - type: webhook
    id: api-ticket

steps:
  # ═══════════════════════════════════════════════════════════
  # PHASE 1: Analysis
  # ═══════════════════════════════════════════════════════════

  - id: analyze-ticket
    name: Analyze Ticket
    type: agent_task
    agent: your-agent-name  # Replace with your agent
    message: |
      Analyze this support ticket and determine its complexity:

      **Subject**: {{input.subject}}
      **Description**: {{input.description}}
      **Customer Tier**: {{input.customer_tier | default:"standard"}}

      Respond with a JSON object:
      {
        "complexity": "simple" | "medium" | "complex",
        "category": "billing" | "technical" | "account" | "other",
        "sentiment": "positive" | "neutral" | "negative",
        "summary": "brief summary",
        "suggested_response": "draft response if simple"
      }
    timeout: 3m

  # ═══════════════════════════════════════════════════════════
  # PHASE 2: Routing Gateway
  # ═══════════════════════════════════════════════════════════

  - id: complexity-router
    name: Route by Complexity
    type: gateway
    depends_on: [analyze-ticket]
    conditions:
      - expression: "{{steps.analyze-ticket.output.complexity}} == 'simple'"
        next: auto-resolve
      - expression: "{{steps.analyze-ticket.output.complexity}} == 'medium'"
        next: human-review
      - expression: "{{steps.analyze-ticket.output.complexity}} == 'complex'"
        next: specialist-escalation
      - default: true
        next: human-review  # Default to human review if unclear

  # ═══════════════════════════════════════════════════════════
  # PHASE 3A: Simple Ticket Path (Automated)
  # ═══════════════════════════════════════════════════════════

  - id: auto-resolve
    name: Auto-Resolve Ticket
    type: agent_task
    agent: your-agent-name
    message: |
      Generate a helpful response for this simple support ticket:

      **Summary**: {{steps.analyze-ticket.output.summary}}
      **Category**: {{steps.analyze-ticket.output.category}}
      **Suggested Response**: {{steps.analyze-ticket.output.suggested_response}}

      Create a polished, friendly response that resolves the issue.
    timeout: 3m

  - id: send-auto-response
    name: Send Response
    type: notification
    depends_on: [auto-resolve]
    channels: [email]
    message: |
      Subject: Re: {{input.subject}}

      {{steps.auto-resolve.output}}

      ---
      This response was generated automatically.
      If you need further assistance, please reply to this email.
    recipients: ["{{input.customer_email}}"]

  # ═══════════════════════════════════════════════════════════
  # PHASE 3B: Medium Ticket Path (Human Review)
  # ═══════════════════════════════════════════════════════════

  - id: draft-response
    name: Draft Response
    type: agent_task
    agent: your-agent-name
    message: |
      Draft a response for this medium-complexity ticket:

      **Original Ticket**:
      Subject: {{input.subject}}
      Description: {{input.description}}

      **Analysis**:
      {{steps.analyze-ticket.output}}

      Create a thorough, helpful draft response.
    timeout: 5m

  - id: human-review
    name: Support Team Review
    type: human_approval
    depends_on: [draft-response]
    title: "Review: {{input.subject}}"
    description: |
      ## Ticket Details
      **Customer**: {{input.customer_email}}
      **Tier**: {{input.customer_tier | default:"standard"}}
      **Sentiment**: {{steps.analyze-ticket.output.sentiment}}

      ## Original Request
      {{input.description}}

      ## Proposed Response
      {{steps.draft-response.output}}

      ---

      **Approve** to send this response, or **Reject** with edits.
    timeout: 4h
    timeout_action: skip

  - id: review-decision
    name: Check Review Decision
    type: gateway
    depends_on: [human-review]
    conditions:
      - expression: "{{steps.human-review.output.decision}} == 'approved'"
        next: send-reviewed-response
      - expression: "{{steps.human-review.output.decision}} == 'rejected'"
        next: revise-response
      - default: true
        next: send-reviewed-response  # Send if timeout

  - id: send-reviewed-response
    name: Send Reviewed Response
    type: notification
    channels: [email]
    message: |
      Subject: Re: {{input.subject}}

      {{steps.draft-response.output}}
    recipients: ["{{input.customer_email}}"]

  - id: revise-response
    name: Revise Response
    type: agent_task
    agent: your-agent-name
    message: |
      Revise this response based on reviewer feedback:

      **Original Draft**:
      {{steps.draft-response.output}}

      **Reviewer Feedback**:
      {{steps.human-review.output.comments}}

      Create an improved response addressing the feedback.
    timeout: 5m

  # ═══════════════════════════════════════════════════════════
  # PHASE 3C: Complex Ticket Path (Specialist Escalation)
  # ═══════════════════════════════════════════════════════════

  - id: specialist-escalation
    name: Escalate to Specialist
    type: notification
    channels: [slack]
    message: |
      🚨 *Complex Ticket Escalation*

      *Subject*: {{input.subject}}
      *Customer*: {{input.customer_email}} ({{input.customer_tier | default:"standard"}})
      *Category*: {{steps.analyze-ticket.output.category}}
      *Sentiment*: {{steps.analyze-ticket.output.sentiment}}

      *Summary*: {{steps.analyze-ticket.output.summary}}

      Please assign a specialist to handle this ticket.
    recipients: ["#support-escalations"]

  - id: await-specialist
    name: Wait for Assignment
    type: timer
    depends_on: [specialist-escalation]
    duration: 30m

  - id: check-assignment
    name: Check Status
    type: agent_task
    depends_on: [await-specialist]
    agent: your-agent-name
    message: |
      Check if ticket "{{input.subject}}" has been assigned.
      Return: {"assigned": true/false, "assignee": "name or null"}
    timeout: 2m

  # ═══════════════════════════════════════════════════════════
  # PHASE 4: Closure (All paths converge here)
  # ═══════════════════════════════════════════════════════════

  - id: close-ticket
    name: Close Ticket
    type: agent_task
    depends_on: [send-auto-response, send-reviewed-response, revise-response, check-assignment]
    agent: your-agent-name
    message: |
      Mark this support ticket as handled:

      Subject: {{input.subject}}
      Resolution Path: Completed via intelligent routing

      Generate a brief internal note about the resolution.
    timeout: 2m

outputs:
  - name: resolution_summary
    source: "{{steps.close-ticket.output}}"
  - name: complexity
    source: "{{steps.analyze-ticket.output.complexity}}"
  - name: category
    source: "{{steps.analyze-ticket.output.category}}"
```

> **Important**: Replace `your-agent-name` with your actual agent name.

## Step 2: Understanding the Gateway

The gateway is the routing brain:

```yaml
- id: complexity-router
  type: gateway
  depends_on: [analyze-ticket]
  conditions:
    - expression: "{{steps.analyze-ticket.output.complexity}} == 'simple'"
      next: auto-resolve
    - expression: "{{steps.analyze-ticket.output.complexity}} == 'medium'"
      next: human-review
    - expression: "{{steps.analyze-ticket.output.complexity}} == 'complex'"
      next: specialist-escalation
    - default: true
      next: human-review
```

**How it works**:
1. Evaluates conditions top-to-bottom
2. First matching condition determines the path
3. `default: true` catches anything that doesn't match

## Step 3: Run with Different Inputs

### Test Simple Path
```json
{
  "subject": "How do I reset my password?",
  "description": "I forgot my password and need to reset it.",
  "customer_email": "user@example.com"
}
```

### Test Medium Path
```json
{
  "subject": "Billing discrepancy on my account",
  "description": "I was charged twice for my subscription this month. I have screenshots of both charges.",
  "customer_email": "user@example.com",
  "customer_tier": "premium"
}
```

### Test Complex Path
```json
{
  "subject": "Data migration failure with custom integration",
  "description": "Our enterprise integration is failing during data migration. We're seeing errors in the API logs and our production system is affected.",
  "customer_email": "enterprise@company.com",
  "customer_tier": "enterprise"
}
```

## Key Concepts

### 1. Gateway Conditions

Available comparison operators:

```yaml
# Equality
"{{value}} == 'expected'"

# Inequality
"{{value}} != 'unwanted'"

# Numeric comparisons
"{{score}} > 80"
"{{score}} >= 80"
"{{score}} < 20"
"{{score}} <= 20"

# Contains (string/array)
"{{tags}} contains 'urgent'"

# Boolean
"{{is_valid}} == true"
```

### 2. Multiple Convergence Points

Different paths can converge:

```yaml
- id: final-step
  depends_on: [path-a-end, path-b-end, path-c-end]
  # Runs after ANY of these complete
```

### 3. Combining Patterns

This workflow uses:
- **Sequential**: analyze → route → handle → close
- **Parallel**: Different paths run independently
- **Approval**: Human review for medium complexity
- **Timer**: Wait for specialist assignment
- **Notification**: Alerts and customer responses

### 4. Graceful Fallbacks

Always include default handling:

```yaml
conditions:
  - expression: "..."
    next: known-path
  - default: true
    next: safe-fallback  # Never leave execution stuck
```

## Design Patterns

### Pattern 1: Priority Routing

```yaml
conditions:
  - expression: "{{input.priority}} == 'critical'"
    next: immediate-escalation
  - expression: "{{input.priority}} == 'high'"
    next: urgent-queue
  - expression: "{{input.priority}} == 'medium'"
    next: standard-queue
  - default: true
    next: low-priority-queue
```

### Pattern 2: Threshold-Based Routing

```yaml
conditions:
  - expression: "{{steps.score.output.value}} >= 90"
    next: excellent-path
  - expression: "{{steps.score.output.value}} >= 70"
    next: good-path
  - expression: "{{steps.score.output.value}} >= 50"
    next: acceptable-path
  - default: true
    next: needs-improvement-path
```

### Pattern 3: Multi-Factor Routing

Use nested gateways for complex decisions:

```yaml
# First gateway: Check priority
- id: priority-check
  type: gateway
  conditions:
    - expression: "{{input.priority}} == 'urgent'"
      next: urgency-assessment
    - default: true
      next: standard-flow

# Second gateway: Check customer tier (for urgent only)
- id: urgency-assessment
  type: gateway
  depends_on: [priority-check]
  conditions:
    - expression: "{{input.tier}} == 'enterprise'"
      next: vip-handling
    - default: true
      next: urgent-standard-handling
```

## Best Practices

### 1. Clear Condition Logic

```yaml
# ✅ Good: Clear, mutually exclusive conditions
conditions:
  - expression: "{{status}} == 'approved'"
    next: proceed
  - expression: "{{status}} == 'rejected'"
    next: revise

# ❌ Avoid: Overlapping conditions
conditions:
  - expression: "{{score}} > 50"
    next: path-a
  - expression: "{{score}} > 70"  # Never reached if score is 80!
    next: path-b
```

### 2. Document Complex Flows

Add comments explaining the logic:

```yaml
# ROUTING LOGIC:
# - Simple tickets (FAQ, password reset) → Auto-resolve
# - Medium tickets (billing, account) → Human review
# - Complex tickets (technical, enterprise) → Specialist
- id: complexity-router
  type: gateway
```

### 3. Test All Paths

Create test inputs that exercise each branch to ensure no dead ends.

## What's Next?

Congratulations! You've completed the Trinity Process Engine learning path. You can now:

- ✅ Create sequential workflows
- ✅ Run steps in parallel
- ✅ Add human approval checkpoints
- ✅ Build complex branching logic

### Continue Learning

- [Pattern Documentation](/processes/docs/patterns/sequential) — Explore more patterns
- [YAML Schema Reference](/processes/docs/reference/yaml-schema) — Complete field reference
- [Process Engine Roadmap](/processes/docs/reference/roadmap) — See what's coming next
