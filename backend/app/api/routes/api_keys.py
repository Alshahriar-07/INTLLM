"""Local API key management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session_required
from app.config.settings import get_settings
from app.core.errors import NotFoundError
from app.db.models import ApiKey
from app.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyOut,
    ApiKeysResponse,
)
from app.services.security.service import get_api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _to_out(record: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=str(record.id),
        name=record.name,
        key=f"{record.key_prefix}…{record.fingerprint[:4]}",
        created=record.created_at.isoformat() if record.created_at else "",
        lastUsed=record.last_used_at.isoformat() if record.last_used_at else None,
        scopes=record.scopes or [],
        status=record.status,
    )


def _base_url() -> str:
    settings = get_settings()
    return f"http://127.0.0.1:{settings.active_api_port}/v1"


@router.get("", response_model=ApiKeysResponse)
async def list_keys(
    session: AsyncSession = Depends(get_session_required),
) -> ApiKeysResponse:
    keys = await get_api_key_service().list(session)
    return ApiKeysResponse(
        connected=True, keys=[_to_out(k) for k in keys], baseUrl=_base_url()
    )


@router.post("", response_model=ApiKeyCreatedResponse)
async def create_key(
    body: ApiKeyCreateRequest,
    session: AsyncSession = Depends(get_session_required),
) -> ApiKeyCreatedResponse:
    record, secret = await get_api_key_service().create(
        session, name=body.name, scopes=body.scopes or None
    )
    return ApiKeyCreatedResponse(key=_to_out(record), secret=secret)


@router.post("/{key_id}/regenerate", response_model=ApiKeyCreatedResponse)
async def regenerate_key(
    key_id: uuid.UUID,
    session: AsyncSession = Depends(get_session_required),
) -> ApiKeyCreatedResponse:
    """Issue a replacement key and revoke the old one in one step."""
    result = await get_api_key_service().regenerate(session, key_id)
    if result is None:
        raise NotFoundError(f"API key not found: {key_id}")
    record, secret = result
    return ApiKeyCreatedResponse(key=_to_out(record), secret=secret)


@router.delete("/{key_id}")
async def revoke_key(
    key_id: uuid.UUID,
    session: AsyncSession = Depends(get_session_required),
) -> dict[str, object]:
    revoked = await get_api_key_service().revoke(session, key_id)
    if not revoked:
        raise NotFoundError(f"API key not found: {key_id}")
    return {"ok": True}
