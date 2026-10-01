"""Generate SHA256.txt for a release directory.

Usage:
    python scripts/make_sha256.py [release_dir]

Hashes every regular file in the directory except SHA256.txt itself, writing
``<sha256>  <filename>`` lines sorted by filename. This is the single place
checksums are produced, so CI and local builds never hand-type hashes.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def generate(release_dir: Path) -> Path:
    if not release_dir.is_dir():
        raise SystemExit(f"release directory does not exist: {release_dir}")
    files = sorted(
        path for path in release_dir.iterdir() if path.is_file() and path.name != "SHA256.txt"
    )
    if not files:
        raise SystemExit(f"no artifacts to hash in {release_dir}")
    lines = [f"{sha256_file(path)}  {path.name}" for path in files]
    manifest = release_dir / "SHA256.txt"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str]) -> int:
    release_dir = Path(argv[1]) if len(argv) > 1 else Path("build/release")
    manifest = generate(release_dir)
    print(manifest.read_text(encoding="utf-8"), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
