"""Tests for vwrapper.agent.intent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from vwrapper.agent.intent import _parse_json, parse, summarize
from vwrapper.config import AppConfig, LLMConfig, VCenterConfig
from vwrapper.models.actions import Action


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config() -> AppConfig:
    return AppConfig(
        max_vms=50,
        dry_run=False,
        vcenter=VCenterConfig(host="fake", user="fake", password="fake"),
        llm=LLMConfig(provider="anthropic", api_key="fake-key", model="claude-haiku-4-5-20251001"),
    )


@pytest.fixture()
def openai_config() -> AppConfig:
    return AppConfig(
        max_vms=50,
        dry_run=False,
        vcenter=VCenterConfig(host="fake", user="fake", password="fake"),
        llm=LLMConfig(provider="openai", api_key="fake-key", model="gpt-4o-mini"),
    )


# ---------------------------------------------------------------------------
# _parse_json — valid JSON
# ---------------------------------------------------------------------------


class TestParseJsonValid:
    def test_plain_json(self) -> None:
        text = '{"action": "list_vms", "params": {}}'
        result = _parse_json(text)
        assert result == {"action": "list_vms", "params": {}}

    def test_json_with_whitespace(self) -> None:
        text = '  \n  {"action": "insight", "params": {"question": "health"}}  \n  '
        result = _parse_json(text)
        assert result["action"] == "insight"

    def test_nested_params(self) -> None:
        text = '{"action": "create_vm", "params": {"name": "vm1", "cpu": 4, "memory_mb": 8192}}'
        result = _parse_json(text)
        assert result["params"]["cpu"] == 4


# ---------------------------------------------------------------------------
# _parse_json — markdown-fenced JSON
# ---------------------------------------------------------------------------


class TestParseJsonMarkdownFenced:
    def test_json_code_fence(self) -> None:
        text = '```json\n{"action": "list_vms", "params": {}}\n```'
        result = _parse_json(text)
        assert result["action"] == "list_vms"

    def test_plain_code_fence(self) -> None:
        text = '```\n{"action": "create_vm", "params": {"name": "x"}}\n```'
        result = _parse_json(text)
        assert result["action"] == "create_vm"

    def test_fence_with_extra_text_around(self) -> None:
        text = 'Here is the action:\n```json\n{"action": "insight", "params": {"question": "q"}}\n```\nDone.'
        result = _parse_json(text)
        assert result["action"] == "insight"


# ---------------------------------------------------------------------------
# _parse_json — fallback to insight
# ---------------------------------------------------------------------------


class TestParseJsonFallback:
    def test_no_json_at_all(self) -> None:
        text = "I don't understand your request."
        result = _parse_json(text)
        assert result["action"] == "insight"
        assert result["params"]["question"] == text

    def test_invalid_json(self) -> None:
        text = "not json at all, no braces here"
        result = _parse_json(text)
        assert result["action"] == "insight"
        assert result["params"]["question"] == text

    def test_embedded_json_object(self) -> None:
        """If there's a JSON object buried in text, it should be extracted."""
        text = 'Sure! Here you go: {"action": "list_vms", "params": {}} Hope that helps!'
        result = _parse_json(text)
        assert result["action"] == "list_vms"


# ---------------------------------------------------------------------------
# parse() — mock LLM calls
# ---------------------------------------------------------------------------


class TestParse:
    @patch("vwrapper.agent.intent._call_llm")
    def test_parse_returns_action(self, mock_llm: MagicMock, config: AppConfig) -> None:
        mock_llm.return_value = '{"action": "list_vms", "params": {}}'
        action = parse("show me all VMs", config)

        assert isinstance(action, Action)
        assert action.name == "list_vms"
        assert action.params == {}
        assert action.raw_query == "show me all VMs"
        mock_llm.assert_called_once_with("show me all VMs", config)

    @patch("vwrapper.agent.intent._call_llm")
    def test_parse_with_create_vm(self, mock_llm: MagicMock, config: AppConfig) -> None:
        mock_llm.return_value = '{"action": "create_vm", "params": {"name": "dev-1", "cpu": 2}}'
        action = parse("create a dev vm", config)

        assert action.name == "create_vm"
        assert action.params["name"] == "dev-1"
        assert action.params["cpu"] == 2

    @patch("vwrapper.agent.intent._call_llm")
    def test_parse_fallback_on_garbage(self, mock_llm: MagicMock, config: AppConfig) -> None:
        mock_llm.return_value = "Sorry, I can't help with that."
        action = parse("do something weird", config)

        assert action.name == "insight"
        assert "Sorry" in action.params["question"]

    @patch("vwrapper.agent.intent._call_llm")
    def test_parse_missing_action_defaults_to_insight(self, mock_llm: MagicMock, config: AppConfig) -> None:
        mock_llm.return_value = '{"params": {"question": "what is going on?"}}'
        action = parse("what is going on?", config)

        assert action.name == "insight"

    @patch("vwrapper.agent.intent._call_llm")
    def test_parse_missing_params_defaults_to_empty(self, mock_llm: MagicMock, config: AppConfig) -> None:
        mock_llm.return_value = '{"action": "list_vms"}'
        action = parse("list vms", config)

        assert action.params == {}


# ---------------------------------------------------------------------------
# summarize() — mock LLM calls
# ---------------------------------------------------------------------------


class TestSummarize:
    @patch("vwrapper.agent.intent._call_anthropic")
    def test_summarize_anthropic(self, mock_anthropic: MagicMock, config: AppConfig) -> None:
        mock_anthropic.return_value = "Everything looks healthy."
        result = summarize({"vm_count": 5}, "how are things?", config)

        assert result == "Everything looks healthy."
        mock_anthropic.assert_called_once()
        # Verify the prompt contains the data and question
        call_args = mock_anthropic.call_args
        assert "how are things?" in call_args[0][0]
        assert "vm_count" in call_args[0][0]

    @patch("vwrapper.agent.intent._call_openai")
    def test_summarize_openai(self, mock_openai: MagicMock, openai_config: AppConfig) -> None:
        mock_openai.return_value = "All good."
        result = summarize({"cpu": 80}, "capacity?", openai_config)

        assert result == "All good."
        mock_openai.assert_called_once()
