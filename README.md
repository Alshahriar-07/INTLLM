# INTLLM

**A local-first AI runtime that turns compatible local LLMs into a richer intelligence environment — layered memory, live retrieval, controlled tools, an Agent mode for coding work, and an OpenAI-compatible local API.**

INTLLM runs on your machine. Conversations, model weights, embeddings and vector memory stay local by default. Nothing is sent to a cloud service unless you explicitly enable live web retrieval for a request.

**Current version: 1.0.2** — see [`RELEASE_INFO.md`](RELEASE_INFO.md) and [`CHANGELOG.md`](CHANGELOG.md).

---

## Core concept

Local models are good reasoning engines, but they have no memory of *your* context, no access to *current* information, and no API surface your other tools can use. INTLLM does not retrain the base model for every new fact. It supplies the surrounding runtime:

```text
User
 ↓
INTLLM Runtime
 ├── L0 Flash Brain        fast memory index
 ├── L1 Hot Cache          short-lived promoted context
 ├── L2 Secondary Brain    durable vector store (PostgreSQL + pgvector)
 ├── Live Web retrieval     optional, per-request, source-attributed
 ├── Tool Gateway           validated, permission-gated tools
 ├── Agent runtime          workspace-scoped files/terminal (Chat → Agent mode)
 ├── Model Adapter          Ollama-backed model management
 └── Local OpenAI API       /v1 with INTLLM API keys
 ↓
Ollama
 ↓
Local model
```

The golden rule: **user responses always have priority**; background maintenance yields resources to interactive requests.

## Local-first architecture

```text
Web UI (React/Vite)  ─┐
OpenAI-compatible API ─┼─> FastAPI backend ─> Orchestrator
CLI (`intllm`)        ─┘         │                 │
                                 │                 ├─> Ollama (local models)
                                 │                 ├─> Memory (PostgreSQL + pgvector)
                                 │                 ├─> Web retrieval (optional)
                                 │                 ├─> Tool gateway / browser agent
                                 │                 └─> Agent runtime (workspace sandbox)
                                 └─> API keys, audit, metrics, background maintenance
```

| Area | Path |
| --- | --- |
| Backend app | `backend/app` |
| OpenAI-compatible API | `backend/app/api/routes/openai.py` |
| Agent runtime | `backend/app/services/agent/`, `backend/app/api/routes/agent.py` |
| API key security | `backend/app/core/security.py`, `backend/app/services/security/service.py` |
| Database models / migrations | `backend/app/db/models.py`, `backend/migrations` |
| Database readiness / init | `backend/app/services/system/db_init.py` |
| Model registry / tiers | `backend/app/services/models/service.py` |
| Windows launcher | `backend/app/launcher.py` |
| CLI | `backend/app/cli.py` |
| Web UI | `src/` |
| Install scripts | `IRM_INSTALL/` |
| CI/CD | `.github/workflows/` |

---

## Features

### Chat
Streaming chat against your local Ollama models, with labelled activities (brain lookup, web retrieval), source cards, and persistent conversation history stored in PostgreSQL.

### Agent Mode
A **Chat / Agent** control in the composer switches the workspace into coding mode. In Agent mode a **Workspace** selector appears above the input.

- **Workspace** — the folder you select becomes the Agent's filesystem boundary.
- **Read / inspect** — list directories, read files, search the workspace.
- **Create / edit** — create files and directories, and write changes.
- **Delete / rename / move** — with approval.
- **Terminal** — run development commands (npm, python, git, build/test) through the backend.
- **Approval-gated** — overwrite, delete, move and terminal execution require an explicit approval; `allow_session` grants suppress repeat prompts for harmless repeated work. The workspace root can never be deleted.
- **Sandboxed** — every path is resolved against the workspace; escapes are rejected (`403`). Enabling Agent mode never exposes your whole filesystem.

> The Agent runtime, its API and its permission gate are implemented. Model-driven autonomous tool-calling (the model choosing tools by itself) is **not yet wired**; today the runtime is driven through the Agent API / UI.

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

Relevant memory is retrieved during chat and labelled in the response. Background maintenance keeps indexes and freshness current at low priority.

### Live web retrieval & tools
Optional per-request web retrieval with source attribution and SSRF guards, plus a tool gateway (browser automation via optional Playwright, web, memory and system tools) enforcing per-action permission policy.

### OpenAI-compatible local API
`GET /v1/models`, `GET /v1/models/{model}`, `POST /v1/chat/completions` (streaming SSE and non-streaming), authenticated with INTLLM API keys.

> INTLLM documents only endpoints it actually implements. `/v1/embeddings`, `/v1/responses`, audio, images, files, batches and fine-tuning are **not** implemented, and no third-party CLI compatibility is claimed unless verified against a build.

---

## Requirements

- **Ollama** installed and running with at least one model pulled (`https://ollama.com`).
- **PostgreSQL 14+** with the **pgvector** extension.
- **Python 3.11+** (wheel / CLI install path).
- **Node.js 20+** (development only).
- **Windows 10/11 x64** for the packaged executable / installer.

INTLLM does **not** bundle or silently install Ollama or PostgreSQL; it detects them and reports what is missing.

---

## Installation

### Windows (PowerShell)

```powershell
irm https://intllm.vercel.app/install.ps1 | iex
```

Downloads `INTLLM.exe` (or `INTLLM-Setup.exe` when `INTLLM_USE_SETUP=1` and the artifact is published), verifies its SHA256 against the release `SHA256.txt`, installs under `%LOCALAPPDATA%\Programs\INTLLM`, adds it to your user `PATH`, and creates `intllm`, Start Menu and desktop shortcuts. Runtime data is kept separately in `%LOCALAPPDATA%\INTLLM` and is preserved across upgrades and uninstall.

### Linux / macOS

```bash
curl -fsSL https://intllm.vercel.app/install.sh | bash
```

Downloads and verifies `intllm-<version>-py3-none-any.whl`, installs it into an isolated virtual environment at `~/.intllm`, and exposes an `intllm` command in `~/.local/bin`.

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
intllm                 start the local runtime and open the web UI
intllm start           same as above
intllm serve           run the API server only (no browser)
intllm doctor          check PostgreSQL, pgvector and Ollama readiness
intllm --version       print the version
intllm --help          print help
```

On Windows the installer also provides `intllm.cmd`, so a fresh terminal resolves `intllm` to the installed application.

---

## Quick start

```bash
intllm --version      # print the version
intllm doctor         # check PostgreSQL, pgvector and Ollama readiness
intllm                # start the local runtime and open the web UI
```

Then pull/select a model in **Models**, create a key in **Settings → API**, and chat. Switch the composer to **Agent** and select a workspace to start coding tasks.

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

Never commit credentials. Use environment variables or your local secret store.

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

Technical schema: `/openapi.json`, `/docs` (Swagger UI), `/redoc`. The in-app **Docs** page is the user-facing reference.

---

## Security

- Local API authentication with hashed keys; constant-time verification.
- Local-first: binds to `127.0.0.1` by default; LAN exposure is explicit opt-in.
- Secret redaction in logs; no secrets in frontend bundles, Git, or release artifacts.
- Restricted CORS origins; request-size limits; consistent error contract.
- Tool and Agent actions are permission-gated; the Agent is sandboxed to the selected workspace.
- SSRF guards on web/browser URLs; retrieved web text treated as data, not instructions.

See `INTLLM-PLAN/10-security/SECURITY.md` for the full model.

---

## Configuration

Environment variables (sensible defaults; `backend/.env.example` has a full list):

| Variable | Default | Purpose |
| --- | --- | --- |
| `INTLLM_HOST` | `127.0.0.1` | Bind address (LAN exposure is opt-in) |
| `INTLLM_PORT` | `8000` | API/UI port |
| `INTLLM_DATABASE_URL` | `postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm` | Async PostgreSQL URL |
| `INTLLM_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama daemon |
| `INTLLM_LOG_LEVEL` | `INFO` | Logging level |
| `INTLLM_DATA_DIR` | `./data` | Data directory |
| `INTLLM_WORKSPACE_DIR` | `./workspace` | Workspace allowlist root |
| `INTLLM_API_PREFIX` | `/api` | Internal API prefix |
| `INTLLM_CORS_ORIGINS` | local origins | Allowed CORS origins |
| `INTLLM_MAX_REQUEST_BYTES` | `10485760` | Request body limit |
| `INTLLM_DEFAULT_MODEL` | (empty) | Default model; empty = auto-detect |
| `INTLLM_AGENT_TERMINAL_TIMEOUT_SECONDS` | `60` | Agent command timeout |

---

## Development

```bash
npm run dev                              # Vite dev server for the UI
cd backend && python -m app.cli serve    # backend API
```

Backend tasks:

```bash
cd backend
python -m pytest -q                      # unit tests (no external services)
ruff check --config pyproject.toml app tests
```

Database integration tests run when `INTLLM_TEST_DATABASE_URL` points at a pgvector-enabled PostgreSQL.

## Testing

- **Backend**: `pytest` covers config, security, health, database readiness, Ollama control, tool policy, chat streaming, memory units, the OpenAI-compatible API contract and the Agent runtime (sandbox, approvals, session grants, terminal).
- **Frontend**: `npm run lint` (TypeScript) and `npm run build`.

## Building

```bash
# Python wheel + sdist (+ Windows exe on Windows) and SHA256.txt
python scripts/build_release.py

# Windows executable + smoke test only
python build_windows.py

# Frontend only
npm run build
```

Artifacts are staged in `build/release/`:

```text
build/release/
├── INTLLM.exe
├── INTLLM-Setup.exe                 # built when Inno Setup is available
├── intllm-<version>-py3-none-any.whl
├── intllm-<version>.tar.gz
├── install.ps1
├── install.sh
└── SHA256.txt
```

> **Note on `dist/`:** `dist/` is the Vite frontend build output (Vite empties it on every build), so release artifacts are staged in `build/release/` instead. `dist/` also carries the served `install.ps1` / `install.sh`.

## Release information

- **Version:** 1.0.2 (single source of truth: `backend/app/__init__.py`; the release tag must match it).
- **Windows artifact:** `INTLLM.exe` (x64, PyInstaller single-file) and `INTLLM-Setup.exe` (Inno Setup).
- **Python artifacts:** `intllm-1.0.2-py3-none-any.whl`, `intllm-1.0.2.tar.gz`.
- **PyPI:** published via Trusted Publishing (`.github/workflows/pypi.yml`).

Releases are built by `.github/workflows/release.yml` (tests → wheel/sdist → Windows exe + installer → `SHA256.txt` → validation → GitHub release). See [`RELEASE_INFO.md`](RELEASE_INFO.md), [`RELEASE.md`](RELEASE.md) and [`CHANGELOG.md`](CHANGELOG.md).

---

## Troubleshooting

| Symptom | Cause / Fix |
| --- | --- |
| `401 authentication_error` | Missing/invalid key. Create one in Settings → API. |
| `503 service_unavailable` | PostgreSQL or Ollama unavailable. Run `intllm doctor`. |
| `404 not_found` on a model | Model not installed in Ollama. Check Models. |
| Database reported `degraded` / `misconfigured` | pgvector missing. Install the extension and restart. |
| Agent reports no workspace | Select a folder in Agent mode before acting. |
| Agent operation returns `permission_required` | Approve the operation (optionally for the session) in the UI. |
| `intllm` not found after install | Open a new shell (PATH changes need a fresh terminal). |
| Stream stalls | Model may still be loading; errors arrive as an SSE error frame followed by `data: [DONE]`. |

## License

**PolyForm Noncommercial License 1.0.0.** Copyright © 2026 Al Shahriar Sowan. See [`LICENSE`](LICENSE).

This is a source-available, **noncommercial** license — commercial use is not permitted under these terms.
