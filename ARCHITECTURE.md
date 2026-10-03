# INTLLM Architecture

INTLLM is a local-first AI runtime delivered as a native desktop application. It
orchestrates local models served by Ollama and surrounds them with layered
memory, persistent chat history, controlled tools, an Agent runtime, and an
OpenAI-compatible local API.

---

## Desktop application

The production experience is a native desktop window, not a browser tab.

```text
INTLLM.exe
 ├── Desktop window (WebView2 via pywebview)   ← user-facing UI
 ├── Startup readiness screen (PostgreSQL / Ollama / Backend)
 ├── Embedded backend (FastAPI, internal 127.0.0.1)
 ├── PostgreSQL (external, detected)
 ├── Ollama (external, detected)
 ├── Memory + chat history (PostgreSQL)
 └── Local OpenAI-compatible API (/v1)
```

- **Framework:** [pywebview](https://pywebview.flowrl.com/) hosting the existing
  React build in the OS webview (WebView2 on Windows). It reuses the frontend
  unchanged, is light relative to Electron/Tauri for a Python backend, bundles
  cleanly with PyInstaller, and produces a normal Windows window.
- **Startup flow** (`backend/app/desktop.py`):
  1. initialize configuration and per-user directories,
  2. initialize rotating file logging (secrets redacted),
  3. bootstrap the PostgreSQL schema,
  4. apply the persisted local/LAN access mode,
  5. resolve the port (attach to an existing INTLLM instance instead of starting
     a duplicate; never kill unrelated processes),
  6. start the FastAPI backend in a background thread,
  7. show the startup window with live service readiness,
  8. load the UI into the window once the backend is ready,
  9. stop the backend it owns when the window closes.
- **Failure handling:** if PostgreSQL is not ready, the startup window shows the
  real reason and offers **Retry** or **Continue anyway** (degraded session). If
  the backend does not become ready in time, it says so and offers Retry.
- **Lifecycle:** only the backend that INTLLM started is shut down. If an
  existing INTLLM backend was detected, INTLLM attaches to it and does not
  terminate it on exit.
- **Headless mode:** `INTLLM_DESKTOP_HEADLESS=1` serves the backend without a
  window (used by the build smoke test). Without a webview backend (e.g. a
  Linux/macOS wheel installed without the `desktop` extra), INTLLM serves
  headlessly and prints its local URL instead of failing.

## Overall runtime

```text
Desktop Window (React UI)  ·  OpenAI-compatible API (/v1)  ·  intllm CLI
 ↓
FastAPI Backend (Orchestrator)
 ├── Model Adapter (OllamaAdapter)      list/pull/delete/chat/health
 ├── L0 Flash Brain                     fast memory index / routing
 ├── L1 Hot Cache                       short-lived promoted context (TTL)
 ├── L2 Secondary Brain                 durable vector store (PostgreSQL + pgvector)
 ├── Chat history                       conversations + messages (PostgreSQL)
 ├── Tool Gateway                       validate → policy → permission → execute → sanitize
 ├── Browser Agent                      Playwright (optional)
 ├── Web Retrieval                      DuckDuckGo / SearXNG (opt-in per request)
 ├── Agent runtime                      workspace sandbox + permission gate + model loop
 ├── Resource Governor                  interactive latency / CPU / RAM thresholds
 └── Background Learner                 low-priority memory/index maintenance
 ↓
Ollama (local models)
 ↓
PostgreSQL + pgvector (conversations, memory, keys, jobs, audit)
```

## Backend layout

| Path | Responsibility |
| --- | --- |
| `backend/app/desktop.py` | Desktop shell, startup window, backend lifecycle |
| `backend/app/launcher.py` | Shared startup helpers (dirs, logging, DB bootstrap, port, static root) |
| `backend/app/main.py` | FastAPI app, middleware, static SPA serving, lifespan |
| `backend/app/cli.py` | `intllm` CLI (`start`, `serve`, `doctor`) |
| `backend/app/api/routes/` | HTTP endpoints (health, chat, models, ollama, agent, api-keys, api-server, …) |
| `backend/app/services/` | Business logic per subsystem |
| `backend/app/db/` | SQLAlchemy models, session, repositories, health state |
| `backend/migrations/` | Alembic migrations |
| `backend/tests/` | Pytest suite (external boundaries monkeypatched) |

## Frontend

React 18 + TypeScript + Vite SPA with a Tailwind design system. The packaged
build is served by the backend (`INTLLM_SERVE_STATIC=1`) with an `index.html`
fallback for client-side routes, and loaded into the desktop window. Development
uses the Vite dev server (see [DEVELOPMENT.md](DEVELOPMENT.md)).

## Data flow: a chat request

```text
UI/API → backend → orchestrator
  → memory lookup (L0 → L1 → L2)
  → optional web retrieval (opt-in)
  → build context → Ollama adapter → model
  → stream tokens back (SSE)
  → persist conversation + messages
```

## Data flow: an Agent request

```text
UI (Agent mode) → agent loop
  → model proposes {"tool": ..., "args": {...}}
  → workspace path validation
  → permission gate (Ask Me → user Allow/Deny; Allow → auto)
  → real filesystem/terminal operation
  → structured result fed back to the model
  → repeat until final answer (bounded)
```

## Security boundaries

- Backend binds loopback by default; LAN exposure is opt-in and limited to
  `/v1`.
- Management routes are loopback-only (middleware).
- Agent paths are resolved against the workspace root.
- Workspace-changing actions are permission-gated.
- Secrets are hashed (keys) and redacted (logs).

See [SECURITY.md](SECURITY.md).

## Packaging

- **Windows executable:** PyInstaller onefile (`backend/INTLLM.spec`), windowed
  (no console), bundling the Python runtime, backend, frontend build and the
  desktop shell. Named `INTLLM-v1.1.0-win64x.exe`.
- **Windows installer:** Inno Setup (`IRM_INSTALL/INTLLM-Setup.iss`), per-user
  install, named `INTLLM-v1.1.0-Setup.exe`.
- **Python:** universal wheel + sdist built from `backend/`.
- **Checksums:** `scripts/make_sha256.py`; verified by
  `scripts/validate_release.py`.

See [RELEASE.md](RELEASE.md).
