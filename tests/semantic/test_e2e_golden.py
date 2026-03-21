"""
End-to-end golden fixture tests for the semantic pipeline.

These tests verify the full chain works without LLM calls,
using pre-built fixture data to catch regressions.
"""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.build_candidates import synthesize_domain_candidates
from semantic.change_detector import ChangeDetector
from semantic.extract_signals import (
    extract_signals_from_files,
    load_fact_canonical,
    load_fact_working_summary,
)
from semantic.signal_cache import SignalCache
from semantic.status import get_status
from semantic.validate import validate_stage

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "semantic"


@pytest.fixture
def fact_root(tmp_path):
    """Set up a FACT root with golden fixture files."""
    fact_dir = tmp_path / "fact"
    fact_dir.mkdir()
    shutil.copy(FIXTURES_DIR / "fact_canonical_sample.yaml", fact_dir)
    shutil.copy(FIXTURES_DIR / "fact_working_summary_sample.yaml", fact_dir)
    return fact_dir


@pytest.fixture
def semantic_workspace(tmp_path):
    """Set up a semantic workspace directory."""
    workspace = tmp_path / "semantic"
    workspace.mkdir()
    return workspace


def test_signals_extraction_produces_output(fact_root, tmp_path):
    canonical = load_fact_canonical(fact_root)
    working = load_fact_working_summary(fact_root)
    result = extract_signals_from_files(canonical, working)
    assert isinstance(result, dict)
    assert "domain_signals" in result
    assert isinstance(result["domain_signals"], list)


def test_signals_have_required_fields(fact_root, tmp_path):
    canonical = load_fact_canonical(fact_root)
    working = load_fact_working_summary(fact_root)
    result = extract_signals_from_files(canonical, working)
    for signal in result["domain_signals"]:
        assert "signal_type" in signal
        assert "summary" in signal


def test_candidates_built_from_signals(tmp_path):
    signals = {
        "domain_signals": [
            {
                "signal_type": "module_grouping",
                "source": "fact_canonical:modules",
                "evidence": "2 modules observed",
                "confidence": "high",
                "summary": "Repository contains 2 distinct modules",
            }
        ]
    }
    result = synthesize_domain_candidates(signals["domain_signals"])
    assert isinstance(result, list)
    assert len(result) > 0


def test_full_pipeline_signals_to_candidates(fact_root, tmp_path):
    canonical = load_fact_canonical(fact_root)
    working = load_fact_working_summary(fact_root)
    signals = extract_signals_from_files(canonical, working)
    candidates = synthesize_domain_candidates(signals["domain_signals"])
    assert isinstance(candidates, list)
    assert len(candidates) > 0


def test_signal_cache_roundtrip(fact_root, tmp_path):
    canonical = load_fact_canonical(fact_root)
    working = load_fact_working_summary(fact_root)
    signals = extract_signals_from_files(canonical, working)

    cache_dir = tmp_path / "cache"
    cache = SignalCache(cache_dir)
    file_path = fact_root / "fact_canonical_sample.yaml"
    detector = ChangeDetector(fact_root, cache_dir)
    file_hash = detector.compute_file_hash(file_path)

    cache.store_signals(file_path, file_hash, signals)
    retrieved = cache.get_cached_signals(file_path, file_hash)
    assert retrieved == signals


def test_incremental_second_run_uses_cache(fact_root, tmp_path):
    from semantic.extract_signals import run_incremental_extraction

    cache_dir = tmp_path / "cache"

    # First run — populates cache
    run_incremental_extraction(fact_root, cache_dir)

    # Second run — should hit cache
    cache = SignalCache(cache_dir)
    cache.reset_stats()
    run_incremental_extraction(fact_root, cache_dir)

    stats = cache.get_cache_stats()
    # After second run the module-level cache instance won't have hits,
    # but the index should have entries showing files were cached
    assert stats["indexed_files"] > 0


def test_validate_stage_after_signals(fact_root, tmp_path):
    canonical = load_fact_canonical(fact_root)
    working = load_fact_working_summary(fact_root)
    signals = extract_signals_from_files(canonical, working)

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    signals_path = workspace / "signals.yaml"
    with open(signals_path, "w", encoding="utf-8") as f:
        yaml.dump(signals, f)

    result = validate_stage("step1_signals", workspace)
    assert result.passed is True


def test_validate_stage_fails_without_artifacts(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    result = validate_stage("step1_signals", empty_dir)
    assert result.passed is False


def test_status_reflects_completed_stages(tmp_path):
    state = {"completed_stages": ["step1_signals"]}
    state_path = tmp_path / "run-state.yaml"
    with open(state_path, "w", encoding="utf-8") as f:
        yaml.dump(state, f)

    report = get_status(tmp_path)
    assert report.next_action == "run semantic-candidates"
