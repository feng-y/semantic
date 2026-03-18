"""
Tests for state_tracker module.
"""

import json
import tempfile
from pathlib import Path
import pytest

from src.commit_semantic.state_tracker import StateTracker


def test_state_tracker_initialization():
    """Test StateTracker initialization with non-existent file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "test_state.json"
        tracker = StateTracker(state_path)

        assert tracker.state['version'] == '1.0'
        assert tracker.state['processed_commits'] == {}
        assert tracker.state['metadata']['total_commits_processed'] == 0


def test_mark_commit_processed():
    """Test marking commits as processed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "test_state.json"
        tracker = StateTracker(state_path)

        # Mark commit as processed
        tracker.mark_commit_processed('abc123', ['case1', 'case2'], status='completed')

        # Verify state
        assert 'abc123' in tracker.state['processed_commits']
        assert tracker.state['processed_commits']['abc123']['status'] == 'completed'
        assert tracker.state['processed_commits']['abc123']['case_ids'] == ['case1', 'case2']
        assert tracker.state['metadata']['total_commits_processed'] == 1
        assert tracker.state['metadata']['total_cases_generated'] == 2


def test_is_commit_processed():
    """Test checking if commit is processed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "test_state.json"
        tracker = StateTracker(state_path)

        # Initially not processed
        assert not tracker.is_commit_processed('abc123')

        # Mark as processed
        tracker.mark_commit_processed('abc123', ['case1'], status='completed')
        assert tracker.is_commit_processed('abc123')

        # Mark another as failed
        tracker.mark_commit_processed('def456', [], status='failed')
        assert not tracker.is_commit_processed('def456')


def test_get_unprocessed_commits():
    """Test filtering unprocessed commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "test_state.json"
        tracker = StateTracker(state_path)

        # Mark some commits as processed
        tracker.mark_commit_processed('abc123', ['case1'], status='completed')
        tracker.mark_commit_processed('def456', ['case2'], status='completed')

        # Test filtering
        all_commits = ['abc123', 'def456', 'ghi789', 'jkl012']
        unprocessed = tracker.get_unprocessed_commits(all_commits)

        assert len(unprocessed) == 2
        assert 'ghi789' in unprocessed
        assert 'jkl012' in unprocessed
        assert 'abc123' not in unprocessed
        assert 'def456' not in unprocessed


def test_state_persistence():
    """Test that state persists across instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "test_state.json"

        # Create first tracker and add data
        tracker1 = StateTracker(state_path)
        tracker1.mark_commit_processed('abc123', ['case1'], status='completed')

        # Create second tracker and verify data persists
        tracker2 = StateTracker(state_path)
        assert tracker2.is_commit_processed('abc123')
        assert tracker2.state['metadata']['total_commits_processed'] == 1


def test_atomic_write():
    """Test that state writes are atomic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "test_state.json"
        tracker = StateTracker(state_path)

        # Mark commit as processed
        tracker.mark_commit_processed('abc123', ['case1'], status='completed')

        # Verify state file exists and tmp file doesn't
        assert state_path.exists()
        assert not state_path.with_suffix('.json.tmp').exists()

        # Verify content is valid JSON
        with open(state_path, 'r') as f:
            state = json.load(f)
            assert state['version'] == '1.0'
            assert 'abc123' in state['processed_commits']


def test_get_failed_commits():
    """Test getting failed commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "test_state.json"
        tracker = StateTracker(state_path)

        # Mark commits with different statuses
        tracker.mark_commit_processed('abc123', ['case1'], status='completed')
        tracker.mark_commit_processed('def456', [], status='failed')
        tracker.mark_commit_processed('ghi789', [], status='failed')

        # Get failed commits
        failed = tracker.get_failed_commits()
        assert len(failed) == 2
        assert 'def456' in failed
        assert 'ghi789' in failed
        assert 'abc123' not in failed


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
