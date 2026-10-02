"""Health and readiness endpoints. Reports real service state."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app import __version__
from app.config.settings import get_settings
from app.db.session import get_database
from app.schemas import HealthResponse, ServiceState
from app.services.runtime.ollama import get_ollama_adapter
from app.services.system.db_init import inspect as inspect_database

router = APIRouter(tags=["health"])


async def _postgres_state() -> ServiceState:
    """Report PostgreSQL with real granularity.

    connected   - reachable, pgvector present and schema initialized
    degraded    - reachable but misconfigured (pgvector missing / no schema)
    unavailable - reachable check failed for a configuration reason
    offline     - cannot connect at all
    """
    db_available, db_error = await get_database().ping()
    if not db_available:
        return ServiceState(status="offline", detail=db_error)
    report = await inspect_database()
    if report.status == "running":
        detail = report.migration or "schema ready"
        return ServiceState(status="connected", detail=detail)
    if report.status == "misconfigured":
        return ServiceState(status="degraded", detail=report.detail)
    return ServiceState(status="unavailable", detail=report.detail or db_error)


async def _service_states() -> dict[str, ServiceState]:
    ollama_available, ollama_error = await get_ollama_adapter().health()
    return {
        "intllm": ServiceState(status="connected", detail=f"v{__version__}"),
        "postgres": await _postgres_state(),
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


@router.get("/ready")
async def ready(response: Response) -> dict[str, object]:
    services = await _service_states()
    ready_ = services["postgres"].status == "connected"
    if not ready_:
        response.status_code = 503
    return {"ready": ready_, "services": {k: v.model_dump() for k, v in services.items()}}
