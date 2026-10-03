# INTLLM

**A local-first AI runtime that turns compatible local models into a richer intelligence environment — layered memory, persistent chat history, live retrieval, controlled tools, an Agent mode for coding work, and an OpenAI-compatible local API — delivered as a native desktop application.**

INTLLM runs on your machine. Conversations, model weights, embeddings and vector memory stay local by default. Nothing is sent to a cloud service unless you explicitly enable live web retrieval for a request.

**Current version: 1.1.0** — see [`RELEASE.md`](RELEASE.md) and [`CHANGELOG.md`](CHANGELOG.md).

---

## What INTLLM is

Local models are good reasoning engines, but they have no memory of *your* context, no access to *current* information, and no API surface your other tools can use. INTLLM does not retrain the base model for every new fact. It supplies the surrounding runtime:

```text
User
 ↓
INTLLM Desktop App (native window, embedded UI)
 ↓
INTLLM Runtime
 ├── L0 Flash Brain        fast memory index
 ├── L1 Hot Cache          short-lived promoted context
 ├── L2 Secondary Brain    durable vector store (PostgreSQL + pgvector)
 ├── Chat history          persistent conversations (PostgreSQL)
 ├── Live Web retrieval     optional, per-request, source-attributed
 ├── Tool Gateway           validated, permission-gated tools
 ├── Agent runtime          workspace-scoped files/terminal (Chat → Agent mode)
 ├── Model Manager          real Ollama inventory + Potato/Medium/High filters
 └── Local OpenAI API       /v1 with INTLLM API keys
 ↓
Ollama
 ↓
Local model
```

The golden rule: **user responses always have priority**; background maintenance yields resources to interactive requests.

## The desktop application

INTLLM v1.1.0 ships as a **real desktop application**, not a browser tab. Launching `INTLLM.exe`:

1. initializes configuration and per-user data directories,
2. bootstraps the local PostgreSQL schema,
3. checks PostgreSQL, Ollama and the backend, showing live status in a startup window,
4. starts the local FastAPI backend internally on `127.0.0.1`,
5. hosts the INTLLM UI **inside a native window** (WebView2 on Windows), and
6. shuts the backend down cleanly when the window closes.

The local backend still runs on localhost internally — that is an implementation detail. **You never have to open a browser URL** to use INTLLM. If PostgreSQL or Ollama is missing, the startup window shows exactly what is wrong and offers **Retry** / **Continue anyway** (degraded session).

Development mode can still use the Vite dev server + browser workflow (see [DEVELOPMENT.md](DEVELOPMENT.md)).

## Local-first architecture

```text
INTLLM Desktop Window (embedded React UI) ─┐
OpenAI-compatible API (/v1)               ─┼─> FastAPI backend ─> Orchestrator
CLI (`intllm`)                            ─┘         │                 │
                                                     │                 ├─> Ollama (local models)
                                                     │                 ├─> Memory (PostgreSQL + pgvector)
                                                     │                 ├─> Web retrieval (optional)
                                                     │                 ├─> Tool gateway / browser agent
                                                     │                 └─> Agent runtime (workspace sandbox)
                                                     └─> API keys, audit, metrics, background maintenance
```

| Area | Path |
| --- | --- |
| Desktop shell | `backend/app/desktop.py` |
| Startup helpers / headless launcher | `backend/app/launcher.py` |
| Backend app | `backend/app` |
| OpenAI-compatible API | `backend/app/api/routes/openai.py` |
| Agent runtime / model loop | `backend/app/services/agent/`, `backend/app/api/routes/agent.py` |
| API key security | `backend/app/core/security.py`, `backend/app/services/security/service.py` |
| LAN access control | `backend/app/services/api_server/service.py` |
| Database models / migrations | `backend/app/db/models.py`, `backend/migrations` |
| Database readiness / init | `backend/app/services/system/db_init.py` |
| Model registry / tiers | `backend/app/services/models/service.py` |
| CLI | `backend/app/cli.py` |
| Web UI | `src/` |
| Install scripts | `IRM_INSTALL/` |
| CI/CD | `.github/workflows/` |

---

## Features

### Desktop application
Native window hosting the embedded UI, with a real startup readiness screen (PostgreSQL / Ollama / INTLLM Backend), Retry and a degraded "Continue anyway" path, resizable window, proper title and icon, and clean shutdown that stops the backend it owns. See [ARCHITECTURE.md](ARCHITECTURE.md).

### Chat
Streaming chat against your local Ollama models, with labelled activities (brain lookup, web retrieval), source cards, and persistent conversation history stored in PostgreSQL — restored across restarts.

### Agent Mode
A **Chat / Agent** control in the composer switches the workspace into coding mode. In Agent mode a **Workspace** selector appears above the input.

- **Workspace** — the folder you select (native folder picker) becomes the Agent's filesystem boundary.
- **Model-driven** — the Agent runs a bounded loop in which the local model proposes tool calls; INTLLM validates each call, applies the permission gate, performs the real operation and feeds the result back.
- **File tools** — list, read, search, create, edit, delete, move; folder operations.
- **Terminal** — run development commands through the backend with the workspace as the working directory.
- **Allow / Ask Me** — in **Ask Me** mode every action that changes the workspace (including terminal) pauses for an explicit Allow/Deny; in **Allow** mode those actions run automatically (the sandbox always applies). A timeout or a cancelled stream resolves as **deny**, never a fake allow.
- **Sandboxed** — every path is resolved against the workspace; escapes are rejected. The workspace root can never be deleted.

See [AGENT.md](AGENT.md).

### Model management
- The model list comes from your actual Ollama inventory — INTLLM never invents models.
- Pull (with real streaming progress), delete, and set a default model.
- **Classification is by parameter count**: `< 3B` → **Potato**, `3B to < 8B` → **Medium**, `>= 8B` → **High**, consistent across the model list, recommendations and UI.

### Hardware-based recommendations
Hardware is detected for real (`psutil` + `nvidia-smi` when present): CPU, RAM, GPU/VRAM, disk, OS. Models are ranked against the detected VRAM/RAM budget; values that cannot be detected render as `N/A`.

### Layered memory
| Layer | Purpose |
| --- | --- |
| **L0** Flash Brain | fast memory index / routing |
| **L1** Hot Cache | short-lived promoted context (TTL) |
| **L2** Secondary Brain | durable vector store in PostgreSQL + pgvector |

Relevant memory is retrieved during chat and labelled in the response. See [MEMORY.md](MEMORY.md).

### Live web retrieval & tools
Optional per-request web retrieval with source attribution and SSRF guards, plus a tool gateway (browser automation via optional Playwright, web, memory and system tools) enforcing per-action permission policy.

### OpenAI-compatible local API
`GET /v1/models`, `GET /v1/models/{model}`, `POST /v1/chat/completions` (streaming SSE and non-streaming), authenticated with INTLLM API keys. Access is **local-only by default**; LAN access is an explicit opt-in and always requires a key. See [API.md](API.md).

> INTLLM documents only endpoints it actually implements. `/v1/embeddings`, `/v1/responses`, audio, images, files, batches and fine-tuning are **not** implemented, and no third-party CLI compatibility is claimed unless verified against a build.

---

## Requirements

- **Windows 10/11 x64** for the packaged desktop application / installer.
- **Ollama** installed and running with at least one model pulled (`https://ollama.com`).
- **PostgreSQL 14+** with the **pgvector** extension.
- **Python 3.11+** (wheel / CLI install path).
- **Node.js 20+** (development only).

INTLLM does **not** bundle or silently install Ollama or PostgreSQL; it detects them and reports what is missing. See [INSTALL.md](INSTALL.md).

---

## Installation

### Windows desktop application (recommended)

Download `INTLLM-v1.1.0-Setup.exe` from the release and run it, or use the one-line installer:

```powershell
irm https://intllm.vercel.app/install.ps1 | iex
```

Either path installs under `%LOCALAPPDATA%\Programs\INTLLM`, adds `intllm` to your user `PATH`, and creates Start Menu (and desktop) shortcuts. Runtime data is kept separately in `%LOCALAPPDATA%\INTLLM` and is **preserved across upgrades and uninstall**.

### Portable Windows executable

`INTLLM-v1.1.0-win64x.exe` is a self-contained x64 executable — run it directly, no install required.

### Linux / macOS

```bash
curl -fsSL https://intllm.vercel.app/install.sh | bash
```

Downloads and verifies `intllm-1.1.0-py3-none-any.whl`, installs it into an isolated virtual environment at `~/.intllm`, and exposes an `intllm` command in `~/.local/bin`. The desktop window requires a webview backend (`pip install "intllm[desktop]"`); without one the backend serves headlessly and prints its local URL.

### Python package (PyPI)

```bash
python -m pip install intllm
```

### From source (development)

```bash
git clone https://github.com/Alshahriar-07/INTLLM.git
cd INTLLM
npm install && npm run build          # build the web UI
python -m pip install -e "./backend[dev]"
```

---

## CLI

```text
intllm                 start the local runtime and open the desktop app
intllm start           same as above
intllm serve           run the API server only (no window)
intllm doctor          check PostgreSQL, pgvector and Ollama readiness
intllm --version       print the version
intllm --help          print help
```

On Windows the installer also provides `intllm.cmd`, so a fresh terminal resolves `intllm` to the installed application.

---

## Quick start

1. Install INTLLM (desktop app or portable exe).
2. Ensure PostgreSQL (with pgvector) and Ollama are running.
3. Launch **INTLLM** — the desktop window opens directly; the startup screen confirms service readiness.
4. In **Models**, pull or select a model.
5. In **Settings → API**, create an API key if you want to use the local API.
6. Chat. Switch the composer to **Agent** and select a workspace to start coding tasks.

```bash
intllm doctor         # verify PostgreSQL, pgvector and Ollama readiness
intllm --version      # print the version
```

---

## Ollama

- INTLLM detects whether Ollama is installed, whether its server is running, and which models are installed.
- Daemon URL defaults to `http://127.0.0.1:11434` (`INTLLM_OLLAMA_URL`).
- If Ollama is unavailable, API calls fail with a clear `503 service_unavailable` — never fabricated output.
- The model list comes from your Ollama inventory; nothing is hardcoded.

## PostgreSQL

- Local PostgreSQL with **pgvector** stores conversations, messages, memory items, API keys, Agent workspace state and background jobs.
- On startup INTLLM verifies → initializes: PostgreSQL reachable → `pgvector` available → schema applied (Alembic, or SQLAlchemy metadata DDL in the packaged executable).
- Readiness is reported with real granularity: `connected`, `degraded` (reachable but pgvector/schema missing), `unavailable` and `offline`. INTLLM never pretends semantic memory works.
- INTLLM does **not** silently fall back to SQLite; PostgreSQL is the primary database.

```text
INTLLM_DATABASE_URL=postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm
```

Never commit credentials. See [DATABASE.md](DATABASE.md).

---

## Local API & API keys

Base URL:

```text
http://127.0.0.1:<INTLLM_PORT>/v1
```

```text
GET  /v1/models
GET  /v1/models/{model}
POST /v1/chat/completions     # stream: false | true (SSE)
```

```text
Authorization: Bearer intllm_…
# or
x-api-key: intllm_…
```

- Generated locally; only a salted **scrypt** hash and a short fingerprint are stored.
- The full key is shown **once** at creation and can never be retrieved again.
- Keys are labelled, revocable, and track last-used time.
- Secrets are redacted from logs and never appear in frontend bundles.
- While no key exists yet, loopback requests are allowed as a bootstrap so you can create the first key in the UI.
- **LAN access is off by default.** Enable it in Settings → API; only `/v1` becomes reachable from the LAN, and it still requires a key. Internal `/api` management routes stay loopback-only.

Technical schema: `/openapi.json`, `/docs` (Swagger UI), `/redoc`. The in-app **Docs** page is the user-facing reference. See [API.md](API.md).

---

## Security

- Local API authentication with hashed keys; constant-time verification.
- Local-first: binds to `127.0.0.1` by default; LAN exposure is explicit opt-in.
- Secret redaction in logs; no secrets in frontend bundles, Git, or release artifacts.
- Restricted CORS origins; request-size limits; consistent error contract.
- Tool and Agent actions are permission-gated; the Agent is sandboxed to the selected workspace.
- SSRF guards on web/browser URLs; retrieved web text treated as data, not instructions.

See [SECURITY.md](SECURITY.md) for the full model and threat analysis.

---

## Configuration

Environment variables (sensible defaults; `backend/.env.example` has a full list). See [CONFIGURATION.md](CONFIGURATION.md).

| Variable | Default | Purpose |
| --- | --- | --- |
| `INTLLM_HOST` | `127.0.0.1` | Bind address (LAN exposure is opt-in) |
| `INTLLM_PORT` | `8000` | API/UI port |
| `INTLLM_API_ACCESS_MODE` | `local` | `local` (loopback) or `lan` |
| `INTLLM_DATABASE_URL` | `postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm` | Async PostgreSQL URL |
| `INTLLM_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama daemon |
| `INTLLM_LOG_LEVEL` | `INFO` | Logging level |
| `INTLLM_DATA_DIR` | `./data` | Data directory |
| `INTLLM_WORKSPACE_DIR` | `./workspace` | Workspace allowlist root |
| `INTLLM_MAX_REQUEST_BYTES` | `10485760` | Request body limit |
| `INTLLM_DEFAULT_MODEL` | (empty) | Default model; empty = auto-detect |
| `INTLLM_AGENT_TERMINAL_TIMEOUT_SECONDS` | `60` | Agent command timeout |

---

## Development

```bash
npm run dev                              # Vite dev server for the UI (browser workflow)
cd backend && python -m app.cli serve    # backend API
```

Backend tasks:

```bash
cd backend
python -m pytest -q                      # unit tests (no external services)
ruff check --config pyproject.toml app tests
```

Database integration tests run when `INTLLM_TEST_DATABASE_URL` points at a pgvector-enabled PostgreSQL. See [DEVELOPMENT.md](DEVELOPMENT.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Building

```bash
# Python wheel + sdist (+ Windows exe + installer on Windows) and SHA256.txt
python scripts/build_release.py

# Windows executable + smoke test only
python build_windows.py

# Frontend only
npm run build
```

Artifacts are staged in `build/release/`:

```text
build/release/
├── INTLLM-v1.1.0-win64x.exe        # portable desktop executable (x64)
├── INTLLM-v1.1.0-Setup.exe         # Windows installer (Inno Setup)
├── intllm-1.1.0-py3-none-any.whl
├── intllm-1.1.0.tar.gz
├── install.ps1
├── install.sh
└── SHA256.txt
```

> `dist/` is the Vite frontend build output (Vite empties it on every build), so release artifacts are staged in `build/release/` instead.

## Release information

- **Version:** 1.1.0 (single source of truth: `backend/app/__init__.py`; the release tag must match it).
- **Windows artifacts:** `INTLLM-v1.1.0-win64x.exe` (x64, PyInstaller single-file desktop app) and `INTLLM-v1.1.0-Setup.exe` (Inno Setup).
- **Python artifacts:** `intllm-1.1.0-py3-none-any.whl`, `intllm-1.1.0.tar.gz`.
- **PyPI:** published via Trusted Publishing (`.github/workflows/pypi.yml`).

Releases are built by `.github/workflows/release.yml` (tests → wheel/sdist → Windows exe + installer → `SHA256.txt` → validation → GitHub release). See [RELEASE.md](RELEASE.md).

---

## Troubleshooting

| Symptom | Cause / Fix |
| --- | --- |
| Startup window shows PostgreSQL unavailable | Start the local PostgreSQL service; confirm `INTLLM_DATABASE_URL`. |
| Startup window shows Ollama offline | Start Ollama (`ollama serve`) and pull a model. |
| `401 authentication_error` | Missing/invalid key. Create one in Settings → API. |
| `503 service_unavailable` | PostgreSQL or Ollama unavailable. Run `intllm doctor`. |
| `404 not_found` on a model | Model not installed in Ollama. Check Models. |
| Database reported `degraded` / `misconfigured` | pgvector missing. Install the extension and restart. |
| Agent reports no workspace | Select a folder in Agent mode before acting. |
| Agent action waits indefinitely | Approve (or deny) the Allow/Ask Me prompt in the UI. |
| `intllm` not found after install | Open a new shell (PATH changes need a fresh terminal). |
| Desktop window blank | WebView2 runtime missing (Windows). Install the Evergreen WebView2 Runtime. |

## License

**PolyForm Noncommercial License 1.0.0.** Copyright © 2026 Al Shahriar Sowan. See [`LICENSE`](LICENSE).

This is a source-available, **noncommercial** license — commercial use is not permitted under these terms.
