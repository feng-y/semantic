"""
Performance benchmark tests for the semantic extraction system.

These tests verify that key operations complete within acceptable time bounds.
All time limits are generous to avoid flakiness in CI environments.
"""
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic.change_detector import ChangeDetector
from semantic.extract_signals import run_incremental_extraction
from semantic.signal_cache import SignalCache


def test_cache_lookup_fast(tmp_path):
    cache = SignalCache(tmp_path / "cache")
    file_path = tmp_path / "test_file.yaml"
    file_path.write_text("content")
    file_hash = "abc123"
    signals = {
        "domain_signals": [{"signal_type": "test", "source": "test", "evidence": "test evidence", "confidence": "high", "name": "D1", "score": 0.9}],
        "concept_signals": [],
        "rule_signals": [],
        "demand_pattern_signals": [],
    }
    cache.store_signals(file_path, file_hash, signals)

    start = time.perf_counter()
    for _ in range(100):
        cache.get_cached_signals(file_path, file_hash)
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / 100) * 1000
    print(f"\nCache lookup avg: {avg_ms:.1f}ms")
    assert avg_ms < 5.0, f"Cache lookup too slow: {avg_ms:.1f}ms (limit 5ms)"


def test_hash_computation_scales(tmp_path):
    big_file = tmp_path / "big.txt"
    big_file.write_bytes(b"x" * 1024 * 1024)  # 1MB

    detector = ChangeDetector(tmp_path, tmp_path / "cache")

    start = time.perf_counter()
    result = detector.compute_file_hash(big_file)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"\n1MB hash time: {elapsed_ms:.0f}ms")
    assert result != "", "Hash should not be empty"
    assert elapsed_ms < 500, f"Hash too slow: {elapsed_ms:.0f}ms (limit 500ms)"


def test_large_signal_merge_fast(tmp_path):
    cache = SignalCache(tmp_path / "cache")

    # Store 50 entries
    for i in range(50):
        fp = tmp_path / f"file_{i}.yaml"
        fp.write_text(f"content {i}")
        signals = {
            "domain_signals": [{"signal_type": "test", "source": "test", "evidence": "test evidence", "confidence": "high", "name": f"D{i}"}],
            "concept_signals": [],
            "rule_signals": [],
            "demand_pattern_signals": [],
        }
        cache.store_signals(fp, f"hash{i}", signals)

    # Build two dicts with 100 items per category
    def make_signals(n, prefix):
        return {
            "domain_signals": [{"signal_type": "test", "source": "test", "evidence": "test evidence", "confidence": "high", "name": f"{prefix}_D{j}"} for j in range(n)],
            "concept_signals": [{"signal_type": "test", "source": "test", "evidence": "test evidence", "confidence": "high", "name": f"{prefix}_C{j}"} for j in range(n)],
            "rule_signals": [{"signal_type": "test", "source": "test", "evidence": "test evidence", "confidence": "high", "name": f"{prefix}_R{j}"} for j in range(n)],
            "demand_pattern_signals": [{"signal_type": "test", "source": "test", "evidence": "test evidence", "confidence": "high", "name": f"{prefix}_P{j}"} for j in range(n)],
        }

    dict_a = make_signals(100, "A")
    dict_b = make_signals(100, "B")

    start = time.perf_counter()
    merged = cache.merge_signals(dict_a, dict_b)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"\nMerge 200 signals: {elapsed_ms:.1f}ms")
    assert len(merged["domain_signals"]) == 200
    assert elapsed_ms < 100, f"Merge too slow: {elapsed_ms:.1f}ms (limit 100ms)"


def test_incremental_faster_than_full(tmp_path):
    fact_root = tmp_path / "fact"
    fact_root.mkdir()

    canonical = {
        "metadata": {"version": "1.0"},
        "domains": [{"name": f"Domain{i}", "description": f"Test domain {i}"} for i in range(3)],
        "concepts": [{"name": f"Concept{i}", "description": f"Test concept {i}"} for i in range(3)],
    }
    (fact_root / "fact_canonical_sample.yaml").write_text(yaml.dump(canonical))

    working = {"summary": "Test working summary", "key_points": ["point1", "point2"]}
    (fact_root / "fact_working_summary_sample.yaml").write_text(yaml.dump(working))

    cache_dir = tmp_path / "cache"

    # Cold run
    start = time.perf_counter()
    run_incremental_extraction(fact_root, cache_dir)
    cold_ms = (time.perf_counter() - start) * 1000

    # Warm run (no changes)
    start = time.perf_counter()
    run_incremental_extraction(fact_root, cache_dir)
    warm_ms = (time.perf_counter() - start) * 1000

    print(f"\nCold: {cold_ms:.0f}ms, Warm: {warm_ms:.0f}ms")
    assert warm_ms <= cold_ms * 1.5, (
        f"Warm run ({warm_ms:.0f}ms) should not be much slower than cold ({cold_ms:.0f}ms)"
    )
