import subprocess
from typing import List, Tuple
from src.types import RawCommit


def get_commit_list(repo_path: str, commit_range: str = None,
                   author: str = None, since: str = None,
                   until: str = None) -> List[str]:
    """Get list of commit IDs based on filters."""
    cmd = ["git", "-C", repo_path, "log", "--format=%H"]

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


def get_commit_details(repo_path: str, commit_id: str) -> RawCommit:
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

        # Get diff chunks
        diff_cmd = ["git", "-C", repo_path, "show", "--format=", commit_id]
        diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)
        diff_chunks = [diff_result.stdout]

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
