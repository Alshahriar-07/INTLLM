"""Lightweight in-process metrics for observability.

Tracks request/lookup/inference latencies and counters exposed by the
diagnostics endpoint. This is intentionally dependency-free; a heavier
metrics backend can replace it without touching call sites.
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict, deque
from collections.abc import Iterator
from contextlib import contextmanager

_WINDOW = 500


class MetricsRegistry:
    def __init__(self) -> None:
        self._samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=_WINDOW))
        self._counters: dict[str, int] = defaultdict(int)

    def observe(self, name: str, value_ms: float) -> None:
        self._samples[name].append(value_ms)

    def increment(self, name: str, by: int = 1) -> None:
        self._counters[name] += by

    @contextmanager
    def timer(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.observe(name, (time.perf_counter() - start) * 1000.0)

    def snapshot(self) -> dict[str, object]:
        latencies: dict[str, dict[str, float]] = {}
        for name, samples in self._samples.items():
            if not samples:
                continue
            latencies[name] = {
                "count": len(samples),
                "avg_ms": round(statistics.fmean(samples), 2),
                "p95_ms": round(_percentile(samples, 95), 2),
                "max_ms": round(max(samples), 2),
            }
        return {"latencies": latencies, "counters": dict(self._counters)}


def _percentile(samples: deque[float], pct: float) -> float:
    ordered = sorted(samples)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1))))
    return ordered[index]


metrics = MetricsRegistry()
