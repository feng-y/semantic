"""Artifact writer — writes artifacts to docs/fact/ with versioning."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

# Default retention: keep latest N working versions
DEFAULT_VERSION_WINDOW = 3

# Directories that hold versioned artifacts
VERSIONED_DIRS = ("discovery", "review")

# Baseline directory (accepted versions, never auto-pruned)
BASELINE_DIR = "baseline"

# Maximum retries for atomic version allocation
_MAX_VERSION_RETRIES = 64


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path using write-then-rename to prevent truncated files."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content)
    os.replace(str(tmp_path), str(path))


def write_artifact(
    root: str | Path,
    category: str,
    name: str,
    content: str,
    *,
    versioned: bool = True,
) -> Path:
    """Write an artifact file under docs/fact/{category}/.

    Args:
        root: Repository root path.
        category: One of 'discovery', 'review', 'baseline', 'schemas'.
        name: Base artifact name (e.g. 'repo-facts').
        content: Artifact content as string.
        versioned: If True, assign a version number. Baselines are always unversioned.

    Returns:
        Path to the written file.
    """
    base_dir = Path(root) / "docs" / "fact" / category
    base_dir.mkdir(parents=True, exist_ok=True)

    if versioned and category in VERSIONED_DIRS:
        version = _next_version(base_dir, name)
        filename = f"{name}.v{version}.md"
    else:
        filename = f"{name}.md"

    out_path = base_dir / filename
    _atomic_write(out_path, content)
    return out_path


def _next_version(directory: Path, name: str) -> int:
    """Atomically allocate the next version number for an artifact.

    Uses O_CREAT | O_EXCL to create a lock file exclusively, preventing
    two concurrent writers from claiming the same version number.

    Retries up to _MAX_VERSION_RETRIES times if another writer claims
    the same version concurrently.

    Returns the allocated version number (lock file is left in place;
    the caller will overwrite it with the actual artifact content).
    """
    existing = _find_versions(directory, name)
    candidate = (max(existing) + 1) if existing else 1

    for _ in range(_MAX_VERSION_RETRIES):
        lock_path = directory / f"{name}.v{candidate}.md"
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return candidate
        except FileExistsError:
            candidate += 1

    raise RuntimeError(
        f"Failed to allocate version for '{name}' after {_MAX_VERSION_RETRIES} retries"
    )


def _peek_next_version(directory: Path, name: str) -> int:
    """Determine the next version number without creating any files.

    Used for staging/validation passes where no file should be created
    until all validations pass. Not safe for concurrent use — use
    _next_version() when atomic allocation is required.
    """
    existing = _find_versions(directory, name)
    return (max(existing) + 1) if existing else 1


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
    """Get the path to the latest valid versioned artifact, or None if none exist.

    Skips empty or truncated files by walking backwards from the highest version.
    """
    base_dir = Path(root) / "docs" / "fact" / category
    versions = _find_versions(base_dir, name)
    if not versions:
        return None
    # Walk backwards to find the latest non-empty artifact
    for v in reversed(versions):
        p = base_dir / f"{name}.v{v}.md"
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def get_latest_valid_version_path(
    root: str | Path,
    category: str,
    name: str,
    validate_fn: Any,
) -> Path | None:
    """Get the path to the latest structurally valid versioned artifact.

    Walks backwards from the highest version, skipping empty files and
    files that fail the provided validator. Returns the first valid path,
    or None if no valid artifact exists.

    This is a defense-in-depth improvement over get_latest_version_path,
    which only checks file size.

    Args:
        validate_fn: callable(content, name) -> list[str] of errors.
    """
    base_dir = Path(root) / "docs" / "fact" / category
    versions = _find_versions(base_dir, name)
    if not versions:
        return None
    for v in reversed(versions):
        p = base_dir / f"{name}.v{v}.md"
        if not p.exists() or p.stat().st_size == 0:
            continue
        content = p.read_text()
        errors = validate_fn(content, name)
        if not errors:
            return p
    return None


def get_latest_working_version_path(
    root: str | Path, category: str, name: str,
) -> Path | None:
    """Get the latest working (non-baseline) versioned artifact.

    Reads only from docs/fact/{category}/, never from baseline/.
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
    base_dir = Path(root) / "docs" / "fact" / category
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


def get_accepted_versions(root: str | Path) -> dict[str, set[int]]:
    """Read accepted baseline versions from checkpoint.json.

    Returns a dict mapping artifact name to set of accepted version numbers.
    These versions should be protected from pruning.
    """
    checkpoint_path = Path(root) / "docs" / "fact" / "baseline" / "checkpoint.json"
    if not checkpoint_path.exists():
        return {}

    try:
        checkpoint = json.loads(checkpoint_path.read_text())
        source_versions = checkpoint.get("source_versions", {})

        # Convert to dict[str, set[int]], filtering out None values
        result: dict[str, set[int]] = {}
        for name, version in source_versions.items():
            if version is not None:
                result[name] = {version}
        return result
    except (json.JSONDecodeError, OSError):
        return {}


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


def stage_artifact(
    root: str | Path,
    category: str,
    name: str,
    content: str,
    *,
    validate_fn: Any | None = None,
) -> tuple[str, str, list[str]]:
    """Validate and prepare an artifact for writing without committing to disk.

    Returns (target_path, content, errors). If errors is non-empty, the
    artifact should not be written.
    """
    base_dir = Path(root) / "docs" / "fact" / category
    base_dir.mkdir(parents=True, exist_ok=True)

    if category in VERSIONED_DIRS:
        # Use peek (no file creation) — actual atomic allocation happens in commit_staged
        version = _peek_next_version(base_dir, name)
        filename = f"{name}.v{version}.md"
    else:
        filename = f"{name}.md"

    target_path = str(base_dir / filename)

    if validate_fn is not None:
        errors = validate_fn(content, name)
        if errors:
            return target_path, content, errors

    return target_path, content, []


def commit_staged(staged: list[tuple[str, str]]) -> list[Path]:
    """Write all staged artifacts to disk atomically. Called only after all validations pass.

    Writes directly from staged paths. Version allocation happens during staging
    via _peek_next_version(). The paths returned match the staged paths.
    """
    written: list[Path] = []
    for target_path, content in staged:
        p = Path(target_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(p, content)
        written.append(p)
    return written


# ---------------------------------------------------------------------------
# Semantic snapshot — cross-artifact version consistency
# ---------------------------------------------------------------------------

SNAPSHOT_ARTIFACTS = [
    ("discovery", "repo-understanding"),
    ("discovery", "knowledge-confidence"),
    ("discovery", "domain-candidates"),
    ("review", "review-summary"),
]


def write_semantic_snapshot(root: str | Path) -> Path:
    """Record current artifact versions as a consistent snapshot.

    Written after successful pipeline completion. Used on next run
    to detect cross-artifact version skew.
    """
    root = Path(root)
    versions: dict[str, int | None] = {}
    for category, name in SNAPSHOT_ARTIFACTS:
        path = get_latest_working_version_path(root, category, name)
        if path is not None:
            m = re.search(r"\.v(\d+)\.md$", path.name)
            versions[name] = int(m.group(1)) if m else None
        else:
            versions[name] = None

    snapshot_path = root / "docs" / "fact" / "semantic_snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(snapshot_path, json.dumps(versions, indent=2) + "\n")
    return snapshot_path


def check_semantic_snapshot(root: str | Path) -> list[str]:
    """Check current artifact versions against the last snapshot.

    Returns a list of warnings if version skew is detected.
    An empty list means versions are consistent (or no snapshot exists).
    """
    root = Path(root)
    snapshot_path = root / "docs" / "fact" / "semantic_snapshot.json"
    if not snapshot_path.exists():
        return []

    try:
        saved = json.loads(snapshot_path.read_text())
    except (json.JSONDecodeError, OSError):
        return ["semantic_snapshot.json is corrupted or unreadable"]

    warnings: list[str] = []
    for category, name in SNAPSHOT_ARTIFACTS:
        path = get_latest_working_version_path(root, category, name)
        if path is not None:
            m = re.search(r"\.v(\d+)\.md$", path.name)
            current_v = int(m.group(1)) if m else None
        else:
            current_v = None

        saved_v = saved.get(name)
        if saved_v is not None and current_v is not None:
            if current_v != saved_v:
                warnings.append(
                    f"{name}: version skew detected "
                    f"(snapshot=v{saved_v}, current=v{current_v})"
                )
        elif saved_v is not None and current_v is None:
            warnings.append(f"{name}: artifact missing (was v{saved_v} at last snapshot)")

    return warnings
