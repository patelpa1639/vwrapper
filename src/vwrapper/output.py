from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from vwrapper.models.actions import Action, ActionResult, VMInfo

console = Console()


def print_vm_table(vms: list[VMInfo]) -> None:
    table = Table(title="Virtual Machines", show_lines=True)
    table.add_column("Name", style="cyan bold")
    table.add_column("Power", style="green")
    table.add_column("CPU", justify="right")
    table.add_column("Memory (MB)", justify="right")
    table.add_column("Guest OS")
    table.add_column("IP Address")

    for vm in vms:
        power_style = "green" if "powered" in vm.power_state.lower() and "on" in vm.power_state.lower() else "red"
        table.add_row(
            vm.name,
            f"[{power_style}]{vm.power_state}[/{power_style}]",
            str(vm.cpu),
            str(vm.memory_mb),
            vm.guest_os,
            vm.ip_address or "-",
        )

    console.print(table)
    console.print(f"\n[dim]{len(vms)} VM(s) total[/dim]")


def print_action_plan(action: Action) -> None:
    params_str = "\n".join(f"  {k}: {v}" for k, v in action.params.items()) if action.params else "  (none)"
    console.print(
        Panel(
            f"[bold]Action:[/bold] {action.name}\n[bold]Params:[/bold]\n{params_str}",
            title="[yellow]Proposed Action[/yellow]",
            border_style="yellow",
        )
    )


def print_result(result: ActionResult) -> None:
    if result.success:
        console.print(
            Panel(
                f"[green bold]Success[/green bold]\n\n{_format_data(result.data)}",
                title=f"[green]{result.action}[/green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red bold]Failed[/red bold]\n\n{result.error}",
                title=f"[red]{result.action}[/red]",
                border_style="red",
            )
        )


def print_insight(summary: str) -> None:
    console.print(
        Panel(
            Markdown(summary),
            title="[blue]Infrastructure Insight[/blue]",
            border_style="blue",
        )
    )


def print_blocked(reason: str) -> None:
    console.print(
        Panel(
            f"[red]{reason}[/red]",
            title="[red]Blocked by Guardrails[/red]",
            border_style="red",
        )
    )


def print_step(icon: str, message: str) -> None:
    console.print(f"  {icon} {message}")


def confirm(message: str) -> bool:
    return console.input(f"\n  [yellow]{message}[/yellow] [dim](y/N)[/dim] ").strip().lower() in ("y", "yes")


def _format_data(data: object) -> str:
    if isinstance(data, dict):
        return "\n".join(f"  {k}: {v}" for k, v in data.items())
    if isinstance(data, list):
        return "\n".join(f"  - {item}" for item in data)
    return str(data) if data else ""
