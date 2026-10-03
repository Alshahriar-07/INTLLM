"""Local API server status and access-mode endpoints.

These routes are internal (loopback-only, enforced by middleware). They report
the *real* reachability of the OpenAI-compatible API and let the UI switch
between Local Only and LAN access. Nothing here fabricates a state.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session_optional, get_session_required
from app.db.repositories.keys import ApiKeyRepository
from app.schemas import ApiServerAccessRequest, ApiServerStatusOut, ServiceState
from app.services.api_server.service import get_api_server_service
from app.services.runtime.ollama import get_ollama_adapter

router = APIRouter(prefix="/api-server", tags=["api-server"])


async def _build(session: AsyncSession | None) -> ApiServerStatusOut:
    service = get_api_server_service()
    payload = await service.status(session)

    key_count = 0
    has_key = False
    key_store_available = session is not None
    if session is not None:
        try:
            keys = await ApiKeyRepository(session).list()
            active = [k for k in keys if k.status == "active"]
            key_count = len(active)
            has_key = key_count > 0
        except Exception:  # noqa: BLE001 - key metadata is best-effort here
            key_store_available = False

    ollama_available, ollama_error = await get_ollama_adapter().health()
    ollama = ServiceState(
        status="connected" if ollama_available else "offline", detail=ollama_error
    )

    return ApiServerStatusOut(
        **payload,
        keyCount=key_count,
        hasKey=has_key,
        keyStoreAvailable=key_store_available,
        ollama=ollama,
    )


@router.get("/status", response_model=ApiServerStatusOut)
async def api_server_status(
    session: AsyncSession | None = Depends(get_session_optional),
) -> ApiServerStatusOut:
    return await _build(session)


@router.post("/access", response_model=ApiServerStatusOut)
async def set_api_access(
    body: ApiServerAccessRequest,
    session: AsyncSession = Depends(get_session_required),
) -> ApiServerStatusOut:
    """Persist the access mode. A restart is required to rebind the interface."""
    await get_api_server_service().set_access_mode(session, body.mode)
    return await _build(session)
