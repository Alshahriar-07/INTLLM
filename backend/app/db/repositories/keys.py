"""API key persistence. Only hashes and fingerprints are stored."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import key_fingerprint
from app.db.models import ApiKey


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[ApiKey]:
        result = await self._session.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
        return list(result.scalars().all())

    async def get(self, key_id: uuid.UUID) -> ApiKey | None:
        return await self._session.get(ApiKey, key_id)

    async def create(
        self,
        *,
        name: str,
        key_prefix: str,
        fingerprint: str,
        salt: str,
        key_hash: str,
        scopes: list[str],
    ) -> ApiKey:
        record = ApiKey(
            name=name,
            key_prefix=key_prefix,
            fingerprint=fingerprint,
            salt=salt,
            key_hash=key_hash,
            scopes=scopes,
            status="active",
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def fingerprint_exists(self, fingerprint: str) -> bool:
        result = await self._session.scalar(
            select(ApiKey.id).where(ApiKey.fingerprint == fingerprint)
        )
        return result is not None

    async def find_active_by_raw_hint(self, raw_key: str) -> list[ApiKey]:
        """Narrow candidates by fingerprint before constant-time verification."""
        fingerprint = key_fingerprint(raw_key)
        result = await self._session.execute(
            select(ApiKey).where(
                ApiKey.fingerprint == fingerprint, ApiKey.status == "active"
            )
        )
        return list(result.scalars().all())

    async def touch(self, record: ApiKey) -> None:
        record.last_used_at = datetime.now(UTC)
        await self._session.flush()

    async def revoke(self, key_id: uuid.UUID) -> bool:
        record = await self.get(key_id)
        if record is None:
            return False
        record.status = "revoked"
        record.revoked_at = datetime.now(UTC)
        await self._session.flush()
        return True
