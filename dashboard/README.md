# Agentic Economy Dashboard

Live 3D visualization of the Nevermined hackathon agent marketplace, centered on our **AI Research & Summarization Engine**. Built for the Autonomous Business Hackathon (AWS Loft SF, March 2026).

![Stack](https://img.shields.io/badge/Next.js-16-black) ![Stack](https://img.shields.io/badge/Three.js-3D-blue) ![Stack](https://img.shields.io/badge/Nevermined-Payments-green)

## What This Is

An interactive 3D force-directed graph that maps the entire agentic economy — every seller, buyer, and team registered on the Nevermined hackathon marketplace — and shows **why** each connection exists from our product's perspective.

This isn't a generic marketplace browser. Every link answers a question:
- **Supply links (cyan):** "Why do we buy from this agent?" — e.g., *"Sentiment data adds emotional context to our research"*
- **Revenue links (amber):** "Why does this agent buy from us?" — e.g., *"Needs AI-powered interpretation of raw data"*
- **Internal pipeline (green):** How purchased intelligence flows through our buyer agent into our AI engine and out to customers

## How the Economy Works

### Our Product

We sell two paid API endpoints on Nevermined, powered by GPT-4o:

| Endpoint | Credits | What It Does |
|----------|---------|--------------|
| `POST /api/crypto/ask` | 1 | Expert AI research on any topic |
| `POST /api/crypto/summarize` | 3 | Intelligent text summarization |

Payment is via **x402** (HTTP 402 protocol) using USDC on Base Sepolia. Buyers order a plan, get credits, then spend them per-request with a `payment-signature` header. The middleware verifies and settles on-chain automatically.

### The Supply Chain

Our buyer agent autonomously purchases from other teams' agents to **enrich** the data our research engine can draw from:

```
[Sentiment Agent] ──sentiment──> [Our Buyer] ──feeds──> [Our AI Engine] ──research──> [Customer Agents]
[DeFi Data Agent] ──prices────>       │                       │
[Web Scraper]     ──live data──>      │                       │
[Social Monitor]  ──trends────>       │                       ├──> /ask (1 credit)
                                      │                       └──> /summarize (3 credits)
                                      │
                              purchased intelligence
                              enriches every response
```

Each supplier is classified by **capability** and **priority**:
- **CRITICAL:** Data analytics, DeFi intelligence, web scraping — directly ground our research in facts
- **HIGH:** Sentiment analysis, social intelligence, verification — add context and credibility
- **MEDIUM:** Orchestrators, brokers — drive volume by routing queries to us
- **LOW:** Advertising, complementary AI — nice-to-have integrations

### The Revenue Side

Other agents buy from us because:
- **Analytics agents** need AI-powered interpretation of their raw data
- **Orchestrators** route research tasks to the best available agent (us)
- **DeFi agents** need research on financial topics, protocol analysis, whitepaper summaries
- **Verification agents** use our research claims as input to their verification pipeline

### Payment Flow (x402)

```
1. Buyer discovers us via Nevermined Discovery API
2. Buyer calls order_plan(plan_id) → pays USDC → gets credits
3. Buyer calls get_x402_access_token(plan_id, agent_id) → JWT token
4. Buyer POSTs to /api/crypto/ask with payment-signature header
5. Our middleware: verify token → check credits → execute → settle on-chain
6. Response returned, credits burned (~$0.0001 settlement on Base L2)
```

## Dashboard Features

### 3D Force Graph
- Glowing Three.js nodes with custom shaders per node type
- Our agents are large, green, double-ringed — always gravitationally centered
- Supply chain links pulse with directional particles (cyan = data flowing in, amber = revenue flowing out)
- Physics simulation clusters teams together naturally
- Click any node to fly the camera toward it

### Inspector Panel
Click any node to see:
- **Strategic Value** — why this agent matters to our economy
- **Supply Chain Connections** — every link with its reason, priority badge, and strategic impact
- Agent metadata: endpoints, pricing, plan IDs, wallet, description

### Natural Language Search
Press `/` to focus. Supports:
- `why did we buy from [name]` — finds supply links with reasoning
- `why does [name] buy from us` — finds customer links with reasoning
- `who buys from us` / `our customers` — lists all revenue streams
- `our suppliers` / `supply chain` — lists all data sources
- `what do we sell` / `our product` — shows our seller agents
- `critical` / `high priority` — filters by connection priority
- Plan IDs, wallet addresses (`0x...`), agent names — direct lookup

### Decision Transcript
Bottom-left live feed showing the autonomous analysis:
- Strategic positioning of our product
- Each supplier evaluated with priority and reasoning
- Revenue stream identification
- Economy optimization summary with cost/revenue estimates

## Setup

```bash
# Install
npm install

# Configure (copy and fill in your Nevermined credentials)
cp .env.example .env.local

# Run
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Environment Variables

| Variable | Description |
|----------|-------------|
| `NVM_API_KEY` | Nevermined API key (`sandbox:eyJ...`) |
| `NVM_ENVIRONMENT` | `sandbox` or `live` |
| `USDC_WALLET` | Your wallet address on Base Sepolia |
| `NVM_AGENT_ID_CRYPTO` | Your seller agent ID |
| `NVM_PLAN_ID_CRYPTO` | Your crypto (USDC) plan ID |
| `NVM_PLAN_ID_FREE` | Your free plan ID |
| `NVM_BUYER_AGENT_ID` | Your buyer agent ID |

## Architecture

```
src/
├── app/
│   ├── page.tsx                    # Root — dynamically imports GraphContainer (no SSR)
│   └── api/economy/route.ts        # Fetches Nevermined Discovery API, builds graph
│                                    #   with intelligent supply chain classification
├── components/
│   ├── ForceGraph3D.tsx            # Three.js 3D graph (react-force-graph-3d)
│   │                               #   Custom node objects: spheres, glow sprites, labels
│   │                               #   Custom force pulling our nodes to center
│   ├── GraphContainer.tsx          # Main orchestrator: data loading, state, layout
│   ├── AgentPanel.tsx              # Right sidebar inspector with supply chain context
│   ├── SearchBar.tsx               # NLP-style search with fuzzy matching
│   ├── TranscriptStream.tsx        # Bottom-left decision log
│   └── StatsOverlay.tsx            # Top-right economy metrics
└── types/
    └── graph.ts                    # AgentNode, AgentLink, TranscriptEntry, etc.
```

### Key Design Decisions

**Why product-centered, not marketplace-centered:**
Every dashboard at the hackathon will show "all agents." Ours shows the economy *from our product's perspective* — why each connection exists, what it costs us, what revenue it drives. This is the "autonomous business" the hackathon is about.

**Why natural language search:**
Judges and demos need instant answers: "why did we buy from X?" Typing that into a search bar and getting the exact strategic reasoning is more compelling than clicking through nodes.

**Why Three.js custom nodes instead of default:**
The glow sprites, double rings on our agents, hexagonal/pentagonal role badges — these visual cues let you instantly distinguish our product (green, large, ringed) from suppliers (cyan badge) and customers (amber badge) without reading labels.

## Tech Stack

- **Next.js 16** — App Router, API routes, TypeScript
- **react-force-graph-3d** — 3D force-directed graph on Three.js
- **Three.js** — Custom node rendering (spheres, glow sprites, ring geometry)
- **Tailwind CSS** — Glassmorphic dark theme
- **Nevermined Discovery API** — Live marketplace data
- **x402 Protocol** — HTTP 402-based agent payments (USDC on Base Sepolia)
