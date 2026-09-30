"""Diagnostics: real metrics, audit events and runtime endpoint configuration."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.metrics import metrics
from app.db.repositories.audit import AuditRepository


class DiagnosticsService:
    async def snapshot(self, session: AsyncSession | None = None) -> dict[str, object]:
        settings = get_settings()
        snapshot: dict[str, object] = {
            "metrics": metrics.snapshot(),
            "runtime_endpoint": settings.runtime_endpoint,
            "environment": settings.intllm_env,
        }
        if session is not None:
            events = await AuditRepository(session).recent(limit=25)
            snapshot["audit"] = [
                {
                    "action": event.action,
                    "actor": event.actor,
                    "target": event.target,
                    "outcome": event.outcome,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                }
                for event in events
            ]
        return snapshot


_diagnostics: DiagnosticsService | None = None


def get_diagnostics_service() -> DiagnosticsService:
    global _diagnostics
    if _diagnostics is None:
        _diagnostics = DiagnosticsService()
    return _diagnostics
