from __future__ import annotations

from pathlib import Path

import yaml

from .runner_models import RunState


def load_state(path: Path, mode: str) -> RunState:
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        loaded_mode = data.get("mode", mode)
        if loaded_mode not in ("next", "all", "resume", "reset"):
            loaded_mode = mode
        return RunState(**data, mode=loaded_mode)  # type: ignore[arg-type]
    return RunState(mode=mode)  # type: ignore[arg-type]

def save_state(path: Path, state: RunState):
    path.write_text(yaml.safe_dump(state.model_dump(), sort_keys=False, allow_unicode=True), encoding="utf-8")
