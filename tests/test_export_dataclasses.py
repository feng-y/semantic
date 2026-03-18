"""Tests for CaseRecord/ExportSummary integration in the export pipeline."""
import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.types import CaseRecord, ExportSummary, DomainPatternStat, HighFrequencyPattern


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


def _make_pattern(pattern_id="p1", domain="backend", count=3):
    return {
        "pattern_id": pattern_id,
        "domain": domain,
        "count": count,
        "representative_issue_text": "Users cannot log in",
        "case_ids": [],
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
# generate_statistics integration test
# ---------------------------------------------------------------------------

class TestGenerateStatistics:
    """Test generate_statistics() returns ExportSummary with correct values."""

    def _run(self, unique_cases, duplicate_groups=None, patterns=None,
             pattern_count_status=None, tmp_path=None):
        # Import here so sys.path manipulation above takes effect
        import importlib, types as _types
        # We need to import the skill module; add its parent to path
        skill_path = Path(__file__).parent.parent / "skills" / "commit-semantic-export"
        sys.path.insert(0, str(skill_path))
        # Use importlib to avoid name collision with built-in 'types'
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_export",
            str(skill_path / "run.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        invalid_path = tmp_path / "invalid" if tmp_path else Path("/nonexistent_invalid")
        low_value_path = tmp_path / "low_value" if tmp_path else Path("/nonexistent_low_value")

        return mod.generate_statistics(
            unique_cases,
            duplicate_groups or [],
            patterns or [],
            pattern_count_status or {},
            invalid_path,
            low_value_path,
        )

    def test_returns_export_summary_instance(self, tmp_path):
        cases = [_make_case()]
        result = self._run(cases, tmp_path=tmp_path)
        assert isinstance(result, ExportSummary)

    def test_counts_are_correct(self, tmp_path):
        cases = [_make_case("c1"), _make_case("c2"), _make_case("c3", development_type="bugfix")]
        dup_groups = [{"duplicate_case_ids": ["d1", "d2"]}]
        result = self._run(cases, duplicate_groups=dup_groups, tmp_path=tmp_path)
        assert result.unique_cases == 3
        assert result.duplicate_cases == 2
        assert result.total_cases == 5  # 3 unique + 2 duplicates + 0 invalid

    def test_bugfix_ratio(self, tmp_path):
        cases = [
            _make_case("c1", development_type="bugfix"),
            _make_case("c2", development_type="bugfix"),
            _make_case("c3", development_type="feature"),
            _make_case("c4", development_type="feature"),
        ]
        result = self._run(cases, tmp_path=tmp_path)
        assert result.bugfix_count == 2
        assert abs(result.bugfix_ratio - 0.5) < 1e-9

    def test_needs_split_ratio(self, tmp_path):
        cases = [
            _make_case("c1", needs_split=True),
            _make_case("c2", needs_split=False),
        ]
        result = self._run(cases, tmp_path=tmp_path)
        assert result.needs_split_count == 1
        assert abs(result.needs_split_ratio - 0.5) < 1e-9

    def test_pattern_count_status_mapped(self, tmp_path):
        cases = [_make_case()]
        pcs = {
            "backend": {
                "pattern_count": 5,
                "pattern_count_status": "excellent",
                "action": "none",
            }
        }
        result = self._run(cases, pattern_count_status=pcs, tmp_path=tmp_path)
        assert "backend" in result.domain_pattern_stats
        assert result.domain_pattern_stats["backend"]["status"] == "excellent"

    def test_high_frequency_patterns_sorted(self, tmp_path):
        cases = [_make_case()]
        patterns = [
            _make_pattern("p1", count=1),
            _make_pattern("p2", count=10),
            _make_pattern("p3", count=5),
        ]
        result = self._run(cases, patterns=patterns, tmp_path=tmp_path)
        assert result.high_frequency_patterns[0]["pattern_id"] == "p2"
        assert result.high_frequency_patterns[1]["pattern_id"] == "p3"

    def test_asdict_output_is_json_serialisable(self, tmp_path):
        import json
        cases = [_make_case()]
        result = self._run(cases, tmp_path=tmp_path)
        json.dumps(dataclasses.asdict(result))  # must not raise

    def test_empty_cases(self, tmp_path):
        result = self._run([], tmp_path=tmp_path)
        assert result.total_cases == 0
        assert result.validation_pass_rate == 0
        assert result.bugfix_ratio == 0
        assert result.needs_split_ratio == 0
