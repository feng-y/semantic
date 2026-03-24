"""Tests for CaseRecord/ExportSummary dataclasses + commit-semantic V1 summary export."""

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
from src.io_utils import save_jsonl

REPO_ROOT = Path(__file__).resolve().parent.parent


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


_RUN_SPEC = importlib.util.spec_from_file_location(
    "commit_semantic_run", str(REPO_ROOT / "skills" / "commit-semantic" / "run.py")
)
_RUN_MOD = importlib.util.module_from_spec(_RUN_SPEC)
_RUN_SPEC.loader.exec_module(_RUN_MOD)
CommitSemanticRunner = _RUN_MOD.CommitSemanticRunner


class TestRunExport:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.semantic_dir = tmp_path / "data" / "commit-semantic"
        self.semantic_dir.mkdir(parents=True)
        self._orig = _RUN_MOD.SEMANTIC_OUTPUT
        _RUN_MOD.SEMANTIC_OUTPUT = self.semantic_dir
        yield
        _RUN_MOD.SEMANTIC_OUTPUT = self._orig

    def _write_fixtures(self, candidates=None, stable=None):
        save_jsonl(candidates or [], str(self.semantic_dir / "capabilities-candidates.jsonl"))
        save_jsonl(stable or [], str(self.semantic_dir / "capabilities.jsonl"))

    def test_returns_true_and_writes_summary_json(self):
        self._write_fixtures(
            candidates=[
                {"capability_id": "cap-a", "canonical_name": "a", "evidence_refs": ["sha:a"], "confidence": "high"},
            ],
            stable=[
                {"capability_id": "cap-a", "canonical_name": "a", "evidence_refs": ["sha:a"], "confidence": "high"},
            ],
        )
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState(metadata={"signal_count": 1}))
        assert result is True
        assert (self.semantic_dir / "summary.json").exists()

    def test_summary_contains_v1_health_fields(self):
        self._write_fixtures(
            candidates=[
                {"capability_id": "cap-a", "canonical_name": "a", "observed_names": ["a"], "evidence_refs": ["sha:a", "summary:a"], "confidence": "high", "flags": []},
                {"capability_id": "cap-b", "canonical_name": "b", "observed_names": ["legacy-b"], "evidence_refs": ["sha:b"], "confidence": "low", "flags": ["mixed", "low_signal"]},
            ],
            stable=[
                {"capability_id": "cap-a", "canonical_name": "a", "observed_names": ["a"], "evidence_refs": ["sha:a", "summary:a"], "confidence": "high"},
                {"capability_id": "cap-b", "canonical_name": "b", "observed_names": ["legacy-b"], "evidence_refs": ["sha:b"], "confidence": "low"},
            ],
        )
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState(metadata={"signal_count": 3}))
        from src.io_utils import load_json
        summary = load_json(str(self.semantic_dir / "summary.json"))
        assert summary["signal_count"] == 3
        assert summary["capability_candidate_count"] == 2
        assert summary["stable_capability_count"] == 2
        assert 0 <= summary["mixed_ratio"] <= 1
        assert 0 <= summary["low_signal_ratio"] <= 1
        assert 0 <= summary["evidence_coverage"] <= 1
        assert "naming_drift_count" in summary

    def test_empty_candidates_produce_valid_summary(self):
        self._write_fixtures([], [])
        runner = CommitSemanticRunner()
        result = runner._run_export(HarnessState())
        assert result is True
        from src.io_utils import load_json
        summary = load_json(str(self.semantic_dir / "summary.json"))
        assert summary["signal_count"] == 0
        assert summary["capability_candidate_count"] == 0
        assert summary["stable_capability_count"] == 0
        assert summary["evidence_coverage"] == 0.0

    def test_summary_json_is_json_serializable(self):
        self._write_fixtures(
            candidates=[{"capability_id": "cap-a", "canonical_name": "a", "evidence_refs": ["sha:a"], "confidence": "high"}],
            stable=[{"capability_id": "cap-a", "canonical_name": "a", "evidence_refs": ["sha:a"], "confidence": "high"}],
        )
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState(metadata={"signal_count": 1}))
        from src.io_utils import load_json
        summary = load_json(str(self.semantic_dir / "summary.json"))
        json.dumps(summary)
        assert "capability_candidate_count" in summary
        assert "stable_capability_count" in summary

    def test_export_removes_legacy_artifacts(self):
        self._write_fixtures(
            candidates=[{"capability_id": "cap-a", "canonical_name": "a", "evidence_refs": ["sha:a"], "confidence": "high"}],
            stable=[{"capability_id": "cap-a", "canonical_name": "a", "evidence_refs": ["sha:a"], "confidence": "high"}],
        )
        (self.semantic_dir / "patterns").mkdir()
        (self.semantic_dir / "patterns" / "legacy.json").write_text("{}", encoding="utf-8")
        (self.semantic_dir / "canonical-demands.yaml").write_text("legacy: true\n", encoding="utf-8")
        (self.semantic_dir / "functional").mkdir()
        (self.semantic_dir / "functional" / "legacy.md").write_text("legacy", encoding="utf-8")
        (self.semantic_dir / "non-functional").mkdir()
        (self.semantic_dir / "non-functional" / "legacy.md").write_text("legacy", encoding="utf-8")

        runner = CommitSemanticRunner()
        runner._run_export(HarnessState(metadata={"signal_count": 1}))

        assert (self.semantic_dir / "summary.json").exists()
        assert not (self.semantic_dir / "patterns").exists()
        assert not (self.semantic_dir / "canonical-demands.yaml").exists()
        assert not (self.semantic_dir / "functional").exists()
        assert not (self.semantic_dir / "non-functional").exists()

    def test_export_is_idempotent_when_no_legacy_artifacts_exist(self):
        self._write_fixtures(
            candidates=[{"capability_id": "cap-a", "canonical_name": "a", "evidence_refs": ["sha:a"], "confidence": "high"}],
            stable=[{"capability_id": "cap-a", "canonical_name": "a", "evidence_refs": ["sha:a"], "confidence": "high"}],
        )
        runner = CommitSemanticRunner()
        runner._run_export(HarnessState(metadata={"signal_count": 1}))
        from src.io_utils import load_json
        summary = load_json(str(self.semantic_dir / "summary.json"))
        assert "capability_candidate_count" in summary
