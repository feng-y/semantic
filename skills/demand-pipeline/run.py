#!/usr/bin/env python3
"""
demand-pipeline skill implementation.

Runs the demand pipeline: normalize -> map -> match -> build -> validate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.demand.run import run_demand_pipeline, run_and_write_demand_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run demand pipeline")
    parser.add_argument("--issue-id", required=True)
    parser.add_argument("--issue-text", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output path for demand-card.yaml",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=True,
        help="Output structured JSON result (default)",
    )
    args = parser.parse_args()

    if args.output:
        result = run_and_write_demand_pipeline(
            issue_id=args.issue_id,
            issue_text=args.issue_text,
            output_path=args.output,
            repo_root=args.repo_root,
        )
    else:
        result = run_demand_pipeline(
            issue_id=args.issue_id,
            issue_text=args.issue_text,
            repo_root=args.repo_root,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
