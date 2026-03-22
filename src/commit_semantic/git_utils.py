import re
import subprocess
from typing import TYPE_CHECKING

from src.types import RawCommit

if TYPE_CHECKING:
    from src.commit_semantic.state_tracker import StateTracker


def get_commit_list(repo_path: str, commit_range: str = None,
                   author: str = None, since: str = None,
                   until: str = None, no_merges: bool = False) -> list[str]:
    """Get list of commit IDs based on filters."""
    cmd = ["git", "-C", repo_path, "log", "--format=%H"]

    if no_merges:
        cmd.append("--no-merges")
    if commit_range:
        cmd.append(commit_range)
    if author:
        cmd.extend(["--author", author])
    if since:
        cmd.extend(["--since", since])
    if until:
        cmd.extend(["--until", until])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{e.stderr}") from e


def get_commit_details(repo_path: str, commit_id: str, exclude_paths: list[str] = None) -> RawCommit:
    """Extract detailed information for a single commit."""
    try:
        # Get commit metadata
        meta_cmd = ["git", "-C", repo_path, "show", "--format=%an%n%at", "--no-patch", commit_id]
        meta_result = subprocess.run(meta_cmd, capture_output=True, text=True, check=True)
        lines = meta_result.stdout.strip().split('\n')
        author = lines[0]
        timestamp = lines[1]

        # Get changed files
        files_cmd = ["git", "-C", repo_path, "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id]
        files_result = subprocess.run(files_cmd, capture_output=True, text=True, check=True)
        files = [f.strip() for f in files_result.stdout.strip().split('\n') if f.strip()]

        # Filter out excluded paths
        if exclude_paths:
            files = [f for f in files if not any(f.startswith(p) for p in exclude_paths)]

        # Get diff chunks
        diff_cmd = ["git", "-C", repo_path, "show", "--format=", commit_id]
        diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)
        raw_diff = diff_result.stdout
        # Split on "diff --git" boundaries, keeping the delimiter
        chunks = re.split(r'(?=^diff --git )', raw_diff, flags=re.MULTILINE)
        diff_chunks = [c for c in chunks if c.strip()]

        # Filter diff chunks for excluded paths
        if exclude_paths:
            def _chunk_path(chunk: str) -> str:
                m = re.match(r'^diff --git a/(\S+)', chunk)
                return m.group(1) if m else ''
            diff_chunks = [c for c in diff_chunks if not any(_chunk_path(c).startswith(p) for p in exclude_paths)]

        # Identify test files
        related_tests = [f for f in files if 'test' in f.lower() or f.endswith('_test.py') or f.endswith('.test.ts')]

        return RawCommit(
            commit_id=commit_id,
            author=author,
            timestamp=timestamp,
            files=files,
            diff_chunks=diff_chunks,
            related_tests=related_tests
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed for commit {commit_id}\n{e.stderr}") from e


def get_commit_message(repo_path: str, commit_id: str) -> str:
    """Get the commit message."""
    cmd = ["git", "-C", repo_path, "log", "--format=%B", "-n", "1", commit_id]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{e.stderr}") from e


def get_commit_list_incremental(
    repo_path: str,
    state_tracker: 'StateTracker',
    commit_range: str = None,
    author: str = None,
    since: str = None,
    until: str = None,
    force_reprocess: bool = False
) -> list[str]:
    """
    Get list of unprocessed commits.

    Args:
        repo_path: Path to git repository
        state_tracker: State tracker instance
        commit_range: Optional commit range (e.g., "HEAD~10..HEAD")
        author: Optional author filter
        since: Optional date filter (e.g., "2 weeks ago")
        until: Optional date filter
        force_reprocess: If True, ignore state and return all commits

    Returns:
        List of commit IDs that need processing
    """
    # Get all commits matching filters
    all_commits = get_commit_list(repo_path, commit_range, author, since, until)

    # If force reprocess, return all
    if force_reprocess:
        return all_commits

    # Filter out already processed commits
    return state_tracker.get_unprocessed_commits(all_commits)
