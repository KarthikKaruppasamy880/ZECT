"""Alembic environment configuration for ZECT."""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, inspect as sa_inspect, pool
from alembic import context

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Caller-set sqlalchemy.url (apply_alembic / tests) wins over the ini placeholder.
# Do not stomp a real URL with the postgres default.
_configured = (config.get_main_option("sqlalchemy.url") or "").strip()
_placeholder = (
    not _configured
    or _configured.startswith("driver://")
    or "user:pass@localhost/dbname" in _configured
)
if _placeholder:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/zect_db",
    )
else:
    database_url = _configured
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Import all models so Alembic can detect them for autogenerate
from app.models import Base  # noqa: E402

target_metadata = Base.metadata


def _bootstrap_orm_tables_if_missing(connection) -> None:
    """Honest catch-up: revision bfe9cfe5fde9 is empty (pass).

    Incremental revisions FK to users/projects. Fresh `upgrade heads` would
    fail on PostgreSQL before later catch-up revisions run. If `users` is
    missing, create ORM tables from metadata, then let the linear chain apply.
    Existing databases with users are left untouched here.
    """
    insp = sa_inspect(connection)
    if "users" in insp.get_table_names():
        return
    target_metadata.create_all(bind=connection)
    connection.commit()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _bootstrap_orm_tables_if_missing(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
