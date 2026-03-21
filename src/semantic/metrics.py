"""
Performance metrics for semantic extraction pipeline.

Usage:
    from semantic.metrics import MetricsCollector

    metrics = MetricsCollector(enabled=True)
    with metrics.time("change_detection"):
        ...do work...
    with metrics.time("signal_extraction"):
        ...do work...

    metrics.report()  # prints summary
"""
import time
from contextlib import contextmanager


class MetricsCollector:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._timings: dict[str, list[float]] = {}  # phase -> list of durations (ms)

    @contextmanager
    def time(self, phase: str):
        """Context manager to time a phase. No-op if not enabled."""
        if not self.enabled:
            yield
            return
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._timings.setdefault(phase, []).append(elapsed_ms)

    def report(self) -> str:
        """Return formatted timing report string."""
        if not self.enabled or not self._timings:
            return ""
        parts = []
        for phase, durations in self._timings.items():
            total_ms = sum(durations)
            parts.append(f"{phase}: {total_ms:.1f}ms")
        return "[metrics] " + ", ".join(parts)

    def get_timings(self) -> dict[str, float]:
        """Return dict of phase -> total_ms for testing."""
        return {phase: sum(durations) for phase, durations in self._timings.items()}
