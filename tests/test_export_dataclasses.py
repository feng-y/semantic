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
# _run_export integration tests (new JSONL-based pipeline)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUN_SPEC = importlib.util.spec_from_file_location(
    "commit_semantic_run", str(_REPO_ROOT / "skills" / "commit-semantic" / "run.py")
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
        self._orig = _RUN_MOD.SEMANTIC_OUTPUT
        _RUN_MOD.SEMANTIC_OUTPUT = self.semantic_dir
        yield
        _RUN_MOD.SEMANTIC_OUTPUT = self._orig

    def _write_demands(self, demands):
        """Write canonical-demands.jsonl."""
        demands_file = self.semantic_dir / "canonical-demands.jsonl"
        with open(demands_file, "w", encoding="utf-8") as f:
            for d in demands:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

    def _write_units(self, units):
        """Write units/all.jsonl."""
        units_dir = self.semantic_dir / "units"
        units_dir.mkdir(parents=True, exist_ok=True)
        with open(units_dir / "all.jsonl", "w", encoding="utf-8") as f:
            for u in units:
                f.write(json.dumps(u, ensure_ascii=False) + "\n")

    def _write_invariants(self, invariants):
        """Write invariants.jsonl."""
        with open(self.semantic_dir / "invariants.jsonl", "w", encoding="utf-8") as f:
            for inv in invariants:
                f.write(json.dumps(inv, ensure_ascii=False) + "\n")

    def _make_unit(self, op="feat", date="2024-01-15T10:00:00"):
        return {
            "sha": "abc123", "date": date, "author": "Test",
            "section_name": "Runtime", "theme": "auth",
            "importance": "primary", "op": op, "summary": "test",
            "is_large_aggregate": False, "is_mixed": False,
        }

    def test_returns_true_and_writes_summary_json(self):
        self._write_demands([
            {"theme": "auth", "score": 8.0, "distinct_commits": 2, "count": 2,
             "op_distribution": {"feat": 1, "bugfix": 1}, "importance_ratio": {"primary": 2},
             "representative_summaries": ["a", "b"], "rank": 1},
        ])
        self._write_units([self._make_unit(), self._make_unit(op="bugfix")])
        self._write_invariants([])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        assert (self.semantic_dir / "summary.json").exists()

    def test_counts_ops_correctly(self):
        self._write_demands([
            {"theme": "auth", "score": 8.0, "distinct_commits": 2, "count": 4,
             "op_distribution": {"feat": 1, "bugfix": 1, "refactor": 1, "other": 1},
             "importance_ratio": {"primary": 4}, "representative_summaries": [],
             "rank": 1},
        ])
        self._write_units([
            self._make_unit(op="feat"),
            self._make_unit(op="bugfix"),
            self._make_unit(op="refactor"),
            self._make_unit(op="other"),
        ])
        self._write_invariants([])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        summary = json.loads((self.semantic_dir / "summary.json").read_text())
        assert summary["op_distribution"]["feat"] == 1
        assert summary["op_distribution"]["bugfix"] == 1
        assert summary["op_distribution"]["refactor"] == 1

    def test_bugfix_ratio_calculation(self):
        self._write_demands([
            {"theme": "a", "score": 8.0, "distinct_commits": 1, "count": 4,
             "op_distribution": {}, "importance_ratio": {}, "representative_summaries": [],
             "rank": 1},
        ])
        self._write_units([
            self._make_unit(op="bugfix"),
            self._make_unit(op="bugfix"),
            self._make_unit(op="feat"),
            self._make_unit(op="feat"),
        ])
        self._write_invariants([])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        summary = json.loads((self.semantic_dir / "summary.json").read_text())
        assert abs(summary["bugfix_ratio"] - 0.5) < 1e-9

    def test_empty_demands_returns_false(self):
        """No canonical-demands.jsonl file -> returns False."""
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is False

    def test_summary_json_is_valid(self):
        self._write_demands([
            {"theme": "auth", "score": 8.0, "distinct_commits": 1, "count": 1,
             "op_distribution": {"feat": 1}, "importance_ratio": {"primary": 1},
             "representative_summaries": ["test"], "rank": 1},
        ])
        self._write_units([self._make_unit()])
        self._write_invariants([])
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState())
        summary = json.loads((self.semantic_dir / "summary.json").read_text())
        assert isinstance(summary, dict)
        assert "total_units" in summary
        assert "bugfix_ratio" in summary
        assert "total_patterns" in summary

    def test_top_patterns_from_demands(self):
        demands = [
            {"theme": f"theme{i}", "score": 10.0 - i, "distinct_commits": 5 - i,
             "count": 3, "op_distribution": {"feat": 3},
             "importance_ratio": {"primary": 3}, "representative_summaries": [],
             "rank": i + 1}
            for i in range(3)
        ]
        self._write_demands(demands)
        self._write_units([self._make_unit() for _ in range(3)])
        self._write_invariants([])
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState())
        summary = json.loads((self.semantic_dir / "summary.json").read_text())
        top = summary["top_patterns"]
        assert len(top) == 3
        assert top[0]["theme"] == "theme0"
