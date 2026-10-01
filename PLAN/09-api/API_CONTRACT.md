# API Contract

## Internal API

Base:

`http://127.0.0.1:<port>/api`

Endpoints:

```text
GET    /health
GET    /system
GET    /models
POST   /models/pull
DELETE /models/{name}

GET    /conversations
POST   /conversations
GET    /conversations/{id}
POST   /conversations/{id}/messages
POST   /chat/stream

GET    /brain/search
GET    /brain/memories/{id}
POST   /brain/memories
DELETE /brain/memories/{id}

GET    /tools
POST   /tools/{tool}/run

GET    /browser/status
POST   /browser/open
POST   /browser/action

GET    /api-keys
POST   /api-keys
DELETE /api-keys/{id}

GET    /background/status
POST   /background/pause
POST   /background/resume
```

## OpenAI-compatible API

Initial compatibility targets:

```text
GET  /v1/models
POST /v1/chat/completions
```

Support streaming where possible.

## API behavior

The compatibility API should route through the same INTLLM orchestrator instead of bypassing memory/security.

That allows Claude Code, Codex, SeedCode CLI and other compatible clients to use the same environment.

## Implementation status (backend phase)

The contract above is implemented by `backend/`. Internal endpoints are mounted
under the configured API prefix (default `/api`); the compatibility API is under
`/v1`.

```text
Internal (implemented)
GET    /api/health, /api/ready
GET    /api/ollama/status
POST   /api/ollama/start, /api/ollama/stop, /api/ollama/restart
GET    /api/ollama/status
POST   /api/ollama/start, /api/ollama/stop, /api/ollama/restart
GET    /api/system, /api/system/services, /api/system/stream (SSE)
GET    /api/models, /api/models/recommend
POST   /api/models/pull (SSE), /api/models/default
DELETE /api/models/{name}
POST   /api/chat/stream (SSE), /api/chat/completions
GET    /api/conversations, /api/conversations/{id}
POST   /api/conversations
DELETE /api/conversations/{id}
GET    /api/brain/search, /api/brain/memories, /api/brain/memories/{id}
POST   /api/brain/memories, /api/brain/cache/invalidate
DELETE /api/brain/memories/{id}
GET    /api/web/search
POST   /api/web/fetch
GET    /api/tools, /api/tools/permissions
POST   /api/tools/{tool}/run, /api/tools/{tool}/permission
GET    /api/browser/status, /api/browser/stream (SSE)
POST   /api/browser/action
GET    /api/api-keys
POST   /api/api-keys
DELETE /api/api-keys/{id}
GET    /api/background/status, /api/background/stream (SSE)
POST   /api/background/pause, /api/background/resume
GET    /api/diagnostics

OpenAI-compatible (implemented)
GET  /v1/models
POST /v1/chat/completions   (supports `stream: true`)
```

Errors follow a single structured shape (see
`FRONTEND_BACKEND_TRACING.md` §6). The compatibility API requires an API key
(`Authorization: Bearer intllm_...`), with a loopback-only bootstrap allowance
until the first key is created.
