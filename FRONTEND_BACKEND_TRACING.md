# INTLLM Frontend to Backend Tracing Specification

**Document Version:** 3.0.0  
**Target Architecture Phase:** Backend Implemented → Frontend Integration Connected  
**Last Updated:** September 2026  
**Primary Authors:** Frontend + Backend Architecture Teams

> [!IMPORTANT]
> **PRODUCTION DATA POLICY**: INTLLM remains a **data-honest** system end to end.
> No fabricated runtime data exists in the frontend or backend. Every
> backend-dependent surface renders genuine **Loading / Empty / Offline / Error /
> Connected** states derived from real service responses. The backend returns
> empty results for empty stores and explicit `offline` / `unavailable` /
> `degraded` states when a dependency is down — it never invents data to make the
> UI look populated.

---

## 1. Theme & Branding Assets Mapping

The frontend continues to use the official high-resolution **PNG branding
artwork**. SVG logo variants remain excluded.

| Asset | Actual File Path | Usage Surface | Theme Variant |
|---|---|---|---|
| Primary Dark Logo | `src/assets/brand/INTLLM-logo-on-dark.png` | Sidebar, Header, Boot Screen | Dark UI |
| Primary Light Logo | `src/assets/brand/INTLLM-logo-on-white.png` | Sidebar, Header, Boot Screen | Light UI |
| App Icon | `src/assets/brand/INTLLM-app-icon.png` | Collapsed Sidebar, Small Badges | Global |
| Favicon ICO | `public/assets/ico/INTLLM.ico` | Browser Tab / Window Title | Global |
| Favicon PNG | `public/assets/png/INTLLM-icon-128.png` | HTML Header Touch Icon | Global |

Theme architecture: `src/hooks/use-theme.tsx` (`dark` | `light` | `system`),
persisted in `localStorage` under `intllm-theme`, applied via the `dark` class on
`<html>` with a pre-hydration inline script in `index.html`.

---

## 2. Empty State Contract Matrix (backend-backed)

| Route | View Component | Disconnected / Empty State | Data Source |
|---|---|---|---|
| `/chat` | `ChatWorkspace.tsx` | "No conversation yet" | `POST /api/chat/stream` |
| `/models` | `ModelManager.tsx` | "No models detected" | `GET /api/models` |
| `/brain` | `BrainDashboard.tsx` | "No memories available" | `GET /api/brain/memories` |
| `/web` | `WebDashboard.tsx` | "Live Web unavailable" | `GET /api/web/search` |
| `/browser` | `BrowserControlPanel.tsx` | "Browser agent offline" | `GET /api/browser/status` |
| `/tools` | `ToolGateway.tsx` | "Gateway Offline (static schemas)" | `GET /api/tools` |
| `/api` | `ApiDashboard.tsx` | "No API keys" | `GET /api/api-keys` |
| `/system` | `SystemDashboard.tsx` | "Telemetry unavailable" | `GET /api/system` |
| `/background` | `BackgroundLearningWidget.tsx` | "Background learning is unavailable" | `GET /api/background/status` |

---

## 3. Integration Boundary Architecture

```text
  UI Component View (React Page)
           │
           ▼
  Connection Hook (src/hooks/use-intllm.tsx) + Page-local fetch state
           │
           ▼
  Service Abstraction Boundary (src/lib/services/*.ts)
  ├── chatService.ts        ├── browserService.ts
  ├── modelService.ts       ├── toolService.ts
  ├── brainService.ts       ├── systemService.ts
  ├── webService.ts         ├── apiService.ts
  └── backgroundService.ts
           │
           ▼
  Transport Client (src/lib/api/client.ts)  ── fetch + SSE frame parser
           │
           ▼
  INTLLM FastAPI Backend (:8000)
  /api/*  internal API     /v1/*  OpenAI-compatible API
```

Presentation components never call `fetch` directly and contain no backend
logic; all network access flows through the service modules.

---

## 4. Backend Runtime Structure

```text
backend/app/
├─ main.py                 # FastAPI app, lifespan, CORS, timing middleware
├─ config/settings.py      # env settings + runtime endpoint validation
├─ core/                   # logging, errors, security, events, metrics
├─ db/                     # base, session, models, repositories/*
├─ schemas/                # Pydantic request/response models
├─ services/
│  ├─ runtime/ollama.py    # model adapter (discovery, chat, embeddings, pull)
│  ├─ models/service.py    # registry sync + tier recommendation
│  ├─ chat/service.py      # orchestration + SSE events
│  ├─ brain/service.py     # L0/L1/L2 routing, candidate storage
│  ├─ web/service.py       # real retrieval + SSRF guard
│  ├─ browser/service.py   # Playwright agent (honest unavailable)
│  ├─ tools/gateway.py     # registry, policy, permissions, execution
│  ├─ system/service.py    # psutil + nvidia-smi telemetry, status
│  ├─ background/*         # worker loop + resource governor
│  ├─ security/service.py  # API keys (scrypt hash)
│  └─ diagnostics/service.py
└─ api/                    # routers + dependencies + SSE helpers
```

Layering: `routes → services → repositories/adapters → PostgreSQL / Ollama / web`.
Route handlers hold no business logic.

---

## 5. Data Ownership

| Data | Owner | Storage |
|---|---|---|
| Conversations & messages | Backend | PostgreSQL `conversations`, `messages` |
| Memory items & sources | Backend | `memory_items`, `memory_sources` |
| L0 flash index / embeddings | Backend | `flash_index` (pgvector) |
| L1 hot cache metadata | Backend | `hot_cache_metadata` |
| Model metadata | Backend | `models` (+ live Ollama inventory) |
| Tool runs & audit | Backend | `tool_runs`, `audit_events` |
| API keys (hashed) | Backend | `api_keys` |
| Background jobs | Backend | `background_jobs`, `job_events` |
| Theme / local prefs | Frontend | `localStorage` |

The frontend owns no server data; it holds only ephemeral view state.

---

## 6. HTTP + SSE Contract

Internal API is mounted at `/api`; the OpenAI-compatible API at `/v1`.

```text
GET    /api/health                GET  /api/ready
GET    /api/ollama/status         POST /api/ollama/start
POST   /api/ollama/stop           POST /api/ollama/restart
GET    /api/system                GET  /api/system/services
GET    /api/system/stream (SSE)   GET  /api/diagnostics
GET    /api/models                POST /api/models/pull (SSE)
POST   /api/models/default        DELETE /api/models/{name}
GET    /api/models/recommend
POST   /api/chat/stream (SSE)     POST /api/chat/completions
GET    /api/conversations         POST /api/conversations
GET    /api/conversations/{id}    DELETE /api/conversations/{id}
GET    /api/brain/search          GET  /api/brain/memories
POST   /api/brain/memories        GET  /api/brain/memories/{id}
DELETE /api/brain/memories/{id}   POST /api/brain/cache/invalidate
GET    /api/web/search            POST /api/web/fetch
GET    /api/tools                 POST /api/tools/{tool}/run
GET    /api/tools/permissions     POST /api/tools/{tool}/permission
GET    /api/browser/status        POST /api/browser/action
GET    /api/browser/stream (SSE)
GET    /api/api-keys              POST /api/api-keys
DELETE /api/api-keys/{id}
GET    /api/background/status     POST /api/background/pause
POST   /api/background/resume     GET  /api/background/stream (SSE)
GET    /v1/models                 POST /v1/chat/completions
```

### Chat stream events (`POST /api/chat/stream`)

```text
chat.started            chat.thinking          brain.lookup
memory.retrieved        web.search.started     web.source.received
web.search.failed       assistant.delta        assistant.completed
chat.completed          chat.error
```

Activity rows in the chat UI are rendered **only** from these events. If no
memory or web event is emitted, no memory/source indicators appear.

### Error contract

```json
{ "error": { "message": "...", "type": "validation_error | authentication_error | permission_error | service_unavailable | timeout | not_found | internal_error", "details": {} } }
```

---

## 7. Environment Configuration

### Frontend (`.env`, Vite — `VITE_` prefixed)

```text
VITE_INTLLM_BASE_URL=http://127.0.0.1:8000   # preferred
VITE_INTLLM_HOST=127.0.0.1                   # fallback
VITE_INTLLM_PORT=8000                        # fallback (valid port only)
```

### Backend (`backend/.env`, see `backend/.env.example`)

```text
INTLLM_ENV / INTLLM_HOST / INTLLM_PORT / INTLLM_LOG_LEVEL / INTLLM_API_PREFIX
INTLLM_CORS_ORIGINS
INTLLM_DATABASE_URL / INTLLM_DATABASE_URL_SYNC
INTLLM_OLLAMA_URL / INTLLM_OLLAMA_TIMEOUT_SECONDS / INTLLM_DEFAULT_MODEL
INTLLM_DATA_DIR / INTLLM_WORKSPACE_DIR / INTLLM_FILESYSTEM_ALLOWLIST
INTLLM_WEB_PROVIDER / INTLLM_WEB_SEARXNG_URL / INTLLM_WEB_TIMEOUT_SECONDS / INTLLM_WEB_MAX_RESULTS
INTLLM_BROWSER_ENABLED / INTLLM_BROWSER_HEADLESS / INTLLM_BROWSER_TIMEOUT_SECONDS
INTLLM_MAX_BACKGROUND_WORKERS / thresholds
```

No secrets are committed. API keys are generated at runtime, hashed with
scrypt, and never logged.

---

## 8. Runtime Endpoint Configuration

The project owner supplied the INTLLM runtime address:

```text
INTLLM HOST:   172.22.0.1
SUPPLIED PORT: 240426
STATUS:        REQUIRES PORT VALIDATION
```

**`240426` is NOT a valid TCP/UDP port.** Valid ports are `0–65535`. The
backend therefore:

- does **not** bind FastAPI to `240426`;
- does **not** silently substitute or invent a replacement port;
- records the supplied value verbatim as
  `INTLLM_RUNTIME_PORT_SUPPLIED=240426` with
  `INTLLM_RUNTIME_PORT_STATUS=requires_validation`;
- reports `port_supplied_is_valid: false` and `validated: false` from
  `Settings.runtime_endpoint` (exposed at `GET /` and `GET /api/diagnostics`);
- only builds a `base_url` once a valid `INTLLM_RUNTIME_PORT` is confirmed.

The backend's own default listening port is the PLAN value `8000`. The actual
runtime port must be confirmed by the backend implementation phase before the
frontend is pointed at `172.22.0.1`.

---

## 9. Required Feature Trace Map (Master Matrix)

| # | Feature | Route | Component | Service | Backend Endpoint | Status |
|---|---|---|---|---|---|---|
| 1 | Chat Workspace | `/chat` | `chat/ChatWorkspace.tsx` | `chatService.ts` | `POST /api/chat/stream` | `CONNECTED` |
| 2 | Message Token Streaming | `/chat` | `chat/ChatWorkspace.tsx` | `chatService.ts` | SSE | `CONNECTED` |
| 3 | Model Selector | Header | `layout/Header.tsx` | `modelService.ts` | `GET /api/models` | `CONNECTED` |
| 4 | Model Management | `/models` | `models/ModelManager.tsx` | `modelService.ts` | `GET /api/models` | `CONNECTED` |
| 5 | L0 Flash Brain Routing | `/brain` | `brain/BrainDashboard.tsx` | `brainService.ts` | `GET /api/brain/search` | `CONNECTED` |
| 6 | L1 Hot Cache | `/brain` | `brain/BrainDashboard.tsx` | `brainService.ts` | `hot_cache_metadata` | `CONNECTED` |
| 7 | L2 Secondary Brain | `/brain` | `brain/BrainDashboard.tsx` | `brainService.ts` | `memory_items` + pgvector | `CONNECTED` |
| 8 | Memory Search | `/brain` | `brain/BrainDashboard.tsx` | `brainService.ts` | `GET /api/brain/search` | `CONNECTED` |
| 9 | Live Web Retrieval | `/web` | `web/WebDashboard.tsx` | `webService.ts` | `GET /api/web/search` | `CONNECTED` |
| 10 | Browser Agent | `/browser` | `browser/BrowserControlPanel.tsx` | `browserService.ts` | `GET /api/browser/status` | `CONNECTED` |
| 11 | Tool Gateway | `/tools` | `tools/ToolGateway.tsx` | `toolService.ts` | `GET /api/tools` | `CONNECTED` |
| 12 | Local API + Keys | `/api` | `api/ApiDashboard.tsx` | `apiService.ts` | `GET/POST/DELETE /api/api-keys` | `CONNECTED` |
| 13 | API Playground | `/api` | `api/ApiDashboard.tsx` | `chatService.ts` | `POST /api/chat/stream` | `CONNECTED` |
| 14 | System Telemetry | `/system` | `system/SystemDashboard.tsx` | `systemService.ts` | `GET /api/system` | `CONNECTED` |
| 15 | Background Learning | header | `learning/BackgroundLearningWidget.tsx` | `backgroundService.ts` | `GET /api/background/status` | `CONNECTED` |
| 16 | Preferences & Theme | `/settings` | `settings/SettingsWorkspace.tsx` | Local Storage | n/a | `FRONTEND ONLY` |
| 17 | Ollama Runtime Control | `/system` + Header | `system/OllamaRuntimePanel.tsx`, `layout/Header.tsx` | `ollamaService.ts` | `GET /api/ollama/status`, `POST /api/ollama/start/stop/restart` | `CONNECTED` |
| 18 | Model Pull / Delete / Default | `/models` | `models/ModelManager.tsx` | `modelService.ts` | `POST /api/models/pull` (SSE), `DELETE /api/models/{name}`, `POST /api/models/default` | `CONNECTED` |
| 19 | Backend Offline Banner | global | `layout/AppShell.tsx` | `use-intllm.tsx` → `probeHealth` | `GET /api/health` | `CONNECTED` |
| 20 | Runtime Settings View | `/settings` | `settings/SettingsWorkspace.tsx` | `lib/api/client.ts` config exports | n/a (env read-only) | `CONNECTED (read-only)` |

---

## 10. Ollama Runtime Control (implemented)

The frontend controls the real Ollama daemon through the backend; the browser
never spawns processes.

```text
UI (SystemDashboard → OllamaRuntimePanel, Header indicator)
  → Component: OllamaRuntimePanel.tsx / Header.tsx
  → Hook: use-intllm.tsx (ollama state, startOllama/stopOllama/restartOllama,
          visibility-aware polling, cleanup on unmount)
  → Service: src/lib/services/ollamaService.ts
  → API: GET /api/ollama/status · POST /api/ollama/start|stop|restart
  → Backend service: app/services/ollama/service.py (state machine:
          running | stopped | starting | stopping | unavailable | error)
  → Process layer: app/services/ollama/process.py (Windows service/executable,
          Linux systemd user service/executable, macOS executable; graceful
          terminate then kill; verifies via real HTTP health endpoint)
  → Runtime dependency: local Ollama daemon (INTLLM_OLLAMA_URL, default
          http://127.0.0.1:11434)
  → Response: real version (/api/version), model count (/api/tags), loaded
          models + VRAM (/api/ps); N/A when the daemon does not report a value
  → Error state: real backend reason surfaced verbatim in the panel with
          [Start] / [Retry] affordances
```

Safety rules: start is a no-op when the daemon already responds; stop verifies
the daemon actually stopped; restart runs stop → verify → start → verify.
Operations are serialized; a second concurrent control call is rejected while
one is in flight. Every failure returns a structured error that the UI displays
without fabrication.

Health and Ollama polling run every `VITE_INTLLM_POLLING_INTERVAL_MS`
(default 8s, clamped 5–60s), only while the tab is visible; listeners are
removed on unmount.

## 11. Backend Developer Quick Start

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```bash
cp .env.example .env
npm install
npm run dev     # http://127.0.0.1:3000
npm run build   # production build + typecheck
```

---

## 11. Security Boundaries

- Localhost binding by default; external bind is explicit opt-in.
- API keys: high-entropy, scrypt-hashed, shown once, never logged.
- Tool policy: `read-only` / `requires-approval` / `restricted`; approval
  decisions are explicit and session grants are auditable.
- Filesystem tools restricted to an allow-list; write + terminal disabled by
  default.
- Web/browser URL guard rejects non-http(s) and private/reserved addresses (SSRF).
- Retrieved web text is treated as untrusted data, never as instructions.
- Background learning yields to interactive requests via the resource governor
  (`NORMAL` → `BUSY` → `CRITICAL`).
