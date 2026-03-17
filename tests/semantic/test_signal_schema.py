import pytest
from pathlib import Path
from semantic.signal_schema import validate_signals, KNOWN_CATEGORIES
from semantic.signal_cache import SignalCache

# --- validate_signals unit tests ---

def test_valid_empty_dict():
    ok, errors = validate_signals({})
    assert ok
    assert errors == []

def test_valid_full_signals():
    signals = {
        'domain_signals': [{'signal_type': 'x', 'source': 'test', 'evidence': 'test evidence', 'confidence': 'high', 'summary': 'y'}],
        'concept_signals': [],
        'rule_signals': [{'signal_type': 'z', 'source': 'test', 'evidence': 'test evidence', 'confidence': 'medium'}],
        'demand_pattern_signals': [],
    }
    ok, errors = validate_signals(signals)
    assert ok
    assert errors == []

def test_none_is_invalid():
    ok, errors = validate_signals(None)
    assert not ok
    assert any("None" in e or "must not be None" in e for e in errors)

def test_non_dict_is_invalid():
    ok, errors = validate_signals([1, 2, 3])
    assert not ok
    assert errors

def test_category_not_list_is_invalid():
    ok, errors = validate_signals({'domain_signals': 'not a list'})
    assert not ok
    assert any('domain_signals' in e for e in errors)

def test_item_not_dict_is_invalid():
    ok, errors = validate_signals({'domain_signals': ['string_item']})
    assert not ok
    assert any('domain_signals[0]' in e for e in errors)

def test_unknown_top_level_keys_allowed():
    ok, errors = validate_signals({'unknown_key': 'anything'})
    assert ok

def test_partial_categories_valid():
    """Only some categories present is fine."""
    ok, errors = validate_signals({'domain_signals': []})
    assert ok

# --- SignalCache integration tests ---

def test_store_rejects_none(tmp_path):
    cache = SignalCache(tmp_path)
    with pytest.raises(ValueError, match="Invalid signals schema"):
        cache.store_signals(Path("test.py"), "hash123", None)

def test_store_rejects_list(tmp_path):
    cache = SignalCache(tmp_path)
    with pytest.raises(ValueError):
        cache.store_signals(Path("test.py"), "hash123", [1, 2, 3])

def test_store_rejects_bad_category_type(tmp_path):
    cache = SignalCache(tmp_path)
    with pytest.raises(ValueError):
        cache.store_signals(Path("test.py"), "hash123", {'domain_signals': 'bad'})

def test_store_accepts_valid_signals(tmp_path):
    cache = SignalCache(tmp_path)
    signals = {'domain_signals': [{'signal_type': 'x', 'source': 'test', 'evidence': 'test evidence', 'confidence': 'high'}], 'concept_signals': []}
    # Should not raise
    cache.store_signals(Path("test.py"), "hash123", signals)
    result = cache.get_cached_signals(Path("test.py"), "hash123")
    assert result is not None
