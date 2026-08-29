"""Add WorkItem.coding_mission_id -- canonical pointer to the coding_engine.lifecycle
Mission created for this WorkItem (see
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase B). String, not a
real FK: the Mission store is JSON-file-backed, not a SQL table.

Revision ID: a1b2c3d4e5f6
Revises: f1a6c7d8e9b0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f1a6c7d8e9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "work_items" not in set(insp.get_table_names()):
        return
    cols = {c["name"] for c in insp.get_columns("work_items")}
    if "coding_mission_id" not in cols:
        op.add_column(
            "work_items",
            sa.Column("coding_mission_id", sa.String(), server_default="", nullable=True),
        )
        op.create_index(
            "ix_work_items_coding_mission_id", "work_items", ["coding_mission_id"], unique=False
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "work_items" not in set(insp.get_table_names()):
        return
    cols = {c["name"] for c in insp.get_columns("work_items")}
    if "coding_mission_id" in cols:
        op.drop_index("ix_work_items_coding_mission_id", table_name="work_items")
        op.drop_column("work_items", "coding_mission_id")
