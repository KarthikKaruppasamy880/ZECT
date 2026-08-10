"""Alembic — mentrix_long_running_runs durable engineering runtime.

Revision ID: d8b02c3e5a21
Revises: c7a91e2b4f10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8b02c3e5a21"
down_revision: Union[str, Sequence[str], None] = "c7a91e2b4f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "mentrix_long_running_runs" in set(insp.get_table_names()):
        return
    op.create_table(
        "mentrix_long_running_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("work_items.id"), nullable=False),
        sa.Column("loop_run_id", sa.Integer(), sa.ForeignKey("mentrix_loop_runs.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("repository_id", sa.Integer(), nullable=True),
        sa.Column("worktree_path", sa.String(), nullable=True),
        sa.Column("base_commit_sha", sa.String(), nullable=True),
        sa.Column("current_commit_sha", sa.String(), nullable=True),
        sa.Column("current_operation_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("worker_id", sa.String(), nullable=True),
        sa.Column("lease_acquired_at", sa.DateTime(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("state_json", sa.Text(), nullable=True),
        sa.Column("budget_json", sa.Text(), nullable=True),
        sa.Column("telemetry_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_mentrix_long_running_runs_run_id", "mentrix_long_running_runs", ["run_id"], unique=True)
    op.create_index("ix_mentrix_long_running_runs_work_item_id", "mentrix_long_running_runs", ["work_item_id"])
    op.create_index("ix_mentrix_long_running_runs_status", "mentrix_long_running_runs", ["status"])


def downgrade() -> None:
    op.drop_table("mentrix_long_running_runs")
