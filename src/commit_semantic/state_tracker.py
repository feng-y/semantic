"""
State tracking for incremental commit processing.

Manages a registry of processed commits to avoid reprocessing.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class StateTracker:
    """Tracks which commits have been processed."""

    def __init__(self, state_path: Path):
        """
        Initialize state tracker.

        Args:
            state_path: Path to state file (e.g., data/.commit-semantic-state.json)
        """
        self.state_path = Path(state_path)
        self.state = self.load_state()

    def load_state(self) -> dict:
        """Load existing state or return empty state."""
        if not self.state_path.exists():
            return self._empty_state()

        try:
            with open(self.state_path, encoding='utf-8') as f:
                state = json.load(f)
                # Validate schema version
                if state.get('version') != '1.0':
                    print(f"Warning: Unknown state version {state.get('version')}, treating as fresh state")
                    return self._empty_state()
                return state
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to load state file: {e}")
            print("Treating as fresh state")
            return self._empty_state()

    def save_state(self, state: dict | None = None) -> None:
        """
        Atomically save state to disk.

        Args:
            state: State dict to save (uses self.state if None)
        """
        if state is None:
            state = self.state

        # Update last_updated timestamp
        state['last_updated'] = datetime.now(timezone.utc).isoformat()

        # Ensure parent directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file
        tmp_path = self.state_path.with_suffix('.json.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        # Atomic rename
        tmp_path.rename(self.state_path)

    def mark_commit_processed(
        self,
        commit_id: str,
        case_ids: list[str],
        status: str = 'completed'
    ) -> None:
        """
        Mark a commit as processed.

        Args:
            commit_id: Git commit SHA
            case_ids: List of semantic case IDs generated from this commit
            status: Processing status ('completed', 'failed', 'skipped')
        """
        self.state['processed_commits'][commit_id] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'case_ids': case_ids,
            'status': status
        }

        # Update metadata
        if status == 'completed':
            self.state['metadata']['total_commits_processed'] += 1
            self.state['metadata']['total_cases_generated'] += len(case_ids)

        self.save_state()

    def is_commit_processed(self, commit_id: str) -> bool:
        """
        Check if commit has been successfully processed.

        Args:
            commit_id: Git commit SHA

        Returns:
            True if commit was processed with status 'completed'
        """
        commit_data = self.state['processed_commits'].get(commit_id)
        if not commit_data:
            return False
        return commit_data.get('status') == 'completed'

    def get_unprocessed_commits(self, all_commits: list[str]) -> list[str]:
        """
        Filter out already processed commits.

        Args:
            all_commits: List of all commit IDs to check

        Returns:
            List of commit IDs that need processing
        """
        return [
            commit_id for commit_id in all_commits
            if not self.is_commit_processed(commit_id)
        ]

    def get_failed_commits(self) -> list[str]:
        """
        Get list of commits that failed processing.

        Returns:
            List of commit IDs with status 'failed'
        """
        return [
            commit_id for commit_id, data in self.state['processed_commits'].items()
            if data.get('status') == 'failed'
        ]

    def _empty_state(self) -> dict:
        """Create empty state structure."""
        return {
            'version': '1.0',
            'repo_path': '',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'processed_commits': {},
            'metadata': {
                'total_commits_processed': 0,
                'total_cases_generated': 0
            }
        }
