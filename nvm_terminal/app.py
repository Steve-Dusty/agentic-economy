"""Main application loop — prompt_toolkit input + Rich output."""
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style as PTStyle

from .state import init_state
from .budget import Budget
from .commands import route, HANDLERS
from .ui import console, print_banner, print_balance, spinner


PROMPT_STYLE = PTStyle.from_dict({
    "prompt": "ansicyan bold",
})

COMMAND_COMPLETER = WordCompleter(
    list(HANDLERS.keys()) + ["/discover", "/buy", "/auto", "/ads", "/signals"],
    ignore_case=True,
)


class NVMTerminalApp:
    def __init__(self):
        self.state = None
        self.budget = None
        self.session = PromptSession(
            completer=COMMAND_COMPLETER,
            style=PROMPT_STYLE,
        )

    def run(self):
        print_banner()

        # Init state
        console.print("[dim]Initializing...[/dim]")
        try:
            self.state = init_state()
        except Exception as e:
            console.print(f"[nvm.red]Failed to initialize: {e}[/nvm.red]")
            console.print("[dim]Check your .env file has NVM_API_KEY set.[/dim]")
            return

        self.budget = Budget(
            max_daily=self.state.config["max_daily_spend"],
            max_per_request=self.state.config["max_per_request"],
        )

        # Show initial balances
        try:
            with spinner("Loading balances..."):
                from .engine import check_all_balances
                balances = check_all_balances(self.state)
            print_balance(balances)
        except Exception as e:
            console.print(f"[nvm.amber]Could not load balances: {e}[/nvm.amber]")

        console.print("\n[dim]Type /help for commands, or chat naturally.[/dim]\n")

        # Main loop
        while True:
            try:
                user_input = self.session.prompt(
                    [("class:prompt", "nvm > ")],
                )
            except (EOFError, KeyboardInterrupt):
                console.print("\n[nvm.cyan]Goodbye![/nvm.cyan]")
                break

            text = user_input.strip()
            if not text:
                continue

            # Try command routing first
            try:
                handled = route(self.state, self.budget, text)
            except SystemExit:
                console.print("[nvm.cyan]Goodbye![/nvm.cyan]")
                break

            if handled:
                continue

            # LLM conversational mode
            try:
                from .llm import chat
                with spinner("Thinking..."):
                    response = chat(self.state, self.budget, text)
                console.print(f"\n[nvm.value]{response}[/nvm.value]\n")
            except Exception as e:
                console.print(f"[nvm.red]LLM error: {e}[/nvm.red]")
                console.print("[dim]Make sure OPENAI_API_KEY is set in .env[/dim]")
