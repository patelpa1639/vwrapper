from __future__ import annotations

from typing import TYPE_CHECKING

from vwrapper.models.actions import Action, GuardrailResult

if TYPE_CHECKING:
    from vwrapper.config import AppConfig

BLOCKED_ACTIONS = {"delete_vm", "destroy_vm", "reset_vm", "format_datastore"}


def validate(
    action: Action,
    config: AppConfig,
    current_vm_count: int | None = None,
) -> GuardrailResult:
    """Run all guardrail rules against an action. First blocker wins."""

    # Dry run mode — block everything
    if config.dry_run:
        return GuardrailResult(
            allowed=False,
            reason=f"Dry-run mode: would execute '{action.name}' with {action.params}",
        )

    # Block destructive actions
    if action.name in BLOCKED_ACTIONS:
        return GuardrailResult(
            allowed=False,
            reason=f"Action '{action.name}' is blocked by guardrails. Destructive operations are not allowed.",
        )

    # Max VM limit
    if action.name == "create_vm" and current_vm_count is not None:
        if current_vm_count >= config.max_vms:
            return GuardrailResult(
                allowed=False,
                reason=f"VM limit reached ({current_vm_count}/{config.max_vms}). Cannot create more VMs.",
            )

    # Require confirmation for create_vm
    if action.name == "create_vm":
        params = action.params
        name = params.get("name", "unnamed")
        cpu = params.get("cpu", 2)
        mem = params.get("memory_mb", 4096)
        disk = params.get("disk_gb", 40)
        return GuardrailResult(
            allowed=True,
            needs_confirmation=True,
            confirmation_message=(
                f"Create VM '{name}' with {cpu} vCPUs, {mem} MB RAM, {disk} GB disk?"
            ),
        )

    # Safe actions pass through
    return GuardrailResult(allowed=True)
