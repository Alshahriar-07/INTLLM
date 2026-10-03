"""PostgreSQL integration tests.

These run against a real database only when ``INTLLM_TEST_DATABASE_URL`` is set
(the CI workflow provides a pgvector-enabled PostgreSQL service). Without it the
whole module is skipped, so unit runs stay hermetic. Nothing here is mocked:
migrations, persistence and restart recovery exercise actual SQL.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

from app.config.settings import Settings
from app.db import models  # noqa: F401 - register metadata
from app.db.base import Base
from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.memory import MemoryRepository
from app.db.session import Database
from app.services.security.service import ApiKeyService

TEST_URL = os.environ.get("INTLLM_TEST_DATABASE_URL")
BACKEND_ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not TEST_URL, reason="INTLLM_TEST_DATABASE_URL is not set"
)


@pytest.fixture
async def database():
    """A clean database instance with a truly empty ``public`` schema."""
    assert TEST_URL
    db = Database(Settings(INTLLM_DATABASE_URL=TEST_URL))
    available, error = await db.ping()
    if not available:
        pytest.skip(f"test database unavailable: {error}")

    async with db.engine.begin() as connection:
        try:
            await connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception as exc:  # noqa: BLE001 - reported as a skip below
            await db.dispose()
            pytest.skip(f"could not create the pgvector extension: {exc}")
        has_vector = await connection.scalar(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        if not has_vector:
            await db.dispose()
            pytest.skip("pgvector is not available in the test database")
        await connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
        await connection.exec_driver_sql("CREATE SCHEMA public")

    yield db
    await db.dispose()


async def _create_schema(db: Database) -> None:
    async with db.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def test_fresh_schema_creation(database):
    await _create_schema(database)
    async with database.engine.connect() as connection:
        for table in ("api_keys", "conversations", "messages", "memory_items", "flash_index"):
            exists = await connection.scalar(
                text(f"SELECT to_regclass('public.{table}')")
            )
            assert exists is not None, f"table {table} was not created"


async def test_migrations_apply_from_empty_schema(database):
    """A fresh install must be able to apply Alembic migrations end to end."""
    env = {**os.environ, "INTLLM_DATABASE_URL": TEST_URL or ""}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic upgrade failed:\n{result.stderr}"

    async with database.engine.connect() as connection:
        revision = await connection.scalar(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )
        assert revision, "alembic_version was not populated"
        exists = await connection.scalar(text("SELECT to_regclass('public.api_keys')"))
        assert exists is not None


async def test_api_key_persistence_and_revocation(database):
    await _create_schema(database)
    service = ApiKeyService()

    async with database.session() as session:
        record, secret = await service.create(session, name="ci-test")
        key_id = record.id
        assert secret.startswith("intllm_")

    # A new session (simulating a restart) must still verify the key.
    async with database.session() as session:
        verified = await service.verify(session, secret)
        assert verified is not None
        assert verified.name == "ci-test"
        listed = await service.list(session)
        assert len(listed) == 1
        assert listed[0].last_used_at is not None  # verification touched it

    async with database.session() as session:
        assert await service.revoke(session, key_id) is True

    async with database.session() as session:
        assert await service.verify(session, secret) is None


async def test_conversation_persistence_and_restart(database):
    await _create_schema(database)

    async with database.session() as session:
        repo = ConversationRepository(session)
        conversation = await repo.create(title="Persistence check", model_name="qwen3:8b")
        conversation_id = conversation.id
        await repo.add_message(conversation_id, "user", "hello")
        await repo.add_message(
            conversation_id, "assistant", "hi there", model_name="qwen3:8b"
        )

    # Reconnect with a fresh engine/session to prove durability.
    reloaded = Database(Settings(INTLLM_DATABASE_URL=TEST_URL))
    try:
        async with reloaded.session() as session:
            conversation = await ConversationRepository(session).get(conversation_id)
            assert conversation is not None
            assert conversation.title == "Persistence check"
            roles = sorted(m.role for m in conversation.messages)
            assert roles == ["assistant", "user"]
            contents = {m.content for m in conversation.messages}
            assert contents == {"hello", "hi there"}
    finally:
        await reloaded.dispose()


async def test_memory_persistence_and_vector_search(database):
    await _create_schema(database)

    embedding = [0.1] * 768
    async with database.session() as session:
        repo = MemoryRepository(session)
        memory = await repo.create_memory(
            type="fact",
            title="pgvector works",
            content="INTLLM stores semantic memory in PostgreSQL with pgvector.",
            normalized_content="intllm stores semantic memory in postgresql with pgvector",
            confidence=90.0,
            keywords=["pgvector", "memory"],
            embedding=embedding,
            embedding_model="test",
        )
        memory_id = memory.id

    async with database.session() as session:
        repo = MemoryRepository(session)
        stored = await repo.get_memory(memory_id)
        assert stored is not None
        assert stored.title == "pgvector works"

        results = await repo.vector_search(embedding, limit=5)
        assert results, "vector search returned no rows"
        assert results[0][0].id == memory_id
        assert results[0][1] == pytest.approx(0.0, abs=1e-6)

        stats = await repo.stats()
        assert stats["total"] == 1
        assert stats["indexed"] == 1


async def test_initialize_verifies_schema_and_preserves_data(database, monkeypatch):
    """First start initializes the schema; later starts reuse it unchanged.

    Forces the SQLAlchemy-metadata path (no Alembic) so the test targets the
    isolated test database rather than the globally-configured URL.
    """
    import app.db.session as session_mod
    from app.services.system import db_init

    monkeypatch.setattr(session_mod, "_database", database)
    monkeypatch.setattr(db_init, "_alembic_config_path", lambda: None)

    first = await db_init.initialize()
    assert first.status == "running"
    assert first.schema is True
    assert first.missing_tables == []

    async with database.session() as session:
        repo = ConversationRepository(session)
        conversation = await repo.create(title="keep me")
        await repo.add_message(conversation.id, "user", "hello")

    # A second startup must not reset or recreate anything.
    second = await db_init.initialize()
    assert second.status == "running"

    async with database.session() as session:
        loaded = await ConversationRepository(session).get(conversation.id)
        assert loaded is not None
        assert loaded.title == "keep me"
        assert len(loaded.messages) == 1


async def test_memory_keyword_search(database):
    await _create_schema(database)
    async with database.session() as session:
        repo = MemoryRepository(session)
        await repo.create_memory(
            type="preference",
            title="Prefers concise answers",
            content="The user prefers concise, technical answers.",
            normalized_content="the user prefers concise technical answers",
            keywords=["concise"],
        )
    async with database.session() as session:
        found = await MemoryRepository(session).keyword_search(["concise"])
        assert len(found) == 1
        assert found[0].title == "Prefers concise answers"
