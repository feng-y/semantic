"""Validation helpers for IBS Core baseline outputs."""

from __future__ import annotations

from . import artifact_validation


IBS_CORE_NAMES = ("purpose", "pipelines", "domains", "concepts")


def validate_ibs_core_artifact(name: str, content: str) -> list[str]:
    """Validate a single IBS Core artifact with existing baseline contracts."""
    return artifact_validation.validate_baseline_files({name: content})


def validate_ibs_core_outputs(outputs: dict[str, str]) -> list[str]:
    """Validate all required IBS Core outputs."""
    errors: list[str] = []
    for name in IBS_CORE_NAMES:
        content = outputs.get(name)
        if content is None:
            errors.append(f"missing ibs core output: {name}")
            continue
        artifact_errors = validate_ibs_core_artifact(name, content)
        for err in artifact_errors:
            errors.append(f"{name}: {err}")
    return errors

