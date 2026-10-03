"""Database health states and error diagnostics.

These exercise the classification/state logic hermetically — no live PostgreSQL
is required. A real driver exception is only used to prove that DSN passwords
are stripped from messages.
"""

from __future__ import annotations

from app.db.health import (
    CATEGORY_AUTHENTICATION_FAILED,
    CATEGORY_DATABASE_MISSING,
    CATEGORY_PGVECTOR_MISSING,
    CATEGORY_SERVICE_NOT_RUNNING,
    CATEGORY_TIMEOUT,
    CATEGORY_UNEXPECTED,
    MEMORY_AVAILABLE,
    MEMORY_ERROR,
    STATUS_CONNECTED,
    STATUS_DISCONNECTED,
    STATUS_ERROR,
    STATUS_INITIALIZING,
    DatabaseHealth,
    classify_database_error,
    sanitize_text,
    status_for_diagnostic,
)


class _PgError(Exception):
    def __init__(self, message: str, *, pgcode: str | None = None) -> None:
        super().__init__(message)
        self.pgcode = pgcode


class _OperationalError(Exception):
    """Stands in for SQLAlchemy's OperationalError wrapping a driver error."""

    def __init__(self, orig: BaseException) -> None:
        super().__init__(str(orig))
        self.orig = orig


def test_sanitize_text_strips_dsn_password():
    text = "could not connect: postgresql+asyncpg://intllm:sup3rsecret@127.0.0.1:5432/intllm"
    cleaned = sanitize_text(text)
    assert cleaned is not None
    assert "sup3rsecret" not in cleaned
    assert "***@" in cleaned


def test_classify_missing_database():
    diagnostic = classify_database_error(
        _OperationalError(_PgError('database "intllm" does not exist', pgcode="3D000"))
    )
    assert diagnostic.category == CATEGORY_DATABASE_MISSING
    assert diagnostic.actions


def test_classify_invalid_credentials_pgcode():
    diagnostic = classify_database_error(
        _OperationalError(_PgError("password authentication failed", pgcode="28P01"))
    )
    assert diagnostic.category == CATEGORY_AUTHENTICATION_FAILED


def test_classify_connection_refused_means_service_not_running():
    diagnostic = classify_database_error(ConnectionRefusedError("connection refused"))
    assert diagnostic.category == CATEGORY_SERVICE_NOT_RUNNING
    assert status_for_diagnostic(diagnostic.category) == STATUS_DISCONNECTED


def test_classify_timeout():
    diagnostic = classify_database_error(TimeoutError("connect timed out"))
    assert diagnostic.category == CATEGORY_TIMEOUT
    assert status_for_diagnostic(diagnostic.category) == STATUS_DISCONNECTED


def test_classify_unknown_is_error():
    diagnostic = classify_database_error(RuntimeError("something exploded"))
    assert diagnostic.category == CATEGORY_UNEXPECTED
    assert status_for_diagnostic(diagnostic.category) == STATUS_ERROR


def test_classify_none_is_unexpected():
    assert classify_database_error(None).category == CATEGORY_UNEXPECTED


def test_health_transitions_initializing_then_connected():
    health = DatabaseHealth()
    assert health.snapshot().status == STATUS_INITIALIZING
    snapshot = health.mark_connected(pgvector=True, schema=True, migration="0001_initial")
    assert snapshot.status == STATUS_CONNECTED
    assert snapshot.memory == MEMORY_AVAILABLE
    assert snapshot.ready is True
    assert snapshot.initialized_at is not None


def test_health_marks_pgvector_missing_as_error():
    health = DatabaseHealth()
    snapshot = health.mark_connected(pgvector=False, schema=True)
    assert snapshot.status == STATUS_ERROR
    assert snapshot.memory == MEMORY_ERROR
    assert snapshot.category == CATEGORY_PGVECTOR_MISSING
    assert snapshot.ready is False


class _RefusingConnCtx:
    async def __aenter__(self):
        raise ConnectionRefusedError("connection refused")

    async def __aexit__(self, *args):
        return False


class _RefusingEngine:
    def connect(self):
        return _RefusingConnCtx()


async def test_ping_failure_updates_shared_health(monkeypatch):
    """A refused connection is recorded as ``disconnected`` with a category."""
    from app.db.health import get_database_health
    from app.db.session import Database

    monkeypatch.setattr(
        "app.db.session.create_async_engine", lambda *a, **k: _RefusingEngine()
    )
    database = Database()
    available, error = await database.ping()
    assert available is False
    snapshot = get_database_health().snapshot()
    assert snapshot.status == STATUS_DISCONNECTED
    assert snapshot.category == CATEGORY_SERVICE_NOT_RUNNING
    assert error is not None
