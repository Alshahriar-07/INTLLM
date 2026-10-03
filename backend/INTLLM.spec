# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the INTLLM Windows x64 single-file executable.

Build (from the repo root):
    python build_windows.py

or manually:
    cd backend && pyinstaller --noconfirm --distpath ../build/release --workpath ../build/intllm INTLLM.spec

The spec bundles:
  - the real FastAPI backend (app package, uvicorn, sqlalchemy, asyncpg, psutil)
  - the production frontend build (dist/ -> frontend/ inside the exe)

Ollama and PostgreSQL are NOT bundled: they are external local dependencies
that INTLLM detects and reports honestly.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    *collect_submodules("sqlalchemy"),
    *collect_submodules("asyncpg"),
    *collect_submodules("app"),
    "app.launcher",
    "app.desktop",
    "app.main",
    "anyio._backends._asyncio",
    "httpx",
    "h11",
    "psutil",
    # Native desktop window (WebView2 via pywebview / pythonnet).
    "webview",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr_loader",
    "pythonnet",
]

# pywebview loads its JS API shim from disk at runtime; bundle it explicitly.
from PyInstaller.utils.hooks import collect_data_files as _collect_data_files

datas = list(_collect_data_files("webview"))

datas += [
    # Production frontend build, served by FastAPI from the packaged exe.
    ("../dist", "frontend"),
]
# Package metadata some libraries probe at runtime.
datas += collect_data_files("pydantic")

# --- INTLLM-managed local PostgreSQL -----------------------------------------
# The app provisions its own local PostgreSQL (pgvector included) inside the
# per-user data directory. Binaries come from the `pgserver` package when it
# is installed at build time; without it the app falls back to external
# detection with clear setup guidance (never a fabricated status).
try:
    from pathlib import Path as _Path

    import pgserver as _pgserver

    _pg_install = _Path(_pgserver.__file__).resolve().parent / "pginstall"
    if _pg_install.is_dir():
        datas.append((str(_pg_install), "postgres"))
        hiddenimports += ["pgserver", "pgserver.utils"]
        print(f"spec: bundling managed PostgreSQL binaries from {_pg_install}")
    else:
        print("spec: WARNING pgserver found but pginstall/ is missing")
except ImportError:
    print("spec: pgserver not installed; building without managed PostgreSQL binaries")

# uvicorn's httptools C extension misbehaves when frozen (accepts connections
# but never answers them); the launcher forces h11, so the httptools protocol
# module is excluded from the bundle entirely.
excludes = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pytest",
    "playwright",
    "pynvml",
    "alembic",
    "uvicorn.protocols.http.httptools_impl",
]

a = Analysis(
    ["app/launcher.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="INTLLM",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    # Windowed app: no console window. The desktop window is the application.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Application icon and Windows version metadata (generated from __version__).
    icon="../assets/ico/INTLLM.ico",
    version="../build/INTLLM-version-info.txt",
)
