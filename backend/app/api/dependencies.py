"""FastAPI dependencies: sessions, settings and API key authentication."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, ServiceUnavailableError
from app.db.models import ApiKey
from app.db.session import get_database
from app.services.api_server.service import is_loopback_host
from app.services.security.service import get_api_key_service


async def get_session_optional() -> AsyncIterator[AsyncSession | None]:
    """Yield a session, or ``None`` when PostgreSQL is unavailable."""
    database = get_database()
    available, _ = await database.ping()
    if not available:
        yield None
        return
    async with database.session() as session:
        yield session


async def get_session_required() -> AsyncIterator[AsyncSession]:
    database = get_database()
    available, error = await database.ping()
    if not available:
        raise ServiceUnavailableError("PostgreSQL is unavailable", details={"reason": error})
    async with database.session() as session:
        yield session


async def require_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> ApiKey | None:
    """Validate a Bearer / x-api-key credential for the OpenAI-compatible API."""
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_api_key:
        token = x_api_key.strip()

    if not token:
        # Bootstrap: allow loopback-only access until the first key exists.
        if _is_loopback(request.client.host if request.client else None):
            database = get_database()
            available, _ = await database.ping()
            if available:
                async with database.session() as session:
                    keys = await get_api_key_service().list(session)
                if not keys:
                    return None
        raise AuthenticationError("Missing API key")

    database = get_database()
    available, error = await database.ping()
    if not available:
        raise ServiceUnavailableError("PostgreSQL is unavailable", details={"reason": error})
    async with database.session() as session:
        key = await get_api_key_service().verify(session, token)
    if key is None:
        raise AuthenticationError("Invalid or revoked API key")
    return key


def _is_loopback(host: str | None) -> bool:
    return is_loopback_host(host)
