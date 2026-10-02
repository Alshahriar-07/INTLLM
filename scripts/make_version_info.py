"""Generate the PyInstaller Windows version-resource file.

Usage:
    python scripts/make_version_info.py <output-path>

The version is read from ``backend/app/__init__.py`` (the single source of
truth) so the executable's product/version metadata can never drift from the
package version. The output file is consumed by ``backend/INTLLM.spec``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "backend" / "app" / "__init__.py"

PRODUCT = "INTLLM"
DESCRIPTION = "INTLLM - Local Intelligence Runtime"
COMPANY = "Al Shahriar Sowan"
COPYRIGHT = "Copyright (C) 2026 Al Shahriar Sowan"


def project_version() -> str:
    text = INIT.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise SystemExit(f"could not read __version__ from {INIT}")
    return match.group(1)


def version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(p) for p in re.findall(r"\d+", version)[:4]]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)  # type: ignore[return-value]


def render(version: str) -> str:
    v = version_tuple(version)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={v},
    prodvers={v},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '{COMPANY}'),
          StringStruct('FileDescription', '{DESCRIPTION}'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', '{PRODUCT}'),
          StringStruct('LegalCopyright', '{COPYRIGHT}'),
          StringStruct('OriginalFilename', '{PRODUCT}.exe'),
          StringStruct('ProductName', '{PRODUCT}'),
          StringStruct('ProductVersion', '{version}'),
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main(argv: list[str]) -> int:
    output = Path(argv[1]) if len(argv) > 1 else ROOT / "build" / "INTLLM-version-info.txt"
    version = project_version()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(version), encoding="utf-8")
    print(f"wrote {output} (version {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
