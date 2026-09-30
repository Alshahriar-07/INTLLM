"""Background job and job-event persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BackgroundJob, JobEvent


class BackgroundRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_jobs(self, limit: int = 50) -> list[BackgroundJob]:
        result = await self._session.execute(
            select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def active_jobs(self) -> list[BackgroundJob]:
        result = await self._session.execute(
            select(BackgroundJob).where(
                BackgroundJob.status.in_(("queued", "running", "throttled", "paused"))
            )
        )
        return list(result.scalars().all())

    async def get(self, job_id: uuid.UUID) -> BackgroundJob | None:
        return await self._session.get(BackgroundJob, job_id)

    async def create(
        self,
        *,
        name: str,
        job_type: str,
        priority: str = "P2 (Maintenance)",
        cpu_budget: str = "Low",
        payload: dict[str, Any] | None = None,
    ) -> BackgroundJob:
        job = BackgroundJob(
            name=name,
            job_type=job_type,
            priority=priority,
            cpu_budget=cpu_budget,
            payload=payload or {},
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def update(
        self,
        job: BackgroundJob,
        *,
        status: str | None = None,
        progress: float | None = None,
        current_action: str | None = None,
        error: str | None = None,
    ) -> BackgroundJob:
        if status is not None:
            job.status = status
            if status == "running" and job.started_at is None:
                job.started_at = datetime.now(timezone.utc)
            if status in ("completed", "failed"):
                job.finished_at = datetime.now(timezone.utc)
        if progress is not None:
            job.progress = progress
        if current_action is not None:
            job.current_action = current_action
        if error is not None:
            job.error = error
        await self._session.flush()
        return job

    async def add_event(
        self,
        job: BackgroundJob,
        event_type: str,
        *,
        message: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> JobEvent:
        event = JobEvent(
            job_id=job.id, event_type=event_type, message=message, data=data or {}
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def events(self, job_id: uuid.UUID, limit: int = 100) -> list[JobEvent]:
        result = await self._session.execute(
            select(JobEvent)
            .where(JobEvent.job_id == job_id)
            .order_by(JobEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
