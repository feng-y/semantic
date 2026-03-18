# Incremental Build Architecture Design

## 1. Overview

This document defines a minimal incremental processing system for the commit-semantic pipeline that avoids reprocessing the entire commit history on subsequent runs.

**Design Principles:**
- Keep state tracking minimal and isolated
- Maintain clear separation from core semantic extraction logic
- Make incremental mode optional, not mandatory
- Avoid complexity explosion in edge case handling

## 2. State Tracking Mechanism

### 2.1 Processed Commits Registry

**Location:** `data/.commit-semantic-state.json`

**Schema:**
```json
{
  "version": "1.0",
  "repo_path": "/absolute/path/to/repo",
  "last_updated": "2026-03-18T10:30:00Z",
  "processed_commits": {
    "abc123def456": {
      "timestamp": "2026-03-15T14:20:00Z",
      "case_ids": ["abc123-parser-01", "abc123-qserver-01"],
      "status": "completed"
    },
    "def456abc789": {
      "timestamp": "2026-03-16T09:15:00Z",
      "case_ids": ["def456-registry-01"],
      "status": "completed"
    }
  },
  "metadata": {
    "total_commits_processed": 245,
    "total_cases_generated": 312
  }
}
```

**Key Fields:**
- `processed_commits`: Map of commit SHA → processing metadata
- `timestamp`: When the commit was processed (ISO 8601)
- `case_ids`: List of semantic case IDs generated from this commit
- `status`: `completed` | `failed` | `skipped`

### 2.2 State File Management

**Module:** `src/commit_semantic/state_tracker.py`

```python
class StateTracker:
    def __init__(self, state_path: Path):
        """Initialize state tracker with path to state file."""

    def load_state(self) -> dict:
        """Load existing state or return empty state."""

    def save_state(self, state: dict) -> None:
        """Atomically save state to disk."""

    def mark_commit_processed(self, commit_id: str, case_ids: list[str]) -> None:
        """Mark a commit as successfully processed."""

    def is_commit_processed(self, commit_id: str) -> bool:
        """Check if commit has been processed."""

    def get_unprocessed_commits(self, all_commits: list[str]) -> list[str]:
        """Filter out already processed commits."""
```

**Atomic Write Strategy:**
- Write to temporary file: `data/.commit-semantic-state.json.tmp`
- Atomic rename to: `data/.commit-semantic-state.json`
- Prevents corruption on interrupted writes

## 3. Commit Range Filtering Strategy

### 3.1 Git Log Integration

**Enhancement to `src/commit_semantic/git_utils.py`:**

```python
def get_commit_list_incremental(
    repo_path: str,
    state_tracker: StateTracker,
    commit_range: str = None,
    author: str = None,
    since: str = None,
    until: str = None,
    force_reprocess: bool = False
) -> List[str]:
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
```

### 3.2 CLI Integration

**Add flag to collect_cases skill:**

```bash
# Process only new commits (incremental mode)
/commit-semantic:collect_cases --incremental

# Force reprocess all commits
/commit-semantic:collect_cases --force

# Process specific range incrementally
/commit-semantic:collect_cases --incremental --range "HEAD~50..HEAD"
```

## 4. Update Handling for Existing Cases

### 4.1 Commit Amendment Detection

**Challenge:** Git commit SHAs change when commits are amended or rebased.

**Strategy:** Do NOT attempt to track amended commits automatically.

**Rationale:**
- Detecting amended commits requires complex heuristics (author + timestamp + file similarity)
- Adds significant complexity for rare edge cases
- Users can explicitly force reprocess if needed

**Recommended Approach:**
```bash
# If commits were amended/rebased, force reprocess the range
/commit-semantic:collect_cases --force --range "HEAD~20..HEAD"
```

### 4.2 Case Update Strategy

**When to regenerate cases:**
1. Commit is not in processed registry → generate new cases
2. Commit is in registry with `status: failed` → retry generation
3. Commit is in registry with `status: completed` → skip (unless force mode)

**No automatic case updates:** If a commit was already processed, we don't regenerate its cases unless explicitly forced.

## 5. Merge Strategy for Incremental Exports

### 5.1 Export File Structure

**Current exports:**
- `data/exports/semantic_cases.jsonl` - All cases in JSONL format
- `data/semantic_cases/*.yaml` - Individual case files

**Incremental merge strategy:**

```python
def merge_incremental_export(
    existing_export_path: Path,
    new_cases: list[dict],
    state_tracker: StateTracker
) -> None:
    """
    Merge new cases into existing export.

    Strategy:
    1. Load existing JSONL export
    2. Append new cases
    3. Write back atomically
    4. Update state tracker
    """
    # Load existing cases
    existing_cases = []
    if existing_export_path.exists():
        with open(existing_export_path, 'r') as f:
            existing_cases = [json.loads(line) for line in f]

    # Append new cases
    all_cases = existing_cases + new_cases

    # Write atomically
    tmp_path = existing_export_path.with_suffix('.jsonl.tmp')
    with open(tmp_path, 'w') as f:
        for case in all_cases:
            f.write(json.dumps(case, ensure_ascii=False) + '\n')

    tmp_path.rename(existing_export_path)
```

**No deduplication at export time:** Deduplication happens in the semantic analysis phase (via `dedup.py`), not during export merge.

## 6. Edge Cases

### 6.1 Force Push

**Scenario:** Remote branch was force-pushed, local history diverged.

**Handling:**
- State file tracks commits by SHA
- After force push, old SHAs no longer exist in history
- New commits with different SHAs will be processed normally
- Old processed commits remain in state file (harmless)

**User action:** None required. System handles automatically.

**Optional cleanup:**
```bash
# Remove state entries for commits no longer in history
/commit-semantic:clean_state
```

### 6.2 Branch Switch

**Scenario:** User switches from `main` to `feature-branch`.

**Handling:**
- State file is repository-wide, not branch-specific
- Commits unique to `feature-branch` will be processed
- Commits shared with `main` will be skipped (already processed)

**User action:** None required.

### 6.3 Merge Commits

**Scenario:** Merge commit brings in commits from another branch.

**Handling:**
- Merge commit itself is processed like any commit
- Individual commits in the merged branch are processed if not already in state
- Git log traversal naturally includes all reachable commits

**User action:** None required.

### 6.4 State File Corruption

**Scenario:** State file is corrupted or deleted.

**Handling:**
- If state file is missing: treat as fresh run, process all commits
- If state file is corrupted (invalid JSON): log error, treat as fresh run
- Backup strategy: keep last 3 state files as `.commit-semantic-state.json.backup.N`

**User action:**
```bash
# Restore from backup if needed
cp data/.commit-semantic-state.json.backup.1 data/.commit-semantic-state.json
```

### 6.5 Partial Processing Failure

**Scenario:** Processing crashes midway through a batch.

**Handling:**
- State is updated after each commit is successfully processed
- On restart, only unprocessed commits are retried
- Failed commits are marked with `status: failed` and can be retried

**User action:**
```bash
# Retry failed commits
/commit-semantic:collect_cases --retry-failed
```

## 7. Implementation Plan

### Phase 1: Core State Tracking (Priority: High)

**Files to create:**
- `src/commit_semantic/state_tracker.py` - State management logic

**Files to modify:**
- `src/commit_semantic/git_utils.py` - Add incremental filtering
- `skills/collect_cases/run.py` - Add `--incremental` flag

**Deliverables:**
- State file creation and atomic updates
- Commit filtering based on processed registry
- CLI flag for incremental mode

### Phase 2: Export Merge (Priority: High)

**Files to modify:**
- `skills/export_cases/run.py` - Add incremental merge logic

**Deliverables:**
- Append-only export strategy
- Atomic export file updates

### Phase 3: Edge Case Handling (Priority: Medium)

**Files to create:**
- `skills/clean_state/run.py` - State cleanup utility

**Files to modify:**
- `src/commit_semantic/state_tracker.py` - Add backup rotation

**Deliverables:**
- State file backup rotation
- Cleanup utility for orphaned state entries
- Retry logic for failed commits

### Phase 4: Testing & Documentation (Priority: Medium)

**Files to create:**
- `tests/test_state_tracker.py` - Unit tests
- `tests/test_incremental_flow.py` - Integration tests

**Deliverables:**
- Test coverage for state tracking
- Test coverage for edge cases
- Updated README with incremental mode usage

## 8. Usage Examples

### 8.1 First Run (Full Processing)

```bash
# Process all commits in repository
/commit-semantic:collect_cases
/commit-semantic:generate_case_semantics
/commit-semantic:export_cases

# State file created: data/.commit-semantic-state.json
# All commits marked as processed
```

### 8.2 Incremental Run (New Commits Only)

```bash
# Process only new commits since last run
/commit-semantic:collect_cases --incremental
/commit-semantic:generate_case_semantics
/commit-semantic:export_cases

# Only unprocessed commits are analyzed
# State file updated with new commits
# Exports merged with existing data
```

### 8.3 Force Reprocess Range

```bash
# Reprocess last 20 commits (ignore state)
/commit-semantic:collect_cases --force --range "HEAD~20..HEAD"
/commit-semantic:generate_case_semantics
/commit-semantic:export_cases

# Specified commits reprocessed
# State file updated
# Exports may contain duplicates (handled by dedup.py)
```

### 8.4 Clean Orphaned State

```bash
# Remove state entries for commits no longer in history
/commit-semantic:clean_state

# Scans git history
# Removes state entries for missing commits
# Compacts state file
```

## 9. Performance Considerations

### 9.1 State File Size

**Growth rate:** ~200 bytes per commit

**Example:**
- 10,000 commits → ~2 MB state file
- 100,000 commits → ~20 MB state file

**Mitigation:** State file size is negligible for typical repositories.

### 9.2 State Lookup Performance

**Lookup strategy:** In-memory hash map (Python dict)

**Performance:**
- Load state: O(n) where n = number of processed commits
- Check if processed: O(1) hash lookup
- Filter commits: O(m) where m = number of candidate commits

**Bottleneck:** Not the state lookup, but the semantic extraction itself.

## 10. Backward Compatibility

### 10.1 Existing Workflows

**Without incremental mode:**
- All existing skills work unchanged
- No state file is created or used
- Full processing on every run (current behavior)

**With incremental mode:**
- Opt-in via `--incremental` flag
- State file created on first incremental run
- Subsequent runs use state for filtering

### 10.2 Migration Path

**For existing users:**
1. Continue using current workflow (no changes required)
2. When ready, add `--incremental` flag to enable incremental mode
3. First incremental run processes all commits and creates state file
4. Subsequent runs process only new commits

**No breaking changes:** Incremental mode is purely additive.

## 11. Summary

This incremental build architecture provides:

✅ **Minimal state tracking** - Just commit SHAs + timestamps + case IDs
✅ **Clear separation** - State logic isolated in `state_tracker.py`
✅ **Simple merge strategy** - Append-only exports with atomic writes
✅ **Graceful edge case handling** - No complexity explosion
✅ **Optional feature** - Existing workflows unchanged
✅ **Performance gain** - Skip already-processed commits

**Key trade-offs:**
- No automatic detection of amended commits (user must force reprocess)
- No automatic deduplication at export time (handled by dedup.py)
- State file grows linearly with commit count (acceptable for typical repos)

**Implementation effort:** ~2-3 days for core functionality + testing.
