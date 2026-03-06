# Development Workflow

> **For developers and AI assistants** working on this project.
> This guide explains how to use the project's tools, agents, and documentation effectively.

---

## The Development Cycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DEVELOPMENT CYCLE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   1. CONTEXT LOADING                                                │
│      ↓                                                              │
│   /read-docs → Load requirements, architecture, roadmap             │
│      ↓                                                              │
│   Read relevant feature-flows/* for the area you'll work on         │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   2. DEVELOPMENT                                                    │
│      ↓                                                              │
│   Implement changes following existing patterns                     │
│      ↓                                                              │
│   Reference feature flows for data flow understanding               │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   3. TESTING                                                        │
│      ↓                                                              │
│   test-runner agent → Run test suite (required)                     │
│      ↓                                                              │
│   Manual verification → UI/API tests (recommended)                  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   4. DOCUMENTATION                                                  │
│      ↓                                                              │
│   feature-flow-analyzer agent → Create/update feature flows         │
│      ↓                                                              │
│   /update-docs → Update changelog, architecture, requirements       │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   5. PR VALIDATION (before merge)                                   │
│      ↓                                                              │
│   /validate-pr → Validate PR meets all methodology requirements     │
│      ↓                                                              │
│   Review report → APPROVE / REQUEST CHANGES / NEEDS DISCUSSION      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Context Loading

**Always start a development session by loading context.**

### Option A: Full Context Load (New Session)

Use the `/read-docs` command:

```
/read-docs
```

This loads:
- `docs/memory/requirements.md` - Feature requirements (source of truth)
- `docs/memory/architecture.md` - System design
- `docs/memory/roadmap.md` - Current priorities
- `docs/memory/changelog.md` - Recent changes

### Option B: Targeted Context (Specific Feature Work)

If you know what you're working on, load the relevant feature flow directly:

```
# Example: Working on user authentication
@docs/memory/feature-flows/user-login.md

# Example: Working on data export
@docs/memory/feature-flows/data-export.md
```

### Available Feature Flows

See `docs/memory/feature-flows.md` for the complete index.

---

## Phase 2: Development

### Before Writing Code

1. **Check requirements**: Does `requirements.md` cover this feature?
2. **Check roadmap**: Is this the current priority?
3. **Read feature flow**: Understand existing data flow before modifying

### During Development

- Follow patterns established in existing code
- Reference feature flows for:
  - API endpoint locations
  - Database operations
  - Event handling
  - Error handling patterns
- Use the TodoWrite tool to track multi-step tasks

---

## Phase 3: Testing

**Every development session must end with testing.**

### Minimum: Run Test Suite

Use the `test-runner` agent:

```
Run the tests
```

This runs the test suite and reports:
- Pass/fail counts
- Failure analysis
- Recommendations

**Test Tiers:**
- **Smoke tests** (~1min): Quick validation
- **Core tests** (~5min): Standard validation (default)
- **Full suite** (~15min): Comprehensive coverage

### Manual Verification

For quick checks during development:

```bash
# Application running?
curl http://localhost:8000/health

# Test specific endpoint
curl http://localhost:8000/api/endpoint
```

---

## Phase 4: Documentation

**After tests pass, update documentation.**

### If You Modified Feature Behavior

**Use the `feature-flow-analyzer` agent:**

```
Analyze and update the feature flow for user-login
```

Or use the command:

```
/feature-flow-analysis user-login
```

This will:
1. Trace the feature from UI → Backend → Database
2. Update or create `docs/memory/feature-flows/{feature}.md`
3. Update the feature flows index

### For All Changes

**Use the `/update-docs` command:**

```
/update-docs
```

Claude Code will determine which documents need updates:

| Document | When to Update |
|----------|----------------|
| `changelog.md` | Always - add timestamped entry |
| `architecture.md` | API changes, schema changes, new integrations |
| `requirements.md` | New features, scope changes |
| `roadmap.md` | Task completion, new discoveries |
| `feature-flows/*.md` | Behavior changes (use analyzer) |

---

## Sub-Agents Reference

### When to Use Each Agent

| Agent | Use When |
|-------|----------|
| `test-runner` | After development to validate changes |
| `feature-flow-analyzer` | After modifying feature behavior |
| `security-analyzer` | Before commits touching auth, credentials, or APIs |

### Invoking Agents

Agents are invoked automatically by Claude Code when appropriate, or you can request them:

```
# Run tests
Use the test-runner agent to run the tests

# Analyze a feature
Use the feature-flow-analyzer to document the user-login feature

# Security check
Use the security-analyzer to review the auth code
```

---

## Slash Commands Reference

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/read-docs` | Load project context | Start of session |
| `/update-docs` | Update documentation | After changes |
| `/feature-flow-analysis <feature>` | Document feature flow | After modifying features |
| `/security-check` | Validate no secrets in staged files | Before every commit |
| `/add-testing` | Add tests for a feature | Improving coverage |
| `/validate-pr <number>` | Validate PR against methodology | Before merging PRs |

---

## Memory Files Explained

The `docs/memory/` directory contains persistent project state:

```
docs/memory/
├── requirements.md      ← SINGLE SOURCE OF TRUTH for features
├── architecture.md      ← Current system design (~1000 lines max)
├── roadmap.md           ← Prioritized task queue
├── changelog.md         ← Timestamped history (~500 lines)
├── feature-flows.md     ← Index of all feature flow documents
└── feature-flows/       ← Individual feature documentation
    ├── user-login.md
    ├── data-export.md
    └── ... (more flows)
```

### How They Work Together

```
requirements.md  ──defines──►  What features exist
       │
       ▼
roadmap.md       ──prioritizes──►  What to work on next
       │
       ▼
feature-flows/*  ──documents──►  How features work
       │
       ▼
changelog.md     ──records──►  What changed and when
       │
       ▼
architecture.md  ──maintains──►  Current system state
```

---

## Example Development Session

### Scenario: Add a new field to user profile

```
# 1. CONTEXT LOADING
You: /read-docs
You: Also read the user-profile feature flow

# 2. DEVELOPMENT
You: Add an "avatar" field to user profiles

Claude: [Reads feature flow, implements changes across frontend/backend]

# 3. TESTING
You: Run the tests to make sure nothing broke

Claude: [Invokes test-runner agent, reports results]

# 4. DOCUMENTATION
You: Update the feature flow for user-profile and update docs

Claude: [Invokes feature-flow-analyzer, then /update-docs]
```

### Scenario: Fix a bug in data export

```
# 1. CONTEXT LOADING
You: @docs/memory/feature-flows/data-export.md
You: The CSV export isn't including timestamps

# 2. DEVELOPMENT
Claude: [Reads flow, traces issue, implements fix]

# 3. TESTING
You: Test it

Claude: [Runs relevant tests, verifies fix]

# 4. DOCUMENTATION
You: Update the docs

Claude: [Updates changelog, possibly updates feature flow if behavior changed]
```

---

## Development Skills

Skills are methodology guides in `.claude/skills/` that define HOW to approach specific tasks.

### Available Skills

| Skill | Purpose | When to Apply |
|-------|---------|---------------|
| `verification` | Evidence-based completion claims | Before saying "done" or "fixed" |
| `systematic-debugging` | Root cause investigation | When fixing bugs or failures |
| `tdd` | Test-driven development | When writing new code |
| `code-review` | Receiving review feedback | When responding to PR comments |

### Key Principles

**Verification**: No completion claims without evidence. Run the command, show the output.

**Debugging**: Find root cause BEFORE attempting fixes. No quick patches.

**TDD**: Write failing test first, then minimal code to pass.

**Code Review**: Technical rigor over social comfort. Verify before implementing.

See `.claude/skills/{name}/SKILL.md` for full methodology guides.

---

## Best Practices

### DO

- ✅ Always load context before starting work
- ✅ Read feature flows before modifying features
- ✅ Run tests after every significant change
- ✅ Update feature flows when behavior changes
- ✅ Use sub-agents for specialized tasks
- ✅ Keep changelog entries concise but informative
- ✅ Run `/security-check` before every commit
- ✅ Run `/validate-pr` before approving any PR
- ✅ Provide evidence with completion claims (verification skill)
- ✅ Investigate root cause before fixing bugs (debugging skill)

### DON'T

- ❌ Skip context loading ("I remember from last time")
- ❌ Modify features without reading their flow
- ❌ Commit without running tests
- ❌ Leave feature flows outdated after changes
- ❌ Write new documentation files without being asked
- ❌ Over-document - keep it minimal and useful
- ❌ Merge PRs without running validation
- ❌ Claim "done" without showing verification output
- ❌ Guess at bug fixes without root cause analysis

---

## Phase 5: PR Validation

**Before merging any PR, validate it meets all methodology requirements.**

### Run PR Validation

```
/validate-pr 42
```

Or with full URL:
```
/validate-pr https://github.com/org/repo/pull/42
```

### What Gets Validated

| Category | Validation |
|----------|------------|
| **Changelog** | Entry exists with timestamp and emoji |
| **Roadmap** | Updated if task completed or new work discovered |
| **Requirements** | Updated if new feature or scope change |
| **Architecture** | Updated if API/schema/integration changes |
| **Feature Flows** | Created/updated for behavior changes, correct format |
| **Security** | No secrets, keys, emails, IPs in diff |
| **Code Quality** | Minimal changes, follows patterns |
| **Traceability** | Links to requirements |

### Validation Report

The command generates a structured report with:
- Summary table showing pass/fail for each category
- Documentation and security checklists
- Issues found (Critical, Warnings, Suggestions)
- **Recommendation**: APPROVE / REQUEST CHANGES / NEEDS DISCUSSION

### Example Workflow

```
# Reviewer receives PR notification
You: /validate-pr 42

# Claude analyzes and generates report
Claude: ## PR Validation Report
        ...
        ### Recommendation
        **REQUEST CHANGES**
        - [ ] Changelog entry missing
        - [ ] Feature flow needs Testing section

# Reviewer posts comment with required changes
# Developer fixes and requests re-review
# Reviewer runs /validate-pr 42 again
```

---

## Quick Start Checklist

For every development session:

- [ ] Load context (`/read-docs` or read relevant feature flows)
- [ ] Understand what you're modifying (read the feature flow)
- [ ] Implement changes
- [ ] Run tests (`test-runner` agent)
- [ ] Update feature flow if behavior changed (`feature-flow-analyzer` agent)
- [ ] Update documentation (`/update-docs`)
- [ ] Run security check before commit (`/security-check`)

For PR reviews:

- [ ] Run `/validate-pr <number>` before approving
- [ ] Verify all Critical issues resolved
- [ ] Review Warnings with human judgment
- [ ] Approve only when report shows all ✅
