# Approval Workflows

Approval workflows add human checkpoints to your automated processes. They're essential for quality gates, compliance requirements, and decisions that need human judgment.

## The Pattern

```
┌──────────┐    ┌──────────────┐    ┌──────────┐
│  Draft   │───►│   Approval   │───►│ Publish  │
│  (Agent) │    │   (Human)    │    │  (Agent) │
└──────────┘    └──────────────┘    └──────────┘
                      │
                      ▼
               ┌──────────────┐
               │  Approved?   │
               └──────┬───────┘
                      │
              ┌───────┴───────┐
              ▼               ▼
        [Continue]       [Reject/Revise]
```

## When to Use Approvals

Add human approval steps when:
- Quality must be verified before publishing
- Compliance requirements mandate human review
- High-stakes decisions need sign-off
- Content should be reviewed before going live
- Budget or resource allocation needs authorization

## Basic Approval Gate

```yaml
name: content-with-approval
version: "1.0"

steps:
  - id: draft
    type: agent_task
    agent: writer
    message: |
      Write a blog post about: {{input.topic}}
      Target length: {{input.word_count | default:800}} words

  - id: editorial-review
    type: human_approval
    depends_on: [draft]
    title: Editorial Review Required
    description: |
      Please review this blog post draft:

      {{steps.draft.output}}

      Check for:
      - Accuracy of information
      - Tone and voice consistency
      - Grammar and clarity

      Approve to publish, or reject with feedback.
    timeout: 24h

  - id: publish
    type: agent_task
    depends_on: [editorial-review]
    agent: publisher
    message: |
      Publish this approved content:
      {{steps.draft.output}}

outputs:
  - name: published_content
    source: "{{steps.publish.output}}"
```

## Approval Step Fields

### Required Fields

| Field | Description |
|-------|-------------|
| `type` | Must be `human_approval` |
| `title` | Short title shown in approval UI |
| `description` | Detailed description with context for reviewer |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `timeout` | Time to wait for response | `24h` |
| `timeout_action` | What happens on timeout: `approve`, `reject`, or `skip` | `skip` |

## Handling Approval Decisions

### Accessing the Decision

After an approval step, access the decision in subsequent steps:

```yaml
- id: next-step
  depends_on: [approval-step]
  message: |
    The reviewer {{steps.approval-step.output.decision}}.

    Comments: {{steps.approval-step.output.comments | default:"No comments"}}

    Approved by: {{steps.approval-step.output.approved_by}}
```

### Conditional Paths Based on Decision

Use a gateway to route based on approval outcome:

```yaml
steps:
  - id: draft
    type: agent_task
    agent: writer
    message: Create draft content

  - id: review
    type: human_approval
    depends_on: [draft]
    title: Content Review
    description: Review the draft for quality

  - id: decision-gate
    type: gateway
    depends_on: [review]
    conditions:
      - expression: "{{steps.review.output.decision}} == 'approved'"
        next: publish
      - expression: "{{steps.review.output.decision}} == 'rejected'"
        next: revise

  - id: publish
    type: agent_task
    agent: publisher
    message: Publish: {{steps.draft.output}}

  - id: revise
    type: agent_task
    agent: writer
    message: |
      Revise the draft based on feedback:

      Original: {{steps.draft.output}}

      Feedback: {{steps.review.output.comments}}
```

## Multi-Level Approval Chains

For sensitive workflows, require multiple approvals:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Create  │───►│ Manager  │───►│ Director │───►│ Execute  │
│  Request │    │ Approval │    │ Approval │    │  Action  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

```yaml
name: budget-approval-chain
version: "1.0"

steps:
  - id: create-request
    type: agent_task
    agent: request-processor
    message: |
      Prepare budget request for:
      Amount: ${{input.amount}}
      Purpose: {{input.purpose}}
      Department: {{input.department}}

  - id: manager-approval
    type: human_approval
    depends_on: [create-request]
    title: "Manager Approval - ${{input.amount}}"
    description: |
      Budget Request Details:
      {{steps.create-request.output}}

      Please review and approve or reject.
    timeout: 48h

  - id: check-manager-decision
    type: gateway
    depends_on: [manager-approval]
    conditions:
      - expression: "{{steps.manager-approval.output.decision}} == 'approved'"
        next: director-approval
      - default: true
        next: request-rejected

  - id: director-approval
    type: human_approval
    title: "Director Final Approval - ${{input.amount}}"
    description: |
      Budget Request (Manager Approved):
      {{steps.create-request.output}}

      Manager notes: {{steps.manager-approval.output.comments}}

      Final approval required.
    timeout: 72h

  - id: check-director-decision
    type: gateway
    depends_on: [director-approval]
    conditions:
      - expression: "{{steps.director-approval.output.decision}} == 'approved'"
        next: execute-budget
      - default: true
        next: request-rejected

  - id: execute-budget
    type: agent_task
    agent: finance-processor
    message: |
      Execute approved budget allocation:
      {{steps.create-request.output}}

      Approved by:
      - Manager: {{steps.manager-approval.output.approved_by}}
      - Director: {{steps.director-approval.output.approved_by}}

  - id: request-rejected
    type: agent_task
    agent: notification-agent
    message: |
      Notify requester that budget request was rejected.
      Original request: {{steps.create-request.output}}
```

## Timeout Handling

### Timeout Actions

| Action | Behavior |
|--------|----------|
| `skip` | Step is skipped, execution continues (default) |
| `approve` | Auto-approve after timeout |
| `reject` | Auto-reject after timeout |

```yaml
- id: urgent-review
  type: human_approval
  title: Urgent Review Required
  description: Time-sensitive content needs review
  timeout: 2h
  timeout_action: approve  # Auto-approve if no response in 2 hours
```

### Timeout Notification Pattern

Combine timer with approval for reminder workflows:

```yaml
steps:
  - id: initial-request
    type: human_approval
    title: Review Required
    description: Please review this content
    timeout: 4h
    timeout_action: skip

  - id: check-initial
    type: gateway
    depends_on: [initial-request]
    conditions:
      - expression: "{{steps.initial-request.status}} == 'skipped'"
        next: send-reminder
      - default: true
        next: process-decision

  - id: send-reminder
    type: agent_task
    agent: notifier
    message: Send escalation reminder - review still pending

  - id: escalated-request
    type: human_approval
    depends_on: [send-reminder]
    title: "[ESCALATED] Review Required"
    description: This review has been pending. Please respond.
    timeout: 2h
    timeout_action: reject
```

## Approval with Rich Context

Provide reviewers with comprehensive information:

```yaml
- id: comprehensive-review
  type: human_approval
  depends_on: [analysis, risk-assessment, cost-estimate]
  title: "Project Approval: {{input.project_name}}"
  description: |
    ## Project Overview
    {{input.description}}

    ## Analysis Summary
    {{steps.analysis.output}}

    ## Risk Assessment
    {{steps.risk-assessment.output}}

    ## Cost Estimate
    {{steps.cost-estimate.output}}

    ---

    **Decision Required**: Approve to proceed with project initiation.

    **Approval Criteria**:
    - [ ] Risk level is acceptable
    - [ ] Budget is within limits
    - [ ] Timeline is feasible
    - [ ] Resources are available
  timeout: 72h
```

## Best Practices

### 1. Write Clear Descriptions

```yaml
# ✅ Good: Clear context and decision criteria
description: |
  Please review this marketing email before it's sent to 50,000 subscribers.

  Email content:
  {{steps.draft-email.output}}

  Check for:
  - Brand voice consistency
  - No spelling/grammar errors
  - Links work correctly
  - Unsubscribe link present

  Approve to send, or reject with specific feedback.

# ❌ Bad: Vague
description: Review this and approve if OK.
```

### 2. Set Appropriate Timeouts

| Scenario | Recommended Timeout |
|----------|-------------------|
| Urgent review | 1-4 hours |
| Standard review | 24-48 hours |
| Complex decision | 48-72 hours |
| Low-priority | 1 week |

### 3. Consider the Reviewer's Context

The reviewer sees only what's in the description. Include:
- What they're reviewing
- Why it needs review
- What to look for
- What happens after approval/rejection

### 4. Use Meaningful Titles

```yaml
# ✅ Good: Informative
title: "Content Review: {{input.article_title}}"
title: "Budget Approval: ${{input.amount}} for {{input.department}}"

# ❌ Bad: Generic
title: "Approval needed"
title: "Please review"
```

## Example: Complete Review Workflow

```yaml
name: document-review-workflow
version: "1.0"
description: Multi-stage document review with revision loop

steps:
  - id: create-document
    type: agent_task
    agent: document-writer
    message: |
      Create a {{input.document_type}} document about:
      {{input.subject}}

  - id: peer-review
    type: human_approval
    depends_on: [create-document]
    title: "Peer Review: {{input.document_type}}"
    description: |
      ## Document for Peer Review

      {{steps.create-document.output}}

      ---

      Please review for:
      - Technical accuracy
      - Clarity of explanation
      - Completeness

      Provide detailed feedback if rejecting.
    timeout: 48h

  - id: route-after-peer
    type: gateway
    depends_on: [peer-review]
    conditions:
      - expression: "{{steps.peer-review.output.decision}} == 'approved'"
        next: final-approval
      - default: true
        next: revise-document

  - id: revise-document
    type: agent_task
    agent: document-writer
    message: |
      Revise the document based on peer feedback:

      Original document:
      {{steps.create-document.output}}

      Feedback to address:
      {{steps.peer-review.output.comments}}

  - id: re-review
    type: human_approval
    depends_on: [revise-document]
    title: "Re-review: Revised Document"
    description: |
      ## Revised Document

      {{steps.revise-document.output}}

      ---

      Previous feedback:
      {{steps.peer-review.output.comments}}

      Please verify feedback was addressed.
    timeout: 24h

  - id: final-approval
    type: human_approval
    title: "Final Approval: {{input.document_type}}"
    description: |
      ## Document Ready for Final Approval

      {{steps.create-document.output}}

      ---

      Peer review: Approved

      Please provide final sign-off for publication.
    timeout: 24h

  - id: publish
    type: agent_task
    depends_on: [final-approval]
    agent: publisher
    message: |
      Publish the approved document:
      {{steps.create-document.output}}

outputs:
  - name: final_document
    source: "{{steps.publish.output}}"
  - name: approval_chain
    source: |
      Peer: {{steps.peer-review.output.approved_by}}
      Final: {{steps.final-approval.output.approved_by}}
```

## Related

- [Sequential Workflows](./sequential) — Linear execution patterns
- [Parallel Execution](./parallel) — Run steps simultaneously
- [Understanding Step Types](/processes/docs/getting-started/step-types) — All step types reference
