import json
from pathlib import Path

import pytest


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "commit_extract_bootstrap"


@pytest.fixture
def bootstrap_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "commit_extract_bootstrap_reliability",
        str(Path(__file__).parent.parent / "skills" / "commit-extract" / "bootstrap.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_fingerprint_changes_when_sources_change(tmp_path, bootstrap_module):
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")

    first = bootstrap_module.compute_bootstrap_fingerprint(tmp_path)

    (tmp_path / "README.md").write_text("# Repo changed\n", encoding="utf-8")
    second = bootstrap_module.compute_bootstrap_fingerprint(tmp_path)

    assert first != second


def test_build_reliability_summary_full_mode(bootstrap_module):
    fixture = load_fixture("example_bootstrap_context.json")

    summary = bootstrap_module.build_reliability_summary(
        fixture["shared_hints"],
        fingerprint="abc123",
        bootstrap_status="full",
        used_cached_context=False,
    )

    assert summary["bootstrap_status"] == "full"
    assert summary["used_cached_context"] is False
    assert summary["degraded_reasons"] == []
    assert summary["bypass_reason"] is None
    assert summary["fingerprint"] == "abc123"


def test_build_reliability_summary_degraded_mode(bootstrap_module):
    fixture = load_fixture("degraded_repo_context.json")

    summary = bootstrap_module.build_reliability_summary(
        fixture["shared_hints"],
        fingerprint="degraded-fingerprint",
        bootstrap_status="degraded",
        used_cached_context=True,
        degraded_reasons=["reduced-shared-hints"],
    )

    assert summary == fixture["summary"]


def test_determine_bootstrap_mode_returns_full_for_fresh_valid_context(tmp_path, bootstrap_module):
    fixture = load_fixture("example_bootstrap_context.json")
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("Instructions\n", encoding="utf-8")
    planning = tmp_path / ".planning" / "codebase"
    planning.mkdir(parents=True)
    (planning / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")

    fingerprint = bootstrap_module.compute_bootstrap_fingerprint(tmp_path)
    summary = bootstrap_module.build_reliability_summary(
        fixture["shared_hints"],
        fingerprint=fingerprint,
        bootstrap_status="full",
        used_cached_context=False,
    )
    fixture["summary"] = summary

    mode = bootstrap_module.determine_bootstrap_mode(
        fixture,
        current_fingerprint=fingerprint,
    )

    assert mode["bootstrap_status"] == "full"
    assert mode["used_cached_context"] is True
    assert mode["degraded_reasons"] == []
    assert mode["bypass_reason"] is None


def test_determine_bootstrap_mode_returns_degraded_for_weak_context(bootstrap_module):
    fixture = load_fixture("degraded_repo_context.json")

    mode = bootstrap_module.determine_bootstrap_mode(
        fixture,
        current_fingerprint=fixture["summary"]["fingerprint"],
    )

    assert mode["bootstrap_status"] == "degraded"
    assert mode["used_cached_context"] is True
    assert mode["degraded_reasons"] == ["reduced-shared-hints"]
    assert mode["bypass_reason"] is None


def test_determine_bootstrap_mode_returns_bypass_for_invalid_or_missing_context(bootstrap_module):
    invalid_context = {"shared_hints": {}, "summary": {"fingerprint": "abc"}}

    invalid = bootstrap_module.determine_bootstrap_mode(invalid_context, current_fingerprint="abc")
    missing = bootstrap_module.determine_bootstrap_mode(None, current_fingerprint="abc")

    assert invalid["bootstrap_status"] == "bypass"
    assert invalid["bypass_reason"] == "invalid-context"
    assert missing["bootstrap_status"] == "bypass"
    assert missing["bypass_reason"] == "missing-context"


def test_determine_bootstrap_mode_returns_bypass_for_stale_context(bootstrap_module):
    fixture = load_fixture("stale_repo_context.json")

    mode = bootstrap_module.determine_bootstrap_mode(
        fixture,
        current_fingerprint="current-fingerprint",
    )

    assert mode["bootstrap_status"] == "bypass"
    assert mode["used_cached_context"] is False
    assert mode["degraded_reasons"] == []
    assert mode["bypass_reason"] == "stale-context"


def test_determine_bootstrap_mode_honors_explicit_bypass(bootstrap_module):
    fixture = load_fixture("example_bootstrap_context.json")

    mode = bootstrap_module.determine_bootstrap_mode(
        fixture,
        current_fingerprint="anything",
        skip_bootstrap=True,
    )

    assert mode["bootstrap_status"] == "bypass"
    assert mode["bypass_reason"] == "skip-bootstrap"
    assert mode["used_cached_context"] is False




def test_determine_bootstrap_mode_preserves_persisted_bypass_status(bootstrap_module):
    fixture = load_fixture("example_bootstrap_context.json")
    fixture["summary"]["bootstrap_status"] = "bypass"
    fixture["summary"]["bypass_reason"] = "skip-bootstrap"
    fixture["shared_hints"]["local_capabilities"] = []

    mode = bootstrap_module.determine_bootstrap_mode(
        fixture,
        current_fingerprint=fixture["summary"]["fingerprint"],
    )

    assert mode["bootstrap_status"] == "bypass"
    assert mode["bypass_reason"] == "skip-bootstrap"
    assert mode["used_cached_context"] is False


def test_build_reliability_summary_rejects_unknown_bootstrap_status(bootstrap_module):
    fixture = load_fixture("example_bootstrap_context.json")

    with pytest.raises(ValueError, match="Invalid bootstrap_status"):
        bootstrap_module.build_reliability_summary(
            fixture["shared_hints"],
            fingerprint="abc123",
            bootstrap_status="cached",
            used_cached_context=False,
        )
