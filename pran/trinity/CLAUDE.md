# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

**Repository**: https://github.com/abilityai/trinity (PUBLIC)

---

## ⚠️ PUBLIC OPEN SOURCE REPOSITORY

**This is a PUBLIC open-source repository visible to the entire world.**

### What NEVER to Commit
- ❌ API keys, tokens, PATs, or any credentials (even in comments or docs)
- ❌ Internal company URLs, production domains, IP addresses
- ❌ Real user emails, personal information, or PII
- ❌ Database dumps, backups, or data exports
- ❌ `.env` files or deployment configs with real values
- ❌ Auth0 client secrets, OAuth credentials, or service account keys
- ❌ Private repository references or internal tooling details
- ❌ Customer names, company-specific configurations, or business data

### Open Source Best Practices
✅ **Use placeholders**: `your-domain.com`, `your-api-key`, `user@example.com`
✅ **Example files**: Commit `.example` templates (e.g., `.env.example`)
✅ **Environment variables**: Reference `${VAR_NAME}` instead of hardcoded values
✅ **Local examples**: Use `localhost` or `127.0.0.1` in documentation
✅ **Review diffs**: Always check `git diff` before committing to catch accidental secrets
✅ **Public-first mindset**: Assume every commit will be visible forever and indexed by search engines

### Git Safety Checklist
Before every commit:
1. Run `git diff` and review all changes line by line
2. Search for patterns: API keys (often start with `sk-`, `pk-`, `ghp_`), emails (`@`), IPs (`192.168.`, `10.0.`)
3. Verify no `.env` or config files with real credentials are staged
4. Check that examples use placeholder values
5. Confirm commit message doesn't reference internal systems

---

## Project Overview

**Trinity** is a **Deep Agent Orchestration Platform** — sovereign infrastructure for deploying, orchestrating, and governing autonomous AI systems that plan, reason, and execute independently.

Unlike reactive chatbots ("System 1" AI), Deep Agents operate with deliberative reasoning ("System 2" AI): they decompose goals into task graphs, persist memory across sessions, delegate to specialized sub-agents, and recover from failures autonomously.

Trinity implements the **Four Pillars of Deep Agency**:
1. **Hierarchical Delegation** — Orchestrator-Worker pattern with context quarantine
2. **Persistent Memory** — Virtual filesystems, vector databases, episodic memory
3. **Extreme Context Engineering** — High-Order Prompts defining reasoning processes
4. **Autonomous Operations** — Scheduling, monitoring, and self-healing capabilities

Each agent runs as an isolated Docker container with standardized interfaces for credentials, tools, and MCP server integrations.

**Local**: http://localhost
**Backend API**: http://localhost:8000/docs

---

## Rules of Engagement

### 1. Requirements-Driven Development
- Update `docs/memory/requirements.md` **BEFORE** implementing new features
- All features must trace back to documented requirements
- Never add features without requirements update first

### 2. Minimal Necessary Changes
- Only change what's required for the task
- No unsolicited refactoring or reorganization
- No cosmetic formatting changes to unrelated code
- No creating documentation files unless explicitly requested

### 3. Follow the Roadmap
- Check GitHub Issues for current priorities (`/roadmap` or `gh issue list`)
- Work P0 issues first, then P1, by issue number (oldest first)
- Close issues when complete

### 4. Mandatory Documentation Updates
After **EVERY** change, update:
- `changelog.md` - Add timestamped entry with emoji prefix
- `architecture.md` - If changing APIs, schema, or integrations
- `feature-flows/` - If modifying feature behavior
- `requirements.md` - If changing feature scope

### 5. Security First (PUBLIC REPO)
- **This is a public repository** - assume all commits are visible worldwide
- Never expose credentials, API keys, or tokens in code or logs
- Never commit internal URLs, IP addresses, or email addresses
- Use environment variables for all secrets
- All credential operations logged via structured logging (values masked, captured by Vector)
- Use placeholder values in example configs (e.g., `your-domain.com`, `your-api-key`)
- Review diffs before committing for accidental sensitive data

### 6. Development Skills
Follow methodology guides in `.claude/skills/`:

| Skill | Key Rule |
|-------|----------|
| `verification` | No "done" claims without evidence (run command, show output) |
| `systematic-debugging` | Find root cause BEFORE attempting fixes |
| `tdd` | Write failing test first, then minimal code to pass |
| `code-review` | Verify feedback technically before implementing |

---

## Memory Files

| File | Purpose |
|------|---------|
| `.claude/memory/requirements.md` | **SINGLE SOURCE OF TRUTH** - All features |
| `.claude/memory/architecture.md` | Current system design (~1000 lines max) |
| GitHub Issues | Prioritized task queue (labels: priority-p0/p1/p2/p3) |
| `.claude/memory/changelog.md` | Timestamped history (~500 lines) |
| `.claude/memory/feature-flows.md` | Index of vertical slice docs |
| `.claude/memory/project_index.json` | Machine-readable project state |

---

## Development Commands

```bash
# Start all services
./scripts/deploy/start.sh

# Stop all services
./scripts/deploy/stop.sh

# Build base agent image
./scripts/deploy/build-base-image.sh

# Rebuild services
docker-compose build

# View logs
docker-compose logs -f backend
```

### Local URLs
- **Web UI**: http://localhost
- **Backend API**: http://localhost:8000/docs
- **MCP Server**: http://localhost:8080/mcp
- **Vector (logs)**: http://localhost:8686/health

---

## Project Structure

```
project_trinity/
├── src/
│   ├── backend/          # FastAPI backend (main.py, database.py)
│   ├── frontend/         # Vue.js 3 + Tailwind CSS
│   └── mcp-server/       # Trinity MCP server (12 tools)
├── docker/
│   ├── base-image/       # Universal agent base (agent-server.py)
│   ├── backend/          # Backend Dockerfile
│   └── frontend/         # Frontend Dockerfile
├── config/
│   ├── agent-templates/  # Pre-configured templates
│   └── vector.yaml       # Vector log aggregation config
├── .claude/
│   ├── memory/           # Persistent project memory
│   ├── commands/         # Slash commands
│   └── agents/           # Sub-agents
└── docs/                 # Additional documentation
```

---

## Key Files

| Category | File | Description |
|----------|------|-------------|
| Backend | `src/backend/main.py` | FastAPI app, 35+ endpoints |
| Backend | `src/backend/database.py` | SQLite persistence |
| Backend | `src/backend/routers/credentials.py` | Credential injection (CRED-002) |
| Frontend | `src/frontend/src/views/AgentDetail.vue` | Agent detail page |
| Frontend | `src/frontend/src/stores/agents.js` | Agent state management |
| Agent | `docker/base-image/agent-server.py` | Agent internal server |

---

## Important Notes for Claude Code

1. **Credential security**: Never log credentials. Credential values are masked in all logs.

2. **Docker socket access**: Backend has read-only Docker socket access. Be cautious with Docker API calls.

3. **Port conflicts**: Agents use incrementing SSH ports (2222+). Check for conflicts.

4. **Data persistence**: SQLite at `~/trinity-data/trinity.db` (bind mount). Redis for secrets (Docker volume). Run `scripts/deploy/backup-database.sh` before major changes.

5. **Logging via Vector**: All container logs are captured by Vector and written to JSON files. Query logs with `jq` or grep.

6. **Frontend dev mode**: Vite with hot reload. Changes to `.vue` files reflect immediately.

7. **Base image rebuilds**: After modifying `docker/base-image/Dockerfile`, run `./scripts/deploy/build-base-image.sh`.

8. **Re-login after restart**: When the backend restarts, users need to re-login (JWT tokens are invalidated).

9. **MCP reconnection**: After backend restart, MCP clients (Claude Code, etc.) need to be manually reconnected (run `/mcp` or restart the client).

---

## Authentication

- **Email Login**: Primary method - users enter email, receive 6-digit code, login
- **Admin Login**: Password-based login for admin user (username fixed as 'admin')
- **Email Whitelist**: Manage allowed emails in Settings → Email Whitelist

---

## Quick Reference

### Creating an Agent
```bash
# Via API
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent", "template": "github:Org/repo"}'

# Via UI
# Visit http://localhost → Create Agent
```

### Agent Container Labels
- `trinity.platform=agent` - Identifies Trinity agents
- `trinity.agent-name` - Agent name
- `trinity.agent-type` - Type (business-assistant, etc.)
- `trinity.template` - Template used

### Credential Pattern
```
.env                    # Source of truth (KEY=VALUE)
.mcp.json.template      # Template with ${VAR} placeholders
.mcp.json               # Generated at runtime
```

---

## Related Repositories

| Repository | Description |
|------------|-------------|
| [abilityai/trinity](https://github.com/abilityai/trinity) | This repository - Deep Agent Orchestration Platform |
| [abilityai/abilities](https://github.com/abilityai/abilities) | **System of record for Trinity skills & plugins** - All onboarding, management, and workflow skills |

### Trinity Onboarding (abilities repo)

The `abilities` repo contains **all Trinity skills** bundled in the `trinity-onboard` plugin:

| Skill | Purpose |
|-------|---------|
| `onboard` | Zero-friction agent deployment to Trinity |
| `trinity-adopt` | Convert any agent to Trinity-compatible format |
| `trinity-compatibility` | Audit agent structure for requirements |
| `trinity-remote` | Remote agent operations (exec, run, notify) |
| `trinity-sync` | Git-based synchronization with remote |
| `trinity-schedules` | Manage scheduled autonomous executions |

**Installation:**
```bash
/plugin marketplace add abilityai/abilities
```

**Onboarding a new agent:**
```bash
/trinity-onboard:onboard
```

---

## See Also

- **Development Workflow**: `docs/DEVELOPMENT_WORKFLOW.md` ← Start here for dev process
- **Full Architecture**: `.claude/memory/architecture.md`
- **All Requirements**: `.claude/memory/requirements.md`
- **Current Roadmap**: https://github.com/abilityai/trinity/issues
- **Recent Changes**: `.claude/memory/changelog.md`
- **Template Spec**: `docs/AGENT_TEMPLATE_SPEC.md`
- **Agent Network Demo**: `docs/AGENT_NETWORK_DEMO.md`
- **Claude Code Plugins**: https://github.com/abilityai/abilities
