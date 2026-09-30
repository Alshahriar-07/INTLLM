"""SQLAlchemy ORM models for the INTLLM PostgreSQL schema.

Mirrors PLAN/08-database/SCHEMA.md. Business logic lives in services; these
models are persistence only.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey

# Default embedding width. Ollama embedding models differ; when a returned
# vector does not match this width it is stored as keyword-only (no vector).
EMBEDDING_DIM = 768


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class ModelRecord(Base, TimestampMixin):
    __tablename__ = "models"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ollama_identifier: Mapped[str] = mapped_column(String(255))
    family: Mapped[str | None] = mapped_column(String(128))
    parameter_size: Mapped[str | None] = mapped_column(String(64))
    quantization: Mapped[str | None] = mapped_column(String(64))
    context_length: Mapped[int | None] = mapped_column(Integer)
    memory_req_gb: Mapped[float | None] = mapped_column(Float)
    tier: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    capabilities: Mapped[list[str]] = mapped_column(JSONB, default=list)
    installed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    model_name: Mapped[str | None] = mapped_column(String(255))

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str | None] = mapped_column(String(255))
    token_count: Mapped[int | None] = mapped_column(Integer)
    activities: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    memory_used: Mapped[int] = mapped_column(Integer, default=0)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class MemoryItem(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "memory_items"

    type: Mapped[str] = mapped_column(String(32), index=True)  # fact/workflow/lesson/preference
    title: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    normalized_content: Mapped[str] = mapped_column(Text)
    layer: Mapped[str] = mapped_column(String(8), default="L2", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=50.0)
    importance: Mapped[float] = mapped_column(Float, default=50.0)
    freshness_score: Mapped[float] = mapped_column(Float, default=100.0)
    freshness_policy: Mapped[str] = mapped_column(String(32), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    sources: Mapped[list["MemorySource"]] = relationship(
        back_populates="memory", cascade="all, delete-orphan"
    )
    flash: Mapped["FlashIndex | None"] = relationship(
        back_populates="memory", cascade="all, delete-orphan", uselist=False
    )


class MemorySource(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "memory_sources"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memory_items.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(512))
    source_type: Mapped[str] = mapped_column(String(32), default="unknown")
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified")

    memory: Mapped[MemoryItem] = relationship(back_populates="sources")


class FlashIndex(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "flash_index"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memory_items.id", ondelete="CASCADE"), unique=True, index=True
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(255))
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    memory_type: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float, default=50.0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access_count: Mapped[int] = mapped_column(Integer, default=0)

    memory: Mapped[MemoryItem] = relationship(back_populates="flash")


class HotCacheMetadata(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "hot_cache_metadata"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memory_items.id", ondelete="CASCADE"), index=True
    )
    cache_key: Mapped[str] = mapped_column(String(255), index=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ToolRun(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "tool_runs"

    tool_name: Mapped[str] = mapped_column(String(128), index=True)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    permission: Mapped[str] = mapped_column(String(32), default="read-only")
    risk_level: Mapped[str] = mapped_column(String(16), default="Low")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BrowserSession(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "browser_sessions"

    status: Mapped[str] = mapped_column(String(32), default="closed", index=True)
    current_url: Mapped[str | None] = mapped_column(Text)
    headless: Mapped[bool] = mapped_column(Boolean, default=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class ApiKey(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(String(128))
    key_prefix: Mapped[str] = mapped_column(String(32))
    fingerprint: Mapped[str] = mapped_column(String(32), index=True)
    salt: Mapped[str] = mapped_column(String(64))
    key_hash: Mapped[str] = mapped_column(String(128))
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BackgroundJob(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "background_jobs"

    name: Mapped[str] = mapped_column(String(128))
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    priority: Mapped[str] = mapped_column(String(32), default="P2 (Maintenance)")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_action: Mapped[str] = mapped_column(String(255), default="")
    cpu_budget: Mapped[str] = mapped_column(String(16), default="Low")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    events: Mapped[list["JobEvent"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobEvent(Base, UUIDPrimaryKey):
    __tablename__ = "job_events"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("background_jobs.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64))
    message: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[BackgroundJob] = relationship(back_populates="events")


class AuditEvent(Base, UUIDPrimaryKey):
    __tablename__ = "audit_events"

    actor: Mapped[str] = mapped_column(String(64), default="local")
    action: Mapped[str] = mapped_column(String(128), index=True)
    target: Mapped[str | None] = mapped_column(String(512))
    outcome: Mapped[str] = mapped_column(String(32), default="success")
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Diagnostic(Base, UUIDPrimaryKey):
    __tablename__ = "diagnostics"

    name: Mapped[str] = mapped_column(String(128), index=True)
    value: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(32))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


__all__ = [
    "AppSetting",
    "ModelRecord",
    "Conversation",
    "Message",
    "MemoryItem",
    "MemorySource",
    "FlashIndex",
    "HotCacheMetadata",
    "ToolRun",
    "BrowserSession",
    "ApiKey",
    "BackgroundJob",
    "JobEvent",
    "AuditEvent",
    "Diagnostic",
    "EMBEDDING_DIM",
]
