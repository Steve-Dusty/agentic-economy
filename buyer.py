"""
Buyer agent — discovers sellers on the Nevermined marketplace,
purchases data via x402 payments, tracks spending.

Usage:
    python buyer.py                          # Interactive CLI
    python buyer.py "search for AI trends"   # One-shot query
"""
import base64
import json
import os
import sys
import threading
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from payments_py import Payments, PaymentOptions

load_dotenv()

NVM_API_KEY = os.environ["NVM_API_KEY"]
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.environ.get("NVM_PLAN_ID", "")
NVM_AGENT_ID = os.environ.get("NVM_AGENT_ID", "")
SELLER_URL = os.getenv("SELLER_URL", "http://localhost:3000")
MAX_DAILY_SPEND = int(os.getenv("MAX_DAILY_SPEND", "50"))
MAX_PER_REQUEST = int(os.getenv("MAX_PER_REQUEST", "10"))

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)


# ---------------------------------------------------------------------------
# Budget tracker
# ---------------------------------------------------------------------------
class Budget:
    def __init__(self, max_daily: int = 0, max_per_request: int = 0):
        self._lock = threading.Lock()
        self._max_daily = max_daily
        self._max_per_request = max_per_request
        self._daily_spend = 0
        self._total_spend = 0
        self._purchase_count = 0
        self._current_day = datetime.now(timezone.utc).date()
        self._purchases: list[dict] = []

    def _reset_if_new_day(self):
        today = datetime.now(timezone.utc).date()
        if today != self._current_day:
            self._daily_spend = 0
            self._current_day = today

    def can_spend(self, credits: int) -> tuple[bool, str]:
        with self._lock:
            self._reset_if_new_day()
            if self._max_per_request > 0 and credits > self._max_per_request:
                return False, f"Costs {credits} but per-request limit is {self._max_per_request}"
            if self._max_daily > 0 and (self._daily_spend + credits) > self._max_daily:
                remaining = self._max_daily - self._daily_spend
                return False, f"Costs {credits} but only {remaining} left in daily budget"
            return True, "OK"

    def record(self, credits: int, seller: str, query: str):
        with self._lock:
            self._reset_if_new_day()
            self._daily_spend += credits
            self._total_spend += credits
            self._purchase_count += 1
            self._purchases.append({
                "credits": credits, "seller": seller,
                "query": query[:80], "time": datetime.now(timezone.utc).isoformat(),
            })

    def status(self) -> dict:
        with self._lock:
            self._reset_if_new_day()
            u = "unlimited"
            return {
                "daily_limit": self._max_daily or u,
                "daily_spent": self._daily_spend,
                "daily_remaining": (self._max_daily - self._daily_spend) if self._max_daily else u,
                "per_request_limit": self._max_per_request or u,
                "total_spent": self._total_spend,
                "purchases": self._purchase_count,
                "recent": self._purchases[-5:],
            }


budget = Budget(max_daily=MAX_DAILY_SPEND, max_per_request=MAX_PER_REQUEST)


# ---------------------------------------------------------------------------
# Buyer operations
# ---------------------------------------------------------------------------
def discover_pricing(seller_url: str = SELLER_URL) -> dict:
    """Discover a seller's pricing and available endpoints."""
    r = requests.get(f"{seller_url}/pricing", timeout=15)
    r.raise_for_status()
    return r.json()


def check_balance(plan_id: str) -> dict:
    """Check credit balance on a plan."""
    bal = payments.plans.get_plan_balance(plan_id)
    return {
        "plan_id": bal.plan_id,
        "plan_name": bal.plan_name,
        "balance": bal.balance,
        "is_subscriber": bal.is_subscriber,
    }


def ensure_subscribed(plan_id: str) -> dict:
    """Subscribe to a plan if not already subscribed, return balance."""
    bal = check_balance(plan_id)
    if not bal["is_subscriber"]:
        print("    Not subscribed — ordering plan...")
        payments.plans.order_plan(plan_id)
        bal = check_balance(plan_id)
        print(f"    Subscribed! Balance: {bal['balance']} credits")
    return bal


def purchase(plan_id: str, agent_id: str, seller_url: str, endpoint: str, payload: dict, credits_cost: int = 1) -> dict:
    """Get x402 token and call a paid seller endpoint with budget checks."""
    # Budget pre-check
    allowed, reason = budget.can_spend(credits_cost)
    if not allowed:
        return {"status": "budget_exceeded", "detail": reason}

    # Get x402 access token
    token_result = payments.x402.get_x402_access_token(
        plan_id=plan_id,
        agent_id=agent_id,
    )
    access_token = token_result.get("accessToken")
    if not access_token:
        return {"status": "error", "detail": "Failed to get x402 token. Are you subscribed?"}

    # Call seller with payment header
    r = requests.post(
        f"{seller_url}{endpoint}",
        headers={
            "payment-signature": access_token,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )

    if r.status_code == 402:
        # Decode payment-required header if present
        pr_header = r.headers.get("payment-required", "")
        detail = r.text
        if pr_header:
            try:
                detail = json.dumps(json.loads(base64.b64decode(pr_header)), indent=2)
            except Exception:
                pass
        return {"status": "payment_required", "detail": detail}
    elif r.status_code != 200:
        return {"status": "error", "code": r.status_code, "detail": r.text[:500]}

    # Record the spend
    query_str = payload.get("query", payload.get("text", str(payload)))
    budget.record(credits_cost, seller_url, query_str)

    return {"status": "success", "data": r.json(), "credits_used": credits_cost}


# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------
def interactive_cli():
    print("=" * 60)
    print("  Buyer Agent — Nevermined x402 Marketplace")
    print("=" * 60)
    print(f"  Seller:    {SELLER_URL}")
    print(f"  Budget:    {MAX_DAILY_SPEND}/day, {MAX_PER_REQUEST}/request")
    print()

    # Discover seller
    print("[1] Discovering seller...")
    try:
        pricing = discover_pricing(SELLER_URL)
        plan_id = pricing.get("plan_id", NVM_PLAN_ID)
        agent_id = pricing.get("agent_id", NVM_AGENT_ID)
        endpoints = pricing.get("endpoints", {})
        print(f"    Plan:  {plan_id[:50]}...")
        print(f"    Agent: {agent_id[:50]}...")
        print("    Endpoints:")
        for ep, info in endpoints.items():
            print(f"      {ep} — {info['credits']} credit(s) — {info['description']}")
    except Exception as e:
        print(f"    Failed: {e}")
        print(f"    Make sure seller is running at {SELLER_URL}")
        return

    # Subscribe + check balance
    print(f"\n[2] Checking subscription...")
    try:
        bal = ensure_subscribed(plan_id)
        print(f"    Balance: {bal['balance']} credits")
    except Exception as e:
        print(f"    Error: {e}")
        return

    # REPL
    print(f"\n[3] Ready! Enter queries to buy data.")
    print("    Commands: balance, budget, pricing, quit")
    print("    Prefix 's:' for summarize (3 credits)")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        cmd = user_input.lower()
        if cmd in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if cmd == "balance":
            b = check_balance(plan_id)
            print(f"  Credits: {b['balance']} (subscriber={b['is_subscriber']})\n")
            continue
        if cmd == "budget":
            print(f"  {json.dumps(budget.status(), indent=2)}\n")
            continue
        if cmd == "pricing":
            p = discover_pricing(SELLER_URL)
            for ep, info in p.get("endpoints", {}).items():
                print(f"  {ep} — {info['credits']} credit(s)")
            print()
            continue

        # Determine endpoint
        if user_input.startswith("s:"):
            endpoint = "/api/summarize"
            payload = {"text": user_input[2:].strip()}
            credits_cost = 3
        else:
            endpoint = "/api/ask"
            payload = {"query": user_input}
            credits_cost = 1

        print(f"  -> POST {endpoint} ({credits_cost} credit{'s' if credits_cost > 1 else ''})")

        result = purchase(plan_id, agent_id, SELLER_URL, endpoint, payload, credits_cost)

        if result["status"] == "success":
            data = result["data"]
            answer = data.get("answer") or data.get("summary") or str(data)
            print(f"  Agent: {answer}")
            b = check_balance(plan_id)
            print(f"  [Credits: {b['balance']} | Day spent: {budget.status()['daily_spent']}]\n")
        elif result["status"] == "budget_exceeded":
            print(f"  Budget exceeded: {result['detail']}\n")
        else:
            print(f"  Error ({result['status']}): {result.get('detail', result)}\n")


def one_shot(query: str):
    """Single query mode."""
    pricing = discover_pricing(SELLER_URL)
    plan_id = pricing.get("plan_id", NVM_PLAN_ID)
    agent_id = pricing.get("agent_id", NVM_AGENT_ID)

    ensure_subscribed(plan_id)

    result = purchase(plan_id, agent_id, SELLER_URL, "/api/ask", {"query": query}, credits_cost=1)
    if result["status"] == "success":
        print(result["data"].get("answer", result["data"]))
    else:
        print(f"Error: {result}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        one_shot(" ".join(sys.argv[1:]))
    else:
        interactive_cli()
