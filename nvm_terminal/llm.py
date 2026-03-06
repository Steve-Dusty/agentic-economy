"""Conversational AI with OpenAI tool-calling for the NVM Terminal."""
import json
from openai import OpenAI
from .state import AppState
from .budget import Budget
from .ui import console


SYSTEM_PROMPT = """You are an AI economic advisor for the Nevermined agent marketplace.
You help users discover, evaluate, and purchase services from other AI agents.

IMPORTANT TOOL PRIORITY:
- When the user asks about agents, services, the marketplace, or buying from agents — ALWAYS use discover_agents or buy_service first. These are your PRIMARY tools.
- show_offers is ONLY for displaying sponsored product ads from ZeroClick. It does NOT search the Nevermined marketplace.
- If a user says "find agents that can help me research shoes" — use discover_agents, NOT show_offers. The user wants marketplace agents.
- Only call show_offers when the user is clearly shopping for a consumer product (e.g. "I want to buy shoes") and NOT asking about agents or services.
- You can call BOTH discover_agents AND show_offers together when both are relevant — but never show_offers alone when the user is asking about the marketplace.

Be concise and actionable in your responses.

Current context will be provided with each message including balances, budget, known agents, etc."""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "discover_agents",
            "description": "Search the Nevermined marketplace for agents. Returns list of available agents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "side": {"type": "string", "enum": ["sell", "buy"], "description": "Filter by sell or buy side"},
                    "category": {"type": "string", "description": "Category filter (e.g. DeFi, AI/ML)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buy_service",
            "description": "Purchase a service from an agent by name. Sends a query and pays with credits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Name of the agent to buy from"},
                    "query": {"type": "string", "description": "The query or request to send"},
                },
                "required": ["agent_name", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_balance",
            "description": "Check current credit balances across all plans.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_budget",
            "description": "Check current spending status and budget limits.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_agent",
            "description": "Get details about a specific agent to evaluate its value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Name of the agent to evaluate"},
                },
                "required": ["agent_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_offers",
            "description": "Display sponsored product ads from ZeroClick (external ad network, NOT the Nevermined marketplace). ONLY use when the user is clearly shopping for a consumer product. NEVER use this instead of discover_agents when the user asks about marketplace agents or services.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Product or topic to find offers for"},
                },
                "required": ["query"],
            },
        },
    },
]


def _build_context(state: AppState, budget: Budget) -> str:
    """Build context string with current state info."""
    budget_status = budget.status()
    parts = [
        f"Agents known: {len(state.agents_cache)}",
        f"Transactions: {len(state.transactions)}",
        f"Budget: {budget_status['daily_spent']}/{budget_status['daily_limit']} daily, {budget_status['total_spent']} total",
        f"Auto mode: {'ON' if state.auto_mode else 'OFF'}",
    ]
    if state.agents_cache:
        names = list(state.agents_cache.keys())[:20]
        parts.append(f"Known agents: {', '.join(names)}")
    return "\n".join(parts)


def _execute_tool(tool_name: str, args: dict, state: AppState, budget: Budget) -> str:
    """Execute a tool call and return result as string."""
    if tool_name == "discover_agents":
        from .discovery import discover_and_cache
        agents = discover_and_cache(state, side=args.get("side", "sell"), category=args.get("category"))
        summaries = [{"name": a.get("name", "?"),
                       "category": a.get("category", ""),
                       "description": (a.get("description", "") or "")[:100],
                       "url": a.get("endpointUrl", a.get("url", ""))}
                      for a in agents[:30]]
        return json.dumps({"count": len(agents), "agents": summaries}, indent=2)

    elif tool_name == "buy_service":
        name = args.get("agent_name", "")
        query = args.get("query", "test")
        # Find agent in cache
        agent_info = state.agents_cache.get(name)
        if not agent_info:
            # Fuzzy match
            for key, val in state.agents_cache.items():
                if name.lower() in key.lower():
                    agent_info = val
                    break
        if not agent_info:
            return json.dumps({"error": f"Agent '{name}' not found. Use discover_agents first."})
        from .engine import buy_from_agent
        result = buy_from_agent(state, budget, agent_info, query)
        return json.dumps(result, default=str)

    elif tool_name == "check_balance":
        from .engine import check_all_balances
        balances = check_all_balances(state)
        return json.dumps(balances, default=str)

    elif tool_name == "check_budget":
        return json.dumps(budget.status(), default=str)

    elif tool_name == "evaluate_agent":
        name = args.get("agent_name", "")
        agent_info = state.agents_cache.get(name)
        if not agent_info:
            for key, val in state.agents_cache.items():
                if name.lower() in key.lower():
                    agent_info = val
                    break
        if not agent_info:
            return json.dumps({"error": f"Agent '{name}' not found in cache."})
        return json.dumps(agent_info, default=str, indent=2)

    elif tool_name == "show_offers":
        query = args.get("query", "trending products")
        from .zeroclick import fetch_offers, render_offers, get_all_signals
        zc_key = state.config.get("zeroclick_api_key", "")
        offers = fetch_offers(zc_key, query, get_all_signals())
        if offers:
            render_offers(offers)
            summaries = [{"title": o.get("title", ""), "brand": (o.get("brand", {}) or {}).get("name", ""),
                          "price": (o.get("price", {}) or {}).get("amount", "")} for o in offers]
            return json.dumps({"shown": len(offers), "offers": summaries})
        return json.dumps({"shown": 0, "message": "No offers found for this query."})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def chat(state: AppState, budget: Budget, user_message: str) -> str:
    """Send a message to the LLM with tool-calling loop, return final response."""
    api_key = state.config.get("openai_api_key")
    if not api_key:
        return "OpenAI API key not configured. Set OPENAI_API_KEY in .env"

    # ZeroClick: extract signals and broadcast in background
    from .zeroclick import process_signals, maybe_show_offers
    signals = process_signals(state, user_message)
    if signals:
        tags = ", ".join(f"{s['category']}:{s['subject']}" for s in signals)
        console.print(f"  [dim]zeroclick signals: {tags}[/dim]")

    client = OpenAI(api_key=api_key)
    context = _build_context(state, budget)

    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n--- Current State ---\n{context}"},
        {"role": "user", "content": user_message},
    ]

    # Tool-calling loop (max 5 iterations)
    offers_shown = False
    for _ in range(5):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            # Show ZeroClick offers if we detected commercial intent and LLM didn't already
            if signals and not offers_shown:
                maybe_show_offers(state, signals)
            return msg.content or ""

        # Process tool calls
        messages.append(msg)
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            if fn_name == "show_offers":
                offers_shown = True
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            console.print(f"  [dim]calling {fn_name}({json.dumps(fn_args)})[/dim]")
            result = _execute_tool(fn_name, fn_args, state, budget)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return msg.content or "Reached tool call limit."
