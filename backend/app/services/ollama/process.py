"""Cross-platform Ollama process/service detection and control.

No blind process spawning: every start/stop/restart verifies the *actual*
daemon state through the real health endpoint before reporting success.
Supported platforms: Windows (service or executable), Linux (systemd user
service or executable), macOS (application binary or executable).
"""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
import subprocess
import time
from typing import Any

import httpx

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

# Wait budget for a start/stop cycle before giving up.
START_TIMEOUT_SECONDS = 30.0
STOP_TIMEOUT_SECONDS = 20.0
HEALTH_POLL_INTERVAL = 0.5

OLLAMA_SERVICE_NAME = "Ollama"  # Windows service / systemd user unit stem


class OllamaControlError(Exception):
    """Raised when a lifecycle operation fails; message is user-facing."""


def _ollama_endpoint() -> str:
    return get_settings().intllm_ollama_url.rstrip("/")


async def _probe_health(timeout: float = 2.0) -> tuple[bool, str | None]:
    """Probe the real Ollama daemon root endpoint."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(_ollama_endpoint())
        if response.status_code < 500:
            # Ollama replies 200 OK on "/" when up.
            return True, None
        return False, f"HTTP {response.status_code}"
    except Exception as exc:  # noqa: BLE001 - reported as unavailable reason
        return False, f"{type(exc).__name__}: {exc}"


async def is_running() -> tuple[bool, str | None]:
    """Return (running, error) based on a real HTTP health probe."""
    return await _probe_health()


def _find_ollama_executable() -> str | None:
    """Locate the Ollama executable across platforms."""
    explicit = os.environ.get("INTLLM_OLLAMA_EXECUTABLE", "").strip()
    if explicit and (os.path.isfile(explicit) or shutil.which(explicit)):
        return explicit

    found = shutil.which("ollama")
    if found:
        return found

    candidates: list[str] = []
    if IS_WINDOWS:
        candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
            r"C:\Program Files\Ollama\ollama.exe",
        ]
    elif IS_MACOS:
        candidates = [
            "/Applications/Ollama.app/Contents/Resources/ollama",
            "/usr/local/bin/ollama",
            "/opt/homebrew/bin/ollama",
        ]
    else:  # Linux
        candidates = ["/usr/local/bin/ollama", "/usr/bin/ollama", "/opt/ollama/ollama"]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


# --- Windows service helpers -------------------------------------------------


def _windows_service_query() -> str | None:
    try:
        result = subprocess.run(
            ["sc", "query", OLLAMA_SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:  # noqa: BLE001
        return None
    if result.returncode != 0:
        return None
    output = result.stdout or ""
    if "RUNNING" in output:
        return "running"
    if "STOPPED" in output:
        return "stopped"
    return "unknown"


def _windows_service_control(action: str) -> tuple[bool, str | None]:
    """Start/stop the Ollama Windows service. Returns (ok, error)."""
    command = {"start": "start", "stop": "stop"}.get(action)
    if not command:
        return False, f"Unknown service action: {action}"
    try:
        result = subprocess.run(
            ["sc", command, OLLAMA_SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if result.returncode != 0:
        # 1060 = service does not exist; fall back to executable launch.
        if "1060" in (result.stdout or "") or "1060" in (result.stderr or ""):
            return False, "no_service"
        return False, (result.stderr or result.stdout or f"sc exit {result.returncode}").strip()
    return True, None


# --- systemd (Linux) helpers --------------------------------------------------


async def _systemd_available() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl",
            "--user",
            "is-active",
            "--quiet",
            OLLAMA_SERVICE_NAME.lower(),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except (FileNotFoundError, OSError):
        return False
    await proc.wait()
    # is-active exits 0 when the unit exists and is active, 3 when inactive but
    # a configured unit; other codes usually mean "no such unit".
    return proc.returncode in (0, 3)


async def _systemd_control(action: str) -> tuple[bool, str | None]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl",
            "--user",
            action,
            OLLAMA_SERVICE_NAME.lower(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
    except (TimeoutError, FileNotFoundError, OSError) as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, stderr.decode("utf-8", "replace").strip() or f"systemctl exit {proc.returncode}"
    return True, None


# --- Process spawn / terminate ------------------------------------------------


async def _spawn_daemon(executable: str) -> None:
    """Launch `ollama serve` detached from this process."""
    if IS_WINDOWS:
        flags: int = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        subprocess.Popen(
            [executable, "serve"],
            creationflags=flags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        subprocess.Popen(
            [executable, "serve"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    logger.info("spawned ollama serve", extra={"intllm_extra": {"executable": executable}})


def _pids_matching() -> list[int]:
    """Find Ollama daemon PIDs (best-effort, psutil)."""
    try:
        import psutil
    except ImportError:  # pragma: no cover - psutil is a hard dependency
        return []
    pids: list[int] = []
    for proc in psutil.process_iter(["name", "exe", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
            exe = (proc.info.get("exe") or "").lower()
            if "ollama" in name and "ollama app" not in name or "ollama" in exe and " serve" in f" {cmdline}" or cmdline.strip() in ("ollama serve",) or cmdline.endswith("ollama serve"):
                pids.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return pids


async def _terminate_pids(pids: list[int], timeout: float) -> tuple[bool, str | None]:
    """Gracefully terminate then kill the given PIDs. Returns (stopped, error)."""
    if not pids:
        return True, None
    try:
        import psutil
    except ImportError:  # pragma: no cover
        return False, "psutil unavailable for process termination"
    procs = []
    for pid in pids:
        try:
            procs.append(psutil.Process(pid))
        except psutil.NoSuchProcess:
            continue
    for proc in procs:
        try:
            proc.terminate()
        except psutil.AccessDenied as exc:
            return False, f"Access denied stopping PID {proc.pid}: {exc}"
    _, alive = psutil.wait_procs(procs, timeout=timeout)
    if alive:
        for proc in alive:
            try:
                proc.kill()
            except psutil.AccessDenied as exc:
                return False, f"Access denied killing PID {proc.pid}: {exc}"
        _, alive = psutil.wait_procs(alive, timeout=5)
    if alive:
        return False, f"Process(es) {', '.join(str(p.pid) for p in alive)} refused to stop"
    return True, None


# --- Public lifecycle operations ----------------------------------------------


async def wait_until(healthy: bool, timeout: float) -> tuple[bool, str | None]:
    """Poll the real endpoint until it matches `healthy` or timeout expires.

    Returns ``(probe_ok, error)`` where ``probe_ok`` is the last health probe
    result: True means the endpoint responded, False means it did not.
    """
    deadline = time.monotonic() + timeout
    while True:
        ok, err = await _probe_health()
        if ok == healthy:
            return ok, None if ok else (err or "unavailable")
        if time.monotonic() >= deadline:
            return ok, err or ("still unreachable" if healthy else "endpoint still responding")
        await asyncio.sleep(HEALTH_POLL_INTERVAL)


async def start() -> dict[str, Any]:
    """Start Ollama; verify actual availability before returning."""
    running, _ = await is_running()
    if running:
        return {"changed": False, "running": True, "message": "Ollama is already running"}

    started_via: str | None = None

    if IS_WINDOWS and _windows_service_query() in ("stopped", "unknown"):
        ok, error = _windows_service_control("start")
        if ok:
            started_via = "windows-service"
        elif error != "no_service":
            return {
                "changed": False,
                "running": False,
                "error": f"Windows service start failed: {error}",
            }

    if started_via is None and not IS_WINDOWS and not IS_MACOS and await _systemd_available():
        ok, error = await _systemd_control("start")
        if ok:
            started_via = "systemd-user"
        else:
            logger.warning("systemd start failed, falling back to executable")

    if started_via is None:
        executable = _find_ollama_executable()
        if not executable:
            return {
                "changed": False,
                "running": False,
                "error": (
                    "Ollama executable not found. Install Ollama (https://ollama.com) "
                    "or set INTLLM_OLLAMA_EXECUTABLE to its path."
                ),
            }
        await _spawn_daemon(executable)
        started_via = "executable"

    ok, error = await wait_until(True, START_TIMEOUT_SECONDS)
    if not ok:
        return {
            "changed": True,
            "running": False,
            "error": f"Ollama did not become healthy after start ({started_via}): {error}",
        }
    return {"changed": True, "running": True, "startedVia": started_via}


async def stop() -> dict[str, Any]:
    """Stop a genuinely running Ollama; verify it actually stopped."""
    running, _ = await is_running()
    if not running:
        return {"changed": False, "running": False, "message": "Ollama is not running"}

    if IS_WINDOWS:
        state = _windows_service_query()
        if state == "running":
            ok, error = _windows_service_control("stop")
            if not ok:
                return {"changed": False, "running": True, "error": f"Windows service stop failed: {error}"}
        else:
            stopped, error = await _terminate_pids(_pids_matching(), STOP_TIMEOUT_SECONDS)
            if not stopped:
                return {"changed": False, "running": True, "error": error}
    elif not IS_MACOS and await _systemd_available():
        ok, error = await _systemd_control("stop")
        if not ok:
            return {"changed": False, "running": True, "error": f"systemd stop failed: {error}"}
    else:
        stopped, error = await _terminate_pids(_pids_matching(), STOP_TIMEOUT_SECONDS)
        if not stopped:
            return {"changed": False, "running": True, "error": error}

    # wait_until(False) returns the last probe result: False means the
    # endpoint stopped responding, i.e. the daemon is really down.
    down, error = await wait_until(False, STOP_TIMEOUT_SECONDS)
    if down is False:
        return {"changed": True, "running": False}
    return {
        "changed": True,
        "running": True,
        "error": f"Ollama still responding after stop: {error}",
    }


async def restart() -> dict[str, Any]:
    running, _ = await is_running()
    if running:
        result = await stop()
        if result.get("error") or result.get("running"):
            return {"changed": False, "running": result.get("running", False), "error": result.get("error") or "stop failed"}
    result = await start()
    return result
