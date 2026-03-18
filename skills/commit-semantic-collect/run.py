#!/usr/bin/env python3
"""
commit-semantic-collect skill implementation.

Extracts semantic cases from git history.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.commit_semantic.git_utils import get_commit_list, get_commit_details
from src.commit_semantic.grouping import extract_change_groups, detect_bugfix_evidence
from src.commit_semantic.semantic_case_builder import build_semantic_cases
from src.io_utils import save_yaml, semantic_case_input_to_dict


def collect_cases(
    repo_path: str,
    commit_range: str = None,
    author: str = None,
    since: str = None,
    until: str = None,
    output_dir: str = "data/semantic_case_inputs"
):
    """
    Main function to collect semantic cases from git history.
    """
    print(f"Collecting commits from {repo_path}...")

    # Get commit list
    commit_ids = get_commit_list(
        repo_path=repo_path,
        commit_range=commit_range,
        author=author,
        since=since,
        until=until
    )

    print(f"Found {len(commit_ids)} commits")

    all_cases = []

    for idx, commit_id in enumerate(commit_ids):
        print(f"Processing commit {idx + 1}/{len(commit_ids)}: {commit_id[:8]}...")

        try:
            # Get commit details
            commit = get_commit_details(repo_path, commit_id)

            # Extract change groups
            groups = extract_change_groups(commit)

            # Detect bugfix evidence
            diff_text = '\n'.join(commit.diff_chunks)
            bugfix_evidence = detect_bugfix_evidence(commit, diff_text)

            # Build semantic cases
            cases = build_semantic_cases(commit_id, groups, bugfix_evidence)

            all_cases.extend(cases)

            print(f"  Generated {len(cases)} semantic case(s)")

        except Exception as e:
            print(f"  Error processing commit {commit_id}: {e}")
            continue

    # Save cases
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for case in all_cases:
        case_file = output_path / f"{case.case_id}.yaml"
        save_yaml(semantic_case_input_to_dict(case), str(case_file))

    print(f"\nCollected {len(all_cases)} semantic cases")
    print(f"Saved to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Collect semantic cases from git history")
    parser.add_argument("repo_path", help="Path to git repository")
    parser.add_argument("--commit-range", help="Commit range (e.g., HEAD~10..HEAD)")
    parser.add_argument("--author", help="Filter by author")
    parser.add_argument("--since", help="Filter by date (e.g., '2024-01-01')")
    parser.add_argument("--until", help="Filter by date (e.g., '2024-12-31')")
    parser.add_argument("--output-dir", default="data/semantic_case_inputs",
                       help="Output directory for semantic case inputs")

    args = parser.parse_args()

    collect_cases(
        repo_path=args.repo_path,
        commit_range=args.commit_range,
        author=args.author,
        since=args.since,
        until=args.until,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
