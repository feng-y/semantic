"""Tests for confidence-based auto-accept logic."""
import pytest
import yaml
from pathlib import Path

from semantic.auto_accept import should_auto_accept, process_recommendations


def test_high_confidence_auto_accepted():
    item = {"id": "x", "name": "X", "confidence": "high"}
    accept, reason = should_auto_accept(item, threshold="high")
    assert accept is True
    assert "high" in reason


def test_medium_confidence_not_accepted_at_high_threshold():
    item = {"id": "x", "name": "X", "confidence": "medium"}
    accept, reason = should_auto_accept(item, threshold="high")
    assert accept is False


def test_medium_confidence_accepted_at_medium_threshold():
    item = {"id": "x", "name": "X", "confidence": "medium"}
    accept, reason = should_auto_accept(item, threshold="medium")
    assert accept is True


def test_low_confidence_never_accepted():
    for threshold in ["high", "medium"]:
        item = {"id": "x", "name": "X", "confidence": "low"}
        accept, _ = should_auto_accept(item, threshold=threshold)
        assert accept is False


def test_process_recommendations_splits_correctly():
    recs = [
        {"id": "a", "name": "A", "confidence": "high"},
        {"id": "b", "name": "B", "confidence": "medium"},
        {"id": "c", "name": "C", "confidence": "low"},
    ]
    report = process_recommendations(recs, threshold="high")
    assert len(report.accepted) == 1
    assert len(report.pending_review) == 2
    assert report.accepted[0].item_id == "a"


def test_acceptance_rate():
    recs = [
        {"id": "a", "name": "A", "confidence": "high"},
        {"id": "b", "name": "B", "confidence": "high"},
        {"id": "c", "name": "C", "confidence": "low"},
    ]
    report = process_recommendations(recs, threshold="high")
    assert report.acceptance_rate == pytest.approx(66.67, abs=0.1)


def test_audit_log_written(tmp_path):
    recs = [{"id": "a", "name": "A", "confidence": "high"}]
    log_path = tmp_path / "audit.yaml"
    process_recommendations(recs, threshold="high", audit_log_path=log_path)
    assert log_path.exists()
    data = yaml.safe_load(log_path.read_text())
    assert "auto_accept_audit" in data
    assert data["auto_accept_audit"][0]["auto_accepted"] is True


def test_empty_recommendations():
    report = process_recommendations([], threshold="high")
    assert report.total == 0
    assert report.acceptance_rate == 0.0
