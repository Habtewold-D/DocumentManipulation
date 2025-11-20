"""initial schema

Revision ID: 20260217_0001
Revises: None
Create Date: 2026-02-17 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260217_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_asset_id", sa.String(length=255), nullable=False),
        sa.Column("current_version_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
    )
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"], unique=False)

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("pdf_asset_id", sa.String(length=255), nullable=True),
        sa.Column("preview_manifest", sa.Text(), nullable=True),
        sa.Column("operation_log", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"], unique=False)
    op.create_index("ix_document_versions_state", "document_versions", ["state"], unique=False)

    op.create_table(
        "tool_execution_logs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("input_payload", sa.Text(), nullable=True),
        sa.Column("output_payload", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["document_versions.id"]),
    )
    op.create_index("ix_tool_execution_logs_document_id", "tool_execution_logs", ["document_id"], unique=False)
    op.create_index("ix_tool_execution_logs_status", "tool_execution_logs", ["status"], unique=False)
    op.create_index("ix_tool_execution_logs_tool_name", "tool_execution_logs", ["tool_name"], unique=False)

    op.create_table(
        "command_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("command_text", sa.Text(), nullable=False),
        sa.Column("planned_tools", sa.Text(), nullable=True),
        sa.Column("draft_version_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
    )
    op.create_index("ix_command_runs_document_id", "command_runs", ["document_id"], unique=False)
    op.create_index("ix_command_runs_status", "command_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_command_runs_status", table_name="command_runs")
    op.drop_index("ix_command_runs_document_id", table_name="command_runs")
    op.drop_table("command_runs")

    op.drop_index("ix_tool_execution_logs_tool_name", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_status", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_document_id", table_name="tool_execution_logs")
    op.drop_table("tool_execution_logs")

    op.drop_index("ix_document_versions_state", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
