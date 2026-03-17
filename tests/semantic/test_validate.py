"""Tests for src/semantic/validate.py"""
import pytest
import yaml
from pathlib import Path
from src.semantic.validate import validate_stage, ValidationResult


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


# ── step1_signals ──────────────────────────────────────────────────────────────

def test_step1_passes(workspace):
    (workspace / "signals.yaml").write_text(yaml.dump({"domain_signals": []}))
    r = validate_stage("step1_signals", workspace)
    assert r.passed
    assert r.errors == []


def test_step1_missing_file(workspace):
    r = validate_stage("step1_signals", workspace)
    assert not r.passed
    assert any("not found" in e for e in r.errors)


def test_step1_missing_key(workspace):
    (workspace / "signals.yaml").write_text(yaml.dump({"other": 1}))
    r = validate_stage("step1_signals", workspace)
    assert not r.passed
    assert any("domain_signals" in e for e in r.errors)


def test_step1_invalid_yaml(workspace):
    (workspace / "signals.yaml").write_text(": bad: yaml: [")
    r = validate_stage("step1_signals", workspace)
    assert not r.passed
    assert any("not valid YAML" in e for e in r.errors)


# ── step2_candidates ───────────────────────────────────────────────────────────

def test_step2_passes(workspace):
    (workspace / "candidates.yaml").write_text(yaml.dump({"candidates": []}))
    r = validate_stage("step2_candidates", workspace)
    assert r.passed


def test_step2_missing_file(workspace):
    r = validate_stage("step2_candidates", workspace)
    assert not r.passed
    assert any("not found" in e for e in r.errors)


def test_step2_missing_key(workspace):
    (workspace / "candidates.yaml").write_text(yaml.dump({"other": 1}))
    r = validate_stage("step2_candidates", workspace)
    assert not r.passed
    assert any("candidates" in e for e in r.errors)


def test_step2_invalid_yaml(workspace):
    (workspace / "candidates.yaml").write_text(": bad: [")
    r = validate_stage("step2_candidates", workspace)
    assert not r.passed
    assert any("not valid YAML" in e for e in r.errors)


# ── step3_recommend ────────────────────────────────────────────────────────────

def test_step3_passes(workspace):
    (workspace / "recommendations.yaml").write_text(yaml.dump({"recommendations": []}))
    r = validate_stage("step3_recommend", workspace)
    assert r.passed


def test_step3_missing_file(workspace):
    r = validate_stage("step3_recommend", workspace)
    assert not r.passed
    assert any("not found" in e for e in r.errors)


def test_step3_missing_key(workspace):
    (workspace / "recommendations.yaml").write_text(yaml.dump({"other": 1}))
    r = validate_stage("step3_recommend", workspace)
    assert not r.passed
    assert any("recommendations" in e for e in r.errors)


def test_step3_invalid_yaml(workspace):
    (workspace / "recommendations.yaml").write_text(": bad: [")
    r = validate_stage("step3_recommend", workspace)
    assert not r.passed
    assert any("not valid YAML" in e for e in r.errors)


# ── step4_review ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("key", ["domains", "concepts", "rules", "demand_models"])
def test_step4_passes_with_any_required_key(workspace, key):
    (workspace / "review-decisions.yaml").write_text(yaml.dump({key: []}))
    r = validate_stage("step4_review", workspace)
    assert r.passed


def test_step4_missing_file(workspace):
    r = validate_stage("step4_review", workspace)
    assert not r.passed
    assert any("not found" in e for e in r.errors)


def test_step4_missing_all_required_keys(workspace):
    (workspace / "review-decisions.yaml").write_text(yaml.dump({"other": 1}))
    r = validate_stage("step4_review", workspace)
    assert not r.passed


def test_step4_invalid_yaml(workspace):
    (workspace / "review-decisions.yaml").write_text(": bad: [")
    r = validate_stage("step4_review", workspace)
    assert not r.passed
    assert any("not valid YAML" in e for e in r.errors)


# ── step5_finalize ─────────────────────────────────────────────────────────────

def test_step5_passes_with_report(workspace):
    (workspace / "finalize-report.yaml").write_text(yaml.dump({"done": True}))
    r = validate_stage("step5_finalize", workspace)
    assert r.passed


def test_step5_passes_with_assets_dir(workspace):
    (workspace / "finalize-assets").mkdir()
    r = validate_stage("step5_finalize", workspace)
    assert r.passed


def test_step5_missing_both(workspace):
    r = validate_stage("step5_finalize", workspace)
    assert not r.passed
    assert any("not found" in e for e in r.errors)


# ── unknown stage ──────────────────────────────────────────────────────────────

def test_unknown_stage_passes_by_default(workspace):
    r = validate_stage("step99_unknown", workspace)
    assert r.passed
    assert r.errors == []
