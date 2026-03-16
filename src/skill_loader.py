"""Skill loader — parses .skill files (YAML) and SKILL.md files (YAML frontmatter) into structured dicts."""

from __future__ import annotations

import re
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
    """Parse a .skill YAML file or SKILL.md (YAML frontmatter) and return a structured dict.

    Supports two formats:
    1. .skill files: Pure YAML
    2. SKILL.md files: YAML frontmatter (--- ... ---) followed by markdown

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

    # Check if this is a SKILL.md file with YAML frontmatter
    if path.name == "SKILL.md":
        # Extract YAML frontmatter: ---\n...\n---
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
        if not match:
            raise SkillLoadError(f"SKILL.md file missing YAML frontmatter: {path}")
        yaml_text = match.group(1)
    else:
        # Legacy .skill format: pure YAML
        yaml_text = text

    try:
        skill = yaml.safe_load(yaml_text)
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
    """Load all skills referenced in manifest.yaml or from plugin.json + skills directory.

    Supports two modes:
    1. Legacy: manifest.yaml with explicit skill paths
    2. Standard: plugin.json with skills directory auto-discovery

    Returns a dict keyed by skill role (init, discover, review, refine, etc.).
    """
    path = Path(manifest_path)

    # Check if this is plugin.json (standard format)
    if path.name == "plugin.json":
        return _load_skills_from_plugin_json(path)

    # Legacy manifest.yaml format
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


def _load_skills_from_plugin_json(plugin_json_path: Path) -> dict[str, dict[str, Any]]:
    """Load skills from plugin.json by scanning the skills directory.

    Expects structure:
    .claude-plugin/plugin.json
    skills/
      semantic-init/SKILL.md
      semantic-discover/SKILL.md
      ...

    Returns dict keyed by skill name (e.g., "init" -> semantic-init skill data).
    """
    try:
        plugin_data = yaml.safe_load(plugin_json_path.read_text())
    except yaml.YAMLError as e:
        raise SkillLoadError(f"Invalid JSON in {plugin_json_path}: {e}") from e

    if not isinstance(plugin_data, dict):
        raise SkillLoadError(f"plugin.json must be a JSON object: {plugin_json_path}")

    # Get skills directory path (default: "./skills/")
    skills_dir_rel = plugin_data.get("skills", "./skills/")
    root = plugin_json_path.parent.parent  # .claude-plugin/plugin.json -> repo root
    skills_dir = root / skills_dir_rel.lstrip("./")

    if not skills_dir.exists():
        raise FileNotFoundError(f"Skills directory not found: {skills_dir}")

    skills: dict[str, dict[str, Any]] = {}

    # Scan for skill directories containing SKILL.md
    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir():
            continue

        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue

        skill_data = load_skill(skill_md, root=root)
        skill_name = skill_data["name"]

        # Map to role (strip "semantic-" prefix for backward compatibility)
        role = skill_name.replace("semantic-", "")
        skills[role] = skill_data

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
