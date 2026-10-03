"""Widen models.size_bytes to BIGINT (int32 overflow for models > 2 GiB).

Real Ollama model files routinely exceed 2,147,483,647 bytes, so an INTEGER
size_bytes crashes model synchronization with an OverflowError for almost
every modern model.

Revision ID: 0002_size_bytes_bigint
Revises: 0001_initial
Create Date: 2026-10-03
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import BigInteger, Integer

revision = "0002_size_bytes_bigint"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "models", "size_bytes", existing_type=Integer(), type_=BigInteger()
    )


def downgrade() -> None:
    # Values above the int32 range cannot round-trip; clamp instead of failing.
    op.execute("UPDATE models SET size_bytes = NULL WHERE size_bytes > 2147483647")
    op.alter_column(
        "models",
        "size_bytes",
        existing_type=BigInteger(),
        existing_nullable=True,
        type_=Integer(),
    )
