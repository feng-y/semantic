from pathlib import Path


def test_stats_command(tmp_path, capsys):
    """stats command prints cache statistics."""
    from semantic.cache_cli import run_stats
    from semantic.signal_cache import SignalCache

    cache = SignalCache(tmp_path)
    cache.store_signals(Path("test.py"), "hash123", {"signals": []})

    run_stats(tmp_path)
    captured = capsys.readouterr()
    assert "Indexed files" in captured.out
    assert "1" in captured.out


def test_list_command(tmp_path, capsys):
    """list command shows cached entries."""
    from semantic.cache_cli import run_list
    from semantic.signal_cache import SignalCache

    cache = SignalCache(tmp_path)
    cache.store_signals(Path("src/foo.py"), "hash_foo", {"signals": []})

    run_list(tmp_path)
    captured = capsys.readouterr()
    assert "foo.py" in captured.out


def test_invalidate_command(tmp_path, capsys):
    """invalidate removes a specific file's cache."""
    from semantic.cache_cli import run_invalidate
    from semantic.signal_cache import SignalCache

    cache = SignalCache(tmp_path)
    cache.store_signals(Path("src/foo.py"), "hash_foo", {"signals": []})

    run_invalidate(tmp_path, "src/foo.py")
    captured = capsys.readouterr()
    assert "Invalidated" in captured.out

    # Verify it's gone
    result = cache.get_cached_signals(Path("src/foo.py"), "hash_foo")
    assert result is None


def test_invalidate_not_cached(tmp_path, capsys):
    """invalidate on uncached file prints not-cached message."""
    from semantic.cache_cli import run_invalidate

    run_invalidate(tmp_path, "nonexistent.py")
    captured = capsys.readouterr()
    assert "Not cached" in captured.out


def test_clear_command(tmp_path, capsys):
    """clear removes all cache entries."""
    from semantic.cache_cli import run_clear
    from semantic.signal_cache import SignalCache

    cache = SignalCache(tmp_path)
    cache.store_signals(Path("a.py"), "h1", {"signals": []})
    cache.store_signals(Path("b.py"), "h2", {"signals": []})

    run_clear(tmp_path)
    captured = capsys.readouterr()
    assert "2" in captured.out
    assert "Cleared" in captured.out
