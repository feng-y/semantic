#!/usr/bin/env python3
"""
export_cases skill implementation.

Exports validated semantic cases to various formats.
"""

import sys
import argparse
from pathlib import Path
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.io_utils import load_yaml, save_jsonl, save_json


def export_cases(
    input_dir: str = "data/semantic_cases",
    output_dir: str = "data/exports",
    invalid_dir: str = "data/invalid_cases"
):
    """
    Export validated semantic cases to JSONL and generate statistics.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    invalid_path = Path(invalid_dir)

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

    # Export to JSONL
    jsonl_path = output_path / "cases.jsonl"
    save_jsonl(cases, str(jsonl_path))
    print(f"Exported {len(cases)} cases to {jsonl_path}")

    # Generate statistics
    stats = generate_statistics(cases, invalid_path)

    # Save statistics
    stats_path = output_path / "summary.json"
    save_json(stats, str(stats_path))
    print(f"Statistics saved to {stats_path}")

    # Print summary
    print("\n=== Summary ===")
    print(f"Total cases: {stats['total_cases']}")
    print(f"Validation pass rate: {stats['validation_pass_rate']:.1%}")
    print(f"\nDevelopment type distribution:")
    for dev_type, count in stats['development_type_distribution'].items():
        print(f"  {dev_type}: {count}")
    print(f"\nBugfix ratio: {stats['bugfix_ratio']:.1%}")
    print(f"Needs split ratio: {stats['needs_split_ratio']:.1%}")


def generate_statistics(cases: list, invalid_path: Path) -> dict:
    """Generate statistics from cases."""
    total_valid = len(cases)

    # Count invalid cases
    invalid_files = list(invalid_path.glob("*.yaml")) if invalid_path.exists() else []
    total_invalid = len(invalid_files)

    total_cases = total_valid + total_invalid
    validation_pass_rate = total_valid / total_cases if total_cases > 0 else 0

    # Development type distribution
    dev_types = [case['development_type'] for case in cases]
    dev_type_dist = dict(Counter(dev_types))

    # Bugfix ratio
    bugfix_count = dev_type_dist.get('bugfix', 0)
    bugfix_ratio = bugfix_count / total_valid if total_valid > 0 else 0

    # Needs split ratio
    needs_split_count = sum(
        1 for case in cases
        if case.get('split_suggestion', {}).get('needs_split', False)
    )
    needs_split_ratio = needs_split_count / total_valid if total_valid > 0 else 0

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

    return {
        'total_cases': total_cases,
        'valid_cases': total_valid,
        'invalid_cases': total_invalid,
        'validation_pass_rate': validation_pass_rate,
        'development_type_distribution': dev_type_dist,
        'bugfix_count': bugfix_count,
        'bugfix_ratio': bugfix_ratio,
        'needs_split_count': needs_split_count,
        'needs_split_ratio': needs_split_ratio,
        'invalid_reason_top_n': invalid_reason_dist
    }


def main():
    parser = argparse.ArgumentParser(description="Export validated semantic cases")
    parser.add_argument("--input-dir", default="data/semantic_cases",
                       help="Input directory with validated cases")
    parser.add_argument("--output-dir", default="data/exports",
                       help="Output directory for exports")
    parser.add_argument("--invalid-dir", default="data/invalid_cases",
                       help="Directory with invalid cases")

    args = parser.parse_args()

    export_cases(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        invalid_dir=args.invalid_dir
    )


if __name__ == "__main__":
    main()
