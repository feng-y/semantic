"""Tests for MetricsCollector in semantic.metrics"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from semantic.metrics import MetricsCollector


def test_timing_disabled():
    metrics = MetricsCollector(enabled=False)
    with metrics.time("phase"):
        pass
    assert metrics.get_timings() == {}


def test_timing_enabled():
    metrics = MetricsCollector(enabled=True)
    with metrics.time("phase"):
        time.sleep(0.001)
    timings = metrics.get_timings()
    assert "phase" in timings
    assert timings["phase"] > 0


def test_report_empty_when_disabled():
    metrics = MetricsCollector(enabled=False)
    with metrics.time("phase"):
        pass
    assert metrics.report() == ""


def test_report_format():
    metrics = MetricsCollector(enabled=True)
    with metrics.time("phase"):
        pass
    report = metrics.report()
    assert report.startswith("[metrics]")
    assert "phase" in report


def test_multiple_phases():
    metrics = MetricsCollector(enabled=True)
    with metrics.time("alpha"):
        pass
    with metrics.time("beta"):
        pass
    timings = metrics.get_timings()
    assert "alpha" in timings
    assert "beta" in timings


def test_get_timings_returns_totals():
    metrics = MetricsCollector(enabled=True)
    with metrics.time("x"):
        pass
    with metrics.time("y"):
        pass
    timings = metrics.get_timings()
    assert len(timings) == 2
    assert all(v >= 0 for v in timings.values())
