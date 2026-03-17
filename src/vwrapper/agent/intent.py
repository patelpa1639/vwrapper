from __future__ import annotations

import json
import re

from vwrapper.config import AppConfig
from vwrapper.models.actions import Action

from .prompts import SYSTEM_PROMPT


def parse(query: str, config: AppConfig) -> Action:
    """Send the user query to the LLM and return a structured Action."""
    raw = _call_llm(query, config)
    data = _parse_json(raw)

    return Action(
        name=data.get("action", "insight"),
        params=data.get("params", {}),
        raw_query=query,
    )


def summarize(data: dict, question: str, config: AppConfig) -> str:
    """Ask the LLM to summarize infrastructure data in plain English."""
    prompt = (
        f"You are an AI SRE assistant. The user asked: '{question}'\n\n"
        f"Here is the infrastructure data:\n{json.dumps(data, indent=2)}\n\n"
        "Summarize this in plain English. Be concise and actionable. "
        "If something looks concerning, flag it. Use bullet points."
    )

    if config.llm.provider == "anthropic":
        return _call_anthropic(prompt, config, system="You are a helpful infrastructure assistant.")
    return _call_openai(prompt, config, system="You are a helpful infrastructure assistant.")


def _call_llm(query: str, config: AppConfig) -> str:
    if config.llm.provider == "anthropic":
        return _call_anthropic(query, config, system=SYSTEM_PROMPT)
    return _call_openai(query, config, system=SYSTEM_PROMPT)


def _call_anthropic(query: str, config: AppConfig, system: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.llm.api_key)
    response = client.messages.create(
        model=config.llm.model,
        max_tokens=300,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": query}],
    )
    return response.content[0].text


def _call_openai(query: str, config: AppConfig, system: str) -> str:
    import openai

    client = openai.OpenAI(api_key=config.llm.api_key)
    response = client.chat.completions.create(
        model=config.llm.model,
        max_tokens=300,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ],
    )
    return response.choices[0].message.content or ""


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response, stripping markdown fences if present."""
    text = text.strip()
    # Strip markdown code fences
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: try to find any JSON object in the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"action": "insight", "params": {"question": text}}
