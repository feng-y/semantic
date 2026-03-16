"""Tests for discovery pipeline error propagation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.discovery_executor import DiscoveryResult, StepResult, run_discovery


@pytest.fixture
def mock_root(tmp_path):
    """Create a mock repository root."""
    root = tmp_path / "test-repo"
    root.mkdir()

    # Create minimal structure
    (root / ".semantic-harness").mkdir()
    (root / ".semantic-harness" / "artifacts").mkdir()
    (root / ".semantic-harness" / "skills").mkdir()

    # Create manifest.yaml with correct key name
    manifest = root / "manifest.yaml"
    manifest.write_text("""
skills:
  discover: .semantic-harness/skills/repo-semantic-discovery.skill
""")

    # Create a minimal skill file
    skill_file = root / ".semantic-harness" / "skills" / "repo-semantic-discovery.skill"
    skill_file.write_text("""
name: repo-semantic-discovery
steps:
  - run: prompts/discover/repo-sampling.prompt
""")

    return root


def test_step_error_stops_pipeline(mock_root):
    """Test that a step returning error status stops the pipeline."""
    mock_executor = MagicMock()

    with patch("src.discovery_executor._execute_prompt_step") as mock_exec:
        # First step returns error
        mock_exec.return_value = StepResult(
            step_index=0,
            action="prompt",
            target="prompts/discover/repo-sampling.prompt",
            status="error",
            errors=["Execution failed"],
        )

        with patch("src.discovery_executor.artifact_writer.write_semantic_snapshot") as mock_snapshot:
            with patch("src.discovery_executor.artifact_writer.check_semantic_snapshot", return_value=[]):
                result = run_discovery(mock_root, executor=mock_executor, sampling_mode="auto")

                # Pipeline should stop with error status
                assert result.status == "error"
                # Snapshot should NOT be written
                mock_snapshot.assert_not_called()
                # Should have one step result
                assert len(result.steps) == 1
                assert result.steps[0].status == "error"


def test_validation_failed_stops_pipeline(mock_root):
    """Test that validation failure stops the pipeline."""
    mock_executor = MagicMock()

    with patch("src.discovery_executor._execute_prompt_step") as mock_exec:
        # First step returns validation_failed
        mock_exec.return_value = StepResult(
            step_index=0,
            action="prompt",
            target="prompts/discover/repo-sampling.prompt",
            status="validation_failed",
            errors=["Validation error"],
        )

        with patch("src.discovery_executor.artifact_writer.write_semantic_snapshot") as mock_snapshot:
            with patch("src.discovery_executor.artifact_writer.check_semantic_snapshot", return_value=[]):
                result = run_discovery(mock_root, executor=mock_executor, sampling_mode="auto")

                # Pipeline should stop with validation_failed status
                assert result.status == "validation_failed"
                # Snapshot should NOT be written
                mock_snapshot.assert_not_called()
                # Should have validation failures recorded
                assert len(result.validation_failures) == 1


def test_successful_pipeline_writes_snapshot(mock_root):
    """Test that a successful pipeline writes the semantic snapshot."""
    mock_executor = MagicMock()

    with patch("src.discovery_executor._execute_prompt_step") as mock_exec:
        # All steps succeed
        mock_exec.return_value = StepResult(
            step_index=0,
            action="prompt",
            target="prompts/discover/repo-sampling.prompt",
            status="ok",
            artifact_path=".semantic-harness/artifacts/sampling-report.md",
        )

        with patch("src.discovery_executor.artifact_writer.write_semantic_snapshot") as mock_snapshot:
            with patch("src.discovery_executor.artifact_writer.check_semantic_snapshot", return_value=[]):
                result = run_discovery(mock_root, executor=mock_executor, sampling_mode="auto")

                # Pipeline should complete successfully
                assert result.status == "ok"
                # Snapshot SHOULD be written
                mock_snapshot.assert_called_once_with(mock_root)


def test_execution_unavailable(mock_root):
    """Test that missing executor results in execution_unavailable status."""
    with patch("src.discovery_executor.artifact_writer.write_semantic_snapshot") as mock_snapshot:
        with patch("src.discovery_executor.artifact_writer.check_semantic_snapshot", return_value=[]):
            result = run_discovery(mock_root, executor=None, sampling_mode="auto")

            # Should return execution_unavailable status
            assert result.status == "execution_unavailable"
            # Snapshot should NOT be written
            mock_snapshot.assert_not_called()
