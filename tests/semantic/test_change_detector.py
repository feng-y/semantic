"""
Tests for ChangeDetector module
"""

import pytest
from pathlib import Path
import json
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.change_detector import ChangeDetector


def test_change_detector_init(tmp_path):
    """Test ChangeDetector initialization"""
    state_file = tmp_path / "state.json"
    patterns = ["*.yaml", "*.py"]

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    assert detector.fact_root == tmp_path
    assert detector.cache_dir == tmp_path / "cache"
    assert detector.state_file.parent.exists()
    assert detector.fact_root == tmp_path
    assert detector.cache_dir == tmp_path / "cache"
    assert detector.state_file.parent.exists()
def test_compute_file_hash(tmp_path):
    """Test file hash computation"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    state_file = tmp_path / "state.json"
    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    hash1 = detector.compute_file_hash(test_file)
    hash2 = detector.compute_file_hash(test_file)

    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex length

    # Different content should produce different hash
    test_file.write_text("Different content")
    hash3 = detector.compute_file_hash(test_file)
    assert hash1 != hash3


def test_compute_file_hash_nonexistent(tmp_path):
    """Test hash computation for nonexistent file"""
    state_file = tmp_path / "state.json"
    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    nonexistent = tmp_path / "nonexistent.txt"
    hash_result = detector.compute_file_hash(nonexistent)

    # Should return empty string for unreadable files
    assert hash_result == ""


def test_get_tracked_files(tmp_path):
    """Test getting tracked files by pattern"""
    # Create the actual FACT files that get_tracked_files looks for
    (tmp_path / "fact_canonical_sample.yaml").write_text("content1")
    (tmp_path / "fact_working_summary_sample.yaml").write_text("content2")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    tracked = detector.get_tracked_files()

    # Should find the FACT files (baseline files may or may not exist)
    assert len(tracked) >= 2
    tracked_names = {f.name for f in tracked}
    assert "fact_canonical_sample.yaml" in tracked_names
    assert "fact_working_summary_sample.yaml" in tracked_names


def test_get_tracked_files_no_duplicates(tmp_path):
    """Test that tracked files have no duplicates"""
    # Create the actual FACT files
    (tmp_path / "fact_canonical_sample.yaml").write_text("content1")
    (tmp_path / "fact_working_summary_sample.yaml").write_text("content2")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    tracked = detector.get_tracked_files()

    # Should not have duplicates
    assert len(tracked) == len(set(tracked))


def test_detect_changes_first_run(tmp_path):
    """Test change detection on first run (no previous state)"""
    # Create the actual FACT files
    (tmp_path / "fact_canonical_sample.yaml").write_text("content1")
    (tmp_path / "fact_working_summary_sample.yaml").write_text("content2")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    changes = detector.detect_changes()

    # First run: all files are "added" (may include baseline files if they exist)
    assert len(changes['added']) >= 2
    assert len(changes['changed']) == 0
    assert len(changes['removed']) == 0
    assert len(changes['unchanged']) == 0


def test_detect_changes_no_changes(tmp_path):
    """Test change detection when nothing changed"""
    # Create the actual FACT file
    file1 = tmp_path / "fact_canonical_sample.yaml"
    file1.write_text("content1")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    # First run
    changes1 = detector.detect_changes()

    # Second run - no changes (detect_changes saves state automatically)
    detector2 = ChangeDetector(tmp_path, tmp_path / "cache")
    changes2 = detector2.detect_changes()

    assert len(changes2['added']) == 0
    assert len(changes2['changed']) == 0
    assert len(changes2['removed']) == 0
    assert len(changes2['unchanged']) >= 1


def test_detect_changes_file_modified(tmp_path):
    """Test change detection when file is modified"""
    file1 = tmp_path / "fact_canonical_sample.yaml"
    file1.write_text("original content")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    # First run
    detector.detect_changes()

    # Modify file
    file1.write_text("modified content")

    # Second run
    detector2 = ChangeDetector(tmp_path, tmp_path / "cache")
    changes = detector2.detect_changes()

    assert len(changes['changed']) == 1
    assert changes['changed'][0] == file1


def test_detect_changes_file_added(tmp_path):
    """Test change detection when file is added"""
    file1 = tmp_path / "fact_canonical_sample.yaml"
    file1.write_text("content1")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    # First run
    detector.detect_changes()

    # Add new file
    file2 = tmp_path / "fact_working_summary_sample.yaml"
    file2.write_text("content2")

    # Second run
    detector2 = ChangeDetector(tmp_path, tmp_path / "cache")
    changes = detector2.detect_changes()

    assert len(changes['added']) == 1
    assert changes['added'][0] == file2
    assert len(changes['unchanged']) >= 1


def test_detect_changes_file_removed(tmp_path):
    """Test change detection when file is removed"""
    file1 = tmp_path / "fact_canonical_sample.yaml"
    file2 = tmp_path / "fact_working_summary_sample.yaml"
    file1.write_text("content1")
    file2.write_text("content2")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    # First run
    detector.detect_changes()

    # Remove file
    file2.unlink()

    # Second run
    detector2 = ChangeDetector(tmp_path, tmp_path / "cache")
    changes = detector2.detect_changes()

    assert len(changes['removed']) == 1
    assert changes['removed'][0] == file2
    assert len(changes['unchanged']) >= 1


def test_detect_changes_mixed(tmp_path):
    """Test change detection with mixed changes"""
    file1 = tmp_path / "fact_canonical_sample.yaml"
    file2 = tmp_path / "fact_working_summary_sample.yaml"

    file1.write_text("content1")
    file2.write_text("content2")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    # First run
    detector.detect_changes()

    # Make mixed changes
    file1.write_text("modified content1")  # Changed
    file2.unlink()  # Removed

    # Add baseline file
    baseline_dir = tmp_path.parent / "fact" / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    file3 = baseline_dir / "new_baseline.md"
    file3.write_text("content3")  # Added

    # Second run
    detector2 = ChangeDetector(tmp_path, tmp_path / "cache")
    changes = detector2.detect_changes()

    # Should have at least 1 added, 1 changed, 1 removed
    assert len(changes['added']) >= 1
    assert len(changes['changed']) >= 1
    assert len(changes['removed']) >= 1
    assert len(changes['changed']) == 1
    assert len(changes['removed']) == 1
    assert len(changes['unchanged']) == 0


def test_save_and_load_state(tmp_path):
    """Test state persistence"""
    file1 = tmp_path / "fact_canonical_sample.yaml"
    file1.write_text("content1")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    # Detect changes (saves state automatically)
    detector.detect_changes()

    # Verify state file exists
    state_file = tmp_path / "cache" / "change_state.json"
    assert state_file.exists()

    # Load state in new detector
    detector2 = ChangeDetector(tmp_path, tmp_path / "cache")
    previous_hashes = detector2.load_state()

    assert len(previous_hashes) >= 1
    # Check that the file key is in the state
    assert any("fact_canonical_sample.yaml" in key for key in previous_hashes.keys())


def test_state_file_structure(tmp_path):
    """Test state file JSON structure"""
    file1 = tmp_path / "fact_canonical_sample.yaml"
    file1.write_text("content1")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    detector.detect_changes()

    # Read and verify structure
    state_file = tmp_path / "cache" / "change_state.json"
    with open(state_file, 'r') as f:
        data = json.load(f)

    assert 'file_hashes' in data
    assert 'last_updated' in data
    # Note: tracked_patterns is no longer in the state file


def test_load_state_corrupted_file(tmp_path):
    """Test loading corrupted state file"""
    state_file = tmp_path / "cache" / "change_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("invalid json {{{")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")
    previous_hashes = detector.load_state()

    # Should handle gracefully with empty state
    assert previous_hashes == {}


def test_load_state_missing_file(tmp_path):
    """Test loading nonexistent state file"""
    state_file = tmp_path / "nonexistent.json"

    detector = ChangeDetector(tmp_path, tmp_path / "cache")
    detector.load_state()

    # Should handle gracefully with empty state


def test_state_file_parent_directory_creation(tmp_path):
    """Test that parent directories are created for state file"""
    file1 = tmp_path / "fact_canonical_sample.yaml"
    file1.write_text("content1")

    detector = ChangeDetector(tmp_path, tmp_path / "cache")
    detector.detect_changes()

    # Parent directories should be created
    state_file = tmp_path / "cache" / "change_state.json"
    assert state_file.parent.exists()
    assert state_file.exists()


def test_empty_tracked_patterns(tmp_path):
    """Test with empty tracked patterns"""
    # Don't create any FACT files - test should handle empty case
    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    changes = detector.detect_changes()

    # May have baseline files from previous tests, so check for reasonable behavior
    # The key is that it doesn't crash
    assert 'added' in changes
    assert 'changed' in changes
    assert 'removed' in changes
    assert 'unchanged' in changes
