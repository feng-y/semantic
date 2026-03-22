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


class TestSample:
    def test_sample_produces_manifest(self, tmp_path, monkeypatch):
        """sample stage writes a manifest.yaml with section entries."""
        import yaml
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "data/commit-extract").mkdir(parents=True)
        gsd_dir = tmp_path / ".planning/codebase"
        gsd_dir.mkdir(parents=True)
        for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                      "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
            (gsd_dir / fname).write_text(f"# {fname}\n\n## Section\nContent for {fname}.\n")

        from src.harness_state import HarnessState
        from skills.repo_structure.run import RepoStructureRunner

        runner = RepoStructureRunner()
        state = HarnessState()
        success = runner._run_sample(state)
        assert success

        manifest = tmp_path / "data/repo-structure/sample/manifest.yaml"
        assert manifest.exists()
        data = yaml.safe_load(manifest.read_text())
        assert "sections" in data
        assert len(data["sections"]) >= 7

    def test_sample_sections_cover_all_7_files(self, tmp_path, monkeypatch):
        """Each of the 7 gsd files gets at least one DocSectionTask entry."""
        import yaml
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "data/commit-extract").mkdir(parents=True)
        gsd_dir = tmp_path / ".planning/codebase"
        gsd_dir.mkdir(parents=True)
        for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                      "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
            (gsd_dir / fname).write_text(f"# {fname}\n\n## Section\nContent.\n")

        from src.harness_state import HarnessState
        from skills.repo_structure.run import RepoStructureRunner

        runner = RepoStructureRunner()
        state = HarnessState()
        runner._run_sample(state)

        data = yaml.safe_load(
            (tmp_path / "data/repo-structure/sample/manifest.yaml").read_text()
        )
        covered_files = {s["source_file"] for s in data["sections"]}
        expected = {f".planning/codebase/{fname}" for fname in [
            "STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
            "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]}
        assert expected.issubset(covered_files), f"Missing: {expected - covered_files}"


class TestHotspot:
    def test_hotspot_consumes_commit_semantic(self, tmp_path, monkeypatch):
        """hotspot stage reads commit-extract + commit-semantic and writes hotspot_map."""
        import yaml
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "data/commit-extract").mkdir(parents=True)
        (tmp_path / "data/commit-semantic/patterns").mkdir(parents=True)

        yaml.dump({"metadata": {"month": "2025-01"}, "commits": [
            {"commit_id": "abc", "files": ["src/hermes/registry.py", "src/hermes/registry.py"]}
        ]}, (tmp_path / "data/commit-extract/2025-01.yaml").open("w"))
        yaml.dump({"patterns": [{"pattern_id": "p1", "description": "Test pattern"}]},
                 (tmp_path / "data/commit-semantic/patterns/canonical.yaml").open("w"))

        from src.harness_state import HarnessState
        from skills.repo_structure.run import RepoStructureRunner

        runner = RepoStructureRunner()
        state = HarnessState()
        success = runner._run_hotspot(state)
        assert success

        maps_dir = tmp_path / "data/repo-structure/maps"
        hotspot_maps = list(maps_dir.glob("hotspot_map.v*.yaml"))
        assert len(hotspot_maps) >= 1

        data = yaml.safe_load(hotspot_maps[0].read_text())
        assert "metadata" in data
        assert "facts" in data


class TestExtract:
    def test_extract_produces_codebase_map(self, tmp_path, monkeypatch):
        """extract stage writes codebase_map.vN.yaml with fact entries."""
        import yaml
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "data/commit-extract").mkdir(parents=True)
        gsd_dir = tmp_path / ".planning/codebase"
        gsd_dir.mkdir(parents=True)
        (gsd_dir / "ARCHITECTURE.md").write_text(
            "## Key Abstractions\n\nThe `OperatorRegistry` class provides registration "
            "for operators using the `REGISTER_OPERATOR_BY_OPS` decorator.\n"
        )
        for fname in ["STRUCTURE.md", "CONCERNS.md", "CONVENTIONS.md",
                      "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
            (gsd_dir / fname).write_text(f"## Section\n\nContent for {fname}.\n")

        from src.harness_state import HarnessState
        from skills.repo_structure.run import RepoStructureRunner

        runner = RepoStructureRunner()
        state = HarnessState()
        runner._run_sample(state)
        success = runner._run_extract(state)
        assert success

        maps_dir = tmp_path / "data/repo-structure/maps"
        assert maps_dir.exists()
        maps = list(maps_dir.glob("codebase_map.v*.yaml"))
        assert len(maps) >= 1

        data = yaml.safe_load(maps[0].read_text())
        assert "facts" in data
        assert "metadata" in data
        assert len(data["facts"]) > 0
        for fact in data["facts"]:
            assert "fact_id" in fact
            assert "fact_type" in fact
            assert "evidence" in fact
            assert len(fact["evidence"]) > 0
            ev = fact["evidence"][0]
            assert "locator_type" in ev
            assert "locator" in ev
