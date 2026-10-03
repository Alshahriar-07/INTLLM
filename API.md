# INTLLM API

INTLLM exposes an **OpenAI-compatible** HTTP API from the local backend. It is
served by the same process as the desktop application.

Only the endpoints documented here exist. INTLLM does **not** implement
`/v1/embeddings`, `/v1/responses`, audio, images, files, batches or fine-tuning,
and no third-party CLI compatibility is claimed unless verified against a build.

---

## Base URL

```text
http://127.0.0.1:<INTLLM_PORT>/v1
```

`INTLLM_PORT` defaults to `8000`. When LAN access is enabled, the same API is
also reachable at the machine's LAN address (shown in Settings → API).

## Authentication

All `/v1` endpoints require an INTLLM API key, sent either way:

```text
Authorization: Bearer intllm_…
```

```text
x-api-key: intllm_…
```

- Create keys in **Settings → API**. The full key is shown **once**.
- Only a salted scrypt hash and a fingerprint are stored.
- While **no key exists yet**, loopback requests are allowed as a bootstrap so
  you can create the first key. This ends as soon as a key exists and never
  applies to non-loopback clients.
- Missing credentials → `401 authentication_error`; invalid/revoked key → `401`.

## Local access

By default the backend binds `127.0.0.1` (`INTLLM_API_ACCESS_MODE=local`), so
`/v1` is reachable only from the same machine.

## LAN access

Enable in **Settings → API** (`INTLLM_API_ACCESS_MODE=lan`), then restart.
Only `/v1` becomes reachable from the LAN; internal `/api/*` routes, the SPA,
`/docs`, `/redoc` and diagnostics stay loopback-only. The API key is still
required. LAN traffic is plain HTTP — see [SECURITY.md](SECURITY.md) §10.

---

## Endpoints

### `GET /v1/models`

List installed models (from the real Ollama inventory).

```bash
curl http://127.0.0.1:8000/v1/models \
  -H "Authorization: Bearer intllm_…"
```

```json
{
  "object": "list",
  "data": [
    { "id": "llama3.2:latest", "object": "model", "created": 1730000000, "owned_by": "intllm" }
  ]
}
```

### `GET /v1/models/{model}`

Retrieve one model. Returns `404` when the model is not installed.

### `POST /v1/chat/completions`

Chat completion, streaming or not. Requests route through the INTLLM
orchestrator (memory/security aware).

#### Request body

| Field | Type | Notes |
| --- | --- | --- |
| `model` | string | Model id from `/v1/models`. Empty = configured default. |
| `messages` | array | `{ "role": "system" \| "user" \| "assistant", "content": string }` |
| `stream` | bool | `false` (default) or `true` (SSE) |
| `temperature` | number | Optional |
| `top_p` | number | Optional |
| `max_tokens` | number | Optional (mapped to Ollama `num_predict`) |
| `stop` | string \| string[] | Optional |
| `intllm_use_brain` | bool | Optional; use layered memory (default `true`) |
| `intllm_use_web` | bool | Optional; enable live web retrieval (default `false`) |

#### Non-streaming request

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer intllm_…" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:latest",
    "messages": [{ "role": "user", "content": "Say hello in one sentence." }],
    "stream": false
  }'
```

#### Non-streaming response

```json
{
  "id": "chatcmpl-…",
  "object": "chat.completion",
  "created": 1730000000,
  "model": "llama3.2:latest",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "Hello!" },
      "finish_reason": "stop"
    }
  ],
  "usage": { "prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16 }
}
```

#### Streaming

Set `"stream": true`. The response is `text/event-stream` with
`chat.completion.chunk` frames, ending with `data: [DONE]`. An error mid-stream
is delivered as a `data: {"error": {...}}` frame followed by `[DONE]`.

---

## Error format

Errors follow a consistent OpenAI-style shape:

```json
{ "error": { "message": "Invalid or revoked API key", "type": "authentication_error" } }
```

| Status | Meaning |
| --- | --- |
| `400` | Malformed request body |
| `401` | Missing / invalid / revoked API key |
| `403` | Endpoint is loopback-only (LAN request to a management route) |
| `404` | Model or resource not found |
| `413` | Request body exceeds `INTLLM_MAX_REQUEST_BYTES` |
| `503` | PostgreSQL or Ollama unavailable (`service_unavailable`) |

When PostgreSQL is down, the backend answers `/api/health` with `503` and the
OpenAI endpoints return `503` rather than fabricating a result. When Ollama is
unreachable, chat returns `503 service_unavailable`.

---

## Client configuration example

Any OpenAI-compatible client works with the base URL and key:

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="intllm_…")
response = client.chat.completions.create(
    model="llama3.2:latest",
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.choices[0].message.content)
```

## Technical schema

The live OpenAPI schema is at `/openapi.json`, with Swagger UI at `/docs` and
ReDoc at `/redoc` (loopback-only). The in-app **Docs** page is the user-facing
reference.
