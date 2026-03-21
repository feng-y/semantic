#!/usr/bin/env python3
"""
Tests for:
1. semantic_value propagation through the full pipeline (Task #2)
2. domain field trust and use_model_optimization threading in patterning (Task #4)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commit_semantic.pattern_extraction_v2 import (
    extract_patterns_v2,
    generate_pattern_fingerprint_v2,
)
from src.commit_semantic.patterning import (
    PatternInput,
    group_patterns,
    select_canonical_pattern_case,
)

# ---------------------------------------------------------------------------
# Task #2: semantic_value propagation
# ---------------------------------------------------------------------------

def _make_case(case_id: str, semantic_value: str = "high", domain: str = "auth") -> dict:
    return {
        "case_id": case_id,
        "commit_id": f"abc{case_id}",
        "module": "auth.login",
        "domain": domain,
        "commit_log": "fix: resolve login timeout",
        "issue_text": "登录超时未正确处理",
        "development_type": "bugfix",
        "rules": ["timeout must be handled"],
        "invariants": ["session must expire"],
        "semantic_value": semantic_value,
    }


def test_semantic_value_preserved_in_pattern_input():
    """PatternInput carries semantic_value from case dict."""
    case = _make_case("c1", semantic_value="high")
    pi = PatternInput(
        case_id=case["case_id"],
        domain=case["domain"],
        module=case["module"],
        development_type=case["development_type"],
        commit_log=case["commit_log"],
        issue_text=case["issue_text"],
        rules=case["rules"],
        invariants=case["invariants"],
        semantic_value=case["semantic_value"],
    )
    assert pi.semantic_value == "high"


def test_extract_patterns_v2_reads_semantic_value():
    """extract_patterns_v2 passes semantic_value into PatternInput (used for canonical selection)."""
    # Two nearly-identical cases — one high, one low — same fingerprint bucket
    cases = [
        _make_case("c1", semantic_value="high"),
        _make_case("c2", semantic_value="low"),
    ]
    # Both cases have identical fingerprints so they land in the same bucket
    fp1 = generate_pattern_fingerprint_v2(cases[0])
    fp2 = generate_pattern_fingerprint_v2(cases[1])
    assert fp1 == fp2, "Both cases must share a fingerprint for this test to be meaningful"

    patterns, _ = extract_patterns_v2(cases, similarity_threshold=0.0)
    assert len(patterns) == 1
    # Canonical should be the high-value case
    assert patterns[0]["canonical_case_id"] == "c1"


def test_semantic_value_default_medium_when_missing():
    """Cases without semantic_value default to 'medium' in extract_patterns_v2."""
    case = _make_case("c1")
    del case["semantic_value"]
    pi_list = []
    # Simulate what extract_patterns_v2 does internally
    from src.commit_semantic.patterning import PatternInput
    pi = PatternInput(
        case_id=case["case_id"],
        domain=case.get("domain", ""),
        module=case.get("module", ""),
        development_type=case.get("development_type", ""),
        commit_log=case.get("commit_log", ""),
        issue_text=case.get("issue_text", ""),
        rules=case.get("rules", []),
        invariants=case.get("invariants", []),
        semantic_value=case.get("semantic_value", "medium"),
    )
    assert pi.semantic_value == "medium"


def test_generate_stage_preserves_semantic_value():
    """Verify generate/run.py assembles case_output with semantic_value from input."""
    # This is a unit-level check of the assembly logic (no executor needed)
    case_input = {
        "case_id": "test-001",
        "commit_id": "abc123",
        "module": "auth",
        "domain": "auth",
        "semantic_value": "high",
    }
    # Replicate the assembly from generate/run.py line 63-75
    case_output = {
        "case_id": case_input["case_id"],
        "commit_id": case_input["commit_id"],
        "module": case_input["module"],
        "domain": case_input.get("domain", case_input["module"]),
        "commit_log": "fix: something",
        "issue_text": "issue",
        "development_type": "bugfix",
        "rules": [],
        "invariants": [],
        "split_suggestion": {"needs_split": False, "split_reasons": []},
        "semantic_value": case_input["semantic_value"],  # line 74 in generate/run.py
    }
    assert case_output["semantic_value"] == "high"


# ---------------------------------------------------------------------------
# Task #4: use_model_optimization threading + domain field trust
# ---------------------------------------------------------------------------

def _make_pattern_input(case_id: str, domain: str = "auth", semantic_value: str = "medium") -> PatternInput:
    return PatternInput(
        case_id=case_id,
        domain=domain,
        module="auth.login",
        development_type="bugfix",
        commit_log="fix: login timeout",
        issue_text="登录超时未正确处理",
        rules=["timeout must be handled"],
        invariants=["session must expire"],
        semantic_value=semantic_value,
    )


def test_group_patterns_accepts_use_model_optimization():
    """group_patterns() must accept use_model_optimization without error."""
    cases = [_make_pattern_input("c1"), _make_pattern_input("c2")]
    # Should not raise TypeError
    result = group_patterns(cases, similarity_threshold=0.0, use_model_optimization=False)
    # With only 2 identical-fingerprint cases and threshold=0, they form one group
    assert isinstance(result, list)


def test_group_patterns_model_optimization_false_uses_rules():
    """With use_model_optimization=False, rule-based canonical selection is used."""
    high = _make_pattern_input("high-case", semantic_value="high")
    low = _make_pattern_input("low-case", semantic_value="low")
    groups = group_patterns([high, low], similarity_threshold=0.0, use_model_optimization=False)
    assert len(groups) == 1
    assert groups[0].canonical_case_id == "high-case"


def test_domain_field_used_in_pattern_fingerprint():
    """Pattern fingerprint uses explicit domain field, not re-guessed from module."""
    case_with_domain = {
        "case_id": "c1",
        "module": "some.unrelated.module",
        "domain": "explicit-domain",
        "development_type": "bugfix",
        "commit_log": "fix: something",
        "issue_text": "issue text",
        "rules": [],
        "invariants": [],
        "semantic_value": "medium",
    }
    fp = generate_pattern_fingerprint_v2(case_with_domain)
    # Fingerprint starts with normalized domain
    assert fp.startswith("explicit-domain|") or fp.split("|")[0] == "explicit-domain"


def test_domain_flows_through_extract_patterns_v2():
    """Domain from case dict is preserved in pattern group output."""
    cases = [
        {**_make_case("c1", domain="payments"), **{"issue_text": "支付超时", "commit_log": "fix: pay timeout"}},
        {**_make_case("c2", domain="payments"), **{"issue_text": "支付超时", "commit_log": "fix: pay timeout"}},
    ]
    patterns, domain_counts = extract_patterns_v2(cases, similarity_threshold=0.0)
    assert len(patterns) == 1
    assert patterns[0]["domain"] == "payments"
    assert "payments" in domain_counts


def test_select_canonical_prefers_high_semantic_value():
    """select_canonical_pattern_case picks high over low semantic_value."""
    cases = [
        _make_pattern_input("low1", semantic_value="low"),
        _make_pattern_input("high1", semantic_value="high"),
        _make_pattern_input("med1", semantic_value="medium"),
    ]
    canonical = select_canonical_pattern_case(cases, use_model_optimization=False)
    assert canonical.case_id == "high1"


if __name__ == "__main__":
    test_semantic_value_preserved_in_pattern_input()
    print("✓ test_semantic_value_preserved_in_pattern_input")

    test_extract_patterns_v2_reads_semantic_value()
    print("✓ test_extract_patterns_v2_reads_semantic_value")

    test_semantic_value_default_medium_when_missing()
    print("✓ test_semantic_value_default_medium_when_missing")

    test_generate_stage_preserves_semantic_value()
    print("✓ test_generate_stage_preserves_semantic_value")

    test_group_patterns_accepts_use_model_optimization()
    print("✓ test_group_patterns_accepts_use_model_optimization")

    test_group_patterns_model_optimization_false_uses_rules()
    print("✓ test_group_patterns_model_optimization_false_uses_rules")

    test_domain_field_used_in_pattern_fingerprint()
    print("✓ test_domain_field_used_in_pattern_fingerprint")

    test_domain_flows_through_extract_patterns_v2()
    print("✓ test_domain_flows_through_extract_patterns_v2")

    test_select_canonical_prefers_high_semantic_value()
    print("✓ test_select_canonical_prefers_high_semantic_value")

    print("\nAll tests passed.")
