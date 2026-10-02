"""INTLLM release build orchestrator.

Usage:
    python scripts/build_release.py                 # wheel + sdist (+ exe on Windows)
    python scripts/build_release.py --skip-windows  # portable/Linux CI
    python scripts/build_release.py --skip-python   # exe only

Artifacts land in ``build/release/`` together with a freshly generated
``SHA256.txt``. The version comes from ``backend/app/__init__.py`` — the single
source of truth — and is verified by the release workflow.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
RELEASE_DIR = ROOT / "build" / "release"


def project_version() -> str:
    text = (BACKEND / "app" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise SystemExit("could not read __version__ from backend/app/__init__.py")
    return match.group(1)


def run(command: list[str], cwd: Path) -> None:
    display = " ".join(command)
    print(f"$ {display}  (cwd={cwd})")
    result = subprocess.run(command, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise SystemExit(f"command failed ({result.returncode}): {display}")


def build_python(release_dir: Path) -> None:
    print("=== Building Python wheel + sdist")
    try:
        import build  # noqa: F401
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "build>=1.2.0"], ROOT)
    release_dir.mkdir(parents=True, exist_ok=True)
    run(
        [sys.executable, "-m", "build", "--outdir", str(release_dir), str(BACKEND)],
        ROOT,
    )


def build_windows(release_dir: Path) -> None:
    if sys.platform != "win32":
        print("=== Skipping Windows executable (not running on Windows)")
        return
    print("=== Building Windows x64 executable")
    # build_windows.py builds the frontend, runs tests + typecheck, packages the
    # exe and smoke-tests it (including SPA fallback).
    run([sys.executable, str(ROOT / "build_windows.py")], ROOT)


def find_iscc() -> str | None:
    """Locate Inno Setup's compiler on PATH or in its usual install dirs."""
    for name in ("iscc", "ISCC", "iscc.exe"):
        found = shutil.which(name)
        if found:
            return found

    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 7" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 7" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 7" / "ISCC.exe",
    ]
    for candidate in candidates:
        if str(candidate) and candidate.is_file():
            return str(candidate)
    return None


def copy_installers(release_dir: Path) -> None:
    """Copy the canonical installers into the release staging directory.

    They are published as release assets (and hashed) alongside the binary
    artifacts, exactly as served at https://intllm.vercel.app/install.*.
    """
    release_dir.mkdir(parents=True, exist_ok=True)
    for name in ("install.ps1", "install.sh"):
        source = ROOT / "IRM_INSTALL" / name
        if source.is_file():
            shutil.copy2(source, release_dir / name)
            print(f"=== Staged {name}")


def build_setup_installer(release_dir: Path, version: str) -> None:
    """Build INTLLM-Setup.exe when Inno Setup's compiler is available."""
    iscc = find_iscc()
    if not iscc:
        print("=== Skipping INTLLM-Setup.exe (Inno Setup 'iscc' not found)")
        return
    source_exe = release_dir / "INTLLM.exe"
    if not source_exe.is_file():
        print("=== Skipping INTLLM-Setup.exe (portable exe not built)")
        return
    print(f"=== Building INTLLM-Setup.exe with {iscc}")
    run(
        [
            iscc,
            f"/DAppVersion={version}",
            f"/DOutputDir={release_dir.resolve()}",
            str(ROOT / "IRM_INSTALL" / "INTLLM-Setup.iss"),
        ],
        ROOT / "IRM_INSTALL",
    )
    setup = release_dir / "INTLLM-Setup.exe"
    if not setup.is_file():
        raise SystemExit("Inno Setup did not produce INTLLM-Setup.exe")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build INTLLM release artifacts")
    parser.add_argument("--release-dir", default=str(RELEASE_DIR))
    parser.add_argument("--skip-python", action="store_true")
    parser.add_argument("--skip-windows", action="store_true")
    args = parser.parse_args(argv)

    release_dir = Path(args.release_dir)
    version = project_version()
    print(f"INTLLM release build — version {version}")
    print(f"Output: {release_dir}")

    if not args.skip_python:
        build_python(release_dir)
    if not args.skip_windows:
        build_windows(release_dir)
        build_setup_installer(release_dir, version)

    # Publish the canonical installers as release assets too.
    copy_installers(release_dir)

    # The .iss writes next to the exe; make sure everything shares one directory.
    run([sys.executable, str(ROOT / "scripts" / "make_sha256.py"), str(release_dir)], ROOT)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
