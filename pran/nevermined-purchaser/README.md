# Nevermined Purchaser Agent

A purchasing agent that calls paid AI agents via the [Nevermined](https://nevermined.app) x402 payment protocol.

## How It Works

1. Authenticates with your Nevermined API key
2. Gets an x402 payment token for the target agent's plan
3. Sends a request with the `payment-signature` header
4. Credits are burned only on successful execution

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

You need:

| Variable | Description | Where to get it |
|----------|-------------|-----------------|
| `NVM_API_KEY` | Your personal API key | [nevermined.app](https://nevermined.app) → Settings → API Keys |
| `NVM_PLAN_ID` | Payment plan of the agent to call | From the agent publisher |
| `NVM_AGENT_ID` | ID of the agent to call | From the agent publisher |

Make sure you've purchased the plan so you have credits.

## Usage

### Call an agent

```bash
source venv/bin/activate
export $(grep -v '^#' .env | grep -v '^$' | xargs)
python3 pay_and_call.py call --url <AGENT_URL> --message "your message"
```

### Check balance

```bash
python3 pay_and_call.py balance
```

### Override plan/agent IDs

```bash
python3 pay_and_call.py call --url <AGENT_URL> --message "hello" --plan-id <PLAN_ID> --agent-id <AGENT_ID>
```

## Example

```
$ python3 pay_and_call.py call --url https://example.com/api/paid/my-agent/chat --message "Hello"
Credits remaining: 17
Getting payment token...
Calling https://example.com/api/paid/my-agent/chat...
Status: 200
{
  "response": "...",
  "status": "success",
  "payment": {
    "settled": true,
    "credits_burned": 1
  }
}
```

## License

MIT
