"""Tests for CaseRecord/ExportSummary dataclasses + new _run_export integration."""

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
        expected_keys = {
            "case_id", "commit_id", "module", "commit_log", "issue_text",
            "development_type", "domain", "rules", "invariants",
            "split_suggestion", "semantic_value", "dedup_key", "pattern_id",
        }
        actual_keys = {f.name for f in dataclasses.fields(CaseRecord)}
        assert actual_keys == expected_keys


# ---------------------------------------------------------------------------
# ExportSummary tests (dataclass still exists for backward compat)
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
        s = self._make_summary()
        d = dataclasses.asdict(s)
        json.dumps(d)

    def test_asdict_keys_match_legacy_dict(self):
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
# _run_export integration tests (new 4-stage pipeline)
# ---------------------------------------------------------------------------

_RUN_SPEC = importlib.util.spec_from_file_location(
    "commit_semantic_run", str(REPO_ROOT / "skills" / "commit-semantic" / "run.py")
)
_RUN_MOD = importlib.util.module_from_spec(_RUN_SPEC)
_RUN_SPEC.loader.exec_module(_RUN_MOD)
CommitSemanticRunner = _RUN_MOD.CommitSemanticRunner


class TestRunExport:
    """Test _run_export() generates correct summary.json output."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.semantic_dir = tmp_path / "data" / "commit-semantic"
        self.semantic_dir.mkdir(parents=True)
        (self.semantic_dir / "units").mkdir(parents=True)
        self._orig = _RUN_MOD.SEMANTIC_OUTPUT
        _RUN_MOD.SEMANTIC_OUTPUT = self.semantic_dir
        yield
        _RUN_MOD.SEMANTIC_OUTPUT = self._orig

    def _write_fixtures(self, units, patterns=None, demands=None, invariants=None):
        from src.io_utils import save_jsonl
        save_jsonl(units, str(self.semantic_dir / "units" / "all.jsonl"))
        save_jsonl(patterns or [], str(self.semantic_dir / "patterns.jsonl"))
        save_jsonl(demands or [], str(self.semantic_dir / "canonical-demands.jsonl"))
        save_jsonl(invariants or [], str(self.semantic_dir / "invariants.jsonl"))

    def test_returns_true_and_writes_summary_json(self):
        self._write_fixtures([
            {"sha": "a", "date": "2026-03-01", "op": "feat", "summary": "add login"},
            {"sha": "b", "date": "2026-03-02", "op": "bugfix", "summary": "fix bug"},
        ])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        assert (self.semantic_dir / "summary.json").exists()

    def test_counts_ops_correctly(self):
        self._write_fixtures([
            {"sha": "a", "date": "2026-03-01", "op": "feat", "summary": "s1"},
            {"sha": "b", "date": "2026-03-02", "op": "bugfix", "summary": "s2"},
            {"sha": "c", "date": "2026-03-03", "op": "refactor", "summary": "s3"},
            {"sha": "d", "date": "2026-03-04", "op": "other", "summary": "s4"},
        ])
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState())
        from src.io_utils import load_json
        summary = load_json(str(self.semantic_dir / "summary.json"))
        assert summary["op_distribution"]["feat"] == 1
        assert summary["op_distribution"]["bugfix"] == 1
        assert summary["op_distribution"]["refactor"] == 1

    def test_bugfix_ratio_calculation(self):
        self._write_fixtures([
            {"sha": "a", "date": "2026-03-01", "op": "bugfix", "summary": "s1"},
            {"sha": "b", "date": "2026-03-02", "op": "bugfix", "summary": "s2"},
            {"sha": "c", "date": "2026-03-03", "op": "feat", "summary": "s3"},
            {"sha": "d", "date": "2026-03-04", "op": "feat", "summary": "s4"},
        ])
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState())
        from src.io_utils import load_json
        summary = load_json(str(self.semantic_dir / "summary.json"))
        assert abs(summary["bugfix_ratio"] - 0.5) < 1e-9

    def test_empty_units_produces_valid_summary(self):
        self._write_fixtures([])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        assert (self.semantic_dir / "summary.json").exists()
        from src.io_utils import load_json
        summary = load_json(str(self.semantic_dir / "summary.json"))
        assert summary["total_units"] == 0

    def test_summary_json_is_json_serializable(self):
        self._write_fixtures([
            {"sha": "a", "date": "2026-03-01", "op": "feat", "summary": "s1"},
        ])
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState())
        from src.io_utils import load_json
        summary = load_json(str(self.semantic_dir / "summary.json"))
        json.dumps(summary)  # must not raise
        assert "total_units" in summary
        assert "bugfix_ratio" in summary

    def test_top_patterns_in_summary(self):
        self._write_fixtures(
            units=[{"sha": "a", "date": "2026-03-01", "op": "feat", "summary": "s1"}],
            demands=[
                {"theme": "auth", "score": 10.0, "distinct_commits": 5, "rank": 1},
                {"theme": "api", "score": 8.0, "distinct_commits": 4, "rank": 2},
            ],
        )
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState())
        from src.io_utils import load_json
        summary = load_json(str(self.semantic_dir / "summary.json"))
        top = summary["top_patterns"]
        assert len(top) == 2
        assert top[0]["theme"] == "auth"
        assert top[0]["score"] == 10.0
