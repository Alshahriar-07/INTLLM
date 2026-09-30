"""Initial INTLLM schema (pgvector + core tables).

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-30
"""

from __future__ import annotations

from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401 - register models on the metadata

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # pgvector must exist before any table with a `vector` column is created.
    bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
