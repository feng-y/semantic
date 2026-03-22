"""tests/test_repo_structure.py — repo-structure skill tests."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock, patch


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


class TestValidate:
    def test_validate_merges_three_maps(self, tmp_path, monkeypatch):
        """validate stage reads all 3 maps and writes validated + conflicts."""
        import yaml
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "data/commit-extract").mkdir(parents=True)
        maps_dir = tmp_path / "data/repo-structure/maps"
        maps_dir.mkdir(parents=True)

        yaml.dump({"metadata": {"version": "v0"}, "facts": [
            {"fact_id": "h1", "fact_type": "hotspot_signal",
             "statement": "module X changes often",
             "confidence": "confirmed", "status": "active",
             "repo_snapshot_commit": "abc", "source": "hotspot",
             "evidence": [{"source_type": "hotspot", "locator_type": "file_path", "locator": "X", "stable_ref": "X"}]}
        ]}, (maps_dir / "hotspot_map.v0.yaml").open("w"))

        yaml.dump({"metadata": {"version": "v0"}, "facts": [
            {"fact_id": "c1", "fact_type": "module_role",
             "statement": "src/X/ is a core module",
             "confidence": "confirmed", "status": "active",
             "repo_snapshot_commit": "abc", "source": "codebase",
             "evidence": [{"source_type": "codebase", "locator_type": "symbol", "locator": "X", "stable_ref": "X"}]}
        ]}, (maps_dir / "codebase_map.v0.yaml").open("w"))

        yaml.dump({"metadata": {"version": "v0"}, "adjudications": [
            {"claim_id": "a1", "status": "evidence_backed",
             "claim_text": "architect claim", "matched_evidence": []}
        ]}, (maps_dir / "architect_augment.v0.yaml").open("w"))

        from src.harness_state import HarnessState
        from skills.repo_structure.run import RepoStructureRunner

        runner = RepoStructureRunner()
        state = HarnessState()
        success = runner._run_validate(state)
        assert success

        facts_dir = tmp_path / "data/repo-structure/facts"
        assert facts_dir.exists()
        assert (facts_dir / "validated.v0.yaml").exists()


class TestBaseline:
    def test_baseline_produces_versioned_facts(self, tmp_path, monkeypatch):
        """baseline stage writes facts.vN.yaml as sole source-of-truth."""
        import yaml
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / "data/commit-extract").mkdir(parents=True)
        maps_dir = tmp_path / "data/repo-structure/maps"
        maps_dir.mkdir(parents=True)
        facts_dir = tmp_path / "data/repo-structure/facts"
        facts_dir.mkdir(parents=True)

        yaml.dump({
            "metadata": {"version": "v0"},
            "facts": [{"fact_id": "f1", "fact_type": "module_role",
                       "statement": "Test fact", "confidence": "confirmed",
                       "status": "active", "repo_snapshot_commit": "abc",
                       "source": "codebase",
                       "evidence": [{"source_type": "codebase", "locator_type": "symbol", "locator": "X", "stable_ref": "X"}]}],
            "conflicts": [],
        }, (facts_dir / "validated.v0.yaml").open("w"))

        from src.harness_state import HarnessState
        from skills.repo_structure.run import RepoStructureRunner

        runner = RepoStructureRunner()
        state = HarnessState()
        success = runner._run_baseline(state)
        assert success

        baseline_dir = tmp_path / "data/repo-structure/baseline"
        baseline_files = sorted(baseline_dir.glob("facts.v*.yaml"))
        assert len(baseline_files) >= 1

        data = yaml.safe_load(baseline_files[0].read_text())
        assert "facts" in data
        assert "metadata" in data
        assert "conflicts" in data
        assert data["metadata"]["version"].startswith("v")


class TestE2E:
    def test_full_pipeline_produces_baseline(self, tmp_path, monkeypatch):
        """Run full pipeline: sample -> hotspot -> extract -> augment -> validate -> baseline."""
        import yaml
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".git").mkdir()

        # Set up all required inputs
        (tmp_path / "data/commit-extract").mkdir(parents=True)
        (tmp_path / "data/commit-semantic/patterns").mkdir(parents=True)
        gsd_dir = tmp_path / ".planning/codebase"
        gsd_dir.mkdir(parents=True)

        for fname in ["STRUCTURE.md", "ARCHITECTURE.md", "CONCERNS.md",
                      "CONVENTIONS.md", "INTEGRATIONS.md", "STACK.md", "TESTING.md"]:
            (gsd_dir / fname).write_text(f"## Section\nTest content for {fname}.\n")

        # commit-extract artifact
        yaml.dump({"metadata": {"month": "2025-01"}, "commits": [
            {"commit_id": "abc", "files": ["src/hermes/registry.py", "src/hermes/registry.py"]}
        ]}, (tmp_path / "data/commit-extract/2025-01.yaml").open("w"))

        # commit-semantic patterns
        yaml.dump({"patterns": [{"pattern_id": "p1", "description": "Test pattern"}]},
                 (tmp_path / "data/commit-semantic/patterns/canonical.yaml").open("w"))

        from src.harness_state import HarnessState
        from skills.repo_structure.run import RepoStructureRunner

        runner = RepoStructureRunner()
        state = HarnessState()

        # Run all stages
        stages = ["sample", "hotspot", "extract", "augment", "validate", "baseline"]
        for stage in stages:
            success = runner.run_stage(stage, state)
            assert success, f"Stage {stage} failed"

        # Verify baseline
        baseline_dir = tmp_path / "data/repo-structure/baseline"
        assert baseline_dir.exists()
        baseline_files = sorted(baseline_dir.glob("facts.v*.yaml"))
        assert len(baseline_files) >= 1, f"No baseline facts found in {baseline_dir}"

        data = yaml.safe_load(baseline_files[0].read_text())
        assert "facts" in data
        assert "metadata" in data
        assert "conflicts" in data
        assert "version" in data["metadata"]
        assert data["metadata"]["version"].startswith("v")
        # Verify snapshot metadata
        assert "snapshot_version" in data["metadata"]
        assert "sources" in data["metadata"]
        # facts.latest.yaml should exist
        assert (baseline_dir / "facts.latest.yaml").exists()
        # snapshot.yaml should exist
        assert (baseline_dir / "snapshot.yaml").exists()
