"""Catch-up: bootstrap missing ORM tables so upgrade heads can complete.

The original initial revision (bfe9cfe5fde9) is empty (pass). Incremental
revisions create a subset of tables that FK to users/projects. Databases
already stamped at e9c4a1b2d3f0 may still lack later ORM tables.

This revision idempotently runs Base.metadata.create_all. Existing tables
are left untouched. Do not edit prior revision files.

env.py also bootstraps when `users` is missing so a *fresh* Postgres
`alembic upgrade heads` can apply the linear chain without FK failures.

Revision ID: f1a6c7d8e9b0
Revises: e9c4a1b2d3f0
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f1a6c7d8e9b0"
down_revision: Union[str, Sequence[str], None] = "e9c4a1b2d3f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.models import Base
    import sqlalchemy as sa

    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = set(insp.get_table_names())
    missing = [table for table in Base.metadata.sorted_tables if table.name not in existing]
    if not missing:
        return
    # create_all inside the Alembic transaction deadlocks SQLite. Autocommit
    # is required when this revision actually creates tables.
    with op.get_context().autocommit_block():
        Base.metadata.create_all(bind=op.get_bind(), tables=missing)


def downgrade() -> None:
    # Catch-up is additive. Do not drop core tables on downgrade.
    pass
