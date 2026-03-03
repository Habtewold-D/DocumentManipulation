"""add missing image_url columns

Revision ID: 20260304_0004
Revises: 2a8c29b41c81
Create Date: 2026-03-04 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260304_0004"
down_revision: str | None = "2a8c29b41c81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(col.get("name") == column_name for col in columns)


def upgrade() -> None:
    if not _has_column("document_versions", "image_url"):
        op.add_column("document_versions", sa.Column("image_url", sa.String(length=500), nullable=True))

    if not _has_column("command_runs", "image_url"):
        op.add_column("command_runs", sa.Column("image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    if _has_column("command_runs", "image_url"):
        op.drop_column("command_runs", "image_url")

    if _has_column("document_versions", "image_url"):
        op.drop_column("document_versions", "image_url")
