"""Smoke tests for vwrapper.output — verify functions don't crash."""

from __future__ import annotations

import pytest
from rich.console import Console

from vwrapper.models.actions import Action, ActionResult, VMInfo
from vwrapper.output import (
    _format_data,
    print_action_plan,
    print_blocked,
    print_insight,
    print_result,
    print_step,
    print_vm_table,
)


@pytest.fixture()
def capture_console(monkeypatch: pytest.MonkeyPatch) -> Console:
    """Replace the module-level console with one that writes to a string buffer."""
    import io

    import vwrapper.output as output_mod

    buf = io.StringIO()
    fake_console = Console(file=buf, no_color=True, highlight=False, width=120)
    monkeypatch.setattr(output_mod, "console", fake_console)
    return fake_console


# ---------------------------------------------------------------------------
# print_vm_table
# ---------------------------------------------------------------------------


class TestPrintVmTable:
    def test_empty_list(self, capture_console: Console) -> None:
        print_vm_table([])
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "0 VM(s) total" in output

    def test_single_vm(self, capture_console: Console) -> None:
        vms = [
            VMInfo(name="web-1", power_state="poweredOn", cpu=2, memory_mb=4096, guest_os="Ubuntu", ip_address="10.0.0.1"),
        ]
        print_vm_table(vms)
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "web-1" in output
        assert "1 VM(s) total" in output

    def test_powered_off_vm(self, capture_console: Console) -> None:
        vms = [
            VMInfo(name="db-1", power_state="poweredOff", cpu=4, memory_mb=8192),
        ]
        print_vm_table(vms)
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "db-1" in output

    def test_vm_without_ip(self, capture_console: Console) -> None:
        vms = [
            VMInfo(name="no-ip", power_state="poweredOn", cpu=1, memory_mb=512, ip_address=None),
        ]
        print_vm_table(vms)
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "-" in output  # placeholder for missing IP


# ---------------------------------------------------------------------------
# print_action_plan
# ---------------------------------------------------------------------------


class TestPrintActionPlan:
    def test_with_params(self, capture_console: Console) -> None:
        action = Action(name="create_vm", params={"name": "vm1", "cpu": 4})
        print_action_plan(action)
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "create_vm" in output
        assert "vm1" in output

    def test_no_params(self, capture_console: Console) -> None:
        action = Action(name="list_vms", params={})
        print_action_plan(action)
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "list_vms" in output
        assert "(none)" in output


# ---------------------------------------------------------------------------
# print_result
# ---------------------------------------------------------------------------


class TestPrintResult:
    def test_success(self, capture_console: Console) -> None:
        result = ActionResult(success=True, action="create_vm", data={"name": "vm1"})
        print_result(result)
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "Success" in output

    def test_failure(self, capture_console: Console) -> None:
        result = ActionResult(success=False, action="create_vm", error="timeout")
        print_result(result)
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "Failed" in output
        assert "timeout" in output


# ---------------------------------------------------------------------------
# print_insight / print_blocked / print_step
# ---------------------------------------------------------------------------


class TestMiscOutput:
    def test_print_insight(self, capture_console: Console) -> None:
        print_insight("Everything looks healthy.")
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "healthy" in output

    def test_print_blocked(self, capture_console: Console) -> None:
        print_blocked("Action blocked by guardrails")
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "blocked" in output.lower()

    def test_print_step(self, capture_console: Console) -> None:
        print_step(">>", "Connecting to vCenter")
        output = capture_console.file.getvalue()  # type: ignore[union-attr]
        assert "Connecting" in output


# ---------------------------------------------------------------------------
# _format_data helper
# ---------------------------------------------------------------------------


class TestFormatData:
    def test_dict(self) -> None:
        assert "name: vm1" in _format_data({"name": "vm1"})

    def test_list(self) -> None:
        assert "- a" in _format_data(["a", "b"])

    def test_string(self) -> None:
        assert _format_data("hello") == "hello"

    def test_none(self) -> None:
        assert _format_data(None) == ""
