from datetime import datetime, timedelta, timezone
from pathlib import Path

from semantic.signal_cache import SignalCache


def test_ttl_expired_returns_none(tmp_path):
    """Entry older than TTL returns None."""
    cache = SignalCache(tmp_path, ttl_hours=1.0)
    cache.store_signals(Path("test.py"), "hash123", {"signals": []})

    # Manually backdate the cached_at in the index
    index = cache.load_index()
    key = list(index.keys())[0]
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    index[key]['cached_at'] = old_time
    cache.save_index(index)

    result = cache.get_cached_signals(Path("test.py"), "hash123")
    assert result is None

def test_ttl_not_expired_returns_data(tmp_path):
    """Fresh entry within TTL returns data."""
    cache = SignalCache(tmp_path, ttl_hours=24.0)
    cache.store_signals(Path("test.py"), "hash123", {"signals": ["x"]})
    result = cache.get_cached_signals(Path("test.py"), "hash123")
    assert result is not None

def test_ttl_zero_never_expires(tmp_path):
    """TTL=0 means no expiry."""
    cache = SignalCache(tmp_path, ttl_hours=0)
    cache.store_signals(Path("test.py"), "hash123", {"signals": []})

    index = cache.load_index()
    key = list(index.keys())[0]
    old_time = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    index[key]['cached_at'] = old_time
    cache.save_index(index)

    result = cache.get_cached_signals(Path("test.py"), "hash123")
    assert result is not None

def test_lru_eviction_removes_oldest(tmp_path):
    """When max_entries exceeded, oldest entry is evicted."""
    cache = SignalCache(tmp_path, max_entries=2)

    cache.store_signals(Path("a.py"), "hash_a", {"signals": ["a"]})
    cache.store_signals(Path("b.py"), "hash_b", {"signals": ["b"]})
    cache.store_signals(Path("c.py"), "hash_c", {"signals": ["c"]})  # triggers eviction

    index = cache.load_index()
    assert len(index) == 2
    # 'a.py' should be evicted (oldest)
    keys = list(index.keys())
    assert not any('a.py' in k for k in keys)

def test_max_entries_zero_unlimited(tmp_path):
    """max_entries=0 means unlimited."""
    cache = SignalCache(tmp_path, max_entries=0)
    for i in range(10):
        cache.store_signals(Path(f"file{i}.py"), f"hash{i}", {"signals": []})

    index = cache.load_index()
    assert len(index) == 10

def test_cache_stats_includes_limits(tmp_path):
    """get_cache_stats includes max_entries and ttl_hours."""
    cache = SignalCache(tmp_path, max_entries=50, ttl_hours=12.0)
    stats = cache.get_cache_stats()
    assert stats['max_entries'] == 50
    assert stats['ttl_hours'] == 12.0
