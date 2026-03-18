#!/usr/bin/env python3
"""
export_cases skill implementation.

Exports validated semantic cases to various formats.
"""

import sys
import argparse
import dataclasses
from pathlib import Path
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.io_utils import load_yaml, save_jsonl, save_json
from src.commit_semantic.deduplication import deduplicate_cases
from src.commit_semantic.pattern_extraction_v2 import extract_patterns_v2, check_pattern_count
from src.types import CaseRecord, ExportSummary, DomainPatternStat, HighFrequencyPattern


def merge_incremental_export(
    existing_export_path: Path,
    new_cases: list,
    output_path: Path
) -> list:
    """
    Merge new cases into existing export.

    Strategy:
    1. Load existing JSONL export
    2. Append new cases
    3. Write back atomically
    4. Return merged cases

    Args:
        existing_export_path: Path to existing JSONL export
        new_cases: List of new case dicts to append
        output_path: Output path for merged export

    Returns:
        List of all cases (existing + new)
    """
    # Load existing cases
    existing_cases = []
    if existing_export_path.exists():
        try:
            import json
            with open(existing_export_path, 'r', encoding='utf-8') as f:
                existing_cases = [json.loads(line) for line in f if line.strip()]
            print(f"Loaded {len(existing_cases)} existing cases from {existing_export_path}")
        except Exception as e:
            print(f"Warning: Failed to load existing export: {e}")
            print("Starting with empty export")

    # Append new cases
    all_cases = existing_cases + new_cases
    print(f"Merged: {len(existing_cases)} existing + {len(new_cases)} new = {len(all_cases)} total")

    # Write atomically
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix('.jsonl.tmp')

    import json
    with open(tmp_path, 'w', encoding='utf-8') as f:
        for case in all_cases:
            f.write(json.dumps(case, ensure_ascii=False) + '\n')

    tmp_path.rename(output_path)

    return all_cases


def export_cases(
    input_dir: str = "data/semantic_cases",
    output_dir: str = "data/exports",
    invalid_dir: str = "data/invalid_cases",
    low_value_dir: str = "data/low_value_cases",
    incremental: bool = False,
    use_model_optimization: bool = False
):
    """
    Export validated semantic cases to JSONL and generate statistics.

    Performs:
    - Deduplication
    - Pattern extraction
    - Statistics generation
    - Incremental merge (if enabled)

    Args:
        input_dir: Input directory with validated cases
        output_dir: Output directory for exports
        invalid_dir: Directory with invalid cases
        low_value_dir: Directory with low value cases
        incremental: If True, merge with existing export
        use_model_optimization: Enable model-assisted dedup and canonical selection
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    invalid_path = Path(invalid_dir)
    low_value_path = Path(low_value_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    # Load all valid cases
    case_files = list(input_path.glob("*.yaml"))
    print(f"Found {len(case_files)} validated cases")

    cases = []
    for case_file in case_files:
        try:
            case_data = load_yaml(str(case_file))
            cases.append(case_data)
        except Exception as e:
            print(f"Error loading {case_file}: {e}")

    # Handle incremental merge
    jsonl_path = output_path / "cases.jsonl"
    if incremental and jsonl_path.exists():
        print(f"\nIncremental mode: merging with existing export...")
        all_cases = merge_incremental_export(jsonl_path, cases, jsonl_path)
        cases = all_cases
    else:
        print(f"\nFull export mode")

    # Deduplication
    print(f"\nDeduplicating cases...")
    unique_cases, duplicate_groups = deduplicate_cases(cases)
    print(f"  Unique cases: {len(unique_cases)}")
    print(f"  Duplicate groups: {len(duplicate_groups)}")

    # Count total duplicate cases
    total_duplicates = sum(len(group['duplicate_case_ids']) for group in duplicate_groups)
    print(f"  Total duplicate cases: {total_duplicates}")

    # Pattern extraction with P2/P3 enhancements
    print(f"\nExtracting patterns (P2/P3)...")
    patterns, domain_counts = extract_patterns_v2(unique_cases, similarity_threshold=0.50)
    print(f"  Found {len(patterns)} patterns across {len(domain_counts)} domains")

    # Check pattern counts per domain
    pattern_count_status = check_pattern_count(domain_counts)
    for domain, status in pattern_count_status.items():
        count = status['pattern_count']
        status_label = status['pattern_count_status']
        if status_label == 'excellent':
            print(f"  ✓ {domain}: {count} patterns (excellent)")
        elif status_label == 'acceptable':
            print(f"  ✓ {domain}: {count} patterns (acceptable)")
        elif status_label == 'too_high':
            print(f"  ⚠ {domain}: {count} patterns (too high - review abstraction)")
        else:  # critical
            print(f"  ✗ {domain}: {count} patterns (CRITICAL - review urgently)")

    # Export unique cases to JSONL
    save_jsonl(unique_cases, str(jsonl_path))
    print(f"\nExported {len(unique_cases)} unique cases to {jsonl_path}")

    # Export duplicates to JSONL
    duplicates_path = output_path / "duplicates.jsonl"
    save_jsonl(duplicate_groups, str(duplicates_path))
    print(f"Exported {len(duplicate_groups)} duplicate groups to {duplicates_path}")

    # Export patterns to JSONL
    patterns_path = output_path / "patterns.jsonl"
    save_jsonl(patterns, str(patterns_path))
    print(f"Exported {len(patterns)} patterns to {patterns_path}")

    # Generate statistics
    stats = generate_statistics(
        unique_cases,
        duplicate_groups,
        patterns,
        pattern_count_status,
        invalid_path,
        low_value_path
    )

    # Save statistics (serialize dataclass to dict for JSON)
    stats_path = output_path / "summary.json"
    save_json(dataclasses.asdict(stats), str(stats_path))
    print(f"Statistics saved to {stats_path}")

    # Print summary
    print("\n=== Summary ===")
    print(f"Total cases: {stats.total_cases}")
    print(f"Unique cases: {stats.unique_cases}")
    print(f"Duplicate cases: {stats.duplicate_cases} ({stats.duplicate_groups} groups)")
    print(f"Low value cases: {stats.low_value_cases}")
    print(f"Validation pass rate: {stats.validation_pass_rate:.1%}")
    print(f"\nDevelopment type distribution:")
    for dev_type, count in stats.development_type_distribution.items():
        print(f"  {dev_type}: {count}")
    print(f"\nBugfix ratio: {stats.bugfix_ratio:.1%}")
    print(f"Needs split ratio: {stats.needs_split_ratio:.1%}")
    print(f"Pattern count: {stats.pattern_count}")

    # Print domain pattern status
    if stats.domain_pattern_stats:
        print(f"\nDomain pattern status:")
        for domain, domain_stats in stats.domain_pattern_stats.items():
            status = domain_stats['status']
            count = domain_stats['pattern_count']
            action = domain_stats['action']

            if status == 'excellent':
                print(f"  ✓ {domain}: {count} patterns (excellent)")
            elif status == 'acceptable':
                print(f"  ✓ {domain}: {count} patterns (acceptable)")
            elif status == 'too_high':
                print(f"  ⚠ {domain}: {count} patterns (too high)")
                print(f"    → Action: {action}")
            else:  # critical
                print(f"  ✗ {domain}: {count} patterns (CRITICAL)")
                print(f"    → Action: {action}")

    # Print high frequency patterns
    if stats.high_frequency_patterns:
        print(f"\nTop high-frequency patterns:")
        for i, pattern in enumerate(stats.high_frequency_patterns[:5], 1):
            print(f"  {i}. [{pattern['domain']}] {pattern['representative_issue_text'][:60]}... (count: {pattern['count']})")


def generate_statistics(
    unique_cases: list,
    duplicate_groups: list,
    patterns: list,
    pattern_count_status: dict,
    invalid_path: Path,
    low_value_path: Path
) -> ExportSummary:
    """Generate statistics from cases, returned as an ExportSummary dataclass."""
    total_unique = len(unique_cases)
    total_duplicates = sum(len(group['duplicate_case_ids']) for group in duplicate_groups)

    # Count invalid cases
    invalid_files = list(invalid_path.glob("*.yaml")) if invalid_path.exists() else []
    total_invalid = len(invalid_files)

    # Count low value cases
    low_value_files = list(low_value_path.glob("*.yaml")) if low_value_path.exists() else []
    total_low_value = len(low_value_files)

    total_cases = total_unique + total_duplicates + total_invalid
    validation_pass_rate = total_unique / total_cases if total_cases > 0 else 0

    # Development type distribution
    dev_types = [case['development_type'] for case in unique_cases]
    dev_type_dist = dict(Counter(dev_types))

    # Bugfix ratio
    bugfix_count = dev_type_dist.get('bugfix', 0)
    bugfix_ratio = bugfix_count / total_unique if total_unique > 0 else 0

    # Needs split ratio
    needs_split_count = sum(
        1 for case in unique_cases
        if case.get('split_suggestion', {}).get('needs_split', False)
    )
    needs_split_ratio = needs_split_count / total_unique if total_unique > 0 else 0

    # Invalid reasons (if available)
    invalid_reasons = []
    for invalid_file in invalid_files[:10]:  # Sample first 10
        try:
            invalid_data = load_yaml(str(invalid_file))
            if 'validation_error' in invalid_data:
                invalid_reasons.append(invalid_data['validation_error'])
        except Exception as e:
            print(f"Error loading invalid case {invalid_file}: {e}")

    invalid_reason_dist = dict(Counter(invalid_reasons))

    # Pattern statistics by domain
    domain_pattern_stats = {}
    for domain, status in pattern_count_status.items():
        domain_pattern_stats[domain] = dataclasses.asdict(DomainPatternStat(
            pattern_count=status['pattern_count'],
            status=status['pattern_count_status'],
            action=status['action']
        ))

    # High frequency patterns (top 10)
    high_freq_patterns = sorted(patterns, key=lambda p: p['count'], reverse=True)[:10]
    high_freq_summary = [
        dataclasses.asdict(HighFrequencyPattern(
            pattern_id=p['pattern_id'],
            domain=p['domain'],
            count=p['count'],
            representative_issue_text=p['representative_issue_text']
        ))
        for p in high_freq_patterns
    ]

    return ExportSummary(
        total_cases=total_cases,
        unique_cases=total_unique,
        duplicate_cases=total_duplicates,
        duplicate_groups=len(duplicate_groups),
        valid_cases=total_unique,
        invalid_cases=total_invalid,
        low_value_cases=total_low_value,
        validation_pass_rate=validation_pass_rate,
        development_type_distribution=dev_type_dist,
        bugfix_count=bugfix_count,
        bugfix_ratio=bugfix_ratio,
        needs_split_count=needs_split_count,
        needs_split_ratio=needs_split_ratio,
        pattern_count=len(patterns),
        domain_pattern_stats=domain_pattern_stats,
        high_frequency_patterns=high_freq_summary,
        invalid_reason_top_n=invalid_reason_dist
    )


def main():
    parser = argparse.ArgumentParser(description="Export validated semantic cases")
    parser.add_argument("--input-dir", default="data/semantic_cases",
                       help="Input directory with validated cases")
    parser.add_argument("--output-dir", default="data/exports",
                       help="Output directory for exports")
    parser.add_argument("--invalid-dir", default="data/invalid_cases",
                       help="Directory with invalid cases")
    parser.add_argument("--low-value-dir", default="data/low_value_cases",
                       help="Directory with low value cases")
    parser.add_argument("--incremental", action="store_true",
                       help="Merge with existing export (incremental mode)")
    parser.add_argument("--use-model-optimization", action="store_true",
                       help="Enable model-assisted dedup and canonical selection (costs API tokens)")

    args = parser.parse_args()

    export_cases(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        invalid_dir=args.invalid_dir,
        low_value_dir=args.low_value_dir,
        incremental=args.incremental,
        use_model_optimization=args.use_model_optimization
    )


if __name__ == "__main__":
    main()
