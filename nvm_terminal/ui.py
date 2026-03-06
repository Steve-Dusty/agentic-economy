"""Rich theme, panels, tables, and status bar helpers."""
from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.text import Text
from rich import box

NVM_THEME = Theme({
    "nvm.cyan": "bold cyan",
    "nvm.amber": "bold yellow",
    "nvm.green": "bold green",
    "nvm.red": "bold red",
    "nvm.dim": "dim",
    "nvm.header": "bold bright_cyan",
    "nvm.value": "bright_white",
    "nvm.label": "cyan",
})

console = Console(theme=NVM_THEME)

BANNER = r"""
[bold cyan]
  _  ___   ____  __   _____                   _             _
 | \| \ \ / /  \/  | |_   _|__ _ _ _ __  _ __(_)_ _  __ _ | |
 | .` |\ V /| |\/| |   | |/ -_) '_| '  \| '_ \ | ' \/ _` || |
 |_|\_| \_/ |_|  |_|   |_|\___|_| |_|_|_| .__/_|_||_\__,_||_|
                                          |_|
[/bold cyan]
[dim]  Nevermined Agent Economy CLI  v0.1.0[/dim]
"""


def print_banner():
    console.print(BANNER)


def print_agent_table(agents: list[dict]):
    """Print a Rich table of discovered agents."""
    if not agents:
        console.print("[nvm.dim]No agents found.[/nvm.dim]")
        return

    table = Table(
        title="Marketplace Agents",
        box=box.ROUNDED,
        title_style="nvm.header",
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="nvm.cyan", max_width=28)
    table.add_column("Category", style="nvm.amber", width=14)
    table.add_column("Pricing", style="bright_white", width=16)
    table.add_column("Description", style="dim", max_width=44)
    table.add_column("URL", style="dim", max_width=40)

    for i, a in enumerate(agents, 1):
        # Extract pricing summary
        pricing = a.get("pricing", {})
        price_str = pricing.get("perRequest", "") if isinstance(pricing, dict) else ""
        table.add_row(
            str(i),
            a.get("name", "?"),
            a.get("category", ""),
            price_str[:16],
            (a.get("description", "") or "").split("\n")[0][:44],
            a.get("endpointUrl", a.get("url", a.get("agentUrl", ""))) or "",
        )
    console.print(table)


def print_balance(balances: list[dict]):
    """Print credit balances as a panel."""
    lines = []
    for b in balances:
        sub = "[nvm.green]yes[/nvm.green]" if b.get("is_subscriber") else "[nvm.red]no[/nvm.red]"
        lines.append(
            f"  [nvm.label]{b.get('plan_name', b.get('plan_id', '?')[:20])}:[/nvm.label] "
            f"[nvm.value]{b.get('balance', '?')}[/nvm.value] credits  (subscribed: {sub})"
        )
    content = "\n".join(lines) if lines else "[nvm.dim]No balances to show.[/nvm.dim]"
    console.print(Panel(content, title="[nvm.header]Credit Balances[/nvm.header]", border_style="cyan", box=box.ROUNDED))


def print_budget(budget_data: dict):
    """Print budget status panel."""
    lines = [
        f"  [nvm.label]Daily limit:[/nvm.label]      [nvm.value]{budget_data.get('daily_limit', '?')}[/nvm.value]",
        f"  [nvm.label]Daily spent:[/nvm.label]      [nvm.value]{budget_data.get('daily_spent', 0)}[/nvm.value]",
        f"  [nvm.label]Daily remaining:[/nvm.label]  [nvm.value]{budget_data.get('daily_remaining', '?')}[/nvm.value]",
        f"  [nvm.label]Per-request limit:[/nvm.label] [nvm.value]{budget_data.get('per_request_limit', '?')}[/nvm.value]",
        f"  [nvm.label]Total spent:[/nvm.label]      [nvm.value]{budget_data.get('total_spent', 0)}[/nvm.value]",
        f"  [nvm.label]Purchases:[/nvm.label]        [nvm.value]{budget_data.get('purchases', 0)}[/nvm.value]",
    ]
    recent = budget_data.get("recent", [])
    if recent:
        lines.append("")
        lines.append("  [nvm.label]Recent purchases:[/nvm.label]")
        for p in recent:
            lines.append(f"    [dim]{p.get('time', '?')}[/dim] {p.get('credits', '?')} cr -> {p.get('seller', '?')[:30]}")
    console.print(Panel("\n".join(lines), title="[nvm.header]Budget Status[/nvm.header]", border_style="cyan", box=box.ROUNDED))


def print_transaction(tx: dict):
    """Print a styled transaction result."""
    status = tx.get("status", "unknown")
    if status == "success":
        style = "nvm.green"
        icon = "OK"
    elif status == "budget_exceeded":
        style = "nvm.amber"
        icon = "BUDGET"
    else:
        style = "nvm.red"
        icon = "ERR"

    lines = [f"  [{style}][{icon}][/{style}] Status: [{style}]{status}[/{style}]"]
    if "credits_used" in tx:
        lines.append(f"  Credits used: {tx['credits_used']}")
    if "data" in tx:
        data = tx["data"]
        answer = data.get("answer") or data.get("summary") or str(data)
        lines.append(f"  [nvm.value]{answer}[/nvm.value]")
    if "detail" in tx:
        lines.append(f"  [dim]{tx['detail'][:300]}[/dim]")

    console.print(Panel("\n".join(lines), title="[nvm.header]Transaction Result[/nvm.header]", border_style="cyan", box=box.ROUNDED))


def print_status(state):
    """Print full economic overview."""
    from .budget import Budget

    lines = []
    lines.append(f"  [nvm.label]Auto mode:[/nvm.label]  [nvm.value]{'ON' if state.auto_mode else 'OFF'}[/nvm.value]")
    lines.append(f"  [nvm.label]Agents cached:[/nvm.label] [nvm.value]{len(state.agents_cache)}[/nvm.value]")
    lines.append(f"  [nvm.label]Transactions:[/nvm.label]  [nvm.value]{len(state.transactions)}[/nvm.value]")
    console.print(Panel("\n".join(lines), title="[nvm.header]NVM Status[/nvm.header]", border_style="cyan", box=box.ROUNDED))


def print_help(commands: dict):
    """Print help table."""
    table = Table(title="Commands", box=box.ROUNDED, title_style="nvm.header", border_style="cyan")
    table.add_column("Command", style="nvm.cyan", width=24)
    table.add_column("Description", style="dim")
    for cmd, desc in commands.items():
        table.add_row(cmd, desc)
    table.add_row("[dim]<any text>[/dim]", "Chat with AI advisor")
    console.print(table)


@contextmanager
def spinner(msg: str = "Working..."):
    """Rich Status context manager for loading states."""
    with console.status(f"[nvm.cyan]{msg}[/nvm.cyan]", spinner="dots"):
        yield
