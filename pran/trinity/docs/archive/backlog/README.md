# Trinity Backlog

This folder contains documented backlog items for future development. Each item is designed to be picked up by an AI agent or human developer with full context.

---

## Backlog Item Format

Each item follows this structure:

- **Summary** - One-line description
- **Problem Description** - What's wrong or what's needed
- **Root Cause Analysis** - Technical investigation findings
- **Files to Modify** - Specific code locations
- **Proposed Solutions** - Implementation options with pros/cons
- **Acceptance Criteria** - Definition of done
- **Testing Plan** - How to verify the fix

---

## Current Backlog Items

| ID | Title | Priority | Type | Status |
|----|-------|----------|------|--------|
| 001 | [Claude Context Window Display Bug](./001-claude-context-window-display-bug.md) | High | Bug | Open |
| 002 | [Unified Context Reporting](./002-unified-context-reporting.md) | Medium | Enhancement | Open |

---

## Priority Levels

- **Critical** - Blocks core functionality, needs immediate attention
- **High** - Significant user impact, should be addressed soon
- **Medium** - Important improvement, can wait for appropriate sprint
- **Low** - Nice to have, address when time permits

---

## For AI Agents

When picking up a backlog item:

1. **Read the full document** - All context is provided
2. **Check dependencies** - Some items depend on others
3. **Follow the testing plan** - Verify your fix works
4. **Update status** - Mark as "In Progress" or "Done"
5. **Document changes** - Add notes about implementation decisions

---

## Adding New Items

Use the next available ID (e.g., `003-feature-name.md`) and follow the existing format. Include:

- All investigation findings
- Specific file paths and line numbers
- Code snippets showing current behavior
- Proposed code changes
- Clear acceptance criteria

