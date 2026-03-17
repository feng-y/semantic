"""Demand pipeline runner (PR3 orchestration entry)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .build_demand_card import build_demand_card, write_demand_card
from .map_semantics import load_semantic_foundation_assets, map_semantics
from .match_development_type import match_development_type
from .normalize_issue import normalize_issue
from .stage_registry import STAGES
from .validate_demand_card import validate_demand_card


def _base_result(issue_id: str) -> dict[str, Any]:
    return {
        "ok": False,
        "issue_id": issue_id,
        "demand_card": None,
        "validation_errors": [],
        "failed_stage": None,
        "error": None,
        "stage_order": list(STAGES),
        "stages": [],
        "intermediate": {
            "normalized_issue": None,
            "semantic_mapping": None,
            "development_type_match": None,
        },
    }


def _mark_stage(result: dict[str, Any], stage: str, status: str, error: str | None = None) -> None:
    result["stages"].append(
        {
            "stage": stage,
            "status": status,
            "error": error,
        }
    )


def run_demand_pipeline(
    *,
    issue_id: str,
    issue_text: str,
    semantic_assets: dict[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Run normalize -> map -> match -> build -> validate and return structured result."""
    result = _base_result(issue_id=issue_id)

    try:
        normalized_issue = normalize_issue(issue_id=issue_id, issue_text=issue_text)
        result["intermediate"]["normalized_issue"] = normalized_issue
        result["issue_id"] = normalized_issue["issue_id"]
        _mark_stage(result, "normalize_issue", "ok")
    except Exception as exc:
        result["failed_stage"] = "normalize_issue"
        result["error"] = str(exc)
        _mark_stage(result, "normalize_issue", "failed", str(exc))
        return result

    assets = semantic_assets
    if assets is None:
        assets = load_semantic_foundation_assets(repo_root or ".")

    try:
        semantic_mapping = map_semantics(
            issue_text=normalized_issue["issue_text"],
            semantic_assets=assets,
        )
        result["intermediate"]["semantic_mapping"] = semantic_mapping
        _mark_stage(result, "map_semantics", "ok")
    except Exception as exc:
        result["failed_stage"] = "map_semantics"
        result["error"] = str(exc)
        _mark_stage(result, "map_semantics", "failed", str(exc))
        return result

    try:
        development_type_match = match_development_type(
            issue_text=normalized_issue["issue_text"],
            semantic_mapping=semantic_mapping,
            demand_model_map=(assets or {}).get("demand_model_map", {}),
        )
        result["intermediate"]["development_type_match"] = development_type_match
        _mark_stage(result, "match_development_type", "ok")
    except Exception as exc:
        result["failed_stage"] = "match_development_type"
        result["error"] = str(exc)
        _mark_stage(result, "match_development_type", "failed", str(exc))
        return result

    try:
        demand_card = build_demand_card(
            issue_id=normalized_issue["issue_id"],
            issue_text=normalized_issue["issue_text"],
            domains=semantic_mapping["domains"],
            concepts=semantic_mapping["concepts"],
            rules=semantic_mapping["rules"],
            invariants=semantic_mapping["invariants"],
            development_type=development_type_match["development_type"],
            open_questions=development_type_match["open_questions"],
        )
        result["demand_card"] = demand_card
        _mark_stage(result, "build_demand_card", "ok")
    except Exception as exc:
        result["failed_stage"] = "build_demand_card"
        result["error"] = str(exc)
        _mark_stage(result, "build_demand_card", "failed", str(exc))
        return result

    validation_errors = validate_demand_card(demand_card)
    result["validation_errors"] = validation_errors
    if validation_errors:
        result["failed_stage"] = "validate_demand_card"
        result["error"] = "validation failed"
        _mark_stage(result, "validate_demand_card", "failed", "validation failed")
        return result

    result["ok"] = True
    _mark_stage(result, "validate_demand_card", "ok")
    return result


def run_and_write_demand_pipeline(
    *,
    issue_id: str,
    issue_text: str,
    output_path: str | Path,
    semantic_assets: dict[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Run demand pipeline and write demand card if successful."""
    result = run_demand_pipeline(
        issue_id=issue_id,
        issue_text=issue_text,
        semantic_assets=semantic_assets,
        repo_root=repo_root,
    )
    if result["ok"] and result["demand_card"] is not None:
        write_demand_card(result["demand_card"], output_path=output_path)
        result["output_path"] = str(Path(output_path))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run demand pipeline")
    parser.add_argument("--issue-id", required=True)
    parser.add_argument("--issue-text", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default=None, help="Optional output path for demand-card.yaml")
    args = parser.parse_args(argv)

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
