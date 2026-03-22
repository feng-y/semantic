"""Tests for harness_state module."""

import json
import os
from pathlib import Path

import pytest

from harness_state import (
    HarnessState,
    get_harness_root,
    get_next_stage,
    get_output_path,
    get_state_path,
    is_valid_transition,
    load_state,
    save_state,
    transition_state,
)


class TestHarnessState:
    """Tests for HarnessState dataclass."""

    def test_default_initialization(self):
        """Test HarnessState initializes with defaults."""
        state = HarnessState()
        assert state.version == "1.0"
        assert state.stage == "init"
        assert state.repo_path == ""
        assert state.metadata == {}
        assert state.last_updated is not None

    def test_custom_initialization(self):
        """Test HarnessState with custom values."""
        state = HarnessState(
            version="2.0",
            stage="extract",
            repo_path="/some/path",
            metadata={"key": "value"},
        )
        assert state.version == "2.0"
        assert state.stage == "extract"
        assert state.repo_path == "/some/path"
        assert state.metadata == {"key": "value"}

    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = HarnessState(stage="semantic", repo_path="/test")
        data = state.to_dict()
        assert data["version"] == "1.0"
        assert data["stage"] == "semantic"
        assert data["repo_path"] == "/test"
        assert "last_updated" in data

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "version": "2.0",
            "stage": "complete",
            "repo_path": "/repo",
            "last_updated": "2024-01-01T00:00:00",
            "metadata": {"count": 5},
        }
        state = HarnessState.from_dict(data)
        assert state.version == "2.0"
        assert state.stage == "complete"
        assert state.repo_path == "/repo"
        assert state.metadata == {"count": 5}

    def test_from_dict_with_defaults(self):
        """Test from_dict provides defaults for missing fields."""
        state = HarnessState.from_dict({})
        assert state.version == "1.0"
        assert state.stage == "init"
        assert state.metadata == {}


class TestPathFunctions:
    """Tests for path helper functions."""

    def test_get_harness_root(self):
        """Test harness root path."""
        root = get_harness_root()
        assert root == Path(".harness")

    def test_get_state_path_commit_extract(self):
        """Test state path for commit-extract."""
        path = get_state_path("commit-extract")
        assert path == Path(".harness/state/commit-extract/state.json")

    def test_get_state_path_commit_semantic(self):
        """Test state path for commit-semantic."""
        path = get_state_path("commit-semantic")
        assert path == Path(".harness/state/commit-semantic/state.json")

    def test_get_output_path_commits(self):
        """Test output path for commits."""
        path = get_output_path("commit-extract", "commits")
        assert path == Path(".harness/outputs/commit-extract/commits")

    def test_get_output_path_patterns(self):
        """Test output path for patterns."""
        path = get_output_path("commit-semantic", "patterns")
        assert path == Path(".harness/outputs/commit-semantic/patterns")


class TestLoadSaveState:
    """Tests for load_state and save_state functions."""

    def setup_method(self):
        """Setup test environment."""
        self.test_pipeline = "test-pipeline"
        # Clean up any existing test state
        state_path = get_state_path(self.test_pipeline)
        if state_path.exists():
            state_path.unlink()

    def teardown_method(self):
        """Cleanup test environment."""
        state_path = get_state_path(self.test_pipeline)
        if state_path.exists():
            state_path.unlink()

    def test_load_state_returns_fresh_when_missing(self):
        """Test load_state returns fresh state when file doesn't exist."""
        state = load_state(self.test_pipeline)
        assert isinstance(state, HarnessState)
        assert state.stage == "init"

    def test_save_and_load_state(self):
        """Test saving and loading state."""
        state = HarnessState(stage="extract", repo_path="/test/repo")
        save_state(self.test_pipeline, state)

        loaded = load_state(self.test_pipeline)
        assert loaded.stage == "extract"
        assert loaded.repo_path == "/test/repo"

    def test_save_updates_timestamp(self):
        """Test save_state updates last_updated timestamp."""
        old_time = "2020-01-01T00:00:00"
        state = HarnessState(last_updated=old_time)
        save_state(self.test_pipeline, state)

        loaded = load_state(self.test_pipeline)
        assert loaded.last_updated != old_time

    def test_save_creates_directories(self, tmp_path):
        """Test save_state creates parent directories."""
        # Use a temporary directory to test directory creation
        os.chdir(tmp_path)
        state = HarnessState()
        save_state("new-pipeline", state)

        assert (tmp_path / ".harness/state/new-pipeline/state.json").exists()

    def test_load_state_handles_corrupt_json(self, tmp_path):
        """Test load_state handles corrupt JSON gracefully."""
        os.chdir(tmp_path)
        # Create corrupt state file
        state_path = Path(".harness/state/bad-pipeline/state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("not valid json{}")

        state = load_state("bad-pipeline")
        assert isinstance(state, HarnessState)
        assert state.stage == "init"

    def test_atomic_write(self, tmp_path):
        """Test save_state uses atomic write."""
        os.chdir(tmp_path)
        state = HarnessState(stage="semantic")
        save_state("atomic-test", state)

        # Should not leave temp files
        temp_file = Path(".harness/state/atomic-test/state.tmp")
        assert not temp_file.exists()


class TestStageTransitions:
    """Tests for stage transition functions."""

    def test_get_next_stage_init(self):
        """Test next stage from init."""
        assert get_next_stage("init") == "extract"

    def test_get_next_stage_extract(self):
        """Test next stage from extract."""
        assert get_next_stage("extract") == "semantic"

    def test_get_next_stage_semantic(self):
        """Test next stage from semantic."""
        assert get_next_stage("semantic") == "complete"

    def test_get_next_stage_complete(self):
        """Test next stage from complete (terminal)."""
        assert get_next_stage("complete") is None

    def test_get_next_stage_unknown(self):
        """Test next stage for unknown stage."""
        assert get_next_stage("unknown") is None

    def test_is_valid_transition_init_to_extract(self):
        """Test valid transition init -> extract."""
        assert is_valid_transition("init", "extract") is True

    def test_is_valid_transition_extract_to_semantic(self):
        """Test valid transition extract -> semantic."""
        assert is_valid_transition("extract", "semantic") is True

    def test_is_valid_transition_extract_to_complete(self):
        """Test valid transition extract -> complete."""
        assert is_valid_transition("extract", "complete") is True

    def test_is_valid_transition_invalid(self):
        """Test invalid transition init -> complete."""
        assert is_valid_transition("init", "complete") is False

    def test_is_valid_transition_unknown(self):
        """Test transition from unknown stage."""
        assert is_valid_transition("unknown", "extract") is False


class TestTransitionState:
    """Tests for transition_state function."""

    def setup_method(self):
        """Setup test environment."""
        self.test_pipeline = "transition-test"
        state_path = get_state_path(self.test_pipeline)
        if state_path.exists():
            state_path.unlink()

    def teardown_method(self):
        """Cleanup test environment."""
        state_path = get_state_path(self.test_pipeline)
        if state_path.exists():
            state_path.unlink()

    def test_transition_valid(self):
        """Test valid state transition."""
        # First set initial state
        state = HarnessState(stage="init")
        save_state(self.test_pipeline, state)

        new_state = transition_state(self.test_pipeline, "extract")
        assert new_state.stage == "extract"

        # Verify persisted
        loaded = load_state(self.test_pipeline)
        assert loaded.stage == "extract"

    def test_transition_invalid_raises(self):
        """Test invalid transition raises ValueError."""
        state = HarnessState(stage="init")
        save_state(self.test_pipeline, state)

        with pytest.raises(ValueError, match="Invalid transition"):
            transition_state(self.test_pipeline, "complete")


class TestIntegration:
    """Integration tests for the full state workflow."""

    def test_full_workflow(self, tmp_path):
        """Test complete state workflow."""
        os.chdir(tmp_path)

        # Initial load returns fresh state
        state = load_state("commit-extract")
        assert state.stage == "init"

        # Save state
        state.repo_path = "/my/repo"
        state.metadata = {"commits_found": 10}
        save_state("commit-extract", state)

        # Load and verify
        loaded = load_state("commit-extract")
        assert loaded.repo_path == "/my/repo"
        assert loaded.metadata["commits_found"] == 10

        # Transition through valid stages
        transition_state("commit-extract", "extract")
        transition_state("commit-extract", "semantic")

        # Verify transition
        final = load_state("commit-extract")
        assert final.stage == "semantic"

        # Check file structure
        state_file = tmp_path / ".harness/state/commit-extract/state.json"
        assert state_file.exists()

        # Verify JSON structure
        data = json.loads(state_file.read_text())
        assert data["version"] == "1.0"
        assert data["stage"] == "semantic"
        assert data["repo_path"] == "/my/repo"
