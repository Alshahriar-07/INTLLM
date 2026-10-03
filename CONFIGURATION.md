# INTLLM Configuration

All configuration is via environment variables. `backend/.env.example` contains
the full annotated list; copy it to `.env` for local development. Never commit a
populated `.env`.

The packaged desktop application reads the same variables from the environment.
Persistent settings that can be changed in the UI (API access mode, Agent
workspace, permission mode) are stored in the database (`app_settings`).

---

## Application

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_ENV` | `development` | Environment label |
| `INTLLM_HOST` | `127.0.0.1` | Loopback bind address |
| `INTLLM_PORT` | `8000` | API/UI port (valid TCP range) |
| `INTLLM_LOG_LEVEL` | `INFO` | Logging level |
| `INTLLM_API_PREFIX` | `/api` | Internal management API prefix |
| `INTLLM_CORS_ORIGINS` | `http://127.0.0.1:3000,http://localhost:3000` | Allowed CORS origins |
| `INTLLM_MAX_REQUEST_BYTES` | `10485760` | Request body size limit (10 MiB) |

## Local / LAN API access

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_API_ACCESS_MODE` | `local` | `local` (loopback) or `lan` |
| `INTLLM_API_LAN_HOST` | `0.0.0.0` | Interface used when LAN access is enabled |

The access mode can also be set in **Settings → API**; the choice is persisted
and applied on the next launch.

## Runtime endpoint (advertised, non-secret)

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_RUNTIME_HOST` | `127.0.0.1` | Advertised host (informational) |
| `INTLLM_RUNTIME_PORT` | (empty) | Advertised port; empty = use `INTLLM_PORT` |
| `INTLLM_RUNTIME_BASE_URL` | (empty) | Advertised base URL |

The backend binds a real localhost TCP port (`INTLLM_PORT`, default `8000`);
the desktop launcher resolves conflicts by picking the next free port and
exports it as `INTLLM_EFFECTIVE_PORT`. Port values outside the valid TCP range
(1–65535) are rejected at startup — historically an invalid `240426` value
existed and is now hard-rejected with a clear error.

## PostgreSQL

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_DATABASE_URL` | `postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm` | Async URL |
| `INTLLM_DATABASE_URL_SYNC` | `postgresql+psycopg://intllm:intllm@127.0.0.1:5432/intllm` | Sync URL (tooling) |
| `INTLLM_DB_CONNECT_TIMEOUT_SECONDS` | `5` | Connect/command timeout |
| `INTLLM_DB_AUTO_CREATE` | `true` | Create a missing database (`CREATE DATABASE` only) |

## Ollama

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama daemon endpoint |
| `INTLLM_OLLAMA_TIMEOUT_SECONDS` | `120` | Request timeout |
| `INTLLM_OLLAMA_EXECUTABLE` | (auto) | Explicit Ollama executable path |
| `INTLLM_DEFAULT_MODEL` | (empty) | Default model; empty = auto-detect |

## Data / workspace

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_DATA_DIR` | `./data` | Data directory |
| `INTLLM_WORKSPACE_DIR` | `./workspace` | Default workspace directory |
| `INTLLM_FILESYSTEM_ALLOWLIST` | `./workspace` | Allow-list of directories for filesystem tools |

In the packaged app these default to the per-user data directory
(`%LOCALAPPDATA%\INTLLM`) when not overridden.

## Agent

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_AGENT_TERMINAL_ENABLED` | `true` | Enable terminal execution |
| `INTLLM_AGENT_TERMINAL_TIMEOUT_SECONDS` | `60` | Command timeout |
| `INTLLM_AGENT_MAX_READ_BYTES` | `200000` | Max bytes returned by a read |
| `INTLLM_AGENT_MAX_WRITE_BYTES` | `2000000` | Max bytes written |
| `INTLLM_AGENT_MAX_SEARCH_RESULTS` | `200` | Max search matches |

## Web retrieval

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_WEB_PROVIDER` | `duckduckgo` | `duckduckgo` (no key) or `searxng` |
| `INTLLM_WEB_SEARXNG_URL` | (empty) | SearXNG instance URL |
| `INTLLM_WEB_TIMEOUT_SECONDS` | `15` | Retrieval timeout |
| `INTLLM_WEB_MAX_RESULTS` | `8` | Max results |

## Browser

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_BROWSER_ENABLED` | `true` | Enable browser tools |
| `INTLLM_BROWSER_HEADLESS` | `true` | Run headless |
| `INTLLM_BROWSER_TIMEOUT_SECONDS` | `30` | Operation timeout |

## Background learning

| Variable | Default | Description |
| --- | --- | --- |
| `INTLLM_MAX_BACKGROUND_WORKERS` | `1` | Worker count |
| `INTLLM_BACKGROUND_POLL_SECONDS` | `5` | Poll interval |
| `INTLLM_BACKGROUND_LATENCY_THRESHOLD_MS` | `1500` | Interactive-latency throttle threshold |
| `INTLLM_BACKGROUND_CPU_THRESHOLD_PERCENT` | `85` | CPU throttle threshold |
| `INTLLM_BACKGROUND_RAM_THRESHOLD_PERCENT` | `90` | RAM throttle threshold |

## Internal / advanced

These are set automatically by the desktop launcher and are documented for
completeness; you should not normally set them.

| Variable | Description |
| --- | --- |
| `INTLLM_SERVE_STATIC` | `1` serves the built frontend from the backend |
| `INTLLM_STATIC_ROOT` | Directory containing the frontend build |
| `INTLLM_STATIC_DIR` | Explicit override for the frontend build location |
| `INTLLM_EFFECTIVE_PORT` | The port actually being served (after port-conflict fallback) |
| `INTLLM_DESKTOP_HEADLESS` | `1` runs the backend without a window (smoke tests) |

## Frontend build-time variables (Vite)

| Variable | Default | Description |
| --- | --- | --- |
| `VITE_INTLLM_BASE_URL` | — | Full backend base URL (preferred) |
| `VITE_INTLLM_HOST` | `127.0.0.1` | Fallback host |
| `VITE_INTLLM_PORT` | `8000` | Fallback port |
| `VITE_INTLLM_POLLING_INTERVAL_MS` | `8000` | Health/Ollama polling interval (clamped 5000–60000) |
| `VITE_INTLLM_CONNECTION_TIMEOUT_MS` | `15000` | Request timeout (clamped 2000–60000) |
