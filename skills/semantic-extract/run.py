#!/usr/bin/env python3
"""semantic-extract skill implementation.

Extracts semantic information from git commits - both commit_log and rules/invariants.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.commit_semantic.executor_bridge import get_executor
from src.commit_semantic.git_utils import get_commit_list, get_commit_details, get_commit_message
from src.semantic_extract.writer import (
    load_all_existing_shas,
    append_commit,
    append_rules_invariants,
)
from src.semantic_extract.executor import (
    extract_rules_invariants,
    extract_commit_semantics,
)


def process_commits(
    repo_path: str,
    commit_ids: list,
    view: str = "both",
    incremental: bool = False,
    dry_run: bool = False,
    executor_fn=None,
):
    """Process commits and extract semantic information."""

    # Load existing SHAs for deduplication
    commit_shas, rules_shas = load_all_existing_shas() if incremental else (set(), set())

    stats = {
        "total": len(commit_ids),
        "commit_processed": 0,
        "commit_skipped": 0,
        "commit_errors": 0,
        "rules_processed": 0,
        "rules_skipped": 0,
        "rules_errors": 0,
    }

    for idx, commit_id in enumerate(commit_ids):
        print(f"Processing {idx + 1}/{len(commit_ids)}: {commit_id[:8]}...")

        try:
            # Get commit details
            commit = get_commit_details(repo_path, commit_id)
            diff = "\n".join(commit.diff_chunks)

            # Get commit message
            commit_msg = get_commit_message(repo_path, commit_id)

            # Convert Unix timestamp to ISO format for filename
            commit_date = datetime.fromtimestamp(int(commit.timestamp)).isoformat()

            # Extract commit view
            if view in ("both", "commit"):
                if commit_id in commit_shas:
                    stats["commit_skipped"] += 1
                    print(f"  [SKIP] commit already exists")
                else:
                    try:
                        title, body, commit_log = extract_commit_semantics(
                            diff, commit_msg, executor_fn
                        )
                        if not dry_run:
                            append_commit(commit_id, title, body, commit_log, commit_date)
                        stats["commit_processed"] += 1
                        print(f"  [OK] commit: {title[:50]}...")
                    except Exception as e:
                        stats["commit_errors"] += 1
                        print(f"  [ERROR] commit: {e}")

            # Extract rules view
            if view in ("both", "rules"):
                if commit_id in rules_shas:
                    stats["rules_skipped"] += 1
                    print(f"  [SKIP] rules already exists")
                else:
                    try:
                        rules, invariants = extract_rules_invariants(
                            diff, commit_msg, executor_fn
                        )
                        if not dry_run:
                            append_rules_invariants(commit_id, rules, invariants, commit_date)
                        stats["rules_processed"] += 1
                        print(f"  [OK] rules: {len(rules)} rules, {len(invariants)} invariants")
                    except Exception as e:
                        stats["rules_errors"] += 1
                        print(f"  [ERROR] rules: {e}")

        except Exception as e:
            print(f"  [ERROR] {e}")
            stats["commit_errors"] += 1
            stats["rules_errors"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Extract semantic information from git commits")
    parser.add_argument("repo_path", help="Path to git repository")
    parser.add_argument("--last", type=int, help="Process last N commits")
    parser.add_argument("--since", help="Process commits since date (YYYY-MM-DD)")
    parser.add_argument("--until", help="Process commits until date (YYYY-MM-DD)")
    parser.add_argument("--range", help="Process commit range (SHA1..SHA2)")
    parser.add_argument("--view", choices=["both", "commit", "rules"], default="both",
                       help="Which view to extract")
    parser.add_argument("--incremental", action="store_true",
                       help="Skip already processed commits")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview without writing")

    args = parser.parse_args()

    # Get commit list
    commit_ids = get_commit_list(
        repo_path=args.repo_path,
        commit_range=args.range,
        since=args.since,
        until=args.until,
    )

    if args.last:
        commit_ids = commit_ids[:args.last]

    print(f"Found {len(commit_ids)} commits to process")

    # Get executor from bridge (set by Claude Code host)
    executor_fn = get_executor()
    if executor_fn is None:
        print("ERROR: No executor configured. Please run via Claude Code with executor injection.")
        sys.exit(1)

    start_time = time.time()

    stats = process_commits(
        repo_path=args.repo_path,
        commit_ids=commit_ids,
        view=args.view,
        incremental=args.incremental,
        dry_run=args.dry_run,
        executor_fn=executor_fn,
    )

    elapsed = time.time() - start_time

    # Print summary
    print("\n=== Semantic Extract Summary ===")
    print(f"Total commits: {stats['total']}")
    print(f"Commit view: processed={stats['commit_processed']}, skipped={stats['commit_skipped']}, errors={stats['commit_errors']}")
    print(f"Rules view: processed={stats['rules_processed']}, skipped={stats['rules_skipped']}, errors={stats['rules_errors']}")
    print(f"Time elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
