"""Discovery API client — find other agents on the marketplace."""
import requests
from .state import AppState


DISCOVERY_URL = "https://nevermined.ai/hackathon/register/api/discover"


def discover_agents(api_key: str, side: str = "sell", category: str | None = None) -> list[dict]:
    """Call the hackathon Discovery API to find agents."""
    params = {}
    if side:
        params["side"] = side
    if category:
        params["category"] = category

    r = requests.get(
        DISCOVERY_URL,
        headers={"x-nvm-api-key": api_key},
        params=params,
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    # API may return list directly or wrapped in a key
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Hackathon API returns {"meta": ..., "sellers": [...]} or {"buyers": [...]}
        return (data.get("sellers")
                or data.get("buyers")
                or data.get("agents")
                or data.get("results")
                or data.get("data")
                or [])
    return []


def get_agent_details(state: AppState, agent_id: str) -> dict:
    """Get agent details from the Payments SDK."""
    try:
        result = state.payments.agents.get_agent(agent_id)
        if hasattr(result, "__dict__"):
            return vars(result)
        return result if isinstance(result, dict) else {"raw": str(result)}
    except Exception as e:
        return {"error": str(e)}


def get_seller_pricing(seller_url: str) -> dict:
    """GET /pricing from a seller endpoint."""
    r = requests.get(f"{seller_url.rstrip('/')}/pricing", timeout=15)
    r.raise_for_status()
    return r.json()


def discover_and_cache(state: AppState, side: str = "sell", category: str | None = None) -> list[dict]:
    """Discover agents and cache them in state."""
    agents = discover_agents(state.config["nvm_api_key"], side=side, category=category)
    for a in agents:
        key = a.get("name") or a.get("agentId") or a.get("id", str(id(a)))
        state.agents_cache[key] = a
    return agents
