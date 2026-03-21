"""
Tests for change detection module
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.semantic.change_detector import ChangeDetector


@pytest.fixture
def temp_fact_dir():
    """Create temporary FACT directory for testing"""
    temp_dir = tempfile.mkdtemp()
    fact_root = Path(temp_dir) / "fact"
    fact_root.mkdir(parents=True)

    yield fact_root

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory for testing"""
    temp_dir = tempfile.mkdtemp()
    cache_dir = Path(temp_dir) / "cache"

    yield cache_dir

    # Cleanup
    shutil.rmtree(temp_dir)


def test_first_run_all_files_added(temp_fact_dir, temp_cache_dir):
    """Test that first run treats all files as added"""
    # Create test files
    canonical = temp_fact_dir / "fact_canonical_sample.yaml"
    canonical.write_text("modules: []\n")

    working = temp_fact_dir / "fact_working_summary_sample.yaml"
    working.write_text("concepts: []\n")

    detector = ChangeDetector(temp_fact_dir, temp_cache_dir)
    changes = detector.detect_changes()

    assert len(changes['changed']) == 0
    assert len(changes['added']) == 2
    assert len(changes['removed']) == 0
    assert canonical in changes['added']
    assert working in changes['added']


def test_no_changes_detected(temp_fact_dir, temp_cache_dir):
    """Test that unchanged files are not reported as changed"""
    # Create test file
    canonical = temp_fact_dir / "fact_canonical_sample.yaml"
    canonical.write_text("modules: []\n")

    detector = ChangeDetector(temp_fact_dir, temp_cache_dir)

    # First run
    detector.detect_changes()

    # Second run - no changes
    changes = detector.detect_changes()

    assert len(changes['changed']) == 0
    assert len(changes['added']) == 0
    assert len(changes['removed']) == 0


def test_file_modification_detected(temp_fact_dir, temp_cache_dir):
    """Test that modified files are detected"""
    # Create test file
    canonical = temp_fact_dir / "fact_canonical_sample.yaml"
    canonical.write_text("modules: []\n")

    detector = ChangeDetector(temp_fact_dir, temp_cache_dir)

    # First run
    detector.detect_changes()

    # Modify file
    canonical.write_text("modules: [module1]\n")

    # Second run - should detect change
    changes = detector.detect_changes()

    assert len(changes['changed']) == 1
    assert canonical in changes['changed']
    assert len(changes['added']) == 0
    assert len(changes['removed']) == 0


def test_file_removal_detected(temp_fact_dir, temp_cache_dir):
    """Test that removed files are detected"""
    # Create test file
    canonical = temp_fact_dir / "fact_canonical_sample.yaml"
    canonical.write_text("modules: []\n")

    detector = ChangeDetector(temp_fact_dir, temp_cache_dir)

    # First run
    detector.detect_changes()

    # Remove file
    canonical.unlink()

    # Second run - should detect removal
    changes = detector.detect_changes()

    assert len(changes['changed']) == 0
    assert len(changes['added']) == 0
    assert len(changes['removed']) == 1
    assert canonical in changes['removed']


def test_compute_file_hash(temp_fact_dir, temp_cache_dir):
    """Test file hash computation"""
    # Create test file
    test_file = temp_fact_dir / "test.yaml"
    test_file.write_text("test content\n")

    detector = ChangeDetector(temp_fact_dir, temp_cache_dir)
    hash1 = detector.compute_file_hash(test_file)

    # Same content should produce same hash
    hash2 = detector.compute_file_hash(test_file)
    assert hash1 == hash2

    # Different content should produce different hash
    test_file.write_text("different content\n")
    hash3 = detector.compute_file_hash(test_file)
    assert hash1 != hash3


def test_has_changes(temp_fact_dir, temp_cache_dir):
    """Test has_changes convenience method"""
    # Create test file
    canonical = temp_fact_dir / "fact_canonical_sample.yaml"
    canonical.write_text("modules: []\n")

    detector = ChangeDetector(temp_fact_dir, temp_cache_dir)

    # First run - has changes (new files)
    assert detector.has_changes() is True
    detector.detect_changes()  # Save baseline

    # Second run - no changes
    assert detector.has_changes() is False

    # Modify file
    canonical.write_text("modules: [module1]\n")

    # Third run - has changes
    assert detector.has_changes() is True


def test_baseline_files_tracked(temp_fact_dir, temp_cache_dir):
    """Test that baseline markdown files are tracked"""
    # Create baseline directory
    baseline_dir = temp_fact_dir.parent / "fact" / "baseline"
    baseline_dir.mkdir(parents=True)

    baseline_file = baseline_dir / "test.md"
    baseline_file.write_text("# Test baseline\n")

    detector = ChangeDetector(temp_fact_dir, temp_cache_dir)
    tracked = detector.get_tracked_files()

    assert baseline_file in tracked
