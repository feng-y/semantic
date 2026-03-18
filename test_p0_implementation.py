#!/usr/bin/env python3
"""
Test P0 implementation: semantic value classification, deduplication, and pattern extraction.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.types import RawCommit, ChangeGroup, SemanticCaseInput, BugfixEvidence, SplitHints
from src.commit_semantic.value_classifier import classify_semantic_value
from src.commit_semantic.deduplication import generate_dedup_key, deduplicate_cases
from src.commit_semantic.pattern_extraction import generate_pattern_fingerprint, extract_patterns


def test_value_classifier():
    """Test semantic value classification."""
    print("=== Testing Value Classifier ===")

    # Test case 1: Format-only commit (low value)
    commit1 = RawCommit(
        commit_id="test1",
        author="test",
        timestamp="123456",
        files=["README.md", "docs/guide.md"],
        diff_chunks=["prettier format changes"],
        related_tests=[]
    )
    groups1 = []
    case1 = SemanticCaseInput(
        case_id="test1_case_0",
        commit_id="test1",
        module="docs",
        files=["README.md"],
        diff_chunks=["prettier format changes"]
    )

    value1 = classify_semantic_value(commit1, groups1, case1)
    print(f"  Format-only commit: {value1}")
    assert value1 == "low", f"Expected 'low', got '{value1}'"

    # Test case 2: Substantial change (high value)
    commit2 = RawCommit(
        commit_id="test2",
        author="test",
        timestamp="123456",
        files=["src/parser/legacy.py", "tests/test_parser.py"],
        diff_chunks=["+" * 500],  # Substantial diff
        related_tests=["tests/test_parser.py"]
    )
    groups2 = [
        ChangeGroup(
            group_id="g1",
            theme="parser",
            files=["src/parser/legacy.py"],
            role="primary"
        )
    ]
    case2 = SemanticCaseInput(
        case_id="test2_case_0",
        commit_id="test2",
        module="parser",
        files=["src/parser/legacy.py", "tests/test_parser.py"],
        diff_chunks=["+" * 500]
    )

    value2 = classify_semantic_value(commit2, groups2, case2)
    print(f"  Substantial change: {value2}")
    assert value2 in ["high", "medium"], f"Expected 'high' or 'medium', got '{value2}'"

    print("  ✓ Value classifier tests passed\n")


def test_deduplication():
    """Test deduplication logic."""
    print("=== Testing Deduplication ===")

    # Create test cases
    case1 = {
        "case_id": "case1",
        "module": "parser",
        "issue_text": "bugfix：修复旧DSL写法边界检查",
        "development_type": "bugfix",
        "commit_log": "在 parser 中补充 legacy 写法的边界检查"
    }

    case2 = {
        "case_id": "case2",
        "module": "parser",
        "issue_text": "bugfix：修复旧DSL写法边界检查",  # Exact same
        "development_type": "bugfix",
        "commit_log": "在 parser 中补充 legacy 写法的边界检查"  # Exact same
    }

    case3 = {
        "case_id": "case3",
        "module": "qserver",
        "issue_text": "feat：实现请求处理流程",
        "development_type": "feature",
        "commit_log": "实现 qserver 请求处理"
    }

    # Generate dedup keys
    key1 = generate_dedup_key(case1)
    key2 = generate_dedup_key(case2)
    key3 = generate_dedup_key(case3)

    print(f"  Case1 dedup_key: {key1}")
    print(f"  Case2 dedup_key: {key2}")
    print(f"  Case3 dedup_key: {key3}")

    # Case1 and Case2 should have same key (exact duplicates)
    assert key1 == key2, f"Exact duplicates should have same dedup_key: {key1} vs {key2}"
    assert key1 != key3, "Different cases should have different dedup_key"

    # Test deduplicate_cases
    cases = [case1, case2, case3]
    unique_cases, duplicate_cases = deduplicate_cases(cases)

    print(f"  Unique cases: {len(unique_cases)}")
    print(f"  Duplicate cases: {len(duplicate_cases)}")

    assert len(unique_cases) == 2, f"Expected 2 unique cases, got {len(unique_cases)}"
    assert len(duplicate_cases) == 1, f"Expected 1 duplicate case, got {len(duplicate_cases)}"

    print("  ✓ Deduplication tests passed\n")


def test_pattern_extraction():
    """Test pattern extraction."""
    print("=== Testing Pattern Extraction ===")

    # Create test cases with similar patterns
    cases = [
        {
            "case_id": "case1",
            "module": "parser",
            "issue_text": "bugfix：修复旧DSL写法边界检查",
            "development_type": "bugfix",
            "commit_log": "在 parser 中补充 legacy 写法的边界检查",
            "files": ["src/parser/legacy.py"],
            "rules": ["legacy syntax compatibility must be preserved"],
            "invariants": ["historical inputs remain parseable"]
        },
        {
            "case_id": "case2",
            "module": "parser",
            "issue_text": "bugfix：修复新DSL写法边界检查",
            "development_type": "bugfix",
            "commit_log": "在 parser 中补充新写法的边界检查",
            "files": ["src/parser/modern.py"],
            "rules": ["syntax compatibility must be preserved"],
            "invariants": ["inputs remain parseable"]
        },
        {
            "case_id": "case3",
            "module": "qserver",
            "issue_text": "feat：实现请求处理",
            "development_type": "feature",
            "commit_log": "实现 qserver 请求处理流程",
            "files": ["src/qserver/handler.py"],
            "rules": [],
            "invariants": []
        }
    ]

    # Generate pattern fingerprints
    fp1 = generate_pattern_fingerprint(cases[0])
    fp2 = generate_pattern_fingerprint(cases[1])
    fp3 = generate_pattern_fingerprint(cases[2])

    print(f"  Case1 pattern: {fp1}")
    print(f"  Case2 pattern: {fp2}")
    print(f"  Case3 pattern: {fp3}")

    # Case1 and Case2 should have same pattern (similar structure)
    assert fp1 == fp2, "Similar cases should have same pattern fingerprint"
    assert fp1 != fp3, "Different cases should have different pattern fingerprint"

    # Extract patterns
    patterns = extract_patterns(cases)

    print(f"  Found {len(patterns)} patterns")

    assert len(patterns) == 1, f"Expected 1 pattern, got {len(patterns)}"

    pattern = patterns[0]
    print(f"  Pattern count: {pattern['count']}")
    print(f"  Canonical case: {pattern['canonical_case_id']}")
    print(f"  Variants: {pattern['variant_case_ids']}")

    assert pattern['count'] == 2, f"Expected count=2, got {pattern['count']}"
    assert len(pattern['variant_case_ids']) == 1, f"Expected 1 variant, got {len(pattern['variant_case_ids'])}"

    print("  ✓ Pattern extraction tests passed\n")


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Commit Semantic P0 - Implementation Tests                  ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    try:
        test_value_classifier()
        test_deduplication()
        test_pattern_extraction()

        print("╔══════════════════════════════════════════════════════════════╗")
        print("║  ✓ All P0 Tests Passed                                      ║")
        print("╚══════════════════════════════════════════════════════════════╝")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
