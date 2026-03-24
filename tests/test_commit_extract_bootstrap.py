import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.io_utils import load_json


FIXTURE_PATH = Path("tests/fixtures/commit_extract_bootstrap/example_bootstrap_context.json")


@pytest.fixture
def bootstrap_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "commit_extract_bootstrap",
        str(Path(__file__).parent.parent / "skills" / "commit-extract" / "bootstrap.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def test_collect_bootstrap_sources_reads_fixed_repo_docs(tmp_path, bootstrap_module):
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("repo instructions\n", encoding="utf-8")

    sources = bootstrap_module.read_bootstrap_sources(tmp_path)

    assert [item["path"] for item in sources["docs"]] == ["README.md", "CLAUDE.md"]


def test_collect_bootstrap_sources_reads_planning_codebase_files(tmp_path, bootstrap_module):
    planning = tmp_path / ".planning" / "codebase"
    planning.mkdir(parents=True)
    (planning / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
    (planning / "MODULES.md").write_text("# Modules\n", encoding="utf-8")

    sources = bootstrap_module.read_bootstrap_sources(tmp_path)

    assert [item["path"] for item in sources["codebase_map"]] == [
        ".planning/codebase/ARCHITECTURE.md",
        ".planning/codebase/MODULES.md",
    ]


def test_collect_bootstrap_sources_skips_missing_inputs(tmp_path, bootstrap_module):
    sources = bootstrap_module.read_bootstrap_sources(tmp_path)

    assert sources == {"docs": [], "codebase_map": []}


def test_build_bootstrap_context_writes_layered_contract(tmp_path, bootstrap_module):
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    planning = tmp_path / ".planning" / "codebase"
    planning.mkdir(parents=True)
    (planning / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")

    output_path = tmp_path / "data" / "commit-extract" / "repo-context.json"
    context = bootstrap_module.build_bootstrap_context(tmp_path)
    bootstrap_module.write_bootstrap_context(output_path, context)

    written = load_json(str(output_path))
    assert set(written.keys()) == {"shared_hints", "semantic_context", "summary"}
    assert set(written["shared_hints"]["source_snapshot"].keys()) == {"docs", "codebase_map"}
    assert written["summary"] == {
        "bootstrap_status": "full",
        "hint_count": 0,
        "source_counts": {"docs": 1, "codebase_map": 1},
        "used_cached_context": False,
        "degraded_reasons": [],
        "bypass_reason": None,
        "fingerprint": bootstrap_module.compute_bootstrap_fingerprint(tmp_path),
    }


def test_bootstrap_builds_shared_hints_for_prompt_injection(bootstrap_module):
    fixture = load_fixture()

    payload = bootstrap_module.extract_shared_hints_for_prompt(fixture)
    payload["local_capabilities"].append("mutated-capability")
    payload["source_snapshot"]["docs"].append("MUTATED.md")

    assert payload != fixture["shared_hints"]
    assert payload is not fixture["shared_hints"]
    assert fixture["shared_hints"]["local_capabilities"] == ["commit-extract", "commit-semantic"]
    assert fixture["shared_hints"]["source_snapshot"]["docs"] == ["README.md", "CLAUDE.md"]
    assert "semantic_context" not in payload
    assert "summary" not in payload


def test_contract_counting_semantics_match_shared_hints_payload(bootstrap_module):
    fixture = load_fixture()

    summary = bootstrap_module.compute_bootstrap_summary(fixture["shared_hints"])

    assert summary == {
        "bootstrap_status": "full",
        "hint_count": fixture["summary"]["hint_count"],
        "source_counts": fixture["summary"]["source_counts"],
    }
    assert summary["hint_count"] == (
        len(fixture["shared_hints"]["local_capabilities"])
        + len(fixture["shared_hints"]["aliases"])
        + len(fixture["shared_hints"]["ownership_hints"])
        + len(fixture["shared_hints"]["seed_concepts"])
    )


def test_fixture_matches_shared_repo_context_contract_counting_rules():
    fixture = load_fixture()

    assert set(fixture.keys()) == {"shared_hints", "semantic_context", "summary"}
    assert fixture["summary"] == {
        "bootstrap_status": "full",
        "hint_count": 5,
        "source_counts": {"docs": 2, "codebase_map": 1},
        "used_cached_context": False,
        "degraded_reasons": [],
        "bypass_reason": None,
        "fingerprint": "bootstrap-example-fingerprint",
    }
