from pathlib import Path

from semantic.signal_cache import SignalCache

SAMPLE_SIGNALS = {
    'domain_signals': [{'signal_type': 'test', 'source': 'test', 'evidence': 'test evidence', 'confidence': 'high', 'summary': 'x' * 100}],
    'concept_signals': [],
    'rule_signals': [],
    'demand_pattern_signals': [],
}


def test_compress_writes_gz_file(tmp_path):
    cache = SignalCache(tmp_path, compress=True)
    cache.store_signals(Path("test.py"), "hash123", SAMPLE_SIGNALS)
    gz_files = list((tmp_path / "signals").glob("*.json.gz"))
    assert len(gz_files) == 1
    json_files = list((tmp_path / "signals").glob("*.json"))
    assert len(json_files) == 0


def test_compress_roundtrip(tmp_path):
    cache = SignalCache(tmp_path, compress=True)
    cache.store_signals(Path("test.py"), "hash123", SAMPLE_SIGNALS)
    result = cache.get_cached_signals(Path("test.py"), "hash123")
    assert result is not None
    assert result['domain_signals'] == SAMPLE_SIGNALS['domain_signals']


def test_no_compress_writes_json_file(tmp_path):
    cache = SignalCache(tmp_path, compress=False)
    cache.store_signals(Path("test.py"), "hash123", SAMPLE_SIGNALS)
    json_files = list((tmp_path / "signals").glob("*.json"))
    assert len(json_files) == 1
    gz_files = list((tmp_path / "signals").glob("*.json.gz"))
    assert len(gz_files) == 0


def test_compress_reduces_size(tmp_path):
    """Compressed file should be smaller than uncompressed for repetitive data."""
    large_signals = {
        'domain_signals': [{'signal_type': 'test', 'source': 'test', 'evidence': 'test evidence', 'confidence': 'high', 'summary': 'x' * 1000}] * 10,
        'concept_signals': [],
        'rule_signals': [],
        'demand_pattern_signals': [],
    }
    cache_c = SignalCache(tmp_path / "compressed", compress=True)
    cache_u = SignalCache(tmp_path / "uncompressed", compress=False)

    cache_c.store_signals(Path("test.py"), "hash1", large_signals)
    cache_u.store_signals(Path("test.py"), "hash1", large_signals)

    gz_size = sum(f.stat().st_size for f in (tmp_path / "compressed" / "signals").glob("*.json.gz"))
    json_size = sum(f.stat().st_size for f in (tmp_path / "uncompressed" / "signals").glob("*.json"))
    assert gz_size < json_size


def test_clear_all_removes_gz_files(tmp_path):
    cache = SignalCache(tmp_path, compress=True)
    cache.store_signals(Path("a.py"), "h1", SAMPLE_SIGNALS)
    cache.store_signals(Path("b.py"), "h2", SAMPLE_SIGNALS)
    cache.clear_all()
    assert list((tmp_path / "signals").glob("*.json.gz")) == []


def test_stats_compressed_field(tmp_path):
    cache = SignalCache(tmp_path, compress=True)
    stats = cache.get_cache_stats()
    assert stats['compressed'] is True

    cache2 = SignalCache(tmp_path / "u", compress=False)
    stats2 = cache2.get_cache_stats()
    assert stats2['compressed'] is False
