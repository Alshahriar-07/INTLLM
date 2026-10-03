"""Validate a built INTLLM release directory.

Usage:
    python scripts/validate_release.py build/release [--install-check] [--require-exe]

Checks:
  * wheel + source archive exist and are named with the project version
  * Windows artifacts exist (when --require-exe is passed)
  * SHA256.txt exists and every listed hash matches the file on disk
  * (--install-check) the wheel installs into a throwaway venv and both
    ``intllm --version`` and ``intllm --help`` succeed

Exits non-zero with a clear message on the first failure.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(f"VALIDATION FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def verify_manifest(release_dir: Path) -> None:
    manifest = release_dir / "SHA256.txt"
    if not manifest.is_file():
        fail("SHA256.txt is missing")
    listed: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            fail(f"malformed SHA256.txt line: {line!r}")
        listed[parts[1].strip()] = parts[0].strip().lower()

    for name, expected in listed.items():
        target = release_dir / name
        if not target.is_file():
            fail(f"SHA256.txt lists {name} but the file is missing")
        actual = sha256_file(target)
        if actual != expected:
            fail(f"hash mismatch for {name}: expected {expected}, got {actual}")
    print(f"  checksums: verified {len(listed)} artifact(s)")


def check_names(release_dir: Path, require_exe: bool) -> None:
    wheels = sorted(release_dir.glob("intllm-*.whl"))
    sdists = sorted(release_dir.glob("intllm-*.tar.gz"))
    if len(wheels) != 1:
        fail(f"expected exactly one wheel, found {[w.name for w in wheels]}")
    if len(sdists) != 1:
        fail(f"expected exactly one source archive, found {[s.name for s in sdists]}")
    print(f"  wheel:  {wheels[0].name}")
    print(f"  sdist:  {sdists[0].name}")

    if require_exe:
        portable = sorted(release_dir.glob("INTLLM-v*-win64x.exe"))
        setups = sorted(release_dir.glob("INTLLM-v*-Setup.exe"))
        if len(portable) != 1:
            fail(f"expected exactly one portable exe, found {[p.name for p in portable]}")
        if len(setups) != 1:
            fail(f"expected exactly one setup installer, found {[s.name for s in setups]}")
        for path in (*portable, *setups):
            if path.stat().st_size == 0:
                fail(f"Windows artifact is empty: {path.name}")
            print(f"  exe:    {path.name}")

    return wheels[0]


def install_check(wheel: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp) / "venv"
        venv.create(env_dir, with_pip=True)
        scripts = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
        python = scripts / ("python.exe" if sys.platform == "win32" else "python")

        install = subprocess.run(
            [str(python), "-m", "pip", "install", "--no-deps", "--quiet", str(wheel)],
            capture_output=True,
            text=True,
        )
        if install.returncode != 0:
            fail(f"pip install of {wheel.name} failed:\n{install.stderr}")

        cli = scripts / ("intllm.exe" if sys.platform == "win32" else "intllm")
        if not cli.is_file():
            fail("the wheel did not install an 'intllm' console script")

        for args in (["--version"], ["--help"]):
            result = subprocess.run([str(cli), *args], capture_output=True, text=True)
            if result.returncode != 0 or not result.stdout.strip():
                fail(f"`intllm {' '.join(args)}` failed:\n{result.stdout}\n{result.stderr}")
        print("  install: wheel installs; intllm --version/--help OK")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate INTLLM release artifacts")
    parser.add_argument("release_dir", nargs="?", default="build/release")
    parser.add_argument("--install-check", action="store_true")
    parser.add_argument("--require-exe", action="store_true")
    args = parser.parse_args(argv)

    release_dir = Path(args.release_dir)
    if not release_dir.is_dir():
        fail(f"release directory does not exist: {release_dir}")

    print(f"Validating {release_dir} ...")
    wheel = check_names(release_dir, args.require_exe)
    verify_manifest(release_dir)
    if args.install_check:
        install_check(wheel)
    print("Release validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
