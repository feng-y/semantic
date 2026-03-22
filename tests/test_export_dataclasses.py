"""Tests for CaseRecord/ExportSummary integration in the export pipeline."""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.types import CaseRecord, ExportSummary
from src.harness_state import HarnessState

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_case(
    case_id="c1",
    commit_id="abc123",
    module="auth",
    development_type="feature",
    domain="backend",
    needs_split=False,
):
    return {
        "case_id": case_id,
        "commit_id": commit_id,
        "module": module,
        "commit_log": "feat: add login",
        "issue_text": "Users cannot log in",
        "development_type": development_type,
        "domain": domain,
        "rules": [],
        "invariants": [],
        "split_suggestion": {"needs_split": needs_split, "split_reasons": []},
        "semantic_value": "high",
        "dedup_key": "",
        "pattern_id": "",
    }

# ---------------------------------------------------------------------------
# CaseRecord tests
# ---------------------------------------------------------------------------

class TestCaseRecord:
    def test_from_dict_roundtrip(self):
        d = _make_case()
        record = CaseRecord(**{f.name: d[f.name] for f in dataclasses.fields(CaseRecord)})
        assert record.case_id == "c1"

    def test_instantiation_minimal(self):
        record = CaseRecord(
            case_id="x",
            commit_id="y",
            module="m",
            commit_log="log",
            issue_text="issue",
            development_type="bugfix",
        )
        assert record.domain == ""
        assert record.rules == []
        assert record.split_suggestion == {}

    def test_asdict_produces_plain_dict(self):
        record = CaseRecord(
            case_id="x",
            commit_id="y",
            module="m",
            commit_log="log",
            issue_text="issue",
            development_type="feature",
        )
        d = dataclasses.asdict(record)
        assert isinstance(d, dict)
        assert d["case_id"] == "x"
        assert d["development_type"] == "feature"

    def test_field_names_match_jsonl_keys(self):
        """CaseRecord fields must match the keys written to cases.jsonl."""
        expected_keys = {
            "case_id", "commit_id", "module", "commit_log", "issue_text",
            "development_type", "domain", "rules", "invariants",
            "split_suggestion", "semantic_value", "dedup_key", "pattern_id",
        }
        actual_keys = {f.name for f in dataclasses.fields(CaseRecord)}
        assert actual_keys == expected_keys


# ---------------------------------------------------------------------------
# ExportSummary tests
# ---------------------------------------------------------------------------

class TestExportSummary:
    def _make_summary(self, **overrides):
        defaults = dict(
            total_cases=10,
            unique_cases=8,
            duplicate_cases=2,
            duplicate_groups=1,
            valid_cases=8,
            invalid_cases=0,
            low_value_cases=1,
            validation_pass_rate=0.8,
            development_type_distribution={"feature": 5, "bugfix": 3},
            bugfix_count=3,
            bugfix_ratio=0.375,
            needs_split_count=1,
            needs_split_ratio=0.125,
            pattern_count=4,
        )
        defaults.update(overrides)
        return ExportSummary(**defaults)

    def test_instantiation(self):
        s = self._make_summary()
        assert s.total_cases == 10
        assert s.unique_cases == 8

    def test_asdict_is_json_serialisable(self):
        import json
        s = self._make_summary()
        d = dataclasses.asdict(s)
        # Must not raise
        json.dumps(d)

    def test_asdict_keys_match_legacy_dict(self):
        """Keys produced by asdict must match the old generate_statistics() dict keys."""
        expected_keys = {
            "total_cases", "unique_cases", "duplicate_cases", "duplicate_groups",
            "valid_cases", "invalid_cases", "low_value_cases", "validation_pass_rate",
            "development_type_distribution", "bugfix_count", "bugfix_ratio",
            "needs_split_count", "needs_split_ratio", "pattern_count",
            "domain_pattern_stats", "high_frequency_patterns", "invalid_reason_top_n",
        }
        s = self._make_summary()
        assert set(dataclasses.asdict(s).keys()) == expected_keys

    def test_default_optional_fields(self):
        s = self._make_summary()
        assert s.domain_pattern_stats == {}
        assert s.high_frequency_patterns == []
        assert s.invalid_reason_top_n == {}


# ---------------------------------------------------------------------------
# _run_export integration tests
# ---------------------------------------------------------------------------

# Load the run module once via spec (avoids macOS case-insensitive import issues)
_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUN_SPEC = importlib.util.spec_from_file_location(
    "commit_semantic_run", str(_REPO_ROOT / "skills" / "commit-semantic" / "run.py")
)
_RUN_MOD = importlib.util.module_from_spec(_RUN_SPEC)
_RUN_SPEC.loader.exec_module(_RUN_MOD)
CommitSemanticRunner = _RUN_MOD.CommitSemanticRunner


class TestRunExport:
    """Test _run_export() generates correct ExportSummary output."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.semantic_dir = tmp_path / "data" / "commit-semantic"
        self.semantic_dir.mkdir(parents=True)
        # Monkey-patch SEMANTIC_OUTPUT to point to temp dir
        self._orig = _RUN_MOD.SEMANTIC_OUTPUT
        _RUN_MOD.SEMANTIC_OUTPUT = self.semantic_dir
        yield
        _RUN_MOD.SEMANTIC_OUTPUT = self._orig

    def _write_demands(self, demands):
        from src.io_utils import save_yaml
        save_yaml({
            "metadata": {"total_demands": len(demands)},
            "demands": demands,
        }, str(self.semantic_dir / "canonical-demands.yaml"))

    def test_returns_true_and_writes_summary_yaml(self):
        self._write_demands([
            {"commit_log": "feat: add login", "module": "auth", "score": 8, "demand_id": "auth-01"},
            {"commit_log": "fix: login bug", "module": "auth", "score": 7, "demand_id": "auth-02"},
        ])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        assert (self.semantic_dir / "summary.yaml").exists()

    def test_counts_feature_and_bugfix_correctly(self):
        self._write_demands([
            {"commit_log": "feat: add feature", "module": "auth", "score": 8, "demand_id": "auth-01"},
            {"commit_log": "fix: bug", "module": "auth", "score": 7, "demand_id": "auth-02"},
            {"commit_log": "refactor: clean up", "module": "api", "score": 6, "demand_id": "api-01"},
            {"commit_log": "some other message", "module": "api", "score": 5, "demand_id": "api-02"},
        ])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        from src.io_utils import load_yaml
        summary = load_yaml(str(self.semantic_dir / "summary.yaml"))
        assert summary["bugfix_count"] == 1
        assert summary["development_type_distribution"]["feature"] == 1
        assert summary["development_type_distribution"]["bugfix"] == 1
        assert summary["development_type_distribution"]["refactor"] == 1
        assert summary["development_type_distribution"]["other"] == 1

    def test_bugfix_ratio_calculation(self):
        self._write_demands([
            {"commit_log": "fix: bug1", "module": "a", "score": 8, "demand_id": "a-01"},
            {"commit_log": "fix: bug2", "module": "b", "score": 8, "demand_id": "b-01"},
            {"commit_log": "feat: feat1", "module": "c", "score": 8, "demand_id": "c-01"},
            {"commit_log": "feat: feat2", "module": "d", "score": 8, "demand_id": "d-01"},
        ])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        from src.io_utils import load_yaml
        summary = load_yaml(str(self.semantic_dir / "summary.yaml"))
        assert summary["bugfix_count"] == 2
        assert abs(summary["bugfix_ratio"] - 0.5) < 1e-9
        assert summary["pattern_count"] == 4

    def test_empty_demands_produces_valid_summary(self):
        """Empty demands file is valid — returns True and produces zero-count summary."""
        self._write_demands([])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        assert (self.semantic_dir / "summary.yaml").exists()
        from src.io_utils import load_yaml
        summary = load_yaml(str(self.semantic_dir / "summary.yaml"))
        assert summary["total_cases"] == 0
        assert summary["bugfix_count"] == 0

    def test_summary_yaml_is_json_serializable(self):
        self._write_demands([
            {"commit_log": "feat: test", "module": "auth", "score": 8, "demand_id": "auth-01"},
        ])
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState())
        from src.io_utils import load_yaml
        summary = load_yaml(str(self.semantic_dir / "summary.yaml"))
        json.dumps(summary)  # must not raise
        assert isinstance(summary, dict)
        assert "total_cases" in summary
        assert "bugfix_ratio" in summary

    def test_high_frequency_patterns_sorted_by_count(self):
        self._write_demands([
            {"commit_log": "feat: a", "module": "auth", "score": 8, "demand_id": "auth-01"},
            {"commit_log": "feat: b", "module": "auth", "score": 8, "demand_id": "auth-02"},
            {"commit_log": "feat: c", "module": "auth", "score": 8, "demand_id": "auth-03"},
            {"commit_log": "feat: d", "module": "api", "score": 8, "demand_id": "api-01"},
        ])
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState())
        from src.io_utils import load_yaml
        summary = load_yaml(str(self.semantic_dir / "summary.yaml"))
        hfp = summary["high_frequency_patterns"]
        # auth (3) should come before api (1)
        assert len(hfp) >= 1
        if len(hfp) >= 2:
            assert hfp[0]["pattern_id"] == "auth"
            assert hfp[0]["count"] == 3
