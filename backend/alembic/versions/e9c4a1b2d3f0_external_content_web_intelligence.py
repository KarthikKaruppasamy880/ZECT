"""Alembic — external content tables for Web Intelligence (C).

Revision ID: e9c4a1b2d3f0
Revises: d8b02c3e5a21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e9c4a1b2d3f0"
down_revision: Union[str, Sequence[str], None] = "d8b02c3e5a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = set(insp.get_table_names())

    if "external_content_versions" not in tables:
        op.create_table(
            "external_content_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("content_sha256", sa.String(length=64), nullable=False),
            sa.Column("scope", sa.String(), nullable=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("owner_user_id", sa.Integer(), nullable=True),
            sa.Column("source_url", sa.String(), nullable=True),
            sa.Column("connector_id", sa.String(), nullable=True),
            sa.Column("adapter", sa.String(), nullable=True),
            sa.Column("mime_type", sa.String(), nullable=True),
            sa.Column("title", sa.String(), nullable=True),
            sa.Column("author", sa.String(), nullable=True),
            sa.Column("markdown_path", sa.String(), nullable=True),
            sa.Column("json_path", sa.String(), nullable=True),
            sa.Column("partial_capabilities", sa.JSON(), nullable=True),
            sa.Column("fetched_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "scope",
                "project_id",
                "owner_user_id",
                "content_sha256",
                name="uq_ext_content_version_identity",
            ),
        )
        op.create_index("ix_external_content_versions_content_sha256", "external_content_versions", ["content_sha256"])
        op.create_index("ix_external_content_versions_scope", "external_content_versions", ["scope"])
        op.create_index("ix_external_content_versions_project_id", "external_content_versions", ["project_id"])
        op.create_index("ix_external_content_versions_owner_user_id", "external_content_versions", ["owner_user_id"])

    if "external_content_artifacts" not in tables:
        op.create_table(
            "external_content_artifacts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("scope", sa.String(), nullable=True),
            sa.Column("source_url", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=True),
            sa.Column("connector_id", sa.String(), nullable=True),
            sa.Column("adapter", sa.String(), nullable=True),
            sa.Column("content_sha256", sa.String(length=64), nullable=False),
            sa.Column("content_version_id", sa.Integer(), sa.ForeignKey("external_content_versions.id"), nullable=True),
            sa.Column("sensitivity", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("is_current", sa.Boolean(), nullable=True),
            sa.Column("superseded_by_id", sa.Integer(), nullable=True),
            sa.Column("knowledge_entry_id", sa.Integer(), sa.ForeignKey("knowledge_entries.id"), nullable=True),
            sa.Column("source_map_json", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("confirmed_browser", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_external_content_artifacts_user_id", "external_content_artifacts", ["user_id"])
        op.create_index("ix_external_content_artifacts_project_id", "external_content_artifacts", ["project_id"])
        op.create_index("ix_external_content_artifacts_scope", "external_content_artifacts", ["scope"])
        op.create_index("ix_external_content_artifacts_content_sha256", "external_content_artifacts", ["content_sha256"])
        op.create_index("ix_external_content_artifacts_content_version_id", "external_content_artifacts", ["content_version_id"])
        op.create_index("ix_external_content_artifacts_status", "external_content_artifacts", ["status"])
        op.create_index("ix_external_content_artifacts_is_current", "external_content_artifacts", ["is_current"])

    if "external_content_chunks" not in tables:
        op.create_table(
            "external_content_chunks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("external_artifact_id", sa.Integer(), sa.ForeignKey("external_content_artifacts.id"), nullable=False),
            sa.Column("content_version_id", sa.Integer(), sa.ForeignKey("external_content_versions.id"), nullable=False),
            sa.Column("content_sha256", sa.String(length=64), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=True),
            sa.Column("heading_path", sa.String(), nullable=True),
            sa.Column("source_offset", sa.Integer(), nullable=True),
            sa.Column("token_count", sa.Integer(), nullable=True),
            sa.Column("chunk_hash", sa.String(length=64), nullable=True),
            sa.Column("text", sa.Text(), nullable=True),
            sa.Column("sensitivity", sa.String(), nullable=True),
            sa.Column("freshness", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_external_content_chunks_external_artifact_id", "external_content_chunks", ["external_artifact_id"])
        op.create_index("ix_external_content_chunks_content_version_id", "external_content_chunks", ["content_version_id"])
        op.create_index("ix_external_content_chunks_content_sha256", "external_content_chunks", ["content_sha256"])
        op.create_index("ix_external_content_chunks_freshness", "external_content_chunks", ["freshness"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = set(insp.get_table_names())
    if "external_content_chunks" in tables:
        op.drop_table("external_content_chunks")
    if "external_content_artifacts" in tables:
        op.drop_table("external_content_artifacts")
    if "external_content_versions" in tables:
        op.drop_table("external_content_versions")
