"""
Tests for signal cache module
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.semantic.signal_cache import SignalCache


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory for testing"""
    temp_dir = tempfile.mkdtemp()
    cache_dir = Path(temp_dir) / "cache"

    yield cache_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_signals():
    """Sample signals data for testing"""
    return {
        'domain_signals': [
            {
                'signal_type': 'module_grouping',
                'source': 'fact_canonical:modules',
                'evidence': '5 modules observed',
                'confidence': 'high',
                'summary': 'Repository contains 5 distinct modules'
            }
        ],
        'concept_signals': [
            {
                'signal_type': 'entity_definition',
                'source': 'fact_canonical:core_entities',
                'evidence': '3 entities observed',
                'confidence': 'high',
                'summary': 'Repository defines 3 core entities'
            }
        ],
        'rule_signals': [],
        'demand_pattern_signals': []
    }


def test_store_and_retrieve_signals(temp_cache_dir, sample_signals):
    """Test storing and retrieving signals from cache"""
    cache = SignalCache(temp_cache_dir)

    file_path = Path("/test/fact_canonical_sample.yaml")
    file_hash = "abc123"

    # Store signals
    cache.store_signals(file_path, file_hash, sample_signals)

    # Retrieve signals
    retrieved = cache.get_cached_signals(file_path, file_hash)

    assert retrieved is not None
    assert retrieved['domain_signals'] == sample_signals['domain_signals']
    assert retrieved['concept_signals'] == sample_signals['concept_signals']


def test_cache_miss_wrong_hash(temp_cache_dir, sample_signals):
    """Test that wrong hash results in cache miss"""
    cache = SignalCache(temp_cache_dir)

    file_path = Path("/test/fact_canonical_sample.yaml")
    file_hash = "abc123"

    # Store signals
    cache.store_signals(file_path, file_hash, sample_signals)

    # Try to retrieve with different hash
    retrieved = cache.get_cached_signals(file_path, "different_hash")

    assert retrieved is None


def test_cache_miss_nonexistent_file(temp_cache_dir):
    """Test that nonexistent file results in cache miss"""
    cache = SignalCache(temp_cache_dir)

    file_path = Path("/test/nonexistent.yaml")
    file_hash = "abc123"

    retrieved = cache.get_cached_signals(file_path, file_hash)

    assert retrieved is None


def test_invalidate_file(temp_cache_dir, sample_signals):
    """Test invalidating cached signals for a file"""
    cache = SignalCache(temp_cache_dir)

    file_path = Path("/test/fact_canonical_sample.yaml")
    file_hash = "abc123"

    # Store signals
    cache.store_signals(file_path, file_hash, sample_signals)

    # Verify it's cached
    assert cache.get_cached_signals(file_path, file_hash) is not None

    # Invalidate
    cache.invalidate_file(file_path)

    # Verify it's gone
    assert cache.get_cached_signals(file_path, file_hash) is None


def test_clear_all(temp_cache_dir, sample_signals):
    """Test clearing entire cache"""
    cache = SignalCache(temp_cache_dir)

    # Store multiple files
    file1 = Path("/test/file1.yaml")
    file2 = Path("/test/file2.yaml")

    cache.store_signals(file1, "hash1", sample_signals)
    cache.store_signals(file2, "hash2", sample_signals)

    # Verify both are cached
    assert cache.get_cached_signals(file1, "hash1") is not None
    assert cache.get_cached_signals(file2, "hash2") is not None

    # Clear all
    cache.clear_all()

    # Verify both are gone
    assert cache.get_cached_signals(file1, "hash1") is None
    assert cache.get_cached_signals(file2, "hash2") is None


def test_merge_signals(temp_cache_dir):
    """Test merging multiple signal dictionaries"""
    cache = SignalCache(temp_cache_dir)

    signals1 = {
        'domain_signals': [{'type': 'signal1'}],
        'concept_signals': [{'type': 'signal2'}],
        'rule_signals': [],
        'demand_pattern_signals': []
    }

    signals2 = {
        'domain_signals': [{'type': 'signal3'}],
        'concept_signals': [],
        'rule_signals': [{'type': 'signal4'}],
        'demand_pattern_signals': []
    }

    merged = cache.merge_signals(signals1, signals2)

    assert len(merged['domain_signals']) == 2
    assert len(merged['concept_signals']) == 1
    assert len(merged['rule_signals']) == 1
    assert len(merged['demand_pattern_signals']) == 0


def test_merge_signals_with_none(temp_cache_dir):
    """Test merging signals with None values"""
    cache = SignalCache(temp_cache_dir)

    signals1 = {
        'domain_signals': [{'type': 'signal1'}],
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': []
    }

    merged = cache.merge_signals(signals1, None)

    assert len(merged['domain_signals']) == 1
    assert len(merged['concept_signals']) == 0


def test_cache_stats(temp_cache_dir, sample_signals):
    """Test cache statistics"""
    cache = SignalCache(temp_cache_dir)

    # Initially empty
    stats = cache.get_cache_stats()
    assert stats['indexed_files'] == 0
    assert stats['cached_signal_files'] == 0

    # Add some files
    cache.store_signals(Path("/test/file1.yaml"), "hash1", sample_signals)
    cache.store_signals(Path("/test/file2.yaml"), "hash2", sample_signals)

    stats = cache.get_cache_stats()
    assert stats['indexed_files'] == 2
    assert stats['cached_signal_files'] == 2
    assert stats['total_size_bytes'] > 0


def test_cache_key_uniqueness(temp_cache_dir, sample_signals):
    """Test that cache keys are unique per file and hash"""
    cache = SignalCache(temp_cache_dir)

    file_path = Path("/test/file.yaml")

    # Store with first hash
    cache.store_signals(file_path, "hash1", sample_signals)

    # Store with second hash (simulating file change)
    modified_signals = {**sample_signals, 'domain_signals': []}
    cache.store_signals(file_path, "hash2", modified_signals)

    # Retrieve with first hash should get original
    retrieved1 = cache.get_cached_signals(file_path, "hash1")
    assert retrieved1 is None  # Old hash is invalidated by new store

    # Retrieve with second hash should get modified
    retrieved2 = cache.get_cached_signals(file_path, "hash2")
    assert retrieved2 is not None
    assert len(retrieved2['domain_signals']) == 0
