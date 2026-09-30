"""Background resource governor.

Interactive (P0) work always wins. When interactive latency, CPU or RAM cross
configured thresholds, background work is throttled or paused and resumes
gradually when the pressure clears.
"""

from __future__ import annotations

import time
from collections import deque
from enum import Enum

from app.config.settings import Settings, get_settings


class ResourceState(str, Enum):
    NORMAL = "NORMAL"
    BUSY = "BUSY"
    CRITICAL = "CRITICAL"


class ResourceGovernor:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._active_interactive = 0
        self._recent_latencies: deque[float] = deque(maxlen=20)
        self._last_state = ResourceState.NORMAL
        self._paused = False

    # --- signals ----------------------------------------------------------
    def begin_interactive(self) -> None:
        self._active_interactive += 1

    def end_interactive(self) -> None:
        self._active_interactive = max(0, self._active_interactive - 1)

    def record_latency(self, ms: float) -> None:
        self._recent_latencies.append(ms)

    @property
    def active_interactive(self) -> int:
        return self._active_interactive

    @property
    def recent_latency_ms(self) -> float | None:
        if not self._recent_latencies:
            return None
        return sum(self._recent_latencies) / len(self._recent_latencies)

    @property
    def paused(self) -> bool:
        return self._paused

    def set_paused(self, value: bool) -> None:
        self._paused = value

    def evaluate(self, *, cpu_percent: float | None = None, ram_percent: float | None = None) -> ResourceState:
        settings = self._settings
        if self._active_interactive > 0:
            state = ResourceState.BUSY
        elif self.recent_latency_ms is not None and (
            self.recent_latency_ms > settings.intllm_background_latency_threshold_ms
        ):
            state = ResourceState.BUSY
        elif cpu_percent is not None and cpu_percent > settings.intllm_background_cpu_threshold_percent:
            state = ResourceState.BUSY
        else:
            state = ResourceState.NORMAL

        if ram_percent is not None and ram_percent > settings.intllm_background_ram_threshold_percent:
            state = ResourceState.CRITICAL
        elif cpu_percent is not None and cpu_percent > 95.0:
            state = ResourceState.CRITICAL

        if self._paused and state is ResourceState.NORMAL:
            state = ResourceState.BUSY
        self._last_state = state
        return state

    def next_delay(self, base_seconds: float) -> float:
        """Delay between background steps based on current pressure."""
        state = self._last_state
        if state is ResourceState.CRITICAL:
            return base_seconds * 6.0
        if state is ResourceState.BUSY:
            return base_seconds * 3.0
        return base_seconds

    @property
    def state(self) -> ResourceState:
        return self._last_state


def monotonic_ms() -> float:
    return time.perf_counter() * 1000.0
