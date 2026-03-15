"""Prompt loader — reads .prompt files and returns structured content."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class PathSandboxError(Exception):
    """Raised when a file path escapes the repository sandbox."""


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


def load_prompt(prompt_path: str | Path, root: Path | None = None) -> dict[str, Any]:
    """Parse a .prompt file into structured sections.

    Prompt files have a simple structure:
      SectionName:
      - item
      - item
    or:
      SectionName:
      free text

    Returns dict with 'goal', 'inputs', 'output', and other sections.

    Args:
        root: If provided, validates that prompt_path is within root sandbox.
    """
    path = Path(prompt_path)
    if root is not None:
        _validate_path(path, root)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    text = path.read_text()
    prompt: dict[str, Any] = {"_path": str(path), "_raw": text}

    current_section: str | None = None
    current_items: list[str] = []
    current_text: list[str] = []

    def _flush():
        if current_section is None:
            return
        key = _normalize_key(current_section)
        if current_items:
            prompt[key] = current_items[:]
        elif current_text:
            prompt[key] = "\n".join(current_text).strip()

    for raw_line in text.splitlines():
        # Section header: "SectionName:" at start of line
        header_match = re.match(r"^([A-Za-z][\w\s]*):$", raw_line.rstrip())
        if header_match:
            _flush()
            current_section = header_match.group(1)
            current_items = []
            current_text = []
            continue

        # List item
        item_match = re.match(r"^- (.+)", raw_line)
        if item_match and current_section:
            current_items.append(item_match.group(1).strip())
            continue

        # Free text continuation
        if current_section and raw_line.strip():
            current_text.append(raw_line)

    _flush()
    return prompt


def _normalize_key(section_name: str) -> str:
    """Convert 'Section Name' to 'section_name'."""
    return re.sub(r"\s+", "_", section_name.strip().lower())


def resolve_prompt_path(prompt_ref: str, root: str | Path) -> Path:
    """Resolve a prompt reference (from a skill step) to an absolute path.

    Validates that the resolved path is within the repository root sandbox.
    """
    root_path = Path(root)
    resolved = root_path / prompt_ref
    _validate_path(resolved, root_path)
    return resolved


def load_prompt_chain(prompt_refs: list[str], root: str | Path) -> list[dict[str, Any]]:
    """Load a sequence of prompts from a list of path references."""
    return [load_prompt(resolve_prompt_path(ref, root)) for ref in prompt_refs]
