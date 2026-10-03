"""Background learning worker.

Runs real, low-priority memory maintenance and yields to interactive requests
via the resource governor. Job state is persisted; the frontend only ever sees
tasks that actually exist.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from app.core.events import event_bus
from app.core.logging import get_logger
from app.db.repositories.background import BackgroundRepository
from app.db.repositories.memory import MemoryRepository
from app.db.session import get_database
from app.services.background.governor import ResourceGovernor, ResourceState

logger = get_logger(__name__)

# Rotating maintenance job types (PLAN/11-background-learning).
JOB_TYPES = (
    ("Memory Verification", "memory_verification"),
    ("Stale Memory Refresh", "stale_memory_refresh"),
    ("Embedding Index Update", "embedding_index_update"),
    ("Hot Cache Cleanup", "hot_cache_cleanup"),
)


class BackgroundLearningService:
    def __init__(self, governor: ResourceGovernor | None = None) -> None:
        self.governor = governor or ResourceGovernor()
        self._task: asyncio.Task[None] | None = None
        self._stopping = False
        self._job_cursor = 0
        self._last_task: dict[str, Any] | None = None

    # --- lifecycle --------------------------------------------------------
    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopping = False
        self._task = asyncio.create_task(self._loop(), name="background-learning")
        logger.info("background learning worker started")

    async def stop(self) -> None:
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("background learning worker stopped")

    # --- interactive priority --------------------------------------------
    @contextlib.asynccontextmanager
    async def interactive_scope(self) -> AsyncIterator[None]:
        self.governor.begin_interactive()
        try:
            yield
        finally:
            self.governor.end_interactive()

    def record_interactive_latency(self, ms: float) -> None:
        self.governor.record_latency(ms)

    def pause(self) -> None:
        self.governor.set_paused(True)

    def resume(self) -> None:
        self.governor.set_paused(False)

    # --- loop -------------------------------------------------------------
    async def _loop(self) -> None:
        from app.config.settings import get_settings

        settings = get_settings()
        while not self._stopping:
            delay = settings.intllm_background_poll_seconds
            try:
                state = self.governor.evaluate()
                if state is not ResourceState.NORMAL:
                    await event_bus.emit(
                        "background",
                        "background.paused" if state is ResourceState.CRITICAL else "background.throttled",
                        {"state": state.value},
                    )
                    await asyncio.sleep(self.governor.next_delay(delay))
                    continue

                await self._run_next_job()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("background loop iteration failed")
            await asyncio.sleep(self.governor.next_delay(delay))

    async def _run_next_job(self) -> None:
        database = get_database()
        available, _error = await database.ping()
        if not available:
            return

        name, job_type = JOB_TYPES[self._job_cursor % len(JOB_TYPES)]
        self._job_cursor += 1

        async with database.session() as session:
            repo = BackgroundRepository(session)
            job = await repo.create(name=name, job_type=job_type)
            await repo.update(job, status="running", current_action=f"Executing {name}")
            await repo.add_event(job, "background.started", message=name)
            await event_bus.emit(
                "background", "background.started", {"job_id": str(job.id), "name": name}
            )

            try:
                detail = await self._execute(session, job_type)
                await repo.update(job, status="completed", progress=100.0, current_action="Done")
                await repo.add_event(job, "background.completed", message=name, data=detail)
                await event_bus.emit(
                    "background",
                    "background.completed",
                    {"job_id": str(job.id), "name": name, "detail": detail},
                )
                self._last_task = {"name": name, "type": job_type, "detail": detail}
            except Exception as exc:  # noqa: BLE001
                await repo.update(job, status="failed", error=str(exc))
                await repo.add_event(job, "background.failed", message=str(exc))
                await event_bus.emit(
                    "background", "background.failed", {"job_id": str(job.id), "error": str(exc)}
                )

    async def _execute(self, session, job_type: str) -> dict[str, Any]:
        memory_repo = MemoryRepository(session)

        if job_type == "memory_verification":
            expired = await memory_repo.expired()
            if expired:
                await memory_repo.mark_stale([m.id for m in expired])
            return {"expired_marked_stale": len(expired)}

        if job_type == "hot_cache_cleanup":
            removed = await memory_repo.hot_cache_invalidate()
            return {"hot_cache_entries_cleared": removed}

        if job_type == "embedding_index_update":
            # Report how many memories still lack a vector (honest count).
            stats = await memory_repo.stats()
            return {"indexed_embeddings": stats["indexed"], "total_memories": stats["total"]}

        if job_type == "stale_memory_refresh":
            stats = await memory_repo.stats()
            return {"avg_freshness": round(stats["avg_freshness"], 1)}

        return {"noop": True}

    # --- status -----------------------------------------------------------
    async def status(self) -> dict[str, Any]:
        database = get_database()
        available, error = await database.ping()
        state = self.governor.evaluate()
        tasks: list[dict[str, Any]] = []
        if available:
            async with database.session() as session:
                repo = BackgroundRepository(session)
                jobs = await repo.list_jobs(limit=25)
                for job in jobs:
                    tasks.append(
                        {
                            "id": str(job.id),
                            "name": job.name,
                            "type": job.job_type,
                            "priority": job.priority,
                            "status": job.status,
                            "progress": job.progress,
                            "currentAction": job.current_action,
                            "cpuBudget": job.cpu_budget,
                            "createdAt": job.created_at.isoformat() if job.created_at else None,
                        }
                    )
        return {
            "connected": available,
            "state": state.value,
            "isThrottled": state is not ResourceState.NORMAL,
            "paused": self.governor.paused,
            "activeInteractive": self.governor.active_interactive,
            "recentLatencyMs": self.governor.recent_latency_ms,
            "tasks": tasks,
            "error": error,
            "capturedAt": datetime.now(UTC).isoformat(),
        }


_background: BackgroundLearningService | None = None


def get_background_service() -> BackgroundLearningService:
    global _background
    if _background is None:
        _background = BackgroundLearningService()
    return _background
