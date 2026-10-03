"""INTLLM-managed local PostgreSQL runtime.

INTLLM is local-first: chat history, memory and API keys live in a local
PostgreSQL with pgvector. On a machine without a PostgreSQL installation,
INTLLM provisions and manages its **own** local PostgreSQL runtime inside its
per-user data directory — nothing cloud, nothing remote:

* binaries are located from an explicit override, the ``pgserver`` package
  (which ships PostgreSQL + pgvector binaries) or the directory bundled into
  the packaged executable;
* the data directory is initialized once with ``initdb`` (only ever created,
  never dropped or reset);
* the server is started with ``pg_ctl`` bound to ``127.0.0.1`` only;
* readiness is verified with a real TCP + SQL connection before the runtime
  reports success.

If the user already runs a PostgreSQL on the configured endpoint, INTLLM uses
it (external mode) and never starts a second server. If the user pinned a
custom ``INTLLM_DATABASE_URL``, only external detection/start is attempted.

Nothing in this module fabricates availability: every failure returns a report
with the actual error and actionable steps.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

IS_WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Managed runtime defaults. These are local-only credentials for the
# INTLLM-owned instance; the server listens on 127.0.0.1 only.
MANAGED_USER = "intllm"
MANAGED_PASSWORD = "intllm"
MANAGED_DATABASE = "intllm"
DEFAULT_PORT = 5432
PORT_SCAN_RANGE = 64  # 5433..5496 as fallbacks

START_TIMEOUT_SECONDS = 60.0
STOP_TIMEOUT_SECONDS = 30.0

MODE_MANAGED = "managed"
MODE_EXTERNAL = "external"
MODE_UNAVAILABLE = "unavailable"

_RUNTIME_FILE = "runtime.json"
_SERVER_LOG = "server.log"


@dataclass
class PostgresRuntimeReport:
    """Honest snapshot of the PostgreSQL runtime subsystem."""

    mode: str = MODE_UNAVAILABLE  # managed | external | unavailable
    running: bool = False
    host: str = "127.0.0.1"
    port: int | None = None
    database: str | None = None
    data_dir: str | None = None
    binaries_dir: str | None = None
    started_by_us: bool = False
    detail: str | None = None
    actions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


# --- Locations ---------------------------------------------------------------


def _app_data_root() -> Path:
    """Per-user application data root (mirrors launcher.app_data_dir)."""
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
        return Path(base) / "INTLLM"
    if sys.platform == "darwin":
        return Path("~/Library/Application Support/INTLLM").expanduser()
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / "INTLLM"


def managed_data_dir() -> Path:
    """Directory holding the INTLLM-managed PostgreSQL cluster."""
    return _app_data_root() / "postgres"


def _pgdata(managed_dir: Path | None = None) -> Path:
    return (managed_dir or managed_data_dir()) / "data"


def _runtime_state_path(managed_dir: Path | None = None) -> Path:
    return (managed_dir or managed_data_dir()) / _RUNTIME_FILE


def _server_log_path(managed_dir: Path | None = None) -> Path:
    return (managed_dir or managed_data_dir()) / _SERVER_LOG


def binaries_dir() -> Path | None:
    """Locate a PostgreSQL server binaries directory.

    Order: INTLLM_PG_BINDIR override -> the pgserver package (PostgreSQL +
    pgvector binaries) -> directory bundled into the packaged executable
    (``postgres/`` next to the frozen app). Returns None when unavailable.
    """
    override = os.environ.get("INTLLM_PG_BINDIR", "").strip()
    if override:
        candidate = Path(override)
        if (candidate / _server_binary_name()).is_file():
            return candidate
        logger.warning("INTLLM_PG_BINDIR does not contain a postgres binary: %s", override)

    try:
        import pgserver

        candidate = Path(pgserver.__file__).resolve().parent / "pginstall" / "bin"
        if (candidate / _server_binary_name()).is_file():
            return candidate
    except ImportError:
        pass

    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        for candidate in (meipass / "postgres" / "bin", meipass / "postgres"):
            if (candidate / _server_binary_name()).is_file():
                return candidate
    return None


def _server_binary_name() -> str:
    return "postgres.exe" if IS_WINDOWS else "postgres"


def _tool(bin_dir: Path, name: str) -> Path:
    return bin_dir / (f"{name}.exe" if IS_WINDOWS else name)


def pg_version(bin_dir: Path | None) -> str | None:
    """PostgreSQL version string from the located binaries (None if absent)."""
    if bin_dir is None:
        return None
    try:
        result = subprocess.run(
            [str(_tool(bin_dir, "postgres")), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW if IS_WINDOWS else 0,
            check=False,
        )
        output = (result.stdout or "").strip()
        return output or None
    except Exception:  # noqa: BLE001 - best-effort diagnostics only
        return None


# --- TCP / SQL probes --------------------------------------------------------


def _tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((host, port)) == 0
    except OSError:
        return False


def _probe_sql(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    timeout: float = 4.0,
) -> tuple[bool, str | None]:
    """Try a real SQL connection; returns (ok, error). Never raises."""
    try:
        import asyncpg

        async def _connect() -> None:
            connection = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                timeout=timeout,
            )
            await connection.close()

        import asyncio

        asyncio.run(_connect())
        return True, None
    except Exception as exc:  # noqa: BLE001 - classified by the caller
        return False, f"{type(exc).__name__}: {exc}"


def _free_port(host: str, preferred: int) -> int:
    """Return a free TCP port on host, preferring `preferred`."""
    candidates = [preferred, *(range(preferred + 1, preferred + 1 + PORT_SCAN_RANGE))]
    for port in candidates:
        if not 1 <= port <= 65535:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                return port
        except OSError:
            continue
    # Last resort: let the OS assign one.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


# --- Managed state persistence -----------------------------------------------


def _read_runtime_state(managed_dir: Path) -> dict[str, object]:
    try:
        return json.loads(_runtime_state_path(managed_dir).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - missing/corrupt file is not fatal
        return {}


def _write_runtime_state(managed_dir: Path, state: dict[str, object]) -> None:
    try:
        managed_dir.mkdir(parents=True, exist_ok=True)
        _runtime_state_path(managed_dir).write_text(
            json.dumps(state, indent=2), encoding="utf-8"
        )
    except Exception as exc:  # noqa: BLE001 - diagnostics only
        logger.warning("could not persist postgres runtime state: %s", exc)


# --- External-install detection ------------------------------------------------


def _windows_postgres_services() -> list[dict[str, str]]:
    """Installed Windows services that look like PostgreSQL servers."""
    services: list[dict[str, str]] = []
    try:
        import psutil

        for service in psutil.win_service_iter():
            info = service.as_dict()
            name = (info.get("name") or "").lower()
            display = (info.get("display_name") or "").lower()
            if "postgres" in name or "pgsql" in name or "postgres" in display:
                services.append(
                    {
                        "name": info.get("name") or "",
                        "display_name": info.get("display_name") or "",
                        "state": (info.get("status") or "").lower(),
                    }
                )
    except Exception:  # noqa: BLE001 - enumeration is best-effort
        pass
    return services


def _try_start_windows_service(service_name: str) -> tuple[bool, str | None]:
    try:
        result = subprocess.run(
            ["sc", "start", service_name],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - returned to the caller
        return False, str(exc)
    if result.returncode == 0:
        return True, None
    output = f"{result.stdout or ''} {result.stderr or ''}"
    if "5" in output and "ACCESS" in output.upper():  # access denied (error 5)
        return False, "access denied (administrator rights required)"
    return False, (result.stdout or result.stderr or f"sc exit {result.returncode}").strip()


def _detect_and_start_external(settings, report: PostgresRuntimeReport) -> PostgresRuntimeReport:
    """Detect an installed (but stopped) local PostgreSQL and try to start it."""
    from urllib.parse import unquote, urlparse

    parsed = urlparse(settings.intllm_database_url.replace("+asyncpg", "").replace("+psycopg", ""))
    host = parsed.hostname or "127.0.0.1"
    port = int(parsed.port or DEFAULT_PORT)

    services = _windows_postgres_services() if IS_WINDOWS else []
    started_any = False
    errors: list[str] = []
    for service in services:
        if service["state"] in ("running", "start_pending"):
            started_any = True
            continue
        if service["state"] in ("stopped", "paused"):
            ok, error = _try_start_windows_service(service["name"])
            if ok:
                started_any = True
            else:
                errors.append(f"{service['name']}: {error}")

    # Give the service a moment, then re-probe.
    if started_any:
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            if _tcp_open(host, port, timeout=1.0):
                ok, _ = _probe_sql(host, port, parsed.username or MANAGED_USER,
                                   unquote(parsed.password or ""), "postgres")
                if ok:
                    report.mode = MODE_EXTERNAL
                    report.running = True
                    report.port = port
                    report.detail = "Started the installed local PostgreSQL service."
                    return report
            time.sleep(1.0)

    report.mode = MODE_UNAVAILABLE
    report.actions = []
    if services:
        report.detail = (
            "A local PostgreSQL installation was found but the service could not be started."
        )
        report.actions.extend(
            [
                "Start the PostgreSQL service manually (Services app or "
                "`sc start <service>` as administrator).",
                *(f"Service error: {error}" for error in errors[:3]),
            ]
        )
    else:
        report.detail = "No PostgreSQL server is reachable and none is installed."
        report.actions = [
            "INTLLM can use its own managed PostgreSQL automatically when its "
            "runtime is available, or you can install PostgreSQL 14+ with the "
            "pgvector extension (https://www.postgresql.org/download/).",
        ]
    return report


# --- Managed runtime -----------------------------------------------------------


def _initdb_if_needed(bin_dir: Path, managed_dir: Path) -> tuple[bool, str | None]:
    """Run initdb when the data directory is fresh. Never touches existing data."""
    data = _pgdata(managed_dir)
    if (data / "PG_VERSION").is_file():
        return True, None
    managed_dir.mkdir(parents=True, exist_ok=True)
    pwfile = managed_dir / ".initpw"
    pwfile.write_text(MANAGED_PASSWORD, encoding="ascii")
    try:
        result = subprocess.run(
            [
                str(_tool(bin_dir, "initdb")),
                "-D",
                str(data),
                "-U",
                MANAGED_USER,
                "-A",
                "scram-sha-256",
                "--pwfile",
                str(pwfile),
                "-E",
                "UTF8",
                "--locale=C",
                "--no-instructions",
            ],
            capture_output=True,
            text=True,
            timeout=180,
            creationflags=CREATE_NO_WINDOW if IS_WINDOWS else 0,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced in the report
        return False, f"initdb failed: {type(exc).__name__}: {exc}"
    finally:
        try:
            pwfile.unlink(missing_ok=True)
        except OSError:
            pass
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-3:]
        return False, "initdb failed: " + " | ".join(tail)
    logger.info("initialized managed PostgreSQL data directory", extra={"intllm_extra": {"path": str(data)}})
    return True, None


def _start_managed(bin_dir: Path, managed_dir: Path, port: int) -> tuple[bool, str | None]:
    """Start the managed server via pg_ctl (waits for readiness)."""
    data = _pgdata(managed_dir)
    log_path = _server_log_path(managed_dir)
    try:
        result = subprocess.run(
            [
                str(_tool(bin_dir, "pg_ctl")),
                "-D",
                str(data),
                "-l",
                str(log_path),
                "-w",
                "-t",
                str(int(START_TIMEOUT_SECONDS)),
                "-o",
                f"-c listen_addresses=127.0.0.1 -p {port}",
                "start",
            ],
            capture_output=True,
            text=True,
            timeout=START_TIMEOUT_SECONDS + 30,
            creationflags=CREATE_NO_WINDOW if IS_WINDOWS else 0,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced in the report
        return False, f"pg_ctl start failed: {type(exc).__name__}: {exc}"
    if result.returncode != 0:
        tail = _log_tail(log_path)
        return False, f"pg_ctl start failed: {(result.stderr or result.stdout).strip() or tail}"
    return True, None


def _log_tail(log_path: Path, lines: int = 5) -> str:
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        return " | ".join(content[-lines:])
    except OSError:
        return ""


def _managed_url(port: int) -> tuple[str, str]:
    """(async URL, sync URL) for the managed cluster on the given port."""
    async_url = (
        f"postgresql+asyncpg://{MANAGED_USER}:{MANAGED_PASSWORD}"
        f"@127.0.0.1:{port}/{MANAGED_DATABASE}"
    )
    sync_url = (
        f"postgresql+psycopg://{MANAGED_USER}:{MANAGED_PASSWORD}"
        f"@127.0.0.1:{port}/{MANAGED_DATABASE}"
    )
    return async_url, sync_url


def _apply_database_override(async_url: str, sync_url: str) -> None:
    """Point the runtime at the managed cluster for this process.

    Updates both the environment (fresh Settings instances) and the cached
    settings object (get_settings() is memoized).
    """
    os.environ["INTLLM_DATABASE_URL"] = async_url
    os.environ["INTLLM_DATABASE_URL_SYNC"] = sync_url
    try:
        from app.config.settings import get_settings

        settings = get_settings()
        settings.intllm_database_url = async_url
        settings.intllm_database_url_sync = sync_url
    except Exception:  # noqa: BLE001 - settings not constructed yet is fine
        pass


def stop_managed(managed_dir: Path | None = None, timeout: float = STOP_TIMEOUT_SECONDS) -> bool:
    """Stop the INTLLM-managed PostgreSQL cluster (fast mode). True if stopped."""
    directory = managed_dir or managed_data_dir()
    bin_dir = binaries_dir()
    data = _pgdata(directory)
    if not (data / "postmaster.pid").is_file() and not (data / "PG_VERSION").is_file():
        return True  # nothing to stop
    if bin_dir is None:
        logger.warning("cannot stop managed PostgreSQL: binaries not found")
        return False
    try:
        result = subprocess.run(
            [
                str(_tool(bin_dir, "pg_ctl")),
                "-D",
                str(data),
                "-m",
                "fast",
                "-w",
                "-t",
                str(int(timeout)),
                "stop",
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 15,
            creationflags=CREATE_NO_WINDOW if IS_WINDOWS else 0,
            check=False,
        )
        stopped = result.returncode == 0
    except Exception as exc:  # noqa: BLE001
        logger.warning("pg_ctl stop failed: %s", exc)
        stopped = False
    if stopped:
        logger.info("managed PostgreSQL stopped")
    else:
        logger.warning("managed PostgreSQL did not stop cleanly")
    return stopped


def ensure_postgres_available(settings) -> PostgresRuntimeReport:
    """Make sure a local PostgreSQL is reachable; provision INTLLM's own if needed.

    Idempotent and safe to call from any startup path (desktop launcher, CLI
    serve, FastAPI lifespan). Never raises; the report always reflects reality.
    """
    from urllib.parse import unquote, urlparse

    report = PostgresRuntimeReport()

    parsed = urlparse(
        settings.intllm_database_url.replace("+asyncpg", "").replace("+psycopg", "")
    )
    host = parsed.hostname or "127.0.0.1"
    url_port = int(parsed.port or DEFAULT_PORT)
    url_user = parsed.username or MANAGED_USER
    url_password = unquote(parsed.password or "")
    url_database = (parsed.path or "").lstrip("/") or MANAGED_DATABASE
    report.host = host
    report.database = url_database

    custom_url = "intllm_database_url" in getattr(settings, "model_fields_set", set())

    # 1. Is something already answering on the configured endpoint?
    if _tcp_open(host, url_port):
        ok, error = _probe_sql(host, url_port, url_user, url_password, "postgres")
        if ok:
            report.mode = MODE_EXTERNAL
            report.running = True
            report.port = url_port
            report.detail = "Connected to the configured PostgreSQL server."
            return report
        # Reachable but our credentials/database do not work yet. If this is
        # the INTLLM-managed cluster, provisioning can continue (it may still
        # be starting or the database may not exist yet - db_init creates it).
        state = _read_runtime_state(managed_data_dir())
        is_ours = bool(state) and state.get("port") == url_port and host == "127.0.0.1"
        if not (is_ours or not custom_url):
            report.mode = MODE_UNAVAILABLE
            report.detail = f"PostgreSQL refused the configured credentials: {error}"
            report.actions = [
                "Verify the username/password/database in INTLLM_DATABASE_URL.",
                "Create the role/database, or remove INTLLM_DATABASE_URL to let "
                "INTLLM use its own managed PostgreSQL.",
            ]
            return report

    # 2. User pinned a custom URL: external only. Detect + try to start services.
    if custom_url:
        return _detect_and_start_external(settings, report)

    # 3. Default URL, nothing usable on 5432: use INTLLM's managed runtime.
    bin_dir = binaries_dir()
    if bin_dir is None:
        return _detect_and_start_external(settings, report)

    managed_dir = managed_data_dir()
    state = _read_runtime_state(managed_dir)
    preferred_port = int(state.get("port") or url_port)

    # Attach to an already-running managed instance when possible.
    if _tcp_open("127.0.0.1", preferred_port):
        ok, _ = _probe_sql(
            "127.0.0.1", preferred_port, MANAGED_USER, MANAGED_PASSWORD, "postgres"
        )
        if ok:
            async_url, sync_url = _managed_url(preferred_port)
            _apply_database_override(async_url, sync_url)
            report.mode = MODE_MANAGED
            report.running = True
            report.port = preferred_port
            report.data_dir = str(managed_dir)
            report.binaries_dir = str(bin_dir)
            report.detail = "Reattached to the INTLLM-managed PostgreSQL."
            return report

    # Fresh start: initdb (first run only) then pg_ctl start on a free port.
    ok, error = _initdb_if_needed(bin_dir, managed_dir)
    if not ok:
        report.mode = MODE_UNAVAILABLE
        report.data_dir = str(managed_dir)
        report.detail = error
        report.actions = [
            "Check the INTLLM data directory permissions, or delete the "
            f"'{managed_dir}' folder to re-initialize the managed database."
        ]
        return report

    port = _free_port("127.0.0.1", preferred_port)
    ok, error = _start_managed(bin_dir, managed_dir, port)
    if not ok:
        report.mode = MODE_UNAVAILABLE
        report.data_dir = str(managed_dir)
        report.binaries_dir = str(bin_dir)
        report.detail = error or "The managed PostgreSQL did not start."
        report.actions = [
            f"Check the server log: {_server_log_path(managed_dir)}",
            f"PostgreSQL version: {pg_version(bin_dir) or 'unknown'}",
        ]
        return report

    ok, error = _probe_sql(
        "127.0.0.1", port, MANAGED_USER, MANAGED_PASSWORD, "postgres"
    )
    if not ok:
        report.mode = MODE_UNAVAILABLE
        report.data_dir = str(managed_dir)
        report.detail = f"Managed PostgreSQL started but is not answering yet: {error}"
        report.actions = [
            "Click Retry; if it persists, check the server log at "
            f"{_server_log_path(managed_dir)}."
        ]
        return report

    _write_runtime_state(
        managed_dir,
        {
            "port": port,
            "user": MANAGED_USER,
            "database": MANAGED_DATABASE,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "pid": None,
        },
    )
    async_url, sync_url = _managed_url(port)
    _apply_database_override(async_url, sync_url)
    report.mode = MODE_MANAGED
    report.running = True
    report.port = port
    report.started_by_us = True
    report.data_dir = str(managed_dir)
    report.binaries_dir = str(bin_dir)
    report.detail = f"INTLLM-managed PostgreSQL ready on 127.0.0.1:{port}."
    logger.info(
        "managed PostgreSQL ready",
        extra={"intllm_extra": {"port": port, "data_dir": str(managed_dir)}},
    )
    return report
