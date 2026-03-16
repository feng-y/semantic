from pathlib import Path
import yaml
from .runner_models import RunState

def load_state(path: Path, mode: str) -> RunState:
    if path.exists():
        return RunState(**(yaml.safe_load(path.read_text(encoding="utf-8")) or {}))
    return RunState(mode=mode)

def save_state(path: Path, state: RunState):
    path.write_text(yaml.safe_dump(state.model_dump(), sort_keys=False, allow_unicode=True), encoding="utf-8")
