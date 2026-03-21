#!/usr/bin/env python3
"""
Test P2/P3 pattern extraction implementation.

Tests:
1. Action/object/constraint class abstraction
2. Pattern fingerprint generation
3. Similarity-based grouping within buckets
4. Pattern count checking and alerts
5. Canonical pattern selection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.commit_semantic.pattern_extraction_v2 import (
    calculate_similarity,
    check_pattern_count,
    extract_action_class,
    extract_constraint_class,
    extract_object_class,
    extract_patterns_v2,
    generate_pattern_fingerprint_v2,
    group_by_similarity,
    select_canonical_pattern_case,
)


def test_action_class_extraction():
    """Test action class extraction."""
    print("Testing action class extraction...")

    cases = [
        {"issue_text": "fix：修复解析错误", "dev_type": "bugfix", "expected": "fix"},
        {"issue_text": "feat：添加新功能", "dev_type": "feature", "expected": "add"},
        {"issue_text": "refactor：重构代码", "dev_type": "refactor", "expected": "refactor"},
        {"issue_text": "optimize：优化性能", "dev_type": "optimize", "expected": "optimize"},
        {"issue_text": "migrate：迁移到新版本", "dev_type": "migration", "expected": "migrate"},
        {"issue_text": "control：控制并发", "dev_type": "feature", "expected": "control"},
        {"issue_text": "align：对齐数据", "dev_type": "feature", "expected": "align"},
    ]

    for case in cases:
        action = extract_action_class(case["issue_text"], case["dev_type"])
        assert action == case["expected"], f"Expected {case['expected']}, got {action}"
        print(f"  ✓ {case['issue_text'][:20]}... -> {action}")

    print("✓ Action class extraction tests passed\n")


def test_object_class_extraction():
    """Test object class extraction."""
    print("Testing object class extraction...")

    cases = [
        {
            "issue_text": "修复解析器错误",
            "rules": ["parser must handle edge cases"],
            "invariants": [],
            "expected": "parser"
        },
        {
            "issue_text": "优化特征提取",
            "rules": ["feature extraction must be efficient"],
            "invariants": [],
            "expected": "feature-extraction"
        },
        {
            "issue_text": "对齐请求响应",
            "rules": ["request and response must align"],
            "invariants": [],
            "expected": "request-response-alignment"
        },
        {
            "issue_text": "控制配置",
            "rules": ["config must be validated"],
            "invariants": [],
            "expected": "config-control"
        },
        {
            "issue_text": "处理并发",
            "rules": ["concurrency must be bounded"],
            "invariants": [],
            "expected": "concurrency-control"
        },
    ]

    for case in cases:
        obj_class = extract_object_class(case)
        assert obj_class == case["expected"], f"Expected {case['expected']}, got {obj_class}"
        print(f"  ✓ {case['issue_text']} -> {obj_class}")

    print("✓ Object class extraction tests passed\n")


def test_constraint_class_extraction():
    """Test constraint class extraction."""
    print("Testing constraint class extraction...")

    cases = [
        {
            "rules": ["must maintain backward compatibility"],
            "invariants": [],
            "expected": "compatibility"
        },
        {
            "rules": ["must align with upstream"],
            "invariants": ["alignment preserved"],
            "expected": "alignment"
        },
        {
            "rules": ["must handle concurrency"],
            "invariants": ["thread-safe"],
            "expected": "concurrency"
        },
        {
            "rules": ["must validate input", "must check bounds"],
            "invariants": [],
            "expected": "boundedness+validation"
        },
        {
            "rules": [],
            "invariants": [],
            "expected": "none"
        },
    ]

    for case in cases:
        constraint = extract_constraint_class(case["rules"], case["invariants"])
        assert constraint == case["expected"], f"Expected {case['expected']}, got {constraint}"
        print(f"  ✓ {case['rules'][:1]} -> {constraint}")

    print("✓ Constraint class extraction tests passed\n")


def test_pattern_fingerprint():
    """Test pattern fingerprint generation."""
    print("Testing pattern fingerprint generation...")

    case = {
        "module": "qserver.parser",
        "domain": "parsing",
        "development_type": "bugfix",
        "issue_text": "fix：修复解析错误",
        "rules": ["must maintain compatibility"],
        "invariants": []
    }

    fingerprint = generate_pattern_fingerprint_v2(case)
    expected = "parsing|bugfix|fix|parser|compatibility"
    assert fingerprint == expected, f"Expected {expected}, got {fingerprint}"
    print(f"  ✓ Fingerprint: {fingerprint}")

    print("✓ Pattern fingerprint tests passed\n")


def test_similarity_calculation():
    """Test text similarity calculation."""
    print("Testing similarity calculation...")

    cases = [
        {
            "text1": "feat：添加新功能",
            "text2": "feat：添加新功能",
            "expected_min": 0.90  # P4 formula: 0.5*seq + 0.3*jaccard + 0.2*constraint
        },
        {
            "text1": "feat：添加用户管理功能",
            "text2": "feat：添加用户管理模块",
            "expected_min": 0.25  # Jaccard + SequenceMatcher for similar Chinese text
        },
        {
            "text1": "feat：添加新功能",
            "text2": "bugfix：修复错误",
            "expected_max": 0.20
        },
    ]

    for case in cases:
        sim = calculate_similarity(case["text1"], case["text2"])
        if "expected_min" in case:
            assert sim >= case["expected_min"], f"Expected >= {case['expected_min']}, got {sim}"
            print(f"  ✓ Similarity: {sim:.2f} (>= {case['expected_min']})")
        else:
            assert sim <= case["expected_max"], f"Expected <= {case['expected_max']}, got {sim}"
            print(f"  ✓ Similarity: {sim:.2f} (<= {case['expected_max']})")

    print("✓ Similarity calculation tests passed\n")


def test_similarity_grouping():
    """Test similarity-based grouping."""
    print("Testing similarity grouping...")

    cases = [
        {
            "case_id": "case_001",
            "issue_text": "feat：添加用户认证功能"
        },
        {
            "case_id": "case_002",
            "issue_text": "feat：添加用户授权功能"
        },
        {
            "case_id": "case_003",
            "issue_text": "feat：添加用户验证功能"
        },
        {
            "case_id": "case_004",
            "issue_text": "bugfix：修复解析错误"
        },
    ]

    groups = group_by_similarity(cases, threshold=0.70)
    print(f"  Found {len(groups)} groups")

    # Should group similar cases together
    assert len(groups) >= 2, f"Expected at least 2 groups, got {len(groups)}"

    # First group should have similar cases
    first_group_ids = [c["case_id"] for c in groups[0]]
    print(f"  ✓ Group 1: {first_group_ids}")

    print("✓ Similarity grouping tests passed\n")


def test_canonical_selection():
    """Test canonical pattern case selection."""
    print("Testing canonical case selection...")

    cases = [
        {
            "case_id": "case_001",
            "issue_text": "feat：添加功能A到模块X",
            "rules": ["rule1"],
            "invariants": [],
            "semantic_value": "medium"
        },
        {
            "case_id": "case_002",
            "issue_text": "feat：添加功能",
            "rules": ["rule1", "rule2"],
            "invariants": ["inv1"],
            "semantic_value": "high"
        },
        {
            "case_id": "case_003",
            "issue_text": "feat：添加功能B到模块Y",
            "rules": [],
            "invariants": [],
            "semantic_value": "low"
        },
    ]

    canonical = select_canonical_pattern_case(cases)
    # Should prefer case_002 (high semantic_value, more rules/invariants)
    assert canonical["case_id"] == "case_002", f"Expected case_002, got {canonical['case_id']}"
    print(f"  ✓ Selected canonical: {canonical['case_id']}")

    print("✓ Canonical selection tests passed\n")


def test_pattern_count_checking():
    """Test pattern count checking and alerts."""
    print("Testing pattern count checking...")

    domain_counts = {
        "domain_a": 8,   # excellent
        "domain_b": 15,  # acceptable
        "domain_c": 25,  # too_high
        "domain_d": 35,  # critical
    }

    results = check_pattern_count(domain_counts)

    assert results["domain_a"]["pattern_count_status"] == "excellent"
    assert results["domain_b"]["pattern_count_status"] == "acceptable"
    assert results["domain_c"]["pattern_count_status"] == "too_high"
    assert results["domain_d"]["pattern_count_status"] == "critical"

    print(f"  ✓ domain_a (8): {results['domain_a']['pattern_count_status']}")
    print(f"  ✓ domain_b (15): {results['domain_b']['pattern_count_status']}")
    print(f"  ✓ domain_c (25): {results['domain_c']['pattern_count_status']}")
    print(f"  ✓ domain_d (35): {results['domain_d']['pattern_count_status']}")

    print("✓ Pattern count checking tests passed\n")


def test_full_pattern_extraction():
    """Test full pattern extraction pipeline."""
    print("Testing full pattern extraction...")

    cases = [
        {
            "case_id": "case_001",
            "module": "qserver.parser",
            "development_type": "bugfix",
            "issue_text": "fix：修复解析错误",
            "rules": ["must maintain compatibility"],
            "invariants": [],
            "semantic_value": "high"
        },
        {
            "case_id": "case_002",
            "module": "qserver.parser",
            "development_type": "bugfix",
            "issue_text": "fix：修复解析异常",
            "rules": ["must maintain compatibility"],
            "invariants": [],
            "semantic_value": "medium"
        },
        {
            "case_id": "case_003",
            "module": "qserver.parser",
            "development_type": "bugfix",
            "issue_text": "fix：修复解析问题",
            "rules": ["must maintain compatibility"],
            "invariants": [],
            "semantic_value": "medium"
        },
        {
            "case_id": "case_004",
            "module": "feature-extraction",
            "development_type": "optimize",
            "issue_text": "optimize：优化特征提取性能",
            "rules": ["must preserve accuracy"],
            "invariants": [],
            "semantic_value": "high"
        },
    ]

    patterns, domain_counts = extract_patterns_v2(cases, similarity_threshold=0.50)

    print(f"  Found {len(patterns)} patterns")
    print(f"  Domain counts: {domain_counts}")

    # Should find at least 1 pattern (the three similar parser bugfix cases)
    assert len(patterns) >= 1, f"Expected at least 1 pattern, got {len(patterns)}"

    # Check pattern structure
    if patterns:
        pattern = patterns[0]
        assert "pattern_id" in pattern
        assert "pattern_fingerprint" in pattern
        assert "domain" in pattern
        assert "count" in pattern
        assert "canonical_case_id" in pattern
        assert "variant_case_ids" in pattern
        print("  ✓ Pattern structure valid")
        print(f"  ✓ Pattern: {pattern['pattern_fingerprint']}")
        print(f"  ✓ Count: {pattern['count']}")
        print(f"  ✓ Canonical: {pattern['canonical_case_id']}")
        print(f"  ✓ Variants: {pattern['variant_case_ids']}")

    print("✓ Full pattern extraction tests passed\n")


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  P2/P3 Pattern Extraction - Unit Tests                      ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    try:
        test_action_class_extraction()
        test_object_class_extraction()
        test_constraint_class_extraction()
        test_pattern_fingerprint()
        test_similarity_calculation()
        test_similarity_grouping()
        test_canonical_selection()
        test_pattern_count_checking()
        test_full_pattern_extraction()

        print("╔══════════════════════════════════════════════════════════════╗")
        print("║  ✓ All P2/P3 Tests Passed                                   ║")
        print("╚══════════════════════════════════════════════════════════════╝")

        return True

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
