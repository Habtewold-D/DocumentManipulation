"""add idempotency key to command runs

Revision ID: 20260217_0002
Revises: 20260217_0001
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260217_0002"
down_revision = "20260217_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("command_runs", sa.Column("idempotency_key", sa.String(length=120), nullable=True))
    op.create_index("ix_command_runs_idempotency_key", "command_runs", ["idempotency_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_command_runs_idempotency_key", table_name="command_runs")
    op.drop_column("command_runs", "idempotency_key")
