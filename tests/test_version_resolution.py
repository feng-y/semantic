"""Version resolution hardening tests.

Verifies get_latest_valid_version_path returns the latest structurally
valid artifact, skipping malformed and empty files.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.artifact_writer import get_latest_valid_version_path, get_latest_version_path
from src.context_builder import _read_latest_working_artifact
from src.discovery_executor import validate_artifact_content
from tests.fake_executors import stub_executor


def _valid_ru() -> str:
    return stub_executor("", {}, artifact_name="repo-understanding")


def _invalid_ru() -> str:
    return "# repo-understanding\n\nMalformed — no schema headings.\n"


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return tmp_path


def _write(repo: Path, name: str, content: str, version: int) -> Path:
    d = repo / "docs" / "fact" / "discovery"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.v{version}.md"
    p.write_text(content)
    return p


# ===========================================================================
# Case 1 — invalid newest versions
# ===========================================================================


def test_case1_invalid_newest_returns_latest_valid(repo: Path) -> None:
    """v1 valid, v2 valid, v3 invalid, v4 invalid → returns v2."""
    _write(repo, "repo-understanding", _valid_ru(), 1)
    _write(repo, "repo-understanding", _valid_ru(), 2)
    _write(repo, "repo-understanding", _invalid_ru(), 3)
    _write(repo, "repo-understanding", _invalid_ru(), 4)

    result = get_latest_valid_version_path(
        repo, "discovery", "repo-understanding", validate_artifact_content,
    )
    assert result is not None
    assert result.name == "repo-understanding.v2.md"


# ===========================================================================
# Case 2 — no valid artifacts
# ===========================================================================


def test_case2_no_valid_returns_none(repo: Path) -> None:
    """v1 invalid, v2 invalid → None."""
    _write(repo, "repo-understanding", _invalid_ru(), 1)
    _write(repo, "repo-understanding", _invalid_ru(), 2)

    result = get_latest_valid_version_path(
        repo, "discovery", "repo-understanding", validate_artifact_content,
    )
    assert result is None


# ===========================================================================
# Case 3 — empty files ignored
# ===========================================================================


def test_case3_empty_files_skipped(repo: Path) -> None:
    """v1 valid, v2 empty, v3 invalid → returns v1."""
    _write(repo, "repo-understanding", _valid_ru(), 1)
    _write(repo, "repo-understanding", "", 2)  # empty
    _write(repo, "repo-understanding", _invalid_ru(), 3)

    result = get_latest_valid_version_path(
        repo, "discovery", "repo-understanding", validate_artifact_content,
    )
    assert result is not None
    assert result.name == "repo-understanding.v1.md"


# ===========================================================================
# Case 4 — newest valid
# ===========================================================================


def test_case4_all_valid_returns_newest(repo: Path) -> None:
    """v1 valid, v2 valid, v3 valid → returns v3."""
    _write(repo, "repo-understanding", _valid_ru(), 1)
    _write(repo, "repo-understanding", _valid_ru(), 2)
    _write(repo, "repo-understanding", _valid_ru(), 3)

    result = get_latest_valid_version_path(
        repo, "discovery", "repo-understanding", validate_artifact_content,
    )
    assert result is not None
    assert result.name == "repo-understanding.v3.md"


# ===========================================================================
# Case 5 — context builder integration (Task 5 failure injection)
# ===========================================================================


def test_case5_context_builder_resolves_valid(repo: Path) -> None:
    """Context builder skips corrupted artifacts and resolves v1."""
    _write(repo, "repo-understanding", _valid_ru(), 1)
    _write(repo, "repo-understanding", _invalid_ru(), 2)
    _write(repo, "repo-understanding", _invalid_ru(), 3)

    content = _read_latest_working_artifact(repo, "discovery", "repo-understanding")
    assert content is not None
    assert "## System Purpose" in content


def test_case5_context_builder_returns_none_when_all_invalid(repo: Path) -> None:
    _write(repo, "repo-understanding", _invalid_ru(), 1)
    _write(repo, "repo-understanding", _invalid_ru(), 2)

    content = _read_latest_working_artifact(repo, "discovery", "repo-understanding")
    assert content is None


# ===========================================================================
# Backward compatibility — get_latest_version_path unchanged
# ===========================================================================


def test_old_resolver_still_returns_non_empty(repo: Path) -> None:
    """get_latest_version_path still returns latest non-empty (unchanged behavior)."""
    _write(repo, "repo-understanding", _valid_ru(), 1)
    _write(repo, "repo-understanding", _invalid_ru(), 2)

    result = get_latest_version_path(repo, "discovery", "repo-understanding")
    assert result is not None
    assert result.name == "repo-understanding.v2.md"  # old behavior: non-empty, not validated
