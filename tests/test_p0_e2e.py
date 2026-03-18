"""
End-to-end tests for P0 pipeline closure.

Tests the complete flow using synthetic fixtures — no git repo or API calls needed:
1. Dedup pipeline: cases → group_strict_duplicates → canonical selection
2. Pattern extraction: cases → extract_patterns_v2 → domain fingerprints
3. Export pipeline: cases → deduplicate_cases → export stats
4. semantic_value preserved end-to-end
5. domain field used in pattern fingerprint (not re-guessed from module)
6. canonical selection respects semantic_value ranking
"""

import sys
import json
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commit_semantic.dedup import (
    DedupInput,
    build_dedup_key,
    group_strict_duplicates,
    select_canonical_duplicate,
)
from src.commit_semantic.deduplication import deduplicate_cases, generate_dedup_key
from src.commit_semantic.patterning import (
    PatternInput,
    build_pattern_fingerprint,
    group_patterns,
)
from src.commit_semantic.pattern_extraction_v2 import extract_patterns_v2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_dedup_input(
    case_id: str,
    module: str = "parser",
    development_type: str = "bugfix",
    issue_text: str = "fix: null pointer crash",
    rules: list = None,
    invariants: list = None,
    semantic_value: str = "medium",
) -> DedupInput:
    return DedupInput(
        case_id=case_id,
        module=module,
        development_type=development_type,
        issue_text=issue_text,
        rules=rules or ["must maintain compatibility"],
        invariants=invariants or ["inputs remain parseable"],
        semantic_value=semantic_value,
    )


def make_case_dict(
    case_id: str,
    module: str = "parser",
    domain: str = "parsing",
    development_type: str = "bugfix",
    issue_text: str = "fix: null pointer crash",
    commit_log: str = "fix null pointer in parser",
    rules: list = None,
    invariants: list = None,
    semantic_value: str = "medium",
) -> dict:
    return {
        "case_id": case_id,
        "module": module,
        "domain": domain,
        "development_type": development_type,
        "issue_text": issue_text,
        "commit_log": commit_log,
        "rules": rules or ["must maintain compatibility"],
        "invariants": invariants or ["inputs remain parseable"],
        "semantic_value": semantic_value,
        "split_suggestion": {"needs_split": False, "split_reasons": []},
        "dedup_key": "",
        "pattern_id": "",
    }


# ---------------------------------------------------------------------------
# 1. Dedup pipeline: semantic_value preserved through dedup
# ---------------------------------------------------------------------------

class TestDedupSemanticValuePreservation:
    def test_semantic_value_preserved_in_dedup_input(self):
        case = make_dedup_input("c1", semantic_value="high")
        assert case.semantic_value == "high"

    def test_dedup_key_ignores_semantic_value(self):
        """Two cases identical except semantic_value must share the same dedup key."""
        c_high = make_dedup_input("c1", issue_text="fix: null pointer", semantic_value="high")
        c_low = make_dedup_input("c2", issue_text="fix: null pointer", semantic_value="low")
        assert build_dedup_key(c_high) == build_dedup_key(c_low)

    def test_canonical_selection_prefers_high_semantic_value(self):
        """select_canonical_duplicate must pick the high-value case."""
        cases = [
            make_dedup_input("c_low", issue_text="fix: null pointer crash", semantic_value="low"),
            make_dedup_input("c_high", issue_text="fix: null pointer crash", semantic_value="high"),
            make_dedup_input("c_med", issue_text="fix: null pointer crash", semantic_value="medium"),
        ]
        canonical = select_canonical_duplicate(cases)
        assert canonical.case_id == "c_high"

    def test_canonical_selection_prefers_medium_over_low(self):
        cases = [
            make_dedup_input("c_low", issue_text="fix: null pointer crash", semantic_value="low"),
            make_dedup_input("c_med", issue_text="fix: null pointer crash", semantic_value="medium"),
        ]
        canonical = select_canonical_duplicate(cases)
        assert canonical.case_id == "c_med"

    def test_group_strict_duplicates_returns_canonical_with_high_value(self):
        """group_strict_duplicates canonical_case_id must be the high-value case."""
        cases = [
            make_dedup_input("c1", issue_text="fix: null pointer crash", semantic_value="low"),
            make_dedup_input("c2", issue_text="fix: null pointer crash", semantic_value="high"),
        ]
        groups = group_strict_duplicates(cases)
        assert len(groups) == 1
        assert groups[0].canonical_case_id == "c2"
        assert "c1" in groups[0].duplicate_case_ids


# ---------------------------------------------------------------------------
# 2. Pattern fingerprint uses domain field, not module
# ---------------------------------------------------------------------------

class TestPatternFingerprintUsesDomain:
    def test_fingerprint_includes_domain_not_module(self):
        """Two cases with same domain but different module must share fingerprint prefix."""
        case_a = PatternInput(
            case_id="a",
            domain="parsing",
            module="parser-v1",
            development_type="bugfix",
            commit_log="fix null pointer",
            issue_text="fix: null pointer crash",
            rules=["must maintain compatibility"],
            invariants=["inputs remain parseable"],
            semantic_value="medium",
        )
        case_b = PatternInput(
            case_id="b",
            domain="parsing",
            module="parser-v2",  # different module, same domain
            development_type="bugfix",
            commit_log="fix null pointer",
            issue_text="fix: null pointer crash",
            rules=["must maintain compatibility"],
            invariants=["inputs remain parseable"],
            semantic_value="medium",
        )
        fp_a = build_pattern_fingerprint(case_a)
        fp_b = build_pattern_fingerprint(case_b)
        # Both start with the domain component
        assert fp_a.startswith("parsing|")
        assert fp_b.startswith("parsing|")
        # Same domain → same fingerprint (module is not in fingerprint)
        assert fp_a == fp_b

    def test_different_domains_produce_different_fingerprints(self):
        case_a = PatternInput(
            case_id="a",
            domain="parsing",
            module="parser",
            development_type="bugfix",
            commit_log="fix null pointer",
            issue_text="fix: null pointer crash",
            rules=[],
            invariants=[],
        )
        case_b = PatternInput(
            case_id="b",
            domain="query-service",
            module="parser",  # same module, different domain
            development_type="bugfix",
            commit_log="fix null pointer",
            issue_text="fix: null pointer crash",
            rules=[],
            invariants=[],
        )
        assert build_pattern_fingerprint(case_a) != build_pattern_fingerprint(case_b)

    def test_extract_patterns_v2_uses_domain_field(self):
        """extract_patterns_v2 must use case['domain'], not re-guess from module."""
        cases = [
            make_case_dict("c1", module="parser-v1", domain="parsing",
                           issue_text="fix: null pointer crash", semantic_value="high"),
            make_case_dict("c2", module="parser-v2", domain="parsing",
                           issue_text="fix: null pointer crash", semantic_value="medium"),
        ]
        patterns, domain_counts = extract_patterns_v2(cases, similarity_threshold=0.50)
        # Both cases share domain "parsing" → should form a pattern
        assert "parsing" in domain_counts or len(patterns) >= 1


# ---------------------------------------------------------------------------
# 3. Full pipeline: cases → dedup → pattern extraction → export stats
# ---------------------------------------------------------------------------

class TestFullPipelineClosure:
    def _make_synthetic_cases(self):
        """Create a set of synthetic cases covering high/medium/low semantic_value."""
        return [
            # Duplicate pair: c1 (high) and c2 (low) — same issue_text
            make_case_dict("c1", issue_text="fix: null pointer crash",
                           semantic_value="high", domain="parsing"),
            make_case_dict("c2", issue_text="fix: null pointer crash",
                           semantic_value="low", domain="parsing"),
            # Duplicate pair: c3 (medium) and c4 (medium)
            make_case_dict("c3", issue_text="feat: add parser compatibility layer",
                           development_type="feature", semantic_value="medium", domain="parsing"),
            make_case_dict("c4", issue_text="feat: add parser compatibility layer",
                           development_type="feature", semantic_value="medium", domain="parsing"),
            # Unique case
            make_case_dict("c5", issue_text="refactor: extract config module",
                           development_type="refactor", semantic_value="medium",
                           domain="configuration", module="config"),
        ]

    def test_deduplicate_cases_preserves_semantic_value(self):
        cases = self._make_synthetic_cases()
        unique_cases, dup_groups = deduplicate_cases(cases)

        # c1 and c2 are duplicates; c1 (high) should be canonical
        dup_group_for_c1_c2 = next(
            (g for g in dup_groups if "c1" in (g["canonical_case_id"], *g["duplicate_case_ids"])
             and "c2" in (g["canonical_case_id"], *g["duplicate_case_ids"])),
            None
        )
        assert dup_group_for_c1_c2 is not None, "c1/c2 duplicate group not found"
        assert dup_group_for_c1_c2["canonical_case_id"] == "c1", (
            f"Expected c1 (high) as canonical, got {dup_group_for_c1_c2['canonical_case_id']}"
        )

        # All unique cases must have semantic_value
        for case in unique_cases:
            assert "semantic_value" in case, f"semantic_value missing from case {case['case_id']}"
            assert case["semantic_value"] in ("high", "medium", "low")

    def test_dedup_key_attached_to_unique_cases(self):
        cases = self._make_synthetic_cases()
        unique_cases, _ = deduplicate_cases(cases)
        for case in unique_cases:
            assert "dedup_key" in case
            assert len(case["dedup_key"]) == 40  # SHA1 hex

    def test_pattern_extraction_uses_domain(self):
        cases = self._make_synthetic_cases()
        unique_cases, _ = deduplicate_cases(cases)
        patterns, domain_counts = extract_patterns_v2(unique_cases, similarity_threshold=0.50)

        # domain_counts keys must be actual domain values, not module names
        for domain in domain_counts:
            assert domain in ("parsing", "configuration", ""), (
                f"Unexpected domain in pattern counts: {domain!r}"
            )

    def test_export_stats_fields_present(self):
        """Simulate the stats generation used by export skill."""
        from collections import Counter
        cases = self._make_synthetic_cases()
        unique_cases, dup_groups = deduplicate_cases(cases)
        patterns, domain_counts = extract_patterns_v2(unique_cases, similarity_threshold=0.50)

        total_duplicates = sum(len(g["duplicate_case_ids"]) for g in dup_groups)
        total_unique = len(unique_cases)
        total_cases = total_unique + total_duplicates
        validation_pass_rate = total_unique / total_cases if total_cases > 0 else 0

        dev_types = [c["development_type"] for c in unique_cases]
        dev_type_dist = dict(Counter(dev_types))

        stats = {
            "unique_cases": total_unique,
            "duplicate_cases": total_duplicates,
            "low_value_cases": 0,
            "pattern_count": len(patterns),
            "validation_pass_rate": validation_pass_rate,
            "development_type_distribution": dev_type_dist,
        }

        required = ["unique_cases", "duplicate_cases", "low_value_cases",
                    "pattern_count", "validation_pass_rate"]
        for field in required:
            assert field in stats, f"Missing required stats field: {field}"

        assert stats["unique_cases"] > 0
        assert stats["validation_pass_rate"] > 0

    def test_semantic_value_survives_full_pipeline(self):
        """semantic_value must be present in every unique case after dedup."""
        cases = self._make_synthetic_cases()
        unique_cases, _ = deduplicate_cases(cases)
        for case in unique_cases:
            assert case.get("semantic_value") in ("high", "medium", "low"), (
                f"Case {case['case_id']} has invalid semantic_value: {case.get('semantic_value')!r}"
            )

    def test_export_to_jsonl_preserves_semantic_value(self):
        """Round-trip through JSONL serialization must preserve semantic_value."""
        cases = self._make_synthetic_cases()
        unique_cases, _ = deduplicate_cases(cases)

        with tempfile.TemporaryDirectory() as tmpdir:
            jsonl_path = Path(tmpdir) / "cases.jsonl"
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for case in unique_cases:
                    f.write(json.dumps(case, ensure_ascii=False) + "\n")

            with open(jsonl_path, encoding="utf-8") as f:
                loaded = [json.loads(line) for line in f if line.strip()]

        assert len(loaded) == len(unique_cases)
        for case in loaded:
            assert "semantic_value" in case
            assert case["semantic_value"] in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# 4. group_patterns threads use_model_optimization (no model calls)
# ---------------------------------------------------------------------------

class TestGroupPatternsModelOptimizationFlag:
    def test_group_patterns_accepts_use_model_optimization_false(self):
        """group_patterns must accept use_model_optimization=False without error."""
        cases = [
            PatternInput(
                case_id="a",
                domain="parsing",
                module="parser",
                development_type="bugfix",
                commit_log="fix null pointer",
                issue_text="fix: null pointer crash",
                rules=["must maintain compatibility"],
                invariants=["inputs remain parseable"],
                semantic_value="high",
            ),
            PatternInput(
                case_id="b",
                domain="parsing",
                module="parser",
                development_type="bugfix",
                commit_log="fix null pointer",
                issue_text="fix: null pointer crash",
                rules=["must maintain compatibility"],
                invariants=["inputs remain parseable"],
                semantic_value="medium",
            ),
        ]
        # Must not raise
        groups = group_patterns(cases, similarity_threshold=0.50, use_model_optimization=False)
        assert isinstance(groups, list)
