# Incremental Signal Extraction

This document describes the incremental extraction feature for the semantic signals layer.

## Overview

The incremental extraction feature allows the semantic signals extraction process to only re-process files that have changed since the last run, significantly reducing processing time and cost for large codebases.

## Architecture

The implementation consists of three main components:

### 1. Change Detector (`src/semantic/change_detector.py`)

Detects which FACT input files have changed since the last extraction run.

**Features:**
- Tracks FACT canonical and working summary YAML files
- Tracks baseline markdown files in `docs/fact/baseline/`
- Uses SHA256 file hashing for change detection
- Maintains state in `.semantic-cache/change_state.json`
- Detects added, changed, and removed files

**Usage:**
```python
from src.semantic.change_detector import ChangeDetector

detector = ChangeDetector(fact_root, cache_dir)
changed, added, removed = detector.detect_changes()
```

### 2. Signal Cache (`src/semantic/signal_cache.py`)

Manages caching of extracted signals at the file level.

**Features:**
- Stores signals per file with hash-based cache keys
- Automatic cache invalidation on file changes
- Signal merging for combining cached and fresh results
- Cache statistics and management

**Usage:**
```python
from src.semantic.signal_cache import SignalCache

cache = SignalCache(cache_dir)

# Store signals
cache.store_signals(file_path, file_hash, signals)

# Retrieve signals
signals = cache.get_cached_signals(file_path, file_hash)

# Merge multiple signal sets
merged = cache.merge_signals(signals1, signals2, signals3)
```

### 3. Enhanced Extract Signals (`src/semantic/extract_signals.py`)

The main extraction script now supports both full and incremental modes.

**New Features:**
- `--incremental` flag to enable incremental extraction
- `--cache-dir` to specify cache location (default: `.semantic-cache`)
- `--clear-cache` to clear cache before extraction
- Automatic fallback to full extraction if cache is invalid

## Usage

### Full Extraction (Default)

```bash
python -m src.semantic.extract_signals \
  --fact-root docs/semantic-foundation/fact \
  --output docs/semantic-foundation/semantic/signals.yaml
```

This is the default mode and works exactly as before.

### Incremental Extraction

```bash
python -m src.semantic.extract_signals \
  --fact-root docs/semantic-foundation/fact \
  --output docs/semantic-foundation/semantic/signals.yaml \
  --incremental
```

**First run:** All files are treated as new, signals are extracted and cached.

**Subsequent runs:** Only changed files are re-processed, unchanged files use cached signals.

### Clear Cache

```bash
python -m src.semantic.extract_signals --clear-cache
```

Or combine with extraction:

```bash
python -m src.semantic.extract_signals \
  --incremental \
  --clear-cache
```

### Custom Cache Directory

```bash
python -m src.semantic.extract_signals \
  --incremental \
  --cache-dir /path/to/custom/cache
```

## Cache Structure

The cache is stored in `.semantic-cache/` (or custom location) with the following structure:

```
.semantic-cache/
├── change_state.json          # Change detection state
├── cache_index.json           # Cache index mapping files to signals
└── signals/                   # Cached signal files
    ├── abc123def456.json
    ├── 789ghi012jkl.json
    └── ...
```

### change_state.json

```json
{
  "timestamp": "2026-03-17T10:30:00Z",
  "file_hashes": {
    "/path/to/fact_canonical_sample.yaml": "abc123...",
    "/path/to/fact_working_summary_sample.yaml": "def456..."
  }
}
```

### cache_index.json

```json
{
  "/path/to/fact_canonical_sample.yaml": {
    "file_hash": "abc123...",
    "cache_key": "abc123def456",
    "cached_at": "2026-03-17T10:30:00Z",
    "signal_file": ".semantic-cache/signals/abc123def456.json"
  }
}
```

## Behavior

### Change Detection

The system detects three types of changes:

1. **Added files**: New FACT files that didn't exist in the previous run
2. **Changed files**: Existing files whose content hash has changed
3. **Removed files**: Files that existed before but are now missing

### Cache Invalidation

Cache is automatically invalidated when:
- File content changes (detected via hash)
- File is removed
- User runs with `--clear-cache`

### Fallback to Full Extraction

The system automatically falls back to full extraction if:
- Cache is corrupted or unreadable
- Required FACT files are missing
- Cache directory cannot be created

## Performance

### Expected Improvements

For a typical project with 100+ FACT entries:

- **First run (full)**: ~30 seconds
- **Subsequent run (no changes)**: ~2 seconds (93% faster)
- **Subsequent run (10% changed)**: ~5 seconds (83% faster)

### Cache Size

Cache size is proportional to the number of tracked files:
- ~1-5 KB per cached file
- Typical project: 10-50 KB total cache size

## Testing

Run the test suite:

```bash
# Test change detection
pytest tests/test_change_detector.py -v

# Test signal cache
pytest tests/test_signal_cache.py -v

# Test incremental extraction integration
pytest tests/test_incremental_extraction.py -v

# Run all tests
pytest tests/test_*.py -v
```

## Design Principles

1. **Safe by default**: Full extraction is the default mode
2. **Opt-in incremental**: Users must explicitly enable `--incremental`
3. **Automatic fallback**: Invalid cache triggers full extraction
4. **Output compatibility**: Incremental mode produces identical output format
5. **Transparent caching**: Cache is managed automatically, no manual intervention needed

## Limitations

1. **File-level granularity**: Changes are tracked at file level, not line level
2. **No cross-file dependencies**: Each file is cached independently
3. **Local cache only**: Cache is not shared across machines
4. **Git-independent**: Uses file hashing, not git history

## Future Enhancements

Potential improvements for future versions:

1. **Distributed cache**: Share cache across team members
2. **Finer granularity**: Track changes at entity/module level
3. **Git integration**: Use git diff for change detection
4. **Cache compression**: Reduce cache size for large projects
5. **Cache expiration**: Auto-expire old cache entries

## Troubleshooting

### Cache not working

```bash
# Clear cache and try again
python -m src.semantic.extract_signals --clear-cache --incremental
```

### Unexpected results

```bash
# Force full extraction
python -m src.semantic.extract_signals
```

### Cache directory issues

```bash
# Use custom cache directory
python -m src.semantic.extract_signals --incremental --cache-dir /tmp/semantic-cache
```

## Integration with Semantic Layer

The incremental extraction integrates seamlessly with the semantic layer pipeline:

1. **FACT Layer** → produces canonical and working summary YAML
2. **Signal Extraction** (this feature) → extracts signals incrementally
3. **Candidate Synthesis** → uses signals to build candidates
4. **Scoring & Recommendation** → ranks candidates

The incremental mode only affects step 2, making it faster while maintaining compatibility with downstream stages.
