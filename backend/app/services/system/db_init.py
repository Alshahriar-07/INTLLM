"""Database bootstrap and readiness inspection.

A fresh local install must be able to initialize PostgreSQL automatically and
report its state honestly. This module:

* verifies PostgreSQL is reachable,
* verifies the ``pgvector`` extension is available (semantic memory depends on
  it and must never silently degrade to keyword-only),
* creates the schema. Alembic is used when it is importable *and* the migration
  directory is present (development / wheel-from-checkout). In the frozen
  Windows executable Alembic (and ``migrations/``) are not bundled, so the
  schema is created from SQLAlchemy metadata instead — real DDL against the
  configured PostgreSQL, not a stub.

Nothing here fabricates success: an unreachable database or a missing extension
is returned as ``unavailable`` / ``misconfigured`` with an actionable message.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Lifecycle vocabulary shared with the launcher / UI (PLAN 13).
STATUS_RUNNING = "running"
STATUS_MISCONFIGURED = "misconfigured"
STATUS_UNAVAILABLE = "unavailable"

_PGVECTOR_ACTION = (
    "Install the pgvector extension for your PostgreSQL server "
    "(https://github.com/pgvector/pgvector) and re-run INTLLM."
)


@dataclass
class DatabaseReport:
    """Honest snapshot of the local database subsystem."""

    status: str
    postgres: bool = False
    pgvector: bool = False
    schema: bool = False
    migration: str | None = None
    detail: str | None = None
    actions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- Inspection ----------------------------------------------------------------


async def _detect_revision(connection) -> str | None:
    from sqlalchemy import text

    exists = await connection.scalar(text("SELECT to_regclass('public.alembic_version')"))
    if exists is None:
        return None
    try:
        row = await connection.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
    except Exception:  # noqa: BLE001 - empty table is not an error
        return "unknown"
    return row


async def _inspect_with_database() -> DatabaseReport:
    """Connect once and report PostgreSQL / pgvector / schema state."""
    from sqlalchemy import text

    from app.db.session import get_database

    database = get_database()
    available, error = await database.ping()
    if not available:
        return DatabaseReport(
            status=STATUS_UNAVAILABLE,
            detail=error,
            actions=[
                "Start PostgreSQL and ensure INTLLM_DATABASE_URL points at a reachable "
                "database, then re-run INTLLM."
            ],
        )

    async with database.engine.connect() as connection:
        pgvector = bool(
            await connection.scalar(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        )
        schema = bool(
            await connection.scalar(text("SELECT to_regclass('public.api_keys') IS NOT NULL"))
        )
        revision = await _detect_revision(connection) if schema else None

    if not pgvector:
        return DatabaseReport(
            status=STATUS_MISCONFIGURED,
            postgres=True,
            pgvector=False,
            schema=schema,
            migration=revision,
            detail="PostgreSQL is reachable but the pgvector extension is not available.",
            actions=[_PGVECTOR_ACTION],
        )

    return DatabaseReport(
        status=STATUS_RUNNING if schema else STATUS_MISCONFIGURED,
        postgres=True,
        pgvector=True,
        schema=schema,
        migration=revision,
        detail=None if schema else "Database schema has not been initialized yet.",
        actions=[] if schema else ["Run INTLLM once to apply migrations automatically."],
    )


async def inspect() -> DatabaseReport:
    """Read-only readiness check (safe to call from request handlers)."""
    try:
        return await _inspect_with_database()
    except Exception as exc:  # noqa: BLE001 - reported as a status, never raised
        return DatabaseReport(status=STATUS_UNAVAILABLE, detail=f"{type(exc).__name__}: {exc}")


# --- Initialization ------------------------------------------------------------

# backend/ root (…/backend/app/services/system/db_init.py -> parents[3] == backend)
_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _alembic_config_path() -> Path | None:
    """Alembic config is only usable when it ships alongside the app."""
    candidate = _BACKEND_ROOT / "alembic.ini"
    return candidate if candidate.is_file() else None


async def _create_schema_from_metadata() -> None:
    """Create the schema from SQLAlchemy metadata (packaged-executable path)."""
    from app.db import models  # noqa: F401 - register metadata
    from app.db.base import Base
    from app.db.session import get_database

    database = get_database()
    async with database.engine.begin() as connection:
        # pgvector must exist before tables with a `vector` column.
        await connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await connection.run_sync(Base.metadata.create_all)


def _run_alembic_upgrade(config_path: Path) -> None:
    """Apply ``alembic upgrade head`` (runs its own event loop internally)."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(config_path))
    config.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    command.upgrade(config, "head")


async def _initialize() -> DatabaseReport:
    from app.db.session import get_database

    report = await inspect()
    if not report.postgres:
        return report

    if not report.pgvector:
        # Best-effort: a superuser may be able to create the extension.
        try:
            async with get_database().engine.begin() as connection:
                await connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception as exc:  # noqa: BLE001 - surfaced in the report
            report.detail = f"{report.detail} (CREATE EXTENSION failed: {exc})"
        report = await inspect()
        if not report.pgvector:
            return report

    if report.schema:
        return report

    config_path = _alembic_config_path()
    try:
        if config_path is not None:
            await asyncio.to_thread(_run_alembic_upgrade, config_path)
        else:
            await _create_schema_from_metadata()
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        failed = await inspect()
        failed.status = STATUS_MISCONFIGURED
        failed.detail = f"Schema initialization failed: {type(exc).__name__}: {exc}"
        failed.actions = [
            "Verify the database user has CREATE privileges (and rights to CREATE "
            "EXTENSION vector), then re-run INTLLM."
        ]
        return failed

    return await inspect()


def initialize_database() -> DatabaseReport:
    """Synchronously initialize the database (used by the launcher).

    Safe to call before uvicorn starts: it runs in its own event loop and
    disposes the engine afterwards so the server creates a fresh one.
    """

    async def _run() -> DatabaseReport:
        from app.db.session import get_database

        try:
            return await _initialize()
        finally:
            # The launcher may run before/without the app loop; discard the
            # engine so it is never reused across event loops.
            await get_database().dispose()

    return asyncio.run(_run())
