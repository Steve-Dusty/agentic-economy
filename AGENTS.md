# Full Stack Agents — Our Agents

We run **five agents** that together form an autonomous AI business. Each one has a specific role. Here's who they are, what they do, and why they exist.

---

## 1. The Seller — AI Research Engine

**What it is:** A FastAPI server that answers questions and summarizes text, powered by GPT-4o. This is our product — the thing we sell on the marketplace.

**Endpoints:**
- `POST /api/crypto/ask` — Ask any question, get expert AI research (1 credit = 0.10 USDC)
- `POST /api/crypto/summarize` — Summarize any text intelligently (3 credits = 0.30 USDC)
- `POST /api/fiat/ask` — Same, pay with credit card
- `POST /api/fiat/summarize` — Same, pay with credit card
- `GET /pricing` — Free. Returns our plans, endpoints, and costs so buyers can discover us programmatically.

**Three payment plans registered on Nevermined:**

| Plan | Price | Credits | Payment |
|------|-------|---------|---------|
| Free Testing | Free | 100 | None (testing only, unlisted) |
| Crypto | 10 USDC | 100 | On-chain USDC via ERC-4337 smart account |
| Fiat | $10 USD | 100 | Stripe credit card checkout |

**How payment works:** Every request hits the x402 PaymentMiddleware before it reaches our code. The middleware verifies the buyer's `payment-signature` header, executes our handler, then settles by burning credits on-chain. We never touch payment logic — the middleware handles verify → work → settle automatically.

**Why it matters:** This is our revenue source. Every credit burned on our endpoints is money earned. But a raw GPT-4o endpoint is commodity — Cortex, CloudAGI, Nexus all sell the same thing. What makes us different is what feeds into it, which is where the buyer comes in.

**File:** `server.py` — run with `python server.py` (serves on port 3000)

---

## 2. The Buyer — Autonomous Purchasing Agent

**What it is:** An autonomous agent that shops the Nevermined marketplace, discovers other teams' agents, evaluates them, and buys their services to enrich our seller's output.

**Registered on Nevermined as:** "AI Research Buyer Agent" with a free plan (50 credits) so other agents can query it too.

**What it does, step by step:**

1. **Discovers** — Calls the Hackathon Discovery API, finds all 54 sellers on the marketplace
2. **Classifies** — Ranks every seller by how useful they are to us:
   - **CRITICAL**: Web scrapers (fresh data), DeFi agents (live prices), data analytics (verified facts)
   - **HIGH**: Sentiment agents (emotional context), search agents (post-cutoff knowledge), verification agents (fact-checking)
   - **MEDIUM**: Orchestrators and brokers (drive traffic to us)
   - **LOW**: Advertising, other LLMs (nice to have)
3. **Budgets** — Enforces hard limits: 50 credits/day max, 10 credits per single purchase. Can't overspend.
4. **Subscribes** — Orders the seller's plan (pays USDC or fiat), receives credits
5. **Purchases** — Gets x402 token, POSTs to seller with payment header, gets response
6. **Records** — Logs every transaction: who, what, how much, when

**The key idea:** We spend 0.01-0.20 USDC buying raw data from suppliers. We feed that into GPT-4o. We sell the synthesized answer for 0.10 USDC. Our answers are better than competitors' because they're backed by live data from multiple sources, not just a single LLM's training data.

**Three autonomous strategies:**
- **Balanced** — Buy from each agent once per round. Diversify across the marketplace.
- **Focused** — Concentrate on the top 5 most valuable suppliers. Go deep.
- **Aggressive** — Maximum speed, minimum delay. Buy from everything.

**File:** `buyer.py` (standalone CLI) or `nvm_terminal/` (full interactive terminal)

---

## 3. NVM Terminal — The Command Center

**What it is:** An interactive CLI (like Claude Code) that wraps everything into a single interface. You can talk to it in natural language, use slash commands, or let it run autonomously.

**What it looks like:**
```
  _  ___   ____  __   _____                   _             _
 | \| \ \ / /  \/  | |_   _|__ _ _ _ __  _ __(_)_ _  __ _ | |
 | .` |\ V /| |\/| |   | |/ -_) '_| '  \| '_ \ | ' \/ _` || |
 |_|\_| \_/ |_|  |_|   |_|\___|_| |_|_|_| .__/_|_||_\__,_||_|
                                          |_|

nvm > /discover
  [43 agents found, cached]

nvm > /buy "Crypto Market Intelligence" what is ETH price today?
  [OK] 1 credit → got live ETH price data

nvm > what agents should I buy from for DeFi research?
  [LLM thinks... calls discover_agents... evaluates options...]
  "I'd recommend Crypto Market Intelligence (0.01 USDC, live DeFi data),
   AiRI (0.01 USDC, resilience scores), and CloudAGI Web Scraper (0.20 USDC,
   fresh web data). Total cost: 0.22 USDC per enriched query."

nvm > /auto balanced
  [Autonomous mode: discovering → buying → recording → loop]
```

**Slash commands:**

| Command | What it does |
|---------|-------------|
| `/discover [category]` | Find agents on the marketplace |
| `/buy <name> [query]` | Buy from a specific agent |
| `/balance` | Show credit balances across all plans |
| `/budget` | Show daily spending, limits, recent purchases |
| `/agents` | List cached agents from last discovery |
| `/auto [balanced\|focused\|aggressive]` | Start autonomous buying loop |
| `/stop` | Stop autonomous mode |
| `/sell` | Show our seller agent IDs and plans |
| `/ads <query>` | Fetch ZeroClick sponsored offers |
| `/signals` | Show collected preference signals |
| `/status` | Full economic overview |
| Any text | Chat with GPT-4o AI advisor that can call tools |

**The AI advisor** (GPT-4o with function calling) can autonomously:
- Discover agents on the marketplace
- Evaluate an agent's pricing and capabilities
- Execute a purchase
- Check balances and budget
- Fetch sponsored offers

It reasons about the marketplace: "The user wants DeFi research → I should buy from the financial data agent AND the resilience scorer → then synthesize." It does the multi-step orchestration that makes our answers premium.

**ZeroClick integration:** Every message the user types gets scanned for commercial intent signals (`purchase_intent`, `evaluation`, `interest`, etc.). These signals are broadcast to ZeroClick's preference network and used to sharpen which suppliers we prioritize and which sponsored offers we surface.

**File:** `nvm_terminal.py` — run with `python nvm_terminal.py`

---

## 4. Haist — The Workflow Factory

**What it is:** A visual workflow automation platform — "n8n meets ChatGPT." Users describe automations in natural language, and an AI assistant builds executable workflows. It's the factory floor where we wire together our supply chain.

**Why it exists in our economy:** Without Haist, every supplier integration is a hardcoded script. With Haist, we wire together a pipeline visually: "When a research query arrives → call CloudAGI Scraper → call AiRI → feed both into GPT-4o → return answer." When a new agent appears on the marketplace tomorrow, we add one node to the pipeline. No code changes.

### How It Works

**Bubbles** are the building blocks — composable, modular units that each do one thing:
- **AI Agent bubble** — LLM-powered reasoning (GPT, Claude, Gemini)
- **HTTP bubble** — Call any API endpoint
- **Reddit Scrape bubble** — Fetch posts from subreddits
- **Web Search bubble** — Search the web for fresh results
- **Slack bubble** — Send messages to Slack channels
- **Gmail bubble** — Read/send emails
- **Google Sheets bubble** — Read/write spreadsheet data
- **PostgreSQL bubble** — Query databases
- Plus 30+ more via Composio (Notion, GitHub, Linear, Jira, Salesforce, etc.)

**Two ways to build workflows:**

1. **Chat with the AI assistant:**
   ```
   User: "Create a workflow that scrapes Reddit r/technology, summarizes the top posts,
          and sends the summary to Slack #research"

   AI: [generates workflow with 3 nodes, wired together, ready to run]
   ```

2. **Visual canvas:** Drag bubble nodes, connect them with edges, configure parameters, execute.

**Automation rules** — Workflows that run themselves:
- **Trigger mode**: Fires on events (new email from boss → summarize → post to Slack)
- **Scheduled mode**: Runs on interval (every morning at 9am → daily briefing)
- **Manual mode**: Invoke by name (`@DailyDigest` in chat)

**Pre-built templates:**
- Daily Email Digest — Summarize unread emails every morning
- Social Mention Monitor — Track brand mentions hourly
- Morning Briefing — Calendar + emails + deadlines summary
- Meeting Prep — Gather context 1 hour before meetings
- Content Repurposer — Turn blog post into Twitter + LinkedIn posts

### Haist in Our Agent Economy

The concrete use case: Haist orchestrates the supply chain pipeline.

```
[Incoming research query]
        ↓
[CloudAGI Web Scraper bubble] → fresh web data
        ↓
[Crypto Market Intelligence bubble] → live DeFi data
        ↓
[AiRI Resilience bubble] → risk scores
        ↓
[GPT-4o Synthesis bubble] → enriched answer combining all sources
        ↓
[Response to customer]
```

Each bubble is an x402 purchase from another agent. Haist manages the orchestration — parallel calls, error handling, fallbacks. If a supplier is down, Haist routes to the backup. If a new supplier appears that's cheaper, we swap one node.

**The code generation engine** compiles visual workflows into executable TypeScript (`BubbleFlow` classes) that the BubbleLab runtime executes. So the visual pipeline actually runs as production code.

**Files:** `haist/workflow-editor/` (Next.js web app), `haist/blockd/` (execution runtime)

---

## 5. The Dashboard — Supply Chain Visualization

**What it is:** A real-time 3D force-directed graph that visualizes the entire marketplace economy from our perspective. It's not a generic marketplace browser — it's our strategic supply chain map.

**What you see:**
- **Green nodes (center, largest)** — Our agents. Gravitationally centered.
- **Cyan links pulsing inward** — Agents we buy from (our suppliers). Thicker = higher priority.
- **Amber links glowing outward** — Agents that buy from us (our customers).
- **Colored clusters** — Other teams, each with their own agents.
- **Thin gray links** — Peer-to-peer trades between other teams (shows the broader economy exists).

**Every link has a "why":**
Not just "we transact" — each connection has a strategic reason:
- Inbound: "We buy sentiment data because it adds emotional context that makes our research more actionable"
- Outbound: "AgentBank buys our research because they need AI interpretation of their raw financial data"

**The classification engine** (`classifySupplier` / `classifyCustomer`) evaluates every agent on the marketplace by scanning their name, description, keywords, category, and services. It assigns:
- **Capability** — What they provide (e.g., "DeFi / Financial Intelligence")
- **Why we buy / why they buy** — The strategic reason
- **How it helps us** — Concrete impact on our product
- **Priority** — CRITICAL / HIGH / MEDIUM / LOW

**Stats overlay shows:**
- Total sellers, buyers, teams on marketplace
- Our supply chain depth (how many suppliers we buy from)
- Revenue streams (how many agents buy from us)
- Estimated supply cost vs revenue per cycle

**File:** `dashboard/` (Next.js app with 3D graph)

---

## How They All Work Together

```
                    ┌─────────────────────────┐
                    │   HAIST (Workflow Factory)│
                    │   Wires the pipeline     │
                    └────────────┬────────────┘
                                 │ orchestrates
                                 ▼
┌──────────────┐    ┌─────────────────────────┐    ┌──────────────┐
│  54 Sellers  │───▶│   BUYER AGENT            │───▶│ SELLER AGENT │
│  on market   │    │   Discovers, evaluates,  │    │ GPT-4o engine│
│              │◀───│   purchases raw data     │◀───│ Enriches and │
│  Scrapers    │    │                          │    │ sells answers│
│  DeFi data   │    │   Budget: 50 cr/day      │    │              │
│  Sentiment   │    │   ZeroClick signals      │    │ 0.10 USDC/q  │
│  Analytics   │    └─────────────────────────┘    │ 0.30 USDC/s  │
└──────────────┘                                    └──────┬───────┘
                                                           │ sells to
                    ┌─────────────────────────┐            ▼
                    │   NVM TERMINAL           │    ┌──────────────┐
                    │   Human command center   │    │  16 Buyers   │
                    │   /discover /buy /auto   │    │  on market   │
                    │   + AI chat advisor      │    │              │
                    └─────────────────────────┘    │  AgentBank   │
                                                    │  AiRI        │
                    ┌─────────────────────────┐    │  Sabi        │
                    │   DASHBOARD              │    │  Churninator │
                    │   3D supply chain viz    │    └──────────────┘
                    │   Shows why every link   │
                    │   exists in real-time    │
                    └─────────────────────────┘
```

**The story in one paragraph:**

Haist wires the supply chain — which agents to call, in what order, with what fallbacks. The Buyer Agent executes that pipeline autonomously: it discovers 54 sellers, classifies them by strategic value, respects budget limits, and purchases raw intelligence (scraped data, DeFi prices, sentiment, risk scores) via x402 on-chain payments. That raw intelligence feeds into the Seller Agent's GPT-4o engine, which synthesizes it into premium research that's richer than any single-source LLM answer. The enriched output is sold to 16+ marketplace buyers at 0.10 USDC per query — a 4x margin on input costs. NVM Terminal gives humans a command center to oversee everything or let it run hands-free. The Dashboard visualizes the entire supply chain in real-time, showing exactly why each economic relationship exists. ZeroClick signals running through it all learn what buyers actually want, making each purchasing decision sharper over time.
