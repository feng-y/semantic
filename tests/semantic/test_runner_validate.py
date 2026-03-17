"""Tests for validate_stage integration in run.py all-mode pipeline."""

from pathlib import Path
import sys
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from src.semantic.run import main
from src.semantic.validate import ValidationResult


def _make_args(workspace: str, mode: str = "all", skip_validation: bool = False):
    args = ["run", mode, "--semantic-root", "/fake", "--workspace", workspace]
    if skip_validation:
        args.append("--skip-validation")
    return args


def _passed_result(stage: str, ws=None) -> ValidationResult:
    return ValidationResult(stage=stage, passed=True, errors=[])


def _failed_result(stage: str, ws=None) -> ValidationResult:
    return ValidationResult(stage=stage, passed=False, errors=["artifact missing"])


def test_all_mode_validates_each_stage():
    with tempfile.TemporaryDirectory() as tmp:
        with patch("src.semantic.run.validate_stage", side_effect=_passed_result) as mock_val:
            with patch.object(sys, "argv", _make_args(tmp)):
                main()

        called_stages = [call.args[0] for call in mock_val.call_args_list]
        assert called_stages == [
            "step1_signals",
            "step2_candidates",
            "step3_recommend",
            "step4_review",
            "step5_finalize",
        ]


def test_all_mode_blocks_on_validation_failure():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)

        def side_effect(stage, ws):
            if stage == "step2_candidates":
                return _failed_result(stage, ws)
            return _passed_result(stage, ws)

        with patch("src.semantic.run.validate_stage", side_effect=side_effect):
            with patch.object(sys, "argv", _make_args(tmp)):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        assert exc_info.value.code == "VALIDATION_FAILED"

        import yaml
        state = yaml.safe_load((workspace / "run-state.yaml").read_text())
        assert "step2_candidates" in state.get("blocked_reason", "")


def test_skip_validation_bypasses_checks():
    with tempfile.TemporaryDirectory() as tmp:
        with patch("src.semantic.run.validate_stage", side_effect=_failed_result) as mock_val:
            with patch.object(sys, "argv", _make_args(tmp, skip_validation=True)):
                main()  # should not raise

        mock_val.assert_not_called()
