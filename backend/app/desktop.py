"""INTLLM desktop application (Windows production entry point).

This is the real desktop shell used by the packaged ``INTLLM.exe``. It does not
open an external browser: it hosts the existing INTLLM web UI inside a native
window backed by the OS WebView2 runtime (via pywebview).

Startup sequence (PLAN stage 5, part 4):

1. initialize configuration and per-user application directories
2. initialize rotating file logging (never logs secrets)
3. bootstrap the local PostgreSQL schema
4. apply the persisted local/LAN API access mode
5. resolve the backend port (connect to an existing INTLLM instance instead of
   starting a duplicate; never kill unrelated processes)
6. start the real FastAPI backend in a background thread
7. show a startup window with live service readiness (PostgreSQL / Ollama /
   backend), with Retry and "Continue anyway" when a dependency is missing
8. load the INTLLM UI into the window once the backend is ready
9. shut the backend down cleanly when the window closes

PostgreSQL and Ollama remain external, honestly reported dependencies. Nothing
here fabricates availability.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

APP_TITLE = "INTLLM — Local Intelligence Runtime"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 840
MIN_WINDOW_WIDTH = 960
MIN_WINDOW_HEIGHT = 600

# How long to wait for the backend to answer before declaring startup failed.
# /api/health probes PostgreSQL and Ollama; when a dependency is unreachable
# its connect probe can take several seconds, so this stays well above that
# or the readiness waiter never sees the (valid) 200/503 response.
STARTUP_TIMEOUT_SECONDS = 60.0
POLL_INTERVAL_SECONDS = 0.5
PROBE_TIMEOUT_SECONDS = 12.0

# The startup window: a self-contained readiness screen with no network access
# of its own. Python pushes state in through ``window.__intllm.setStatus``.
SPLASH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>INTLLM</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body {
    background: #0b0d10; color: #e7eaee;
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    display: flex; align-items: center; justify-content: center;
    -webkit-user-select: none; user-select: none;
  }
  .card { width: min(560px, 88vw); }
  .brand { display: flex; align-items: center; gap: 14px; margin-bottom: 28px; }
  .mark {
    width: 44px; height: 44px; border-radius: 11px; flex: none;
    background: linear-gradient(135deg, #2b6cff, #7aa2ff);
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 19px; color: #fff; letter-spacing: .5px;
  }
  .brand h1 { font-size: 21px; margin: 0; font-weight: 600; letter-spacing: .3px; }
  .brand p { margin: 2px 0 0; font-size: 12.5px; color: #8b95a5; }
  .status { list-style: none; margin: 0; padding: 0; }
  .status li {
    display: flex; align-items: center; gap: 12px;
    padding: 13px 15px; border: 1px solid #1b2028; border-radius: 10px;
    margin-bottom: 9px; background: #10141a;
  }
  .dot { width: 9px; height: 9px; border-radius: 50%; flex: none; background: #57606f; }
  .dot.connected { background: #3fb950; box-shadow: 0 0 0 3px rgba(63,185,80,.16); }
  .dot.unavailable, .dot.offline { background: #f85149; box-shadow: 0 0 0 3px rgba(248,81,73,.16); }
  .dot.degraded { background: #d29922; box-shadow: 0 0 0 3px rgba(210,153,34,.16); }
  .dot.checking { background: #d29922; animation: pulse 1.1s ease-in-out infinite; }
  @keyframes pulse { 0%,100% { opacity: .35; } 50% { opacity: 1; } }
  .name { font-size: 13.5px; font-weight: 600; min-width: 108px; }
  .detail { font-size: 12px; color: #8b95a5; margin-left: auto; text-align: right;
            max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .note { margin-top: 20px; font-size: 12.5px; color: #8b95a5; line-height: 1.55; }
  .note.error { color: #f0a7a1; }
  .actions { margin-top: 22px; display: flex; gap: 10px; }
  button {
    font: inherit; font-size: 13px; padding: 9px 18px; border-radius: 8px;
    border: 1px solid #2a3140; background: #1a2029; color: #e7eaee; cursor: pointer;
  }
  button.primary { background: #2b6cff; border-color: #2b6cff; }
  button:hover { filter: brightness(1.12); }
  .hidden { display: none !important; }
  .spinner {
    width: 14px; height: 14px; border: 2px solid #2a3140; border-top-color: #7aa2ff;
    border-radius: 50%; animation: spin .8s linear infinite; margin-left: auto;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
  <div class="card">
    <div class="brand">
      <div class="mark">IL</div>
      <div>
        <h1>INTLLM</h1>
        <p>Local Intelligence Runtime</p>
      </div>
    </div>
    <ul class="status" id="status"></ul>
    <div class="note" id="note">Starting local services…</div>
    <div class="actions hidden" id="actions">
      <button class="primary" id="retry">Retry</button>
      <button id="continue">Continue anyway</button>
    </div>
  </div>
<script>
  function render(state) {
    const list = document.getElementById('status');
    const note = document.getElementById('note');
    const actions = document.getElementById('actions');
    list.innerHTML = '';
    (state.services || []).forEach(function (svc) {
      const li = document.createElement('li');
      const dot = document.createElement('span');
      dot.className = 'dot ' + (svc.status || 'checking');
      const name = document.createElement('span');
      name.className = 'name';
      name.textContent = svc.name;
      li.appendChild(dot);
      li.appendChild(name);
      if (svc.detail) {
        const detail = document.createElement('span');
        detail.className = 'detail';
        detail.textContent = svc.detail;
        detail.title = svc.detail;
        li.appendChild(detail);
      }
      if (svc.status === 'checking') {
        const spinner = document.createElement('span');
        spinner.className = 'spinner';
        li.appendChild(spinner);
      }
      list.appendChild(li);
    });
    note.textContent = state.note || '';
    note.className = 'note' + (state.failed ? ' error' : '');
    actions.className = state.failed ? 'actions' : 'actions hidden';
  }
  window.__intllm = { setStatus: render };
  document.getElementById('retry').addEventListener('click', function () {
    if (window.pywebview && window.pywebview.api) window.pywebview.api.retry();
  });
  document.getElementById('continue').addEventListener('click', function () {
    if (window.pywebview && window.pywebview.api) window.pywebview.api.continue_anyway();
  });
</script>
</body>
</html>
"""


def _ensure_std_streams() -> None:
    """Make print() safe in a windowed (noconsole) executable.

    A PyInstaller ``console=False`` build has no stdout/stderr by default, so
    ``print()`` would raise. When the process was launched *from a terminal*
    (e.g. ``INTLLM.exe --version`` during install verification) we attach to
    that console so the output is visible; otherwise (double-click launch) we
    discard it. Either way no console window is shown.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    if sys.platform == "win32":
        try:
            import ctypes

            # ATTACH_PARENT_PROCESS = -1: reuse the launching console if present.
            if ctypes.windll.kernel32.AttachConsole(-1):
                sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                return
        except Exception:  # noqa: BLE001 - fall through to devnull
            pass
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


class _Bridge:
    """JS API exposed to the startup window (Retry / Continue anyway)."""

    def __init__(self, app: DesktopApp) -> None:
        self._app = app

    def retry(self) -> bool:
        self._app.request_retry()
        return True

    def continue_anyway(self) -> bool:
        self._app.continue_anyway()
        return True


class DesktopApp:
    def __init__(self) -> None:
        self.window: Any = None
        self._server: Any = None
        self._server_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._retry = threading.Event()
        self._continue = threading.Event()
        self._owns_backend = False
        self._port: int | None = None
        self._base_url: str | None = None

    # --- window updates ---------------------------------------------------
    def _set_status(self, state: dict[str, Any]) -> None:
        if self.window is None:
            return
        try:
            payload = json.dumps(state)
            self.window.evaluate_js(f"window.__intllm && window.__intllm.setStatus({payload});")
        except Exception as exc:  # noqa: BLE001 - a closed window is not fatal
            logger.debug("could not update startup window: %s", exc)

    def request_retry(self) -> None:
        self._retry.set()

    def continue_anyway(self) -> None:
        self._continue.set()

    # --- backend lifecycle ------------------------------------------------
    def _start_backend(self, settings) -> None:
        import uvicorn

        config = uvicorn.Config(
            "app.main:app",
            host=settings.api_bind_host,
            port=self._port,
            log_level=settings.intllm_log_level.lower(),
            # Pure-Python HTTP protocol: httptools' C extension does not survive
            # PyInstaller onefile bundling reliably.
            http="h11",
            ws="websockets" if _ws_available() else None,
            lifespan="on",
        )
        server = uvicorn.Server(config)
        # Not the main thread: signal handlers cannot be installed here.
        server.install_signal_handlers = lambda: None  # type: ignore[assignment]
        self._server = server
        self._owns_backend = True
        self._server_thread = threading.Thread(
            target=server.run, name="intllm-backend", daemon=True
        )
        self._server_thread.start()

    def _stop_backend(self) -> None:
        if self._server is not None:
            try:
                self._server.should_exit = True
            except Exception:  # noqa: BLE001
                pass
        if self._server_thread is not None:
            self._server_thread.join(timeout=15)
            if self._server_thread.is_alive():
                logger.warning("backend thread did not stop within 15s")
        self._server = None
        self._server_thread = None

    # --- readiness probing ------------------------------------------------
    def _probe(self) -> tuple[bool, dict[str, Any]]:
        """Return (backend_ready, status_state). Never fabricates a state."""
        import urllib.error
        import urllib.request

        base = self._base_url
        assert base is not None
        try:
            with urllib.request.urlopen(
                f"{base}/api/health", timeout=PROBE_TIMEOUT_SECONDS
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return True, _state_from_health(payload, backend="Ready")
        except urllib.error.HTTPError as exc:
            # A degraded 503 is a valid, honest health response.
            if exc.code in (200, 503):
                try:
                    payload = json.loads(exc.read().decode("utf-8"))
                    return True, _state_from_health(payload, backend="Ready")
                except Exception:  # noqa: BLE001
                    return True, _state_from_health({}, backend="Ready")
            return False, _waiting_state(f"HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001 - backend not up yet
            return False, _waiting_state(f"{type(exc).__name__}")

    def _autostart_ollama(self) -> None:
        """Start the installed Ollama daemon if it is not running yet."""

        def _worker() -> None:
            try:
                import asyncio

                from app.services.ollama import process as ollama_process

                running, _ = asyncio.run(ollama_process.is_running())
                if running:
                    return
                result = asyncio.run(ollama_process.start())
                logger.info(
                    "ollama autostart",
                    extra={"intllm_extra": {k: v for k, v in result.items() if k != "error"}},
                )
                if result.get("error"):
                    # Not fatal: the startup window reports Ollama as offline.
                    logger.warning("ollama autostart failed: %s", result["error"])
            except Exception as exc:  # noqa: BLE001 - never block startup
                logger.warning("ollama autostart error: %s", exc)

        threading.Thread(target=_worker, name="intllm-ollama-autostart", daemon=True).start()

    def _monitor(self) -> None:
        """Push live status to the window, then load the UI when ready.

        Implements real retry: when the user clicks Retry, we re-bootstrap the
        database and wait for the backend to become ready again.
        """
        self._monitor_loop(deadline=time.monotonic() + STARTUP_TIMEOUT_SECONDS)

    def _monitor_loop(self, deadline: float) -> None:
        """Core monitoring loop. Returns when UI is loaded or app is stopping."""
        while not self._stop.is_set():
            ready, state = self._probe()
            if ready:
                postgres = _service_status(state, "PostgreSQL")
                ollama = _service_status(state, "Ollama")

                # Check if PostgreSQL is actually ready (not just that backend responds)
                db_ready = postgres in ("connected", "running")

                if not db_ready:
                    # PostgreSQL is not ready - show proper error state
                    self._set_status(
                        {
                            **state,
                            "failed": True,
                            "note": self._postgres_error_note(state),
                        }
                    )
                    # Wait for user action (retry or continue)
                    self._wait_for_user_action()
                    if self._stop.is_set():
                        return

                    if self._continue.is_set():
                        # User chose to continue despite PostgreSQL issues
                        self._load_ui()
                        return

                    if self._retry.is_set():
                        # Real retry: re-bootstrap database and try again
                        self._retry.clear()
                        self._continue.clear()
                        self._perform_real_retry()
                        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
                        continue

                    continue

                # Backend and PostgreSQL are ready
                self._load_ui()
                return

            # Backend not ready yet
            self._set_status(state)
            if time.monotonic() >= deadline:
                self._set_status(
                    {
                        "services": state["services"],
                        "failed": True,
                        "note": (
                            "The INTLLM backend did not become ready in time. "
                            "Check the log file in the INTLLM data folder, then Retry."
                        ),
                    }
                )
                self._retry.clear()
                self._continue.clear()
                self._wait_for_user_action()
                if self._stop.is_set():
                    return
                if self._continue.is_set():
                    self._load_ui()
                    return
                if self._retry.is_set():
                    self._retry.clear()
                    self._continue.clear()
                    self._perform_real_retry()
                    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
                    continue
            time.sleep(POLL_INTERVAL_SECONDS)

    def _postgres_error_note(self, state: dict) -> str:
        """Generate a helpful error note about PostgreSQL status."""
        postgres = _service_status(state, "PostgreSQL")
        if postgres == "checking":
            return "Checking PostgreSQL connection…"

        # The database endpoint comes from INTLLM_DATABASE_URL, not from the
        # backend's own bind address.
        db_endpoint = _database_endpoint()

        # Try to get more details from the health endpoint
        services = state.get("services", [])
        pg_service = next((s for s in services if s.get("name") == "PostgreSQL"), None)
        detail = pg_service.get("detail") if pg_service else None

        if postgres == "offline":
            if detail and "connection refused" in str(detail).lower():
                return (
                    f"PostgreSQL is not reachable at {db_endpoint}. INTLLM starts its own "
                    "managed PostgreSQL automatically when available. Click Retry to "
                    "run the full recovery sequence, or continue with a degraded session."
                )
            return (
                f"PostgreSQL is not reachable at {db_endpoint}. Click Retry to run the "
                "full recovery sequence, or continue with a degraded session."
            )
        elif postgres == "unavailable":
            return (
                f"PostgreSQL: {detail or 'Not available'}. "
                "Click Retry to attempt recovery, or continue with a degraded session."
            )
        elif postgres == "degraded":
            return (
                f"PostgreSQL: {detail or 'Degraded'}. "
                "Click Retry to attempt recovery, or continue with limited functionality."
            )
        return (
            "PostgreSQL is not ready. Chat history, memory and the API key store need it. "
            "Click Retry to run the full recovery sequence, or continue with a degraded session."
        )

    def _wait_for_user_action(self) -> None:
        """Wait for the user to click Retry or Continue anyway."""
        self._retry.clear()
        self._continue.clear()
        while not self._stop.is_set():
            if self._retry.is_set():
                return
            if self._continue.is_set():
                return
            time.sleep(0.2)

    def _perform_real_retry(self) -> None:
        """Perform a real retry: recover PostgreSQL (managed runtime included),
        re-bootstrap the schema and restart the backend when needed."""
        logger.info("performing retry: full database recovery")
        try:
            from app.config.settings import get_settings
            from app.launcher import _bootstrap_database, _resolve_port_conflict
            from app.services.api_server.service import apply_persisted_access_mode

            settings = get_settings()

            # Full recovery: managed PostgreSQL provisioning / external service
            # start + schema initialization. Reports honestly on failure.
            db_report = _bootstrap_database()
            logger.info(
                "retry database bootstrap result",
                extra={"intllm_extra": db_report.as_dict()}
            )
            self._db_ready = db_report.status == "running"
            self._db_report = db_report

            # Re-apply persisted access mode
            apply_persisted_access_mode()

            # Update effective port in case settings changed
            port, _ = _resolve_port_conflict(settings)
            if port != self._port:
                logger.info(f"port changed on retry: {self._port} -> {port}")
                self._port = port
                self._base_url = f"http://{settings.intllm_host}:{port}"
                os.environ["INTLLM_EFFECTIVE_PORT"] = str(port)

                # Restart backend on new port if we own it
                if self._owns_backend:
                    self._stop_backend()
                    self._start_backend(settings)

        except Exception as exc:
            logger.error(f"retry failed: {exc}", exc_info=True)

    def _load_ui(self) -> None:
        if self.window is None or self._base_url is None:
            return
        logger.info("desktop UI ready", extra={"intllm_extra": {"url": self._base_url}})
        try:
            # Root serves the SPA (index.html fallback) in packaged mode.
            self.window.load_url(f"{self._base_url}/")
        except Exception as exc:  # noqa: BLE001
            logger.error("failed to load the UI: %s", exc)

    # --- entry point ------------------------------------------------------
    def run(self) -> int:
        argv = sys.argv[1:]
        if "--version" in argv or "-V" in argv:
            print(f"INTLLM {_version()}")
            return 0
        if "--help" in argv or "-h" in argv:
            print(HELP_TEXT)
            return 0

        from app.config.settings import get_settings
        from app.launcher import (
            _bootstrap_database,
            _ensure_dirs,
            _init_file_logging,
            _looks_like_intllm,
            _port_in_use,
            _resolve_port_conflict,
            _static_root,
        )

        settings = get_settings()
        dirs = _ensure_dirs(settings)
        _init_file_logging(settings, dirs["logs"])
        logger.info(
            "INTLLM desktop starting",
            extra={"intllm_extra": {"version": _version(), "data_dir": str(dirs["root"])}},
        )

        # Initialize database first - this is critical for the app to function.
        db_report = _bootstrap_database()
        db_ready = db_report.status == "running"

        # Start Ollama when it is installed but not running (real process
        # control, verified against the daemon health endpoint). Runs in the
        # background so a slow start never blocks the startup window.
        self._autostart_ollama()

        from app.services.api_server.service import apply_persisted_access_mode

        apply_persisted_access_mode()
        settings = get_settings()

        port, notice = _resolve_port_conflict(settings)
        self._port = port
        self._base_url = f"http://{settings.intllm_host}:{port}"
        if notice:
            logger.warning(notice)

        static_root = _static_root()
        os.environ["INTLLM_SERVE_STATIC"] = "1"
        os.environ["INTLLM_STATIC_ROOT"] = str(static_root)
        os.environ["INTLLM_EFFECTIVE_PORT"] = str(port)

        # If a healthy INTLLM backend is already running, attach to it instead
        # of starting a duplicate (never kill unrelated processes).
        existing = _port_in_use(settings.intllm_host, port) and _looks_like_intllm(
            self._base_url
        )
        if not existing:
            self._start_backend(settings)

        # Headless verification mode: the packaged build's backend + bundled
        # frontend are exercised without opening a GUI window. Used by
        # build_windows.py's smoke test; never the user-facing path.
        if os.environ.get("INTLLM_DESKTOP_HEADLESS") == "1":
            return self._run_headless()

        try:
            import webview
        except ImportError:
            # No native webview backend (e.g. a Linux/macOS wheel installed
            # without the `desktop` extra). Be honest: serve headless and print
            # the local URL instead of failing.
            print(
                "[INTLLM] No desktop webview backend is available; serving the "
                "backend headlessly."
            )
            print(f"[INTLLM] Open {self._base_url}/ in a browser.")
            return self._run_headless(announce=False)

        import webview

        self.window = webview.create_window(
            APP_TITLE,
            html=SPLASH_HTML,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT),
            js_api=_Bridge(self),
            background_color="#0b0d10",
        )
        # Store DB readiness for the monitor thread
        self._db_ready = db_ready
        self._db_report = db_report
        threading.Thread(target=self._monitor, name="intllm-readiness", daemon=True).start()

        try:
            webview.start()
        finally:
            self._stop.set()
            if self._owns_backend:
                self._stop_backend()
            # Stop the PostgreSQL cluster this app instance started. External
            # servers and clusters another instance is using are left alone.
            try:
                from app.launcher import shutdown_managed_postgres

                shutdown_managed_postgres()
            except Exception as exc:  # noqa: BLE001 - shutdown must never crash
                logger.warning("managed PostgreSQL shutdown skipped: %s", exc)
            logger.info("INTLLM desktop stopped")
        return 0


    def _run_headless(self, *, announce: bool = True) -> int:
        """Serve the backend without a window until the process is terminated."""
        assert self._base_url is not None
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            ready, _state = self._probe()
            if ready:
                if announce:
                    print(f"[INTLLM] desktop headless smoke ready at {self._base_url}")
                break
            time.sleep(POLL_INTERVAL_SECONDS)
        else:
            print("[INTLLM] desktop headless smoke: backend did not become ready")
            return 1
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            if self._owns_backend:
                self._stop_backend()
        return 0


def _database_endpoint() -> str:
    """Human-readable endpoint of the configured PostgreSQL server."""
    try:
        from urllib.parse import urlparse

        from app.config.settings import get_settings

        parsed = urlparse(
            get_settings().intllm_database_url.replace("+asyncpg", "").replace("+psycopg", "")
        )
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        database = parsed.database or "intllm"
        return f"{host}:{port}/{database}"
    except Exception:  # noqa: BLE001 - diagnostics only
        return "127.0.0.1:5432"


def _service_status(state: dict[str, Any], name: str) -> str:
    for service in state.get("services", []):
        if service.get("name") == name:
            return str(service.get("status", ""))
    return ""


def _waiting_state(detail: str) -> dict[str, Any]:
    return {
        "services": [
            {"name": "PostgreSQL", "status": "checking", "detail": "waiting for backend"},
            {"name": "Ollama", "status": "checking", "detail": "waiting for backend"},
            {"name": "INTLLM Backend", "status": "checking", "detail": detail},
        ],
        "note": "Starting local services…",
        "failed": False,
    }


def _state_from_health(payload: dict[str, Any], *, backend: str) -> dict[str, Any]:
    """Translate the /api/health payload into startup-window rows."""
    services = payload.get("services") or {}

    def row(label: str, key: str) -> dict[str, Any]:
        entry = services.get(key) or {}
        status = str(entry.get("status") or "checking")
        return {"name": label, "status": status, "detail": entry.get("detail")}

    return {
        "services": [
            row("PostgreSQL", "postgres"),
            row("Ollama", "ollama"),
            {"name": "INTLLM Backend", "status": "connected", "detail": backend},
        ],
        "note": "Backend ready.",
        "failed": False,
    }


def _ws_available() -> bool:
    try:
        import websockets  # noqa: F401

        return True
    except ImportError:
        return False


def _version() -> str:
    from app import __version__

    return __version__


HELP_TEXT = """INTLLM - local-first AI runtime with an OpenAI-compatible API.

Usage:
  INTLLM.exe                 open the INTLLM desktop application
  INTLLM.exe --version       print the version and exit
  INTLLM.exe --help          print this help and exit

The desktop application starts the local backend, PostgreSQL and Ollama checks
and hosts the INTLLM UI in a native window (no browser required).

Configuration is via INTLLM_* environment variables (see CONFIGURATION.md).
PostgreSQL and Ollama are external local dependencies that INTLLM detects and
reports honestly; neither is bundled or silently installed.
"""


def main() -> int:
    _ensure_std_streams()
    return DesktopApp().run()


if __name__ == "__main__":
    sys.exit(main())
