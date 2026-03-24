import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "commit_extract_bootstrap"
SHARED_FIXTURE = Path(__file__).parent / "fixtures" / "shared_repo_context" / "example_repo_context.json"
INVALID_RUNTIME_SUMMARY_FIXTURE = Path(__file__).parent / "fixtures" / "shared_repo_context" / "invalid_runtime_summary.json"


@pytest.fixture
def bootstrap_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "commit_extract_bootstrap_quality_gates",
        str(Path(__file__).parent.parent / "skills" / "commit-extract" / "bootstrap.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_bootstrap_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def load_shared_fixture() -> dict:
    return json.loads(SHARED_FIXTURE.read_text())


def load_invalid_runtime_summary_fixture() -> dict:
    return json.loads(INVALID_RUNTIME_SUMMARY_FIXTURE.read_text())


def test_final_summary_contract_fields_are_present_in_shared_fixture():
    data = load_shared_fixture()
    summary = data["summary"]

    assert summary["bootstrap_status"] in {"full", "degraded", "bypass"}
    assert isinstance(summary["hint_count"], int)
    assert set(summary["source_counts"].keys()) == {"docs", "codebase_map"}
    assert isinstance(summary["used_cached_context"], bool)
    assert isinstance(summary["degraded_reasons"], list)
    assert summary["bypass_reason"] is None or isinstance(summary["bypass_reason"], str)
    assert isinstance(summary["fingerprint"], str) and summary["fingerprint"]


def test_hint_count_and_source_counts_match_shared_fixture_payload():
    data = load_shared_fixture()
    shared_hints = data["shared_hints"]
    summary = data["summary"]

    expected_hint_count = (
        len(shared_hints["local_capabilities"])
        + len(shared_hints["aliases"])
        + len(shared_hints["ownership_hints"])
        + len(shared_hints["seed_concepts"])
    )
    assert summary["hint_count"] == expected_hint_count
    assert summary["source_counts"] == {
        "docs": len(shared_hints["source_snapshot"]["docs"]),
        "codebase_map": len(shared_hints["source_snapshot"]["codebase_map"]),
    }


def test_helper_and_runtime_agree_on_persisted_bypass(bootstrap_module):
    fixture = load_bootstrap_fixture("example_bootstrap_context.json")
    fixture["summary"]["bootstrap_status"] = "bypass"
    fixture["summary"]["bypass_reason"] = "skip-bootstrap"
    fixture["shared_hints"]["local_capabilities"] = []

    mode = bootstrap_module.determine_bootstrap_mode(
        fixture,
        current_fingerprint=fixture["summary"]["fingerprint"],
    )

    assert mode == {
        "bootstrap_status": "bypass",
        "used_cached_context": False,
        "degraded_reasons": [],
        "bypass_reason": "skip-bootstrap",
    }


def test_helper_and_runtime_agree_on_degraded_reason_shape(bootstrap_module):
    fixture = load_bootstrap_fixture("degraded_repo_context.json")

    mode = bootstrap_module.determine_bootstrap_mode(
        fixture,
        current_fingerprint=fixture["summary"]["fingerprint"],
    )

    assert mode["bootstrap_status"] == "degraded"
    assert mode["used_cached_context"] is True
    assert mode["degraded_reasons"] == ["reduced-shared-hints"]
    assert mode["bypass_reason"] is None


def test_invalid_runtime_summary_fixture_is_explicitly_rejected(bootstrap_module):
    fixture = load_invalid_runtime_summary_fixture()

    mode = bootstrap_module.determine_bootstrap_mode(
        fixture,
        current_fingerprint=fixture["summary"]["fingerprint"],
    )

    assert mode == {
        "bootstrap_status": "bypass",
        "used_cached_context": False,
        "degraded_reasons": [],
        "bypass_reason": "invalid-bootstrap-status",
    }


def test_helper_reports_reused_full_context_as_cached(bootstrap_module, tmp_path):
    fixture = load_bootstrap_fixture("example_bootstrap_context.json")
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("Instructions\n", encoding="utf-8")
    planning = tmp_path / ".planning" / "codebase"
    planning.mkdir(parents=True)
    (planning / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")

    fingerprint = bootstrap_module.compute_bootstrap_fingerprint(tmp_path)
    fixture["summary"] = bootstrap_module.build_reliability_summary(
        fixture["shared_hints"],
        fingerprint=fingerprint,
        bootstrap_status="full",
        used_cached_context=False,
    )

    mode = bootstrap_module.determine_bootstrap_mode(
        fixture,
        current_fingerprint=fingerprint,
    )

    assert mode["bootstrap_status"] == "full"
    assert mode["used_cached_context"] is True
