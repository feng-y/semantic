from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.demand.run import run_demand_pipeline
from src.demand.stage_registry import STAGES


def _semantic_assets() -> dict:
    return {
        "domain_map": {"domains": [{"name": "FS DSL"}, {"name": "Parser"}]},
        "concept_map": {"concepts": [{"name": "hash_to_context operator"}, {"name": "syntax parser"}]},
        "rule_map": {"rules": [{"name": "parser compatibility"}, {"name": "api stability"}]},
        "invariants": ["legacy syntax must remain parseable"],
    }


def test_run_demand_pipeline_success_and_structure() -> None:
    result = run_demand_pipeline(
        issue_id="ISSUE-2000",
        issue_text="Add hash_to_context operator in FS DSL",
        semantic_assets=_semantic_assets(),
    )

    assert result["ok"] is True
    assert result["failed_stage"] is None
    assert result["validation_errors"] == []
    assert result["demand_card"] is not None
    assert result["stage_order"] == STAGES
    assert [s["stage"] for s in result["stages"]] == STAGES
    assert all(s["status"] == "ok" for s in result["stages"])
    assert result["intermediate"]["normalized_issue"] is not None
    assert result["intermediate"]["semantic_mapping"] is not None
    assert result["intermediate"]["development_type_match"] is not None


def test_run_demand_pipeline_surfaces_normalize_failure() -> None:
    result = run_demand_pipeline(
        issue_id="ISSUE-2001",
        issue_text="   ",
        semantic_assets=_semantic_assets(),
    )

    assert result["ok"] is False
    assert result["failed_stage"] == "normalize_issue"
    assert "issue_text" in result["error"]
    assert len(result["stages"]) == 1
    assert result["stages"][0]["status"] == "failed"


def test_run_demand_pipeline_surfaces_validation_failure() -> None:
    with patch("src.demand.run.validate_demand_card", return_value=["invalid card"]):
        result = run_demand_pipeline(
            issue_id="ISSUE-2002",
            issue_text="Fix parser compatibility bug",
            semantic_assets=_semantic_assets(),
        )

    assert result["ok"] is False
    assert result["failed_stage"] == "validate_demand_card"
    assert result["validation_errors"] == ["invalid card"]
    assert result["demand_card"] is not None


def test_run_demand_pipeline_failure_result_shape_stable() -> None:
    with patch("src.demand.run.map_semantics", side_effect=ValueError("mapping error")):
        result = run_demand_pipeline(
            issue_id="ISSUE-2003",
            issue_text="Add operator",
            semantic_assets=_semantic_assets(),
        )

    assert result["ok"] is False
    assert result["failed_stage"] == "map_semantics"
    assert set(result.keys()) == {
        "ok",
        "issue_id",
        "demand_card",
        "validation_errors",
        "failed_stage",
        "error",
        "stage_order",
        "stages",
        "intermediate",
    }


def test_run_demand_pipeline_surfaces_build_failure() -> None:
    with patch("src.demand.run.build_demand_card", side_effect=ValueError("build error")):
        result = run_demand_pipeline(
            issue_id="ISSUE-2004",
            issue_text="Add operator",
            semantic_assets=_semantic_assets(),
        )

    assert result["ok"] is False
    assert result["failed_stage"] == "build_demand_card"
    assert "build error" in result["error"]
