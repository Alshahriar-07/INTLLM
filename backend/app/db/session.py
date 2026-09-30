"""Async PostgreSQL session lifecycle.

The engine is created lazily. If PostgreSQL is unreachable the application
still starts and reports the database as ``unavailable`` rather than crashing
or fabricating data.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import Settings, get_settings
from app.core.errors import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)


class Database:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                self._settings.intllm_database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
                future=True,
            )
        return self._engine

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._sessionmaker is None:
            self._sessionmaker = async_sessionmaker(
                self.engine, expire_on_commit=False, class_=AsyncSession
            )
        return self._sessionmaker

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def ping(self) -> tuple[bool, str | None]:
        """Return ``(available, error)`` without raising."""
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True, None
        except Exception as exc:  # noqa: BLE001 - surfaced as service status
            return False, f"{type(exc).__name__}: {exc}"

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None


_database: Database | None = None


def get_database() -> Database:
    global _database
    if _database is None:
        _database = Database()
    return _database


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a session or a real 503."""
    database = get_database()
    available, error = await database.ping()
    if not available:
        raise ServiceUnavailableError(
            "PostgreSQL is unavailable", details={"reason": error}
        )
    async with database.session() as session:
        yield session


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
