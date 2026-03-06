"""Nevermined x402 payment client - handles token generation and paid agent calls."""

import requests
from payments_py import Payments, PaymentOptions

from .config import BUYER_NVM_API_KEY, PLAN_ID, AGENTS


_payments = None


def get_payments() -> Payments:
    global _payments
    if _payments is None:
        _payments = Payments.get_instance(
            PaymentOptions(nvm_api_key=BUYER_NVM_API_KEY, environment="sandbox")
        )
    return _payments


def get_balance() -> dict:
    p = get_payments()
    result = p.plans.get_plan_balance(PLAN_ID)
    return {"balance": result.balance, "is_subscriber": result.is_subscriber}


def call_agent(agent_name: str, message: str, timeout: int = 90) -> dict:
    """Call a leaf agent via x402 payment. Returns the response dict."""
    agent = AGENTS[agent_name]
    p = get_payments()

    # Get x402 access token
    token_result = p.x402.get_x402_access_token(
        plan_id=PLAN_ID, agent_id=agent["agent_id"]
    )
    token = token_result["accessToken"]

    # Call the paid endpoint
    resp = requests.post(
        agent["endpoint"],
        headers={"Content-Type": "application/json", "payment-signature": token},
        json={"message": message},
        timeout=timeout,
    )

    if resp.status_code == 200:
        data = resp.json()
        return {
            "status": "success",
            "agent": agent_name,
            "response": data.get("response", ""),
            "credits_burned": data.get("payment", {}).get("credits_burned", 0),
            "tx_hash": data.get("payment", {}).get("tx_hash", ""),
        }
    else:
        return {
            "status": "error",
            "agent": agent_name,
            "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            "credits_burned": 0,
        }
