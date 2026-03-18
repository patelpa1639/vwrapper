"""Tests for vwrapper.config."""

from __future__ import annotations

import pytest

from vwrapper.config import AppConfig, LLMConfig, VCenterConfig


# ---------------------------------------------------------------------------
# VCenterConfig
# ---------------------------------------------------------------------------


class TestVCenterConfig:
    def test_defaults(self) -> None:
        cfg = VCenterConfig()
        assert cfg.host == "vcenter.lab.local"
        assert cfg.user == "administrator@vsphere.local"
        assert cfg.password == ""
        assert cfg.insecure is True

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VCENTER_HOST", "vc.example.com")
        monkeypatch.setenv("VCENTER_USER", "admin@corp")
        monkeypatch.setenv("VCENTER_PASSWORD", "s3cret")
        monkeypatch.setenv("VCENTER_INSECURE", "false")

        cfg = VCenterConfig()
        assert cfg.host == "vc.example.com"
        assert cfg.user == "admin@corp"
        assert cfg.password == "s3cret"
        assert cfg.insecure is False


# ---------------------------------------------------------------------------
# LLMConfig
# ---------------------------------------------------------------------------


class TestLLMConfig:
    def test_defaults(self) -> None:
        cfg = LLMConfig()
        assert cfg.provider == "anthropic"
        assert cfg.api_key == ""
        assert cfg.model == "claude-haiku-4-5-20251001"

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "sk-test123")
        monkeypatch.setenv("LLM_MODEL", "gpt-4o")

        cfg = LLMConfig()
        assert cfg.provider == "openai"
        assert cfg.api_key == "sk-test123"
        assert cfg.model == "gpt-4o"

    def test_invalid_provider_rejected(self) -> None:
        with pytest.raises(Exception):
            LLMConfig(provider="gemini")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------


class TestAppConfig:
    def test_defaults(self) -> None:
        cfg = AppConfig()
        assert cfg.max_vms == 50
        assert cfg.dry_run is False
        assert isinstance(cfg.vcenter, VCenterConfig)
        assert isinstance(cfg.llm, LLMConfig)

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VWRAPPER_MAX_VMS", "100")
        monkeypatch.setenv("VWRAPPER_DRY_RUN", "true")

        cfg = AppConfig()
        assert cfg.max_vms == 100
        assert cfg.dry_run is True

    def test_nested_configs_receive_their_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VCENTER_HOST", "my-vc.local")
        monkeypatch.setenv("LLM_API_KEY", "key-abc")

        cfg = AppConfig()
        assert cfg.vcenter.host == "my-vc.local"
        assert cfg.llm.api_key == "key-abc"

    def test_explicit_values_override_defaults(self) -> None:
        cfg = AppConfig(
            max_vms=10,
            dry_run=True,
            vcenter=VCenterConfig(host="custom"),
            llm=LLMConfig(provider="openai", api_key="k"),
        )
        assert cfg.max_vms == 10
        assert cfg.dry_run is True
        assert cfg.vcenter.host == "custom"
        assert cfg.llm.provider == "openai"
