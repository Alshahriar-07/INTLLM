"""API key service. Raw keys are shown once and never stored or logged."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.core.security import (
    KEY_PREFIX,
    generate_api_key,
    hash_api_key,
    key_fingerprint,
    verify_api_key,
)
from app.db.models import ApiKey
from app.db.repositories.audit import AuditRepository
from app.db.repositories.keys import ApiKeyRepository

DEFAULT_SCOPES = ["chat", "models.read"]


class ApiKeyService:
    async def create(
        self,
        session: AsyncSession,
        *,
        name: str,
        scopes: list[str] | None = None,
    ) -> tuple[ApiKey, str]:
        repo = ApiKeyRepository(session)
        # Cryptographic randomness already makes collisions effectively
        # impossible; the fingerprint check guarantees uniqueness anyway.
        raw_key = generate_api_key()
        for _ in range(5):
            if not await repo.fingerprint_exists(key_fingerprint(raw_key)):
                break
            raw_key = generate_api_key()
        else:
            raise ConflictError("Could not generate a unique API key; please retry.")
        salt_hex, hash_hex = hash_api_key(raw_key)
        record = await repo.create(
            name=name,
            key_prefix=KEY_PREFIX,
            fingerprint=key_fingerprint(raw_key),
            salt=salt_hex,
            key_hash=hash_hex,
            scopes=scopes or DEFAULT_SCOPES,
        )
        await AuditRepository(session).record(
            "api_key.created", target=record.name, detail={"key_id": str(record.id)}
        )
        return record, raw_key

    async def list(self, session: AsyncSession) -> list[ApiKey]:
        return await ApiKeyRepository(session).list()

    async def verify(self, session: AsyncSession, raw_key: str) -> ApiKey | None:
        repo = ApiKeyRepository(session)
        for candidate in await repo.find_active_by_raw_hint(raw_key):
            if verify_api_key(raw_key, candidate.salt, candidate.key_hash):
                await repo.touch(candidate)
                return candidate
        return None

    async def revoke(self, session: AsyncSession, key_id: uuid.UUID) -> bool:
        revoked = await ApiKeyRepository(session).revoke(key_id)
        if revoked:
            await AuditRepository(session).record(
                "api_key.revoked", target=str(key_id), outcome="success"
            )
        return revoked

    async def regenerate(
        self, session: AsyncSession, key_id: uuid.UUID
    ) -> tuple[ApiKey, str] | None:
        """Revoke the named key and issue a replacement with the same label."""
        repo = ApiKeyRepository(session)
        existing = await repo.get(key_id)
        if existing is None:
            return None
        name = existing.name
        scopes = existing.scopes or DEFAULT_SCOPES
        await repo.revoke(key_id)
        record, raw_key = await self.create(session, name=name, scopes=scopes)
        await AuditRepository(session).record(
            "api_key.regenerated",
            target=name,
            detail={"old_key_id": str(key_id), "new_key_id": str(record.id)},
        )
        return record, raw_key


_key_service: ApiKeyService | None = None


def get_api_key_service() -> ApiKeyService:
    global _key_service
    if _key_service is None:
        _key_service = ApiKeyService()
    return _key_service
