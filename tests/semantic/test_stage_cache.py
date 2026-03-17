"""
Tests for StageCache module
"""

import pytest
from pathlib import Path
import json
import sys
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.stage_cache import StageCache


def test_cache_miss_returns_none(tmp_path):
    """Fresh cache returns None on get"""
    cache = StageCache(tmp_path / "cache")
    result = cache.get('build_candidates', 'abc123')
    assert result is None


def test_cache_hit_returns_data(tmp_path):
    """put then get returns same data"""
    cache = StageCache(tmp_path / "cache")
    data = {'domains': [{'id': 'x', 'name': 'Test'}], 'metadata': {'count': 1}}
    cache.put('build_candidates', 'abc123', data)
    result = cache.get('build_candidates', 'abc123')
    assert result == data


def test_cache_ttl_expiry(tmp_path):
    """Expired entry returns None"""
    cache = StageCache(tmp_path / "cache", ttl_hours=0.000001)
    data = {'domains': [], 'metadata': {}}
    cache.put('build_candidates', 'abc123', data)
    # Force expiry by backdating the index entry
    index_file = tmp_path / "cache" / "stage_index.json"
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)
    entry_key = 'build_candidates:abc123'
    index[entry_key]['cached_at'] = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    ).isoformat()
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f)
    result = cache.get('build_candidates', 'abc123')
    assert result is None


def test_cache_invalidate(tmp_path):
    """invalidate removes the entry"""
    cache = StageCache(tmp_path / "cache")
    data = {'domains': [], 'metadata': {}}
    cache.put('build_candidates', 'abc123', data)
    cache.invalidate('build_candidates', 'abc123')
    result = cache.get('build_candidates', 'abc123')
    assert result is None


def test_cache_clear(tmp_path):
    """clear removes all entries"""
    cache = StageCache(tmp_path / "cache")
    cache.put('build_candidates', 'hash1', {'a': 1})
    cache.put('score_recommend', 'hash2', {'b': 2})
    cache.clear()
    assert cache.get('build_candidates', 'hash1') is None
    assert cache.get('score_recommend', 'hash2') is None


def test_hash_file(tmp_path):
    """hash_file returns consistent hex string"""
    f = tmp_path / "input.yaml"
    f.write_text("domain_signals: []\n", encoding='utf-8')
    cache = StageCache(tmp_path / "cache")
    h1 = cache.hash_file(f)
    h2 = cache.hash_file(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex
    assert h1 != ""


def test_stats_hit_rate(tmp_path):
    """stats() returns correct hit_rate after hits/misses"""
    cache = StageCache(tmp_path / "cache")
    data = {'x': 1}
    cache.put('stage', 'h1', data)
    cache.get('stage', 'h1')   # hit
    cache.get('stage', 'h1')   # hit
    cache.get('stage', 'miss') # miss
    s = cache.stats()
    assert s['hits'] == 2
    assert s['misses'] == 1
    assert abs(s['hit_rate'] - 66.666) < 0.1


def test_different_stages_independent(tmp_path):
    """Same input_hash, different stage = independent entries"""
    cache = StageCache(tmp_path / "cache")
    data_a = {'stage': 'a'}
    data_b = {'stage': 'b'}
    cache.put('stage_a', 'samehash', data_a)
    cache.put('stage_b', 'samehash', data_b)
    assert cache.get('stage_a', 'samehash') == data_a
    assert cache.get('stage_b', 'samehash') == data_b
    cache.invalidate('stage_a', 'samehash')
    assert cache.get('stage_a', 'samehash') is None
    assert cache.get('stage_b', 'samehash') == data_b
