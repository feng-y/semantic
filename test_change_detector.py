#!/usr/bin/env python3
"""Quick test for change_detector module"""

from pathlib import Path
import tempfile
import shutil
from src.semantic.change_detector import ChangeDetector


def test_change_detector():
    """Test basic change detection functionality"""
    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state_file = root / "state.json"

        # Create test files
        (root / "file1.txt").write_text("content1")
        (root / "file2.txt").write_text("content2")

        # Initialize detector
        detector = ChangeDetector(state_file, ["*.txt"])

        # First run - all files should be added
        changes = detector.detect_changes(root)
        print(f"First run - Added: {len(changes['added'])}, Changed: {len(changes['changed'])}")
        assert len(changes['added']) == 2
        assert len(changes['changed']) == 0
        assert len(changes['removed']) == 0

        # Save state
        detector.save_state()

        # Second run - no changes
        detector2 = ChangeDetector(state_file, ["*.txt"])
        changes2 = detector2.detect_changes(root)
        print(f"Second run - Unchanged: {len(changes2['unchanged'])}, Changed: {len(changes2['changed'])}")
        assert len(changes2['unchanged']) == 2
        assert len(changes2['changed']) == 0

        # Modify a file
        (root / "file1.txt").write_text("modified content")

        # Third run - one changed
        detector3 = ChangeDetector(state_file, ["*.txt"])
        changes3 = detector3.detect_changes(root)
        print(f"Third run - Changed: {len(changes3['changed'])}, Unchanged: {len(changes3['unchanged'])}")
        assert len(changes3['changed']) == 1
        assert len(changes3['unchanged']) == 1

        # Remove a file
        (root / "file2.txt").unlink()

        # Fourth run - one removed
        detector4 = ChangeDetector(state_file, ["*.txt"])
        changes4 = detector4.detect_changes(root)
        print(f"Fourth run - Removed: {len(changes4['removed'])}")
        assert len(changes4['removed']) == 1

        print("\n✓ All tests passed!")


if __name__ == "__main__":
    test_change_detector()
