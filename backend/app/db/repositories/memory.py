"""Memory persistence: L2 items, sources, L0 flash index and L1 hot cache."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import FlashIndex, HotCacheMetadata, MemoryItem, MemorySource


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- write ------------------------------------------------------------
    async def create_memory(
        self,
        *,
        type: str,
        title: str,
        content: str,
        normalized_content: str,
        layer: str = "L2",
        confidence: float = 50.0,
        importance: float = 50.0,
        freshness_score: float = 100.0,
        freshness_policy: str = "medium",
        keywords: list[str] | None = None,
        verified_at: datetime | None = None,
        expires_at: datetime | None = None,
        sources: list[dict[str, Any]] | None = None,
        embedding: list[float] | None = None,
        embedding_model: str | None = None,
    ) -> MemoryItem:
        memory = MemoryItem(
            type=type,
            title=title,
            content=content,
            normalized_content=normalized_content,
            layer=layer,
            confidence=confidence,
            importance=importance,
            freshness_score=freshness_score,
            freshness_policy=freshness_policy,
            keywords=keywords or [],
            verified_at=verified_at,
            expires_at=expires_at,
        )
        self._session.add(memory)
        await self._session.flush()

        for source in sources or []:
            self._session.add(
                MemorySource(
                    memory_id=memory.id,
                    url=source.get("url"),
                    title=source.get("title"),
                    source_type=source.get("source_type", "unknown"),
                    retrieved_at=source.get("retrieved_at"),
                    published_at=source.get("published_at"),
                    verification_status=source.get("verification_status", "unverified"),
                )
            )

        self._session.add(
            FlashIndex(
                memory_id=memory.id,
                embedding=embedding,
                embedding_model=embedding_model,
                keywords=keywords or [],
                memory_type=type,
                confidence=confidence,
                expires_at=expires_at,
            )
        )
        await self._session.flush()
        return memory

    async def update_memory(self, memory_id: uuid.UUID, **fields: Any) -> MemoryItem | None:
        memory = await self.get_memory(memory_id)
        if memory is None:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(memory, key):
                setattr(memory, key, value)
        await self._session.flush()
        return memory

    async def delete_memory(self, memory_id: uuid.UUID) -> bool:
        memory = await self._session.get(MemoryItem, memory_id)
        if memory is None:
            return False
        await self._session.delete(memory)
        return True

    # --- read -------------------------------------------------------------
    async def get_memory(self, memory_id: uuid.UUID) -> MemoryItem | None:
        result = await self._session.execute(
            select(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .options(selectinload(MemoryItem.sources))
        )
        return result.scalar_one_or_none()

    async def list_memories(
        self,
        *,
        layer: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryItem]:
        stmt = select(MemoryItem).options(selectinload(MemoryItem.sources))
        if layer:
            stmt = stmt.where(MemoryItem.layer == layer)
        if status:
            stmt = stmt.where(MemoryItem.status == status)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(MemoryItem.title.ilike(pattern), MemoryItem.content.ilike(pattern))
            )
        stmt = stmt.order_by(MemoryItem.updated_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def keyword_search(self, keywords: list[str], limit: int = 10) -> list[MemoryItem]:
        if not keywords:
            return []
        clauses = []
        for keyword in keywords[:8]:
            pattern = f"%{keyword}%"
            clauses.append(MemoryItem.normalized_content.ilike(pattern))
        result = await self._session.execute(
            select(MemoryItem)
            .where(or_(*clauses), MemoryItem.status == "active")
            .options(selectinload(MemoryItem.sources))
            .order_by(MemoryItem.confidence.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def vector_search(
        self, embedding: list[float], limit: int = 10
    ) -> list[tuple[MemoryItem, float]]:
        """Return ``(memory, cosine_distance)`` ordered by closeness."""
        distance = FlashIndex.embedding.cosine_distance(embedding).label("distance")
        stmt = (
            select(MemoryItem, distance)
            .join(FlashIndex, FlashIndex.memory_id == MemoryItem.id)
            .where(FlashIndex.embedding.is_not(None), MemoryItem.status == "active")
            .options(selectinload(MemoryItem.sources))
            .order_by(distance)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(row[0], float(row[1])) for row in result.all()]

    async def stats(self) -> dict[str, Any]:
        layer_rows = await self._session.execute(
            select(MemoryItem.layer, func.count()).group_by(MemoryItem.layer)
        )
        counts = {layer: count for layer, count in layer_rows.all()}

        agg = await self._session.execute(
            select(
                func.count(MemoryItem.id),
                func.avg(MemoryItem.confidence),
                func.avg(MemoryItem.freshness_score),
            )
        )
        total, avg_confidence, avg_freshness = agg.one()
        indexed = await self._session.execute(
            select(func.count()).select_from(FlashIndex).where(FlashIndex.embedding.is_not(None))
        )
        return {
            "total": int(total or 0),
            "by_layer": counts,
            "avg_confidence": float(avg_confidence or 0.0),
            "avg_freshness": float(avg_freshness or 0.0),
            "indexed": int(indexed.scalar() or 0),
        }

    async def expired(self, limit: int = 100) -> list[MemoryItem]:
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(MemoryItem)
            .where(MemoryItem.expires_at.is_not(None), MemoryItem.expires_at < now)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_stale(self, memory_ids: list[uuid.UUID]) -> None:
        if not memory_ids:
            return
        await self._session.execute(
            update(MemoryItem).where(MemoryItem.id.in_(memory_ids)).values(status="stale")
        )

    async def touch_access(self, memory_ids: list[uuid.UUID]) -> None:
        if not memory_ids:
            return
        now = datetime.now(timezone.utc)
        await self._session.execute(
            update(FlashIndex)
            .where(FlashIndex.memory_id.in_(memory_ids))
            .values(last_accessed_at=now, access_count=FlashIndex.access_count + 1)
        )

    # --- L1 hot cache -----------------------------------------------------
    async def hot_cache_get(self, cache_key: str) -> HotCacheMetadata | None:
        result = await self._session.execute(
            select(HotCacheMetadata).where(HotCacheMetadata.cache_key == cache_key)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        now = datetime.now(timezone.utc)
        if record.expires_at is not None:
            expires = record.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < now:
                await self._session.delete(record)
                await self._session.flush()
                return None
        record.hit_count += 1
        record.last_accessed_at = now
        await self._session.flush()
        return record

    async def hot_cache_put(
        self, *, memory_id: uuid.UUID, cache_key: str, ttl_seconds: int | None = None
    ) -> HotCacheMetadata:
        now = datetime.now(timezone.utc)
        expires = (
            datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=timezone.utc)
            if ttl_seconds
            else None
        )
        record = HotCacheMetadata(
            memory_id=memory_id,
            cache_key=cache_key,
            promoted_at=now,
            last_accessed_at=now,
            expires_at=expires,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def hot_cache_invalidate(self, cache_key: str | None = None) -> int:
        stmt = delete(HotCacheMetadata)
        if cache_key:
            stmt = stmt.where(HotCacheMetadata.cache_key == cache_key)
        result = await self._session.execute(stmt)
        return int(result.rowcount or 0)
