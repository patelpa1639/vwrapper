from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VCenterConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VCENTER_")

    host: str = "vcenter.lab.local"
    user: str = "administrator@vsphere.local"
    password: str = ""
    insecure: bool = True


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: Literal["anthropic", "openai"] = "anthropic"
    api_key: str = ""
    model: str = "claude-haiku-4-5-20251001"


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VWRAPPER_")

    max_vms: int = 50
    dry_run: bool = False

    vcenter: VCenterConfig = Field(default_factory=VCenterConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


@lru_cache
def get_config() -> AppConfig:
    from dotenv import load_dotenv

    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    return AppConfig()
