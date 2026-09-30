"""Audit event persistence. Never stores secrets."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        action: str,
        *,
        actor: str = "local",
        target: str | None = None,
        outcome: str = "success",
        detail: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            actor=actor,
            target=target,
            outcome=outcome,
            detail=detail or {},
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def recent(self, limit: int = 50) -> list[AuditEvent]:
        result = await self._session.execute(
            select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
