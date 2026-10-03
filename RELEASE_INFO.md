# INTLLM Release Information

## Product

**INTLLM** — a local-first AI runtime for Ollama models with layered memory, live
retrieval, controlled tools, an Agent mode for coding work, and an
OpenAI-compatible local API, delivered as a native Windows desktop application.

- **Version:** 1.1.0 (single source of truth: `backend/app/__init__.py`)
- **Release status:** Production release — packaged application built and
  validated end-to-end against a live PostgreSQL (pgvector) and a live Ollama
- **Release date:** 2026-10-03
- **Website:** https://intllm.vercel.app
- **Repository:** https://github.com/Alshahriar-07/INTLLM
- **License:** PolyForm Noncommercial License 1.0.0
- **Copyright:** Copyright © 2026 Al Shahriar Sowan

## Supported platforms

| Platform | Support |
| --- | --- |
| Windows 10/11 x64 (AMD64) | Portable desktop executable + installer (native window, WebView2) |
| Linux (x86_64 / aarch64) | Python wheel (`install.sh`) |
| macOS (x86_64 / arm64) | Python wheel (`install.sh`) |

Python 3.11+ is required for the wheel/CLI path.

## Artifacts

All artifacts are staged in `build/release/` and published to the GitHub Release.

| Artifact | Platform | Purpose |
| --- | --- | --- |
| `INTLLM-v1.1.0-win64x.exe` | Windows x64 | Portable desktop application (PyInstaller single-file) |
| `INTLLM-v1.1.0-Setup.exe` | Windows x64 | Windows installer (Inno Setup 6) |
| `intllm-1.1.0-py3-none-any.whl` | Python | PyPI / package installation |
| `intllm-1.1.0.tar.gz` | Python | Source distribution |
| `install.ps1` | Windows | Automated installation |
| `install.sh` | Unix-like | Automated installation |
| `SHA256.txt` | All | SHA-256 checksums of every artifact above |

## Installation

### Windows (PowerShell)

```powershell
irm https://intllm.vercel.app/install.ps1 | iex
```

Or run `INTLLM-v1.1.0-Setup.exe` directly, or use the portable
`INTLLM-v1.1.0-win64x.exe` with no installation.

### Linux / macOS

```bash
curl -fsSL https://intllm.vercel.app/install.sh | bash
```

### Python package

```bash
python -m pip install intllm
```

## Desktop application behavior

Launching `INTLLM-v1.1.0-win64x.exe` (or the installed `INTLLM` shortcut):

1. starts the local FastAPI backend on a real localhost TCP port
   (`127.0.0.1`, conflict-resolved, never a browser tab);
2. provisions/detects local PostgreSQL — including the INTLLM-managed runtime
   (bundled binaries, loopback-only) — and applies the schema/migrations;
3. starts the installed Ollama daemon when it is not running and detects the
   models that are actually installed;
4. shows live readiness (PostgreSQL / Ollama / backend) with a working Retry,
   then loads the INTLLM UI into a native window; and
5. shuts the backend and any managed PostgreSQL cluster it owns down cleanly
   when the window closes.

The root URL serves the application shell (SPA); `/api/*`, `/v1/*` and
`/health`/`/ready` remain pure JSON API routes.

## CLI commands

```text
intllm                 start the local runtime and open the desktop app
intllm start           same as above
intllm serve           run the API server only
intllm doctor          check PostgreSQL, pgvector and Ollama readiness
intllm --version       print the version
intllm --help          print help
```

## PyPI information

- **Package name:** `intllm`
- **Version:** 1.1.0
- **Publishing:** PyPI Trusted Publishing (OIDC) via `.github/workflows/pypi.yml`
- **Artifacts:** `intllm-1.1.0-py3-none-any.whl`, `intllm-1.1.0.tar.gz`

## Requirements

- **Ollama** installed with at least one model pulled (`https://ollama.com`).
  Not bundled. INTLLM starts the daemon when installed but not running.
- **PostgreSQL 14+** with the **pgvector** extension. When no local server is
  reachable, INTLLM uses its own managed local PostgreSQL runtime when its
  binaries are available (packaged build); otherwise it reports exactly what
  is missing. Default URL: `postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm`
  (`INTLLM_DATABASE_URL`).
- Python 3.11+ for the wheel/CLI path.

## API

Local OpenAI-compatible API:

```text
GET  /v1/models
GET  /v1/models/{model}
POST /v1/chat/completions     # stream: false | true (SSE)
```

`/v1/models` returns the real Ollama inventory. `/v1/chat/completions`
validates the requested model, resolves it against Ollama and returns an
OpenAI-compatible response. Authenticate with `Authorization: Bearer intllm_…`
or `x-api-key: intllm_…`. API keys are created in Settings → API; only a salted
scrypt hash and a fingerprint are stored, and the full key is shown once.
Access is loopback-only by default; LAN exposure is an explicit opt-in that
still requires a key.

## Agent Mode

Agent Mode adds workspace-scoped coding capabilities to Chat:

- **Workspace** — the selected folder is the Agent's filesystem boundary
  (native folder picker with manual-path fallback, persisted locally).
- **Real tool loop** — the local model proposes JSON tool calls
  (`fs.list`, `fs.read`, `fs.search`, `fs.write`, `fs.edit`, `fs.mkdir`,
  `fs.delete`, `fs.move`, `terminal`); INTLLM validates each call, applies the
  permission gate, executes it for real and feeds the result back until the
  model produces a final answer. Verified live end-to-end with
  `qwen2.5-coder:7b`.
- **Sandbox** — every path is resolved against the workspace; traversal,
  absolute paths, drive and UNC escapes are rejected (`403`). The workspace
  root cannot be deleted.
- **Permissions** — Allow / Ask Me. In Ask Me, workspace-changing operations
  (including terminal) pause for an explicit Allow/Deny. Reads run freely.
- **Terminal** — real async subprocess execution with the workspace as cwd,
  stdout/stderr capture, exit code, duration, timeout, cancellation and
  output tailing.
- **Bounded context** — file reads are size-limited (binary files return
  metadata only), search skips `.git`/`node_modules`/etc., terminal output is
  tailed, and tool transcripts are truncated before re-entering the model.

## Known limitations

- Ollama is external and must be installed by the user; INTLLM does not bundle
  or silently install it (it does start it when present).
- `/v1/embeddings`, `/v1/responses`, audio, images, files, batches and
  fine-tuning are **not** implemented.
- Agent permission-mode persistence and workspace persistence are stored in
  local PostgreSQL (`app_settings`) and require the database to be ready.
- No third-party CLI compatibility is claimed unless verified against a build.

## Testing status (this release)

| Check | Result |
| --- | --- |
| Backend unit tests (`pytest`) | 131 passed, 8 skipped (DB integration tests skip without `INTLLM_TEST_DATABASE_URL`) |
| Backend lint (`ruff check`) | 0 errors, 0 warnings (66 style findings are informational; no F/E9 class errors) |
| Frontend typecheck (`tsc --noEmit`) | passed |
| Frontend production build (`vite build`) | passed (code-split: app chunk ~111 kB, vendor chunks cached separately) |
| Windows executable build (`build_windows.py`) | built — 50.4 MB, x64 (AMD64), icon + version metadata |
| Packaged EXE end-to-end | health `ok` with **PostgreSQL connected, memory connected, Ollama connected**; `/` and `/app/` serve the SPA; `/api/models` returned the real installed inventory (`gemma3:4b`, `qwen2.5-coder:7b`); chat streamed a real Ollama completion and persisted it to PostgreSQL |
| Live model registry sync | passed (real Ollama metadata incl. 3.1–4.5 GB sizes, fixed via BIGINT migration) |
| Live chat pipeline (dev backend) | passed (SSE stream → PostgreSQL history; conversations survive backend restart) |
| Live Agent run (real model) | passed (read file → write file → final answer in 23 s; file verified on disk) |
| Agent terminal | passed (`python --version` → real stdout, exit 0, 262 ms) |
| Workspace sandbox | passed (`../secret.txt` and absolute `C:\Users\...` both rejected) |
| Memory store | passed (create + search + stats via PostgreSQL/pgvector; survives restart) |
| OpenAI-compatible API | passed (`/v1/models` real inventory; `/v1/chat/completions` real completion from `gemma3:4b` with key auth) |
| Wheel + sdist build | built; wheel installs into a clean venv; `intllm --version` / `--help` pass |
| Windows installer (`INTLLM-v1.1.0-Setup.exe`) | built with Inno Setup 6 (successful compile); **interactive install/uninstall not executed** in this environment because it would modify the current user's PATH and per-user locations — run it interactively or with `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` |
| SHA256 (`SHA256.txt`) | generated from the real artifacts and re-verified independently (6/6 match) |
| Ollama live integration | detected and exercised for real (version 0.34.2; generation verified) |

## License

**PolyForm Noncommercial License 1.0.0**

Copyright © 2026 Al Shahriar Sowan

Licensed under the PolyForm Noncommercial License 1.0.0. This is a
source-available, noncommercial license; commercial use is not permitted under
these terms. The full license text is in [`LICENSE`](LICENSE).
