# Adding Human Checkpoints

Automated workflows are powerful, but sometimes you need a human in the loop. This tutorial shows how to add approval gates that pause execution until someone reviews and approves.

## What You'll Learn

- How to add `human_approval` steps
- How to handle approval and rejection
- How to route based on the decision
- How to set timeouts and timeout actions

## Prerequisites

Before starting:
- ✅ Completed "Your First Process" tutorial
- ✅ Understanding of sequential steps with `depends_on`

## What We'll Build

A content review workflow that:
1. Generates a draft
2. **Pauses for human review**
3. Publishes if approved, OR revises if rejected

```
┌───────────┐    ┌─────────────┐    ┌───────────┐
│  Draft    │───►│   REVIEW    │───►│  Publish  │
│  (Agent)  │    │   (Human)   │    │  (Agent)  │
└───────────┘    └──────┬──────┘    └───────────┘
                        │
                        ▼ (if rejected)
                 ┌─────────────┐
                 │   Revise    │
                 │   (Agent)   │
                 └─────────────┘
```

## Step 1: Create the Process

Navigate to **Processes** → **Create Process** and enter:

```yaml
name: content-review-workflow
version: "1.0"
description: Generate content with human review before publishing

triggers:
  - type: manual
    id: start-review

steps:
  # Step 1: Generate the initial draft
  - id: generate-draft
    name: Generate Draft
    type: agent_task
    agent: your-agent-name  # Replace with your agent
    message: |
      Write a {{input.content_type}} about: {{input.topic}}

      Requirements:
      - Length: {{input.word_count | default:500}} words
      - Tone: {{input.tone | default:"professional"}}
      - Include a compelling introduction
      - End with a call to action
    timeout: 10m

  # Step 2: Human approval gate
  - id: editorial-review
    name: Editorial Review
    type: human_approval
    depends_on: [generate-draft]
    title: "Review: {{input.topic}}"
    description: |
      ## Content for Review

      **Type**: {{input.content_type}}
      **Topic**: {{input.topic}}

      ---

      {{steps.generate-draft.output}}

      ---

      ## Review Checklist

      Please verify:
      - [ ] Content is accurate
      - [ ] Tone is appropriate
      - [ ] No spelling/grammar errors
      - [ ] Call to action is clear

      **Approve** to publish, or **Reject** with feedback for revision.
    timeout: 24h
    timeout_action: skip

  # Step 3: Gateway to route based on decision
  - id: review-decision
    name: Route Decision
    type: gateway
    depends_on: [editorial-review]
    conditions:
      - expression: "{{steps.editorial-review.output.decision}} == 'approved'"
        next: publish-content
      - expression: "{{steps.editorial-review.output.decision}} == 'rejected'"
        next: revise-draft
      - default: true
        next: publish-content  # If timeout skipped, publish anyway

  # Step 4a: Publish (if approved)
  - id: publish-content
    name: Publish Content
    type: agent_task
    agent: your-agent-name
    message: |
      Format and publish this approved content:

      {{steps.generate-draft.output}}

      Add appropriate formatting for {{input.platform | default:"blog"}}.
    timeout: 5m

  # Step 4b: Revise (if rejected)
  - id: revise-draft
    name: Revise Draft
    type: agent_task
    agent: your-agent-name
    message: |
      Revise this content based on reviewer feedback:

      ## Original Draft
      {{steps.generate-draft.output}}

      ## Reviewer Feedback
      {{steps.editorial-review.output.comments}}

      Address all feedback and improve the content.
    timeout: 10m

outputs:
  - name: final_content
    source: "{{steps.publish-content.output | default:steps.revise-draft.output}}"
  - name: review_decision
    source: "{{steps.editorial-review.output.decision}}"
  - name: reviewer_comments
    source: "{{steps.editorial-review.output.comments}}"
```

> **Important**: Replace `your-agent-name` with your actual agent name.

## Step 2: Understanding the Approval Step

Let's break down the `human_approval` configuration:

```yaml
- id: editorial-review
  type: human_approval
  title: "Review: {{input.topic}}"      # Shows in approval list
  description: |                         # What reviewer sees
    ## Content for Review
    {{steps.generate-draft.output}}
  timeout: 24h                           # Max wait time
  timeout_action: skip                   # What happens if no response
```

### Approval Outcome Fields

After review, these fields are available:

| Field | Description |
|-------|-------------|
| `decision` | `"approved"` or `"rejected"` |
| `comments` | Reviewer's notes |
| `approved_by` | Who made the decision |

## Step 3: Run and Approve

1. **Save and Publish** the process
2. Click **Play** and enter:

```json
{
  "topic": "Benefits of remote work",
  "content_type": "blog post",
  "word_count": 400
}
```

3. Watch the execution pause at "Editorial Review"

## Step 4: Make the Approval Decision

1. Navigate to **Approvals** in the sidebar
2. Find your pending approval
3. Read the content in the description
4. Add comments (optional)
5. Click **Approve** or **Reject**

### If You Approve:
- Execution continues to `publish-content`
- Final content is published

### If You Reject:
- Execution routes to `revise-draft`
- Agent revises based on your feedback
- (In a real workflow, you might loop back for re-review)

## Key Concepts

### 1. Writing Good Descriptions

Give reviewers context:

```yaml
description: |
  ## What to Review
  {{steps.draft.output}}

  ## Context
  This is for {{input.audience}}.

  ## Decision Criteria
  - Accurate information
  - Appropriate tone
  - Clear call to action
```

### 2. Timeout Handling

What happens if no one responds?

```yaml
timeout: 24h              # Wait up to 24 hours
timeout_action: skip      # Then skip this step
```

Options for `timeout_action`:
- `skip` — Continue without decision (default)
- `approve` — Auto-approve after timeout
- `reject` — Auto-reject after timeout

### 3. Routing with Gateway

Use a `gateway` step to branch based on the decision:

```yaml
- id: decision-gate
  type: gateway
  depends_on: [review-step]
  conditions:
    - expression: "{{steps.review-step.output.decision}} == 'approved'"
      next: approved-path
    - expression: "{{steps.review-step.output.decision}} == 'rejected'"
      next: rejected-path
```

### 4. Accessing Reviewer Feedback

Use the feedback in revision steps:

```yaml
message: |
  Address this feedback:
  {{steps.editorial-review.output.comments}}

  From reviewer: {{steps.editorial-review.output.approved_by}}
```

## Advanced: Multi-Level Approval

For sensitive content, require multiple approvals:

```yaml
steps:
  - id: draft
    # ... generate content ...

  - id: peer-review
    type: human_approval
    depends_on: [draft]
    title: "Peer Review"
    timeout: 24h

  - id: manager-review
    type: human_approval
    depends_on: [peer-review]
    title: "Manager Approval"
    description: |
      Peer review passed by: {{steps.peer-review.output.approved_by}}

      Content: {{steps.draft.output}}
    timeout: 48h

  - id: publish
    depends_on: [manager-review]
    # ... publish ...
```

## Try It Yourself

1. **Add a second review**: Require both peer and manager approval
2. **Change the timeout**: Try `timeout: 5m` for testing
3. **Auto-approve urgent content**: Use `timeout_action: approve`

## What's Next?

Ready for more complex logic? Learn to build workflows with multiple conditional paths:

→ [Complex Workflows](./complex-workflows) — Gateways and conditional branching

## Related

- [Approval Workflows Pattern](/processes/docs/patterns/approvals) — Deep dive into approvals
- [Human Approval Step Type](/processes/docs/getting-started/step-types#human-approval) — Complete reference
