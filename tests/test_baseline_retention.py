"""Tests for baseline version retention during pruning."""

import json
from pathlib import Path

import pytest

from src import artifact_writer


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def test_accepted_baseline_survives_prune(temp_repo):
    """Test that accepted baseline versions are not pruned."""
    # Create multiple versions of repo-understanding
    for i in range(1, 6):
        artifact_writer.write_artifact(
            temp_repo, "discovery", "repo-understanding",
            f"Version {i} content", versioned=True,
        )

    # Create a checkpoint marking version 2 as accepted
    checkpoint_dir = temp_repo / "docs" / "fact" / "baseline"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "timestamp": "2024-01-01T00:00:00Z",
        "source_versions": {
            "repo-understanding": 2,
            "knowledge-confidence": 1,
        },
        "baseline_files": ["purpose.md", "domains.md"],
        "feedback_hash": "abc123",
    }
    checkpoint_path = checkpoint_dir / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint, indent=2))

    # Prune with keep=3 (should keep versions 3, 4, 5 normally)
    # But version 2 should also be kept because it's accepted
    removed = artifact_writer.prune_old_versions(
        temp_repo, "discovery", "repo-understanding",
        keep=3,
        accepted_versions={2},
    )

    # Only version 1 should be removed
    assert len(removed) == 1
    assert "v1.md" in str(removed[0])

    # Verify versions 2-5 still exist
    discovery_dir = temp_repo / "docs" / "fact" / "discovery"
    for v in [2, 3, 4, 5]:
        assert (discovery_dir / f"repo-understanding.v{v}.md").exists()


def test_multiple_accepted_baselines_preserved(temp_repo):
    """Test that multiple accepted baseline versions are preserved."""
    # Create 10 versions
    for i in range(1, 11):
        artifact_writer.write_artifact(
            temp_repo, "discovery", "knowledge-confidence",
            f"Version {i} content", versioned=True,
        )

    # Mark versions 3 and 7 as accepted
    removed = artifact_writer.prune_old_versions(
        temp_repo, "discovery", "knowledge-confidence",
        keep=3,
        accepted_versions={3, 7},
    )

    # Should remove versions 1-6 except 3, and keep 7-10
    # So removed: 1, 2, 4, 5, 6
    assert len(removed) == 5

    discovery_dir = temp_repo / "docs" / "fact" / "discovery"
    # Verify accepted versions still exist
    assert (discovery_dir / "knowledge-confidence.v3.md").exists()
    assert (discovery_dir / "knowledge-confidence.v7.md").exists()
    # Verify latest versions exist
    for v in [8, 9, 10]:
        assert (discovery_dir / f"knowledge-confidence.v{v}.md").exists()


def test_working_artifacts_pruned_safely(temp_repo):
    """Test that working artifacts are pruned while accepted ones are kept."""
    # Create versions 1-8
    for i in range(1, 9):
        artifact_writer.write_artifact(
            temp_repo, "discovery", "domain-candidates",
            f"Version {i} content", versioned=True,
        )

    # Mark version 2 as accepted (from baseline checkpoint)
    # Keep window is 3, so normally keep 6, 7, 8
    removed = artifact_writer.prune_old_versions(
        temp_repo, "discovery", "domain-candidates",
        keep=3,
        accepted_versions={2},
    )

    # Should remove 1, 3, 4, 5 (not 2 because it's accepted)
    assert len(removed) == 4

    discovery_dir = temp_repo / "docs" / "fact" / "discovery"
    # Version 2 (accepted) should exist
    assert (discovery_dir / "domain-candidates.v2.md").exists()
    # Latest 3 versions should exist
    for v in [6, 7, 8]:
        assert (discovery_dir / f"domain-candidates.v{v}.md").exists()


def test_get_accepted_versions_reads_checkpoint(temp_repo):
    """Test that get_accepted_versions correctly reads checkpoint.json."""
    # Create checkpoint with multiple accepted versions
    checkpoint_dir = temp_repo / "docs" / "fact" / "baseline"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "timestamp": "2024-01-01T00:00:00Z",
        "source_versions": {
            "repo-understanding": 5,
            "knowledge-confidence": 3,
            "domain-candidates": 7,
            "review-summary": None,  # Should be filtered out
        },
        "baseline_files": ["purpose.md"],
        "feedback_hash": "abc123",
    }
    checkpoint_path = checkpoint_dir / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint, indent=2))

    # Read accepted versions
    accepted = artifact_writer.get_accepted_versions(temp_repo)

    # Should have 3 entries (review-summary filtered out because it's None)
    assert len(accepted) == 3
    assert accepted["repo-understanding"] == {5}
    assert accepted["knowledge-confidence"] == {3}
    assert accepted["domain-candidates"] == {7}
    assert "review-summary" not in accepted


def test_get_accepted_versions_no_checkpoint(temp_repo):
    """Test that get_accepted_versions returns empty dict when no checkpoint exists."""
    accepted = artifact_writer.get_accepted_versions(temp_repo)
    assert accepted == {}


def test_get_accepted_versions_corrupted_checkpoint(temp_repo):
    """Test that get_accepted_versions handles corrupted checkpoint gracefully."""
    checkpoint_dir = temp_repo / "docs" / "fact" / "baseline"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "checkpoint.json"
    checkpoint_path.write_text("{ invalid json }")

    accepted = artifact_writer.get_accepted_versions(temp_repo)
    assert accepted == {}
