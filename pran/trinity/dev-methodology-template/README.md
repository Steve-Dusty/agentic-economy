# Claude Code Development Methodology Template

A reusable development methodology kit for Claude Code projects. Provides slash commands, sub-agents, memory files, and documentation templates to enforce disciplined, traceable development practices.

## What's Included

| Category | Contents |
|----------|----------|
| **Commands** | 6 slash commands: `/read-docs`, `/update-docs`, `/feature-flow-analysis`, `/add-testing`, `/security-check`, `/validate-pr` |
| **Agents** | 3 sub-agents: `feature-flow-analyzer`, `test-runner`, `security-analyzer` |
| **Skills** | 4 methodology guides: `verification`, `systematic-debugging`, `tdd`, `code-review` |
| **Memory Files** | Templates for requirements, architecture, roadmap, changelog, feature flows |
| **Workflow** | Development cycle documentation and testing guide |
| **Testing** | Phase-based testing framework templates |

## Quick Start

### 1. Copy to Your Project

```bash
# From your project root
cp -r path/to/dev-methodology-template/.claude .claude
cp -r path/to/dev-methodology-template/docs docs
cp path/to/dev-methodology-template/templates/CLAUDE.md.template CLAUDE.md
```

### 2. Configure Placeholders

Edit `CLAUDE.md` and replace:

| Placeholder | Replace With |
|-------------|--------------|
| `{{PROJECT_NAME}}` | Your project name |
| `{{PROJECT_DESCRIPTION}}` | One-line description |
| `{{REPO_URL}}` | GitHub repository URL |
| `{{BACKEND_URL}}` | API URL (e.g., `http://localhost:8000`) |
| `{{FRONTEND_URL}}` | Web UI URL (e.g., `http://localhost:3000`) |

### 3. Initialize Memory Files

```bash
# Remove .template extension and fill in initial content
cd docs/memory
for f in *.template; do mv "$f" "${f%.template}"; done
```

Edit each file to add your project's initial state.

## Directory Structure

```
your-project/
├── CLAUDE.md                    # Project instructions (from template)
├── CLAUDE.local.md              # Local/private config (gitignored)
├── .claude/
│   ├── commands/                # Slash commands
│   │   ├── read-docs.md
│   │   ├── update-docs.md
│   │   ├── feature-flow-analysis.md
│   │   ├── add-testing.md
│   │   ├── security-check.md
│   │   └── validate-pr.md
│   ├── agents/                  # Sub-agents
│   │   ├── feature-flow-analyzer.md
│   │   ├── test-runner.md
│   │   └── security-analyzer.md
│   ├── skills/                  # Methodology guides
│   │   ├── verification/SKILL.md
│   │   ├── systematic-debugging/SKILL.md
│   │   ├── tdd/SKILL.md
│   │   └── code-review/SKILL.md
│   └── settings.local.json      # Claude Code settings
└── docs/
    ├── DEVELOPMENT_WORKFLOW.md  # Development cycle guide
    ├── TESTING_GUIDE.md         # Testing philosophy
    └── memory/                  # Persistent project state
        ├── requirements.md      # Source of truth for features
        ├── architecture.md      # Current system design
        ├── roadmap.md           # Prioritized task queue
        ├── changelog.md         # Timestamped history
        ├── feature-flows.md     # Feature flow index
        └── feature-flows/       # Individual flow documents
```

## Development Cycle

This methodology enforces a 5-phase development cycle:

```
1. CONTEXT LOADING    →  /read-docs
       ↓
2. DEVELOPMENT        →  Implement changes
       ↓
3. TESTING            →  test-runner agent
       ↓
4. DOCUMENTATION      →  /update-docs
       ↓
5. PR VALIDATION      →  /validate-pr (before merge)
```

See `docs/DEVELOPMENT_WORKFLOW.md` for details.

## Commands Reference

| Command | Purpose |
|---------|---------|
| `/read-docs` | Load project context at session start |
| `/update-docs` | Update changelog, architecture, requirements after changes |
| `/feature-flow-analysis <name>` | Document feature from UI to database |
| `/add-testing <name>` | Add testing section to feature flow |
| `/security-check` | Validate no secrets in staged files before commit |
| `/validate-pr <number>` | Validate PR against methodology and generate merge report |

## Agents Reference

| Agent | Purpose |
|-------|---------|
| `feature-flow-analyzer` | Traces and documents feature vertical slices |
| `test-runner` | Runs test suite with tiered execution (smoke/core/full) |
| `security-analyzer` | OWASP Top 10 security analysis |

## Skills Reference

Skills are methodology guides that define HOW to approach specific tasks.

| Skill | Purpose | Key Rule |
|-------|---------|----------|
| `verification` | Evidence-based completion | No "done" without proof |
| `systematic-debugging` | Root cause investigation | Investigate before fixing |
| `tdd` | Test-driven development | Failing test first |
| `code-review` | Receiving feedback | Verify before implementing |

Skills are located in `.claude/skills/{name}/SKILL.md`.

## Memory Files Explained

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

## Customization

### Adding Project-Specific Commands

Create new `.md` files in `.claude/commands/`:

```markdown
# My Custom Command

Description of what this command does.

## Instructions

1. Step one
2. Step two
```

### Adding Project-Specific Agents

Create new `.md` files in `.claude/agents/`:

```markdown
---
name: my-agent
description: What this agent does
tools: Read, Grep, Glob, Write, Edit
model: sonnet
---

You are a specialist for [domain]. Your job is to [task].

## Instructions
...
```

### Extending Memory Files

The memory file structure can be extended. Common additions:

- `docs/memory/decisions.md` - Architecture Decision Records (ADRs)
- `docs/memory/incidents.md` - Incident response log
- `docs/memory/integrations.md` - Third-party integration details

## Best Practices

### DO

- Load context before starting work (`/read-docs`)
- Read feature flows before modifying features
- Run tests after every significant change
- Update feature flows when behavior changes
- Run `/security-check` before every commit

### DON'T

- Skip context loading ("I remember from last time")
- Modify features without reading their flow
- Commit without running tests
- Leave feature flows outdated after changes
- Create documentation files unless explicitly asked

## Changelog Format

Use emoji prefixes for quick visual scanning:

| Emoji | Category |
|-------|----------|
| `🎉` | Major milestone |
| `✨` | New feature |
| `🔧` | Bug fix |
| `🔄` | Refactoring |
| `📝` | Documentation |
| `🔒` | Security update |
| `🚀` | Performance |
| `💾` | Data/persistence |
| `🐳` | Infrastructure |

## Status Labels

Use consistent status labels across all memory files:

| Status | Meaning |
|--------|---------|
| `⏳` | Pending / Not started |
| `🚧` | In progress |
| `✅` | Complete |
| `❌` | Blocked / Failed |

## License

MIT License - Use freely in your projects.
