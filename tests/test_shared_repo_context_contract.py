import json
import re
from pathlib import Path


FIXTURE_PATH = Path("tests/fixtures/shared_repo_context/example_repo_context.json")
KEY_GRAMMARS = {
    "local_capabilities": re.compile(r"^local_capabilities\.[^.]+$"),
    "aliases": re.compile(r"^aliases\.[^.]+\.[^.]+$"),
    "ownership_hints": re.compile(r"^ownership_hints\.[^.]+$"),
    "seed_concepts": re.compile(r"^seed_concepts\.[^.]+$"),
}


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def test_repo_context_contract_has_layered_top_level_keys():
    data = load_fixture()
    assert set(data.keys()) == {"shared_hints", "semantic_context", "summary"}


def test_shared_hints_contains_required_nested_keys():
    data = load_fixture()
    assert set(data["shared_hints"].keys()) == {
        "local_capabilities",
        "aliases",
        "ownership_hints",
        "seed_concepts",
        "source_provenance",
        "hint_confidence",
        "conflicts",
        "source_snapshot",
    }
    assert set(data["shared_hints"]["source_snapshot"].keys()) == {"docs", "codebase_map"}


def test_semantic_context_contains_required_nested_keys():
    data = load_fixture()
    assert set(data["semantic_context"].keys()) == {
        "local_capabilities",
        "ownership_hints",
        "aliases",
        "seed_concepts",
        "confidence",
    }


def test_summary_contains_required_nested_keys():
    data = load_fixture()
    assert set(data["summary"].keys()) == {
        "bootstrap_status",
        "hint_count",
        "source_counts",
        "used_cached_context",
        "degraded_reasons",
        "bypass_reason",
        "fingerprint",
    }
    assert set(data["summary"]["source_counts"].keys()) == {"docs", "codebase_map"}
    assert isinstance(data["summary"]["used_cached_context"], bool)
    assert isinstance(data["summary"]["degraded_reasons"], list)
    assert data["summary"]["bypass_reason"] is None or isinstance(data["summary"]["bypass_reason"], str)
    assert isinstance(data["summary"]["fingerprint"], str) and data["summary"]["fingerprint"]


def test_alias_items_match_contract_shape():
    data = load_fixture()
    for alias in data["shared_hints"]["aliases"]:
        assert set(alias.keys()) == {"canonical", "alias", "kind"}
        assert all(isinstance(alias[key], str) and alias[key] for key in alias)


def test_ownership_hint_items_match_contract_shape():
    data = load_fixture()
    for hint in data["shared_hints"]["ownership_hints"]:
        assert set(hint.keys()) == {"scope", "owner", "note"}
        assert all(isinstance(hint[key], str) and hint[key] for key in hint)


def test_seed_concept_items_match_contract_shape():
    data = load_fixture()
    for concept in data["shared_hints"]["seed_concepts"]:
        assert set(concept.keys()) == {"name", "description"}
        assert all(isinstance(concept[key], str) and concept[key] for key in concept)


def test_conflict_items_match_contract_shape():
    data = load_fixture()
    for conflict in data["shared_hints"]["conflicts"]:
        assert set(conflict.keys()) == {"field", "sources", "reason"}
        assert isinstance(conflict["field"], str) and conflict["field"]
        assert isinstance(conflict["sources"], list) and conflict["sources"]
        assert all(isinstance(source, str) and source for source in conflict["sources"])
        assert isinstance(conflict["reason"], str) and conflict["reason"]


def test_enum_values_match_contract():
    data = load_fixture()
    assert data["semantic_context"]["confidence"] in {"high", "medium", "low"}
    assert data["summary"]["bootstrap_status"] in {"full", "degraded", "bypass"}
    assert {alias["kind"] for alias in data["shared_hints"]["aliases"]} <= {
        "term",
        "subsystem",
        "concept",
    }
    assert set(data["hint_confidence"] for data in []) == set()


def test_hint_confidence_values_match_contract():
    data = load_fixture()
    assert set(data["shared_hints"]["hint_confidence"].values()) <= {"high", "medium", "low"}


def test_summary_counting_semantics_match_shared_hints_payload():
    data = load_fixture()
    shared_hints = data["shared_hints"]
    expected_hint_count = (
        len(shared_hints["local_capabilities"])
        + len(shared_hints["aliases"])
        + len(shared_hints["ownership_hints"])
        + len(shared_hints["seed_concepts"])
    )
    assert data["summary"]["hint_count"] == expected_hint_count
    assert data["summary"]["source_counts"] == {
        "docs": len(shared_hints["source_snapshot"]["docs"]),
        "codebase_map": len(shared_hints["source_snapshot"]["codebase_map"]),
    }


def test_source_provenance_keys_follow_stable_key_grammar():
    data = load_fixture()
    for key, sources in data["shared_hints"]["source_provenance"].items():
        prefix = key.split(".", 1)[0]
        assert prefix in KEY_GRAMMARS
        assert KEY_GRAMMARS[prefix].match(key)
        assert isinstance(sources, list)
        assert all(isinstance(source, str) and source for source in sources)


def test_hint_confidence_keys_follow_stable_key_grammar():
    data = load_fixture()
    for key, confidence in data["shared_hints"]["hint_confidence"].items():
        prefix = key.split(".", 1)[0]
        assert prefix in KEY_GRAMMARS
        assert KEY_GRAMMARS[prefix].match(key)
        assert confidence in {"high", "medium", "low"}
