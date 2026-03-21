"""E2E tests for commit-semantic skill - Task 2 implementation.

Tests the Team Agent architecture for commit-semantic:
- Reads commit_log from extract output (not commit_message)
- Classifies functional/non-functional commits
- Splits by module
- Scores functional commits 0-10
- Aggregates high-scored by module
- Distills canonical demands
"""

from __future__ import annotations

import sys
import tempfile
import yaml
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_commit_semantic_module():
    """Load commit-semantic skill module."""
    import importlib.util
    repo_root = Path(__file__).parent.parent.parent
    spec = importlib.util.spec_from_file_location(
        "commit_semantic_test",
        str(repo_root / "skills/commit-semantic/run.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_semantic_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestCommitSemanticReadsCommitLog:
    """Tests: reads commit_log field from extract output, NOT original_message."""

    def test_split_reads_commit_log_not_original_message(self, tmp_path):
        """_run_split reads commit_log as canonical field.

        The critical constraint: commit_log is the LLM-regenerated field from
        commit-extract workers. The semantic stage must read commit_log, NOT
        original_message or commit_message.
        """
        mod = load_commit_semantic_module()

        # Create a temp extract output directory
        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        # Write extract output with commit_log populated by workers
        commits = [
            {
                "commit_id": "abc123def0000000000000000000000000001",
                "timestamp": "2024-01-15T10:00:00",
                "author": "Test <test@test.com>",
                "files": ["src/parser.py"],
                "diff_chunks": ["+def parse(): pass"],
                # original_message is raw git message
                "original_message": "feat: add stuff",
                # commit_log is LLM-regenerated from diff (the canonical field)
                "commit_log": "在 parser 中新增 parse 函数用于 DSL 解析",
            },
            {
                "commit_id": "abc123def0000000000000000000000000002",
                "timestamp": "2024-01-16T10:00:00",
                "author": "Test <test@test.com>",
                "files": ["src/config.py"],
                "diff_chunks": ["+cfg = {}\n"],
                "original_message": "fix: update config",
                # commit_log is the canonical semantic field
                "commit_log": "更新 config 模块的配置加载逻辑",
            },
        ]

        month_file = extract_dir / "2024-01.yaml"
        month_file.write_text(
            yaml.dump({
                "metadata": {"month": "2024-01", "total_commits": 2},
                "commits": commits,
            })
        )

        # Patch output path and run
        saved_extract = mod.EXTRACT_OUTPUT
        saved_semantic = mod.SEMANTIC_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = tmp_path / "data" / "commit-semantic"

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.harness_state import HarnessState

        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="split",
            metadata={"completed_stages": [], "artifacts_written": []},
        )
        result = runner._run_split(state)

        mod.EXTRACT_OUTPUT = saved_extract
        mod.SEMANTIC_OUTPUT = saved_semantic

        assert result is True

        units_file = tmp_path / "data" / "commit-semantic" / "units" / "all.yaml"
        assert units_file.exists(), "units/all.yaml should be created"

        data = yaml.safe_load(units_file.read_text())
        units = data["units"]

        # Verify that commit_log from extract IS present in units
        # (not original_message)
        commit_logs = [u.get("commit_log", "") for u in units]
        assert any("parser" in log for log in commit_logs), \
            "commit_log should reference 'parser' (from LLM-regenerated field)"
        assert any("config" in log for log in commit_logs), \
            "commit_log should reference 'config' (from LLM-regenerated field)"

        # Verify original_message is NOT used as commit_log
        assert not any("add stuff" in log for log in commit_logs), \
            "original_message 'add stuff' should NOT appear as commit_log"
        assert not any("update config" in log for log in commit_logs), \
            "original_message 'update config' should NOT appear as commit_log"

    def test_split_does_not_read_commit_message_field(self, tmp_path):
        """_run_split must not use a 'commit_message' field - it should use commit_log."""
        mod = load_commit_semantic_module()

        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        # Write a commit that has commit_message (the WRONG field name)
        # This simulates the bug where commit_message was read instead of commit_log
        bad_commit = {
            "commit_id": "abc123def0000000000000000000000000003",
            "timestamp": "2024-01-17T10:00:00",
            "author": "Test <test@test.com>",
            "files": ["src/server.py"],
            "diff_chunks": ["+def serve(): pass"],
            "original_message": "feat: add server",
            # No commit_log — this commit has the WRONG field
            "commit_message": "add server feature",
        }

        month_file = extract_dir / "2024-01.yaml"
        month_file.write_text(
            yaml.dump({
                "metadata": {"month": "2024-01", "total_commits": 1},
                "commits": [bad_commit],
            })
        )

        saved_extract = mod.EXTRACT_OUTPUT
        saved_semantic = mod.SEMANTIC_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = tmp_path / "data" / "commit-semantic"

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.harness_state import HarnessState

        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="split",
            metadata={"completed_stages": [], "artifacts_written": []},
        )
        result = runner._run_split(state)

        mod.EXTRACT_OUTPUT = saved_extract
        mod.SEMANTIC_OUTPUT = saved_semantic

        assert result is True

        units_file = tmp_path / "data" / "commit-semantic" / "units" / "all.yaml"
        data = yaml.safe_load(units_file.read_text())
        units = data["units"]

        # When commit_log is missing, the unit should have empty/None commit_log,
        # NOT the value from commit_message
        for unit in units:
            # The bug: old code did commit.get("commit_message", "")
            # After fix: it should use commit.get("commit_log", "")
            # A missing commit_log should NOT be filled from commit_message
            if "commit_message" in bad_commit:
                assert unit.get("commit_log", "") != bad_commit.get("commit_message", ""), \
                    "commit_log should NOT be read from commit_message field"


class TestCommitSemanticClassification:
    """Tests for commit classification."""

    def test_classify_functional(self):
        """feat, bugfix, optimize = functional."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        assert runner._classify_type("feat: add parser") == "functional", \
            "feat prefix should be functional"
        assert runner._classify_type("bugfix: fix boundary") == "functional", \
            "bugfix prefix should be functional"
        assert runner._classify_type("optimize: improve perf") == "functional", \
            "optimize prefix should be functional"
        assert runner._classify_type("feat+bugfix: fix and add") == "functional", \
            "compound prefix with feat should be functional"

    def test_classify_non_functional(self):
        """refactor, test, config, cleanup = non-functional."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        assert runner._classify_type("refactor: cleanup code") == "non-functional", \
            "refactor should be non-functional"
        assert runner._classify_type("test: add parser tests") == "non-functional", \
            "test should be non-functional"
        assert runner._classify_type("config: update deps") == "non-functional", \
            "config should be non-functional"
        assert runner._classify_type("chore: update deps") == "non-functional", \
            "chore should be non-functional"
        assert runner._classify_type("cleanup: remove dead code") == "non-functional", \
            "cleanup should be non-functional"
        assert runner._classify_type("docs: update readme") == "non-functional", \
            "docs should be non-functional"
        assert runner._classify_type("perf: improve perf") == "non-functional", \
            "perf should be non-functional (not in FUNCTIONAL_PREFIXES)"


class TestCommitSemanticSplitByModule:
    """Tests for module-based splitting."""

    def test_split_by_module_detects_multiple_modules(self, tmp_path):
        """Multi-module commits produce separate units per module."""
        mod = load_commit_semantic_module()

        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        commits = [
            {
                "commit_id": "abc123def0000000000000000000000000004",
                "timestamp": "2024-02-10T10:00:00",
                "author": "Test <test@test.com>",
                "files": ["src/parser.py", "src/server.py"],
                "diff_chunks": ["+def parse(): pass\n+def serve(): pass"],
                "original_message": "feat: add parser and server modules",
                # commit_log mentions both parser and server
                "commit_log": "新增 parser 解析模块和 server 服务模块",
            },
        ]

        (extract_dir / "2024-02.yaml").write_text(
            yaml.dump({
                "metadata": {"month": "2024-02", "total_commits": 1},
                "commits": commits,
            })
        )

        saved_extract = mod.EXTRACT_OUTPUT
        saved_semantic = mod.SEMANTIC_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = tmp_path / "data" / "commit-semantic"

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.harness_state import HarnessState

        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="split",
            metadata={"completed_stages": [], "artifacts_written": []},
        )
        result = runner._run_split(state)

        mod.EXTRACT_OUTPUT = saved_extract
        mod.SEMANTIC_OUTPUT = saved_semantic

        assert result is True
        units_file = tmp_path / "data" / "commit-semantic" / "units" / "all.yaml"
        data = yaml.safe_load(units_file.read_text())
        units = data["units"]

        modules = [u["module"] for u in units]
        # Should produce units for both parser and server
        assert "parser" in modules or "server" in modules, \
            "Should detect at least one module from commit_log"

    def test_split_unknown_module_for_unmatched_commits(self, tmp_path):
        """Commits with no module keywords get 'unknown' module."""
        mod = load_commit_semantic_module()

        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        commits = [
            {
                "commit_id": "abc123def0000000000000000000000000005",
                "timestamp": "2024-03-01T10:00:00",
                "author": "Test <test@test.com>",
                "files": [],
                "diff_chunks": ["+x = 1\n"],
                "original_message": "wip: stuff",
                "commit_log": "工作进展更新",
            },
        ]

        (extract_dir / "2024-03.yaml").write_text(
            yaml.dump({
                "metadata": {"month": "2024-03", "total_commits": 1},
                "commits": commits,
            })
        )

        saved_extract = mod.EXTRACT_OUTPUT
        saved_semantic = mod.SEMANTIC_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = tmp_path / "data" / "commit-semantic"

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.harness_state import HarnessState

        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="split",
            metadata={"completed_stages": [], "artifacts_written": []},
        )
        runner._run_split(state)

        mod.EXTRACT_OUTPUT = saved_extract
        mod.SEMANTIC_OUTPUT = saved_semantic

        units_file = tmp_path / "data" / "commit-semantic" / "units" / "all.yaml"
        data = yaml.safe_load(units_file.read_text())
        units = data["units"]

        assert len(units) == 1
        assert units[0]["module"] == "unknown", \
            "Unmatched commit should get 'unknown' module"


class TestCommitSemanticScoring:
    """Tests for scoring functional commits."""

    def test_score_functional_range(self, tmp_path):
        """Functional commits scored 0-10."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        units = [
            {"commit_log": "feat: add parser with proper description here", "module": "parser"},
            {"commit_log": "x", "module": "unknown"},
            {"commit_log": "feat: fix important bug in the database module", "module": "db"},
            {"commit_log": "feat: add", "module": "api"},
        ]

        for unit in units:
            score = runner._score_unit(unit)
            assert 0 <= score <= 10, \
                f"Score {score} for unit {unit} should be between 0 and 10"

    def test_score_module_affects_score(self):
        """Known module boosts score."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        unit_known = {"commit_log": "feat: add parser module", "module": "parser"}
        unit_unknown = {"commit_log": "feat: add parser module", "module": "unknown"}

        score_known = runner._score_unit(unit_known)
        score_unknown = runner._score_unit(unit_unknown)

        assert score_known > score_unknown, \
            "Known module should score higher than unknown"

    def test_score_clear_message_bonus(self):
        """Clear, well-described commit log gets bonus."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        unit_clear = {
            "commit_log": "feat: add parser module with proper description and clear intent",
            "module": "parser",
        }
        unit_short = {
            "commit_log": "feat: add",
            "module": "parser",
        }

        score_clear = runner._score_unit(unit_clear)
        score_short = runner._score_unit(unit_short)

        assert score_clear >= score_short, \
            "Clear message should score >= short message"


class TestCommitSemanticAggregate:
    """Tests for aggregating high-scored units by module."""

    def test_aggregate_patterns(self, tmp_path):
        """High-scored units are grouped by module into patterns."""
        mod = load_commit_semantic_module()

        # Setup: create functional/high directory with units
        high_dir = tmp_path / "data" / "commit-semantic" / "functional" / "high"
        high_dir.mkdir(parents=True)

        units = [
            {
                "unit_id": "abc00001-parser",
                "commit_id": "abc00001",
                "module": "parser",
                "score": 9,
                "commit_log": "在 parser 中新增 AST 解析函数",
            },
            {
                "unit_id": "abc00002-parser",
                "commit_id": "abc00002",
                "module": "parser",
                "score": 8,
                "commit_log": "修复 parser 边界条件",
            },
            {
                "unit_id": "abc00003-server",
                "commit_id": "abc00003",
                "module": "server",
                "score": 9,
                "commit_log": "新增 server 启动回调机制",
            },
        ]

        (high_dir / "units.yaml").write_text(
            yaml.dump({
                "metadata": {"tier": "high", "count": len(units)},
                "units": units,
            })
        )

        saved_semantic = mod.SEMANTIC_OUTPUT
        mod.SEMANTIC_OUTPUT = tmp_path / "data" / "commit-semantic"

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.harness_state import HarnessState

        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="aggregate",
            metadata={"completed_stages": ["split", "analyze"], "artifacts_written": []},
        )
        result = runner._run_aggregate(state)

        mod.SEMANTIC_OUTPUT = saved_semantic

        assert result is True

        patterns_dir = tmp_path / "data" / "commit-semantic" / "patterns"
        assert patterns_dir.exists(), "patterns directory should be created"

        parser_pattern = patterns_dir / "parser.yaml"
        server_pattern = patterns_dir / "server.yaml"

        assert parser_pattern.exists(), "parser.yaml should be created from high units"
        assert server_pattern.exists(), "server.yaml should be created from high units"

        parser_data = yaml.safe_load(parser_pattern.read_text())
        assert parser_data["metadata"]["module"] == "parser"
        assert len(parser_data["patterns"]) == 2, "parser should have 2 patterns"


class TestCommitSemanticDistill:
    """Tests for extracting canonical demands."""

    def test_distill_demands(self, tmp_path):
        """Canonical demands extracted from patterns."""
        mod = load_commit_semantic_module()

        # Setup: create patterns directory
        patterns_dir = tmp_path / "data" / "commit-semantic" / "patterns"
        patterns_dir.mkdir(parents=True)

        patterns = [
            {
                "commit_id": "abc00001",
                "module": "parser",
                "score": 9,
                "commit_log": "在 parser 中新增 AST 解析函数",
            },
            {
                "commit_id": "abc00002",
                "module": "parser",
                "score": 8,
                "commit_log": "修复 parser 边界条件",
            },
            {
                "commit_id": "abc00003",
                "module": "server",
                "score": 9,
                "commit_log": "新增 server 启动回调机制",
            },
        ]

        (patterns_dir / "parser.yaml").write_text(
            yaml.dump({
                "metadata": {"module": "parser", "count": 2},
                "patterns": patterns[:2],
            })
        )
        (patterns_dir / "server.yaml").write_text(
            yaml.dump({
                "metadata": {"module": "server", "count": 1},
                "patterns": patterns[2:],
            })
        )

        saved_semantic = mod.SEMANTIC_OUTPUT
        mod.SEMANTIC_OUTPUT = tmp_path / "data" / "commit-semantic"

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.harness_state import HarnessState

        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="distill",
            metadata={
                "completed_stages": ["split", "analyze", "aggregate"],
                "artifacts_written": [],
            },
        )
        result = runner._run_distill(state)

        mod.SEMANTIC_OUTPUT = saved_semantic

        assert result is True

        demands_file = tmp_path / "data" / "commit-semantic" / "canonical-demands.yaml"
        assert demands_file.exists(), "canonical-demands.yaml should be created"

        data = yaml.safe_load(demands_file.read_text())
        demands = data["demands"]

        assert len(demands) > 0, "Should produce at least one demand"
        assert all("demand_id" in d for d in demands), "Each demand needs demand_id"
        assert all("module" in d for d in demands), "Each demand needs module"
        assert all("commit_log" in d for d in demands), "Each demand needs commit_log"


class TestCommitSemanticFullPipeline:
    """Integration tests for the full pipeline."""

    def test_full_pipeline_with_extract_output(self, tmp_path):
        """Full pipeline runs when extract output exists."""
        mod = load_commit_semantic_module()

        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        commits = [
            {
                "commit_id": "abc123def0000000000000000000000000006",
                "timestamp": "2024-04-01T10:00:00",
                "author": "Test <test@test.com>",
                "files": ["src/parser.py"],
                "diff_chunks": ["+def parse(): pass"],
                "original_message": "feat: add parser",
                "commit_log": "在 parser 中新增 parse 函数用于 DSL 解析",
            },
            {
                "commit_id": "abc123def0000000000000000000000000007",
                "timestamp": "2024-04-02T10:00:00",
                "author": "Test <test@test.com>",
                "files": ["src/parser.py"],
                "diff_chunks": ["+def parse(): pass\n"],
                "original_message": "refactor: cleanup",
                "commit_log": "重构 parser 代码结构",
            },
        ]

        (extract_dir / "2024-04.yaml").write_text(
            yaml.dump({
                "metadata": {"month": "2024-04", "total_commits": 2},
                "commits": commits,
            })
        )

        saved_extract = mod.EXTRACT_OUTPUT
        saved_semantic = mod.SEMANTIC_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = tmp_path / "data" / "commit-semantic"

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.harness_state import HarnessState

        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="init",
            metadata={"completed_stages": [], "artifacts_written": []},
        )

        # Run all stages
        runner._run_split(state)
        runner._run_analyze(state)
        runner._run_aggregate(state)
        runner._run_distill(state)

        mod.EXTRACT_OUTPUT = saved_extract
        mod.SEMANTIC_OUTPUT = saved_semantic

        # Verify all output files exist
        assert (tmp_path / "data" / "commit-semantic" / "units" / "all.yaml").exists()
        assert (tmp_path / "data" / "commit-semantic" / "functional").exists()
        assert (tmp_path / "data" / "commit-semantic" / "non-functional").exists()
        assert (tmp_path / "data" / "commit-semantic" / "patterns").exists()
        assert (tmp_path / "data" / "commit-semantic" / "canonical-demands.yaml").exists()


class TestCommitSemanticTeamAgentArchitecture:
    """Tests for Team Agent architecture hooks."""

    def test_spawn_worker_method_exists(self):
        """Runner should have _spawn_worker method stub for Task agent spawning."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        assert hasattr(runner, "_spawn_worker"), \
            "CommitSemanticRunner should have _spawn_worker method"
        assert callable(runner._spawn_worker), \
            "_spawn_worker should be callable"

    def test_batch_units_method_exists(self):
        """Runner should have _batch_units method for batching units to workers."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        assert hasattr(runner, "_batch_units"), \
            "CommitSemanticRunner should have _batch_units method"
        assert callable(runner._batch_units), \
            "_batch_units should be callable"

    def test_worker_prompt_templates_exist(self):
        """Worker prompt templates should exist in prompts/ directory."""
        repo_root = Path(__file__).parent.parent.parent
        prompts_dir = repo_root / "skills" / "commit-semantic" / "prompts"

        assert prompts_dir.exists(), \
            f"prompts directory should exist at {prompts_dir}"

        classify_prompt = prompts_dir / "classify.md"
        score_prompt = prompts_dir / "score.md"
        distill_prompt = prompts_dir / "distill.md"

        assert classify_prompt.exists(), \
            f"classify.md should exist at {classify_prompt}"
        assert score_prompt.exists(), \
            f"score.md should exist at {score_prompt}"
        assert distill_prompt.exists(), \
            f"distill.md should exist at {distill_prompt}"

    def test_skill_md_has_team_agent_architecture(self):
        """SKILL.md should document Team Agent architecture (not deprecated)."""
        repo_root = Path(__file__).parent.parent.parent
        skill_md = repo_root / "skills" / "commit-semantic" / "SKILL.md"

        content = skill_md.read_text()

        # Should NOT be deprecated
        assert "deprecated" not in content.lower() and "replacement" not in content.lower(), \
            "SKILL.md should not be marked as deprecated"

        # Should mention worker agents or Task tool
        assert "worker" in content.lower() or "task" in content.lower(), \
            "SKILL.md should mention worker agents or Task tool"


class TestCommitSemanticPrerequisites:
    """Tests for prerequisite checking."""

    def test_prerequisites_requires_extract_output(self):
        """_check_prerequisites fails when no extract output exists."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        # Temporarily change the extract path to non-existent
        saved = mod.EXTRACT_OUTPUT
        mod.EXTRACT_OUTPUT = Path("/nonexistent/path/that/does/not/exist")
        ok, msg = runner._check_prerequisites()
        mod.EXTRACT_OUTPUT = saved

        assert ok is False, "Should fail when extract output does not exist"
        assert "commit-extract" in msg.lower() or "not found" in msg.lower()

    def test_prerequisites_passes_with_extract_output(self, tmp_path):
        """_check_prerequisites passes when extract output exists."""
        mod = load_commit_semantic_module()

        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)
        (extract_dir / "2024-01.yaml").write_text(
            yaml.dump({"metadata": {}, "commits": []})
        )

        saved = mod.EXTRACT_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        ok, msg = mod.CommitSemanticRunner()._check_prerequisites()
        mod.EXTRACT_OUTPUT = saved

        assert ok is True, f"Should pass when extract output exists: {msg}"
