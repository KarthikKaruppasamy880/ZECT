"""Alembic revision — companion learning tables + automation loops + personal_actions columns.

Revision ID: c7a91e2b4f10
Revises: bfe9cfe5fde9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7a91e2b4f10"
down_revision: Union[str, Sequence[str], None] = "bfe9cfe5fde9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = set(insp.get_table_names())

    if "personal_actions" in tables:
        cols = {c["name"] for c in insp.get_columns("personal_actions")}
        if "connector_id" not in cols:
            op.add_column("personal_actions", sa.Column("connector_id", sa.String(), server_default="", nullable=True))
        if "description" not in cols:
            op.add_column("personal_actions", sa.Column("description", sa.Text(), server_default="", nullable=True))

    if "learning_sources" not in tables:
        op.create_table(
            "learning_sources",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_type", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("repository_url", sa.String(), nullable=True),
            sa.Column("license", sa.String(), nullable=True),
            sa.Column("attribution", sa.Text(), nullable=True),
            sa.Column("refresh_policy", sa.String(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "learning_resources" not in tables:
        op.create_table(
            "learning_resources",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("learning_source_id", sa.Integer(), sa.ForeignKey("learning_sources.id"), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("source_url", sa.String(), nullable=True),
            sa.Column("language", sa.String(), nullable=True),
            sa.Column("technologies_json", sa.Text(), nullable=True),
            sa.Column("project_type", sa.String(), nullable=True),
            sa.Column("difficulty", sa.String(), nullable=True),
            sa.Column("prerequisites_json", sa.Text(), nullable=True),
            sa.Column("skills_json", sa.Text(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("attribution", sa.Text(), nullable=True),
            sa.Column("content_policy", sa.String(), nullable=True),
            sa.Column("external_license_status", sa.String(), nullable=True),
            sa.Column("indexed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("learning_source_id", "source_url", name="uq_learning_resource_source_url"),
        )
    if "learning_projects" not in tables:
        op.create_table(
            "learning_projects",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("resource_id", sa.Integer(), sa.ForeignKey("learning_resources.id"), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("mode", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("goals_json", sa.Text(), nullable=True),
            sa.Column("milestones_json", sa.Text(), nullable=True),
            sa.Column("skills_json", sa.Text(), nullable=True),
            sa.Column("repository_id", sa.Integer(), nullable=True),
            sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("work_items.id"), nullable=True),
            sa.Column("progress_json", sa.Text(), nullable=True),
            sa.Column("evidence_json", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
    if "mentrix_loop_definitions" not in tables:
        op.create_table(
            "mentrix_loop_definitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("org_id", sa.String(), nullable=True),
            sa.Column("autonomy_level", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("target", sa.String(), nullable=True),
            sa.Column("budget_json", sa.Text(), nullable=True),
            sa.Column("policy_json", sa.Text(), nullable=True),
            sa.Column("trigger_json", sa.Text(), nullable=True),
            sa.Column("checkpoint_json", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "mentrix_loop_runs" not in tables:
        op.create_table(
            "mentrix_loop_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("loop_definition_id", sa.Integer(), sa.ForeignKey("mentrix_loop_definitions.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("autonomy_level", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("trigger_kind", sa.String(), nullable=True),
            sa.Column("checkpoint_json", sa.Text(), nullable=True),
            sa.Column("evidence_json", sa.Text(), nullable=True),
            sa.Column("result_json", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("mentrix_loop_runs")
    op.drop_table("mentrix_loop_definitions")
    op.drop_table("learning_projects")
    op.drop_table("learning_resources")
    op.drop_table("learning_sources")
