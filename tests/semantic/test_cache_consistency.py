"""Tests for SignalCache.validate_consistency()"""
from pathlib import Path

from semantic.signal_cache import SignalCache


def test_consistent_cache_reports_no_issues(tmp_path):
    cache = SignalCache(tmp_path)
    cache.store_signals(Path("a.py"), "h1", {"domain_signals": []})
    result = cache.validate_consistency()
    assert result['is_consistent'] is True
    assert result['orphaned_files'] == []
    assert result['missing_files'] == []
    assert result['corrupt_files'] == []


def test_detects_orphaned_signal_file(tmp_path):
    """Signal file on disk but not in index."""
    cache = SignalCache(tmp_path)
    orphan = tmp_path / "signals" / "orphan_abc123.json"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text('{"domain_signals": []}')

    result = cache.validate_consistency()
    assert not result['is_consistent']
    assert len(result['orphaned_files']) == 1


def test_detects_missing_signal_file(tmp_path):
    """Index entry exists but signal file deleted."""
    cache = SignalCache(tmp_path)
    cache.store_signals(Path("a.py"), "h1", {"domain_signals": []})
    for f in (tmp_path / "signals").glob("*.json"):
        f.unlink()

    result = cache.validate_consistency()
    assert not result['is_consistent']
    assert len(result['missing_files']) == 1


def test_repair_removes_orphans(tmp_path):
    cache = SignalCache(tmp_path)
    orphan = tmp_path / "signals" / "orphan_xyz.json"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text('{}')

    result = cache.validate_consistency(repair=True)
    assert result['repaired'] is True
    assert not orphan.exists()


def test_repair_removes_missing_index_entries(tmp_path):
    cache = SignalCache(tmp_path)
    cache.store_signals(Path("a.py"), "h1", {"domain_signals": []})
    for f in (tmp_path / "signals").glob("*.json"):
        f.unlink()

    cache.validate_consistency(repair=True)
    index = cache.load_index()
    assert len(index) == 0


def test_empty_cache_is_consistent(tmp_path):
    cache = SignalCache(tmp_path)
    result = cache.validate_consistency()
    assert result['is_consistent'] is True
