"""Layered memory service.

Routing: query -> L0 flash index -> L1 hot cache -> L2 vector/keyword search.
Returns real records with real latency; if nothing matches, it reports a miss.
Never generates memories for display.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import MemoryItem
from app.db.repositories.memory import MemoryRepository
from app.db.repositories.models import ModelRepository
from app.services.runtime.ollama import OllamaAdapter, get_ollama_adapter

logger = get_logger(__name__)

# TTL policy in hours per freshness policy (PLAN: news very short, docs medium,
# static workflows long).
FRESHNESS_TTL_HOURS: dict[str, int] = {
    "static": 24 * 365,
    "long": 24 * 180,
    "medium": 24 * 30,
    "short": 24 * 7,
    "live": 6,
}

_CONFIDENCE_THRESHOLD = 55.0
_FRESHNESS_THRESHOLD = 60.0
_HOT_CACHE_TTL_SECONDS = 60 * 30
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "how",
    "what", "why", "when", "where", "do", "does", "for", "with", "on", "i",
}


@dataclass(slots=True)
class MemoryCandidate:
    type: str
    title: str
    content: str
    confidence: float = 50.0
    importance: float = 50.0
    freshness_policy: str = "medium"
    keywords: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    verified_at: datetime | None = None


@dataclass(slots=True)
class LookupResult:
    memories: list[MemoryItem] = field(default_factory=list)
    source: str = "none"  # L0 | L1 | L2 | none
    hit: bool = False
    cached: bool = False
    confidence: float = 0.0
    total_ms: float = 0.0
    timings: dict[str, float] = field(default_factory=dict)
    stale: bool = False


def normalize_content(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def extract_keywords(text: str, limit: int = 10) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_\-]{3,}", text.lower())
    seen: list[str] = []
    for token in tokens:
        if token in _STOPWORDS or token in seen:
            continue
        seen.append(token)
        if len(seen) >= limit:
            break
    return seen


def freshness_score(
    *, verified_at: datetime | None, created_at: datetime | None, policy: str, now: datetime
) -> float:
    reference = verified_at or created_at
    if reference is None:
        return 0.0
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    ttl_hours = FRESHNESS_TTL_HOURS.get(policy, FRESHNESS_TTL_HOURS["medium"])
    age_hours = max(0.0, (now - reference).total_seconds() / 3600.0)
    score = 100.0 * (1.0 - min(age_hours / ttl_hours, 1.0))
    return round(score, 1)


class BrainService:
    def __init__(self, adapter: OllamaAdapter | None = None) -> None:
        self._adapter = adapter or get_ollama_adapter()
        self._embedding_model_cache: str | None | bool = False  # False = unresolved

    async def _embedding_model(self, session: AsyncSession) -> str | None:
        if self._embedding_model_cache is not False:
            return self._embedding_model_cache  # type: ignore[return-value]
        records = await ModelRepository(session).list()
        candidate = next(
            (
                r.name
                for r in records
                if "embed" in r.name.lower() and r.installed
            ),
            None,
        )
        self._embedding_model_cache = candidate
        return candidate

    async def _embed(self, session: AsyncSession, text: str) -> tuple[list[float] | None, str | None]:
        model = await self._embedding_model(session)
        if not model:
            return None, None
        vector = await self._adapter.embeddings(model, text)
        return vector, model

    async def store(self, session: AsyncSession, candidate: MemoryCandidate) -> MemoryItem:
        repo = MemoryRepository(session)
        normalized = normalize_content(f"{candidate.title} {candidate.content}")
        keywords = candidate.keywords or extract_keywords(normalized)
        embedding, embedding_model = await self._embed(session, normalized)
        now = datetime.now(timezone.utc)
        ttl_hours = FRESHNESS_TTL_HOURS.get(candidate.freshness_policy, 24 * 30)
        expires_at = now + timedelta(hours=ttl_hours) if ttl_hours < 24 * 365 else None

        memory = await repo.create_memory(
            type=candidate.type,
            title=candidate.title,
            content=candidate.content,
            normalized_content=normalized,
            layer="L2",
            confidence=candidate.confidence,
            importance=candidate.importance,
            freshness_score=100.0,
            freshness_policy=candidate.freshness_policy,
            keywords=keywords,
            verified_at=candidate.verified_at or now,
            expires_at=expires_at,
            sources=candidate.sources,
            embedding=embedding,
            embedding_model=embedding_model,
        )
        return memory

    async def lookup(
        self, session: AsyncSession, query: str, *, limit: int = 5
    ) -> LookupResult:
        started = time.perf_counter()
        repo = MemoryRepository(session)
        result = LookupResult()
        now = datetime.now(timezone.utc)
        cache_key = hashlib.sha256(normalize_content(query).encode("utf-8")).hexdigest()[:40]

        # L1 hot cache first: a promoted query result avoids all vector work.
        t0 = time.perf_counter()
        cached = await repo.hot_cache_get(cache_key)
        result.timings["l1_hot_cache_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        if cached is not None:
            memory = await repo.get_memory(cached.memory_id)
            if memory is not None and memory.status == "active":
                self._apply_freshness(memory, now)
                result.memories = [memory]
                result.hit = True
                result.cached = True
                result.source = "L1"
                result.confidence = memory.confidence
                result.stale = memory.freshness_score < _FRESHNESS_THRESHOLD
                result.total_ms = round((time.perf_counter() - started) * 1000.0, 2)
                return result

        matches: list[MemoryItem] = []

        # L0 flash index: embedding-backed micro lookup.
        t0 = time.perf_counter()
        embedding, _ = await self._embed(session, query)
        if embedding:
            try:
                vector_hits = await repo.vector_search(embedding, limit=limit)
                matches = [memory for memory, _distance in vector_hits]
                result.source = "L0"
            except Exception as exc:  # noqa: BLE001 - pgvector may be absent
                logger.warning(
                    "vector lookup failed; falling back to keyword search",
                    extra={"intllm_extra": {"error": str(exc)}},
                )
        result.timings["l0_flash_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # L2 keyword fallback keeps recall when no embeddings exist.
        if not matches:
            t0 = time.perf_counter()
            keywords = extract_keywords(query)
            matches = await repo.keyword_search(keywords, limit=limit)
            result.timings["l2_secondary_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
            if matches:
                result.source = "L2"

        for memory in matches:
            self._apply_freshness(memory, now)

        if matches:
            await repo.touch_access([m.id for m in matches])
            top = matches[0]
            result.hit = top.confidence >= _CONFIDENCE_THRESHOLD
            result.confidence = top.confidence
            result.stale = top.freshness_score < _FRESHNESS_THRESHOLD
            result.memories = matches
            if result.hit and not result.stale:
                await repo.hot_cache_put(
                    memory_id=top.id, cache_key=cache_key, ttl_seconds=_HOT_CACHE_TTL_SECONDS
                )

        result.total_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return result

    @staticmethod
    def _apply_freshness(memory: MemoryItem, now: datetime) -> None:
        memory.freshness_score = freshness_score(
            verified_at=memory.verified_at,
            created_at=memory.created_at,
            policy=memory.freshness_policy,
            now=now,
        )

    async def search(
        self,
        session: AsyncSession,
        *,
        query: str | None = None,
        layer: str | None = None,
        status: str | None = "active",
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryItem]:
        repo = MemoryRepository(session)
        memories = await repo.list_memories(
            layer=layer, status=status, search=query, limit=limit, offset=offset
        )
        now = datetime.now(timezone.utc)
        for memory in memories:
            self._apply_freshness(memory, now)
        return memories

    async def stats(self, session: AsyncSession) -> dict[str, Any]:
        repo = MemoryRepository(session)
        raw = await repo.stats()
        total = raw["total"] or 0
        by_layer = raw["by_layer"]
        return {
            "totalMemories": total,
            "by_layer": {
                "L0": raw["indexed"],
                "L1": by_layer.get("L1", 0),
                "L2": by_layer.get("L2", total),
            },
            "avgConfidence": round(raw["avg_confidence"], 1),
            "avgFreshness": round(raw["avg_freshness"], 1),
        }

    async def invalidate(self, session: AsyncSession, cache_key: str | None = None) -> int:
        return await MemoryRepository(session).hot_cache_invalidate(cache_key)


_brain: BrainService | None = None


def get_brain_service() -> BrainService:
    global _brain
    if _brain is None:
        _brain = BrainService()
    return _brain
