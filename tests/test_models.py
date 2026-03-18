"""Tests for vwrapper.models.actions (Pydantic models)."""

from __future__ import annotations

import pytest

from vwrapper.models.actions import Action, ActionResult, GuardrailResult, VMInfo


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------


class TestAction:
    def test_create_with_all_fields(self) -> None:
        a = Action(name="create_vm", params={"name": "vm1"}, raw_query="make a vm")
        assert a.name == "create_vm"
        assert a.params == {"name": "vm1"}
        assert a.raw_query == "make a vm"

    def test_defaults(self) -> None:
        a = Action(name="list_vms")
        assert a.params == {}
        assert a.raw_query == ""

    def test_params_accept_arbitrary_types(self) -> None:
        a = Action(name="x", params={"count": 3, "flag": True, "tags": ["a", "b"]})
        assert a.params["count"] == 3
        assert a.params["flag"] is True
        assert a.params["tags"] == ["a", "b"]

    def test_serialization_round_trip(self) -> None:
        a = Action(name="insight", params={"question": "how many vms?"}, raw_query="q")
        data = a.model_dump()
        b = Action(**data)
        assert a == b


# ---------------------------------------------------------------------------
# ActionResult
# ---------------------------------------------------------------------------


class TestActionResult:
    def test_success_result(self) -> None:
        r = ActionResult(success=True, data={"name": "vm1"}, action="create_vm")
        assert r.success is True
        assert r.error is None
        assert r.data == {"name": "vm1"}
        assert r.action == "create_vm"

    def test_failure_result(self) -> None:
        r = ActionResult(success=False, error="connection refused")
        assert r.success is False
        assert r.error == "connection refused"
        assert r.data is None

    def test_defaults(self) -> None:
        r = ActionResult(success=True)
        assert r.data is None
        assert r.error is None
        assert r.action == ""

    def test_data_can_be_list(self) -> None:
        r = ActionResult(success=True, data=[1, 2, 3])
        assert r.data == [1, 2, 3]


# ---------------------------------------------------------------------------
# VMInfo
# ---------------------------------------------------------------------------


class TestVMInfo:
    def test_full_creation(self) -> None:
        vm = VMInfo(
            name="web-1",
            power_state="poweredOn",
            cpu=4,
            memory_mb=8192,
            guest_os="Ubuntu 22.04",
            ip_address="10.0.0.5",
        )
        assert vm.name == "web-1"
        assert vm.power_state == "poweredOn"
        assert vm.cpu == 4
        assert vm.memory_mb == 8192
        assert vm.guest_os == "Ubuntu 22.04"
        assert vm.ip_address == "10.0.0.5"

    def test_defaults(self) -> None:
        vm = VMInfo(name="test", power_state="poweredOff", cpu=1, memory_mb=512)
        assert vm.guest_os == ""
        assert vm.ip_address is None

    def test_ip_address_optional(self) -> None:
        vm = VMInfo(name="a", power_state="off", cpu=1, memory_mb=256, ip_address=None)
        assert vm.ip_address is None


# ---------------------------------------------------------------------------
# GuardrailResult
# ---------------------------------------------------------------------------


class TestGuardrailResult:
    def test_allowed(self) -> None:
        r = GuardrailResult(allowed=True)
        assert r.allowed is True
        assert r.reason == ""
        assert r.needs_confirmation is False
        assert r.confirmation_message == ""

    def test_blocked_with_reason(self) -> None:
        r = GuardrailResult(allowed=False, reason="too dangerous")
        assert r.allowed is False
        assert r.reason == "too dangerous"

    def test_needs_confirmation(self) -> None:
        r = GuardrailResult(allowed=True, needs_confirmation=True, confirmation_message="Are you sure?")
        assert r.needs_confirmation is True
        assert r.confirmation_message == "Are you sure?"
