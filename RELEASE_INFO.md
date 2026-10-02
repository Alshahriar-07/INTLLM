# INTLLM Release Information

## Product

**INTLLM** — a local-first AI runtime for Ollama models with layered memory, live
retrieval, controlled tools, an Agent mode for coding work, and an
OpenAI-compatible local API.

- **Version:** 1.0.2
- **Release status:** Production release (Windows x64, Python package, source distribution)
- **Release date:** 2026-10-02
- **Website:** https://intllm.vercel.app
- **Repository:** https://github.com/Alshahriar-07/INTLLM
- **License:** PolyForm Noncommercial License 1.0.0
- **Copyright:** Copyright © 2026 Al Shahriar Sowan

## Supported platforms

| Platform | Support |
| --- | --- |
| Windows 10/11 x64 (AMD64) | Standalone executable + installer |
| Linux (x86_64 / aarch64) | Python wheel (`install.sh`) |
| macOS (x86_64 / arm64) | Python wheel (`install.sh`) |

Python 3.11+ is required for the wheel/CLI path.

## Artifacts

All artifacts are staged in `build/release/` and published to the GitHub Release.

| Artifact | Platform | Purpose |
| --- | --- | --- |
| `INTLLM.exe` | Windows x64 | Standalone application (PyInstaller single-file) |
| `INTLLM-Setup.exe` | Windows x64 | Windows installer (Inno Setup) |
| `intllm-1.0.2-py3-none-any.whl` | Python | PyPI / package installation |
| `intllm-1.0.2.tar.gz` | Python | Source distribution |
| `SHA256.txt` | All | Artifact verification |
| `install.ps1` | Windows | Automated installation |
| `install.sh` | Unix-like | Automated installation |

## Installation

### Windows (PowerShell)

```powershell
irm https://intllm.vercel.app/install.ps1 | iex
```

Or run `INTLLM-Setup.exe` directly.

### Linux / macOS

```bash
curl -fsSL https://intllm.vercel.app/install.sh | bash
```

### Python package

```bash
python -m pip install intllm
```

## CLI commands

```text
intllm                 start the local runtime and open the web UI
intllm start           same as above
intllm serve           run the API server only
intllm doctor          check PostgreSQL, pgvector and Ollama readiness
intllm --version       print the version
intllm --help          print help
```

## PyPI information

- **Package name:** `intllm`
- **Version:** 1.0.2
- **Publishing:** PyPI Trusted Publishing (OIDC) via `.github/workflows/pypi.yml`
- **Artifacts:** `intllm-1.0.2-py3-none-any.whl`, `intllm-1.0.2.tar.gz`

## Requirements

- **Ollama** installed and running with at least one model pulled
  (`https://ollama.com`). Not bundled.
- **PostgreSQL 14+** with the **pgvector** extension. Not bundled.
  Default URL: `postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm`
  (`INTLLM_DATABASE_URL`).
- Python 3.11+ for the wheel/CLI path.

INTLLM detects these dependencies and reports their state honestly
(`connected` / `degraded` / `unavailable` / `offline`).

## API

Local OpenAI-compatible API:

```text
GET  /v1/models
GET  /v1/models/{model}
POST /v1/chat/completions     # stream: false | true (SSE)
```

Authenticate with `Authorization: Bearer intllm_…` or `x-api-key: intllm_…`.
API keys are created in Settings → API; only a salted scrypt hash and a
fingerprint are stored, and the full key is shown once.

## Agent Mode

Agent Mode adds workspace-scoped coding capabilities to Chat:

- **Workspace** — the selected folder is the Agent's filesystem boundary.
- **Sandbox** — every path is resolved against the workspace and escapes are
  rejected (`403`). The workspace root cannot be deleted.
- **Permissions** — overwrite, delete, move and terminal execution require an
  explicit approval decision; `allow_session` grants suppress repeat prompts for
  harmless repeated work.
- **Terminal** — commands run through the backend with the workspace as the
  working directory and a configurable timeout; commands referencing paths
  outside the workspace are flagged.

## Known limitations

- Ollama and PostgreSQL are external and must be installed by the user; INTLLM
  does not bundle or silently install them.
- `/v1/embeddings`, `/v1/responses`, audio, images, files, batches and
  fine-tuning are **not** implemented.
- Model-driven autonomous tool-calling in Agent Mode is **not yet wired**; the
  Agent runtime is driven through the Agent API / UI.
- A browsable public model catalog is not provided; the model list is the real
  Ollama inventory.
- No third-party CLI compatibility is claimed unless verified against a build.
- The Windows installer was compiled and statically validated (PE header, version
  metadata, payload and license page), but a live install/uninstall was **not**
  executed in this environment because it would modify the current user's PATH
  and per-user locations. Run `INTLLM-Setup.exe` interactively, or
  `INTLLM-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`, to install.

## Testing status

| Check | Result |
| --- | --- |
| Backend unit tests (`pytest`) | 80 passed, 6 skipped (DB integration tests skip without `INTLLM_TEST_DATABASE_URL`) |
| Frontend typecheck (`tsc --noEmit`) | passed |
| Frontend production build (`vite build`) | passed |
| Windows executable build (`build_windows.py`) | built — 34.0 MB, x64 (AMD64), icon + version metadata |
| Executable smoke test (`/api/health`, SPA fallback) | passed |
| Executable runtime checks (`/`, `/api/health`, `/api/models`, `/api/agent/status`, `/chat`, `/v1/models`) | passed (real Ollama inventory; honest `503 degraded` with PostgreSQL down) |
| Executable CLI (`INTLLM.exe --version` / `--help`) | passed (`INTLLM 1.0.2`) |
| Wheel + sdist build | built; `twine check` PASSED |
| Wheel install + console script (`intllm --version` / `--help`) | passed |
| sdist independent rebuild | passed (builds both wheel and sdist) |
| Windows installer (`INTLLM-Setup.exe`) | built with Inno Setup 6, version metadata + payload verified; **install/uninstall not executed at runtime** (would modify the user's PATH and profile) |
| SHA256 (`SHA256.txt`) | generated from the real artifacts and re-verified independently |
| PostgreSQL / pgvector live integration | not available in this environment (reported honestly at runtime) |
| Ollama live integration | detected and reported correctly (models listed) |

See the Stage 2 release report for exact commands and outputs.

## License

**PolyForm Noncommercial License 1.0.0**

Copyright © 2026 Al Shahriar Sowan

Licensed under the PolyForm Noncommercial License 1.0.0. This is a
source-available, noncommercial license; commercial use is not permitted under
these terms. The full license text is in [`LICENSE`](LICENSE).
