"""INTLLM Windows application launcher.

Single-entry startup used by the packaged INTLLM.exe:

1. initialize configuration and local application directories
2. initialize rotating file logging (never logs secrets)
3. check the configured backend port (connect to an existing INTLLM instance
   instead of starting a duplicate; never kill unrelated processes)
4. start the real FastAPI backend (uvicorn, in-process)
5. wait until /api/health responds
6. open the production frontend in the default browser
7. serve until the user closes the window (Ctrl+C or console close)

Database and Ollama stay external, honestly reported dependencies:
the launcher never fabricates availability.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

APP_NAME = "INTLLM"
HEALTH_TIMEOUT_SECONDS = 45.0
HEALTH_POLL_SECONDS = 0.4
# /api/health probes PostgreSQL and Ollama; when Ollama is unreachable its
# connect probe can take several seconds, so the request timeout must be well
# above that or the readiness waiter never sees the (valid) 200/503 response.
HEALTH_REQUEST_TIMEOUT_SECONDS = 10.0


# --- Application directories ---------------------------------------------------


def app_data_dir() -> Path:
    """Per-user writable data dir: %LOCALAPPDATA%\\INTLLM on Windows."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / APP_NAME


def _ensure_dirs(settings) -> dict[str, Path]:
    data = app_data_dir()
    dirs = {
        "root": data,
        "logs": data / "logs",
        "workspace": data / "workspace",
        "data": data / "data",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    # Point the backend's relative dirs at the per-user location when the
    # process has not been given explicit overrides.
    if not os.environ.get("INTLLM_WORKSPACE_DIR"):
        os.environ["INTLLM_WORKSPACE_DIR"] = str(dirs["workspace"])
    if not os.environ.get("INTLLM_DATA_DIR"):
        os.environ["INTLLM_DATA_DIR"] = str(dirs["data"])
    # Alembic/migrations are frozen inside the exe; a file: URL is meaningless
    # there, so schema init in packaged mode uses metadata.create_all via the
    # db_init service (real SQL DDL against the configured PostgreSQL).
    os.environ.setdefault("INTLLM_LOG_LEVEL", "INFO")
    return dirs


# --- Logging -------------------------------------------------------------------


def _init_file_logging(settings, logs_dir: Path) -> None:
    """Add a rotating file handler next to the existing stdout handler.

    The redaction filter from app.core.logging applies to this handler too,
    so API keys / bearer tokens never reach disk.
    """
    import logging
    from logging.handlers import RotatingFileHandler

    from app.core.logging import _JsonFormatter, _RedactionFilter

    handler = RotatingFileHandler(
        logs_dir / "intllm.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_RedactionFilter())
    logging.getLogger().addHandler(handler)


# --- Database bootstrap ---------------------------------------------------------


def _bootstrap_database() -> None:
    """Initialize the local PostgreSQL schema before the server starts.

    PostgreSQL and pgvector stay external, honestly reported dependencies: an
    unavailable database does not crash the app, it is surfaced with the exact
    remediation step. Schema creation is real DDL (Alembic, or SQLAlchemy
    metadata when Alembic is not bundled into the frozen executable).
    """
    from app.services.system.db_init import initialize_database

    report = initialize_database()
    logger.info("database bootstrap", extra={"intllm_extra": report.as_dict()})
    if report.status != "running":
        print(f"[INTLLM] Database: {report.status}")
        if report.detail:
            print(f"[INTLLM]   {report.detail}")
        for action in report.actions:
            print(f"[INTLLM]   -> {action}")


# --- Port utilities -------------------------------------------------------------


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _looks_like_intllm(base_url: str) -> bool:
    """True when base_url answers like an INTLLM backend."""
    try:
        import httpx

        response = httpx.get(f"{base_url}/api/health", timeout=HEALTH_REQUEST_TIMEOUT_SECONDS)
        if response.status_code in (200, 503):
            payload = response.json()
            return payload.get("service") == "intllm" or "services" in payload
    except Exception:  # noqa: BLE001 - any failure means "not INTLLM"
        return False
    return False


def _resolve_port_conflict(settings) -> tuple[int, str | None]:
    """Return (port, notice). Connects to an existing INTLLM instance when found."""
    port = settings.intllm_port
    host = settings.intllm_host
    if not _port_in_use(host, port):
        return port, None

    candidate_base = f"http://{host}:{port}"
    if _looks_like_intllm(candidate_base):
        return port, (
            f"An INTLLM backend is already running on {candidate_base}; "
            "opening the existing instance instead of starting a duplicate."
        )

    # Port occupied by an unrelated program: try a small fallback range before
    # reporting a hard error. Never kill anything.
    for fallback in range(port + 1, port + 11):
        if not _port_in_use(host, fallback):
            return fallback, (
                f"Configured port {port} is occupied by another application; "
                f"INTLLM backend will use port {fallback} instead."
            )
    raise SystemExit(
        f"FATAL: configured port {port} and fallback ports {port + 1}-{port + 10} are all in use. "
        "Free a port or set INTLLM_PORT to a free port and relaunch."
    )


# --- Backend serving ------------------------------------------------------------


def _static_root() -> Path:
    """Locate the bundled frontend dist directory (PyInstaller layout aware)."""
    override = os.environ.get("INTLLM_STATIC_DIR")
    if override:
        candidate = Path(override)
        if candidate.is_dir():
            return candidate
    if getattr(sys, "frozen", False):  # running inside INTLLM.exe
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        for candidate in (meipass / "frontend", meipass / "dist"):
            if (candidate / "index.html").is_file():
                return candidate
    for candidate in (
        Path(__file__).resolve().parents[2] / "dist",  # repo checkout
        Path.cwd() / "dist",
    ):
        if (candidate / "index.html").is_file():
            return candidate
    raise SystemExit(
        "FATAL: frontend assets not found. Build the frontend (npm run build) "
        "and rebuild the executable, or set INTLLM_STATIC_DIR to the dist folder."
    )


def _serve_frontend_once_ready(base_url: str) -> None:
    """Wait for /api/health, then open the UI in the default browser.

    Uses stdlib urllib (no event loop involved) so the waiter thread can never
    interfere with uvicorn's asyncio loop on Windows.
    """
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(  # noqa: S310 - loopback, fixed URL scheme
                f"{base_url}/api/health", timeout=HEALTH_REQUEST_TIMEOUT_SECONDS
            ) as response:
                if response.status in (200, 503):
                    ui_url = f"{base_url}/app/"
                    logger.info(
                        "backend ready; opening UI",
                        extra={"intllm_extra": {"ui_url": ui_url}},
                    )
                    webbrowser.open(ui_url)
                    return
                last_error = f"HTTP {response.status}"
        except urllib.error.HTTPError as exc:  # still means the server is up
            if exc.code in (200, 503):
                webbrowser.open(f"{base_url}/app/")
                return
            last_error = f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001 - backend not up yet
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(HEALTH_POLL_SECONDS)
    logger.error(
        "backend did not become healthy in time; UI not opened automatically",
        extra={"intllm_extra": {"base_url": base_url, "last_error": last_error}},
    )


HELP_TEXT = """INTLLM - local-first AI runtime with an OpenAI-compatible API.

Usage:
  INTLLM-windows-x64.exe                 start the runtime and open the web UI
  INTLLM-windows-x64.exe --version       print the version and exit
  INTLLM-windows-x64.exe --help          print this help and exit

Configuration is via INTLLM_* environment variables (see README).
PostgreSQL and Ollama are external local dependencies that INTLLM detects
and reports honestly; neither is bundled or silently installed.
"""


def main() -> int:
    argv = sys.argv[1:]
    if "--version" in argv or "-V" in argv:
        print(f"INTLLM {_version()}")
        return 0
    if "--help" in argv or "-h" in argv:
        print(HELP_TEXT)
        return 0

    from app.config.settings import get_settings

    settings = get_settings()
    dirs = _ensure_dirs(settings)
    _init_file_logging(settings, dirs["logs"])

    logger.info(
        "INTLLM starting",
        extra={"intllm_extra": {"version": _version(), "data_dir": str(dirs["root"])}},
    )

    _bootstrap_database()

    port, notice = _resolve_port_conflict(settings)
    base_url = f"http://{settings.intllm_host}:{port}"
    if notice:
        logger.warning(notice)
        print(f"[INTLLM] {notice}")

    static_root = _static_root()
    os.environ["INTLLM_SERVE_STATIC"] = "1"
    os.environ["INTLLM_STATIC_ROOT"] = str(static_root)
    os.environ["INTLLM_EFFECTIVE_PORT"] = str(port)

    threading.Thread(target=_serve_frontend_once_ready, args=(base_url,), daemon=True).start()

    import uvicorn

    try:
        uvicorn.run(
            "app.main:app",
            host=settings.intllm_host,
            port=port,
            log_level=settings.intllm_log_level.lower(),
            # Pure-Python HTTP protocol: httptools' C extension does not
            # survive PyInstaller onefile bundling reliably and can accept
            # connections without ever answering them. h11 is dependable.
            http="h11",
            # SSE only; no WebSocket upgrade needed by the current frontend.
            ws="websockets" if _ws_available() else None,
            # The exe is a console app; Ctrl+C or closing the window shuts down.
            lifespan="on",
        )
    except KeyboardInterrupt:
        pass
    logger.info("INTLLM stopped")
    return 0


def _ws_available() -> bool:
    try:
        import websockets  # noqa: F401

        return True
    except ImportError:
        return False


def _version() -> str:
    from app import __version__

    return __version__


if __name__ == "__main__":
    sys.exit(main())
