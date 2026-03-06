"""Slash command router and handlers."""
import threading
from .state import AppState
from .budget import Budget
from .ui import (
    console, print_agent_table, print_balance, print_budget,
    print_transaction, print_status, print_help, spinner,
)

COMMANDS = {
    "/discover [category]": "List marketplace agents",
    "/buy <name> [query]": "Buy from agent by name",
    "/balance": "Show all plan balances",
    "/budget": "Show spending history/limits",
    "/agents": "List cached/known agents",
    "/auto [strategy]": "Start autonomous mode (balanced|focused|aggressive)",
    "/stop": "Stop auto mode",
    "/sell": "Show our seller status",
    "/ads <query>": "Fetch ZeroClick sponsored offers",
    "/signals": "Show collected ZeroClick preference signals",
    "/status": "Full economic overview",
    "/help": "Show all commands",
    "/quit": "Exit",
}


def cmd_discover(state: AppState, budget: Budget, args: str):
    category = args.strip() or None
    with spinner("Discovering agents..."):
        from .discovery import discover_and_cache
        agents = discover_and_cache(state, side="sell", category=category)
    print_agent_table(agents)
    console.print(f"[dim]{len(agents)} agents found. Cached for /buy and /agents.[/dim]")


def cmd_buy(state: AppState, budget: Budget, args: str):
    parts = args.strip().split(maxsplit=1)
    if not parts:
        console.print("[nvm.red]Usage: /buy <agent_name> [query][/nvm.red]")
        return

    name = parts[0]
    query = parts[1] if len(parts) > 1 else "What services do you provide?"

    # Find agent in cache
    agent_info = state.agents_cache.get(name)
    if not agent_info:
        for key, val in state.agents_cache.items():
            if name.lower() in key.lower():
                agent_info = val
                name = key
                break
    if not agent_info:
        console.print(f"[nvm.red]Agent '{name}' not found. Run /discover first.[/nvm.red]")
        return

    console.print(f"[nvm.cyan]Buying from {name}...[/nvm.cyan]")
    with spinner(f"Purchasing from {name}..."):
        from .engine import buy_from_agent
        result = buy_from_agent(state, budget, agent_info, query)
    print_transaction(result)


def cmd_balance(state: AppState, budget: Budget, args: str):
    with spinner("Checking balances..."):
        from .engine import check_all_balances
        balances = check_all_balances(state)
    print_balance(balances)


def cmd_budget(state: AppState, budget: Budget, args: str):
    print_budget(budget.status())


def cmd_agents(state: AppState, budget: Budget, args: str):
    if not state.agents_cache:
        console.print("[nvm.dim]No agents cached. Run /discover first.[/nvm.dim]")
        return
    agents = list(state.agents_cache.values())
    print_agent_table(agents)


def cmd_auto(state: AppState, budget: Budget, args: str):
    strategy = args.strip() or "balanced"
    if strategy not in ("balanced", "focused", "aggressive"):
        console.print("[nvm.red]Strategy must be: balanced, focused, or aggressive[/nvm.red]")
        return

    if state.auto_mode:
        console.print("[nvm.amber]Auto mode already running. Use /stop first.[/nvm.amber]")
        return

    from .auto import run_auto
    # Run in a thread so the main loop can still accept /stop
    t = threading.Thread(target=run_auto, args=(state, budget, strategy), daemon=True)
    t.start()


def cmd_stop(state: AppState, budget: Budget, args: str):
    if not state.auto_mode:
        console.print("[nvm.dim]Auto mode is not running.[/nvm.dim]")
        return
    state.auto_stop = True
    console.print("[nvm.amber]Stopping auto mode...[/nvm.amber]")


def cmd_ads(state: AppState, budget: Budget, args: str):
    query = args.strip() or "trending deals"
    zc_key = state.config.get("zeroclick_api_key", "")
    if not zc_key:
        console.print("[nvm.red]ZEROCLICK_API_KEY not set in .env[/nvm.red]")
        return
    console.print(f"[dim]Fetching offers for: {query}[/dim]")
    with spinner("Loading offers..."):
        from .zeroclick import fetch_offers, render_offers, get_all_signals
        offers = fetch_offers(zc_key, query, get_all_signals())
    if offers:
        render_offers(offers)
    else:
        console.print("[nvm.dim]No offers found.[/nvm.dim]")


def cmd_signals(state: AppState, budget: Budget, args: str):
    from .zeroclick import get_all_signals
    signals = get_all_signals()
    if not signals:
        console.print("[nvm.dim]No ZeroClick signals collected yet. Chat naturally to generate signals.[/nvm.dim]")
        return
    console.print(f"[nvm.header]{len(signals)} signals collected this session:[/nvm.header]")
    for s in signals:
        cat = s.get("category", "?")
        subj = s.get("subject", "?")
        conf = s.get("confidence", "?")
        sent = s.get("sentiment", "?")
        console.print(f"  [nvm.cyan][{cat}][/nvm.cyan] {subj} [dim](conf={conf}, {sent})[/dim]")


def cmd_sell(state: AppState, budget: Budget, args: str):
    console.print("[nvm.header]Seller Info[/nvm.header]")
    console.print(f"  Agent ID (Free):   {state.config.get('agent_id', 'N/A')[:50]}...")
    console.print(f"  Agent ID (Crypto): {state.config.get('agent_id_crypto', 'N/A')[:50]}...")
    console.print(f"  Plan (Free):       {state.config.get('plan_id', 'N/A')[:50]}...")
    console.print(f"  Plan (Crypto):     {state.config.get('plan_id_crypto', 'N/A')[:50]}...")
    console.print(f"  Plan (Fiat):       {state.config.get('plan_id_fiat', 'N/A')[:50]}...")
    console.print(f"  Wallet:            {state.config.get('wallet', 'N/A')}")
    console.print(f"\n[dim]Seller server runs separately: python server.py[/dim]")


def cmd_status(state: AppState, budget: Budget, args: str):
    print_status(state)
    print_budget(budget.status())
    # Also show balances
    try:
        from .engine import check_all_balances
        balances = check_all_balances(state)
        print_balance(balances)
    except Exception as e:
        console.print(f"[nvm.red]Balance check failed: {e}[/nvm.red]")


def cmd_help(state: AppState, budget: Budget, args: str):
    print_help(COMMANDS)


def cmd_quit(state: AppState, budget: Budget, args: str):
    raise SystemExit(0)


# Router
HANDLERS = {
    "/discover": cmd_discover,
    "/buy": cmd_buy,
    "/balance": cmd_balance,
    "/budget": cmd_budget,
    "/agents": cmd_agents,
    "/auto": cmd_auto,
    "/stop": cmd_stop,
    "/sell": cmd_sell,
    "/ads": cmd_ads,
    "/signals": cmd_signals,
    "/status": cmd_status,
    "/help": cmd_help,
    "/quit": cmd_quit,
    "/exit": cmd_quit,
    "/q": cmd_quit,
}


def route(state: AppState, budget: Budget, input_text: str) -> bool:
    """Parse input, dispatch to handler or return False for LLM chat.

    Returns True if handled as a command, False if should go to LLM.
    """
    text = input_text.strip()
    if not text:
        return True  # ignore empty

    if not text.startswith("/"):
        return False  # not a command — send to LLM

    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    handler = HANDLERS.get(cmd)
    if handler:
        try:
            handler(state, budget, args)
        except SystemExit:
            raise
        except Exception as e:
            console.print(f"[nvm.red]Command error: {e}[/nvm.red]")
        return True

    console.print(f"[nvm.red]Unknown command: {cmd}. Try /help[/nvm.red]")
    return True
