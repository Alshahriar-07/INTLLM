# Developing INTLLM

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+ with pgvector (for database-backed features)
- Ollama (for live model features)

## Setup

```bash
git clone https://github.com/Alshahriar-07/INTLLM.git
cd INTLLM

# Frontend
npm install

# Backend (editable, with dev tooling)
python -m pip install -e "./backend[dev]"

# Optional: native desktop window locally
python -m pip install -e "./backend[desktop]"
```

## Development mode (browser workflow)

Development can use the Vite dev server + a browser — this is unchanged by the
desktop build:

```bash
# terminal 1 — backend API
cd backend
python -m app.cli serve

# terminal 2 — Vite dev server (http://127.0.0.1:3000)
npm run dev
```

The frontend talks to the backend via `VITE_INTLLM_BASE_URL` (or
`VITE_INTLLM_HOST`/`VITE_INTLLM_PORT`), defaulting to `http://127.0.0.1:8000`.

## Production mode (desktop window)

The packaged entry point is `app.desktop`:

```bash
cd backend
INTLLM_SERVE_STATIC=1 INTLLM_STATIC_ROOT=../dist python -c "from app.desktop import main; main()"
```

It starts the backend, shows the readiness window, and loads the built frontend
(`npm run build`) into a native window. Use `INTLLM_DESKTOP_HEADLESS=1` to run
the same path without a window (useful in CI/smoke tests).

## Tests

```bash
cd backend
python -m pytest -q            # unit tests; external services monkeypatched
ruff check --config pyproject.toml app tests
```

Database integration tests run when `INTLLM_TEST_DATABASE_URL` points at a
pgvector-enabled PostgreSQL:

```bash
INTLLM_TEST_DATABASE_URL=postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm_test \
  python -m pytest -q
```

Frontend:

```bash
npm run lint     # tsc --noEmit
npm run build    # production build into dist/
```

## Building release artifacts

```bash
# Everything: wheel + sdist (+ Windows exe + installer on Windows) + SHA256.txt
python scripts/build_release.py

# Windows executable + smoke test only
python build_windows.py

# Validate a built release directory (checksums + install check)
python scripts/validate_release.py build/release --require-exe --install-check
```

The build is reproducible as much as practical: the version is single-sourced
from `backend/app/__init__.py`, the version resource and checksums are generated
by scripts, and no developer-specific absolute paths are embedded. Record the
build version, target architecture and dependency versions when reproducing a
release (see [RELEASE.md](RELEASE.md)).

## Code layout

See [ARCHITECTURE.md](ARCHITECTURE.md) for the module map and data flows.

## Conventions

- Match existing patterns; prefer editing existing modules over adding new ones.
- No fake/demo data: report real state honestly (`connected`/`degraded`/
  `unavailable`), never fabricate availability or results.
- Keep secrets out of code, logs, bundles and artifacts.
- Run the test suite and lint before opening a pull request.

See [CONTRIBUTING.md](CONTRIBUTING.md).
