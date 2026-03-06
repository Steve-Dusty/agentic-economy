"""Purchase engine — x402 payment flow."""
import base64
import json
import requests
from .state import AppState
from .budget import Budget


def check_balance(state: AppState, plan_id: str) -> dict:
    """Check credit balance on a plan."""
    bal = state.payments.plans.get_plan_balance(plan_id)
    return {
        "plan_id": bal.plan_id,
        "plan_name": bal.plan_name,
        "balance": bal.balance,
        "is_subscriber": bal.is_subscriber,
    }


def check_all_balances(state: AppState) -> list[dict]:
    """Check balances for all configured plans."""
    results = []
    plan_ids = {
        "Free Plan": state.config.get("plan_id"),
        "Crypto Plan": state.config.get("plan_id_crypto"),
        "Fiat Plan": state.config.get("plan_id_fiat"),
    }
    for label, pid in plan_ids.items():
        if not pid:
            continue
        try:
            bal = check_balance(state, pid)
            bal["label"] = label
            results.append(bal)
        except Exception as e:
            results.append({"label": label, "plan_id": pid, "balance": f"error: {e}", "is_subscriber": False})
    return results


def subscribe(state: AppState, plan_id: str) -> dict:
    """Subscribe to a plan if not already subscribed."""
    bal = check_balance(state, plan_id)
    if not bal["is_subscriber"]:
        state.payments.plans.order_plan(plan_id)
        bal = check_balance(state, plan_id)
    return bal


def purchase(state: AppState, budget: Budget, plan_id: str, agent_id: str,
             seller_url: str, endpoint: str, payload: dict, credits_cost: int = 1) -> dict:
    """Full x402 purchase flow: budget check -> token -> POST -> record."""
    # Budget pre-check
    allowed, reason = budget.can_spend(credits_cost)
    if not allowed:
        return {"status": "budget_exceeded", "detail": reason}

    # Get x402 access token
    try:
        token_result = state.payments.x402.get_x402_access_token(
            plan_id=plan_id,
            agent_id=agent_id,
        )
        access_token = token_result.get("accessToken")
        if not access_token:
            return {"status": "error", "detail": "Failed to get x402 token. Are you subscribed?"}
    except Exception as e:
        return {"status": "error", "detail": f"Token error: {e}"}

    # Call seller with payment header
    try:
        r = requests.post(
            f"{seller_url.rstrip('/')}{endpoint}",
            headers={
                "payment-signature": access_token,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
    except Exception as e:
        return {"status": "error", "detail": f"Request error: {e}"}

    if r.status_code == 402:
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

    # Record spend
    query_str = payload.get("query", payload.get("text", str(payload)))
    budget.record(credits_cost, seller_url, query_str)

    result = {"status": "success", "data": r.json(), "credits_used": credits_cost}
    state.transactions.append(result)
    return result


def buy_from_agent(state: AppState, budget: Budget, agent_info: dict, query: str) -> dict:
    """High-level: resolve plan from discovery data, subscribe if needed, purchase.

    Supports hackathon discovery format with planPricing array and endpointUrl.
    Also supports direct /pricing endpoint format from our own seller.
    """
    url = (agent_info.get("endpointUrl")
           or agent_info.get("url")
           or agent_info.get("agentUrl")
           or agent_info.get("endpoint", ""))
    if not url:
        return {"status": "error", "detail": "No URL found for agent"}

    plan_id = None
    agent_id = None
    credits_cost = 1

    # 1. Try planPricing from discovery API (preferred)
    plan_pricing = agent_info.get("planPricing", [])
    if plan_pricing:
        # Prefer crypto plans, then fiat
        for ptype in ("crypto", "fiat"):
            for pp in plan_pricing:
                if pp.get("paymentType") == ptype and pp.get("planDid"):
                    plan_id = pp["planDid"]
                    credits_cost = 1  # Default; actual cost depends on endpoint
                    break
            if plan_id:
                break
        # Fallback: just take the first plan with a planDid
        if not plan_id:
            for pp in plan_pricing:
                if pp.get("planDid"):
                    plan_id = pp["planDid"]
                    break

    # 2. Try direct /pricing endpoint (for sellers that expose it)
    if not plan_id:
        try:
            from .discovery import get_seller_pricing
            pricing = get_seller_pricing(url)
            if isinstance(pricing, dict):
                for plan_type in ("crypto", "fiat"):
                    plan_data = pricing.get(plan_type, {})
                    if plan_data.get("plan_id"):
                        plan_id = plan_data["plan_id"]
                        agent_id = plan_data.get("agent_id", "")
                        break
                if not plan_id:
                    plan_id = pricing.get("plan_id") or pricing.get("planId", "")
                    agent_id = pricing.get("agent_id") or pricing.get("agentId", "")
        except Exception:
            pass

    # 3. Fallback to agent_info fields
    if not plan_id:
        plan_id = agent_info.get("planId") or agent_info.get("plan_id", "")
    if not agent_id:
        agent_id = agent_info.get("agentId") or agent_info.get("agent_id", "")

    if not plan_id:
        return {"status": "error", "detail": f"No plan found for {agent_info.get('name', url)}"}

    # If we have plan_id but no agent_id, try to get it from the plan
    if not agent_id:
        try:
            agents_on_plan = state.payments.plans.get_agents_associated_to_plan(plan_id)
            if agents_on_plan:
                first = agents_on_plan[0] if isinstance(agents_on_plan, list) else agents_on_plan
                agent_id = first.get("agentId") or first.get("agent_id") or str(first)
        except Exception:
            pass

    if not agent_id:
        return {"status": "error", "detail": f"No agent_id found for plan {plan_id[:30]}..."}

    # Subscribe
    try:
        subscribe(state, plan_id)
    except Exception as e:
        return {"status": "error", "detail": f"Subscribe error: {e}"}

    # Build request — the endpointUrl IS the full endpoint for hackathon agents
    # So we POST directly to it with the query
    payload = {"query": query}

    # For hackathon agents, the endpointUrl is the full path, so endpoint is ""
    # For our own server format, we'd use /api/crypto/ask etc.
    # Detect: if url ends with a specific path (not just domain), post directly to it
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.path and parsed.path != "/":
        # Endpoint URL includes path — post directly
        base_url = url
        endpoint = ""
    else:
        # Root URL — try /api/ask
        base_url = url
        endpoint = "/api/ask"

    return purchase(state, budget, plan_id, agent_id, base_url, endpoint, payload, credits_cost)
