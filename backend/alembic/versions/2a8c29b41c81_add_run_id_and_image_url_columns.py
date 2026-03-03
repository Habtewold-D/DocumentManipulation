"""add run_id and image_url columns

Revision ID: 2a8c29b41c81
Revises: 20260217_0003
Create Date: 2026-03-03 20:23:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "2a8c29b41c81"
down_revision: str | None = "20260217_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(col.get("name") == column_name for col in columns)


def upgrade() -> None:
    if not _has_column("document_versions", "run_id"):
        op.add_column("document_versions", sa.Column("run_id", sa.String(length=36), nullable=True))

    if not _has_column("document_versions", "image_url"):
        op.add_column("document_versions", sa.Column("image_url", sa.String(length=500), nullable=True))

    if not _has_column("command_runs", "image_url"):
        op.add_column("command_runs", sa.Column("image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    if _has_column("command_runs", "image_url"):
        op.drop_column("command_runs", "image_url")

    if _has_column("document_versions", "image_url"):
        op.drop_column("document_versions", "image_url")

    if _has_column("document_versions", "run_id"):
        op.drop_column("document_versions", "run_id")
