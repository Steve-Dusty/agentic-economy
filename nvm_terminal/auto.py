"""Autonomous buying loop."""
import time
from .state import AppState
from .budget import Budget
from .discovery import discover_and_cache
from .engine import buy_from_agent, check_all_balances
from .ui import console, print_agent_table, print_transaction


def run_auto(state: AppState, budget: Budget, strategy: str = "balanced", delay: float = 5.0):
    """Run autonomous discovery and purchasing loop.

    Strategies:
      - balanced: spread across agents, 1 purchase per agent per round
      - focused: deep on highest-value agents (by category relevance)
      - aggressive: max purchases, minimal delay
    """
    state.auto_mode = True
    state.auto_stop = False

    if strategy == "aggressive":
        delay = 1.0

    console.print(f"\n[nvm.cyan]Starting autonomous mode[/nvm.cyan] (strategy={strategy}, delay={delay}s)")
    console.print("[dim]Press Ctrl+C or /stop to halt[/dim]\n")

    round_num = 0
    purchased_agents = set()

    try:
        while not state.auto_stop:
            round_num += 1
            console.print(f"[nvm.header]--- Auto Round {round_num} ---[/nvm.header]")

            # 1. Discover sellers
            console.print("[dim]Discovering sellers...[/dim]")
            try:
                agents = discover_and_cache(state, side="sell")
            except Exception as e:
                console.print(f"[nvm.red]Discovery error: {e}[/nvm.red]")
                time.sleep(delay)
                continue

            if not agents:
                console.print("[nvm.amber]No sellers found. Retrying...[/nvm.amber]")
                time.sleep(delay)
                continue

            console.print(f"[dim]Found {len(agents)} sellers[/dim]")

            # 2. Filter by budget
            budget_status = budget.status()
            daily_remaining = budget_status["daily_remaining"]
            if isinstance(daily_remaining, int) and daily_remaining <= 0:
                console.print("[nvm.amber]Daily budget exhausted. Stopping auto mode.[/nvm.amber]")
                break

            # 3. Select agents based on strategy
            candidates = agents
            if strategy == "balanced":
                # Skip agents we've already purchased from this session
                candidates = [a for a in agents if a.get("name", "") not in purchased_agents]
                if not candidates:
                    console.print("[nvm.green]Purchased from all known agents. Resetting.[/nvm.green]")
                    purchased_agents.clear()
                    candidates = agents

            elif strategy == "focused":
                # Prefer agents with URLs (actually reachable)
                candidates = sorted(agents, key=lambda a: bool(a.get("url") or a.get("agentUrl")), reverse=True)
                candidates = candidates[:5]

            # 4. Purchase from each candidate
            for agent in candidates:
                if state.auto_stop:
                    break

                name = agent.get("name", "unknown")
                url = agent.get("url") or agent.get("agentUrl") or ""
                if not url:
                    continue

                console.print(f"\n[nvm.cyan]Trying: {name}[/nvm.cyan] ({url[:50]})")

                try:
                    result = buy_from_agent(state, budget, agent, "What services do you provide?")
                    print_transaction(result)
                    purchased_agents.add(name)

                    if result.get("status") == "budget_exceeded":
                        console.print("[nvm.amber]Budget limit hit. Stopping.[/nvm.amber]")
                        state.auto_stop = True
                        break
                except Exception as e:
                    console.print(f"[nvm.red]Error with {name}: {e}[/nvm.red]")

                time.sleep(delay)

            # Show round summary
            console.print(f"\n[dim]Round {round_num} complete. Purchased from {len(purchased_agents)} agents total.[/dim]")

            if strategy != "aggressive":
                time.sleep(delay * 2)

    except KeyboardInterrupt:
        console.print("\n[nvm.amber]Auto mode interrupted.[/nvm.amber]")

    state.auto_mode = False
    console.print("[nvm.green]Auto mode stopped.[/nvm.green]")

    # Final report
    console.print(f"\n[nvm.header]Auto Mode Summary[/nvm.header]")
    console.print(f"  Rounds: {round_num}")
    console.print(f"  Agents purchased: {len(purchased_agents)}")
    console.print(f"  Total transactions: {len(state.transactions)}")
    bs = budget.status()
    console.print(f"  Credits spent: {bs['daily_spent']} today, {bs['total_spent']} total")
