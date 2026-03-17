from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Action(BaseModel):
    name: str
    params: dict[str, Any] = {}
    raw_query: str = ""


class ActionResult(BaseModel):
    success: bool
    data: Any = None
    error: str | None = None
    action: str = ""


class VMInfo(BaseModel):
    name: str
    power_state: str
    cpu: int
    memory_mb: int
    guest_os: str = ""
    ip_address: str | None = None


class GuardrailResult(BaseModel):
    allowed: bool
    reason: str = ""
    needs_confirmation: bool = False
    confirmation_message: str = ""
