# INTLLM Backend

FastAPI backend for the INTLLM local AI runtime. It orchestrates memory,
retrieval, tools and model inference, and exposes an OpenAI-compatible local
API. It never fabricates runtime data: empty stores return empty results and
unavailable services return explicit offline/unavailable states.

## Stack

- Python 3.11+ / FastAPI / Pydantic v2
- SQLAlchemy 2 (async) + asyncpg + Alembic
- PostgreSQL with pgvector
- Ollama (model runtime)
- Playwright (optional browser agent)
- httpx (web retrieval)

## Layout

```text
backend/
├─ app/
│  ├─ main.py            # FastAPI app, lifespan, middleware
│  ├─ config/            # environment settings (+ INTLLM endpoint validation)
│  ├─ core/              # logging, errors, security, events, metrics
│  ├─ db/                # declarative base, session, models, repositories
│  ├─ schemas/           # Pydantic request/response models
│  ├─ services/          # runtime, models, chat, brain, web, browser, tools,
│  │                     # system, background, security, diagnostics
│  └─ api/               # routers + dependencies + SSE helpers
├─ migrations/           # Alembic env + revisions
├─ tests/
├─ alembic.ini
├─ pyproject.toml
└─ .env.example
```

## Quick start

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev,browser,gpu]"                # omit extras as needed

cp .env.example .env                                # then edit values
createdb intllm                                     # or via your PG tooling
alembic upgrade head                                # create schema + pgvector

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
# or: intllm-api
```

The API is served under `/api` (`/api/health`, `/api/system`, ...). The
OpenAI-compatible API is served under `/v1` (`/v1/models`,
`/v1/chat/completions`).

Interactive docs: <http://127.0.0.1:8000/docs>

## Ollama

Ensure Ollama is running (`ollama serve`) and at least one model is pulled:

```bash
ollama pull llama3.1
ollama pull nomic-embed-text   # enables semantic memory search
```

Without an embedding model, memory search falls back to keyword matching.
Without Ollama, `/api/models` reports `connected: false`.

## INTLLM runtime endpoint

The project owner supplied `http://172.22.0.1:240426`. **240426 is outside the
valid TCP/UDP port range (0-65535)** and must not be bound or dialed. The
backend keeps this value in `INTLLM_RUNTIME_PORT_SUPPLIED` flagged as
`requires_validation` and does not substitute a port. Set `INTLLM_RUNTIME_PORT`
once the real port is confirmed.

## Tests

```bash
cd backend
pip install -e ".[dev]"
pytest
```

Unit tests run without PostgreSQL/Ollama; external boundaries are stubbed.
Integration tests against a live database should be added as the environment
is finalised.

## Security notes

- Default binding is `127.0.0.1`; external binding is explicit opt-in.
- API keys are hashed with scrypt; raw keys are shown once and never logged.
- Tool execution is policy-gated; filesystem access is restricted to an
  allow-list and terminal/filesystem-write are disabled by default.
- Web/browser URLs pass an SSRF guard that rejects private/reserved addresses.
