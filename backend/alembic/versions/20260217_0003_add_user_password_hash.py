"""add user password hash

Revision ID: 20260217_0003
Revises: 20260217_0002
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260217_0003"
down_revision = "20260217_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""))
    op.alter_column("users", "password_hash", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "password_hash")
