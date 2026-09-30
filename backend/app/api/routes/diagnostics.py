"""Diagnostics endpoint exposing real metrics and audit events."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session_optional
from app.services.diagnostics.service import get_diagnostics_service

router = APIRouter(tags=["diagnostics"])


@router.get("/diagnostics")
async def diagnostics(
    session: AsyncSession | None = Depends(get_session_optional),
) -> dict[str, object]:
    snapshot = await get_diagnostics_service().snapshot(session)
    snapshot["capturedAt"] = datetime.now(timezone.utc).isoformat()
    return snapshot
