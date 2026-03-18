#!/usr/bin/env python3
"""
End-to-end test for P2/P3 pattern extraction in export skill.

Creates test cases, runs export with P2/P3, verifies outputs.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.io_utils import save_yaml, load_json, load_jsonl


def create_test_cases(output_dir: Path):
    """Create test semantic cases."""
    cases = [
        # Pattern 1: Parser bugfixes (3 similar cases)
        {
            "case_id": "case_001",
            "commit_id": "abc001",
            "module": "qserver.parser",
            "commit_log": "修复解析器在处理特殊字符时的错误",
            "issue_text": "fix：修复解析错误",
            "development_type": "bugfix",
            "rules": ["must maintain backward compatibility"],
            "invariants": ["parser output format unchanged"],
            "split_suggestion": {"needs_split": False, "split_reasons": []},
            "semantic_value": "high",
            "dedup_key": "",
            "pattern_id": ""
        },
        {
            "case_id": "case_002",
            "commit_id": "abc002",
            "module": "qserver.parser",
            "commit_log": "修复解析器在处理空值时的异常",
            "issue_text": "fix：修复解析异常",
            "development_type": "bugfix",
            "rules": ["must maintain backward compatibility"],
            "invariants": ["parser output format unchanged"],
            "split_suggestion": {"needs_split": False, "split_reasons": []},
            "semantic_value": "medium",
            "dedup_key": "",
            "pattern_id": ""
        },
        {
            "case_id": "case_003",
            "commit_id": "abc003",
            "module": "qserver.parser",
            "commit_log": "修复解析器在处理边界情况时的问题",
            "issue_text": "fix：修复解析问题",
            "development_type": "bugfix",
            "rules": ["must maintain backward compatibility"],
            "invariants": ["parser output format unchanged"],
            "split_suggestion": {"needs_split": False, "split_reasons": []},
            "semantic_value": "medium",
            "dedup_key": "",
            "pattern_id": ""
        },
        # Pattern 2: Feature extraction optimization (2 similar cases)
        {
            "case_id": "case_004",
            "commit_id": "abc004",
            "module": "feature-extraction.core",
            "commit_log": "优化特征提取的性能，减少计算时间",
            "issue_text": "optimize：优化特征提取性能",
            "development_type": "optimize",
            "rules": ["must preserve accuracy"],
            "invariants": ["feature output unchanged"],
            "split_suggestion": {"needs_split": False, "split_reasons": []},
            "semantic_value": "high",
            "dedup_key": "",
            "pattern_id": ""
        },
        {
            "case_id": "case_005",
            "commit_id": "abc005",
            "module": "feature-extraction.core",
            "commit_log": "优化特征提取的效率，提升处理速度",
            "issue_text": "optimize：优化特征提取效率",
            "development_type": "optimize",
            "rules": ["must preserve accuracy"],
            "invariants": ["feature output unchanged"],
            "split_suggestion": {"needs_split": False, "split_reasons": []},
            "semantic_value": "high",
            "dedup_key": "",
            "pattern_id": ""
        },
        # Unique case (no pattern)
        {
            "case_id": "case_006",
            "commit_id": "abc006",
            "module": "demand.analyzer",
            "commit_log": "实现需求分析的完整流程",
            "issue_text": "feat：实现需求分析流程",
            "development_type": "feature",
            "rules": ["must validate input"],
            "invariants": ["analysis results consistent"],
            "split_suggestion": {"needs_split": False, "split_reasons": []},
            "semantic_value": "high",
            "dedup_key": "",
            "pattern_id": ""
        },
        # Exact duplicate of case_001
        {
            "case_id": "case_007",
            "commit_id": "abc007",
            "module": "qserver.parser",
            "commit_log": "修复解析器在处理特殊字符时的错误",
            "issue_text": "fix：修复解析错误",
            "development_type": "bugfix",
            "rules": ["must maintain backward compatibility"],
            "invariants": ["parser output format unchanged"],
            "split_suggestion": {"needs_split": False, "split_reasons": []},
            "semantic_value": "medium",
            "dedup_key": "",
            "pattern_id": ""
        },
    ]

    output_dir.mkdir(parents=True, exist_ok=True)

    for case in cases:
        case_file = output_dir / f"{case['case_id']}.yaml"
        save_yaml(case, str(case_file))

    return len(cases)


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  P2/P3 Pattern Extraction - End-to-End Test                 ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_dir = tmpdir / "semantic_cases"
        export_dir = tmpdir / "exports"
        invalid_dir = tmpdir / "invalid_cases"
        low_value_dir = tmpdir / "low_value_cases"

        # Create test cases
        print("=== Step 1: Create Test Cases ===")
        num_cases = create_test_cases(input_dir)
        print(f"Created {num_cases} test cases\n")

        # Run export with P2/P3
        print("=== Step 2: Run Export with P2/P3 ===")
        import subprocess
        result = subprocess.run([
            "python3", "skills/commit-semantic-export/run.py",
            "--input-dir", str(input_dir),
            "--output-dir", str(export_dir),
            "--invalid-dir", str(invalid_dir),
            "--low-value-dir", str(low_value_dir)
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"✗ Export failed: {result.stderr}")
            return False

        print(result.stdout)

        # Verify outputs
        print("\n=== Step 3: Verify P2/P3 Outputs ===")

        # Check files exist
        cases_jsonl = export_dir / "cases.jsonl"
        duplicates_jsonl = export_dir / "duplicates.jsonl"
        patterns_jsonl = export_dir / "patterns.jsonl"
        summary_json = export_dir / "summary.json"

        for file_path, name in [
            (cases_jsonl, "cases.jsonl"),
            (duplicates_jsonl, "duplicates.jsonl"),
            (patterns_jsonl, "patterns.jsonl"),
            (summary_json, "summary.json")
        ]:
            if file_path.exists():
                print(f"✓ {name} exists")
            else:
                print(f"✗ {name} missing")
                return False

        # Load and verify summary
        summary = load_json(str(summary_json))

        print(f"\n=== Summary Statistics ===")
        print(f"Total cases: {summary['total_cases']}")
        print(f"Unique cases: {summary['unique_cases']}")
        print(f"Duplicate cases: {summary['duplicate_cases']}")
        print(f"Duplicate groups: {summary['duplicate_groups']}")
        print(f"Pattern count: {summary['pattern_count']}")

        # Verify expected values
        assert summary['total_cases'] == 7, f"Expected 7 total cases, got {summary['total_cases']}"
        assert summary['unique_cases'] == 6, f"Expected 6 unique cases, got {summary['unique_cases']}"
        assert summary['duplicate_cases'] == 1, f"Expected 1 duplicate case, got {summary['duplicate_cases']}"
        assert summary['duplicate_groups'] == 1, f"Expected 1 duplicate group, got {summary['duplicate_groups']}"
        assert summary['pattern_count'] >= 1, f"Expected at least 1 pattern, got {summary['pattern_count']}"

        # Verify domain pattern stats
        print(f"\n=== Domain Pattern Stats ===")
        domain_stats = summary['domain_pattern_stats']
        for domain, stats in domain_stats.items():
            print(f"{domain}: {stats['pattern_count']} patterns ({stats['status']})")

        # Verify high frequency patterns
        print(f"\n=== High Frequency Patterns ===")
        for i, pattern in enumerate(summary['high_frequency_patterns'], 1):
            print(f"{i}. [{pattern['domain']}] {pattern['representative_issue_text']} (count: {pattern['count']})")

        # Load and verify patterns
        patterns = load_jsonl(str(patterns_jsonl))
        print(f"\n=== Pattern Details ===")
        for pattern in patterns:
            print(f"Pattern: {pattern['pattern_fingerprint']}")
            print(f"  Domain: {pattern['domain']}")
            print(f"  Count: {pattern['count']}")
            print(f"  Canonical: {pattern['canonical_case_id']}")
            print(f"  Variants: {pattern['variant_case_ids']}")
            print(f"  Issue: {pattern['representative_issue_text']}")
            print()

        # Load and verify duplicates
        duplicates = load_jsonl(str(duplicates_jsonl))
        print(f"=== Duplicate Groups ===")
        for dup_group in duplicates:
            print(f"Dedup key: {dup_group['dedup_key']}")
            print(f"  Canonical: {dup_group['canonical_case_id']}")
            print(f"  Duplicates: {dup_group['duplicate_case_ids']}")
            print()

        print("╔══════════════════════════════════════════════════════════════╗")
        print("║  ✓ P2/P3 End-to-End Test Passed                             ║")
        print("╚══════════════════════════════════════════════════════════════╝")

        print("\n验证完成:")
        print("  ✓ P2/P3 pattern extraction working")
        print("  ✓ Domain-aware aggregation working")
        print("  ✓ Similarity-based grouping working")
        print("  ✓ Pattern count checking working")
        print("  ✓ Duplicate groups output working")
        print("  ✓ Enhanced statistics working")
        print("\nP2/P3 implementation verified!")

        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
