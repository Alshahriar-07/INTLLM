"""Health and readiness endpoints. Reports real service state.

The coarse ``/api/health`` contract (``connected`` / ``degraded`` / ``offline``)
is kept for the existing frontend. ``/api/health/database`` exposes the richer
four-state model (``connected`` / ``disconnected`` / ``initializing`` / ``error``)
plus memory readiness and an actionable diagnostic category.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from app import __version__
from app.config.settings import get_settings
from app.schemas import HealthResponse, ServiceState
from app.services.runtime.ollama import get_ollama_adapter
from app.services.system.db_init import inspect as inspect_database

router = APIRouter(tags=["health"])


def _postgres_state(db_available: bool, db_error: str | None, report) -> ServiceState:
    """Report PostgreSQL with real granularity.

    connected   - reachable, pgvector present and schema initialized
    degraded    - reachable but misconfigured (pgvector missing / no schema)
    unavailable - reachable check failed for a configuration reason
    offline     - cannot connect at all
    """
    if not db_available:
        return ServiceState(status="offline", detail=db_error)
    if report is None:
        return ServiceState(status="unavailable", detail=db_error or "database not inspected")
    if report.status == "running":
        detail = report.migration or "schema ready"
        return ServiceState(status="connected", detail=detail)
    if report.status == "misconfigured":
        return ServiceState(status="degraded", detail=report.detail)
    return ServiceState(status="unavailable", detail=report.detail or db_error)


def _memory_state(report) -> ServiceState:
    """Memory is available only when PostgreSQL + pgvector + schema are ready.

    This makes ``Memory store unavailable`` a *real* backend fact rather than a
    frontend fetch failure: if memory is reported unavailable here, it is
    because the underlying store is not actually ready.
    """
    if report is None:
        return ServiceState(status="unavailable", detail="memory store unavailable")
    if report.status == "running" and report.pgvector and report.schema:
        return ServiceState(status="connected", detail="pgvector memory ready")
    if report.status == "misconfigured":
        return ServiceState(status="degraded", detail=report.detail)
    return ServiceState(
        status="unavailable", detail=report.detail or "memory store unavailable"
    )


async def _service_states() -> dict[str, ServiceState]:
    ollama_available, ollama_error = await get_ollama_adapter().health()
    # A single inspection covers both PostgreSQL and memory readiness (it
    # pings internally and returns a classified failure when unreachable).
    report = await inspect_database()
    db_available = report.postgres
    db_error = None if db_available else report.detail
    return {
        "intllm": ServiceState(status="connected", detail=f"v{__version__}"),
        "postgres": _postgres_state(db_available, db_error, report),
        "memory": _memory_state(report),
        "ollama": ServiceState(
            status="connected" if ollama_available else "offline", detail=ollama_error
        ),
    }


@router.get("/health", response_model=HealthResponse)
async def health(response: Response) -> HealthResponse:
    services = await _service_states()
    degraded = any(s.status != "connected" for s in services.values())
    # Readiness is 503 when a required dependency (PostgreSQL) is down.
    if services["postgres"].status != "connected":
        response.status_code = 503
    settings = get_settings()
    return HealthResponse(
        status="degraded" if degraded else "ok",
        version=__version__,
        environment=settings.intllm_env,
        services=services,
    )


@router.get("/health/database")
async def database_health() -> dict[str, object]:
    """Rich database + memory state for diagnostics.

    Contains only non-secret information: state, category, a sanitized message
    and remediation steps.
    """
    from app.db.health import get_database_health

    report = await inspect_database()
    snapshot = get_database_health().snapshot()
    return {
        "state": snapshot.status,
        "memory": snapshot.memory,
        "ready": snapshot.ready,
        "category": snapshot.category,
        "detail": snapshot.detail,
        "actions": snapshot.actions,
        "postgres": report.postgres,
        "pgvector": report.pgvector,
        "schema": report.schema,
        "missing_tables": report.missing_tables,
        "migration": report.migration,
        "checked_at": snapshot.checked_at,
        "initialized_at": snapshot.initialized_at,
    }


@router.get("/ready")
async def ready(response: Response) -> dict[str, object]:
    services = await _service_states()
    ready_ = services["postgres"].status == "connected"
    if not ready_:
        response.status_code = 503
    return {"ready": ready_, "services": {k: v.model_dump() for k, v in services.items()}}
