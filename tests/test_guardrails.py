"""Tests for vwrapper.guardrails.rules."""

from __future__ import annotations

import pytest

from vwrapper.config import AppConfig, LLMConfig, VCenterConfig
from vwrapper.guardrails.rules import BLOCKED_ACTIONS, validate
from vwrapper.models.actions import Action


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config() -> AppConfig:
    """Normal (non-dry-run) config with default VM limit."""
    return AppConfig(
        max_vms=50,
        dry_run=False,
        vcenter=VCenterConfig(host="fake", user="fake", password="fake"),
        llm=LLMConfig(provider="anthropic", api_key="fake"),
    )


@pytest.fixture()
def dry_run_config() -> AppConfig:
    return AppConfig(
        max_vms=50,
        dry_run=True,
        vcenter=VCenterConfig(host="fake", user="fake", password="fake"),
        llm=LLMConfig(provider="anthropic", api_key="fake"),
    )


# ---------------------------------------------------------------------------
# Blocked actions
# ---------------------------------------------------------------------------


class TestBlockedActions:
    """Destructive actions must always be rejected."""

    @pytest.mark.parametrize("action_name", sorted(BLOCKED_ACTIONS))
    def test_blocked_actions_are_rejected(self, config: AppConfig, action_name: str) -> None:
        action = Action(name=action_name, params={})
        result = validate(action, config)

        assert result.allowed is False
        assert "blocked" in result.reason.lower()
        assert action_name in result.reason

    def test_blocked_actions_set_contains_expected_entries(self) -> None:
        expected = {"delete_vm", "destroy_vm", "reset_vm", "format_datastore"}
        assert BLOCKED_ACTIONS == expected


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


class TestDryRunMode:
    """In dry-run mode every action must be blocked."""

    @pytest.mark.parametrize(
        "action_name",
        ["list_vms", "create_vm", "insight", "delete_vm"],
    )
    def test_dry_run_blocks_everything(self, dry_run_config: AppConfig, action_name: str) -> None:
        action = Action(name=action_name, params={"foo": "bar"})
        result = validate(action, dry_run_config)

        assert result.allowed is False
        assert "dry-run" in result.reason.lower()
        assert action_name in result.reason

    def test_dry_run_includes_params_in_reason(self, dry_run_config: AppConfig) -> None:
        params = {"name": "test-vm", "cpu": 4}
        action = Action(name="create_vm", params=params)
        result = validate(action, dry_run_config)

        assert str(params) in result.reason


# ---------------------------------------------------------------------------
# VM limit enforcement
# ---------------------------------------------------------------------------


class TestVMLimit:
    """create_vm should be blocked when the VM cap is reached."""

    def test_create_vm_blocked_at_limit(self, config: AppConfig) -> None:
        action = Action(name="create_vm", params={"name": "new-vm"})
        result = validate(action, config, current_vm_count=50)

        assert result.allowed is False
        assert "limit" in result.reason.lower()

    def test_create_vm_blocked_above_limit(self, config: AppConfig) -> None:
        action = Action(name="create_vm", params={"name": "new-vm"})
        result = validate(action, config, current_vm_count=55)

        assert result.allowed is False

    def test_create_vm_allowed_below_limit(self, config: AppConfig) -> None:
        action = Action(name="create_vm", params={"name": "new-vm"})
        result = validate(action, config, current_vm_count=10)

        assert result.allowed is True

    def test_create_vm_allowed_when_count_none(self, config: AppConfig) -> None:
        """When current_vm_count is not provided the limit check is skipped."""
        action = Action(name="create_vm", params={"name": "new-vm"})
        result = validate(action, config, current_vm_count=None)

        assert result.allowed is True

    def test_custom_max_vms(self) -> None:
        cfg = AppConfig(
            max_vms=5,
            dry_run=False,
            vcenter=VCenterConfig(host="x", user="x", password="x"),
            llm=LLMConfig(provider="anthropic", api_key="x"),
        )
        action = Action(name="create_vm", params={"name": "vm"})

        assert validate(action, cfg, current_vm_count=5).allowed is False
        assert validate(action, cfg, current_vm_count=4).allowed is True


# ---------------------------------------------------------------------------
# create_vm confirmation
# ---------------------------------------------------------------------------


class TestCreateVMConfirmation:
    """create_vm that passes limit checks should still require confirmation."""

    def test_needs_confirmation(self, config: AppConfig) -> None:
        action = Action(name="create_vm", params={"name": "web-1", "cpu": 4, "memory_mb": 8192, "disk_gb": 80})
        result = validate(action, config, current_vm_count=10)

        assert result.allowed is True
        assert result.needs_confirmation is True
        assert "web-1" in result.confirmation_message
        assert "4" in result.confirmation_message  # cpu
        assert "8192" in result.confirmation_message  # mem
        assert "80" in result.confirmation_message  # disk

    def test_uses_defaults_when_params_missing(self, config: AppConfig) -> None:
        action = Action(name="create_vm", params={})
        result = validate(action, config)

        assert result.needs_confirmation is True
        assert "unnamed" in result.confirmation_message
        assert "2" in result.confirmation_message  # default cpu
        assert "4096" in result.confirmation_message  # default mem
        assert "40" in result.confirmation_message  # default disk


# ---------------------------------------------------------------------------
# Safe actions
# ---------------------------------------------------------------------------


class TestSafeActions:
    """Read-only / informational actions should pass through without issue."""

    @pytest.mark.parametrize("action_name", ["list_vms", "insight", "get_capacity"])
    def test_safe_actions_allowed(self, config: AppConfig, action_name: str) -> None:
        action = Action(name=action_name, params={})
        result = validate(action, config)

        assert result.allowed is True
        assert result.needs_confirmation is False
        assert result.reason == ""
