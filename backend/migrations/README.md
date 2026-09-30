# Database migrations

INTLLM uses Alembic for schema management. Tables are never created implicitly
on application startup.

## Prerequisites

1. A running PostgreSQL instance with the `pgvector` extension available.
2. `INTLLM_DATABASE_URL` (asyncpg) and `INTLLM_DATABASE_URL_SYNC` (psycopg)
   pointing at the same database.

## Commands

```bash
cd backend
alembic upgrade head         # apply all migrations
alembic current              # show current revision
alembic downgrade -1         # roll back one revision
alembic revision --autogenerate -m "add something"   # new migration
```

The initial migration creates the `vector` extension and the full core schema.
Future changes should use `--autogenerate`, reviewed before commit.
