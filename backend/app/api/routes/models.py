"""Model registry endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session_optional
from app.api.sse import SSE_HEADERS
from app.core.errors import NotFoundError
from app.db.models import ModelRecord
from app.schemas import (
    ModelListResponse,
    ModelOut,
    ModelPullRequest,
    ModelRecommendation,
    ModelRecommendResponse,
)
from app.services.models.service import ModelService, tier_for_memory
from app.services.runtime.base import RuntimeUnavailable

router = APIRouter(prefix="/models", tags=["models"])
_service = ModelService()


def _to_out(record: ModelRecord) -> ModelOut:
    return ModelOut(
        id=str(record.id),
        name=record.name,
        parameterSize=record.parameter_size,
        quantization=record.quantization,
        contextWindow=str(record.context_length) if record.context_length else None,
        memoryReqGB=record.memory_req_gb,
        tier=record.tier,
        capabilities=record.capabilities or [],
        installed=record.installed,
        isDefault=record.is_default,
        family=record.family,
    )


@router.get("", response_model=ModelListResponse)
async def list_models(
    session: AsyncSession | None = Depends(get_session_optional),
) -> ModelListResponse:
    try:
        if session is not None:
            records = await _service.sync_registry(session)
            return ModelListResponse(connected=True, models=[_to_out(r) for r in records])
        # No database: still report live Ollama inventory honestly.
        live = await _service._adapter.list_models()
        models = [
            ModelOut(
                id=info.name,
                name=info.name,
                parameterSize=info.parameter_size,
                quantization=info.quantization,
                memoryReqGB=ModelService._estimate_memory_gb(info),
                tier=tier_for_memory(ModelService._estimate_memory_gb(info)),
                capabilities=info.capabilities,
                installed=True,
                family=info.family,
            )
            for info in live
        ]
        return ModelListResponse(connected=True, models=models)
    except RuntimeUnavailable as exc:
        return ModelListResponse(connected=False, models=[], error=str(exc))


@router.post("/discover", response_model=ModelListResponse)
async def discover(
    session: AsyncSession | None = Depends(get_session_optional),
) -> ModelListResponse:
    return await list_models(session=session)


@router.get("/recommend", response_model=ModelRecommendResponse)
async def recommend(
    session: AsyncSession | None = Depends(get_session_optional),
) -> ModelRecommendResponse:
    from app.services.system.service import get_hardware_service

    hardware = await get_hardware_service().snapshot()
    gpu = hardware.get("gpu")
    vram_total = gpu["vramTotalGB"] if gpu else None
    ram_total = hardware["ram"]["totalGB"] if hardware.get("ram") else None
    if session is None:
        return ModelRecommendResponse(vram_total_gb=vram_total, ram_total_gb=ram_total)
    recommendations = await _service.recommend(
        session, vram_total_gb=vram_total, ram_total_gb=ram_total
    )
    return ModelRecommendResponse(
        vram_total_gb=vram_total,
        ram_total_gb=ram_total,
        recommendations=[ModelRecommendation(**item) for item in recommendations],
    )


@router.post("/default")
async def set_default(
    body: ModelPullRequest,
    session: AsyncSession | None = Depends(get_session_optional),
) -> dict[str, object]:
    if session is None:
        raise HTTPException(status_code=503, detail="PostgreSQL is unavailable")
    if not await _service.set_default(session, body.name):
        raise NotFoundError(f"Model not found: {body.name}")
    return {"ok": True, "default": body.name}


@router.post("/pull")
async def pull_model(body: ModelPullRequest) -> StreamingResponse:
    async def generator():
        yield f"event: model.pull.started\ndata: {json.dumps({'name': body.name})}\n\n"
        async for progress in _service.pull(body.name):
            if progress.get("error"):
                yield f"event: model.pull.failed\ndata: {json.dumps(progress)}\n\n"
                return
            yield f"event: model.pull.progress\ndata: {json.dumps(progress, default=str)}\n\n"
        yield f"event: model.pull.completed\ndata: {json.dumps({'name': body.name})}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.delete("/{name}")
async def delete_model(
    name: str,
    session: AsyncSession | None = Depends(get_session_optional),
) -> dict[str, object]:
    if session is None:
        raise HTTPException(status_code=503, detail="PostgreSQL is unavailable")
    ok, error = await _service.delete_model(session, name)
    if not ok:
        raise HTTPException(status_code=502, detail=error or "Model delete failed")
    return {"ok": True, "deleted": name}
