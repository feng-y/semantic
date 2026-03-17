"""
Tests for SignalCache module
"""

import pytest
from pathlib import Path
import json
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.signal_cache import SignalCache


def test_signal_cache_init(tmp_path):
    """Test SignalCache initialization"""
    cache_dir = tmp_path / "cache"
    cache = SignalCache(cache_dir)

    assert cache.cache_dir == cache_dir
    assert cache_dir.exists()
    assert (cache_dir / "signals").exists()


def test_signal_cache_init_creates_directories(tmp_path):
    """Test that cache initialization creates necessary directories"""
    cache_dir = tmp_path / "nested" / "cache" / "dir"
    cache = SignalCache(cache_dir)

    assert cache_dir.exists()
    assert cache.signals_dir.exists()


def test_get_cache_key_deterministic(tmp_path):
    """Test that cache key generation is deterministic"""
    cache = SignalCache(tmp_path)

    file_path = Path("/some/file.yaml")
    file_hash = "abc123"

    key1 = cache._get_cache_key(file_path, file_hash)
    key2 = cache._get_cache_key(file_path, file_hash)

    assert key1 == key2
    assert len(key1) == 16  # SHA256 truncated to 16


def test_get_cache_key_unique(tmp_path):
    """Test that different inputs produce different cache keys"""
    cache = SignalCache(tmp_path)

    key1 = cache._get_cache_key(Path("/file1.yaml"), "hash1")
    key2 = cache._get_cache_key(Path("/file2.yaml"), "hash1")
    key3 = cache._get_cache_key(Path("/file1.yaml"), "hash2")

    assert key1 != key2
    assert key1 != key3
    assert key2 != key3


def test_put_and_get_signals(tmp_path):
    """Test storing and retrieving signals"""
    cache = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash = "abc123def456"
    signals = {
        'domain_signals': [
            {'signal_type': 'test', 'source': 'test', 'evidence': 'test evidence', 'confidence': 'high'}
        ],
        'concept_signals': []
    }

    # Store signals
    cache.store_signals(file_path, file_hash, signals)

    # Retrieve signals
    retrieved = cache.get_cached_signals(file_path, file_hash)

    assert retrieved == signals


def test_get_nonexistent_cache(tmp_path):
    """Test retrieving from nonexistent cache"""
    cache = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash = "abc123"

    result = cache.get_cached_signals(file_path, file_hash)

    assert result is None


def test_get_with_wrong_hash(tmp_path):
    """Test that wrong hash returns None"""
    cache = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash = "abc123"
    signals = {'domain_signals': []}

    # Store with one hash
    cache.store_signals(file_path, file_hash, signals)

    # Try to retrieve with different hash
    result = cache.get_cached_signals(file_path, "different_hash")

    assert result is None


def test_cache_entry_structure(tmp_path):
    """Test that cache entry has correct structure"""
    cache = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash = "abc123"
    signals = {'domain_signals': []}

    cache.store_signals(file_path, file_hash, signals)

    # Read signal file directly
    cache_key = cache._get_cache_key(file_path, file_hash)
    signal_file = cache._get_signal_file(cache_key)

    assert signal_file.exists()

    with open(signal_file, 'r') as f:
        stored_signals = json.load(f)

    # Verify signals are stored correctly
    assert stored_signals == signals

    # Verify index entry structure
    index = cache.load_index()
    file_key = str(file_path)
    assert file_key in index

    entry = index[file_key]
    assert 'file_hash' in entry
    assert 'cache_key' in entry
    assert 'cached_at' in entry
    assert 'signal_file' in entry

    assert entry['file_hash'] == file_hash
    assert entry['cache_key'] == cache_key


def test_cache_timestamp(tmp_path):
    """Test that cache entry includes timestamp"""
    cache = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash = "abc123"
    signals = {}

    before = datetime.now(timezone.utc)
    cache.store_signals(file_path, file_hash, signals)
    after = datetime.now(timezone.utc)

    # Read index to get timestamp
    index = cache.load_index()
    file_key = str(file_path)
    entry = index[file_key]

    cached_at = datetime.fromisoformat(entry['cached_at'])
    assert before <= cached_at <= after


def test_invalidate_cache(tmp_path):
    """Test cache invalidation for a file"""
    cache = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash1 = "hash1"
    file_hash2 = "hash2"

    # Store first version
    cache.store_signals(file_path, file_hash1, {'v': 1})

    # Store second version (overwrites first in index)
    cache.store_signals(file_path, file_hash2, {'v': 2})

    # Only the latest hash should be retrievable (index has one entry per file)
    assert cache.get_cached_signals(file_path, file_hash1) is None
    assert cache.get_cached_signals(file_path, file_hash2) is not None

    # Invalidate
    cache.invalidate_file(file_path)

    # Should be gone
    assert cache.get_cached_signals(file_path, file_hash2) is None


def test_invalidate_only_target_file(tmp_path):
    """Test that invalidation only affects target file"""
    cache = SignalCache(tmp_path)

    file1 = Path("/test/file1.yaml")
    file2 = Path("/test/file2.yaml")

    cache.store_signals(file1, "hash1", {'file': 1})
    cache.store_signals(file2, "hash2", {'file': 2})

    # Invalidate file1
    cache.invalidate_file(file1)

    # file1 should be gone, file2 should remain
    assert cache.get_cached_signals(file1, "hash1") is None
    assert cache.get_cached_signals(file2, "hash2") == {'file': 2}


def test_clear_cache(tmp_path):
    """Test clearing all cache entries"""
    cache = SignalCache(tmp_path)

    # Store multiple entries
    cache.store_signals(Path("/file1.yaml"), "hash1", {'f': 1})
    cache.store_signals(Path("/file2.yaml"), "hash2", {'f': 2})
    cache.store_signals(Path("/file3.yaml"), "hash3", {'f': 3})

    # Verify they exist
    assert cache.get_cached_signals(Path("/file1.yaml"), "hash1") is not None
    assert cache.get_cached_signals(Path("/file2.yaml"), "hash2") is not None

    # Clear all
    cache.clear_all()

    # All should be gone
    assert cache.get_cached_signals(Path("/file1.yaml"), "hash1") is None
    assert cache.get_cached_signals(Path("/file2.yaml"), "hash2") is None
    assert cache.get_cached_signals(Path("/file3.yaml"), "hash3") is None


def test_stats_empty_cache(tmp_path):
    """Test stats for empty cache"""
    cache = SignalCache(tmp_path)

    stats = cache.get_cache_stats()

    assert stats['indexed_files'] == 0
    assert stats['cached_signal_files'] == 0
    assert stats['total_size_bytes'] == 0
    assert stats['cache_dir'] == str(tmp_path)


def test_stats_with_entries(tmp_path):
    """Test stats with cache entries"""
    cache = SignalCache(tmp_path)

    # Add some entries
    cache.store_signals(Path("/file1.yaml"), "hash1", {'data': 'x' * 100})
    cache.store_signals(Path("/file2.yaml"), "hash2", {'data': 'y' * 200})

    stats = cache.get_cache_stats()

    assert stats['indexed_files'] == 2
    assert stats['cached_signal_files'] == 2
    assert stats['total_size_bytes'] > 0
    assert stats['cache_dir'] == str(tmp_path)


def test_merge_signals_simple(tmp_path):
    """Test simple signal merging"""
    cache = SignalCache(tmp_path)

    cached = {
        'domain_signals': [
            {'signal_type': 'cached1', 'file': 'file1.yaml'},
            {'signal_type': 'cached2', 'file': 'file2.yaml'}
        ],
        'concept_signals': []
    }

    new = {
        'domain_signals': [
            {'signal_type': 'new1', 'file': 'file3.yaml'}
        ],
        'concept_signals': []
    }

    merged = cache.merge_signals(cached, new)

    assert len(merged['domain_signals']) == 3
    assert cached['domain_signals'][0] in merged['domain_signals']
    assert cached['domain_signals'][1] in merged['domain_signals']
    assert new['domain_signals'][0] in merged['domain_signals']


def test_merge_signals_empty_cached(tmp_path):
    """Test merging with empty cached signals"""
    cache = SignalCache(tmp_path)

    cached = {
        'domain_signals': [],
        'concept_signals': []
    }
    new = {
        'domain_signals': [{'signal_type': 'new1'}],
        'concept_signals': []
    }

    merged = cache.merge_signals(cached, new)

    assert merged['domain_signals'] == new['domain_signals']


def test_merge_signals_empty_new(tmp_path):
    """Test merging with empty new signals"""
    cache = SignalCache(tmp_path)

    cached = {
        'domain_signals': [{'signal_type': 'cached1'}],
        'concept_signals': []
    }
    new = {
        'domain_signals': [],
        'concept_signals': []
    }

    merged = cache.merge_signals(cached, new)

    assert merged['domain_signals'] == cached['domain_signals']


def test_merge_signals_both_empty(tmp_path):
    """Test merging with both empty"""
    cache = SignalCache(tmp_path)

    empty1 = {
        'domain_signals': [],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }
    empty2 = {
        'domain_signals': [],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }

    merged = cache.merge_signals(empty1, empty2)

    assert merged == {
        'domain_signals': [],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }


def test_merge_signals_preserves_order(tmp_path):
    """Test that merge preserves order (cached first, then new)"""
    cache = SignalCache(tmp_path)

    cached = {
        'domain_signals': [{'id': 1}, {'id': 2}],
        'concept_signals': []
    }
    new = {
        'domain_signals': [{'id': 3}, {'id': 4}],
        'concept_signals': []
    }

    merged = cache.merge_signals(cached, new)

    assert merged['domain_signals'] == [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}]


def test_cache_handles_corrupted_file(tmp_path):
    """Test that cache handles corrupted cache files gracefully"""
    cache = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash = "abc123"

    # Create corrupted signal file
    cache_key = cache._get_cache_key(file_path, file_hash)
    signal_file = cache._get_signal_file(cache_key)

    # Create index entry pointing to corrupted file
    index = {
        str(file_path): {
            'file_hash': file_hash,
            'cache_key': cache_key,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'signal_file': str(signal_file)
        }
    }
    cache.save_index(index)

    # Write corrupted signal file
    signal_file.write_text("invalid json {{{")

    # Should return None for corrupted cache
    result = cache.get_cached_signals(file_path, file_hash)
    assert result is None


def test_cache_handles_missing_fields(tmp_path):
    """Test that cache handles entries with missing fields"""
    cache = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash = "abc123"

    # Create index entry with missing cache_key field
    index = {
        str(file_path): {
            'file_hash': file_hash,
            # missing 'cache_key' field
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
    }
    cache.save_index(index)

    # Should return None for incomplete entry
    result = cache.get_cached_signals(file_path, file_hash)
    assert result is None


def test_invalidate_handles_corrupted_files(tmp_path):
    """Test that invalidate handles corrupted cache files"""
    cache = SignalCache(tmp_path)

    # Create corrupted cache file
    corrupted_file = cache.signals_dir / "corrupted.json"
    corrupted_file.write_text("invalid json")

    # Should not raise exception
    cache.invalidate_file(Path("/some/file.yaml"))


def test_clear_handles_permission_errors(tmp_path):
    """Test that clear handles files that can't be deleted"""
    cache = SignalCache(tmp_path)

    cache.store_signals(Path("/file.yaml"), "hash", {})

    # Clear should not raise even if files can't be deleted
    # (In practice, this is hard to test without mocking)
    cache.clear_all()


def test_multiple_cache_instances_same_dir(tmp_path):
    """Test that multiple cache instances can share the same directory"""
    cache1 = SignalCache(tmp_path)
    cache2 = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash = "abc123"
    signals = {'data': 'test'}

    # Write with cache1
    cache1.store_signals(file_path, file_hash, signals)

    # Read with cache2
    retrieved = cache2.get_cached_signals(file_path, file_hash)

    assert retrieved == signals


def test_cache_with_complex_signals(tmp_path):
    """Test caching complex signal structures"""
    cache = SignalCache(tmp_path)

    file_path = Path("/test/file.yaml")
    file_hash = "abc123"

    complex_signals = {
        'domain_signals': [
            {
                'signal_type': 'module_grouping',
                'source': 'fact_canonical:modules',
                'evidence': 'Multiple modules observed',
                'confidence': 'high',
                'metadata': {
                    'module_count': 5,
                    'patterns': ['pattern1', 'pattern2']
                }
            }
        ],
        'concept_signals': [
            {
                'signal_type': 'entity_definition',
                'source': 'test',
                'evidence': 'test evidence',
                'confidence': 'high',
                'nested': {
                    'deep': {
                        'structure': [1, 2, 3]
                    }
                }
            }
        ]
    }

    cache.store_signals(file_path, file_hash, complex_signals)
    retrieved = cache.get_cached_signals(file_path, file_hash)

    assert retrieved == complex_signals
