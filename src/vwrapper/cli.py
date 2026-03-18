from __future__ import annotations

import typer
from rich.console import Console

from vwrapper import __version__
from vwrapper.config import get_config
from vwrapper.models.actions import ActionResult

app = typer.Typer(
    name="vwrapper",
    help="AI-powered VMware infrastructure control.",
    add_completion=False,
    invoke_without_command=True,
)
console = Console()


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    query: str = typer.Argument(None, help="Natural language command"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show extra detail"),
) -> None:
    """Execute a VMware action from natural language."""
    # If a subcommand was invoked, skip
    if ctx.invoked_subcommand is not None:
        return

    # Typer quirk: subcommand names get captured as query arg
    _subcommands = {"demo", "sandbox", "status", "version"}
    if query in _subcommands:
        ctx.invoke(globals()[query])
        return

    # No query → launch interactive REPL
    if query is None:
        from vwrapper.repl import start_repl
        start_repl()
        return

    _execute(query, dry_run=dry_run, yes=yes, verbose=verbose)


def _execute(
    query: str,
    *,
    dry_run: bool = False,
    yes: bool = False,
    verbose: bool = False,
) -> None:
    from vwrapper.agent.intent import parse, summarize
    from vwrapper.guardrails.rules import validate
    from vwrapper.output import (
        confirm,
        print_action_plan,
        print_blocked,
        print_insight,
        print_result,
        print_step,
        print_vm_table,
    )
    from vwrapper.providers.vmware import VMwareProvider

    config = get_config()
    if dry_run:
        config.dry_run = True

    # Step 1: Parse intent
    console.print()
    print_step("\U0001f9e0", "[bold]Parsing intent...[/bold]")
    action = parse(query, config)

    if verbose:
        print_action_plan(action)

    # Step 2: Connect to vCenter
    print_step("\U0001f50c", "[bold]Connecting to vCenter...[/bold]")
    provider = VMwareProvider(config.vcenter)
    try:
        provider.connect()
    except Exception as e:
        console.print(f"  [red]Failed to connect: {e}[/red]")
        raise typer.Exit(1)

    try:
        current_vm_count = provider.vm_count() if action.name == "create_vm" else None

        # Step 3: Guardrails
        print_step("\U0001f512", "[bold]Validating...[/bold]")
        guard = validate(action, config, current_vm_count)

        if not guard.allowed:
            print_blocked(guard.reason)
            raise typer.Exit(1)

        # Step 4: Confirmation
        if guard.needs_confirmation and not yes:
            print_action_plan(action)
            if not confirm(guard.confirmation_message):
                console.print("  [dim]Cancelled.[/dim]")
                raise typer.Exit(0)

        # Step 5: Execute
        print_step("\u2699\ufe0f", "[bold]Executing...[/bold]")
        result: ActionResult | None = None

        if action.name == "list_vms":
            vms = provider.list_vms()
            console.print()
            print_vm_table(vms)
            return

        elif action.name == "create_vm":
            result = provider.create_vm(
                name=action.params.get("name", "new-vm"),
                cpu=action.params.get("cpu", 2),
                memory_mb=action.params.get("memory_mb", 4096),
                disk_gb=action.params.get("disk_gb", 40),
            )

        elif action.name == "insight":
            vms = provider.list_vms()
            capacity = provider.get_capacity()
            data = {
                "capacity": capacity,
                "vms": [vm.model_dump() for vm in vms],
            }
            question = action.params.get("question", action.raw_query)
            summary = summarize(data, question, config)
            console.print()
            print_insight(summary)
            return

        else:
            console.print(f"  [red]Unknown action: {action.name}[/red]")
            raise typer.Exit(1)

        # Step 6: Display result
        if result:
            console.print()
            print_result(result)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"\n  [red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        provider.disconnect()


@app.command()
def sandbox() -> None:
    """Launch interactive REPL with fake data — no vCenter required."""
    from vwrapper.repl import start_repl
    start_repl(demo=True)


@app.command()
def demo() -> None:
    """Run a non-interactive demo showcasing all features."""
    import time

    from vwrapper.models.actions import Action, ActionResult, VMInfo
    from vwrapper.output import (
        print_action_plan,
        print_blocked,
        print_insight,
        print_result,
        print_step,
        print_vm_table,
    )

    fake_vms = [
        VMInfo(name="web-01", power_state="poweredOn", cpu=4, memory_mb=8192, guest_os="Ubuntu 22.04 (64-bit)", ip_address="10.0.1.10"),
        VMInfo(name="db-01", power_state="poweredOn", cpu=8, memory_mb=16384, guest_os="CentOS 9 (64-bit)", ip_address="10.0.1.20"),
        VMInfo(name="api-gateway", power_state="poweredOn", cpu=2, memory_mb=4096, guest_os="Alpine Linux (64-bit)", ip_address="10.0.1.30"),
        VMInfo(name="ml-worker-01", power_state="poweredOff", cpu=16, memory_mb=65536, guest_os="Ubuntu 22.04 (64-bit)", ip_address=None),
        VMInfo(name="dev-box", power_state="poweredOff", cpu=2, memory_mb=4096, guest_os="Other Linux (64-bit)", ip_address=None),
    ]

    # --- Demo 1: List VMs ---
    console.print("\n[bold dim]━━━ Demo 1: List VMs ━━━[/bold dim]\n")
    console.print('  [dim]$ vwrapper "show me all my VMs"[/dim]\n')
    time.sleep(0.3)
    print_step("\U0001f9e0", "[bold]Parsing intent...[/bold]")
    time.sleep(0.5)
    print_step("\U0001f50c", "[bold]Connecting to vCenter...[/bold]")
    time.sleep(0.3)
    print_step("\U0001f512", "[bold]Validating...[/bold]")
    time.sleep(0.2)
    print_step("\u2699\ufe0f", "[bold]Executing...[/bold]")
    time.sleep(0.3)
    console.print()
    print_vm_table(fake_vms)

    # --- Demo 2: Create VM ---
    console.print("\n[bold dim]━━━ Demo 2: Create VM ━━━[/bold dim]\n")
    console.print('  [dim]$ vwrapper "spin up a 4-cpu dev box called test-api" --yes[/dim]\n')
    time.sleep(0.3)
    print_step("\U0001f9e0", "[bold]Parsing intent...[/bold]")
    time.sleep(0.5)
    action = Action(name="create_vm", params={"name": "test-api", "cpu": 4, "memory_mb": 8192, "disk_gb": 40}, raw_query="spin up a 4-cpu dev box called test-api")
    print_action_plan(action)
    time.sleep(0.3)
    print_step("\U0001f50c", "[bold]Connecting to vCenter...[/bold]")
    time.sleep(0.3)
    print_step("\U0001f512", "[bold]Validating...[/bold]")
    time.sleep(0.2)
    print_step("\u2699\ufe0f", "[bold]Executing...[/bold]")
    time.sleep(0.5)
    console.print()
    print_result(ActionResult(success=True, action="create_vm", data={"name": "test-api", "cpu": 4, "memory_mb": 8192, "disk_gb": 40}))

    # --- Demo 3: Insight ---
    console.print("\n[bold dim]━━━ Demo 3: Infrastructure Insight ━━━[/bold dim]\n")
    console.print('  [dim]$ vwrapper "is my cluster running hot?"[/dim]\n')
    time.sleep(0.3)
    print_step("\U0001f9e0", "[bold]Parsing intent...[/bold]")
    time.sleep(0.5)
    print_step("\U0001f50c", "[bold]Connecting to vCenter...[/bold]")
    time.sleep(0.3)
    print_step("\U0001f512", "[bold]Validating...[/bold]")
    time.sleep(0.2)
    print_step("\u2699\ufe0f", "[bold]Executing...[/bold]")
    time.sleep(0.5)
    console.print()
    print_insight(
        "## Cluster Health Summary\n\n"
        "Your cluster is **not running hot** — resource usage is moderate.\n\n"
        "- **CPU**: 32% utilized (2,840 MHz of 8,800 MHz)\n"
        "- **Memory**: 58% utilized (56.2 GB of 96.0 GB)\n"
        "- **VMs**: 5 total (3 powered on, 2 powered off)\n\n"
        "The ML worker (`ml-worker-01`) is powered off — if you start it, "
        "memory will jump to ~92%. Consider adding capacity before powering it on."
    )

    # --- Demo 4: Guardrail block ---
    console.print("\n[bold dim]━━━ Demo 4: Guardrail Block ━━━[/bold dim]\n")
    console.print('  [dim]$ vwrapper "delete all VMs"[/dim]\n')
    time.sleep(0.3)
    print_step("\U0001f9e0", "[bold]Parsing intent...[/bold]")
    time.sleep(0.5)
    print_step("\U0001f50c", "[bold]Connecting to vCenter...[/bold]")
    time.sleep(0.3)
    print_step("\U0001f512", "[bold]Validating...[/bold]")
    time.sleep(0.3)
    print_blocked("Action 'delete_vm' is permanently blocked. Destructive operations are not allowed.")
    console.print()


@app.command()
def status() -> None:
    """Check vCenter connectivity."""
    from vwrapper.providers.vmware import VMwareProvider

    config = get_config()
    console.print("\n  \U0001f50c Connecting to vCenter...", end="")
    try:
        with VMwareProvider(config.vcenter) as provider:
            vm_count = provider.vm_count()
        console.print(f" [green]connected[/green]")
        console.print(f"  [dim]{vm_count} VM(s) found[/dim]\n")
    except Exception as e:
        console.print(f" [red]failed[/red]")
        console.print(f"  [red]{e}[/red]\n")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version."""
    console.print(f"vWrapper v{__version__}")


def main() -> None:
    app()
