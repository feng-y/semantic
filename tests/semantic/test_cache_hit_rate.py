"""
Tests for cache hit rate tracking
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.signal_cache import SignalCache


def test_cache_hit_increments_counter(tmp_path):
    """First lookup is miss, second is hit."""
    cache = SignalCache(tmp_path)

    # First lookup - miss
    result = cache.get_cached_signals(Path("test.py"), "hash123")
    assert result is None
    stats = cache.get_cache_stats()
    assert stats['hits'] == 0
    assert stats['misses'] == 1

    # Store signals
    cache.store_signals(Path("test.py"), "hash123", {"signals": []})

    # Second lookup - hit
    result = cache.get_cached_signals(Path("test.py"), "hash123")
    assert result is not None
    stats = cache.get_cache_stats()
    assert stats['hits'] == 1
    assert stats['misses'] == 1
    assert stats['hit_rate'] == 50.0


def test_hit_rate_zero_when_no_lookups(tmp_path):
    """Hit rate is 0 when no cache operations."""
    cache = SignalCache(tmp_path)
    stats = cache.get_cache_stats()
    assert stats['hit_rate'] == 0.0


def test_hit_rate_100_when_all_hits(tmp_path):
    """Hit rate is 100% when all lookups hit."""
    cache = SignalCache(tmp_path)
    cache.store_signals(Path("test.py"), "hash123", {"signals": []})

    # 3 hits
    for _ in range(3):
        cache.get_cached_signals(Path("test.py"), "hash123")

    stats = cache.get_cache_stats()
    assert stats['hits'] == 3
    assert stats['misses'] == 0
    assert stats['hit_rate'] == 100.0


def test_multiple_misses_increment_counter(tmp_path):
    """Multiple cache misses increment the counter correctly."""
    cache = SignalCache(tmp_path)

    # 3 misses
    cache.get_cached_signals(Path("file1.py"), "hash1")
    cache.get_cached_signals(Path("file2.py"), "hash2")
    cache.get_cached_signals(Path("file3.py"), "hash3")

    stats = cache.get_cache_stats()
    assert stats['hits'] == 0
    assert stats['misses'] == 3
    assert stats['hit_rate'] == 0.0


def test_mixed_hits_and_misses(tmp_path):
    """Test hit rate calculation with mixed hits and misses."""
    cache = SignalCache(tmp_path)

    # Store 2 files
    cache.store_signals(Path("file1.py"), "hash1", {"signals": []})
    cache.store_signals(Path("file2.py"), "hash2", {"signals": []})

    # 2 hits
    cache.get_cached_signals(Path("file1.py"), "hash1")
    cache.get_cached_signals(Path("file2.py"), "hash2")

    # 1 miss
    cache.get_cached_signals(Path("file3.py"), "hash3")

    stats = cache.get_cache_stats()
    assert stats['hits'] == 2
    assert stats['misses'] == 1
    assert abs(stats['hit_rate'] - 66.666666) < 0.01  # ~66.67%


def test_hash_mismatch_counts_as_miss(tmp_path):
    """Cache lookup with wrong hash counts as miss."""
    cache = SignalCache(tmp_path)

    # Store with hash1
    cache.store_signals(Path("test.py"), "hash1", {"signals": []})

    # Lookup with hash2 - should be miss
    result = cache.get_cached_signals(Path("test.py"), "hash2")
    assert result is None

    stats = cache.get_cache_stats()
    assert stats['hits'] == 0
    assert stats['misses'] == 1


def test_reset_stats(tmp_path):
    """Test resetting hit/miss counters."""
    cache = SignalCache(tmp_path)

    # Generate some hits and misses
    cache.store_signals(Path("test.py"), "hash123", {"signals": []})
    cache.get_cached_signals(Path("test.py"), "hash123")  # hit
    cache.get_cached_signals(Path("other.py"), "hash456")  # miss

    stats = cache.get_cache_stats()
    assert stats['hits'] == 1
    assert stats['misses'] == 1

    # Reset
    cache.reset_stats()

    stats = cache.get_cache_stats()
    assert stats['hits'] == 0
    assert stats['misses'] == 0
    assert stats['hit_rate'] == 0.0
