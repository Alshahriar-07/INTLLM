# INTLLM

**A local-first AI runtime that turns compatible local LLMs into a richer intelligence environment — with layered memory, live retrieval, browser tools, an OpenAI-compatible local API, and a production web UI.**

INTLLM runs on your machine. Conversations, model weights, embeddings and vector memory stay local by default. Nothing is sent to a cloud service unless you explicitly enable live web retrieval for a request.

---

## What it is

- A FastAPI backend that orchestrates local models served by **Ollama**.
- A React + TypeScript web UI (black / white / ash monochrome design system).
- A **local OpenAI-compatible API** (`/v1`) with its own API-key system.
- A **layered memory** store in local **PostgreSQL + pgvector**.
- A **tool gateway** that mediates browser automation and filesystem/system actions.

## Why it exists

Local models are good reasoning engines but have no memory of *your* context and no access to *current* information. INTLLM does not retrain the base model for every new fact. Instead it supplies current context, tools, memory and orchestration around the model — while keeping the golden rule: **user responses always have priority**, and background work yields resources to interactive requests.

---

## Architecture

```
Web UI (React/Vite)  ─┐
OpenAI-compatible API ─┼─> FastAPI backend ─> Orchestrator
CLI (`intllm`)        ─┘         │                 │
                                 │                 ├─> Ollama (local models)
                                 │                 ├─> Memory (PostgreSQL + pgvector)
                                 │                 ├─> Web retrieval (optional)
                                 │                 └─> Tool gateway / browser agent
                                 └─> API keys, audit, metrics, background maintenance
```

Key source locations:

| Area | Path |
| --- | --- |
| Backend app | `backend/app` |
| OpenAI-compatible API | `backend/app/api/routes/openai.py` |
| API key security | `backend/app/core/security.py`, `backend/app/services/security/service.py` |
| Database models / migrations | `backend/app/db/models.py`, `backend/migrations` |
| Database readiness / init | `backend/app/services/system/db_init.py` |
| Windows launcher | `backend/app/launcher.py` |
| CLI | `backend/app/cli.py` |
| Web UI | `src/` |
| Install scripts | `IRM_INSTALL/` |
| CI/CD | `.github/workflows/` |

---

## Features

- **Local chat** against Ollama models, with streaming.
- **OpenAI-compatible local API**: `GET /v1/models`, `GET /v1/models/{model}`, `POST /v1/chat/completions` (streaming and non-streaming).
- **Local API key system** — INTLLM keys (not Ollama keys), salted scrypt hashes, one-time secret reveal, revocation, labels, last-used tracking.
- **Layered memory**: L0 Flash Brain (fast micro-cache), L1 Hot Cache, L2 Secondary Brain (PostgreSQL + pgvector).
- **Optional live web retrieval** with source attribution.
- **Tool gateway + browser agent** with per-action permission checks.
- **Honest dependency reporting**: PostgreSQL, pgvector and Ollama are detected and reported as `running` / `stopped` / `unavailable` / `misconfigured`. INTLLM never fabricates availability.
- **Background maintenance** of memory/indexes and knowledge state — it does **not** continuously retrain Ollama model weights.
- **Windows packaging**: PyInstaller single-file x64 executable and an Inno Setup installer.

> INTLLM documents only endpoints it actually implements. Endpoints such as `/v1/embeddings` or `/v1/responses` are **not** implemented. INTLLM does not claim tested compatibility with any specific third-party CLI unless verified against a build.

---

## Requirements

- **Python 3.11+** (for the CLI / wheel install).
- **Ollama** installed and running with at least one model pulled (`https://ollama.com`).
- **PostgreSQL 14+** with the **pgvector** extension for semantic memory.
- Node.js 20+ (development only).
- Windows 10/11 x64 for the packaged installer path.

INTLLM does **not** bundle or silently install Ollama or PostgreSQL. The installer places INTLLM and reports what is missing.

---

## Installation

### Windows

```powershell
irm https://intllm.vercel.app/install.ps1 | iex
```

Downloads `INTLLM-windows-x64.exe` (or `INTLLM-Setup.exe` when published), verifies its SHA256 against the release `SHA256.txt`, installs under `%LOCALAPPDATA%\Programs\INTLLM`, adds it to your user `PATH`, and creates a Start Menu shortcut. Runtime data is kept separately in `%LOCALAPPDATA%\INTLLM` and is preserved across upgrades and uninstall.

### Linux / macOS

```bash
curl -fsSL https://intllm.vercel.app/install.sh | bash
```

Downloads and verifies `intllm-<version>-py3-none-any.whl`, installs it into an isolated virtual environment at `~/.intllm`, and exposes an `intllm` command in `~/.local/bin`.

### From source (development)

```bash
git clone https://github.com/Alshahriar-07/INTLLM.git
cd INTLLM
npm install && npm run build          # build the web UI
python -m pip install -e "./backend[dev]"
```

---

## Quick start

```bash
intllm --version      # print the version
intllm doctor         # check PostgreSQL, pgvector and Ollama readiness
intllm                # start the local runtime and open the web UI
intllm serve          # run the API server only (no browser)
```

Then open the web UI, pull/select a model in **Models**, create a key in **Settings → API**, and chat.

---

## Ollama

- INTLLM detects whether Ollama is installed, whether its server is running, and which models are installed.
- The daemon URL defaults to `http://127.0.0.1:11434` (`INTLLM_OLLAMA_URL`).
- If Ollama is unavailable, API calls fail with a clear `503 service_unavailable` — never fabricated output.
- INTLLM does not hardcode a model that may not exist; the model list comes from your Ollama inventory.

## PostgreSQL

- Local PostgreSQL with **pgvector** stores conversations, messages, memory items, API keys and background jobs.
- On startup INTLLM verifies: PostgreSQL reachable → database exists → `pgvector` available → schema initialized.
- If `pgvector` is unavailable, INTLLM reports the database as **misconfigured** with an actionable step — it never pretends semantic memory works.
- Schema is applied automatically: Alembic migrations when available (development / CI), or SQLAlchemy metadata DDL in the packaged executable. Tables are never created by hand.

Configuration:

```text
INTLLM_DATABASE_URL=postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm
```

Never commit credentials. Use environment variables or your local secret store.

---

## Local API

Base URL:

```text
http://127.0.0.1:<INTLLM_PORT>/v1
```

Implemented endpoints:

```text
GET  /v1/models
GET  /v1/models/{model}
POST /v1/chat/completions     # stream: false | true (SSE)
```

Technical schema: `/openapi.json`, `/docs` (Swagger UI), `/redoc`. The in-app **Docs** page is the user-facing reference.

## API keys

```text
Authorization: Bearer sk-intllm-…
# or
x-api-key: sk-intllm-…
```

- Generated locally; only a salted **scrypt** hash and a short fingerprint are stored.
- The full key is shown **once** at creation and can never be retrieved again.
- Keys are labelled, revocable, and track last-used time.
- Secrets are redacted from logs and never appear in frontend bundles.
- While no key exists yet, loopback requests are allowed as a bootstrap so you can create the first key in the UI.

---

## Docs

The web UI includes a **Docs** page covering Overview, Quick Start, Local API, Authentication, Models, Chat Completions, OpenAI Compatibility, Ollama, Memory, Browser Tools, API Examples, Troubleshooting and Security.

## Memory architecture

| Layer | Purpose |
| --- | --- |
| **L0** Flash Brain | Sub-15 ms micro-cache for hot/recent items |
| **L1** Hot Cache | Short-lived context with TTL |
| **L2** Secondary Brain | Durable vector store in PostgreSQL + pgvector |

During a chat, relevant memory is retrieved and added to the model context; retrieved memory is labelled in the response activities. Background maintenance keeps indexes and freshness current at low priority.

## Browser tools

Browser automation and other tools run through the **tool gateway**, which enforces per-action permission policy. Tool execution never bypasses the gateway. Filesystem access is restricted to the configured workspace allowlist. Browser automation is optional (Playwright) and reported as unavailable when not installed.

---

## Security

- Local API authentication with hashed keys.
- Secret redaction in logs; no secrets in frontend bundles, Git, or release artifacts.
- Binds to `127.0.0.1` by default; LAN exposure is an explicit opt-in.
- Restricted CORS origins.
- Request size limits and input validation with a consistent error contract.
- Tool permission checks on every action.

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

`INTLLM_API_ENABLED` and other planned variables are documented where implemented; do not assume unimplemented variables have an effect.

---

## Development

```bash
npm run dev        # Vite dev server for the UI
cd backend && python -m app.cli serve   # backend API
```

Common backend tasks:

```bash
cd backend
python -m pytest -q                      # unit tests (no external services)
ruff check --config pyproject.toml app tests
```

Database integration tests run when `INTLLM_TEST_DATABASE_URL` points at a pgvector-enabled PostgreSQL.

## Testing

- **Backend**: `pytest` covers config, security, health, Ollama control, tool policy, chat streaming, memory units and the OpenAI-compatible API contract (auth, invalid/revoked keys, streaming, errors). Database integration tests cover migrations, persistence and restart recovery when a real database is provided.
- **Frontend**: `npm run lint` (TypeScript) and `npm run build`.

## Building

```bash
# Python wheel + sdist (+ Windows exe on Windows) with SHA256.txt
python scripts/build_release.py

# Frontend only
npm run build

# Windows executable + smoke test only
python build_windows.py
```

Artifacts are written to `build/release/`:

```text
build/release/
├── INTLLM-windows-x64.exe
├── INTLLM-Setup.exe                 # built when Inno Setup is available
├── intllm-<version>-py3-none-any.whl
├── intllm-<version>.tar.gz
└── SHA256.txt
```

> **Note on `dist/`:** in this repository `dist/` is the Vite frontend build output (Vite empties it on every build), so release artifacts are staged in `build/release/` instead. `dist/` also carries the served `install.ps1` / `install.sh`.

## Release

Releases are built by `.github/workflows/release.yml`, which runs tests, builds the wheel, sdist and Windows executable, attempts the Inno Setup installer, regenerates `SHA256.txt`, validates artifacts (including installing the wheel and running `intllm --version` / `--help`), and publishes a GitHub release. See [`RELEASE.md`](RELEASE.md) and [`CHANGELOG.md`](CHANGELOG.md).

The version is single-sourced from `backend/app/__init__.py`; the release tag must match it.

---

## Troubleshooting

| Symptom | Cause / Fix |
| --- | --- |
| `401 authentication_error` | Missing/invalid key. Create one in Settings → API. |
| `503 service_unavailable` | PostgreSQL or Ollama unavailable. Run `intllm doctor`. |
| `404 not_found` on a model | Model not installed in Ollama. Check Models. |
| Database reported `misconfigured` | pgvector missing. Install the extension and restart. |
| `intllm` not found after install | Open a new shell or add the install dir to `PATH`. |
| Stream stalls | Model may still be loading; errors arrive as an SSE error frame followed by `data: [DONE]`. |

## License

MIT. See [`LICENSE`](LICENSE).
