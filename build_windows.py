"""INTLLM Windows x64 build pipeline.

Reproducible one-command build:

    python build_windows.py

Steps (all real, no shortcuts):
  1. npm install + npm run build   -> production frontend in dist/
  2. python -m pytest (backend)    -> real test gate
  3. npm run lint (tsc typecheck)  -> real type gate
  4. PyInstaller --onefile         -> build/release/INTLLM-v<version>-win64x.exe
  5. verify the exe exists, is x64, and serves a working /api/health + SPA
     (headless desktop mode, no GUI window during the build)

The exe bundles the Python runtime + backend + frontend build + the native
desktop shell (pywebview/WebView2). Ollama and PostgreSQL remain external
dependencies that the app detects and reports honestly.
"""

from __future__ import annotations

import os
import re
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND_DIST = ROOT / "dist"
BUILD_DIR = ROOT / "build"
# Release output lives in build/release so the exe never collides with the
# frontend dist/ folder that Vite empties on every build.
RELEASE_DIR = ROOT / "build" / "release"

STEP_PREFIX = "\n=== "


def project_version() -> str:
    text = (BACKEND / "app" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise SystemExit("could not read __version__ from backend/app/__init__.py")
    return match.group(1)


def portable_exe_path(version: str) -> Path:
    return RELEASE_DIR / f"INTLLM-v{version}-win64x.exe"


def run(command: list[str] | str, cwd: Path, timeout: int = 1200) -> None:
    display = " ".join(command) if isinstance(command, list) else command
    print(f"{STEP_PREFIX}RUN{chr(32)}$ {display}  (cwd={cwd.relative_to(ROOT)})")
    # shell=True resolves npm.cmd/ssh-style shims on Windows and is harmless
    # for list commands on POSIX-style bash used by this repo.
    result = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    if result.returncode != 0:
        raise SystemExit(f"Build step failed (exit {result.returncode}): {display}")


def step_frontend() -> None:
    print(f"{STEP_PREFIX}1/5 Frontend production build")
    if not (ROOT / "node_modules").exists():
        run(["npm", "install"], ROOT)
    run(["npm", "run", "build"], ROOT)
    if not (FRONTEND_DIST / "index.html").is_file():
        raise SystemExit("Frontend build did not produce dist/index.html")


def step_backend_tests() -> None:
    print(f"{STEP_PREFIX}2/5 Backend tests")
    run([sys.executable, "-m", "pytest"], BACKEND)


def step_typecheck() -> None:
    print(f"{STEP_PREFIX}3/5 TypeScript check")
    run(["npm", "run", "lint"], ROOT)


def step_package(version: str) -> Path:
    print(f"{STEP_PREFIX}4/5 PyInstaller package (onefile)")
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"], BACKEND)
    try:
        import webview  # noqa: F401
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "pywebview>=5.0"], BACKEND)
    # Managed local PostgreSQL binaries (pgserver ships PostgreSQL + pgvector).
    try:
        import pgserver  # noqa: F401
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "pgserver>=0.1.4"], BACKEND)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    out_exe = portable_exe_path(version)
    if out_exe.exists():
        try:
            out_exe.unlink()
        except PermissionError:
            raise SystemExit(
                f"{out_exe} is locked (another INTLLM.exe is still running). "
                "Close it and retry."
            )
    BUILD_DIR.mkdir(exist_ok=True)
    # Windows version metadata for the exe, generated from __version__.
    run(
        [sys.executable, str(ROOT / "scripts" / "make_version_info.py"),
         str(BUILD_DIR / "INTLLM-version-info.txt")],
        ROOT,
    )
    run(
        [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath", str(RELEASE_DIR),
            "--workpath", str(BUILD_DIR / "intllm"),
            "INTLLM.spec",
        ],
        BACKEND,
    )
    # PyInstaller names the output from the spec ("INTLLM.exe"); rename it to
    # the versioned release asset name.
    produced = RELEASE_DIR / "INTLLM.exe"
    if not produced.is_file():
        raise SystemExit(f"{produced.name} was not produced")
    if produced != out_exe:
        if out_exe.exists():
            out_exe.unlink()
        produced.replace(out_exe)
    return out_exe


def exe_arch(path: Path) -> str:
    """Read the PE machine type from a Windows executable."""
    with path.open("rb") as fh:
        fh.seek(0x3C)
        pe_offset = struct.unpack("<I", fh.read(4))[0]
        fh.seek(pe_offset)
        if fh.read(4) != b"PE\0\0":
            return "not-a-pe"
        machine = struct.unpack("<H", fh.read(2))[0]
    return {0x8664: "x64 (AMD64)", 0xAA64: "ARM64", 0x14C: "x86"}.get(machine, hex(machine))


def step_smoke_test(out_exe: Path) -> None:
    print(f"{STEP_PREFIX}5/5 Executable smoke test")
    if not out_exe.is_file():
        raise SystemExit(f"{out_exe.name} was not produced")
    size_mb = out_exe.stat().st_size / (1024 * 1024)
    arch = exe_arch(out_exe)
    print(f"  exe: {out_exe.name}")
    print(f"  size: {size_mb:.1f} MB | arch: {arch}")
    if "x64" not in arch:
        raise SystemExit(f"Executable is not x64: {arch}")

    # Launch the real exe on a test port in headless desktop mode (no GUI
    # window during the build) and probe /api/health + the SPA fallback.
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", 8791)) == 0:
            raise SystemExit("Smoke test port 8791 busy; free it and retry")

    env = {
        **os.environ,
        "INTLLM_PORT": "8791",
        "INTLLM_DESKTOP_HEADLESS": "1",
    }
    log_path = BUILD_DIR / "smoke-test.log"
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [str(out_exe)],
            cwd=str(ROOT / "build"),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        base = "http://127.0.0.1:8791"
        try:
            deadline = time.time() + 90
            health = None
            last_error = "no response yet"
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen(f"{base}/api/health", timeout=10) as response:
                        health = response.status
                        break
                except urllib.error.HTTPError as exc:
                    # A degraded 503 is a valid, honest health response: the
                    # server is up, PostgreSQL/Ollama may simply be absent.
                    if exc.code in (200, 503):
                        health = exc.code
                        break
                    last_error = f"HTTP {exc.code}"
                except Exception as exc:  # noqa: BLE001 - backend not up yet
                    last_error = f"{type(exc).__name__}: {exc}"
                    if proc.poll() is not None:
                        raise SystemExit(
                            f"EXE exited during smoke test; log: {log_path}\n"
                            + log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
                        )
                    time.sleep(1)
            if health not in (200, 503):
                raise SystemExit(
                    f"/api/health did not respond correctly (got {health}, last error: {last_error}); "
                    f"log: {log_path}"
                )

            with urllib.request.urlopen(f"{base}/chat", timeout=5) as response:
                body = response.read().decode("utf-8", "replace")
                if "INTLLM" not in body or 'id="root"' not in body:
                    raise SystemExit("SPA fallback did not serve index.html for /chat")
            print("  /api/health OK, SPA fallback OK")
        finally:
            # Kill the whole process tree: a onefile PyInstaller app spawns a
            # child, and terminating only the bootloader would leave the child
            # running (and the exe locked) after the build.
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                )
            else:
                proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("  smoke test passed")


def main() -> int:
    version = project_version()
    out_exe = portable_exe_path(version)
    print(f"INTLLM Windows x64 build -> {out_exe.name}")
    step_frontend()
    step_backend_tests()
    step_typecheck()
    built = step_package(version)
    step_smoke_test(built)
    print(
        f"\nBUILD COMPLETE: {built.name} "
        f"({built.stat().st_size / (1024**2):.1f} MB, {exe_arch(built)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
