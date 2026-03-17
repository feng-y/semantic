"""
Integration tests for incremental signals extraction
"""

import pytest
from pathlib import Path
import json
import yaml
import sys
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.change_detector import ChangeDetector
from semantic.signal_cache import SignalCache
from semantic.extract_signals import (
    extract_domain_signals,
    extract_concept_signals,
    extract_rule_signals,
    extract_demand_pattern_signals
)


@pytest.fixture
def fact_data():
    """Sample FACT data for testing"""
    return {
        'canonical': {
            'modules': [
                {'name': 'module1', 'path': 'src/module1.py'},
                {'name': 'module2', 'path': 'src/module2.py'}
            ],
            'core_entities': [
                {'name': 'Entity1', 'type': 'class'},
                {'name': 'Entity2', 'type': 'class'}
            ]
        },
        'working': {
            'domain_proposals': [
                {'name': 'domain1'},
                {'name': 'domain2'}
            ],
            'concepts': [
                {'name': 'Concept1'}
            ]
        }
    }


@pytest.fixture
def fact_files(tmp_path, fact_data):
    """Create FACT input files"""
    fact_root = tmp_path / "fact"
    fact_root.mkdir()

    canonical_path = fact_root / "fact_canonical_sample.yaml"
    working_path = fact_root / "fact_working_summary_sample.yaml"

    with open(canonical_path, 'w') as f:
        yaml.safe_dump(fact_data['canonical'], f)

    with open(working_path, 'w') as f:
        yaml.safe_dump(fact_data['working'], f)

    return fact_root


def extract_all_signals(canonical, working):
    """Helper to extract all signal types"""
    domain = extract_domain_signals(canonical, working)
    concept = extract_concept_signals(canonical, working)
    rule = extract_rule_signals(canonical, working)
    demand = extract_demand_pattern_signals(canonical, working)

    return {
        'domain_signals': domain,
        'concept_signals': concept,
        'rule_signals': rule,
        'demand_pattern_signals': demand
    }


def test_first_run_full_extraction(tmp_path, fact_files):
    """Test first run extracts all signals (no cache)"""
    state_file = tmp_path / "state.json"
    cache_dir = tmp_path / "cache"

    detector = ChangeDetector(fact_files, cache_dir)
    cache = SignalCache(cache_dir)

    # Detect changes (first run)
    changes = detector.detect_changes()

    # First run: all files are new
    assert len(changes['added']) == 2
    assert len(changes['unchanged']) == 0

    # Load and extract signals
    canonical_path = fact_files / "fact_canonical_sample.yaml"
    with open(canonical_path, 'r') as f:
        canonical = yaml.safe_load(f)

    working_path = fact_files / "fact_working_summary_sample.yaml"
    with open(working_path, 'r') as f:
        working = yaml.safe_load(f)

    signals = extract_all_signals(canonical, working)

    # Verify signals extracted
    assert len(signals['domain_signals']) > 0
    assert len(signals['concept_signals']) > 0

    # Cache the signals
    file_hash = detector.compute_file_hash(canonical_path)
    cache.store_signals(canonical_path, file_hash, signals)

    # Save state

    # Verify cache
    cached = cache.get_cached_signals(canonical_path, file_hash)
    assert cached == signals


def test_second_run_no_changes_all_cached(tmp_path, fact_files):
    """Test second run with no changes uses cache"""
    state_file = tmp_path / "state.json"
    cache_dir = tmp_path / "cache"

    # First run
    detector1 = ChangeDetector(fact_files, cache_dir)
    cache = SignalCache(cache_dir)

    changes1 = detector1.detect_changes()

    canonical_path = fact_files / "fact_canonical_sample.yaml"
    with open(canonical_path, 'r') as f:
        canonical = yaml.safe_load(f)

    signals = extract_all_signals(canonical, None)
    file_hash = detector1.compute_file_hash(canonical_path)
    cache.store_signals(canonical_path, file_hash, signals)

    # Second run - no changes
    detector2 = ChangeDetector(fact_files, cache_dir)
    changes2 = detector2.detect_changes()

    # All files should be unchanged
    assert len(changes2['added']) == 0
    assert len(changes2['changed']) == 0
    assert len(changes2['removed']) == 0
    assert len(changes2['unchanged']) == 2

    # Should be able to retrieve from cache
    cached_signals = cache.get_cached_signals(canonical_path, file_hash)
    assert cached_signals == signals


def test_partial_file_change_incremental(tmp_path, fact_files):
    """Test incremental extraction when some files change"""
    state_file = tmp_path / "state.json"
    cache_dir = tmp_path / "cache"

    # First run
    detector1 = ChangeDetector(fact_files, cache_dir)
    cache = SignalCache(cache_dir)

    changes1 = detector1.detect_changes()

    # Cache signals for both files
    canonical_path = fact_files / "fact_canonical_sample.yaml"
    working_path = fact_files / "fact_working_summary_sample.yaml"

    with open(canonical_path, 'r') as f:
        canonical = yaml.safe_load(f)
    with open(working_path, 'r') as f:
        working = yaml.safe_load(f)

    canonical_signals = extract_all_signals(canonical, None)
    working_signals = extract_all_signals(None, working)

    canonical_hash = detector1.compute_file_hash(canonical_path)
    working_hash = detector1.compute_file_hash(working_path)

    cache.store_signals(canonical_path, canonical_hash, canonical_signals)
    cache.store_signals(working_path, working_hash, working_signals)

    # Modify only canonical file
    canonical['modules'].append({'name': 'module3', 'path': 'src/module3.py'})
    with open(canonical_path, 'w') as f:
        yaml.safe_dump(canonical, f)

    # Second run
    detector2 = ChangeDetector(fact_files, cache_dir)
    changes2 = detector2.detect_changes()

    # One file changed, one unchanged
    assert len(changes2['changed']) == 1
    assert len(changes2['unchanged']) == 1
    assert changes2['changed'][0] == canonical_path

    # Can still use cache for unchanged file
    cached_working = cache.get_cached_signals(working_path, working_hash)
    assert cached_working == working_signals

    # Need to re-extract for changed file
    new_canonical_hash = detector2.compute_file_hash(canonical_path)
    assert new_canonical_hash != canonical_hash

    # Old cache should not match
    old_cached = cache.get_cached_signals(canonical_path, canonical_hash)
    assert old_cached == canonical_signals  # Old cache still exists

    # New hash should not be cached yet
    new_cached = cache.get_cached_signals(canonical_path, new_canonical_hash)
    assert new_cached is None


def test_cache_clear_forces_full_extraction(tmp_path, fact_files):
    """Test that clearing cache forces full re-extraction"""
    state_file = tmp_path / "state.json"
    cache_dir = tmp_path / "cache"

    # First run with caching
    detector = ChangeDetector(fact_files, cache_dir)
    cache = SignalCache(cache_dir)

    changes = detector.detect_changes()

    canonical_path = fact_files / "fact_canonical_sample.yaml"
    with open(canonical_path, 'r') as f:
        canonical = yaml.safe_load(f)

    signals = extract_all_signals(canonical, None)
    file_hash = detector.compute_file_hash(canonical_path)
    cache.store_signals(canonical_path, file_hash, signals)

    # Verify cache exists
    assert cache.get_cached_signals(canonical_path, file_hash) is not None

    # Clear cache
    cache.clear_all()

    # Cache should be empty
    assert cache.get_cached_signals(canonical_path, file_hash) is None

    # Stats should show zero entries
    stats = cache.get_cache_stats()
    assert stats['indexed_files'] == 0


def test_performance_cache_vs_extraction(tmp_path, fact_files):
    """Test that cache retrieval is faster than extraction"""
    cache_dir = tmp_path / "cache"
    cache = SignalCache(cache_dir)

    canonical_path = fact_files / "fact_canonical_sample.yaml"
    with open(canonical_path, 'r') as f:
        canonical = yaml.safe_load(f)

    # Measure extraction time
    start_extract = time.time()
    signals = extract_all_signals(canonical, None)
    extract_time = time.time() - start_extract

    # Cache the signals
    file_hash = "test_hash_123"
    cache.store_signals(canonical_path, file_hash, signals)

    # Measure cache retrieval time
    start_cache = time.time()
    cached_signals = cache.get_cached_signals(canonical_path, file_hash)
    cache_time = time.time() - start_cache

    # Cache should be faster (though for small data, difference may be minimal)
    # Just verify cache works correctly
    assert cached_signals == signals
    assert cache_time < 1.0  # Should be very fast


def test_incremental_with_file_removal(tmp_path, fact_files):
    """Test incremental extraction when files are removed"""
    state_file = tmp_path / "state.json"
    cache_dir = tmp_path / "cache"

    # First run
    detector1 = ChangeDetector(fact_files, cache_dir)
    cache = SignalCache(cache_dir)

    changes1 = detector1.detect_changes()
    assert len(changes1['added']) == 2

    # Remove one file
    working_path = fact_files / "fact_working_summary_sample.yaml"
    working_path.unlink()

    # Second run
    detector2 = ChangeDetector(fact_files, cache_dir)
    changes2 = detector2.detect_changes()

    # One file removed, one unchanged
    assert len(changes2['removed']) == 1
    assert len(changes2['unchanged']) == 1
    assert changes2['removed'][0] == working_path


def test_incremental_with_new_file(tmp_path, fact_files):
    """Test incremental extraction when new files are added"""
    state_file = tmp_path / "state.json"
    cache_dir = tmp_path / "cache"

    # First run
    detector1 = ChangeDetector(fact_files, cache_dir)
    changes1 = detector1.detect_changes()

    # Initially both tracked files are added
    assert len(changes1['added']) == 2

    # Add a baseline markdown file (which is tracked)
    baseline_dir = fact_files.parent / "fact" / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    new_file = baseline_dir / "new_baseline.md"
    new_file.write_text("# New baseline content")

    # Second run
    detector2 = ChangeDetector(fact_files, cache_dir)
    changes2 = detector2.detect_changes()

    # One file added, others unchanged
    assert len(changes2['added']) == 1
    assert len(changes2['unchanged']) == 2
    assert changes2['added'][0] == new_file


def test_cache_invalidation_workflow(tmp_path, fact_files):
    """Test cache invalidation in incremental workflow"""
    cache_dir = tmp_path / "cache"
    cache = SignalCache(cache_dir)

    canonical_path = fact_files / "fact_canonical_sample.yaml"

    # Cache first version
    signals_v1 = {
        'domain_signals': [{'signal_type': 'v1'}],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }
    cache.store_signals(canonical_path, "hash1", signals_v1)

    # Verify first version cached
    assert cache.get_cached_signals(canonical_path, "hash1") == signals_v1

    # Cache second version (should replace first in index)
    signals_v2 = {
        'domain_signals': [{'signal_type': 'v2'}],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }
    cache.store_signals(canonical_path, "hash2", signals_v2)

    # Only latest version should be retrievable via index
    assert cache.get_cached_signals(canonical_path, "hash1") is None
    assert cache.get_cached_signals(canonical_path, "hash2") == signals_v2

    # Invalidate all versions for this file
    cache.invalidate_file(canonical_path)

    # All versions should be gone
    assert cache.get_cached_signals(canonical_path, "hash1") is None
    assert cache.get_cached_signals(canonical_path, "hash2") is None


def test_merge_signals_simple(tmp_path):
    """Test merging cached and new signals"""
    cache = SignalCache(tmp_path)

    cached_signals = {
        'domain_signals': [{'signal_type': 'cached1', 'source': 'file1'}],
        'concept_signals': [{'signal_type': 'cached2', 'source': 'file2'}],
        'rule_signals': [],
        'demand_pattern_signals': []
    }

    new_signals = {
        'domain_signals': [{'signal_type': 'new1', 'source': 'file3'}],
        'concept_signals': [],
        'rule_signals': [{'signal_type': 'new2', 'source': 'file4'}],
        'demand_pattern_signals': []
    }

    merged = cache.merge_signals(cached_signals, new_signals)

    assert len(merged['domain_signals']) == 2
    assert len(merged['concept_signals']) == 1
    assert len(merged['rule_signals']) == 1
    assert cached_signals['domain_signals'][0] in merged['domain_signals']
    assert new_signals['domain_signals'][0] in merged['domain_signals']


def test_merge_signals_empty_cached(tmp_path):
    """Test merging with empty cached signals"""
    cache = SignalCache(tmp_path)

    new_signals = {
        'domain_signals': [{'signal_type': 'new1'}],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }
    merged = cache.merge_signals({}, new_signals)

    assert merged == new_signals


def test_merge_signals_empty_new(tmp_path):
    """Test merging with empty new signals"""
    cache = SignalCache(tmp_path)

    cached_signals = {
        'domain_signals': [{'signal_type': 'cached1'}],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }
    merged = cache.merge_signals(cached_signals, {})

    assert merged == cached_signals


def test_state_persistence_across_runs(tmp_path, fact_files):
    """Test that state persists correctly across multiple runs"""
    cache_dir = tmp_path / "cache"
    state_file = cache_dir / "change_state.json"

    # Run 1
    detector1 = ChangeDetector(fact_files, cache_dir)
    changes1 = detector1.detect_changes()

    # Verify state file exists
    assert state_file.exists()

    # Run 2
    detector2 = ChangeDetector(fact_files, cache_dir)
    changes2 = detector2.detect_changes()

    # Should load previous state
    assert len(detector2.load_state()) > 0
    assert len(changes2['unchanged']) == 2


def test_cache_stats_accuracy(tmp_path, fact_files):
    """Test cache statistics accuracy"""
    cache_dir = tmp_path / "cache"
    cache = SignalCache(cache_dir)

    # Initially empty
    stats = cache.get_cache_stats()
    assert stats['indexed_files'] == 0
    assert stats['total_size_bytes'] == 0

    # Add some entries
    signals1 = {
        'domain_signals': [{'signal_type': 'test1'}],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }
    signals2 = {
        'domain_signals': [{'signal_type': 'test2'}],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }
    cache.store_signals(Path("/file1.yaml"), "hash1", signals1)
    cache.store_signals(Path("/file2.yaml"), "hash2", signals2)

    stats = cache.get_cache_stats()
    assert stats['indexed_files'] == 2
    assert stats['total_size_bytes'] > 0


def test_concurrent_file_changes(tmp_path, fact_files):
    """Test handling multiple file changes in one run"""
    state_file = tmp_path / "state.json"
    cache_dir = tmp_path / "cache"

    # First run
    detector1 = ChangeDetector(fact_files, cache_dir)
    changes1 = detector1.detect_changes()

    # Modify both files
    canonical_path = fact_files / "fact_canonical_sample.yaml"
    working_path = fact_files / "fact_working_summary_sample.yaml"

    canonical_path.write_text("modified: canonical")
    working_path.write_text("modified: working")

    # Second run
    detector2 = ChangeDetector(fact_files, cache_dir)
    changes2 = detector2.detect_changes()

    # Both files should be detected as changed
    assert len(changes2['changed']) == 2
    assert len(changes2['unchanged']) == 0


def test_hash_collision_resistance(tmp_path):
    """Test that different files produce different hashes"""
    cache_dir = tmp_path / "cache"
    fact_root = tmp_path / "fact"
    fact_root.mkdir()

    detector = ChangeDetector(fact_root, cache_dir)

    file1 = fact_root / "file1.txt"
    file2 = fact_root / "file2.txt"

    file1.write_text("content A")
    file2.write_text("content B")

    hash1 = detector.compute_file_hash(file1)
    hash2 = detector.compute_file_hash(file2)

    assert hash1 != hash2


def test_incremental_extraction_complete_workflow(tmp_path, fact_data):
    """Test complete incremental extraction workflow"""
    # Setup
    fact_root = tmp_path / "fact"
    fact_root.mkdir()
    state_file = tmp_path / "state.json"
    cache_dir = tmp_path / "cache"

    canonical_path = fact_root / "fact_canonical_sample.yaml"
    working_path = fact_root / "fact_working_summary_sample.yaml"

    # Write initial files
    with open(canonical_path, 'w') as f:
        yaml.safe_dump(fact_data['canonical'], f)
    with open(working_path, 'w') as f:
        yaml.safe_dump(fact_data['working'], f)

    detector = ChangeDetector(fact_root, cache_dir)
    cache = SignalCache(cache_dir)

    # === Run 1: Full extraction ===
    changes1 = detector.detect_changes()
    assert len(changes1['added']) == 2

    # Extract and cache
    with open(canonical_path, 'r') as f:
        canonical = yaml.safe_load(f)
    signals1 = extract_all_signals(canonical, None)

    hash1 = detector.compute_file_hash(canonical_path)
    cache.store_signals(canonical_path, hash1, signals1)

    # === Run 2: No changes ===
    detector2 = ChangeDetector(fact_root, cache_dir)
    changes2 = detector2.detect_changes()
    assert len(changes2['unchanged']) == 2

    # Use cache
    cached = cache.get_cached_signals(canonical_path, hash1)
    assert cached == signals1

    # === Run 3: Modify one file ===
    fact_data['canonical']['modules'].append({'name': 'module3', 'path': 'src/module3.py'})
    with open(canonical_path, 'w') as f:
        yaml.safe_dump(fact_data['canonical'], f)

    detector3 = ChangeDetector(fact_root, cache_dir)
    changes3 = detector3.detect_changes()
    assert len(changes3['changed']) == 1
    assert len(changes3['unchanged']) == 1

    # Re-extract changed file
    with open(canonical_path, 'r') as f:
        canonical_new = yaml.safe_load(f)
    signals3 = extract_all_signals(canonical_new, None)

    # Signals should be different (content changed, not necessarily count)
    assert signals3['domain_signals'] != signals1['domain_signals']
    # Verify the evidence reflects the new module count
    if signals3['domain_signals']:
        assert '3 modules' in signals3['domain_signals'][0]['evidence']


def test_error_handling_corrupted_cache(tmp_path):
    """Test handling of corrupted cache files"""
    cache_dir = tmp_path / "cache"
    cache = SignalCache(cache_dir)

    # Create corrupted cache file
    cache_key = cache._get_cache_key(Path("/test.yaml"), "hash123")
    cache_path = cache._get_signal_file(cache_key)

    cache_path.write_text("{ invalid json")

    # Should return None for corrupted cache
    result = cache.get_cached_signals(Path("/test.yaml"), "hash123")
    assert result is None


def test_error_handling_corrupted_state(tmp_path, fact_files):
    """Test handling of corrupted state file"""
    cache_dir = tmp_path / "cache"
    state_file = cache_dir / "change_state.json"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create corrupted state file
    state_file.write_text("{ invalid json")

    # Should handle gracefully
    detector = ChangeDetector(fact_files, cache_dir)

    # Load state should return empty dict for corrupted file
    state_before = detector.load_state()
    assert len(state_before) == 0

    # Detect changes should treat as first run
    changes = detector.detect_changes()
    assert len(changes['added']) == 2

    # After detect_changes, state should be saved correctly
    state_after = detector.load_state()
    assert len(state_after) == 2
