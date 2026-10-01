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
    "app.main",
    "anyio._backends._asyncio",
    "httpx",
    "h11",
    "psutil",
]

datas = [
    # Production frontend build, served by FastAPI from the packaged exe.
    ("../dist", "frontend"),
]
# Package metadata some libraries probe at runtime.
datas += collect_data_files("pydantic")

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
    name="INTLLM-windows-x64",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # console app: visible window doubles as shutdown control
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
