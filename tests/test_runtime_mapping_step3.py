"""Step 3 — Runtime Mapping tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RUNTIME_MAPPING = {
    "semantic-init": ("src.dispatcher", "_handle_init"),
    "semantic-discover": ("src.discovery_executor", "run_discovery"),
    "semantic-review": ("src.state_inspector", "inspect"),
    "semantic-refine": ("src.refine_executor", "run_refine"),
    "semantic-baseline": ("src.refine_executor", "run_refine"),
    "semantic-status": ("src.state_inspector", "inspect"),
    "semantic-reset": ("src.dispatcher", "_handle_reset"),
}


class TestRuntimeMappingStep3:
    @pytest.mark.parametrize("skill,mapping", list(RUNTIME_MAPPING.items()))
    def test_entrypoint_exists(self, skill: str, mapping: tuple[str, str]) -> None:
        module_path, func_name = mapping
        mod = importlib.import_module(module_path)
        assert hasattr(mod, func_name), (
            f"Skill {skill}: {module_path}.{func_name} not found"
        )

    @pytest.mark.parametrize("skill,mapping", list(RUNTIME_MAPPING.items()))
    def test_entrypoint_callable(self, skill: str, mapping: tuple[str, str]) -> None:
        module_path, func_name = mapping
        mod = importlib.import_module(module_path)
        fn = getattr(mod, func_name)
        assert callable(fn), f"Skill {skill}: {module_path}.{func_name} is not callable"
