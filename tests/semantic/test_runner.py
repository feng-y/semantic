"""Tests for refactored semantic runner (run.py)."""

from pathlib import Path
import sys
import tempfile
from unittest.mock import patch, MagicMock
import yaml
import pytest

from src.semantic.run import main, load_state, save_state, next_stage, check_finalize_guard
from src.semantic.runner_models import RunState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_state(workspace: Path, completed: list[str], mode: str = "next") -> Path:
    state_path = workspace / "run-state.yaml"
    state = RunState(
        mode=mode,
        current_stage=completed[-1] if completed else None,
        completed_stages=completed,
    )
    state_path.write_text(
        yaml.safe_dump(state.model_dump(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return state_path


def _write_review_decisions(workspace: Path, has_verify_first: bool = True):
    action = "verify_first" if has_verify_first else "accept"
    decisions = {
        "domains": [{"id": "d1", "name": "D1", "final_action": action, "final_reason": "r", "source_recommendation_id": "r1", "evidence_refs": []}],
        "concepts": [],
        "rules": [],
        "demand_models": [],
    }
    (workspace / "review-decisions.yaml").write_text(yaml.dump(decisions))


def _write_evidence_checks(workspace: Path, status: str = "completed"):
    checks = {
        "evidence_checks": [{"id": "c1", "target_id": "d1", "target_type": "domain", "target_name": "D1", "reason": "r", "required_evidence": [], "status": status}]
    }
    (workspace / "evidence-checks.yaml").write_text(yaml.dump(checks))


def _run_main(mode: str, workspace: Path):
    sys.argv = ["run.py", mode, "--semantic-root", str(workspace), "--workspace", str(workspace)]
    main()


# ---------------------------------------------------------------------------
# next mode
# ---------------------------------------------------------------------------

def test_next_mode_advances_one_stage(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _run_main("next", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "PASS: step1_signals"

        state = load_state(workspace / "run-state.yaml", "next")
        assert state.completed_stages == ["step1_signals"]
        assert state.current_stage == "step1_signals"


def test_next_mode_advances_second_stage(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_state(workspace, ["step1_signals"])
        _run_main("next", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "PASS: step2_candidates"


def test_next_mode_prints_done_when_all_complete(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        all_stages = ["step1_signals", "step2_candidates", "step3_recommend", "step4_review", "step5_finalize"]
        _write_state(workspace, all_stages)
        _run_main("next", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "DONE"


# ---------------------------------------------------------------------------
# all mode
# ---------------------------------------------------------------------------

def test_all_mode_completes_all_stages(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        with patch("src.semantic.run.validate_stage", return_value=MagicMock(passed=True)):
            _run_main("all", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "DONE"

        state = load_state(workspace / "run-state.yaml", "all")
        assert len(state.completed_stages) == 5
        assert state.current_stage == "step5_finalize"


def test_all_mode_resumes_from_partial(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_state(workspace, ["step1_signals", "step2_candidates"], mode="all")
        with patch("src.semantic.run.validate_stage", return_value=MagicMock(passed=True)):
            _run_main("all", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "DONE"

        state = load_state(workspace / "run-state.yaml", "all")
        assert len(state.completed_stages) == 5


# ---------------------------------------------------------------------------
# resume mode
# ---------------------------------------------------------------------------

def test_resume_mode_continues_from_last_incomplete(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_state(workspace, ["step1_signals", "step2_candidates"], mode="resume")
        _run_main("resume", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "PASS: step3_recommend"

        state = load_state(workspace / "run-state.yaml", "resume")
        assert "step3_recommend" in state.completed_stages


def test_resume_mode_prints_done_when_all_complete(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        all_stages = ["step1_signals", "step2_candidates", "step3_recommend", "step4_review", "step5_finalize"]
        _write_state(workspace, all_stages, mode="resume")
        _run_main("resume", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "DONE"


def test_resume_mode_starts_fresh_when_no_state(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _run_main("resume", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "PASS: step1_signals"


# ---------------------------------------------------------------------------
# reset mode
# ---------------------------------------------------------------------------

def test_reset_mode_clears_state(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_state(workspace, ["step1_signals", "step2_candidates"])
        state_path = workspace / "run-state.yaml"
        assert state_path.exists()

        _run_main("reset", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "RESET"
        assert not state_path.exists()


def test_reset_mode_no_state_file(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _run_main("reset", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "RESET"


# ---------------------------------------------------------------------------
# finalize guard
# ---------------------------------------------------------------------------

def test_finalize_guard_blocks_when_verify_first_no_evidence():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_review_decisions(workspace, has_verify_first=True)
        is_blocked, reason = check_finalize_guard(workspace)
        assert is_blocked is True
        assert "evidence-checks.yaml is missing" in reason


def test_finalize_guard_blocks_when_evidence_pending():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_review_decisions(workspace, has_verify_first=True)
        _write_evidence_checks(workspace, status="pending")
        is_blocked, reason = check_finalize_guard(workspace)
        assert is_blocked is True
        assert "unresolved evidence checks" in reason


def test_finalize_guard_passes_when_evidence_resolved():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_review_decisions(workspace, has_verify_first=True)
        _write_evidence_checks(workspace, status="completed")
        is_blocked, reason = check_finalize_guard(workspace)
        assert is_blocked is False
        assert reason == ""


def test_finalize_guard_passes_when_no_review_decisions():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        is_blocked, reason = check_finalize_guard(workspace)
        assert is_blocked is False


def test_finalize_guard_passes_when_no_verify_first():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_review_decisions(workspace, has_verify_first=False)
        is_blocked, reason = check_finalize_guard(workspace)
        assert is_blocked is False


def test_next_mode_finalize_blocked_by_guard():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_state(workspace, ["step1_signals", "step2_candidates", "step3_recommend", "step4_review"])
        _write_review_decisions(workspace, has_verify_first=True)

        sys.argv = ["run.py", "next", "--semantic-root", str(workspace), "--workspace", str(workspace)]
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert str(exc_info.value) == "BLOCKED"

        state = load_state(workspace / "run-state.yaml", "next")
        assert state.blocked_reason == "verify_first exists but evidence-checks.yaml is missing"


def test_next_mode_finalize_passes_when_evidence_resolved(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        _write_state(workspace, ["step1_signals", "step2_candidates", "step3_recommend", "step4_review"])
        _write_review_decisions(workspace, has_verify_first=True)
        _write_evidence_checks(workspace, status="completed")

        _run_main("next", workspace)
        out = capsys.readouterr().out.strip()
        assert out == "PASS: step5_finalize"
