"""System and hardware telemetry.

Uses psutil for CPU/RAM/disk and nvidia-smi (when present) for GPU. Metrics
that cannot be detected are returned as ``None`` with a status flag rather
than being invented.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.db.health import get_database_health
from app.db.session import get_database
from app.services.browser.service import get_browser_service
from app.services.runtime.ollama import get_ollama_adapter
from app.services.web.service import get_web_service

logger = get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _run_blocking(func, *args):
    return await asyncio.to_thread(func, *args)


def _cpu_name() -> str:
    processor = platform.processor()
    if processor:
        return processor
    try:
        import psutil

        freq = psutil.cpu_freq()
        if freq and freq.max:
            return f"CPU @ {freq.max / 1000:.2f} GHz"
    except Exception:  # noqa: BLE001
        pass
    return platform.machine() or "Unknown CPU"


def _gpu_info() -> dict[str, Any] | None:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None
    try:
        output = subprocess.run(
            [
                executable,
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:  # noqa: BLE001
        return None
    if output.returncode != 0 or not output.stdout.strip():
        return None
    first = output.stdout.strip().splitlines()[0].split(",")
    if len(first) < 4:
        return None
    try:
        return {
            "name": first[0].strip(),
            "vramUsedGB": round(float(first[1]) / 1024, 2),
            "vramTotalGB": round(float(first[2]) / 1024, 2),
            "usage": float(first[3]),
        }
    except ValueError:
        return None


class HardwareService:
    async def snapshot(self) -> dict[str, Any]:
        import psutil

        cpu_percent = await _run_blocking(lambda: psutil.cpu_percent(interval=0.1))
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(get_settings().workspace_dir.parent))
        gpu = await _run_blocking(_gpu_info)

        return {
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
            },
            "cpu": {
                "name": _cpu_name(),
                "usage": float(cpu_percent),
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
            },
            "ram": {
                "usedGB": round((memory.total - memory.available) / (1024**3), 2),
                "totalGB": round(memory.total / (1024**3), 2),
                "percent": float(memory.percent),
            },
            "gpu": gpu,
            "gpu_available": gpu is not None,
            "disk": {
                "freeGB": round(disk.free / (1024**3), 2),
                "totalGB": round(disk.total / (1024**3), 2),
                "percent": float(disk.percent),
            },
            "captured_at": _now_iso(),
        }


class SystemService:
    # The web reachability probe hits the network, so it is cached briefly so a
    # polling dashboard does not repeatedly probe the provider.
    WEB_PROBE_TTL_SECONDS = 30.0

    def __init__(self) -> None:
        self._web_cache: tuple[float, bool, str | None] | None = None

    async def _web_health(self) -> tuple[bool, str | None]:
        import time as _time

        now = _time.monotonic()
        if self._web_cache and now - self._web_cache[0] < self.WEB_PROBE_TTL_SECONDS:
            return self._web_cache[1], self._web_cache[2]
        try:
            available, error = await get_web_service().health()
        except Exception as exc:  # noqa: BLE001
            available, error = False, str(exc)
        self._web_cache = (now, available, error)
        return available, error

    async def status(self) -> dict[str, Any]:
        """Aggregate real status for INTLLM, PostgreSQL, Ollama, Web, Browser."""
        db_available, db_error = await get_database().ping()
        ollama_available, ollama_error = await get_ollama_adapter().health()
        web_available, web_error = await self._web_health()
        snapshot = get_database_health().snapshot()

        browser = get_browser_service()
        browser_available, browser_error = browser.availability()

        return {
            "intllm": {"status": "connected", "detail": "Backend online"},
            "postgres": {
                "status": "connected" if db_available else "offline",
                "detail": db_error,
                "state": snapshot.status,
                "category": snapshot.category,
            },
            "memory": {
                "status": snapshot.memory,
                "detail": snapshot.detail,
            },
            "ollama": {
                "status": "connected" if ollama_available else "offline",
                "detail": ollama_error,
            },
            "web": {
                "status": "connected" if web_available else "unavailable",
                "detail": web_error,
            },
            "browser": {
                "status": browser_available,
                "detail": browser_error,
            },
            "captured_at": _now_iso(),
        }


_hardware: HardwareService | None = None
_system: SystemService | None = None


def get_hardware_service() -> HardwareService:
    global _hardware
    if _hardware is None:
        _hardware = HardwareService()
    return _hardware


def get_system_service() -> SystemService:
    global _system
    if _system is None:
        _system = SystemService()
    return _system
