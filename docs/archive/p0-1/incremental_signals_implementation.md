# Incremental Signals Extraction Implementation

**Status**: ✅ Implemented
**Version**: 1.0.0
**Last Updated**: 2026-03-17

## Overview

Incremental signals extraction enables efficient re-processing of FACT inputs by only extracting signals from changed files and reusing cached results for unchanged files. This dramatically reduces both cost and execution time for iterative workflows.

### Key Benefits

- **80% Cost Reduction**: Only process changed files (typically 20% of codebase)
- **80% Time Savings**: Skip extraction for unchanged files
- **Iterative Workflow**: Makes frequent re-runs practical and affordable
- **Cache Transparency**: Automatic cache management with manual override options

## Architecture

The incremental extraction system consists of two core components:

### 1. ChangeDetector

**Purpose**: Detect which FACT input files have changed since the last extraction.

**Location**: `src/semantic/change_detector.py`

**Key Features**:
- SHA256-based file hashing for reliable change detection
- Glob pattern support for flexible file tracking
- State persistence across runs
- Categorizes files as: added, changed, removed, unchanged

**How It Works**:
```python
# 1. Scan tracked files and compute current hashes
current_files = get_tracked_files(root_dir)
current_state = {file: compute_hash(file) for file in current_files}

# 2. Load previous state from disk
previous_state = load_state()

# 3. Compare states to detect changes
added = current_files - previous_files
removed = previous_files - current_files
changed = files where hash differs
unchanged = files where hash matches

# 4. Save current state for next run
save_state(current_state)
```

**State File Format**:
```json
{
  "file_hashes": {
    "/path/to/file1.yaml": "abc123...",
    "/path/to/file2.yaml": "def456..."
  },
  "updated_at": "2026-03-17T10:30:00Z",
  "tracked_patterns": ["*.yaml", "docs/**/*.md"]
}
```

### 2. SignalCache

**Purpose**: Store and retrieve extracted signals at file granularity.

**Location**: `src/semantic/signal_cache.py`

**Key Features**:
- File-level signal caching with hash verification
- MD5-based cache keys (path + hash)
- Automatic cache invalidation on file changes
- Cache statistics and management utilities

**How It Works**:
```python
# 1. Generate cache key from file path + hash
cache_key = md5(f"{file_path}:{file_hash}")

# 2. Store signals with metadata
cache_entry = {
  'file_path': str(file_path),
  'file_hash': file_hash,
  'signals': extracted_signals,
  'cached_at': timestamp
}

# 3. Retrieve signals if hash matches
cached_signals = get(file_path, file_hash)
if cached_signals and cached_signals['file_hash'] == current_hash:
    return cached_signals['signals']
```

**Cache Directory Structure**:
```
.semantic-cache/
├── signals/
│   ├── a1b2c3d4.json  # Cached signals for file 1
│   ├── e5f6g7h8.json  # Cached signals for file 2
│   └── ...
└── change_state.json  # Change detection state
```

## Usage

### Full Extraction (Default)

Process all files regardless of changes:

```bash
# Extract signals from all FACT inputs
semantic-signals --fact-root docs/semantic-foundation/fact \
                 --output docs/semantic-foundation/semantic/signals.yaml
```

### Incremental Extraction

Process only changed files and reuse cached results:

```bash
# Extract signals incrementally
semantic-signals --fact-root docs/semantic-foundation/fact \
                 --output docs/semantic-foundation/semantic/signals.yaml \
                 --incremental
```

### Custom Cache Directory

Specify a custom cache location:

```bash
# Use custom cache directory
semantic-signals --fact-root docs/semantic-foundation/fact \
                 --output docs/semantic-foundation/semantic/signals.yaml \
                 --incremental \
                 --cache-dir /path/to/custom/cache
```

Default cache location: `.semantic-cache/` in the current working directory.

### Clear Cache

Force full re-extraction by clearing the cache:

```bash
# Clear cache and run full extraction
semantic-signals --fact-root docs/semantic-foundation/fact \
                 --output docs/semantic-foundation/semantic/signals.yaml \
                 --incremental \
                 --clear-cache
```

## Performance Characteristics

### Typical Scenario

**Initial Run** (no cache):
- Processes: 100% of files
- Time: 10-30 minutes (large projects)
- Cost: $10-50 in API calls

**Incremental Run** (20% changed):
- Processes: 20% of files (changed only)
- Reuses: 80% from cache (unchanged)
- Time: 2-6 minutes (80% faster)
- Cost: $2-10 (80% cheaper)

### Performance Factors

**Cache Hit Rate**:
- High (80-90%): Typical for focused changes
- Medium (50-70%): Moderate refactoring
- Low (<50%): Major restructuring

**File Size Impact**:
- Large files: Greater benefit from caching
- Small files: Lower overhead, still beneficial

**Change Patterns**:
- Localized changes: Maximum benefit
- Widespread changes: Reduced benefit
- Configuration changes: May affect many files

## Implementation Details

### Change Detection Algorithm

1. **File Discovery**: Scan for files matching tracked patterns
2. **Hash Computation**: Calculate SHA256 for each file
3. **State Comparison**: Compare with previous run's state
4. **Categorization**: Classify as added/changed/removed/unchanged
5. **State Persistence**: Save current state for next run

### Cache Management

**Cache Key Generation**:
```python
cache_key = md5(f"{file_path}:{file_hash}")
```

**Cache Validation**:
- Verify file hash matches cached hash
- Reject cache entries with mismatched hashes
- Handle corrupted cache files gracefully

**Cache Merging**:
```python
# Combine cached and newly extracted signals
all_signals = cached_signals + new_signals
```

### Error Handling

**Unreadable Files**:
- Return empty hash
- Skip from tracking
- Log warning

**Corrupted Cache**:
- Ignore corrupted entries
- Re-extract signals
- Continue processing

**Missing State File**:
- Treat as first run
- Process all files
- Create new state

## Testing

### Test Coverage

**Total Tests**: 61
**Coverage**: 97%

**Test Categories**:
- Change detection: 29 tests
- Signal caching: 32 tests
- Integration scenarios: Multiple test cases

### Key Test Scenarios

**ChangeDetector Tests**:
- File hash computation (deterministic, unique)
- Change detection (added, changed, removed, unchanged)
- State persistence (save, load, recovery)
- Edge cases (empty patterns, nonexistent files, corrupted state)

**SignalCache Tests**:
- Cache operations (put, get, invalidate, clear)
- Cache key generation (deterministic, unique)
- Hash verification (match, mismatch)
- Complex signal structures
- Cache statistics

**Integration Tests**:
- End-to-end incremental extraction
- Cache hit/miss scenarios
- State persistence across runs

### Running Tests

```bash
# Run all tests
pytest tests/semantic/

# Run with coverage
pytest tests/semantic/ --cov=src/semantic --cov-report=term-missing

# Run specific test file
pytest tests/semantic/test_change_detector.py
pytest tests/semantic/test_signal_cache.py
```

## Troubleshooting

### Cache Not Being Used

**Symptoms**: Every run processes all files

**Possible Causes**:
1. `--incremental` flag not specified
2. Cache directory doesn't exist or is inaccessible
3. State file is corrupted or missing

**Solutions**:
```bash
# Verify incremental mode is enabled
semantic-signals --incremental ...

# Check cache directory permissions
ls -la .semantic-cache/

# Clear and rebuild cache
semantic-signals --incremental --clear-cache ...
```

### Unexpected Cache Misses

**Symptoms**: Files marked as changed when they haven't been modified

**Possible Causes**:
1. File timestamps changed (git operations)
2. Line ending changes (CRLF vs LF)
3. Whitespace modifications

**Solutions**:
- Cache uses content hashing (SHA256), not timestamps
- Normalize line endings before processing
- Use `--clear-cache` to reset if needed

### Cache Growing Too Large

**Symptoms**: Cache directory consuming excessive disk space

**Possible Causes**:
1. Many file versions cached over time
2. Large signal outputs

**Solutions**:
```bash
# Check cache size
du -sh .semantic-cache/

# Clear old cache entries
semantic-signals --clear-cache

# Use custom cache location
semantic-signals --cache-dir /tmp/semantic-cache
```

### State File Corruption

**Symptoms**: JSON decode errors, unexpected behavior

**Solutions**:
```bash
# Remove corrupted state file
rm .semantic-cache/change_state.json

# Run full extraction to rebuild
semantic-signals --incremental ...
```

## Best Practices

### When to Use Incremental Mode

**✅ Use Incremental When**:
- Iterating on FACT inputs
- Making focused changes
- Running frequently (daily/hourly)
- Working with large projects

**❌ Use Full Extraction When**:
- First time setup
- Major refactoring
- Suspicious cache behavior
- Validating results

### Cache Management

**Regular Workflow**:
```bash
# Normal incremental runs
semantic-signals --incremental ...

# Periodic full validation (weekly)
semantic-signals --incremental --clear-cache ...
```

**CI/CD Integration**:
```bash
# Always use full extraction in CI
semantic-signals --fact-root ... --output ...

# Or use incremental with cache persistence
semantic-signals --incremental --cache-dir $CI_CACHE_DIR ...
```

### Performance Optimization

1. **Minimize Tracked Files**: Only track necessary FACT inputs
2. **Localize Changes**: Keep modifications focused
3. **Cache Persistence**: Preserve cache across sessions
4. **Periodic Cleanup**: Clear cache when needed

## Future Enhancements

### Potential Improvements

1. **Smart Cache Invalidation**: Detect dependency changes
2. **Parallel Processing**: Process changed files concurrently
3. **Cache Compression**: Reduce disk usage
4. **Cache Sharing**: Team-level cache for CI/CD
5. **Incremental Merging**: Smarter signal deduplication

### Monitoring

Track these metrics to optimize incremental extraction:

- Cache hit rate (target: >80%)
- Average processing time (target: <5 min)
- Cache size growth (target: <100 MB)
- False cache hits (target: 0%)

## References

- Implementation: `src/semantic/change_detector.py`, `src/semantic/signal_cache.py`
- Tests: `tests/semantic/test_change_detector.py`, `tests/semantic/test_signal_cache.py`
- Task Planning: `docs/plan/task_priority_summary.md`
- Skill Documentation: `skills/semantic-signals/SKILL.md`

---

**Implementation Team**: coder-1, coder-2
**Documentation**: documenter
**Review Date**: 2026-03-17
