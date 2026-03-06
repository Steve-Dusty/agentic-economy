# Nevermined Autonomous Business Hackathon - Getting Started

**Event:** Nevermined "Autonomous Business Hackathon: When Agents Run Businesses"
**Dates:** March 5-6, 2026 - San Francisco
**Contact:** Eugene Vyborov - eugene@ability.ai

---

## Trinity Instance Access

**Shared instance:** https://us14.abilityai.dev/login

This instance is pre-configured and ready to use. It runs on Eugene's Anthropic Max subscription. If it hits rate limits during the hackathon, you may need to configure your own Anthropic API key or subscription.

**To get access:**
1. Give Eugene your email address
2. He will add you to the whitelist
3. Log in at the URL above

Individual Trinity instances can be provisioned by request for the duration of the hackathon - just ask.

> Note: This instance is normally behind a VPN but has been made public for the hackathon.

---

## Run Your Own Trinity Instance (Optional)

Trinity is open source. You can provision your own local instance if you prefer.

**Repository:** https://github.com/Abilityai/trinity/tree/main

**Requirements:**
- Docker and Docker Compose v2+
- 8 GB RAM minimum (16 GB recommended for multiple agents)
- Anthropic API Key (`sk-ant-...`) or Claude Max/Pro subscription token

**Quick start:**
```bash
git clone https://github.com/abilityai/trinity.git
cd trinity

# Configure environment
cp .env.example .env
# Edit .env - at minimum set these three:
#   SECRET_KEY=<run: openssl rand -hex 32>
#   ADMIN_PASSWORD=<your password>
#   ANTHROPIC_API_KEY=<your key>

# Build the agent base image and start
./scripts/deploy/build-base-image.sh
./scripts/deploy/start.sh
```

After startup: **http://localhost** (UI), **http://localhost:8000/docs** (API).

**First login:** Use `admin` / your `ADMIN_PASSWORD`. Then go to **Settings > Email Whitelist** to add team emails for email-based login.

For email login codes during local dev, codes print to backend logs (`docker compose logs -f backend`) since `EMAIL_PROVIDER=console` by default.

See `docs/DEPLOYMENT.md` in the repo for full configuration reference.

---

## Connecting Local Agents to Trinity

The recommended workflow is to develop agents locally with Claude Code and deploy them to Trinity via MCP.

**Step 1: Get an MCP API Key**

1. Log into the Trinity UI
2. Go to **API Keys** page (left sidebar)
3. Click **Create API Key** — copy the key (starts with `trinity_mcp_`)

**Step 2: Configure your local agent**

Add this to your local agent's `.mcp.json`:
```json
{
  "mcpServers": {
    "trinity": {
      "type": "http",
      "url": "https://us14.abilityai.dev/mcp",
      "headers": { "Authorization": "Bearer trinity_mcp_YOUR_KEY_HERE" }
    }
  }
}
```
For a self-hosted instance, replace the URL with `http://localhost:8080/mcp`.

**Step 3: Deploy**

```
/trinity-onboard
```
This pushes your local agent to Trinity as a remote container. Use `/trinity-sync` for ongoing git-based synchronization.

**Best practice:** Always deploy agents through a local Claude Code agent connected to Trinity via MCP — not by manually creating agents in the UI. This gives you the twin-agent workflow (local for development, remote for autonomous execution).

See `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` for full agent structure requirements.

---

## Abilities SDK (Plugin Marketplace)

The Abilities SDK gives your agents memory, playbooks, deployment tools, and more - 7 packages, 30 skills.

**Repository:** https://github.com/Abilityai/abilities

**Install in Claude Code:**
```
/plugin marketplace add abilityai/abilities
```

**What you get after installing:**

| Package | What It Does |
|---------|-------------|
| **json-memory** | Structured JSON memory - agents remember across sessions |
| **brain-memory** | Zettelkasten knowledge base - agents build long-term knowledge |
| **file-indexing** | File system awareness - agents know what files exist |
| **playbook-builder** | Create, capture, and iterate on structured playbooks |
| **project-management-kit** | Multi-session project organization |
| **utilities** | Conversation saving and exports |
| **trinity-onboard** | Full deployment lifecycle to Trinity - onboard, sync, schedule, dashboards |

**Key commands after install:**
- `/setup-memory` - Initialize agent memory
- `/setup-brain` - Initialize knowledge base
- `/setup-index` - Initialize file index
- `/create-playbook` - Build a new playbook from scratch
- `/save-playbook` - Capture a working workflow as a playbook
- `/trinity-onboard` - Deploy agent to Trinity
- `/trinity-sync` - Sync local agent with remote Trinity agent
- `/trinity-schedules` - Manage scheduled tasks on Trinity

---

## Agent Templates

Fork these repositories as starting points for your agents. Each is a pre-configured Claude Code agent with CLAUDE.md identity, skills, and integrations for a specific business function.

| Template | Business Function | Repository |
|----------|------------------|------------|
| **Cornelius** | Knowledge & Research | https://github.com/Abilityai/cornelius |
| **Ruby** | Content & Marketing | https://github.com/Abilityai/ruby |
| **Outbound** | Sales & Outreach | https://github.com/abilityai/outbound-agent |
| **Webmaster** | Website & Digital Presence | https://github.com/Abilityai/webmaster |

All templates require credentials and configuration for their respective integrations (API keys, service accounts, etc.).

**To use a template:**
1. Fork the repository
2. Clone it locally
3. Customize `CLAUDE.md` for your domain and business
4. Install the Abilities SDK: `/plugin marketplace add abilityai/abilities`
5. Initialize memory and playbooks
6. Deploy to Trinity: `/trinity-onboard`

---

## Enabling Payments (Nevermined)

Payments are built into Trinity - every agent can be monetized through the UI.

**To enable payments for an agent:**

1. Open your agent in Trinity UI -> **Payments tab**
2. Configure:
   - **NVM API Key** (from nevermined.app - format: `environment:jwt_token`)
   - **Environment:** sandbox (for testing) or live (for real transactions)
   - **Agent ID:** Your agent's Nevermined registration ID
   - **Plan ID:** Your pricing plan ID from Nevermined
   - **Credits per request:** How many credits each call costs
3. Toggle the **Enable** switch
4. Copy the **paid endpoint URL** - this is what external callers use to pay and interact with your agent

**How it works (x402 protocol):**
1. External caller discovers your agent's payment requirements via `GET /api/paid/{agent}/info`
2. Caller hits `POST /api/paid/{agent}/chat` - gets `402 Payment Required` with pricing details
3. Caller creates a payment access token via Nevermined SDK
4. Caller retries with `payment-signature` header containing the token
5. Trinity verifies credits -> executes the agent task -> settles on-chain (only if successful)
6. Caller receives response + payment receipt with blockchain transaction hash

**Key details:**
- **Pay-for-success:** Credits only burn when the agent successfully completes work
- **Internal fleet traffic is free** - agents talking to each other within your fleet via `chat_with_agent` don't pay
- **On-chain settlement** on Base (Sepolia testnet for sandbox, Base mainnet for production)

---

## Using the Trinity UI

Once logged in, here's what you can do:

**Creating agents** — Click **Create Agent** on the Dashboard or Agents page. Pick a GitHub template or create from scratch. Agents spin up as Docker containers in ~15 seconds.

**Agent Detail page** — Click any agent to access its tabs:

| Tab | What It Does |
|-----|-------------|
| **Terminal** | Interactive Claude Code terminal — talk to the agent directly |
| **Chat** | Simple chat interface with dynamic status labels |
| **Tasks** | Trigger tasks, view execution history, monitor running work |
| **Playbooks** | Browse and invoke the agent's installed skills |
| **Files** | Browse and edit files inside the agent container |
| **Dashboard** | Agent-defined metrics via `dashboard.yaml` |
| **Payments** | Configure Nevermined x402 monetization |
| **Schedules** | Set up cron-based autonomous execution |

**Agent collaboration** — Go to **Permissions** tab to grant agents permission to call each other. Then agents use `chat_with_agent` MCP tool to communicate. The main Dashboard shows a live graph of agent interactions.

**Scheduling** — In the **Schedules** tab, create cron-based tasks. Toggle **Autonomy** in the agent header to enable/disable all schedules at once.

See `docs/MULTI_AGENT_SYSTEM_GUIDE.md` for patterns on wiring multi-agent systems.

---

## Agent Credentials

Agents need API keys for external services (Google, Slack, etc.).

**Quick inject:** In Agent Detail → **Credentials** section, paste `.env`-style key-value pairs:
```
GOOGLE_API_KEY=your-key
SLACK_BOT_TOKEN=xoxb-your-token
```

These are written directly to the agent's `.env` file and hot-reloaded — no restart needed.

**Using your own Anthropic key/subscription per agent:**
- **API Key:** Set in platform Settings → Anthropic API Key (shared by all agents)
- **Subscription:** If you have Claude Max/Pro, run `claude setup-token` locally, then register the token in Settings → Subscriptions and assign it to specific agents

---

## Suggested Hackathon Workflow

1. **Pick a business** — What does it do? What are its core functions?
2. **Map functions to agents** — Which agents does your business need?
3. **Fork templates** — Start from the closest agent template(s)
4. **Customize** — Edit CLAUDE.md for your domain, install the Abilities SDK
5. **Build playbooks** — One per agent, iterate until they work locally
6. **Deploy to Trinity** — `/trinity-onboard` to push to the shared instance
7. **Enable payments** — Configure each agent's Payments tab in Trinity UI
8. **Wire agents together** — Use `chat_with_agent` MCP tool for inter-agent collaboration
9. **Add dashboards** — Make each agent's work visible via `dashboard.yaml`
10. **Schedule everything** — Your business should run autonomously

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Agent creation fails | Rebuild base image: `./scripts/deploy/build-base-image.sh` |
| Email login code not arriving | Check backend logs: `docker compose logs -f backend` (codes print to console in dev mode) |
| Agent hits rate limits | Configure your own API key in Settings, or assign a subscription token |
| Agent terminal shows errors | Check agent logs: Agent Detail → Logs tab, or `docker logs agent-{name}` |
| MCP connection refused | Verify API key is valid, check URL matches your instance |
| Port conflicts | Trinity uses ports 80, 8000, 8080, 6379, and 2222+ for agent SSH |

For self-hosted instances, see `docs/DEPLOYMENT.md` for full troubleshooting.

---

## Quick Reference

| Resource | URL |
|----------|-----|
| Trinity Instance | https://us14.abilityai.dev/login |
| Trinity Source Code | https://github.com/Abilityai/trinity/tree/main |
| Abilities SDK | https://github.com/Abilityai/abilities |
| Cornelius (Research Agent) | https://github.com/Abilityai/cornelius |
| Ruby (Content Agent) | https://github.com/Abilityai/ruby |
| Outbound (Sales Agent) | https://github.com/abilityai/outbound-agent |
| Nevermined Docs | https://nevermined.ai/docs |
| Contact | eugene@ability.ai |

**In-repo documentation** (for self-hosted users):

| Document | Path | Covers |
|----------|------|--------|
| Deployment Guide | `docs/DEPLOYMENT.md` | Full setup, configuration, troubleshooting |
| Agent Guide | `docs/TRINITY_COMPATIBLE_AGENT_GUIDE.md` | Building Trinity-compatible agents |
| Multi-Agent Guide | `docs/MULTI_AGENT_SYSTEM_GUIDE.md` | Wiring agents together, collaboration patterns |
| Template Spec | `docs/AGENT_TEMPLATE_SPEC.md` | `template.yaml` format for agent templates |
| API Docs | `http://localhost:8000/docs` | Full interactive API reference (Swagger) |
