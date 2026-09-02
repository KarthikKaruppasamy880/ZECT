"""Add DocumentArtifact.work_item_id and DocumentArtifact.kind -- an
attachment made in ASK is now a durable row keyed to the WorkItem, so PLAN
and AGENT can see and reuse it without asking the user to re-upload (see
ZECT_DEVELOPER_V4_1_LIVE_AGENT_ACTIVITY_SKILLS_CONTEXT_ADDENDUM.md /
UX-continuity acceptance tranche, item 2). `kind` distinguishes a parsed
document from a raw image (no parsing/chunking, used as vision content).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "document_artifacts" not in set(insp.get_table_names()):
        return
    cols = {c["name"] for c in insp.get_columns("document_artifacts")}
    if "kind" not in cols:
        op.add_column(
            "document_artifacts",
            sa.Column("kind", sa.String(), server_default="document", nullable=True),
        )
        op.create_index("ix_document_artifacts_kind", "document_artifacts", ["kind"], unique=False)
    if "work_item_id" not in cols:
        op.add_column(
            "document_artifacts",
            sa.Column("work_item_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            "ix_document_artifacts_work_item_id", "document_artifacts", ["work_item_id"], unique=False
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "document_artifacts" not in set(insp.get_table_names()):
        return
    cols = {c["name"] for c in insp.get_columns("document_artifacts")}
    if "work_item_id" in cols:
        op.drop_index("ix_document_artifacts_work_item_id", table_name="document_artifacts")
        op.drop_column("document_artifacts", "work_item_id")
    if "kind" in cols:
        op.drop_index("ix_document_artifacts_kind", table_name="document_artifacts")
        op.drop_column("document_artifacts", "kind")
