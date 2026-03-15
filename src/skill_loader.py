"""Skill loader — parses .skill files (YAML) into structured dicts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SkillLoadError(Exception):
    """Raised when a .skill file is invalid or missing required fields."""


class PathSandboxError(Exception):
    """Raised when a file path escapes the repository sandbox."""


REQUIRED_FIELDS = {"name"}


def _validate_path(path: Path, root: Path) -> None:
    """Validate that path is within root (sandbox check).

    Raises PathSandboxError if the resolved path escapes the root.
    """
    try:
        resolved = path.resolve()
        resolved_root = root.resolve()
        resolved.relative_to(resolved_root)
    except ValueError:
        raise PathSandboxError(
            f"Path '{path}' escapes repository sandbox '{root}'"
        )


def load_skill(skill_path: str | Path, root: Path | None = None) -> dict[str, Any]:
    """Parse a .skill YAML file and return a structured dict.

    Required fields: name
    Optional fields: purpose, inputs, steps, outputs, logic

    Args:
        root: If provided, validates that skill_path is within root sandbox.
    """
    path = Path(skill_path)
    if root is not None:
        _validate_path(path, root)
    if not path.exists():
        raise FileNotFoundError(f"Skill file not found: {path}")

    text = path.read_text()
    try:
        skill = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise SkillLoadError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(skill, dict):
        raise SkillLoadError(f"Skill file must be a YAML mapping, got {type(skill).__name__}: {path}")

    missing = REQUIRED_FIELDS - skill.keys()
    if missing:
        raise SkillLoadError(f"Missing required fields {missing} in {path}")

    skill["_path"] = str(path)
    return skill


def load_all_skills(manifest_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load all skills referenced in manifest.yaml.

    Returns a dict keyed by skill role (init, discover, review, refine, etc.).
    """
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    text = path.read_text()
    try:
        manifest = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise SkillLoadError(f"Invalid YAML in manifest {path}: {e}") from e

    if not isinstance(manifest, dict) or "skills" not in manifest:
        raise SkillLoadError(f"Manifest must contain a 'skills' mapping: {path}")

    root = path.parent
    skills: dict[str, dict[str, Any]] = {}
    for role, rel_path in manifest["skills"].items():
        skills[role] = load_skill(root / rel_path, root=root)

    return skills


def get_skill_steps(skill: dict[str, Any]) -> list[dict[str, str]]:
    """Extract step entries from a loaded skill.

    Each step in the YAML is a dict with one of:
      - {run: path}
      - {apply: path}
      - {if: condition, run: path}

    Returns list of dicts with 'action' and 'target' keys,
    plus 'condition' for conditional steps.
    """
    steps_raw = skill.get("steps", [])
    if not isinstance(steps_raw, list):
        raise SkillLoadError(f"'steps' must be a list in skill '{skill.get('name')}'")

    steps: list[dict[str, str]] = []
    for entry in steps_raw:
        if isinstance(entry, dict):
            if "run" in entry and "if" in entry:
                steps.append({
                    "action": "conditional",
                    "condition": entry["if"],
                    "target": entry["run"],
                })
            elif "run" in entry:
                steps.append({"action": "run", "target": entry["run"]})
            elif "apply" in entry:
                steps.append({"action": "apply", "target": entry["apply"]})
            else:
                raise SkillLoadError(
                    f"Unknown step keys {set(entry.keys())} in skill '{skill.get('name')}'"
                )
        else:
            raise SkillLoadError(
                f"Step must be a mapping, got {type(entry).__name__}: {entry}"
            )

    return steps
