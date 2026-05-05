import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Load backend/.env before DATABASE_URL is read (matches main.py; works when importing database alone).
_backend_root = Path(__file__).resolve().parents[1]
load_dotenv(_backend_root / ".env")

# Default to PostgreSQL; fall back to SQLite only if DATABASE_URL is not set
_default_db = "postgresql+psycopg://postgres:postgres@localhost:5432/zect_db"
DATABASE_URL = os.getenv("DATABASE_URL", _default_db)
# Ensure the psycopg (v3) driver prefix is present for PostgreSQL URLs
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_missing_columns():
    """Add any columns that exist in models but are missing from the database.

    SQLAlchemy's create_all only creates new tables — it never alters existing
    ones.  This helper inspects every mapped table and issues ALTER TABLE for
    any columns the database is missing so that schema upgrades are seamless
    without requiring Alembic on first run.
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # create_all will handle brand-new tables
        db_columns = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in db_columns:
                continue
            # Build a portable column type string
            col_type = col.type.compile(engine.dialect)
            nullable = "NULL" if col.nullable else "NOT NULL"
            default = ""
            if col.default is not None and col.default.is_scalar:
                val = col.default.arg
                default = f" DEFAULT '{val}'" if isinstance(val, str) else f" DEFAULT {val}"
            ddl = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type} {nullable}{default}"
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                print(f"[ZECT DB] Added column {table.name}.{col.name}")
            except Exception as exc:
                # Column may already exist (race condition) or type mismatch — log and continue
                print(f"[ZECT DB] Could not add {table.name}.{col.name}: {exc}")


def init_db():
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
