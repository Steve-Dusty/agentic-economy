# Autonomous Business Hackathon — Project Overview

## Goal
Build an autonomous business where AI agents buy and sell services from other teams' agents. All transactions go through Nevermined.

## Deadline
**8PM March 5**: Must have at least 1 paid agent-to-agent transaction to be eligible for prizes.

---

## How Nevermined Works

Nevermined is the **payment and settlement layer** between all agents. It:
1. **Meters** usage (tracks credits per API call)
2. **Bills** via x402 tokens (buyer proves they can pay)
3. **Settles** on-chain (burns ERC-1155 credits on Base L2, ~$0.0001/tx)

### The x402 Payment Flow
```
Buyer                          Seller                      Nevermined
  |                              |                            |
  |--- POST /data ------------->|                            |
  |<-- 402 Payment Required ----|                            |
  |                              |                            |
  |--- get x402 token ---------------------------------->|
  |<-- accessToken ----------------------------------------|
  |                              |                            |
  |--- POST /data ------------->|                            |
  |    + payment-signature       |--- verify token -------->|
  |                              |<-- ok -------------------|
  |                              |                            |
  |                              | (execute business logic)   |
  |                              |                            |
  |                              |--- settle credits ------->|
  |<-- 200 + response -----------|<-- receipt ---------------|
```

### Payment Methods (both use x402 protocol)
| | Fiat (Recommended) | Crypto |
|---|---|---|
| Scheme | `nvm:card-delegation` | `nvm:erc4337` |
| Funding | Stripe test cards | USDC on Base testnet |
| Setup | Enroll card at nevermined.app | Get test USDC from faucet.circle.com |
| Seller code | Same | Same |
| Buyer code | Needs `CardDelegationConfig` | Simpler token options |

**Using fiat/Stripe** — no crypto wallet needed, just Stripe test card numbers from https://docs.stripe.com/testing

---

## Architecture Choices

### Protocol Options
| Protocol | Best For | How It Works |
|---|---|---|
| **x402 HTTP** | Simple REST APIs | Standard HTTP + payment headers |
| **A2A** | Multi-agent discovery | Agent cards + JSON-RPC + SSE streaming |
| **MCP** | Tool monetization | Logical URLs, per-tool pricing |

### Starter Kit (github.com/nevermined-io/hackathons)
- **Seller agent**: FastAPI server, 3 tiered tools (search=1cr, summarize=5cr, research=10cr)
- **Buyer agent**: Discovers sellers, manages budgets, purchases with x402 tokens
- Can extend these or build from scratch

---

## Environment Variables Needed
```env
NVM_API_KEY=sandbox:your-key          # Get from nevermined.app → API Keys
NVM_ENVIRONMENT=sandbox
NVM_PLAN_ID=did:nv:your-plan-id      # Create at nevermined.app → Create Agent
NVM_AGENT_ID=your-agent-id           # Needed for A2A mode
OPENAI_API_KEY=sk-your-key           # For LLM-powered tools
SELLER_URL=http://localhost:3000     # Default seller endpoint
```

---

## SDK Quick Reference
```python
from payments_py import Payments, PaymentOptions

# Initialize
payments = Payments.get_instance(
    PaymentOptions(nvm_api_key="sandbox:xxx", environment="sandbox")
)

# Check balance
payments.plans.get_plan_balance(plan_id)

# Get x402 token (buyer side)
token = payments.x402.get_x402_access_token(plan_id, agent_id)

# Verify token (seller side — read-only)
payments.facilitator.verify_permissions(token, plan_id)

# Settle credits (seller side — burns credits)
payments.facilitator.settle_permissions(token, plan_id, credits=1)
```

### FastAPI Middleware (seller shortcut)
```python
from payments_py.x402.fastapi import PaymentMiddleware

app.add_middleware(PaymentMiddleware, payments=payments,
    routes={"POST /data": {"plan_id": PLAN_ID, "credits": 1}})
```

---

## Prize Strategy
| Prize | Amount | What to demonstrate |
|---|---|---|
| Best Seller | **$3,000** | Sell to 2+ teams, 3+ transactions, repeat buyers |
| Best Buyer | $1,000 | Buy from 2+ teams, 3+ txns, switching/repeat logic |
| Most Interconnected | $1,000 | Both buy AND sell, most cross-team transactions |
| Ability | $2,000 | Best use of TrinityOS + Nevermined |
| Mindra | $2,000 | 5+ agents in single flow, hierarchical orchestration |
| ZeroClick | $2,000 | Best ZeroClick AI native ads + Nevermined |

---

## Next Steps
1. [ ] Sign up at nevermined.app, get sandbox API key
2. [ ] Create a payment plan (pricing + credits)
3. [ ] Clone starter repo and get seller agent running
4. [ ] Execute first paid transaction (meet 8PM deadline)
5. [ ] Build out unique business logic
6. [ ] List service in shared Team Registration
7. [ ] Buy from other teams' agents
