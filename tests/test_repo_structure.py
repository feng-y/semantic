"""tests/test_repo_structure.py — repo-structure skill tests."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _mock_git_run(*args, **kwargs):
    """Return a fake subprocess result for git rev-parse HEAD."""
    if args and "rev-parse" in args[0]:
        m = MagicMock()
        m.stdout = "f00bar"
        m.returncode = 0
        return m
    return subprocess.run(*args, **kwargs)


class TestPreflight:
    def test_preflight_detects_missing_commit_extract(self, tmp_path, monkeypatch):
        """Preflight fails when commit-extract output is missing."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / ".planning" / "codebase").mkdir(parents=True)
        for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                      "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
            (tmp_path / ".planning" / "codebase" / fname).write_text("# fake")

        with patch.object(subprocess, "run", side_effect=_mock_git_run):
            from skills.repo_structure.preflight import check
            result = check(tmp_path)
        assert result.ok is False
        assert any(i.producer == "commit-extract" for i in result.missing)

    def test_preflight_detects_missing_gsd_dossier(self, tmp_path, monkeypatch):
        """Preflight fails when any of the 7 gsd files are missing."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "data" / "commit-extract").mkdir(parents=True)
        # Add at least one file so commit-extract passes
        (tmp_path / "data" / "commit-extract" / "commits.json").write_text("[]")

        with patch.object(subprocess, "run", side_effect=_mock_git_run):
            from skills.repo_structure.preflight import check
            result = check(tmp_path)
        assert result.ok is False
        missing_subjects = {m.subject for m in result.missing}
        for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                      "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
            assert any(fname in s for s in missing_subjects), (
                f"{fname} should be a missing subject; got {missing_subjects}"
            )

    def test_preflight_warns_on_missing_architecture_doc(self, tmp_path, monkeypatch):
        """Preflight warns (not fails) when docs/ARCHITECTURE.md is absent."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "data" / "commit-extract").mkdir(parents=True)
        (tmp_path / "data" / "commit-extract" / "commits.json").write_text("[]")
        gsd_dir = tmp_path / ".planning" / "codebase"
        gsd_dir.mkdir(parents=True)
        for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                      "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
            (gsd_dir / fname).write_text("# fake")

        with patch.object(subprocess, "run", side_effect=_mock_git_run):
            from skills.repo_structure.preflight import check
            result = check(tmp_path)
        assert result.ok is True
        arch_warnings = [w for w in result.warnings if "ARCHITECTURE" in w.subject]
        assert len(arch_warnings) >= 1

    def test_preflight_ok_when_all_required_present(self, tmp_path, monkeypatch):
        """Preflight passes when all required inputs exist."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "data" / "commit-extract").mkdir(parents=True)
        (tmp_path / "data" / "commit-extract" / "commits.json").write_text("[]")
        gsd_dir = tmp_path / ".planning" / "codebase"
        gsd_dir.mkdir(parents=True)
        for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                      "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
            (gsd_dir / fname).write_text("# fake")

        with patch.object(subprocess, "run", side_effect=_mock_git_run):
            from skills.repo_structure.preflight import check
            result = check(tmp_path)
        assert result.ok is True
