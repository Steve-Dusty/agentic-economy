# Onboarding Feature Manual Tests

> **Purpose**: Validate the onboarding and documentation features
> **Sprint**: 7, 8, 8.5, 9
> **Features**: Empty states, checklist, docs tab, contextual help

---

## Test Checklist

### UI Navigation Tests

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| O1.1 | Fresh start - Empty state | See welcome message + template cards | ⬜ |
| O1.2 | Onboarding checklist visible | Floating checklist in bottom-right | ⬜ |
| O1.3 | Docs tab accessible | Navigate to `/processes/docs` | ⬜ |
| O1.4 | Documentation content loads | Markdown renders correctly | ⬜ |

### Empty State Tests

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| O2.1 | Template cards display | 3 cards: Content, Data, Support | ⬜ |
| O2.2 | Click template card | Opens editor with template YAML | ⬜ |
| O2.3 | "Create from Scratch" button | Opens empty editor | ⬜ |
| O2.4 | "Import YAML" button | Opens import modal | ⬜ |
| O2.5 | Docs link in empty state | Navigates to docs | ⬜ |

### Onboarding Checklist Tests

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| O3.1 | Checklist shows 5 items | 3 required + 2 optional | ⬜ |
| O3.2 | Progress indicator | Shows "0 of 3 complete" | ⬜ |
| O3.3 | Create process → checked | First item auto-completes | ⬜ |
| O3.4 | Run execution → checked | Second item auto-completes | ⬜ |
| O3.5 | Checklist minimize | Can collapse/expand | ⬜ |
| O3.6 | Checklist dismiss | Can hide after completion | ⬜ |
| O3.7 | "See above ↑" hint | Shows when already on target page | ⬜ |
| O3.8 | Restart from Docs page | Button resets checklist | ⬜ |

### Documentation Tests

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| O4.1 | Getting Started loads | 3 docs: What, First Process, Step Types | ⬜ |
| O4.2 | Tutorials load | 3 docs: Parallel, Checkpoints, Complex | ⬜ |
| O4.3 | Patterns load | 3 docs: Sequential, Parallel, Approvals | ⬜ |
| O4.4 | Reference load | 4 docs: Schema, Variables, Triggers, Errors | ⬜ |
| O4.5 | Troubleshooting load | 1 doc: Common Errors | ⬜ |
| O4.6 | Next/Previous navigation | Footer links work | ⬜ |
| O4.7 | Sidebar expansion | Sections expand/collapse | ⬜ |
| O4.8 | Search placeholder | Shows "coming soon" message | ⬜ |

### Editor Help Panel Tests

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| O5.1 | Help panel toggle | ? button shows/hides panel | ⬜ |
| O5.2 | Cursor on `name:` | Shows "Process Name" help | ⬜ |
| O5.3 | Cursor on `steps:` | Shows "Steps" help | ⬜ |
| O5.4 | Cursor on `depends_on:` | Shows "Dependencies" help | ⬜ |
| O5.5 | Help shows type/required | Metadata displays correctly | ⬜ |
| O5.6 | Help shows example | Code example visible | ⬜ |
| O5.7 | "Learn more" link | Navigates to docs | ⬜ |
| O5.8 | Panel state persists | Remembers open/closed | ⬜ |

### Status Explainer Tests

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| O6.1 | Pending status tooltip | "Waiting to start..." | ⬜ |
| O6.2 | Running status tooltip | "Execution in progress" | ⬜ |
| O6.3 | Paused status tooltip | "Awaiting approval" + link hint | ⬜ |
| O6.4 | Completed status tooltip | "All steps finished" | ⬜ |
| O6.5 | Failed status tooltip | Shows error context | ⬜ |
| O6.6 | Step status tooltips | Show in timeline | ⬜ |

---

## Test Execution Steps

### Preparation

1. Clear database (done via script)
2. Clear localStorage: `localStorage.clear()` in browser console
3. Refresh page

### Quick Test Path

1. **O1.1**: Navigate to `/processes` - should see empty state
2. **O1.2**: Check for floating checklist
3. **O2.2**: Click "Content Pipeline" template
4. **O5.1**: Toggle help panel with ? button
5. **O5.2**: Click on `name:` field, verify help shows
6. Save process, verify checklist updates (O3.3)
7. Publish and execute process
8. **O6.1-O6.5**: Check status tooltips during execution
9. **O1.3**: Navigate to Docs tab
10. **O4.1**: Verify Getting Started docs load
11. **O3.8**: Click "Restart Getting Started" button

---

## Test Process Definition

For testing the full flow, use this simple process:

```yaml
name: onboarding-test
version: "1.0"
description: Simple process for onboarding testing

triggers:
  - type: manual
    id: manual-start

steps:
  - id: step-one
    name: First Step
    type: agent_task
    agent: test-echo
    message: |
      Echo this message back: "Hello from onboarding test!"
    timeout: 5m
```

---

## Notes

- Tests marked ⬜ are pending
- Tests marked ✅ passed
- Tests marked ❌ failed (add notes)
