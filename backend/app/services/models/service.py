"""Model service.

Merges live Ollama inventory with persistent registry metadata and derives
hardware-aware tier recommendations. No models are ever invented: an empty
Ollama install yields an empty list.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import ModelRecord
from app.db.repositories.models import ModelRepository
from app.services.runtime.base import ModelInfo, RuntimeUnavailable
from app.services.runtime.ollama import OllamaAdapter, get_ollama_adapter

logger = get_logger(__name__)

TIER_POTATO = "POTATO"
TIER_NEUTRAL = "NEUTRAL"
TIER_WHOLE_PC = "I PAID FOR MY WHOLE PC"


def tier_for_memory(memory_req_gb: float | None) -> str:
    if memory_req_gb is None:
        return TIER_NEUTRAL
    if memory_req_gb < 6:
        return TIER_POTATO
    if memory_req_gb <= 20:
        return TIER_NEUTRAL
    return TIER_WHOLE_PC


class ModelService:
    def __init__(self, adapter: OllamaAdapter | None = None) -> None:
        self._adapter = adapter or get_ollama_adapter()

    async def runtime_health(self) -> tuple[bool, str | None]:
        return await self._adapter.health()

    async def sync_registry(self, session: AsyncSession) -> list[ModelRecord]:
        """Pull live Ollama inventory into the registry. Raises if offline."""
        live = await self._adapter.list_models()
        repo = ModelRepository(session)
        existing = {record.name: record for record in await repo.list()}
        live_names = {info.name for info in live}

        for info in live:
            record = existing.get(info.name)
            memory_req = self._estimate_memory_gb(info)
            fields: dict[str, Any] = {
                "ollama_identifier": info.name,
                "family": info.family,
                "parameter_size": info.parameter_size,
                "quantization": info.quantization,
                "size_bytes": info.size_bytes,
                "memory_req_gb": memory_req,
                "tier": tier_for_memory(memory_req),
                "installed": True,
            }
            if record is None and not info.capabilities:
                fields["capabilities"] = await self._detect_capabilities(info.name)
            await repo.upsert(info.name, **fields)

        # Models removed from Ollama are marked uninstalled, not deleted.
        for name, record in existing.items():
            if name not in live_names and record.installed:
                record.installed = False

        await session.flush()
        return await repo.list()

    async def list_models(self, session: AsyncSession) -> list[ModelRecord]:
        return await ModelRepository(session).list()

    async def set_default(self, session: AsyncSession, name: str) -> bool:
        repo = ModelRepository(session)
        if await repo.get_by_name(name) is None:
            return False
        await repo.set_default(name)
        return True

    async def delete_model(self, session: AsyncSession, name: str) -> tuple[bool, str | None]:
        ok, error = await self._adapter.delete(name)
        if not ok:
            return False, error
        await ModelRepository(session).delete(name)
        return True, None

    async def pull(self, name: str) -> AsyncIterator[dict[str, Any]]:
        async for progress in self._adapter.pull(name):
            yield progress

    async def _detect_capabilities(self, name: str) -> list[str]:
        try:
            detail = await self._adapter.show(name)
        except RuntimeUnavailable:
            return []
        caps = detail.get("capabilities")
        if isinstance(caps, list):
            return [str(c) for c in caps]
        return []

    @staticmethod
    def _estimate_memory_gb(info: ModelInfo) -> float | None:
        if info.size_bytes:
            # Weights must fit alongside KV cache; use ~1.15x weight size.
            return round((info.size_bytes / (1024**3)) * 1.15, 1)
        return None

    async def recommend(
        self, session: AsyncSession, *, vram_total_gb: float | None, ram_total_gb: float | None
    ) -> list[dict[str, Any]]:
        """Compatibility ranking from actual hardware + actual installed models."""
        records = await ModelRepository(session).list()
        budget = vram_total_gb if vram_total_gb else (ram_total_gb * 0.7 if ram_total_gb else None)
        recommendations: list[dict[str, Any]] = []
        for record in records:
            required = record.memory_req_gb
            fits = budget is None or required is None or required <= budget
            utilization = (
                round((required / budget) * 100, 1)
                if budget and required
                else None
            )
            recommendations.append(
                {
                    "name": record.name,
                    "tier": record.tier or tier_for_memory(required),
                    "memory_req_gb": required,
                    "fits": fits,
                    "utilization_percent": utilization,
                    "installed": record.installed,
                    "parameter_size": record.parameter_size,
                    "family": record.family,
                }
            )
        recommendations.sort(
            key=lambda item: (not item["fits"], -(item["memory_req_gb"] or 0))
        )
        return recommendations
