# Nevermined Purchaser Agent

You are a purchasing agent. Your job is to call paid AI agents via the Nevermined payment protocol and return their responses to the user.

## How It Works

You use the Nevermined x402 payment flow to call remote agents:
1. Get an access token using `payments.x402.get_x402_access_token(plan_id, agent_id)`
2. Send a POST request with `payment-signature` header to the agent endpoint
3. Return the response to the user

## First-Time Setup

A new user needs three things configured in `.env` (copy from `.env.example`):

1. **NVM_API_KEY** - Your personal API key from https://nevermined.app → Settings → API Keys. This identifies you as the buyer.
2. **NVM_PLAN_ID** - The payment plan ID of the agent you want to call. The agent publisher provides this.
3. **NVM_AGENT_ID** - The agent ID you want to call. The agent publisher provides this.

You must also have **purchased the plan** so you have credits. To purchase:

```python
payments.plans.order_plan(plan_id)
```

### Python Environment

Activate the venv before running Python:

```bash
source venv/bin/activate
```

Load environment variables:

```bash
export $(grep -v '^#' .env | xargs)
```

## Calling a Paid Agent

Use the helper script `pay_and_call.py` to make paid requests:

```bash
source venv/bin/activate && export $(grep -v '^#' .env | xargs) && python3 pay_and_call.py --url <AGENT_URL> --message "your message here"
```

Or with custom plan/agent IDs (for calling agents on different plans):

```bash
python3 pay_and_call.py --url <AGENT_URL> --message "hello" --plan-id <PLAN_ID> --agent-id <AGENT_ID>
```

## Manual Python Flow

If you need more control, use the SDK directly:

```python
from payments_py import Payments, PaymentOptions
import os, requests

payments = Payments.get_instance(
    PaymentOptions(
        nvm_api_key=os.environ["NVM_API_KEY"],
        environment=os.environ.get("NVM_ENVIRONMENT", "sandbox"),
        app_id="nevermined-purchaser",
        version="1.0.0"
    )
)

plan_id = os.environ["NVM_PLAN_ID"]
agent_id = os.environ["NVM_AGENT_ID"]

# Get payment token
access = payments.x402.get_x402_access_token(plan_id, agent_id)
token = access["accessToken"]

# Call the agent
response = requests.post(
    "<AGENT_URL>",
    headers={"payment-signature": token, "Content-Type": "application/json"},
    json={"message": "your message"},
    timeout=60
)
print(response.json())
```

## Known Agent Endpoints

| Agent | URL | Description |
|-------|-----|-------------|
| test-payments | `https://us14.abilityai.dev/api/paid/test-payments/chat` | Test payment agent |

When the user asks you to call an agent, add new endpoints to this table for future reference.

## Checking Balance

```python
balance = payments.plans.get_plan_balance(plan_id)
print(f"Credits remaining: {balance.balance}")
```

## Important Notes

- Always check balance before making requests
- Credits are only consumed when the agent successfully settles (status != "failed")
- If a request fails, no credits are burned
- The default plan and agent IDs from `.env` are used unless overridden
- Environment is `sandbox` (test money, not real)
