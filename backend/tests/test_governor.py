"""Background resource governor priority behaviour."""

from __future__ import annotations

from app.config.settings import Settings
from app.services.background.governor import ResourceGovernor, ResourceState


def _governor() -> ResourceGovernor:
    return ResourceGovernor(
        Settings(
            INTLLM_DATABASE_URL="postgresql+asyncpg://x/y",
            INTLLM_BACKGROUND_RAM_THRESHOLD_PERCENT=90,
            INTLLM_BACKGROUND_CPU_THRESHOLD_PERCENT=85,
            INTLLM_BACKGROUND_LATENCY_THRESHOLD_MS=1000,
        )
    )


def test_interactive_request_forces_busy():
    governor = _governor()
    governor.begin_interactive()
    assert governor.evaluate() is ResourceState.BUSY
    governor.end_interactive()
    assert governor.evaluate() is ResourceState.NORMAL


def test_high_latency_throttles():
    governor = _governor()
    governor.record_latency(2000)
    assert governor.evaluate() is ResourceState.BUSY


def test_ram_pressure_is_critical():
    governor = _governor()
    assert governor.evaluate(ram_percent=95) is ResourceState.CRITICAL


def test_cpu_pressure_throttles():
    governor = _governor()
    assert governor.evaluate(cpu_percent=90) is ResourceState.BUSY


def test_paused_does_not_resume_at_normal():
    governor = _governor()
    governor.set_paused(True)
    assert governor.evaluate() is ResourceState.BUSY


def test_next_delay_scales_with_pressure():
    governor = _governor()
    governor.evaluate()
    normal_delay = governor.next_delay(5.0)
    governor.record_latency(5000)
    governor.evaluate()
    busy_delay = governor.next_delay(5.0)
    assert busy_delay > normal_delay
