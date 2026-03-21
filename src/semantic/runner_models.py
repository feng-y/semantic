from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class RunState(BaseModel):
    mode: Literal["next", "all", "resume", "reset"]
    current_stage: str | None = None
    completed_stages: list[str] = []
    artifacts: dict[str, str] = {}
    errors: list[dict] = []
    warnings: list[str] = []
    blocked_reason: str | None = None
