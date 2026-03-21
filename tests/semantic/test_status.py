"""Tests for src/semantic/status.py"""
from pathlib import Path

import yaml

from src.semantic.status import get_status


def write_state(tmp_path: Path, data: dict) -> None:
    (tmp_path / "run-state.yaml").write_text(yaml.dump(data), encoding="utf-8")


def test_no_state_file(tmp_path):
    report = get_status(tmp_path)
    assert report.current_stage is None
    assert report.next_action == "run semantic-signals"
    assert report.blocked is False
    assert report.blocked_reason is None
    assert report.completed == []


def test_after_step1_completed(tmp_path):
    write_state(tmp_path, {"completed_stages": ["step1_signals"]})
    report = get_status(tmp_path)
    assert report.next_action == "run semantic-candidates"
    assert report.blocked is False


def test_after_all_stages_completed(tmp_path):
    write_state(tmp_path, {
        "completed_stages": [
            "step1_signals",
            "step2_candidates",
            "step3_recommend",
            "step4_review",
            "step5_finalize",
        ]
    })
    report = get_status(tmp_path)
    assert report.next_action == "pipeline complete"
    assert report.blocked is False


def test_blocked_state_next_action(tmp_path):
    write_state(tmp_path, {
        "completed_stages": ["step1_signals"],
        "blocked_reason": "missing input file",
    })
    report = get_status(tmp_path)
    assert "resolve:" in report.next_action
    assert "missing input file" in report.next_action


def test_blocked_true_when_blocked_reason_set(tmp_path):
    write_state(tmp_path, {"blocked_reason": "some error"})
    report = get_status(tmp_path)
    assert report.blocked is True
    assert report.blocked_reason == "some error"


def test_empty_state_file(tmp_path):
    (tmp_path / "run-state.yaml").write_text("", encoding="utf-8")
    report = get_status(tmp_path)
    assert report.next_action == "run semantic-signals"
    assert report.blocked is False
