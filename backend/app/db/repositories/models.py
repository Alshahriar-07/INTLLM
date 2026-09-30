"""Model registry persistence."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModelRecord


class ModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[ModelRecord]:
        result = await self._session.execute(select(ModelRecord).order_by(ModelRecord.name))
        return list(result.scalars().all())

    async def get(self, model_id: uuid.UUID) -> ModelRecord | None:
        return await self._session.get(ModelRecord, model_id)

    async def get_by_name(self, name: str) -> ModelRecord | None:
        result = await self._session.execute(
            select(ModelRecord).where(ModelRecord.name == name)
        )
        return result.scalar_one_or_none()

    async def upsert(self, name: str, **fields: Any) -> ModelRecord:
        record = await self.get_by_name(name)
        if record is None:
            record = ModelRecord(name=name, ollama_identifier=fields.get("ollama_identifier", name))
            self._session.add(record)
        for key, value in fields.items():
            if value is not None and hasattr(record, key):
                setattr(record, key, value)
        await self._session.flush()
        return record

    async def set_default(self, name: str) -> None:
        await self._session.execute(update(ModelRecord).values(is_default=False))
        record = await self.get_by_name(name)
        if record is not None:
            record.is_default = True
        await self._session.flush()

    async def delete(self, name: str) -> bool:
        record = await self.get_by_name(name)
        if record is None:
            return False
        await self._session.delete(record)
        return True
