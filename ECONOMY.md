# Full Stack Agents — Agent Economy Story

## Who We Are

We're **Full Stack Agents** — an AI Research & Summarization Engine on the Nevermined agent marketplace. We sell GPT-4o-powered research at **0.10 USDC per query** and summarization at **0.30 USDC per summary**. All transactions settle on-chain via the x402 payment protocol on Base Sepolia (L2).

On a marketplace of 54 sellers, we're one of many research agents. Cortex, CloudAGI, Nexus Intelligence Hub all sell similar LLM responses at similar prices.

**What makes us different: we don't just answer — we source.**

---

## The Core Business Model

```
Other agents' raw data  →  Our AI Engine  →  Enriched Research  →  Sold at premium
   (cheap inputs)            (synthesis)       (high-value output)
```

We buy raw intelligence from other agents on the marketplace — scraped web data, live DeFi prices, sentiment signals, risk scores — then synthesize it all through GPT-4o into a richer answer than any single agent could produce alone. We sell that enriched output at a margin.

**Unit economics example:**
- Buy from 3 suppliers: ~0.02-0.05 USDC
- Sell enriched answer: 0.10 USDC
- Margin: ~60-80%

---

## How We Decide Who to Buy From

Our dashboard API (`classifySupplier()`) encodes a priority-ranked decision tree that evaluates every agent on the marketplace:

### CRITICAL — Buy first. Without these, our answers are generic.

| Agent | Price | What They Give Us | Why It Matters |
|---|---|---|---|
| **CloudAGI Web Scraper** | 0.20 USDC | Fresh data from any URL | GPT-4o has a training cutoff. The scraper doesn't. When someone asks "what's ETH price today" — we can actually answer with live data. |
| **DataForge Web** | 0.01 USDC | Structured web extraction | Same idea, much cheaper. Pipelines into our summarizer for structured output. |
| **Crypto Market Intelligence** | 0.01-0.10 USDC | Live DeFi data, prices, yields | Our #1 query category. Users ask about DeFi constantly. Without live on-chain data we're guessing. |
| **AgentBank** | 0.01 USDC | On-chain financial data | Fractional banking data for agents. Cross-references with our financial research. |
| **AiRI (AI Resilience Index)** | 0.01 USDC | AI disruption risk scores | Nobody else offers resilience scoring. We layer this on company research — unique differentiation no competitor has. |
| **Market Intel Agent** | 0.10 USDC | Verified market analytics | Verified structured data beats hallucinated numbers every time. |

### HIGH — Adds dimensions our competitors don't have.

| Agent | Price | What They Give Us |
|---|---|---|
| **Social Media Manager** | Free | What people are actually talking about right now. Our answers reflect live trends, not stale training data. |
| **TrustNet** | 0.02 USDC | Agent trust scores. We can tell our customer "this was sourced from a 4.8/5 rated agent." |
| **QA Checker Agent** | Free-0.10 USDC | Independent fact-checking. Our answers come back verified, not just generated. |
| **CloudAGI Smart Search** | 0.05 USDC | Web search beyond training cutoff. Essential for current events research. |

### MEDIUM — These drive traffic TO us, not data.

| Agent | Role |
|---|---|
| **meta_agents** (Team Ironman) | Orchestrator — routes tasks to the best research agent. Being in their routing table = free inbound customers. |
| **AI Research Broker Agent** | Broker — white-labels our service and resells to their clients. |
| **ProcurePilot** | Procurement agent — recommends us to buyers shopping for research. |

### LOW — Nice to have.

| Agent | Role |
|---|---|
| **Nevermailed.com** | Email delivery for agents. Could notify customers of completed research. |
| **AgentCard Enhancement** | Improves our marketplace listing. Marketing channel. |
| Other LLM agents | Second-opinion AI. Cross-referencing improves accuracy through consensus. |

---

## The Decision Engine — How a Query Flows

When a query arrives, here's how the system decides what to buy:

```
User asks: "Is Aave v4 safe to use?"
                    ↓
     ZeroClick extracts intent signals:
       purchase_intent: "DeFi protocol evaluation"
       interest: "Aave v4 safety"
                    ↓
     LLM Advisor sees signals + budget (42 credits remaining today)
     Thinks: "This needs live DeFi data + risk scoring + verification"
                    ↓
     Decision: Buy from 3 suppliers
       1. Crypto Market Intelligence → "Aave v4 TVL, yield, recent exploits" (0.01 USDC)
       2. AiRI Resilience Index → "Aave v4 resilience score: 87/100" (0.01 USDC)
       3. QA Checker → verify the claims (free)
                    ↓
     GPT-4o synthesizes all three into one answer:
       "Aave v4 has $3.2B TVL, 87/100 resilience score, no exploits
        in 180 days. The protocol is considered safe with caveats..."
                    ↓
     Sold to customer for 1 credit (0.10 USDC)

     Cost: 0.02 USDC in supplier purchases
     Revenue: 0.10 USDC
     Margin: 0.08 USDC (80%)
```

The key insight: **the answer adapts based on the query**. A DeFi question triggers financial suppliers. A social trends question triggers the Social Media Manager. ZeroClick signals tell us what the user actually cares about.

---

## Who Buys From Us (and Why)

Looking at the 16 registered buyers on the marketplace:

| Buyer Agent | Team | What They Want | Why They Buy From Us |
|---|---|---|---|
| **AgentBank Treasury Ops** | WAGMI | "Market intelligence, research data, analytics" | That's literally our product. We're their research backend. |
| **AiRI Buyer Agent** | AiRI | "Company data enrichment, competitive analysis, sentiment analysis" | Our /ask + /summarize covers all of this — enriched with multi-source data. |
| **The Churninator** | TaskRoute | "Task-based evaluations and real-time performance metrics" | Our research engine evaluates anything on demand. |
| **Sabi** | BennySpenny | "Text that would benefit from verification" | Our fact-checked, multi-source research is exactly this. |
| **Market Intelligence Feed** | robin | "News sentiment scores" | We buy raw sentiment, synthesize it, sell it enriched. |
| **Social** | TrinityAgents | "Social analysis, topic analysis, trend analysis" | We aggregate social + search + data agents into a unified research answer. |

Other sellers also become our customers — agents like data analytics sellers buy our AI interpretation to enhance their own raw data output.

---

## The ZeroClick Signal Loop

ZeroClick isn't just ads. It's our **demand signal antenna**.

Every conversation generates intent signals extracted by GPT-4o-mini:
- `purchase_intent: "DeFi safety"`
- `evaluation: "Aave vs Compound"`
- `price_sensitivity: "cheap research"`

These signals serve two purposes:

1. **Sharpen buying decisions**: If signals say "DeFi", prioritize Crypto Market Intelligence over Social Media Manager for this specific query
2. **Surface sponsored offers**: When a user shows commercial intent, ZeroClick returns relevant product offers — revenue from attention, not just from research
3. **Build preference profile**: Accumulated signals across a session create a user profile. Future queries get better supplier selection because we know what this user cares about.

The broadcast flow:
```
User message → GPT-4o-mini extracts signals → stored locally + broadcast to ZeroClick MCP
                                                                     ↓
                                              ZeroClick builds preference profile
                                                                     ↓
                                              Returns personalized offers on next query
```

---

## Pricing Strategy

Our pricing in context of the marketplace:

| Agent | Price/query | What You Get |
|---|---|---|
| CloudAGI Smart Search | 0.05 USDC | Raw search results, no enrichment |
| **Us (Full Stack Agents)** | **0.10 USDC** | **Multi-source synthesized research** |
| Cortex | 0.10 USDC | Single LLM response |
| Nexus Intelligence Hub | 0.10 USDC | Single-source research |
| CloudAGI Code Review | 0.50 USDC | Specialized code review |
| AgentAudit | 1.00 USDC | Deep agent audits |

We're priced at market rate. The argument isn't that we're cheaper — it's that **our 0.10 USDC buys a better answer** because it's sourced from multiple agents, verified, and enriched with live data.

For summarization (3 credits = 0.30 USDC), we differentiate similarly: our summaries are cross-referenced with real data, not just LLM compression.

---

## Budget Constraints & Autonomous Spending

The buyer agent enforces hard limits:
- **Daily cap**: 50 credits/day (~5.00 USDC)
- **Per-request cap**: 10 credits max per single purchase

This forces smart allocation. We can't buy from everyone, so the priority ranking matters. The autonomous mode has three strategies:

- **Balanced**: Spread across agents — 1 purchase per agent per round (diversification)
- **Focused**: Concentrate on top 5 highest-value suppliers (conviction play)
- **Aggressive**: Maximum throughput, minimal delay (market-making)

Budget exhaustion triggers an automatic circuit breaker — the system stops buying and waits for the next daily reset.

---

## Haist: The Workflow Orchestration Layer

Haist is our visual workflow editor — think "n8n meets ChatGPT." Instead of hardcoding each supplier integration, we wire together composable "bubbles" on a visual canvas:

```
[Incoming Query] → [CloudAGI Scraper bubble] → [AiRI Score bubble] → [GPT-4o Synthesis bubble] → [Response]
```

When a new agent appears on the marketplace tomorrow, we add one bubble to our pipeline. No code changes. The supply chain is reconfigurable in minutes.

Haist also supports:
- Natural language workflow creation ("scrape Reddit, analyze with Gemini, export JSON")
- Scheduled automations (periodic discovery sweeps)
- Execution logging (track which supplier calls succeeded/failed)
- OpenClaw integration (local machine access for the AI assistant)

---

## The x402 Payment Protocol — How Transactions Work

Every purchase follows this flow:

```
1. Buyer gets x402 access token from Nevermined SDK
   → payments.x402.get_x402_access_token(plan_id, agent_id)
   → Returns signed JWT-like token

2. Buyer POSTs to seller with payment-signature header
   → POST https://seller.com/api/ask
   → Header: payment-signature: <token>
   → Body: {"query": "..."}

3. Seller middleware verifies token (read-only, no credits burned yet)
   → Checks: valid signature, correct plan, sufficient balance

4. Seller executes the work (LLM call, data processing, etc.)

5. Seller middleware settles — burns credits on-chain
   → ERC-1155 credit burn on Base Sepolia
   → ~$0.0001 gas (paid by Nevermined via ERC-4337 bundler)
   → Returns tx hash as receipt

6. Buyer gets response + settlement receipt in payment-response header
```

Two payment rails:
- **Crypto (nvm:erc4337)**: USDC on Base Sepolia. ERC-4337 smart accounts with session keys. No ETH needed.
- **Fiat (nvm:card-delegation)**: Stripe credit card. On-chain credit burn with automatic card-funded top-ups.

---

## The Dashboard: Supply Chain Visualization

Our 3D force-directed graph dashboard shows the entire economy from our perspective:

- **Green nodes (center)**: Our agents — seller + buyer
- **Cyan links inbound**: Agents we buy from (suppliers)
- **Amber links outbound**: Agents that buy from us (customers)
- **Link thickness**: Priority weight (CRITICAL = thickest)
- **Every link has a "why"**: Not just "we transact" but "we buy sentiment data because it adds emotional context that makes our research more actionable"

The dashboard API calls the Discovery API in real-time, classifies every agent as supplier/customer/peer, and computes supply chain cost vs revenue per cycle.

---

## The Marketplace at a Glance

```
54 sellers on the Nevermined marketplace
16 registered buyers
~20 teams participating
        ↓
Our buyer agent discovers all of them
        ↓
classifySupplier() ranks them: CRITICAL > HIGH > MEDIUM > LOW
        ↓
Budget allows 50 credits/day → forces selective purchasing
        ↓
We buy raw data from ~10 agents (cost: ~0.50 USDC/cycle)
        ↓
GPT-4o synthesizes into enriched research
        ↓
We sell to potential buyers (revenue: ~1.60 USDC/cycle)
        ↓
ZeroClick signals optimize which suppliers matter per query
        ↓
Dashboard visualizes the entire supply chain in real-time
        ↓
Haist lets us rewire the pipeline when new agents appear
```

---

## The Competitive Moat

Every team at the hackathon can sell GPT responses. But:

1. **We buy from our competitors** to make our product better than theirs
2. **Our competitors buy from us** because our synthesized output is more useful than their raw data
3. **The more agents we integrate, the better our answers, the more people buy**
4. **Budget discipline means we're profitable per transaction** — we don't overspend
5. **ZeroClick signals make each purchase smarter** — we learn what buyers want in real-time
6. **Haist makes our supply chain reconfigurable** — new agent on the marketplace? One new bubble in the pipeline.

We're not just an AI agent. We're a broker that buys cheap ingredients, cooks them into a premium dish, and sells it at 4x markup. The recipe changes based on what the customer ordered (ZeroClick signals), and the kitchen (Haist) can be rewired in minutes when new ingredients (agents) appear on the market.

---

## Technical Stack

- **Python 3.10+** with payments-py SDK
- **FastAPI** seller server with x402 PaymentMiddleware
- **NVM Terminal** — interactive CLI (prompt_toolkit + Rich) with slash commands + LLM chat
- **Haist** — visual workflow editor (Next.js + TypeScript)
- **Dashboard** — 3D supply chain visualization (Next.js + force-directed graph)
- **ZeroClick** — signal extraction (GPT-4o-mini) + MCP broadcast + offer rendering
- **Nevermined** — x402 protocol, plan management, credit settlement on Base Sepolia
- **OpenAI GPT-4o** — research synthesis engine
- **Base Sepolia** — L2 testnet, USDC stablecoin, ERC-4337 smart accounts

## Key IDs

- Wallet: `0x8d1915D5d4fE497Ec3795CdB927bE93c6c20d26E`
- Crypto Plan: sells 100 credits for 10 USDC
- Free Plan: 100 free credits (unlisted, for testing)
- Fiat Plan: $10 USD for 100 credits via Stripe
- USDC on Base Sepolia: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
