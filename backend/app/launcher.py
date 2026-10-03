"""INTLLM shared startup helpers and headless launcher.

This module owns the pieces every startup path shares:

* per-user application directories (``%LOCALAPPDATA%\\INTLLM`` on Windows)
* rotating file logging with secret redaction
* database bootstrap
* port resolution that attaches to an existing INTLLM instance instead of
  starting a duplicate (and never kills unrelated processes)
* locating the bundled frontend build

The user-facing production entry point is :mod:`app.desktop`, which hosts the
INTLLM UI in a native window (no browser required). ``launcher.main`` delegates
to it so the packaged ``INTLLM.exe`` opens the desktop application.

Database and Ollama stay external, honestly reported dependencies:
the launcher never fabricates availability.
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.services.system.db_init import DatabaseReport

logger = get_logger(__name__)

APP_NAME = "INTLLM"  # data root: %LOCALAPPDATA%\\INTLLM
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


def _bootstrap_database() -> DatabaseReport:
    """Bring PostgreSQL up and initialize the local schema.

    Real startup sequence:

    1. ensure a local PostgreSQL is reachable — start the INTLLM-managed
       runtime when present (initdb on first run, pg_ctl start, loopback
       only) or a detected installed-but-stopped local service;
    2. initialize the schema (Alembic, or SQLAlchemy metadata DDL in the
       packaged executable) and verify every required table.

    An unavailable database never crashes the app: it is returned as an
    honest report with the exact remediation step.
    """
    from app.config.settings import get_settings
    from app.services.system.db_init import initialize_database
    from app.services.system.postgres_runtime import ensure_postgres_available

    runtime = ensure_postgres_available(get_settings())
    logger.info("postgres runtime", extra={"intllm_extra": runtime.as_dict()})
    if runtime.running:
        print(
            f"[INTLLM] PostgreSQL: {runtime.detail or 'connected'}"
            + (f" (127.0.0.1:{runtime.port})" if runtime.port else "")
        )

    report = initialize_database()
    # Merge the runtime outcome into the schema report so callers see one
    # honest picture (schema init never overwrites a real runtime failure).
    if report.status != "running" and runtime.mode == "unavailable":
        report.detail = report.detail or runtime.detail
        report.actions = [*report.actions, *runtime.actions]
    logger.info("database bootstrap", extra={"intllm_extra": report.as_dict()})
    if report.status != "running":
        category = f" ({report.category})" if report.category else ""
        print(f"[INTLLM] Database: {report.status}{category}")
        if report.detail:
            print(f"[INTLLM]   {report.detail}")
        for action in report.actions:
            print(f"[INTLLM]   -> {action}")
    return report


def shutdown_managed_postgres() -> None:
    """Stop the INTLLM-managed PostgreSQL cluster (desktop shutdown path)."""
    from app.services.system.postgres_runtime import managed_data_dir, stop_managed

    # Only stop the cluster this app instance owns; external servers and a
    # cluster another INTLLM instance is using are left alone.
    stop_managed(managed_data_dir())


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


def _version() -> str:
    from app import __version__

    return __version__


def main() -> int:
    """Packaged application entry point.

    The production experience is the desktop application (native window
    hosting the INTLLM UI). This delegates to :mod:`app.desktop` so that
    ``INTLLM.exe`` opens the desktop window rather than a browser.
    """
    from app.desktop import main as desktop_main

    return desktop_main()


if __name__ == "__main__":
    sys.exit(main())
