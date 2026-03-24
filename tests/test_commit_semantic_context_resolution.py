import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


FIXTURE_PATH = Path("tests/fixtures/commit_semantic_consumer/shared_extract_repo_context.json")


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def load_commit_semantic_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "commit_semantic_resolution_test",
        str(Path(__file__).parent.parent / "skills" / "commit-semantic" / "run.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_load_repo_context_prefers_shared_extract_artifact(tmp_path):
    mod = load_commit_semantic_module()
    extract_dir = tmp_path / "data" / "commit-extract"
    semantic_dir = tmp_path / "data" / "commit-semantic"
    extract_dir.mkdir(parents=True)
    semantic_dir.mkdir(parents=True)

    shared_payload = load_fixture()
    local_payload = {
        "semantic_context": {
            "local_capabilities": ["local-semantic"],
            "ownership_hints": [{"capability": "commit-semantic"}],
            "aliases": [],
            "seed_concepts": [],
            "confidence": "low",
        }
    }
    (extract_dir / "repo-context.json").write_text(json.dumps(shared_payload), encoding="utf-8")
    (semantic_dir / "repo-context.json").write_text(json.dumps(local_payload), encoding="utf-8")

    mod.EXTRACT_OUTPUT = extract_dir
    mod.SEMANTIC_OUTPUT = semantic_dir
    runner = mod.CommitSemanticRunner()

    resolved = runner._load_repo_context()

    assert resolved == shared_payload["semantic_context"]
    assert resolved["local_capabilities"] == ["shared-extract", "commit-extract"]


def test_load_repo_context_falls_back_to_local_semantic_artifact(tmp_path):
    mod = load_commit_semantic_module()
    extract_dir = tmp_path / "data" / "commit-extract"
    semantic_dir = tmp_path / "data" / "commit-semantic"
    extract_dir.mkdir(parents=True)
    semantic_dir.mkdir(parents=True)

    local_payload = {
        "shared_hints": {
            "local_capabilities": ["local-semantic"],
            "aliases": [],
            "ownership_hints": [],
            "seed_concepts": [],
            "source_provenance": {},
            "hint_confidence": {},
            "conflicts": [],
            "source_snapshot": {"docs": [], "codebase_map": []},
        },
        "semantic_context": {
            "local_capabilities": ["local-semantic"],
            "ownership_hints": [{"capability": "commit-semantic"}],
            "aliases": [],
            "seed_concepts": [],
            "confidence": "medium",
        },
        "summary": {
            "bootstrap_status": "degraded",
            "hint_count": 1,
            "source_counts": {"docs": 0, "codebase_map": 0},
        },
    }
    (semantic_dir / "repo-context.json").write_text(json.dumps(local_payload), encoding="utf-8")

    mod.EXTRACT_OUTPUT = extract_dir
    mod.SEMANTIC_OUTPUT = semantic_dir
    runner = mod.CommitSemanticRunner()

    resolved = runner._load_repo_context()

    assert resolved == local_payload["semantic_context"]
    assert resolved["local_capabilities"] == ["local-semantic"]


def test_load_repo_context_returns_empty_when_no_artifacts_exist(tmp_path):
    mod = load_commit_semantic_module()
    extract_dir = tmp_path / "data" / "commit-extract"
    semantic_dir = tmp_path / "data" / "commit-semantic"
    extract_dir.mkdir(parents=True)
    semantic_dir.mkdir(parents=True)

    mod.EXTRACT_OUTPUT = extract_dir
    mod.SEMANTIC_OUTPUT = semantic_dir
    runner = mod.CommitSemanticRunner()

    assert runner._load_repo_context() == {}


def test_load_repo_context_invalid_shared_falls_back_to_valid_local(tmp_path):
    mod = load_commit_semantic_module()
    extract_dir = tmp_path / "data" / "commit-extract"
    semantic_dir = tmp_path / "data" / "commit-semantic"
    extract_dir.mkdir(parents=True)
    semantic_dir.mkdir(parents=True)

    invalid_shared_payload = {
        "shared_hints": {
            "local_capabilities": ["shared-extract"],
        },
        "summary": {
            "bootstrap_status": "full",
        },
    }
    local_payload = {
        "shared_hints": {
            "local_capabilities": ["local-semantic"],
            "aliases": [],
            "ownership_hints": [],
            "seed_concepts": [],
            "source_provenance": {},
            "hint_confidence": {},
            "conflicts": [],
            "source_snapshot": {"docs": [], "codebase_map": []},
        },
        "semantic_context": {
            "local_capabilities": ["local-semantic"],
            "ownership_hints": [{"capability": "commit-semantic"}],
            "aliases": [],
            "seed_concepts": [],
            "confidence": "medium",
        },
        "summary": {
            "bootstrap_status": "degraded",
            "hint_count": 1,
            "source_counts": {"docs": 0, "codebase_map": 0},
        },
    }
    (extract_dir / "repo-context.json").write_text(json.dumps(invalid_shared_payload), encoding="utf-8")
    (semantic_dir / "repo-context.json").write_text(json.dumps(local_payload), encoding="utf-8")

    mod.EXTRACT_OUTPUT = extract_dir
    mod.SEMANTIC_OUTPUT = semantic_dir
    runner = mod.CommitSemanticRunner()

    resolved = runner._load_repo_context()

    assert resolved == local_payload["semantic_context"]
    assert resolved["local_capabilities"] == ["local-semantic"]


def test_load_repo_context_invalid_shared_without_local_returns_empty(tmp_path):
    mod = load_commit_semantic_module()
    extract_dir = tmp_path / "data" / "commit-extract"
    semantic_dir = tmp_path / "data" / "commit-semantic"
    extract_dir.mkdir(parents=True)
    semantic_dir.mkdir(parents=True)

    invalid_shared_payload = {
        "shared_hints": {
            "local_capabilities": ["shared-extract"],
        },
        "summary": {
            "bootstrap_status": "full",
        },
    }
    (extract_dir / "repo-context.json").write_text(json.dumps(invalid_shared_payload), encoding="utf-8")

    mod.EXTRACT_OUTPUT = extract_dir
    mod.SEMANTIC_OUTPUT = semantic_dir
    runner = mod.CommitSemanticRunner()

    assert runner._load_repo_context() == {}


def test_load_repo_context_consumes_semantic_context_only(tmp_path):
    mod = load_commit_semantic_module()
    extract_dir = tmp_path / "data" / "commit-extract"
    semantic_dir = tmp_path / "data" / "commit-semantic"
    extract_dir.mkdir(parents=True)
    semantic_dir.mkdir(parents=True)

    payload = load_fixture()
    (extract_dir / "repo-context.json").write_text(json.dumps(payload), encoding="utf-8")

    mod.EXTRACT_OUTPUT = extract_dir
    mod.SEMANTIC_OUTPUT = semantic_dir
    runner = mod.CommitSemanticRunner()

    resolved = runner._load_repo_context()

    assert resolved == payload["semantic_context"]
    assert "shared_hints" not in resolved
    assert "summary" not in resolved
