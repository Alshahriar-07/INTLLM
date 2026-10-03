# INTLLM Database

INTLLM stores its state in a **local PostgreSQL** database with the **pgvector**
extension. PostgreSQL is the primary database; INTLLM does **not** silently fall
back to SQLite.

---

## What is stored

| Data | Table(s) |
| --- | --- |
| Conversations and messages | `conversations`, `messages` |
| Layered memory items and sources | `memory_items`, `memory_sources` |
| Flash index / hot cache metadata | `flash_index`, `hot_cache_metadata` |
| API keys (hash + fingerprint only) | `api_keys` |
| Model registry | `models` |
| Background jobs and events | `background_jobs`, `job_events` |
| Tool runs and browser sessions | `tool_runs`, `browser_sessions` |
| Audit events and diagnostics | `audit_events`, `diagnostics` |
| Application settings (workspace, access mode) | `app_settings` |

API keys are stored only as a salted **scrypt** hash plus a short fingerprint;
the raw key is shown once at creation and never stored.

## Connection configuration

```text
INTLLM_DATABASE_URL=postgresql+asyncpg://intllm:intllm@127.0.0.1:5432/intllm
INTLLM_DATABASE_URL_SYNC=postgresql+psycopg://intllm:intllm@127.0.0.1:5432/intllm
INTLLM_DB_CONNECT_TIMEOUT_SECONDS=5
INTLLM_DB_AUTO_CREATE=true
```

- `INTLLM_DATABASE_URL` is the async URL used by the app and by Alembic.
- `INTLLM_DATABASE_URL_SYNC` is retained for tooling that prefers a sync driver.
- Never commit real credentials. Configure via environment or a local secret
  store. DSN passwords are sanitized out of error messages before they are
  logged or shown.

## Initialization

On startup INTLLM runs a real verification → initialization sequence:

1. **PostgreSQL reachable?** If not, the failure is classified (service not
   running, authentication failed, database missing, timeout, …) with an
   actionable remediation step.
2. **Database exists?** If the configured database is missing and
   `INTLLM_DB_AUTO_CREATE=true`, INTLLM connects to the `postgres` maintenance
   database and runs `CREATE DATABASE` for it. It only ever **creates** — it
   never drops or resets user data.
3. **pgvector available?** INTLLM verifies the `vector` extension. If missing it
   attempts `CREATE EXTENSION IF NOT EXISTS vector`; if that fails, memory is
   reported unavailable rather than silently degrading.
4. **Schema applied.** Alembic migrations are used when available
   (`backend/migrations`); in the packaged executable, where migration files are
   not present, the schema is created from SQLAlchemy metadata DDL.
5. **Tables verified.** Every required table must exist before the database is
   reported `running`, so a half-applied schema can never masquerade as ready.

## Schema and migrations

- Models live in `backend/app/db/models.py`.
- Migrations live in `backend/migrations/` (current revision `0001`).
- The packaged executable applies the schema from SQLAlchemy metadata because
  Alembic config/files are not bundled.

To apply migrations manually during development:

```bash
cd backend
alembic upgrade head
```

## Chat history

Conversations and messages are persisted server-side and restored on reload and
after a restart. History is only shown when the database is reachable; otherwise
the UI reports it as unavailable.

## Memory

Layered memory (L0 Flash Brain, L1 Hot Cache, L2 Secondary Brain) is stored in
PostgreSQL with pgvector-backed embeddings. Memory availability is derived from
PostgreSQL + pgvector + schema readiness. See [MEMORY.md](MEMORY.md).

## Persistent data and location

| Platform | Application data |
| --- | --- |
| Windows | `%LOCALAPPDATA%\INTLLM` (data, workspace, logs) |
| macOS | `~/Library/Application Support/INTLLM` |
| Linux | `$XDG_DATA_HOME/INTLLM` or `~/.local/share/INTLLM` |

The PostgreSQL **data directory** is managed by your PostgreSQL installation, not
by INTLLM. Program files (Windows: `%LOCALAPPDATA%\Programs\INTLLM`) are
separate and are the only thing removed on uninstall.

## Backup considerations

- **Conversations, memory and API keys** live in the PostgreSQL database. Back
  it up with `pg_dump`:

  ```bash
  pg_dump -U intllm intllm > intllm-backup.sql
  ```

- **Application data** (workspace files, logs) lives under the application data
  directory above.
- Model weights live in Ollama's own storage and are not INTLLM's to back up.
- To migrate to a new machine: restore the database, copy the application data
  directory, and reinstall Ollama models.

## Data safety

- Upgrades and uninstall do **not** delete runtime data. Only the program
  directory is removed on Windows uninstall.
- INTLLM never runs `DROP DATABASE` or destructive resets. The only DDL it
  performs automatically is `CREATE DATABASE` (when the database is missing) and
  `CREATE EXTENSION IF NOT EXISTS vector`.
