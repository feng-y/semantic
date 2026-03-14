"""Artifact writer — writes artifacts to docs/semantic/ with versioning."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Default retention: keep latest N working versions
DEFAULT_VERSION_WINDOW = 3

# Directories that hold versioned artifacts
VERSIONED_DIRS = ("discovery", "review")

# Baseline directory (accepted versions, never auto-pruned)
BASELINE_DIR = "baseline"


def write_artifact(
    root: str | Path,
    category: str,
    name: str,
    content: str,
    *,
    versioned: bool = True,
) -> Path:
    """Write an artifact file under docs/semantic/{category}/.

    Args:
        root: Repository root path.
        category: One of 'discovery', 'review', 'baseline', 'schemas'.
        name: Base artifact name (e.g. 'repo-facts').
        content: Artifact content as string.
        versioned: If True, assign a version number. Baselines are always unversioned.

    Returns:
        Path to the written file.
    """
    base_dir = Path(root) / "docs" / "semantic" / category
    base_dir.mkdir(parents=True, exist_ok=True)

    if versioned and category in VERSIONED_DIRS:
        version = _next_version(base_dir, name)
        filename = f"{name}.v{version}.md"
    else:
        filename = f"{name}.md"

    out_path = base_dir / filename
    out_path.write_text(content)
    return out_path


def _next_version(directory: Path, name: str) -> int:
    """Determine the next version number for an artifact."""
    existing = _find_versions(directory, name)
    if not existing:
        return 1
    return max(existing) + 1


def _find_versions(directory: Path, name: str) -> list[int]:
    """Find all existing version numbers for an artifact name."""
    pattern = re.compile(rf"^{re.escape(name)}\.v(\d+)\.md$")
    versions = []
    if directory.exists():
        for f in directory.iterdir():
            m = pattern.match(f.name)
            if m:
                versions.append(int(m.group(1)))
    return sorted(versions)


def get_latest_version_path(root: str | Path, category: str, name: str) -> Path | None:
    """Get the path to the latest versioned artifact, or None if none exist."""
    base_dir = Path(root) / "docs" / "semantic" / category
    versions = _find_versions(base_dir, name)
    if not versions:
        return None
    return base_dir / f"{name}.v{max(versions)}.md"


def get_latest_working_version_path(
    root: str | Path, category: str, name: str,
) -> Path | None:
    """Get the latest working (non-baseline) versioned artifact.

    Reads only from docs/semantic/{category}/, never from baseline/.
    This ensures refine never accidentally reads accepted checkpoint artifacts.
    """
    if category == BASELINE_DIR:
        return None
    return get_latest_version_path(root, category, name)


def prune_old_versions(
    root: str | Path,
    category: str,
    name: str,
    *,
    keep: int = DEFAULT_VERSION_WINDOW,
    accepted_versions: set[int] | None = None,
) -> list[Path]:
    """Remove old versions beyond the retention window.

    Never removes accepted or checkpointed versions.

    Returns:
        List of paths that were removed.
    """
    base_dir = Path(root) / "docs" / "semantic" / category
    versions = _find_versions(base_dir, name)
    accepted = accepted_versions or set()

    if len(versions) <= keep:
        return []

    to_remove = versions[: len(versions) - keep]
    removed: list[Path] = []
    for v in to_remove:
        if v in accepted:
            continue
        p = base_dir / f"{name}.v{v}.md"
        if p.exists():
            p.unlink()
            removed.append(p)
    return removed


def write_baseline(root: str | Path, name: str, content: str) -> Path:
    """Write an accepted baseline artifact (never auto-pruned)."""
    return write_artifact(root, BASELINE_DIR, name, content, versioned=False)


def safe_write_artifact(
    root: str | Path,
    category: str,
    name: str,
    content: str,
    validate_fn: Any | None = None,
) -> tuple[Path | None, list[str]]:
    """Write an artifact only if it passes validation.

    Args:
        validate_fn: Optional callable(content, name) -> list[str] of errors.
                     If None, skips validation.

    Returns:
        (written_path, errors). If errors is non-empty, path is None.
    """
    if validate_fn is not None:
        errors = validate_fn(content, name)
        if errors:
            return None, errors

    path = write_artifact(root, category, name, content)
    return path, []
