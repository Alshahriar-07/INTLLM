"""Layered memory (brain) endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session_optional, get_session_required
from app.core.errors import NotFoundError
from app.core.metrics import metrics
from app.db.repositories.memory import MemoryRepository
from app.schemas import (
    BrainSearchResponse,
    BrainStatsOut,
    MemoryCreateRequest,
    MemoryOut,
)
from app.services.brain.service import MemoryCandidate, get_brain_service

router = APIRouter(prefix="/brain", tags=["brain"])


def _to_out(memory) -> MemoryOut:
    sources = getattr(memory, "sources", None)
    source_label = "local"
    if sources:
        first = sources[0]
        source_label = first.url or first.title or first.source_type or "local"
    return MemoryOut(
        id=str(memory.id),
        title=memory.title,
        layer=memory.layer,
        type=memory.type,
        confidence=memory.confidence,
        freshnessScore=memory.freshness_score,
        source=source_label,
        lastVerified=memory.verified_at.isoformat() if memory.verified_at else "",
        status=memory.status,
        keywords=memory.keywords or [],
        rawSnippet=memory.content[:280],
        vectorId=str(memory.id),
    )


@router.get("/search", response_model=BrainSearchResponse)
async def search_memory(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession | None = Depends(get_session_optional),
) -> BrainSearchResponse:
    if session is None:
        return BrainSearchResponse(
            connected=False, memories=[], stats=None, error="PostgreSQL is unavailable"
        )
    with metrics.timer("brain.lookup"):
        result = await get_brain_service().lookup(session, q, limit=limit)
    metrics.increment("brain.lookup.count")
    if result.hit:
        metrics.increment("brain.lookup.hit")
    memories = [_to_out(m) for m in result.memories]
    return BrainSearchResponse(connected=True, memories=memories, stats=None)


@router.get("/memories", response_model=BrainSearchResponse)
async def list_memories(
    q: str | None = None,
    layer: str | None = Query(default=None, pattern="^(L0|L1|L2)$"),
    status: str | None = "active",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession | None = Depends(get_session_optional),
) -> BrainSearchResponse:
    if session is None:
        return BrainSearchResponse(
            connected=False, memories=[], stats=None, error="PostgreSQL is unavailable"
        )
    brain = get_brain_service()
    memories = await brain.search(
        session, query=q, layer=layer, status=status, limit=limit, offset=offset
    )
    stats_raw = await brain.stats(session)
    counters = metrics.snapshot()["counters"]
    lookups = counters.get("brain.lookup.count", 0)
    hits = counters.get("brain.lookup.hit", 0)
    stats = BrainStatsOut(
        totalMemories=stats_raw["totalMemories"],
        hitRatePercent=(round(hits / lookups * 100, 1) if lookups else None),
        avgLookupTimeMs=None,
        freshnessPercent=round(stats_raw["avgFreshness"], 1) if stats_raw["totalMemories"] else None,
        byLayer=stats_raw["by_layer"],
    )
    return BrainSearchResponse(
        connected=True, memories=[_to_out(m) for m in memories], stats=stats
    )


@router.post("/memories", response_model=MemoryOut)
async def create_memory(
    body: MemoryCreateRequest,
    session: AsyncSession = Depends(get_session_required),
) -> MemoryOut:
    candidate = MemoryCandidate(
        type=body.type,
        title=body.title,
        content=body.content,
        confidence=body.confidence,
        importance=body.importance,
        freshness_policy=body.freshness_policy,
        keywords=body.keywords,
        sources=body.sources,
    )
    created = await get_brain_service().store(session, candidate)
    memory = await MemoryRepository(session).get_memory(created.id)
    return _to_out(memory or created)


@router.get("/memories/{memory_id}", response_model=MemoryOut)
async def get_memory(
    memory_id: uuid.UUID,
    session: AsyncSession = Depends(get_session_required),
) -> MemoryOut:
    memory = await MemoryRepository(session).get_memory(memory_id)
    if memory is None:
        raise NotFoundError(f"Memory not found: {memory_id}")
    get_brain_service()._apply_freshness(memory, datetime.now(timezone.utc))
    return _to_out(memory)


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: uuid.UUID,
    session: AsyncSession = Depends(get_session_required),
) -> dict[str, object]:
    deleted = await MemoryRepository(session).delete_memory(memory_id)
    if not deleted:
        raise NotFoundError(f"Memory not found: {memory_id}")
    return {"ok": True}


@router.post("/cache/invalidate")
async def invalidate_cache(
    key: str | None = None,
    session: AsyncSession = Depends(get_session_required),
) -> dict[str, object]:
    removed = await get_brain_service().invalidate(session, key)
    return {"ok": True, "removed": removed}
