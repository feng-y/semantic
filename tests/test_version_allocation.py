"""Tests for atomic version allocation in artifact_writer."""

import threading
from pathlib import Path

import pytest

from src import artifact_writer


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def test_version_allocation_is_atomic(temp_repo):
    """Test that version allocation creates a file atomically with O_CREAT|O_EXCL."""
    base_dir = temp_repo / "docs" / "semantic" / "discovery"
    base_dir.mkdir(parents=True, exist_ok=True)

    # First allocation should return version 1
    v1 = artifact_writer._next_version(base_dir, "repo-understanding")
    assert v1 == 1

    # The lock file should exist
    assert (base_dir / "repo-understanding.v1.md").exists()

    # Second allocation should return version 2 (v1 file exists)
    v2 = artifact_writer._next_version(base_dir, "repo-understanding")
    assert v2 == 2


def test_concurrent_writes_get_different_versions(temp_repo):
    """Test that concurrent writes get different version numbers."""
    base_dir = temp_repo / "docs" / "semantic" / "discovery"
    base_dir.mkdir(parents=True, exist_ok=True)

    versions = []
    errors = []
    num_threads = 10

    def write_artifact():
        try:
            path = artifact_writer.write_artifact(
                temp_repo, "discovery", "repo-understanding",
                "Content from thread", versioned=True,
            )
            # Extract version number from path
            import re
            m = re.search(r"\.v(\d+)\.md$", path.name)
            if m:
                versions.append(int(m.group(1)))
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=write_artifact) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No errors should have occurred
    assert errors == [], f"Errors during concurrent writes: {errors}"

    # All versions should be unique
    assert len(versions) == num_threads, f"Expected {num_threads} versions, got {len(versions)}"
    assert len(set(versions)) == num_threads, f"Duplicate versions: {sorted(versions)}"


def test_version_allocation_skips_existing(temp_repo):
    """Test that version allocation skips already-existing version files."""
    base_dir = temp_repo / "docs" / "semantic" / "discovery"
    base_dir.mkdir(parents=True, exist_ok=True)

    # Pre-create versions 1 and 2 to simulate existing files
    (base_dir / "repo-facts.v1.md").write_text("v1")
    (base_dir / "repo-facts.v2.md").write_text("v2")

    # Next version should be 3
    v = artifact_writer._next_version(base_dir, "repo-facts")
    assert v == 3


def test_version_allocation_starts_at_one_for_new_artifact(temp_repo):
    """Test that version allocation starts at 1 for a new artifact."""
    base_dir = temp_repo / "docs" / "semantic" / "discovery"
    base_dir.mkdir(parents=True, exist_ok=True)

    v = artifact_writer._next_version(base_dir, "new-artifact")
    assert v == 1
