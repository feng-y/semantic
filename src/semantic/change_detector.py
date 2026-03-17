"""
Change Detection Module

Detects which FACT input files have changed since the last extraction run.
Uses file hashing to determine what needs re-processing.
"""

from pathlib import Path
from typing import Set, Optional, Dict, List
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone


class ChangeDetector:
    """Detects changes in FACT input files for incremental processing"""

    def __init__(self, fact_root: Path, cache_dir: Path):
        self.fact_root = fact_root
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = cache_dir / "change_state.json"

    def get_tracked_files(self) -> Set[Path]:
        """Get list of FACT files to track for changes"""
        tracked = set()

        # Primary FACT files
        canonical = self.fact_root / "fact_canonical_sample.yaml"
        working = self.fact_root / "fact_working_summary_sample.yaml"

        if canonical.exists():
            tracked.add(canonical)
        if working.exists():
            tracked.add(working)

        # Baseline markdown files
        baseline_dir = self.fact_root.parent / "fact" / "baseline"
        if baseline_dir.exists():
            for md_file in baseline_dir.glob("*.md"):
                tracked.add(md_file)

        return tracked

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file contents"""
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (FileNotFoundError, PermissionError):
            return ""

    def load_state(self) -> Dict[str, str]:
        """Load previous file hashes from state file"""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                return data.get('file_hashes', {})
        except (json.JSONDecodeError, KeyError):
            return {}

    def save_state(self, file_hashes: Dict[str, str]):
        """Save current file hashes to state file (atomic write)"""
        state = {
            'file_hashes': file_hashes,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        with tempfile.NamedTemporaryFile('w', dir=self.cache_dir, delete=False,
                                         suffix='.tmp', encoding='utf-8') as tmp:
            json.dump(state, tmp, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, self.state_file)

    def detect_changes(self, save: bool = True) -> Dict[str, List[Path]]:
        """
        Detect which files have changed since last run.

        Returns:
            Dict with keys: 'added', 'changed', 'removed', 'unchanged'
        """
        tracked_files = self.get_tracked_files()
        previous_hashes = self.load_state()
        current_hashes = {}

        changes = {
            'added': [],
            'changed': [],
            'removed': [],
            'unchanged': []
        }

        # Check current files
        for file_path in tracked_files:
            try:
                file_key = str(file_path.relative_to(self.fact_root.parent))
            except ValueError:
                file_key = str(file_path)
            current_hash = self.compute_file_hash(file_path)
            current_hashes[file_key] = current_hash

            if file_key not in previous_hashes:
                changes['added'].append(file_path)
            elif previous_hashes[file_key] != current_hash:
                changes['changed'].append(file_path)
            else:
                changes['unchanged'].append(file_path)

        # Check for removed files
        for file_key in previous_hashes:
            file_path = self.fact_root.parent / file_key
            if file_path not in tracked_files:
                changes['removed'].append(file_path)

        # Save current state
        if save:
            self.save_state(current_hashes)

        return changes

    def has_changes(self) -> bool:
        """Quick check if any files have changed (read-only, does not save state)"""
        changes = self.detect_changes(save=False)
        return bool(changes['added'] or changes['changed'] or changes['removed'])

    def is_first_run(self) -> bool:
        """Check if this is the first run (no previous state)"""
        return not self.state_file.exists()
