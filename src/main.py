"""CLI entry point for Semantic Harness."""

from __future__ import annotations

import argparse
import json
import sys

from . import dispatcher


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="semantic-harness",
        description="Semantic Harness v1 — semantic construction for repositories",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Repository root (default: current directory)",
    )

    sub = parser.add_subparsers(dest="command")

    # init
    sub.add_parser("init", help="Initialize semantic harness directory structure")

    # discover
    disc = sub.add_parser("discover", help="Run semantic discovery")
    disc.add_argument(
        "--sampling-mode",
        choices=["auto", "confirm"],
        default="auto",
        help="Sampling mode (default: auto)",
    )
    disc.add_argument(
        "--sampling-timeout",
        type=int,
        default=None,
        help="Sampling timeout in seconds",
    )

    # refine
    sub.add_parser("refine", help="Run semantic refinement")

    # status
    sub.add_parser("status", help="Show current semantic state")

    # reset
    sub.add_parser("reset", help="Reset working state (preserves baseline and schemas)")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    kwargs = {}
    if args.command == "discover":
        kwargs["sampling_mode"] = args.sampling_mode
        kwargs["sampling_timeout"] = args.sampling_timeout

    result = dispatcher.dispatch(args.command, args.root, **kwargs)
    print(json.dumps(result, indent=2))
    failure_statuses = {
        "error", "validation_failed", "execution_unavailable",
        "version_skew", "acceptance_failed",
    }
    return 0 if result.get("status") not in failure_statuses else 1


if __name__ == "__main__":
    sys.exit(main())
