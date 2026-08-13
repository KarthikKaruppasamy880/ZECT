import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Load backend/.env before DATABASE_URL is read (matches main.py; works when importing database alone).
# Packaged sidecar: skip installer .env; honor ZECT_USER_DATA sqlite path.
_backend_root = Path(__file__).resolve().parents[1]
_packaged = (os.getenv("ZECT_PACKAGED") or "").strip().lower() in ("1", "true", "yes")
_user_data = (os.getenv("ZECT_USER_DATA") or "").strip()
if _packaged and _user_data:
    user_env = Path(_user_data) / "config" / ".env"
    if user_env.is_file():
        load_dotenv(user_env, override=False)
elif not _packaged:
    load_dotenv(_backend_root / ".env")

# Default to SQLite for zero-config local development.
# Set DATABASE_URL in .env to use PostgreSQL in production.
if _user_data:
    data_dir = Path(_user_data) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    _default_db = f"sqlite:///{(data_dir / 'zect.db').as_posix()}"
else:
    _default_db = "sqlite:///./zect.db"
DATABASE_URL = os.getenv("DATABASE_URL", _default_db)
# Ensure the psycopg (v3) driver prefix is present for PostgreSQL URLs
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Try to connect; if PostgreSQL fails, fall back to SQLite automatically
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
    # Test the connection immediately
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print(f"[ZECT DB] Connected to: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
except Exception as exc:
    print(f"[ZECT DB] Could not connect to {DATABASE_URL}: {exc}")
    if not DATABASE_URL.startswith("sqlite"):
        print("[ZECT DB] Falling back to SQLite (zect.db)")
        DATABASE_URL = "sqlite:///./zect.db"
        connect_args = {"check_same_thread": False}
        engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
    else:
        raise
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


def _migrate_cloned_voices():
    """Chatterbox multi-voice: drop per-user UNIQUE, backfill new columns."""
    inspector = inspect(engine)
    if "cloned_voices" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("cloned_voices")}
    try:
        with engine.begin() as conn:
            if "external_voice_id" in cols:
                # Clear bad backfill: ZECT voice_id was incorrectly copied into
                # external_voice_id. Voicebox assigns its own UUID — equal ids are stale.
                conn.execute(
                    text(
                        "UPDATE cloned_voices SET external_voice_id = NULL "
                        "WHERE external_voice_id IS NOT NULL AND voice_id IS NOT NULL "
                        "AND external_voice_id = voice_id"
                    )
                )
            if "is_default" in cols:
                conn.execute(
                    text(
                        "UPDATE cloned_voices SET is_default = 1 "
                        "WHERE is_default IS NULL OR is_default = 0"
                    )
                )
                # Keep one default per user (highest id) after backfill
                if engine.dialect.name == "sqlite":
                    conn.execute(
                        text(
                            """
                            UPDATE cloned_voices SET is_default = 0
                            WHERE id NOT IN (
                              SELECT MAX(id) FROM cloned_voices GROUP BY user_id
                            )
                            """
                        )
                    )
            if "provider" in cols:
                conn.execute(
                    text(
                        "UPDATE cloned_voices SET provider = 'chatterbox' "
                        "WHERE provider IN ('voicebox', '') OR provider IS NULL"
                    )
                )
        # SQLite: rebuild table if user_id still has a unique index (blocks multi-voice)
        if engine.dialect.name == "sqlite":
            indexes = inspector.get_indexes("cloned_voices")
            unique_on_user = any(
                ix.get("unique") and ix.get("column_names") == ["user_id"] for ix in indexes
            )
            # Also check unique constraints
            try:
                uqs = inspector.get_unique_constraints("cloned_voices")
                unique_on_user = unique_on_user or any(
                    uc.get("column_names") == ["user_id"] for uc in uqs
                )
            except Exception:
                pass
            if unique_on_user:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE cloned_voices RENAME TO cloned_voices_old"))
                # Recreate from current model metadata
                from app.models import ClonedVoice  # noqa: F401

                ClonedVoice.__table__.create(bind=engine)
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            INSERT INTO cloned_voices
                              (id, user_id, provider, voice_id, external_voice_id, name,
                               sample_path, reference_text, is_default, created_at)
                            SELECT
                              id, user_id,
                              COALESCE(NULLIF(provider, ''), 'chatterbox'),
                              voice_id,
                              COALESCE(external_voice_id, voice_id),
                              COALESCE(name, ''),
                              sample_path, reference_text,
                              COALESCE(is_default, 1),
                              created_at
                            FROM cloned_voices_old
                            """
                        )
                    )
                    conn.execute(text("DROP TABLE cloned_voices_old"))
                print("[ZECT DB] Migrated cloned_voices for multi-voice Chatterbox")
    except Exception as exc:
        print(f"[ZECT DB] cloned_voices migrate skipped/failed: {exc}")


def init_db():
    try:
        # Import models so they are registered with Base.metadata before create_all
        import app.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        _add_missing_columns()
        _migrate_cloned_voices()
        print("[ZECT DB] All tables created/verified successfully")
    except Exception as exc:
        print(f"[ZECT DB] Error during init_db: {exc}")
        print("[ZECT DB] The app will start but some features may not work until the database is fixed.")
