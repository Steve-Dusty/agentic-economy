# Full Stack Agents — The Story

## The Name Is the Answer

Every other team at this hackathon built one agent that does one thing. A scraper. A DeFi price feed. A sentiment analyzer. An email sender. They're microservices. Useful, but narrow.

We're not a microservice. We're the general contractor.

Think about building a house. You don't hire one person. You hire a plumber, an electrician, a roofer, a painter. But someone has to hire them all, schedule them, make sure the plumber finishes before the tiler starts, handle it when the electrician doesn't show up, and deliver you a house — not a pile of parts.

That's us. Haist is the construction site. The marketplace agents are the subcontractors. We deliver the finished house.

**Other teams sell ingredients. We sell recipes. Haist is the kitchen.**

---

## What We Actually Sell

We don't sell "AI answers." We sell automated workflows that chain multiple agents together into complete business solutions.

A customer doesn't come to us and say "what's ETH price." They go to Crypto Market Intelligence for that — it costs 0.01 USDC and they get a number.

A customer comes to us and says: "Every morning, check DeFi yields across the top 10 protocols, compare them to yesterday, score the risk of each one, summarize the findings, and post it to my Slack."

No single agent on the marketplace can do that. You need:

1. **Crypto Market Intelligence** — pulls the yield data (0.01 USDC)
2. **AiRI Resilience Index** — scores the risk (0.01 USDC)
3. **CloudAGI Web Scraper** — gets the latest protocol news (0.20 USDC)
4. **Our GPT-4o engine** — synthesizes all three into a coherent briefing
5. **Slack delivery** — via Haist's Slack bubble

Total input cost: ~0.23 USDC. We charge 1-3 credits (0.10-0.30 USDC) for the synthesized output. But the real value isn't the one-time answer — it's that Haist runs this every morning forever. The customer pays once to set it up, and it runs autonomously.

---

## Why "Full Stack"

On this marketplace:

- **CloudAGI** is backend — raw compute, scraping, search
- **Nevermailed** is infrastructure — email delivery
- **TrustNet** is QA — agent trust scoring
- **Crypto Market Intelligence** is a data feed — DeFi numbers
- **Social Media Manager** is a single channel — social posting

We're full stack because we touch every layer. We buy the backend data, process it through AI middleware, deliver it through frontend channels (Slack, email, dashboards), and orchestrate the whole thing through Haist workflows. We're the only team that doesn't do one thing — we do the thing that connects all the things.

---

## Haist IS the Product

Haist isn't a side project in our stack. Haist is the product.

Other teams sell endpoints. We sell pipelines. A Haist workflow is a visual chain of "bubbles" — each bubble is either one of our own capabilities or an x402 purchase from another marketplace agent. The customer describes what they want in plain English. Haist's AI assistant builds the workflow. It runs on schedule or on trigger.

### Example Workflows

**"DeFi Morning Briefing"**
```
[Schedule: 9am daily]
  → [Crypto Market Intelligence: top 10 yields]
  → [AiRI: risk score each protocol]
  → [GPT-4o: synthesize into briefing]
  → [Slack: post to #defi-alerts]
```

**"Competitor Watch"**
```
[Schedule: hourly]
  → [CloudAGI Scraper: check competitor URLs]
  → [Social Media Manager: pull social mentions]
  → [GPT-4o: summarize changes + sentiment]
  → [Email via Nevermailed: send digest]
```

**"Agent Portfolio Manager"**
```
[Schedule: every 6 hours]
  → [Discovery API: find new agents]
  → [TrustNet: score their reliability]
  → [AgentAudit: audit their quality]
  → [GPT-4o: recommend buy/skip/drop]
  → [Auto-purchase from top-scored agents]
```

**"Grant Research Pipeline"**
```
[Manual trigger]
  → [CloudAGI Smart Search: find grant opportunities]
  → [DataForge Web: extract application details]
  → [QA Checker: verify deadlines and eligibility]
  → [GPT-4o: draft application summary]
  → [Google Sheets: log to tracking spreadsheet]
```

**"Social Pulse Report"**
```
[Schedule: every 4 hours]
  → [Social Media Manager: trending topics]
  → [CloudAGI Scraper: pull top Reddit/Twitter threads]
  → [Sentiment analysis via GPT-4o]
  → [Nevermailed: email report to team]
```

Each arrow that crosses into another team's agent is an x402 payment. We're spending credits to buy raw ingredients and selling the assembled meal.

---

## How We Decide What to Buy

We don't buy randomly. We buy based on what workflows our customers need.

If nobody's asking for DeFi briefings, we don't buy from Crypto Market Intelligence. If everyone wants social monitoring, we increase our spend on Social Media Manager and sentiment agents. ZeroClick signals tell us what people are actually asking about — that's our demand signal. The buyer agent's budget allocation follows demand.

### The Priority Ranking

**CRITICAL suppliers** — agents whose data appears in our most popular workflows:
- Web scrapers (CloudAGI, DataForge) — fresh data beyond LLM training cutoff
- DeFi feeds (Crypto Market Intelligence, AgentBank) — live on-chain numbers
- Data analytics (Market Intel Agent, AiRI) — verified, structured facts

**HIGH suppliers** — agents that add differentiation no competitor has:
- Sentiment agents (Social Media Manager) — emotional context layered on top of facts
- Verification agents (QA Checker, TrustNet) — independently checked claims
- Search agents (CloudAGI Smart Search) — current events past training cutoff

**MEDIUM suppliers** — agents that drive traffic to us, not data:
- Orchestrators (meta_agents) — they route tasks to us, we get free inbound customers
- Brokers (AI Research Broker) — they white-label our workflows for their clients
- Procurement (ProcurePilot) — they recommend us to buyers shopping for solutions

**LOW** — nice to have:
- Advertising (Nevermailed for reach, AgentCard for marketplace presence)
- Other LLMs (second-opinion consensus, marginally better accuracy)

### The Budget Constraint

50 credits/day. 10 credits max per purchase. This forces smart allocation — we can't buy from everyone, so the priority ranking matters. When budget is tight, we cut LOW and MEDIUM first. CRITICAL suppliers keep running because without them, our most valuable workflows break.

---

## The Pricing Logic

A single agent call costs 0.01-0.20 USDC on the marketplace. Raw. One-shot. The customer has to know which agent to call, subscribe to their plan, handle the x402 token, parse the response.

We charge 0.10-0.30 USDC per workflow step — but the customer gets:

- **Orchestration** — multiple agents wired together, not DIY
- **Synthesis** — interpreted intelligence, not raw data dumps
- **Automation** — runs on schedule or trigger, not one-shot
- **Reliability** — Haist handles retries and fallbacks if a supplier is down
- **One subscription** — instead of managing five separate agent plans

We're the bundle. Like how you don't buy individual AWS services — you buy a solution from a consultancy that wires them together. The agents are Lambda, S3, DynamoDB. We're the solutions architect.

---

## The ZeroClick Loop

ZeroClick isn't ads. It's how we learn what to build next.

Every conversation generates intent signals: "DeFi safety", "competitor tracking", "grant applications." These accumulate. Over time they tell us:

- Which workflow templates are most requested → build more of those
- Which supplier categories matter most → increase budget there
- Which customers have recurring needs → offer them scheduled automations
- What price sensitivity looks like → adjust credit costs per workflow

ZeroClick closes the feedback loop between demand and supply. Without it we're guessing which workflows to build. With it we know.

---

## The Dashboard

The dashboard isn't vanity. It shows the real-time supply chain:

- Which agents we're currently buying from (our active subcontractors)
- Which agents are buying from us (our customers)
- The cost-to-revenue ratio (are we profitable per workflow?)
- Which links are CRITICAL vs optional (what breaks if a supplier goes down?)
- How the broader marketplace economy flows between teams

It's the general contractor's project management board. Every link has a reason: "We buy from X because workflow Y needs their data." "Z buys from us because they need orchestrated research, not raw endpoints."

---

## The NVM Terminal

The terminal is the operator's seat. When the system runs autonomously, you don't need it. But when you want to:

- Manually test a purchase from a new agent → `/buy AgentName test query`
- Check if the budget is healthy → `/budget`
- See what the marketplace looks like right now → `/discover`
- Spin up autonomous purchasing → `/auto balanced`
- Ask the AI advisor "which agents should I add to the DeFi briefing workflow?" → just type it

It's the human override for an otherwise autonomous system.

---

## The Full Picture

```
MARKETPLACE (54 specialized agents)
  │
  │ Discovery API: who's selling what, at what price?
  │
  ▼
BUYER AGENT (procurement department)
  │
  │ Classifies agents by priority
  │ Budget: 50 credits/day
  │ ZeroClick signals: what do customers actually want?
  │
  ▼
HAIST (the workflow engine — THIS IS THE PRODUCT)
  │
  │ Wires agents into automated pipelines
  │ Visual canvas or natural language
  │ Runs on schedule, trigger, or manual
  │
  ▼
SELLER AGENT (the storefront)
  │
  │ Exposes workflow outputs as paid endpoints
  │ x402 payment: verify → execute workflow → settle on-chain
  │ 0.10-0.30 USDC per request
  │
  ▼
CUSTOMERS (16 marketplace buyers + direct users)
  │
  │ Get orchestrated, multi-source, synthesized intelligence
  │ Not raw data — finished products
  │
  ▼
DASHBOARD (the control room)
  │
  │ Shows the entire supply chain in real-time
  │ Why each relationship exists
  │ Cost vs revenue per cycle
  │
  ▼
ZEROCLICK (the feedback antenna)
    │
    │ Learns what customers want
    │ Shapes which workflows we build
    │ Shapes which suppliers we prioritize
    │ Closes the loop
```

---

## The Economy We're In

We're not in the "sell LLM answers" economy. Every team does that.

We're in the **orchestration economy.** The marketplace has 54 specialists. Customers don't want to hire 5 specialists and manage them. They want one contractor who handles everything.

That contractor is us. The "full stack" isn't a buzzword — it's the literal business model. We span the full stack of the agent economy: discovery, procurement, orchestration, synthesis, delivery, and feedback. Nobody else does all of it.

The subcontractors compete on who has the cheapest raw data. We compete on who assembles it into the most valuable finished product. Different game entirely.
