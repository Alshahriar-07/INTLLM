"""PostgreSQL lifecycle health and error diagnostics.

The UI must be able to tell the difference between four database states —
``connected`` / ``disconnected`` / ``initializing`` / ``error`` — instead of a
single boolean. This module is the single source of truth for that state.

It also classifies connection failures into actionable categories so an operator
can tell *why* PostgreSQL is unavailable (service not running, bad credentials,
missing database, migration failure, ...) rather than seeing one vague message.
Messages are sanitized so a DSN password can never reach the logs or the UI.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

# --- Database states -------------------------------------------------------
STATUS_INITIALIZING = "initializing"
STATUS_CONNECTED = "connected"
STATUS_DISCONNECTED = "disconnected"
STATUS_ERROR = "error"

# --- Memory states (derived from PostgreSQL + pgvector + schema) -----------
MEMORY_INITIALIZING = "initializing"
MEMORY_AVAILABLE = "available"
MEMORY_UNAVAILABLE = "unavailable"
MEMORY_ERROR = "error"

# --- Diagnostic categories -------------------------------------------------
CATEGORY_SERVICE_NOT_RUNNING = "service_not_running"
CATEGORY_CONNECTION_REFUSED = "connection_refused"
CATEGORY_AUTHENTICATION_FAILED = "authentication_failed"
CATEGORY_DATABASE_MISSING = "database_missing"
CATEGORY_TIMEOUT = "timeout"
CATEGORY_MIGRATION_FAILURE = "migration_failure"
CATEGORY_SCHEMA_MISSING = "schema_missing"
CATEGORY_PGVECTOR_MISSING = "pgvector_missing"
CATEGORY_UNEXPECTED = "unexpected"

#: Categories that indicate a misconfiguration (status ``error``) rather than a
#: transient outage (status ``disconnected``).
_CONFIGURATION_CATEGORIES = frozenset(
    {
        CATEGORY_AUTHENTICATION_FAILED,
        CATEGORY_DATABASE_MISSING,
        CATEGORY_MIGRATION_FAILURE,
        CATEGORY_SCHEMA_MISSING,
        CATEGORY_PGVECTOR_MISSING,
        CATEGORY_UNEXPECTED,
    }
)

_DSN_PASSWORD = re.compile(r"(?P<scheme>[a-zA-Z0-9+]+://[^:/@\s]+):[^@\s/]+@")
_PGVECTOR_ACTION = (
    "Install the pgvector extension for your PostgreSQL server "
    "(https://github.com/pgvector/pgvector) and re-run INTLLM."
)


def sanitize_text(value: Any) -> str | None:
    """Remove DSN passwords from a diagnostic string.

    asyncpg/SQLAlchemy almost never include the password, but a malformed URL or
    a driver wrapping the DSN in an error can — strip it defensively.
    """
    if value is None:
        return None
    text = str(value)
    return _DSN_PASSWORD.sub(r"\g<scheme>:***@", text)


@dataclass(slots=True)
class DatabaseDiagnostic:
    """A classified, actionable database failure."""

    category: str
    message: str
    actions: list[str] = field(default_factory=list)


def _cause_chain(exc: BaseException | None) -> list[BaseException]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen and len(chain) < 8:
        seen.add(id(current))
        chain.append(current)
        nxt = getattr(current, "orig", None)
        if nxt is None:
            nxt = current.__cause__ or current.__context__
        current = nxt if isinstance(nxt, BaseException) else None
    return chain


def classify_database_error(exc: BaseException | None) -> DatabaseDiagnostic:
    """Map a connection/migration exception to an actionable category."""
    if exc is None:
        return DatabaseDiagnostic(
            category=CATEGORY_UNEXPECTED,
            message="Unknown database error",
            actions=["Re-run INTLLM and check the backend logs for details."],
        )

    chain = _cause_chain(exc)
    names = " ".join(type(item).__name__ for item in chain).lower()
    text = sanitize_text(" | ".join(str(item) for item in chain)) or ""
    lowered = text.lower()
    codes = {
        str(getattr(item, "pgcode", "") or "").upper() for item in chain
    } | {str(getattr(item, "sqlstate", "") or "").upper() for item in chain}

    # pgvector / schema problems raised as plain exceptions.
    if "missing pgvector" in lowered or "extension \"vector\"" in lowered:
        return DatabaseDiagnostic(
            category=CATEGORY_PGVECTOR_MISSING, message=text, actions=[_PGVECTOR_ACTION]
        )

    if "3D000" in codes or "invalidcatalogname" in names or (
        "database" in lowered and "does not exist" in lowered
    ):
        return DatabaseDiagnostic(
            category=CATEGORY_DATABASE_MISSING,
            message=text,
            actions=[
                "Create the database (or let INTLLM create it automatically) and "
                "ensure the configured user can access it."
            ],
        )

    if (
        "28P01" in codes
        or "28000" in codes
        or "invalidpassword" in names
        or "invalidauthorization" in names
        or "password authentication failed" in lowered
        or "authentication failed" in lowered
    ):
        return DatabaseDiagnostic(
            category=CATEGORY_AUTHENTICATION_FAILED,
            message=text,
            actions=[
                "Check INTLLM_DATABASE_URL: the username/password must match the "
                "local PostgreSQL role (never commit them to source)."
            ],
        )

    if (
        "timeout" in names
        or "timeout" in lowered
        or "timed out" in lowered
        or "timeout expired" in lowered
    ):
        return DatabaseDiagnostic(
            category=CATEGORY_TIMEOUT,
            message=text,
            actions=[
                "PostgreSQL did not answer in time. Confirm the server is running "
                "and reachable at the configured host/port."
            ],
        )

    if (
        "connectionrefused" in names
        or "connection refused" in lowered
        or "actively refused" in lowered
        or "10061" in lowered
        or "no connection could be made" in lowered
    ):
        return DatabaseDiagnostic(
            category=CATEGORY_SERVICE_NOT_RUNNING,
            message=text,
            actions=[
                "Start the local PostgreSQL service and confirm it listens on the "
                "configured host/port (default 127.0.0.1:5432), then re-run INTLLM."
            ],
        )

    if (
        "cannotconnectnow" in names
        or "57P03" in codes
        or "starting up" in lowered
    ):
        return DatabaseDiagnostic(
            category=CATEGORY_SERVICE_NOT_RUNNING,
            message=text,
            actions=["PostgreSQL is still starting up. Wait a moment and retry."],
        )

    if (
        "connectiondoesnotexist" in names
        or "connectionwasclosed" in names
        or "server closed the connection" in lowered
        or "connection reset" in lowered
    ):
        return DatabaseDiagnostic(
            category=CATEGORY_CONNECTION_REFUSED,
            message=text,
            actions=["The connection was dropped. INTLLM will retry automatically."],
        )

    if "migration" in lowered or "alembic" in lowered:
        return DatabaseDiagnostic(
            category=CATEGORY_MIGRATION_FAILURE,
            message=text,
            actions=[
                "Verify the database user has CREATE privileges and re-run INTLLM."
            ],
        )

    return DatabaseDiagnostic(
        category=CATEGORY_UNEXPECTED,
        message=text,
        actions=["Check the INTLLM backend logs for the underlying database error."],
    )


def status_for_diagnostic(category: str) -> str:
    """Configuration problems are ``error``; transient outages are ``disconnected``."""
    return STATUS_ERROR if category in _CONFIGURATION_CATEGORIES else STATUS_DISCONNECTED


@dataclass
class DatabaseHealthSnapshot:
    """Serializable snapshot of the database/memory subsystem state."""

    status: str = STATUS_INITIALIZING
    memory: str = MEMORY_INITIALIZING
    ready: bool = False
    category: str | None = None
    detail: str | None = None
    actions: list[str] = field(default_factory=list)
    pgvector: bool = False
    schema: bool = False
    migration: str | None = None
    checked_at: str | None = None
    initialized_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class DatabaseHealth:
    """Mutable process-wide health state.

    The database layer records transitions here; the health/status endpoints
    read them so the frontend never has to infer state from a bare ping.
    """

    def __init__(self) -> None:
        self._snapshot = DatabaseHealthSnapshot()

    # --- transitions ------------------------------------------------------
    def begin_initialization(self) -> DatabaseHealthSnapshot:
        self._snapshot.status = STATUS_INITIALIZING
        self._snapshot.memory = MEMORY_INITIALIZING
        self._snapshot.ready = False
        self._snapshot.category = None
        self._snapshot.detail = None
        self._snapshot.actions = []
        self._snapshot.checked_at = _now_iso()
        return self.snapshot()

    def mark_connected(
        self,
        *,
        pgvector: bool,
        schema: bool,
        migration: str | None = None,
    ) -> DatabaseHealthSnapshot:
        snap = self._snapshot
        snap.pgvector = pgvector
        snap.schema = schema
        snap.migration = migration
        snap.checked_at = _now_iso()

        if pgvector and schema:
            snap.status = STATUS_CONNECTED
            snap.memory = MEMORY_AVAILABLE
            snap.ready = True
            snap.category = None
            snap.detail = migration or "schema ready"
            snap.actions = []
            if snap.initialized_at is None:
                snap.initialized_at = _now_iso()
            return self.snapshot()

        if not pgvector:
            snap.status = STATUS_ERROR
            snap.memory = MEMORY_ERROR
            snap.ready = False
            snap.category = CATEGORY_PGVECTOR_MISSING
            snap.detail = "PostgreSQL is reachable but the pgvector extension is not available."
            snap.actions = [_PGVECTOR_ACTION]
            return self.snapshot()

        # Connected, pgvector present, but the schema has not been verified.
        snap.status = STATUS_ERROR
        snap.memory = MEMORY_UNAVAILABLE
        snap.ready = False
        snap.category = CATEGORY_SCHEMA_MISSING
        snap.detail = "The database schema has not been initialized or is incomplete."
        snap.actions = ["Re-run INTLLM to apply the schema automatically."]
        return self.snapshot()

    def mark_failure(self, diagnostic: DatabaseDiagnostic) -> DatabaseHealthSnapshot:
        snap = self._snapshot
        snap.status = status_for_diagnostic(diagnostic.category)
        snap.memory = (
            MEMORY_ERROR if snap.status == STATUS_ERROR else MEMORY_UNAVAILABLE
        )
        snap.ready = False
        snap.category = diagnostic.category
        snap.detail = diagnostic.message
        snap.actions = list(diagnostic.actions)
        snap.checked_at = _now_iso()
        return self.snapshot()

    def mark_schema_failure(self, exc: BaseException) -> DatabaseHealthSnapshot:
        diagnostic = classify_database_error(exc)
        diagnostic.category = CATEGORY_MIGRATION_FAILURE
        diagnostic.actions = [
            "Verify the database user has CREATE privileges (and rights to CREATE "
            "EXTENSION vector), then re-run INTLLM."
        ]
        return self.mark_failure(diagnostic)

    def snapshot(self) -> DatabaseHealthSnapshot:
        return DatabaseHealthSnapshot(**asdict(self._snapshot))


_health: DatabaseHealth | None = None


def get_database_health() -> DatabaseHealth:
    global _health
    if _health is None:
        _health = DatabaseHealth()
    return _health


__all__ = [
    "CATEGORY_AUTHENTICATION_FAILED",
    "CATEGORY_CONNECTION_REFUSED",
    "CATEGORY_DATABASE_MISSING",
    "CATEGORY_MIGRATION_FAILURE",
    "CATEGORY_PGVECTOR_MISSING",
    "CATEGORY_SCHEMA_MISSING",
    "CATEGORY_SERVICE_NOT_RUNNING",
    "CATEGORY_TIMEOUT",
    "CATEGORY_UNEXPECTED",
    "MEMORY_AVAILABLE",
    "MEMORY_ERROR",
    "MEMORY_INITIALIZING",
    "MEMORY_UNAVAILABLE",
    "STATUS_CONNECTED",
    "STATUS_DISCONNECTED",
    "STATUS_ERROR",
    "STATUS_INITIALIZING",
    "DatabaseDiagnostic",
    "DatabaseHealth",
    "DatabaseHealthSnapshot",
    "classify_database_error",
    "get_database_health",
    "sanitize_text",
    "status_for_diagnostic",
]
