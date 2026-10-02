# INTLLM-DATA.md

**Status legend used throughout this file:**

- **Implemented** — exists in the codebase and is covered by tests or verifiable code paths.
- **Planned** — specified in `INTLLM-PLAN/` but not yet implemented.
- **Experimental** — implemented but optional/behind an opt-in dependency (e.g. requires Playwright).
- **Future** — listed in the roadmap only; do not present as shipped.

---

## 1. DOCUMENT PURPOSE

INTLLM-DATA.md is the canonical product/content reference for the INTLLM website.

It contains:

- product identity
- positioning
- product explanation
- features
- architecture
- user flows
- installation
- API
- memory system
- Ollama integration
- browser/tool system
- hardware/model system
- security
- branding
- UI direction
- SEO information
- website structure
- content rules
- terminology
- links
- release information

This document is written primarily for:

- website developers
- UI/UX designers
- content writers
- SEO systems
- AI coding agents
- documentation systems
- future maintainers

It is **not** a replacement for the technical planning documents in `INTLLM-PLAN/`. Where this file and the code disagree, **the code wins**, and this file must be updated.

---

## 2. PRODUCT IDENTITY

```text
Product Name:
INTLLM

Official Website:
https://intllm.vercel.app

Product Type:
Local-first AI runtime / local intelligence operating environment

Core Runtime:
Ollama

Backend:
Python 3.11+ / FastAPI

Frontend:
React 18 + TypeScript + Vite (Tailwind CSS, monochrome design system)

Database:
PostgreSQL + pgvector

Browser:
Playwright (optional dependency)

API:
OpenAI-compatible local API (/v1)

License:
PolyForm Noncommercial License 1.0.0

Repository:
https://github.com/Alshahriar-07/INTLLM

Current Version:
1.0.2 (single source of truth: backend/app/__init__.py)
```

The distribution/CLI package is named `intllm`; the frontend package is `intllm-frontend`.

---

## 3. ONE-LINE DESCRIPTION

Canonical one-liner:

> **INTLLM is a local-first AI runtime that extends compatible local models (via Ollama) with layered memory, optional live web retrieval, controlled browser tools, and an OpenAI-compatible local API — all on your machine.**

Wording requirements:

- communicates: local-first, model-agnostic, memory-aware, tool-enabled, internet-capable *when enabled*, built around local models, extends local AI capabilities
- does **not** claim INTLLM retrains model weights continuously
- does **not** claim INTLLM magically turns small models into frontier models
- technically accurate

---

## 4. SHORT PRODUCT DESCRIPTION

### 1-sentence version (browser metadata / search results / social previews)

> INTLLM is a local-first AI runtime that gives local models memory, live information, tools and an OpenAI-compatible API — without sending your data to the cloud.

### 2–3 sentence version (homepage hero / supporting text)

> INTLLM runs entirely on your machine, orchestrating local models served by Ollama. It adds layered memory, optional live web retrieval, controlled browser tools and an OpenAI-compatible local API around the model. Your conversations, embeddings and data stay local by default.

### Short paragraph (About / Product sections)

> INTLLM is a local-first AI runtime built around local models served by Ollama. Instead of retraining a base model for every new fact, INTLLM supplies the surrounding environment: a layered memory system (Flash Brain, Hot Cache, Secondary Brain) stored in local PostgreSQL with pgvector, optional live web retrieval with source attribution, a tool gateway that mediates browser and filesystem access, and a local OpenAI-compatible API with its own key system. A React + TypeScript web UI provides chat, model management, system monitoring and documentation. Background maintenance keeps memory indexes fresh at low priority and always yields to user requests.

### Technical description (for developers)

> INTLLM is a FastAPI backend that orchestrates local LLM inference through Ollama, persists conversations, models, layered memory (pgvector-backed), API keys, tool runs and background jobs in PostgreSQL, exposes an OpenAI-compatible `/v1` API routed through the same orchestrator (auth via hashed scrypt API keys), performs optional DuckDuckGo/SearXNG live retrieval with SSRF guards and trust scoring, mediates Playwright browser automation and workspace-restricted filesystem access through a permission-gated tool gateway, and runs a low-priority background maintenance worker governed by interactive-latency thresholds. The frontend is a React 18 + TypeScript + Vite SPA served by the backend in packaged mode; Windows ships as a PyInstaller onefile executable plus an Inno Setup installer, and Linux/macOS install a universal Python wheel.

---

## 5. PRODUCT PHILOSOPHY

These concepts are documented factually, as implemented:

| Concept | What it means in INTLLM |
| --- | --- |
| **Local First** | The backend, database, memory, models and UI all run on the user's machine. The API binds to `127.0.0.1` by default. |
| **User First** | User responses always have priority. The background maintenance worker yields resources whenever interactive work needs them (resource governor with latency/CPU/RAM thresholds). |
| **Privacy by Default** | Conversations, messages, memory items and API keys live in the local PostgreSQL database. There is no hidden cloud sync. Nothing is sent to a cloud service unless the user explicitly enables live web retrieval for a request. |
| **Model Agnostic** | INTLLM does not hardcode a model. The model list comes from the user's Ollama inventory; the runtime works with whatever compatible models are installed. |
| **Transparent** | Dependency state is reported honestly (`running` / `stopped` / `unavailable` / `misconfigured`). INTLLM never fabricates availability, sources, or tool activity. Retrieved memory and web sources are labelled in the UI. |
| **Tool Enabled** | Browser, web and filesystem capabilities run through a tool gateway with schema validation, policy checks and per-action permission decisions. |
| **Memory Aware** | A layered memory system (L0/L1/L2) retrieves relevant knowledge and injects it into model context during chat. |
| **Fresh Information** | Memory items carry confidence, freshness scores, TTL policies and verification metadata; optional live retrieval supplies current information when local knowledge is insufficient. |
| **User-Controlled** | API keys are user-created and revocable; risky tools require explicit approval; web retrieval is opt-in per request. |
| **OpenAI Compatible** | A local `/v1` API implements `GET /v1/models`, `GET /v1/models/{model}` and `POST /v1/chat/completions` (streaming SSE and non-streaming), so OpenAI-compatible clients can talk to local models. |

---

## 6. THE PROBLEM INTLLM SOLVES

A normal local model setup provides only:

```text
Model
 ↓
Prompt
 ↓
Response
```

Such a model has no memory of your context, no access to current information, no safe tool access, and no API surface your other tools can use.

INTLLM adds the surrounding runtime:

```text
User
 ↓
INTLLM Runtime
 ├── Flash Brain (L0)
 ├── Hot Cache (L1)
 ├── Secondary Brain (L2)
 ├── Internet Retrieval (optional)
 ├── Browser Agent (Playwright, optional)
 ├── Tool Gateway
 ├── Ollama
 └── Local OpenAI-compatible API
 ↓
Model
```

**Positioning statement:** INTLLM is the runtime/orchestration layer *around* the model — not a replacement model, and not a retraining pipeline. The model remains the reasoning engine; INTLLM supplies context, tools, memory, and orchestration while keeping user responses the top priority.

---

## 7. CORE VALUE PROPOSITION

### Run AI locally
Use local models through Ollama. Inference happens on the user's machine via the Ollama daemon (`http://127.0.0.1:11434` by default).

### Give local models useful context
Layered memory (L0 Flash Brain / L1 Hot Cache / L2 Secondary Brain in PostgreSQL + pgvector) retrieves relevant, scored, freshness-tracked knowledge and adds it to the model context during chat.

### Access fresh information
Live web retrieval (DuckDuckGo by default, SearXNG optional) can be enabled per request (`intllm_use_web: true`, or the Web workspace in the UI) when current information is required. Sources carry domain trust scores and verification status.

### Use tools
The tool gateway exposes browser automation (Playwright), web search/extraction, memory search, system info and workspace-scoped filesystem reads — each behind schema validation, permission policy and risk levels.

### Keep control local
Data and runtime remain on the user's machine by default: localhost binding, restricted CORS, no hidden sync. PostgreSQL, Ollama and pgvector are external dependencies that INTLLM detects and reports honestly — it never bundles or silently installs them.

### Use existing AI tools
The OpenAI-compatible local API lets supported clients point at `http://127.0.0.1:<port>/v1` with an INTLLM API key and use local models.

---

## 8. ARCHITECTURE OVERVIEW

Website-friendly architecture:

```text
User
 ↓
INTLLM Web UI (React/TypeScript/Vite)  ·  OpenAI-compatible API (/v1)  ·  intllm CLI
 ↓
FastAPI Backend (Orchestrator)
 ├── Model Adapter (OllamaAdapter)
 ├── L0 Flash Brain        — fast micro-cache / flash index
 ├── L1 Hot Cache          — short-lived context cache with TTL
 ├── L2 Secondary Brain    — durable vector store (PostgreSQL + pgvector)
 ├── Tool Gateway          — validation → policy → permission → execution → sanitization
 ├── Browser Agent         — Playwright (optional)
 ├── Internet Retrieval    — DuckDuckGo / SearXNG (optional, per-request opt-in)
 ├── Resource Governor     — interactive latency / CPU / RAM thresholds
 └── Background Learner    — low-priority memory/index maintenance
 ↓
Ollama (local models)
 ↓
PostgreSQL + pgvector (conversations, memory, keys, jobs, audit)
```

Component explanations in simple language:

- **Web UI** — the local control center: chat, model management, memory (Brain), web, browser, tools, API keys, system status, docs, settings.
- **Model Adapter** — a uniform interface to Ollama (list/pull/delete models, chat streaming, embeddings, health). The runtime stays consistent while models change.
- **L0 Flash Brain** — a fast routing/index layer over memory (vector index + keywords). Answers "is useful memory available, where, how fresh, how confident?" It is *not* the full knowledge store.
- **L1 Hot Cache** — short-lived cache of recently useful query results (default TTL 30 minutes in code).
- **L2 Secondary Brain** — the durable store of curated, verified knowledge in PostgreSQL + pgvector.
- **Tool Gateway** — every model-requested tool call is validated, policy-checked, permission-decided, executed, and its result sanitized before returning to the model.
- **Browser Agent** — optional Playwright-driven automation; reported as unavailable when Playwright is not installed.
- **Internet Retrieval** — real HTTP retrieval with SSRF guards, trust scoring and verification; sources are never fabricated.
- **Resource Governor** — monitors interactive latency and system load; throttles/pauses background work under pressure.
- **Background Learner** — rotating low-priority maintenance jobs (verification, stale refresh, index updates, cache cleanup).

---

## 9. FLASH BRAIN

```text
L0 Flash Brain
```

**What it is:** a fast routing/index layer over the memory store. In code it is the flash index (`flash_index` table) plus embedding-backed lookup: it stores memory ID, compact keywords, semantic embedding (pgvector, default 768 dimensions), memory type, confidence, expiry/TTL, access counts and last-accessed time.

**What it answers:**

- Is useful memory available?
- Where is it (which layer)?
- Is it fresh?
- How confident is it?

**What it is NOT:** it is not the complete knowledge store. Full content lives in L2 (Secondary Brain); L0 is an index that makes lookup fast. In the implementation, L0 lookup runs a vector search against the flash index and falls back to L2 keyword search when embeddings are unavailable.

---

## 10. HOT CACHE

```text
L1 Hot Cache
```

Purpose:

- holds frequently used / recently useful information
- fast access (a promoted query result avoids all vector work on repeat lookups)
- compact context
- short lifetime — entries expire via TTL (30-minute default for promoted query results in code; a `hot_cache_metadata` table tracks hits, promotion time and expiry)

Promotion signals (implemented): a top memory match that is both confident (≥ 55 threshold) and fresh (≥ 60 freshness score) is promoted to the hot cache. Background cleanup invalidates expired entries.

---

## 11. SECONDARY BRAIN

```text
L2 Secondary Brain
```

The durable knowledge store in **PostgreSQL + pgvector**. It stores useful, curated persistent information:

- compact facts
- workflows
- lessons / failures
- preferences explicitly allowed to persist
- reusable knowledge with metadata
- source/provenance records (`memory_sources`: URL, title, source type, retrieval/verification timestamps)
- freshness information (score, policy, `verified_at`, optional `expires_at`)

Memory items have a type (`fact` / `workflow` / `lesson` / `preference`), confidence and importance scores, keywords, status, and freshness policies with TTLs:

```text
static: ~1 year · long: ~180 days · medium: ~30 days · short: ~7 days · live: 6 hours
```

**Do not describe it as blindly storing every webpage or conversation.** INTLLM stores structured, scored memory items with provenance — not raw page dumps. (Automatic post-response "memory candidate → verify → promote" learning is specified in `INTLLM-PLAN/05-memory/MEMORY_PIPELINE.md` and is **planned**, not implemented; users can create memories explicitly via the Brain workspace/API.)

---

## 12. BACKGROUND LEARNING

Precise description:

INTLLM can perform **low-priority background maintenance** such as:

- memory verification (expired items marked stale)
- stale data refresh (freshness statistics)
- embedding index updates (reports honest indexed/total counts)
- cache promotion/demotion (hot cache cleanup/invalidation)
- source freshness checks (freshness scoring)
- cleanup (expired hot-cache entries)

Job state is persisted in `background_jobs` / `job_events` with priorities, progress, status, CPU budget and events; the UI only ever shows tasks that actually exist. The resource governor tracks recent interactive latency and CPU/RAM thresholds (`INTLLM_BACKGROUND_LATENCY_THRESHOLD_MS` default 1500 ms, CPU 85%, RAM 90%); when thresholds are crossed, background work is throttled or paused, and it resumes when pressure clears. The worker can also be paused/resumed from the UI and API.

**Important:**

```text
This is memory/index/knowledge maintenance.
It is NOT continuous retraining of Ollama model weights.
```

Duplicate detection, memory compression, and failure analysis are **planned** job types (from `INTLLM-PLAN/11-background-learning/BACKGROUND_LEARNING.md`) and must not be presented as shipped.

User requests always have higher priority (the "golden rule").

---

## 13. INTERNET ACCESS

INTLLM **can** use live internet information when appropriate — it is opt-in, not automatic. Web retrieval is off by default per chat request (`intllm_use_web: false`) and is enabled per request or through the Web workspace. Default provider is DuckDuckGo (HTML endpoint); SearXNG is supported via configuration.

Flow:

```text
Local knowledge
 ↓
Check freshness/relevance (memory lookup with confidence + freshness scores)
 ↓
If insufficient → retrieve current information (live web search, per-request opt-in)
 ↓
Analyze (readable text extraction, domain trust scoring)
 ↓
Verify (sources marked verified only after a real fetch)
 ↓
Store useful compact knowledge (structured memory items with provenance — planned pipeline; explicit memory creation is implemented)
```

Guarantees in the implementation:

- Every request does **not** automatically go to the internet — retrieval is explicit.
- Sources are never fabricated; if the provider is unreachable, the caller receives an explicit error/unavailable state.
- SSRF protection: non-http(s) URLs and private/loopback/link-local/reserved addresses are rejected (`guard_url`).
- Retrieved web text is treated as **data, not instructions** (prompt-injection defense in the system policy).

---

## 14. BROWSER AGENT

Browser capabilities, with actual status:

| Capability | Status |
| --- | --- |
| Open URL (`browser.open`) | **Implemented** (requires approval permission level) |
| Read page / extract text (`browser.read`) | **Implemented** (read-only; up to 20,000 chars) |
| Screenshot (`browser.screenshot`) | **Implemented** (PNG, base64) |
| Click (`browser.click`) | **Implemented** (requires approval permission level) |
| Tabs (single active session tab state) | **Implemented** (single-page session state; full multi-tab management is planned) |
| Form filling | **Planned** (Phase 2 of `INTLLM-PLAN/07-tools-browser/BROWSER_AGENT.md`) |
| Navigation history / structured page interaction | **Planned** |
| Search via browser | **Implemented** via `web.search` tool (DuckDuckGo/SearXNG), not via Playwright |

Implementation facts:

- Playwright is an **optional** dependency (`backend[browser]`). When Playwright (or its browser binaries) are missing, operations return an explicit "unavailable" state — the UI reports this honestly.
- The browser runs headless by default (`INTLLM_BROWSER_HEADLESS=true`), configurable.
- Sessions are local and tracked in the `browser_sessions` table.
- The URL guard (SSRF protection) applies to browser-opened URLs.

**Security framing (use this wording):**

```text
Website content is untrusted data. Tool permissions are enforced by the
runtime. Sensitive actions require appropriate permission/approval.
```

The plan explicitly forbids silently performing purchases, account deletion, message/email sending, credential submission, and irreversible changes; such actions require explicit user confirmation (**planned** enforcement maturity — today `browser.open`/`browser.click` require an approval decision, and `filesystem.write` / `terminal.execute` are disabled by default policy).

---

## 15. TOOL GATEWAY

Why it exists: the model never directly owns OS/browser privileges. Every tool call passes through a uniform gate so that risky capabilities are validated, authorized, audited and sanitized — and the system prompt is not treated as a security boundary.

Flow:

```text
Model
 ↓
Tool request
 ↓
Schema validation (required args, non-empty strings)
 ↓
Policy check (enabled/disabled by policy)
 ↓
Permission decision (read-only · requires-approval · restricted; allow / allow_session / deny)
 ↓
Tool execution (handler dispatch)
 ↓
Sanitized result
 ↓
Model
```

Tool registry (as implemented in `backend/app/services/tools/gateway.py`):

| Tool | Permission | Risk | Status |
| --- | --- | --- | --- |
| `web.search` | read-only | Low | Implemented |
| `web.open` | read-only | Low | Implemented |
| `web.extract` | read-only | Low | Implemented |
| `browser.open` | requires-approval | Medium | Implemented |
| `browser.read` | read-only | Low | Implemented |
| `browser.click` | requires-approval | Medium | Implemented |
| `browser.screenshot` | read-only | Low | Implemented |
| `brain.search` | read-only | Low | Implemented |
| `system.info` | read-only | Low | Implemented |
| `filesystem.read` | requires-approval | Medium | Implemented (workspace allowlist only) |
| `filesystem.write` | restricted | High | **Disabled by default policy** |
| `terminal.execute` | restricted | Critical | **Disabled by default policy** |

Every tool definition carries: name, category, description, permission level, risk level, enabled flag, timeout, and required arguments. Session-level grants (`allow_session`) can approve a tool for the session and can be revoked. Tool runs are persisted in `tool_runs` with arguments, permission, risk, status, duration and error. Events are emitted for permission requests and completions.

Filesystem access is restricted to the configured workspace allowlist (`INTLLM_FILESYSTEM_ALLOWLIST`, default `./workspace`).

---

## 16. MODEL SUPPORT

Philosophy:

```text
Model Agnostic
```

- The model list comes from the user's actual Ollama inventory — INTLLM never invents models or provides a cloud fallback. An empty Ollama install yields an empty list.
- Ollama-supported model families work in principle, e.g. Qwen, Llama, DeepSeek, Gemma, Mistral and other compatible local models. **Do not imply every model supports every feature** (e.g. embeddings require an installed embedding-capable model; capability detection is per-model via Ollama's `show`).
- Model capabilities are detected from the daemon when available and stored in the registry.

The Model Adapter layer:

```text
Model
 ↓
Adapter (OllamaAdapter)
 ↓
INTLLM Runtime
```

The adapter provides model discovery, listing, pull (with SSE progress), delete, inspect, chat streaming, embeddings, and health checks. The runtime remains consistent while models change. (Additional adapters beyond Ollama are **future** work — see `INTLLM-PLAN/06-ai-runtime/MODEL_ADAPTERS.md`.)

Configuration: `INTLLM_OLLAMA_URL` (default `http://127.0.0.1:11434`), `INTLLM_DEFAULT_MODEL` (empty = auto-detect), `INTLLM_OLLAMA_TIMEOUT_SECONDS` (120 s default), optional `INTLLM_OLLAMA_NUM_GPU=0` to force CPU inference.

---

## 17. HARDWARE TIERS

INTLLM classifies models, and makes hardware recommendations, by **parameter
count** (v1.0.2 rules). The classification is consistent everywhere: the model
list, model details, the Models workspace, the pull UI, recommendations, the
backend registry metadata and the frontend labels.

The three categories are:

```text
Potato   — < 3B parameters   (code value: POTATO)
Medium   — 3B to < 8B params  (code value: MEDIUM)
High     — >= 8B parameters   (code value: HIGH)
```

These are **recommendation categories, not strict compatibility restrictions**:

- **Potato** — tiny models for low-end hardware / integrated graphics.
- **Medium** — balanced models for everyday hardware.
- **High** — larger models for high-end desktops and workstations; heavier agent
  workflows.

The classification comes from the Ollama-reported parameter size (for
mixture-of-experts strings such as `8x7B`, the total magnitude is used). When a
model reports no parameter size it is treated as **Medium**.

Actual hardware detection (via `psutil` + `nvidia-smi` when present) may consider:

- CPU (name, cores, threads, usage)
- RAM (total/used/percent)
- GPU (NVIDIA via `nvidia-smi`: name, VRAM used/total, utilization)
- VRAM (from GPU query)
- architecture / OS / Python version
- disk space (free/total)
- Ollama availability

Values that cannot be detected are returned as `None` / N/A rather than invented. Model recommendations rank installed models by a memory-requirement vs. VRAM/RAM budget comparison (`/api/models/recommend`).

---

## 18. OLLAMA

What Ollama is used for: **all local model inference and model management.** INTLLM is the orchestration layer around the Ollama daemon.

How INTLLM interacts with it (actual implementation):

- **HTTP API** — the `OllamaAdapter` talks to the daemon (`/api/version`, `/api/ps`, chat, embeddings, model endpoints). Default endpoint `http://127.0.0.1:11434` (`INTLLM_OLLAMA_URL`).
- **Installation detection** — locates the Ollama executable across platforms (PATH, `%LOCALAPPDATA%\Programs\Ollama`, `C:\Program Files\Ollama`, macOS app bundle, Linux paths), overridable via `INTLLM_OLLAMA_EXECUTABLE`.
- **Server detection** — real HTTP health probe of the daemon endpoint.
- **Model detection** — live model inventory from the daemon; no hardcoded model lists.
- **Model management** — pull (with progress streaming), delete, set default, inspect; registry sync marks models removed from Ollama as uninstalled (not deleted).
- **Startup behavior** — INTLLM can start Ollama when a local executable/service is found: Windows service (`sc`), Linux systemd user service, or detached `ollama serve` spawn — always verified by a real health probe before reporting success (30 s start / 20 s stop budgets). Stop/restart are likewise verified. INTLLM never kills unrelated processes.
- **Honest failure** — if Ollama is unavailable, API calls fail with a clear `503 service_unavailable`; never fabricated output. The UI status endpoint reports `running | stopped | starting | stopping | unavailable | error` with version, model count, loaded models and VRAM when the daemon exposes them (N/A otherwise).

Troubleshooting (canonical):

| Symptom | Cause / Fix |
| --- | --- |
| `503 service_unavailable` | Ollama or PostgreSQL unavailable. Run `intllm doctor`. |
| `404 not_found` on a model | Model not installed in Ollama. Check the Models workspace. |
| INTLLM cannot start Ollama | Install Ollama (https://ollama.com) or set `INTLLM_OLLAMA_EXECUTABLE`. |
| Stream stalls | Model may still be loading; errors arrive as an SSE error frame followed by `data: [DONE]`. |

INTLLM does **not** bundle or silently install Ollama.

---

## 19. DATABASE

```text
PostgreSQL 14+
pgvector
```

The local PostgreSQL database with the pgvector extension is INTLLM's single persistence layer. Actual tables (from `backend/app/db/models.py`, schema revision `0001`):

| Category | Tables | Purpose |
| --- | --- | --- |
| Configuration metadata | `app_settings` | Key/value application settings (JSONB) |
| Models | `models` | Model registry: name, family, parameters, quantization, context length, memory requirement, tier, capabilities, installed flag, default flag |
| Conversations / messages | `conversations`, `messages` | Chat history; messages carry activities, sources, memory-used count |
| Memory | `memory_items`, `memory_sources`, `flash_index`, `hot_cache_metadata` | Layered memory: items with confidence/freshness/TTL, provenance, pgvector flash index, hot-cache promotion metadata |
| API keys | `api_keys` | Key metadata, salted scrypt hash, fingerprint, scopes, status, last-used |
| Background jobs | `background_jobs`, `job_events` | Maintenance job queue state and event log |
| Tool/audit/diagnostics | `tool_runs`, `browser_sessions`, `audit_events`, `diagnostics` | Tool execution records, browser session state, audit trail, diagnostics |

Startup verification (implemented): PostgreSQL reachable → database exists → pgvector available → schema initialized. If pgvector is missing, the database is reported as **misconfigured** with an actionable step — semantic memory never silently pretends to work.

Schema management: Alembic migrations when available (`backend/migrations`); SQLAlchemy metadata DDL fallback inside the packaged executable. Tables are never created by hand. Connection: `INTLLM_DATABASE_URL` (async, asyncpg) and `INTLLM_DATABASE_URL_SYNC`.

Default embedding width is 768; vectors that do not match are stored keyword-only.

---

## 20. LOCAL API

INTLLM provides a **local API gateway around the local runtime**. Requests route through the same INTLLM orchestrator (memory/security aware) rather than bypassing it.

Base URL:

```text
http://127.0.0.1:<INTLLM_PORT>/v1
```

(default port `8000`)

Authentication: `Authorization: Bearer <key>` or `x-api-key` header (see §21).

Implemented OpenAI-compatible endpoints (tested):

```text
GET  /v1/models                 # list installed models
GET  /v1/models/{model}         # retrieve one model
POST /v1/chat/completions       # stream: false (JSON) | stream: true (SSE)
```

Supported chat request fields: `model`, `messages`, `stream`, `temperature`, `top_p`, `max_tokens`, `stop`. Unknown fields are accepted and ignored (so clients with extra parameters still work).

INTLLM-specific extra body fields:

```text
intllm_use_brain  — include relevant long-term memory in context (default true)
intllm_use_web    — enable live web retrieval for this request (default false)
```

Streaming follows the OpenAI chunk format and terminates with `data: [DONE]`; errors arrive as an SSE error frame. Usage maps Ollama prompt/eval counters onto the OpenAI `usage` shape.

**Not implemented** and deliberately undocumented: `/v1/embeddings`, `/v1/responses`, audio, images, files, batches, fine-tuning. Do not claim them.

Technical schema: `/openapi.json`, `/docs` (Swagger UI), `/redoc`. The in-app **Docs** page is the user-facing reference.

Internal API (used by the web UI, prefix `/api` by default): health/ready, ollama status/start/stop/restart, system status + SSE stream, models (list/pull SSE/default/delete/recommend), chat (stream SSE + completions), conversations CRUD, brain (search/memories CRUD/cache invalidate), web (search/fetch), tools (list/run/permission), browser (status/action/stream), api-keys CRUD, background (status/stream/pause/resume), diagnostics.

---

## 21. API KEY

```text
INTLLM Local API Key
```

- **Generated locally** — `intllm_`-prefixed, high-entropy (`secrets.token_urlsafe(32)`).
- **Used for API authentication** — required on `/v1` endpoints; validated via constant-time comparison.
- **Stored securely** — only a salted **scrypt** hash (n=2¹⁴, r=8, p=1) plus a short 12-hex fingerprint is persisted. The raw key is never stored.
- **One-time reveal** — the full key is shown exactly once at creation and can never be retrieved again; the frontend only ever receives a masked fingerprint.
- **Revocable & labelled** — keys can be named, revoked, and track last-used time; scopes default to `chat` and `models.read`.
- **Never hardcoded, never exposed unnecessarily** — secrets are redacted from logs (redaction filter on all handlers, including the rotating file log) and never appear in frontend bundles, Git, or release artifacts.
- **Bootstrap rule** — while no key exists yet, loopback-only requests are allowed so the first key can be created from the UI. As soon as a key exists, authentication is required.

Example header (illustrative only — never include a real secret):

```text
Authorization: Bearer sk-intllm-...
# or
x-api-key: sk-intllm-...
```

> Note on prefix: the implemented generator uses `intllm_` (e.g. `intllm_AbC...`); historical docs/show copy sometimes display `sk-intllm-…`. On the website prefer `intllm_...` for accuracy.

---

## 22. DEVELOPER INTEGRATION

Actually implemented and test-covered:

- **OpenAI SDK (Python)** — documented with example code in the in-app Docs page (`OpenAI(base_url=..., api_key=...)`).
- **OpenAI SDK (JavaScript/TypeScript)** — documented with example code.
- **curl** — documented streaming and non-streaming examples.
- **Any OpenAI-compatible application** — works in principle via the `/v1` surface (chat completions + model listing are the implemented scope).

Compatible in principle / testing required (do **not** claim verified support):

- **Claude Code, Codex, SeedCode CLI** and other OpenAI-compatible CLI tools — the plan targets them ("Claude Code/Codex/SeedCode-compatible integration where protocol-compatible"), but the project explicitly does **not** claim tested compatibility with any specific third-party CLI unless verified against a build. Mark as *Compatible in principle / Testing required*.
- **Custom applications** — any HTTP client speaking the implemented `/v1` subset.

Unsupported: embeddings, responses API, audio, images, files, fine-tuning, batches.

---

## 23. INSTALLATION

Official installation commands:

### Windows (PowerShell)

```powershell
irm https://intllm.vercel.app/install.ps1 | iex
```

Downloads `INTLLM.exe` (or `INTLLM-Setup.exe` when `INTLLM_USE_SETUP=1` and the artifact is published), verifies its SHA256 against the release `SHA256.txt`, installs under `%LOCALAPPDATA%\Programs\INTLLM`, adds it to the user `PATH`, creates `intllm`/Start Menu/desktop shortcuts. Runtime data lives separately in `%LOCALAPPDATA%\INTLLM` and is preserved across upgrades and uninstall.

### Linux / macOS (bash)

```bash
curl -fsSL https://intllm.vercel.app/install.sh | bash
```

Downloads and verifies `intllm-<version>-py3-none-any.whl`, installs it into an isolated virtual environment at `~/.intllm`, and exposes an `intllm` command in `~/.local/bin`.

### Manual installation (Python package)

```bash
python -m pip install intllm     # from a release wheel / PyPI when published
```

Console scripts: `intllm` (CLI) and `intllm-api` (API server). Requires Python 3.11+.

### Development installation

```bash
git clone https://github.com/Alshahriar-07/INTLLM.git
cd INTLLM
npm install && npm run build          # build the web UI
python -m pip install -e "./backend[dev]"
```

### External dependencies (user-installed, INTLLM detects and reports them)

- Ollama installed and running with at least one model pulled (https://ollama.com)
- PostgreSQL 14+ with the pgvector extension
- Optional: Playwright (`backend[browser]`) for browser automation; Node.js 20+ for development only
- Windows 10/11 x64 for the packaged installer path

INTLLM does **not** bundle or silently install Ollama or PostgreSQL; the installer places INTLLM and reports what is missing.

---

## 24. INSTALLATION FLOW

```text
Install                      (user runs the one-liner or installer — automatic download + SHA256 verification)
 ↓
Detect environment           (architecture/OS check; per-user install dir; PATH/Start Menu setup)
 ↓
Detect Ollama                (automatic: health probe + executable search)
 ↓
Detect PostgreSQL            (automatic: reachability probe)
 ↓
Configure database           (automatic: INTLLM creates per-user dirs; connection from INTLLM_DATABASE_URL —
                              the PostgreSQL server itself is user-installed, a user-assisted step)
 ↓
Run migrations               (automatic: Alembic when available, metadata DDL fallback in packaged exe)
 ↓
Verify dependencies          (automatic: `intllm doctor` / /api/health reports real states with remediation steps)
 ↓
Start INTLLM                 (automatic: launcher starts uvicorn, resolves port conflicts without killing processes)
 ↓
Open local UI                (automatic: default browser opens when /api/health responds)
```

Automatic: environment detection, Ollama/PostgreSQL *detection* (not installation), schema creation/migrations, dependency verification, port-conflict fallback, UI auto-open.

User-assisted: installing Ollama and PostgreSQL/pgvector, pulling a first model, creating the first API key.

---

## 25. FIRST-RUN EXPERIENCE

What a new user experiences:

1. **Hardware detection** — the Overview/System workspace shows CPU, RAM, GPU/VRAM (via `psutil`/`nvidia-smi`), disk, OS. Undetectable values render as N/A.
2. **Ollama detection** — status (running/stopped/unavailable), version, model count; INTLLM can start it when found.
3. **Database setup** — on first start INTLLM verifies PostgreSQL reachability and pgvector; schema is created automatically. If pgvector is missing, an actionable remediation step is shown.
4. **Model detection** — the Models workspace lists whatever Ollama reports installed; a recommendation ranks models against the detected VRAM/RAM budget.
5. **Model recommendation** — tier labels (Potato / Nutral / I Paid for My Whole PC) and fit/utilization percentages from real hardware.
6. **API setup** — the user creates the first key in Settings → API; the full key is shown once.
7. **Local web UI** — the launcher opens the UI in the default browser once `/api/health` responds (10 s request timeout, 45 s readiness budget).
8. **First chat** — chat streams from the selected model; activities (brain lookup, web retrieval) are labelled in the response.
9. **System status** — the sidebar and System workspace show live service dots (Ollama engine, Postgres database, local runtime) and metrics.

---

## 26. WEB APP PAGES

### INTLLM application (implemented — `NavigationTab` in `src/types/index.ts`)

```text
Overview     (dashboard: hardware, services, quick actions)
Chat         (streaming chat with activities, sources, model selector)
Models       (Ollama inventory, pull/delete, tiers, recommendations)
Brain        (layered memory: search, create, stats)
Web          (live search / fetch workspace)
Browser      (Playwright session status and actions)
Tools        (tool registry, permissions, run)
API          (API key management — also reachable via Settings)
System       (service status, hardware metrics, diagnostics)
Docs         (in-app documentation: Overview, Quick Start, Local API, Authentication, Models,
              Chat Completions, OpenAI Compatibility, Ollama, Memory, Browser Tools,
              API Examples, Troubleshooting, Security)
Settings     (including the consolidated API section)
History      (conversation history — implemented via the Chat workspace's conversation list
              and the /api/conversations endpoints; not a separate top-level tab)
Memory       (the Brain tab)
```

### Public marketing website (planned — to be built)

```text
Home
Features
Architecture
Models
Documentation
API
Install
Security
GitHub
Releases
```

Only the application pages above exist today; the public site structure is the recommendation in §27.

---

## 27. PUBLIC WEBSITE STRUCTURE

Recommended official website information architecture:

```text
/
├── Home
├── Features
├── Architecture
├── Models
├── Docs
│   ├── Quick Start
│   ├── Installation
│   ├── Local API
│   ├── Memory
│   ├── Browser
│   ├── Tools
│   └── Security
├── Download / Install
├── Releases
├── GitHub
└── About
```

Content for Docs pages should be derived from the in-app Docs page sections (§26) and README, which describe only implemented endpoints and features.

---

## 28. HOMEPAGE CONTENT

### Hero

- **Name:** INTLLM
- **Concise product statement:** "The local-first AI runtime. Layered memory, live information, controlled tools and an OpenAI-compatible local API around your own local models." (adapt from §3/§4)
- **CTA:** Install INTLLM (→ §23 command) · View on GitHub
- **Local-first message:** "Runs on your machine. Conversations, model weights, embeddings and vector memory stay local by default. Nothing is sent to a cloud service unless you explicitly enable live web retrieval for a request." (verbatim-safe: this sentence is from the README)

### Product explanation
Use the 2–3 sentence version from §4. Explain: INTLLM is the runtime around the model, not the model itself.

### Architecture
Show the runtime layers from §8 (Web UI/API → FastAPI orchestrator → adapter/brain/tools/governor → Ollama → PostgreSQL). Keep the diagram monochrome and simple.

### Features
Highlight only real features (§46 copy bank): local chat with streaming, OpenAI-compatible API, API key system, layered memory, optional live retrieval with source attribution, tool gateway + browser agent, honest dependency reporting, background maintenance, Windows packaging.

### Model support
Explain model flexibility (§16): model list comes from the user's Ollama inventory; adapter keeps the runtime consistent while models change.

### Local API
Explain developer integration (§20): three implemented endpoints, streaming, INTLLM API keys, works with OpenAI SDKs.

### Memory
Explain Flash Brain (fast index/routing), Hot Cache (short-lived promoted results), Secondary Brain (durable pgvector store) — per §9–11. Include the "not continuous weight retraining" clarification.

### Browser/tools
Explain controlled tool access (§14–15): gateway flow, permission levels, disabled-by-default writes/terminal, untrusted web content as data.

### Installation
Show the two official commands from §23 verbatim in code blocks, plus the external-dependency note (Ollama, PostgreSQL, pgvector are user-installed).

### Security
Explain the local-first security model (§35): localhost binding, hashed keys, redacted logs, explicit opt-ins, tool permissions. No absolute-security claims.

### Footer
Include: GitHub · Documentation · Releases · License (PolyForm Noncommercial 1.0.0) · Version (current version from §44). Link targets from §43.

**Do not write exaggerated marketing claims.**

---

## 29. BRANDING

The `assets/` directory is the source of truth. Official assets (do **not** recreate the logo in CSS):

- **Primary logo (transparent raster):** `assets/png/INTLLM-logo-transparent.png`
- **Vector logo:** `assets/INTLLM-brand-assets/svg/INTLLM-logo.svg`
- **Dark-background logo (white):** `assets/png/INTLLM-logo-white.png` / `assets/INTLLM-brand-assets/svg/INTLLM-logo-white.svg`
- **Light-background logo (on white):** `assets/png/INTLLM-logo-on-white.png`
- **Logo on black:** `assets/png/INTLLM-logo-on-black.png` / `INTLLM-logo-on-dark.png`
- **Icon:** `assets/INTLLM-brand-assets/svg/INTLLM-icon.svg`, `assets/ico/INTLLM.ico` (multi-size Windows/favicon ICO), `assets/png/INTLLM-icon-{128,256,512,1024}.png`, `assets/png/INTLLM-app-icon.png`
- **Emblem-only transparent mark:** `assets/png/INTLLM-emblem-transparent-1024.png`
- **OG image:** `assets/banners/INTLLM-open-graph-1200x630.png`
- **GitHub social preview:** `assets/banners/INTLLM-github-social-1280x640.png`
- **General banner:** `assets/banners/INTLLM-banner-1600x500.png`
- **Brand guide:** `assets/docs/BRAND_GUIDE.md`

Usage rules (from the brand guide):

- Light UI: primary transparent logo / dark wordmark. Dark UI: white logo variant or icon.
- App/favicon: `INTLLM.ico` or `INTLLM-icon.svg`.
- Do not stretch, rotate, add drop shadows, or recolor the primary mark.

The `public/assets/` directory mirrors these for web serving; the app favicon is wired in `index.html`.

---

## 30. VISUAL DESIGN DIRECTION

The website should follow the same visual philosophy as the application.

Primary visual language:

```text
White
Black
Ash
Gray
```

Light mode:

```text
Bright · White · Clean · Minimal
(light surfaces #FAFAFA/#FFFFFF, near-black text #171717, light gray borders #E5E5E5)
```

Dark mode:

```text
Near Black · Black · Ash · White
(canvas #050505, surfaces #0A0A0A–#141414, borders #262626–#404040, text #F5F5F5)
```

(Values above are the actual design tokens from `src/index.css`.)

Avoid:

- neon gradients
- generic AI purple/blue gradients
- excessive glassmorphism
- fake futuristic effects
- giant rounded cards (the app uses a restrained radius scale: 2–12 px)
- excessive glow
- colorful dashboard aesthetics

The product should feel:

```text
Professional
Technical
Minimal
Precise
Mature
Local-first
Developer-focused
```

Typography (as implemented): **Inter** for UI text, **JetBrains Mono** for code. Syntax highlighting is grayscale. Motion is subtle (140–180 ms ease-out); respect `prefers-reduced-motion`.

---

## 31. BRAND COLORS

Reference: `assets/docs/BRAND_GUIDE.md`. The current brand accent colors remain part of the identity, **but the main UI/website is monochrome**:

```text
Cyan:   #16C8FF
Blue:   #2563EB
Violet: #7C2CFF
Dark:   #090D16
Wordmark dark: #111827
White:  #FFFFFF
```

Important: these accents should **NOT** dominate the UI. The primary interface language is:

```text
Black + White + Ash
```

Accent colors may appear sparingly (e.g. status semantics: success/warning/error, small badges) — mirroring the app, where semantic colors are "used sparingly" by design-token comment.

---

## 32. SEO DATA

### Site title

```text
INTLLM — Local-First AI Runtime for Ollama Models
```

(App title currently in `index.html`: "INTLLM — Local Intelligence Operating Environment"; either is acceptable, keep one consistently per page.)

### Meta description

```text
INTLLM is a local-first AI runtime that gives local Ollama models layered memory,
live web retrieval, controlled browser tools and an OpenAI-compatible local API —
with your data staying on your machine.
```

### Keywords

Relevant, non-spammy:

```text
INTLLM
local AI
local LLM
Ollama
AI runtime
local AI runtime
OpenAI compatible local API
local AI memory
AI browser agent
local AI tools
local-first AI
pgvector
FastAPI AI backend
```

### Open Graph

- **og:title:** INTLLM — Local-First AI Runtime for Ollama Models
- **og:description:** the 1-sentence description from §4
- **og:image:** `https://intllm.vercel.app/assets/banners/INTLLM-open-graph-1200x630.png` (1200×630)
- **og:url:** `https://intllm.vercel.app/`
- **og:type:** website

### Twitter/X metadata

- **twitter:card:** summary_large_image
- **twitter:title:** same as og:title
- **twitter:description:** same as og:description
- **twitter:image:** same as og:image

### Canonical URL

```text
https://intllm.vercel.app/
```

---

## 33. SEARCH INTENT

What people might search for:

```text
INTLLM
INTLLM AI
INTLLM Ollama
local AI runtime
Ollama AI runtime
OpenAI compatible local API
local LLM memory
local AI browser agent
run AI locally
local AI API
```

**Do not keyword-stuff the website.** Use each term naturally in the section where it is factually relevant.

---

## 34. SOCIAL SHARING

Official social assets (actual files and dimensions):

| Asset | File | Dimensions |
| --- | --- | --- |
| Open Graph image | `assets/banners/INTLLM-open-graph-1200x630.png` | 1200×630 |
| GitHub social preview | `assets/banners/INTLLM-github-social-1280x640.png` | 1280×640 |
| General banner | `assets/banners/INTLLM-banner-1600x500.png` | 1600×500 |
| Logo | `assets/png/INTLLM-logo-transparent.png` (+ variants) | 1024-class raster |
| Icon | `assets/ico/INTLLM.ico`, `assets/png/INTLLM-icon-*.png` | 128–1024 |

Serve banners from the site (e.g. `/assets/banners/…`) and reference absolute URLs in OG/Twitter tags.

---

## 35. SECURITY POSITIONING

Explain security honestly. Key principles (all implemented):

```text
Local by default
No hidden cloud sync
Local API bound to localhost by default
Explicit network exposure (INTLLM_HOST opt-in)
API authentication (hashed keys, constant-time verification)
Secure key storage (salted scrypt + fingerprint only; one-time reveal)
Tool permissions (read-only / requires-approval / restricted; risk levels)
Untrusted web content isolation (treated as data, not instructions; SSRF guards)
```

Additional implemented measures: restricted CORS origins, 10 MiB default request-body limit with early 413 rejection, input validation with a consistent structured error contract, secret redaction in all logs, audit events for key creation/revocation, structured JSON file logging with redaction filter.

**Do not claim absolute security or absolute privacy.** Suggested honest framing: "INTLLM is designed to keep data and execution local by default, and to make every privileged action explicit — but local does not automatically mean safe; tool permissions and dependencies remain the user's responsibility to configure."

---

## 36. PRIVACY

INTLLM is designed around local-first operation. Clarifications:

- **Local conversations** — chat history is stored in the local PostgreSQL database (`conversations`, `messages`).
- **Local database** — PostgreSQL runs on the user's machine (`127.0.0.1:5432` by default); there is no INTLLM-hosted database.
- **Local memory** — memory items, embeddings (pgvector) and caches live in the same local database.
- **Local model execution** — inference happens through the local Ollama daemon; no model calls leave the machine.
- **Internet access only when enabled/required by the user** — live retrieval is off by default and explicitly enabled per request; the only automatic outbound probes are health checks (e.g. the web-provider reachability probe, cached 30 s) that do not send user content.
- **No hidden synchronization** — there is no cloud sync, telemetry pipeline, or account system.

---

## 37. PERFORMANCE

**No official benchmark published yet.**

If/when benchmarks exist, document them with: hardware, model, quantization, context length, task, benchmark method, and result. Do not publish arbitrary numbers.

Factual, non-benchmark implementation notes that may be stated:

- Streaming is SSE-based; first tokens arrive as the model generates.
- L0 flash lookup is designed as a fast path (sub-15 ms target from the plan; the implementation reports real per-layer latencies in lookup results and the UI).
- API keys are hashed with scrypt parameters chosen for ~16 MB / ~50 ms on typical hardware (a deliberate cost, not a latency claim).
- Scrypt hash timing and background thresholds are configurable; interactive latency is measured and reported (`X-Process-Time-Ms` header, activity `latencyMs`).

---

## 38. ROADMAP

Concise roadmap from `INTLLM-PLAN/16-roadmap/ROADMAP.md` and the implemented state:

### Current (implemented in 1.0.2)

- FastAPI backend, React/Vite web UI, PostgreSQL + pgvector, migrations, health checks
- Ollama detection, model list/pull/delete, adapter, streaming chat, conversation persistence
- L2 memory, L0 Flash Brain, L1 Hot Cache, memory scoring, TTL, pgvector
- Web search, page extraction, source tracking, trust scoring, verification, context builder
- Tool gateway, Playwright browser agent (optional), permission system, controlled actions
- API keys, OpenAI-compatible endpoints (`/v1/models`, `/v1/chat/completions`), streaming
- Background learner queue, resource governor, verification/refresh/index/cleanup jobs, pause/resume
- Windows packaging (PyInstaller exe + Inno Setup installer), release engineering, CI/CD

### Next (planned — specified, not implemented)

- Automatic post-response memory candidate → verify → promote pipeline (learning from conversations)
- Duplicate detection, memory compression, failed-workflow analysis as background jobs
- Read-only browser workflow maturation, richer browser workflows (form filling, structured interaction)
- Model registry expansion / compatibility scoring from the plan's model-registry design
- Memory export/import

### Future

- Better model routing (multi-runtime routing)
- Advanced agent planning, autonomous complex browser workflows
- Optional model fine-tuning / adapter experiments
- Distributed/cloud mode
- Additional model adapters beyond Ollama

**Do not present speculative features as shipped.**

---

## 39. CURRENT STATUS

Machine-readable status section (populated from the actual repository state):

```yaml
project:
  name: INTLLM
  website: https://intllm.vercel.app
  github: https://github.com/Alshahriar-07/INTLLM
  repository: https://github.com/Alshahriar-07/INTLLM.git
  version: "1.0.2"
  status: development

features:
  local_runtime: implemented          # FastAPI orchestrator + launcher + CLI
  web_ui: implemented                 # React/TS/Vite SPA, 11 workspace tabs
  ollama: implemented                 # detection, control, adapter, model management
  postgres: implemented               # conversations, memory, keys, jobs, audit
  pgvector: implemented               # L0 flash index embeddings, vector search
  layered_memory: implemented         # L0 flash / L1 hot cache / L2 secondary brain
  live_web_retrieval: implemented     # DuckDuckGo default, SearXNG optional; opt-in per request
  tool_gateway: implemented           # 12-tool registry, permission levels, risk levels
  browser_agent: experimental         # implemented via optional Playwright dependency
  openai_local_api: implemented       # /v1/models, /v1/models/{model}, /v1/chat/completions (SSE)
  api_keys: implemented               # scrypt hashes, one-time reveal, revocation, scopes
  docs_page: implemented              # in-app Docs workspace, 13 sections
  background_learning: implemented    # maintenance jobs + resource governor (NOT weight retraining)
  hardware_detection: implemented     # psutil + nvidia-smi; honest N/A when undetectable
  model_recommendation: implemented   # tier + fit ranking vs VRAM/RAM budget
  memory_candidate_pipeline: planned  # auto learn-from-conversation (verify → promote)
  duplicate_detection: planned
  memory_compression: planned
  memory_export_import: planned
  advanced_browser_workflows: planned # form filling, structured interaction
  multi_runtime_routing: future
  model_fine_tuning: future

cli:
  intllm: implemented                 # start / serve / doctor / version
  intllm-api: implemented

packaging:
  windows_exe: implemented            # INTLLM.exe (PyInstaller onefile, built by CI)
  windows_setup: implemented          # INTLLM-Setup.exe (Inno Setup; built when iscc available)
  wheel: implemented                  # intllm-<version>-py3-none-any.whl
  source_archive: implemented         # intllm-<version>.tar.gz
  sha256_manifest: implemented        # SHA256.txt, generated and re-verified in CI
  install_scripts: implemented        # install.ps1 / install.sh served from the site

release:
  current_version: "1.0.2"
  release_date: 2026-10-01
  first_public_release: v1.0.1        # designated by the project owner; see §53
  windows_x64: planned                # first tagged GitHub release
  setup_exe: planned
  wheel: planned
  source_archive: planned
```

> Note on `first_public_release: v1.0.1`: the project owner designated **v1.0.1** as the first official public release/tag (§53). The repository's authoritative version source currently reports **1.0.2**. Until a `v1.0.1` tag exists in the repository, the website must not claim v1.0.1 artifacts are downloadable; use "latest release" links that resolve dynamically (the installers resolve the latest release via the GitHub API, which makes them forward-compatible).

---

## 40. TERMINOLOGY

Canonical glossary. For every term: preferred wording, short definition, wording to avoid.

| Term | Preferred wording | Short definition | Avoid |
| --- | --- | --- | --- |
| INTLLM | INTLLM | The local-first AI runtime; the orchestration layer around local models. | "INTLLM AI", "the model" |
| Runtime | INTLLM runtime | The FastAPI backend + services that orchestrate memory, tools, retrieval and models. | "server" (ambiguous), "engine" |
| Model Adapter | Model Adapter | Uniform interface between the runtime and Ollama (list/pull/chat/stream/embeddings/health). | "driver" |
| Flash Brain | L0 Flash Brain | Fast routing/index layer over memory; answers availability/freshness/confidence. Not the full knowledge store. | "the brain that thinks", "knowledge base" |
| Hot Cache | L1 Hot Cache | Short-lived cache of recently useful query results with TTL. | "RAM memory" |
| Secondary Brain | L2 Secondary Brain | Durable curated knowledge store in PostgreSQL + pgvector with provenance and freshness. | "database of everything", "it stores every webpage" |
| Background Learner | Background maintenance / Background Learner | Low-priority memory/index/knowledge maintenance that yields to user requests. | "self-training", "continuous learning" |
| Tool Gateway | Tool Gateway | Validation → policy → permission → execution → sanitization layer for every tool call. | "plugin system" |
| Browser Agent | Browser Agent | Optional Playwright-driven browser automation behind the gateway. | "autonomous surfer" |
| Local API | INTLLM Local API | The OpenAI-compatible HTTP API at `http://127.0.0.1:<port>/v1`. | "cloud API" |
| OpenAI-compatible | OpenAI-compatible local API | Implements the chat-completions and models subset locally; not affiliated with OpenAI. | "OpenAI API" |
| Ollama | Ollama | External local LLM runtime used for inference and model management. | "INTLLM's model" |
| pgvector | pgvector | PostgreSQL extension providing vector similarity search for embeddings. | "the vector DB" |
| Memory | Memory / layered memory | The L0/L1/L2 knowledge system used to give models relevant context. | "training data" |
| Freshness | Freshness score | 0–100 score decaying with age against a TTL policy; drives stale/verify decisions. | "accuracy" |
| TTL | TTL (time-to-live) | Per-policy lifetime for memory items (static→live; ~1 year → 6 hours). | "expiry date" (loosely ok) |
| Hardware Tier | Hardware recommendation tier | Potato / Nutral / I Paid for My Whole PC — recommendations, not restrictions. | "minimum requirements" |

---

## 41. WORDING RULES

Preferred:

```text
local-first
local AI runtime
local model
memory layer
knowledge maintenance
background maintenance
live information retrieval
controlled browser access
OpenAI-compatible local API
recommendation tier
honest status reporting
```

Avoid misleading wording:

```text
self-training AI
AGI
human-level AI
GPT replacement
unlimited intelligence
always learns like a human
continuously retrains itself
guaranteed smarter
cloud-powered
unbreakable security
```

---

## 42. WEBSITE CONTENT RULES

The website must:

- use real features
- avoid fake statistics
- avoid fake testimonials
- avoid fake user counts
- avoid fake benchmarks
- avoid fake integrations
- avoid fake screenshots (use real assets from `assets/`; UI screenshots only from the actual app)
- avoid placeholder copy
- avoid unsupported claims

If information is unknown, say:

```text
Not yet available
```

or omit it.

---

## 43. LINKS

Canonical links (actual URLs from the repository/installers — do not invent others):

```text
Official Website:      https://intllm.vercel.app
GitHub Repository:     https://github.com/Alshahriar-07/INTLLM
Repository (clone):    https://github.com/Alshahriar-07/INTLLM.git
Documentation:         https://intllm.vercel.app  (in-app Docs page; public docs to be hosted on the site)
Releases:              https://github.com/Alshahriar-07/INTLLM/releases
Latest release:        https://github.com/Alshahriar-07/INTLLM/releases/latest
Install script (Win):  https://intllm.vercel.app/install.ps1
Install script (nix):  https://intllm.vercel.app/install.sh
Issues:                https://github.com/Alshahriar-07/INTLLM/issues
License:               https://github.com/Alshahriar-07/INTLLM/blob/main/LICENSE
Ollama:                https://ollama.com
```

The website itself is served by Vercel (see `vercel.json`: the Vite app at the root with `/install.ps1` and `/install.sh` served from `public/`).

---

## 44. RELEASE INFORMATION

Actual current project version (authoritative source `backend/app/__init__.py`, mirrored in `package.json`, `RELEASE.md`, `CHANGELOG.md`):

```text
Current version: 1.0.2
Release date:    2026-10-01
Latest release URL: https://github.com/Alshahriar-07/INTLLM/releases/latest
```

**First official public release (per project owner designation, §53): v1.0.1.** The repository does not yet contain a `v1.0.1` tag or GitHub release; until it exists, the website should link to the dynamic "releases/latest" URL rather than naming artifacts of a specific tag.

Artifact names (as built by `scripts/build_release.py` and the release workflow):

```text
INTLLM.exe
INTLLM-Setup.exe                  # built when Inno Setup's iscc is available
intllm-<version>-py3-none-any.whl
intllm-<version>.tar.gz
SHA256.txt
```

Installation methods: Windows one-liner (PowerShell), Linux/macOS one-liner (bash), pip wheel, from-source development build (§23).

SHA256 availability: **yes** — a `SHA256.txt` manifest is generated for every artifact set (`scripts/make_sha256.py`) and re-verified by the release workflow (`scripts/validate_release.py`, including a wheel install + `intllm --version` check). Installers verify checksums before use. Users can verify:

```bash
sha256sum -c SHA256.txt                    # Linux/macOS
Get-FileHash .\INTLLM.exe -Algorithm SHA256   # Windows PowerShell
```

The version is single-sourced from `backend/app/__init__.py`; the release tag must match it (enforced by the release workflow).

---

## 45. LICENSE

**PolyForm Noncommercial License 1.0.0.** Copyright © 2026 Al Shahriar Sowan. See [`LICENSE`](LICENSE).

(The repository license file was read directly; do not assume any other license.)

---

## 46. WEBSITE ASSET MAP

| Asset | Location | Purpose |
| --- | --- | --- |
| Main Logo (transparent) | `assets/png/INTLLM-logo-transparent.png` | Header (light UI) |
| Vector Logo | `assets/INTLLM-brand-assets/svg/INTLLM-logo.svg` | Header / scalable uses |
| White Logo | `assets/png/INTLLM-logo-white.png` (+ `svg/INTLLM-logo-white.svg`) | Dark mode header |
| On-white Logo | `assets/png/INTLLM-logo-on-white.png` | Light marketing sections |
| Icon (SVG) | `assets/INTLLM-brand-assets/svg/INTLLM-icon.svg` | Inline icon / scalable |
| Icon (ICO) | `assets/ico/INTLLM.ico` | Favicon / Windows app icon |
| Icon (PNG) | `assets/png/INTLLM-icon-{128,256,512,1024}.png` | Favicon/app store sizes |
| Emblem | `assets/png/INTLLM-emblem-transparent-1024.png` | Emblem-only mark |
| OG Image | `assets/banners/INTLLM-open-graph-1200x630.png` | Social sharing (1200×630) |
| GitHub Banner | `assets/banners/INTLLM-github-social-1280x640.png` | GitHub/social preview (1280×640) |
| General Banner | `assets/banners/INTLLM-banner-1600x500.png` | Hero/social banners (1600×500) |
| Brand Guide | `assets/docs/BRAND_GUIDE.md` | Design reference |
| Served copies | `public/assets/…` (mirror of the above) | Web-served assets |

---

## 47. WEBSITE COPY BANK

Reusable canonical copy. Use verbatim or lightly edit without changing meaning.

**Hero title:**
> INTLLM — The local-first AI runtime

**Hero subtitle:**
> Layered memory, live information, controlled tools and an OpenAI-compatible local API around your own local models. Runs entirely on your machine.

**CTA (primary):**
> Install INTLLM

**CTA (secondary):**
> View on GitHub

**About section:**
> INTLLM is a local-first AI runtime built around local models served by Ollama. It does not retrain the base model for every new fact — instead it supplies current context, tools, memory and orchestration around the model, while user responses always have priority over background work.

**Features (six short blurbs):**
> - **Local chat with streaming** — talk to any model in your Ollama inventory, with token streaming and activity labels.
> - **OpenAI-compatible local API** — `/v1/models` and `/v1/chat/completions` (streaming SSE), routed through the same runtime as the UI.
> - **Layered memory** — L0 Flash Brain, L1 Hot Cache and L2 Secondary Brain in local PostgreSQL + pgvector, with confidence and freshness scoring.
> - **Live information retrieval** — optional per-request web search with source attribution, trust scores and SSRF protection.
> - **Controlled tools** — a permission-gated tool gateway for browser automation and workspace-scoped filesystem access.
> - **Honest status reporting** — PostgreSQL, pgvector and Ollama states are detected and reported; nothing is fabricated.

**Architecture section:**
> The web UI and the OpenAI-compatible API both talk to a FastAPI orchestrator. Around the model it runs the model adapter, the three memory layers, the tool gateway, the optional browser agent and live retrieval, a resource governor, and a low-priority background maintenance worker — with PostgreSQL + pgvector as the single local persistence layer.

**Memory section:**
> Flash Brain is the fast routing/index layer that answers whether useful memory exists, where it is, how fresh and how confident it is. The Hot Cache keeps recently useful results immediately available. The Secondary Brain is the durable store of compact, verified knowledge with sources and freshness policies. Background maintenance keeps indexes and freshness current — it is knowledge maintenance, not model retraining.

**Local API section:**
> Point any OpenAI-compatible client at `http://127.0.0.1:8000/v1` with an INTLLM API key. Implemented endpoints: `GET /v1/models`, `GET /v1/models/{model}`, `POST /v1/chat/completions` (streaming and non-streaming). Endpoints that are not implemented are not exposed and not documented.

**Installation section (Windows):**
> ```powershell
> irm https://intllm.vercel.app/install.ps1 | iex
> ```

**Installation section (Linux/macOS):**
> ```bash
> curl -fsSL https://intllm.vercel.app/install.sh | bash
> ```
> PostgreSQL and Ollama are external local dependencies — INTLLM detects and reports them; it never bundles or silently installs them.

**Security section:**
> The API binds to localhost by default; LAN exposure is an explicit opt-in. API keys are salted scrypt hashes with one-time reveal and revocation. Secrets are redacted from logs and never ship in frontend bundles. Tool and browser execution always passes through the permission gateway, and retrieved web content is treated as data, not instructions.

**Footer:**
> INTLLM · GitHub · Documentation · Releases · License (PolyForm Noncommercial 1.0.0) · v1.0.2 *(update with the current release)*

**Docs intro:**
> Everything INTLLM actually implements — the local OpenAI-compatible API, authentication, memory and tools. No unsupported endpoints are documented. (This sentence is the real intro line from the in-app Docs page.)

---

## 48. WEBSITE CTA

Canonical CTA labels:

```text
Install INTLLM
View Documentation
View on GitHub
Download for Windows
Explore the API
Read the Architecture
Check the Releases
Run intllm doctor
```

Do **not** use vague CTAs such as:

```text
Get Started Now!!!
Unlock the Future!!!
Experience AI!!!
```

---

## 49. FAQ DATA

Factual FAQ entries (answers reflect actual implementation):

**What is INTLLM?**
INTLLM is a local-first AI runtime: a FastAPI backend, web UI, layered memory, tools and an OpenAI-compatible local API built around local models served by Ollama. It is the orchestration layer around the model, not a model itself.

**Does INTLLM run locally?**
Yes. The backend, database, memory, models and UI run on your machine. The API binds to `127.0.0.1` by default.

**Does INTLLM use Ollama?**
Yes — Ollama is the core local model runtime. INTLLM detects the daemon, lists/pulls/deletes models, and streams inference through it. Ollama is installed separately; INTLLM never bundles or silently installs it.

**Does INTLLM require internet?**
No. It works fully offline except for the features you explicitly enable: live web retrieval is opt-in per request. Model inference and memory are local.

**Where is my data stored?**
In your local PostgreSQL database (with pgvector), on your machine. There is no cloud sync and no INTLLM-hosted storage. Windows installs keep runtime data in `%LOCALAPPDATA%\INTLLM`.

**What models can I use?**
Whatever your local Ollama installation reports — e.g. Qwen, Llama, DeepSeek or other compatible families. INTLLM does not hardcode or invent models. Feature support varies per model (e.g. embeddings need an embedding-capable model).

**Does INTLLM support OpenAI-compatible APIs?**
Yes, locally. Implemented endpoints: `GET /v1/models`, `GET /v1/models/{model}`, `POST /v1/chat/completions` (streaming SSE and non-streaming). Embeddings, responses, audio and images are not implemented and not exposed.

**What is Flash Brain?**
The L0 layer: a fast routing/index layer over memory. It answers whether useful memory is available, where, how fresh, and how confident — it is not the complete knowledge store.

**What is Secondary Brain?**
The L2 layer: the durable store of curated, verified knowledge (facts, workflows, lessons) in PostgreSQL + pgvector, with sources, confidence and freshness metadata.

**Does INTLLM retrain models?**
No. INTLLM performs low-priority background *knowledge maintenance* (verification, freshness, index updates, cache cleanup). It never retrains Ollama model weights.

**Can I use INTLLM with coding tools?**
Any client that speaks the implemented OpenAI-compatible chat surface can point at the local `/v1` endpoint with an INTLLM API key. INTLLM does not claim tested compatibility with specific third-party CLIs unless verified against a build.

**How do I install INTLLM?**
Windows: `irm https://intllm.vercel.app/install.ps1 | iex` · Linux/macOS: `curl -fsSL https://intllm.vercel.app/install.sh | bash`. You will also need Ollama and PostgreSQL with pgvector installed separately.

**What hardware do I need?**
INTLLM gives recommendation tiers — Potato, Nutral, I Paid for My Whole PC — based on detected CPU/RAM/GPU/VRAM. They are recommendations, not strict restrictions; what matters most is fitting the model's memory requirement within your VRAM/RAM budget.

---

## 50. WEBSITE DEVELOPMENT HANDOFF

Read INTLLM-DATA.md first.

Then inspect:

- `assets/` (brand source of truth)
- `README.md`
- `INTLLM-PLAN/`
- API documentation (`/openapi.json` on a running instance; the in-app Docs page source `src/components/docs/DocsDashboard.tsx`)

Rules:

- Use this file as the canonical content reference.
- Do not invent product functionality.
- Use the existing brand assets (§29, §46); do not recreate the logo in CSS.
- Follow the monochrome visual system (§30–31).
- Keep technical claims synchronized with the backend: only the three `/v1` endpoints exist; `browser_agent` is experimental (optional Playwright); writes/terminal tools are disabled by default; benchmarks/user counts do not exist.
- Update INTLLM-DATA.md whenever major public-facing product information changes (§51).

---

## 51. MAINTENANCE RULE

Whenever any of these change:

```text
Feature
API
Architecture
Installation
Branding
Website
Release
Model support
Security
Pricing
License
Roadmap
```

review and update:

```text
INTLLM-DATA.md
```

This file must remain synchronized with the actual product. The authoritative version lives in `backend/app/__init__.py`; when it changes, update §2, §39, §44, §47 (footer version) and §32 where applicable in the same change.

---

## 52. OFFICIAL PROJECT LINKS

Canonical public project references:

### Official Website

```text
https://intllm.vercel.app
```

### Official GitHub Repository

```text
https://github.com/Alshahriar-07/INTLLM.git
```

Repository display URL:

```text
https://github.com/Alshahriar-07/INTLLM
```

Do not invent or replace the repository URL.

---

## 53. RELEASE INFORMATION

The designated first official INTLLM release is:

```text
v1.0.1
```

Release tag:

```text
v1.0.1
```

Treat `v1.0.1` as the first public release version **unless the repository contains authoritative release metadata that explicitly supersedes this**. Current repository state: the authoritative version source reports `1.0.2` — so the website may state "first public release: v1.0.1" as the designated version, but must not present v1.0.1 artifacts as existing until the tag is published, and must not claim v1.0.1 contains features not present in the corresponding build.

The website must use this information consistently across:

- homepage
- download page
- releases page
- documentation
- footer
- SEO metadata where appropriate
- GitHub links
- installation instructions
- release information
- API documentation where version information is shown

Practical rule for the website: always link releases via `https://github.com/Alshahriar-07/INTLLM/releases/latest` (and let the installers resolve the latest tag via the GitHub API, which they already do), so version references stay correct automatically.

---

## 54. CANONICAL PROJECT METADATA

Keep the following metadata synchronized:

```yaml
project:
  name: INTLLM
  website: https://intllm.vercel.app
  github: https://github.com/Alshahriar-07/INTLLM
  repository: https://github.com/Alshahriar-07/INTLLM.git

release:
  first_public_release: v1.0.1
  first_public_tag: v1.0.1
  current_code_version: "1.0.2"   # authoritative: backend/app/__init__.py
```

Do not invent a different first-release version.

---

## 55. RELEASE WEBSITE CONTENT

The public website should be able to communicate:

```text
Latest Release
v1.0.1        # once the tag exists; until then show the latest published release
```

and provide a GitHub repository link (`https://github.com/Alshahriar-07/INTLLM`).

Do not claim that `v1.0.1` contains features that are not actually present in that release. If the repository contains release notes or a GitHub release for `v1.0.1`, use those as the authoritative source for release-specific features. Until then, feature claims must stay limited to what is in the code (see §38 "Current").

---

## 56. VERSIONING RULE

INTLLM follows semantic-style versioning:

```text
MAJOR.MINOR.PATCH
```

The first public release is:

```text
v1.0.1
```

The version is **single-sourced** from `backend/app/__init__.py` (`__version__`); the release workflow verifies that the git tag matches it. `package.json` mirrors it for the frontend. Future releases should update the version consistently across:

- source code (`backend/app/__init__.py`)
- package metadata (`backend/pyproject.toml` dynamic version, `package.json`)
- CLI (`intllm --version`)
- API (`/api/health`, `/` meta endpoint, `/openapi.json`)
- executable (`INTLLM.exe --version`)
- installer (`INTLLM-Setup.exe`, Inno Setup `AppVersion`)
- wheel + source archive (`intllm-<version>-…`)
- documentation (README, RELEASE.md, CHANGELOG.md, in-app Docs)
- GitHub release/tag
- website (footer, download page)
- INTLLM-DATA.md (§2, §39, §44, §47)

Never maintain conflicting version numbers across these surfaces.
