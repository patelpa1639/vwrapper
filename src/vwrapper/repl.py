from __future__ import annotations

import json
import readline  # noqa: F401 — enables arrow keys & history in input()
import sys
import time
from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from vwrapper import __version__
from vwrapper.config import AppConfig, get_config
from vwrapper.models.actions import ActionResult

if TYPE_CHECKING:
    from vwrapper.providers.vmware import VMwareProvider

console = Console()

# ── Slash commands ──────────────────────────────────────────────

SLASH_COMMANDS = {
    "/help": "Show available commands",
    "/status": "Check connection to vCenter/ESXi",
    "/vms": "Quick list of all VMs",
    "/clear": "Clear the screen",
    "/history": "Show command history",
    "/exit": "Exit vWrapper",
    "/quit": "Exit vWrapper",
}


# ── Banner ──────────────────────────────────────────────────────

def _print_banner(config: AppConfig, host_info: str = "") -> None:
    banner_lines = [
        f"[bold cyan]vWrapper[/bold cyan] [dim]v{__version__}[/dim]",
        "",
        f"[dim]Connected to[/dim] [bold]{config.vcenter.host}[/bold]" + (f" [dim]({host_info})[/dim]" if host_info else ""),
        f"[dim]LLM:[/dim] [bold]{config.llm.model}[/bold]",
        "",
        "[dim]Type natural language commands to manage your infrastructure.[/dim]",
        "[dim]Type /help for commands, /exit to quit.[/dim]",
    ]
    console.print()
    console.print(
        Panel(
            "\n".join(banner_lines),
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


# ── Spinner helper ──────────────────────────────────────────────

def _with_spinner(message: str, func, *args, **kwargs):
    """Run a function while showing a spinner."""
    spinner = Spinner("dots", text=Text(f" {message}", style="bold"))
    with Live(spinner, console=console, refresh_per_second=12, transient=True):
        return func(*args, **kwargs)


# ── Command handlers ────────────────────────────────────────────

def _handle_help() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Command", style="cyan bold")
    table.add_column("Description", style="dim")
    for cmd, desc in SLASH_COMMANDS.items():
        table.add_row(cmd, desc)
    console.print()
    console.print(table)
    console.print()
    console.print("  [dim]Or just type in plain English:[/dim]")
    console.print('  [dim]  "list all my VMs"[/dim]')
    console.print('  [dim]  "create a VM called web-02 with 4 CPUs"[/dim]')
    console.print('  [dim]  "is my cluster running hot?"[/dim]')
    console.print()


def _handle_status(provider: VMwareProvider) -> None:
    try:
        count = _with_spinner("Checking connection...", provider.vm_count)
        console.print(f"  [green]Connected[/green] — {count} VM(s) found\n")
    except Exception as e:
        console.print(f"  [red]Connection error:[/red] {e}\n")


def _handle_vms(provider: VMwareProvider) -> None:
    from vwrapper.output import print_vm_table

    try:
        vms = _with_spinner("Fetching VMs...", provider.list_vms)
        console.print()
        print_vm_table(vms)
        console.print()
    except Exception as e:
        console.print(f"  [red]Error:[/red] {e}\n")


def _handle_history(history: list[str]) -> None:
    if not history:
        console.print("  [dim]No history yet.[/dim]\n")
        return
    console.print()
    for i, cmd in enumerate(history, 1):
        console.print(f"  [dim]{i}.[/dim] {cmd}")
    console.print()


# ── Main execute logic ──────────────────────────────────────────

def _execute_query(
    query: str,
    provider: VMwareProvider,
    config: AppConfig,
    conversation: list[dict],
) -> None:
    from vwrapper.agent.intent import parse, summarize
    from vwrapper.guardrails.rules import validate
    from vwrapper.output import (
        print_action_plan,
        print_blocked,
        print_insight,
        print_result,
        print_vm_table,
    )

    # Parse intent with spinner
    action = _with_spinner("Thinking...", parse, query, config)

    # Guardrails
    current_vm_count = None
    if action.name == "create_vm":
        current_vm_count = provider.vm_count()

    guard = validate(action, config, current_vm_count)

    if not guard.allowed:
        console.print()
        print_blocked(guard.reason)
        console.print()
        return

    # Confirmation for dangerous actions
    if guard.needs_confirmation:
        console.print()
        print_action_plan(action)
        answer = console.input(f"  [yellow]{guard.confirmation_message}[/yellow] [dim](y/N)[/dim] ").strip().lower()
        if answer not in ("y", "yes"):
            console.print("  [dim]Cancelled.[/dim]\n")
            return

    # Execute
    result: ActionResult | None = None

    if action.name == "list_vms":
        vms = _with_spinner("Fetching VMs...", provider.list_vms)
        console.print()
        print_vm_table(vms)
        console.print()

    elif action.name == "create_vm":
        def _create():
            return provider.create_vm(
                name=action.params.get("name", "new-vm"),
                cpu=action.params.get("cpu", 2),
                memory_mb=action.params.get("memory_mb", 4096),
                disk_gb=action.params.get("disk_gb", 40),
            )

        result = _with_spinner("Creating VM...", _create)
        console.print()
        print_result(result)
        console.print()

    elif action.name == "insight":
        vms = _with_spinner("Gathering data...", provider.list_vms)
        capacity = _with_spinner("Analyzing capacity...", provider.get_capacity)
        data = {
            "capacity": capacity,
            "vms": [vm.model_dump() for vm in vms],
        }
        question = action.params.get("question", action.raw_query)

        # Add conversation context for richer answers
        context_prompt = question
        if conversation:
            recent = conversation[-6:]  # last 3 exchanges
            history_str = "\n".join(f"- {m['role']}: {m['content']}" for m in recent)
            context_prompt = f"Conversation so far:\n{history_str}\n\nCurrent question: {question}"

        summary = _with_spinner("Thinking...", summarize, data, context_prompt, config)
        console.print()
        print_insight(summary)
        console.print()

        # Track conversation
        conversation.append({"role": "user", "content": query})
        conversation.append({"role": "assistant", "content": summary})
        return

    else:
        console.print(f"  [red]Unknown action: {action.name}[/red]\n")
        return

    # Track conversation
    conversation.append({"role": "user", "content": query})
    if result:
        conversation.append({"role": "assistant", "content": f"Executed {result.action}: {'success' if result.success else 'failed'}"})


# ── REPL entry point ────────────────────────────────────────────

def start_repl(*, demo: bool = False) -> None:
    """Launch the interactive vWrapper REPL.

    Args:
        demo: If True, use a fake provider with simulated data instead of
              connecting to a real vCenter/ESXi host.
    """
    config = get_config()

    if demo:
        from vwrapper.providers.fake import FakeProvider

        provider = FakeProvider()
        _with_spinner("Connecting to vCenter...", provider.connect)
        host_info = "demo mode — fake data"
    else:
        from vwrapper.providers.vmware import VMwareProvider

        provider = VMwareProvider(config.vcenter)

        try:
            _with_spinner("Connecting to vCenter...", provider.connect)
        except Exception as e:
            console.print(f"\n  [red]Failed to connect:[/red] {e}")
            console.print(f"  [dim]Check your .env config and try again.[/dim]\n")
            sys.exit(1)

        try:
            about = provider.content.about
            host_info = f"{about.fullName}"
        except Exception:
            host_info = ""

    _print_banner(config, host_info)

    # REPL loop
    history: list[str] = []
    conversation: list[dict] = []

    try:
        while True:
            try:
                query = console.input("[bold cyan]>[/bold cyan] ").strip()
            except EOFError:
                break

            if not query:
                continue

            # Slash commands
            lower = query.lower()
            if lower in ("/exit", "/quit"):
                console.print("  [dim]Goodbye![/dim]\n")
                break
            elif lower == "/help":
                _handle_help()
                continue
            elif lower == "/status":
                _handle_status(provider)
                continue
            elif lower == "/vms":
                _handle_vms(provider)
                continue
            elif lower == "/clear":
                console.clear()
                _print_banner(config, host_info)
                continue
            elif lower == "/history":
                _handle_history(history)
                continue
            elif lower.startswith("/"):
                console.print(f"  [red]Unknown command: {query}[/red] — type /help for commands.\n")
                continue

            history.append(query)

            try:
                _execute_query(query, provider, config, conversation)
            except KeyboardInterrupt:
                console.print("\n  [dim]Interrupted.[/dim]\n")
            except Exception as e:
                console.print(f"  [red]Error:[/red] {e}\n")

    except KeyboardInterrupt:
        console.print("\n  [dim]Goodbye![/dim]\n")
    finally:
        provider.disconnect()
