import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.infrastructure.db_url import is_postgres_url, normalize_database_url

# Load backend/.env before DATABASE_URL is read (matches main.py; works when importing database alone).
# Packaged sidecar: skip installer .env; honor ZECT_USER_DATA sqlite path.
# database.py lives at backend/app/infrastructure/ — parents[2] is backend/.
_backend_root = Path(__file__).resolve().parents[2]
_packaged = (os.getenv("ZECT_PACKAGED") or "").strip().lower() in ("1", "true", "yes")
_user_data = (os.getenv("ZECT_USER_DATA") or "").strip()
if _packaged and _user_data:
    user_env = Path(_user_data) / "config" / ".env"
    if user_env.is_file():
        load_dotenv(user_env, override=False)
elif not _packaged:
    load_dotenv(_backend_root / ".env")

# Two supported modes (intentional, not a defect):
# - desktop_sqlite: packaged Electron / zero-config local. Default under
#   ZECT_USER_DATA/data/zect.db. Schema via create_all + additive columns.
# - server_postgres: DATABASE_URL=postgresql://... Canonical Alembic lifecycle.
#   Connection failure must not silently fall back to SQLite.
if _user_data:
    data_dir = Path(_user_data) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    _default_db = f"sqlite:///{(data_dir / 'zect.db').as_posix()}"
else:
    _default_db = "sqlite:///./zect.db"


def database_mode(url: str | None = None) -> str:
    """desktop_sqlite | server_postgres — never infer a third silent hybrid."""
    raw = DATABASE_URL if url is None else url
    return "server_postgres" if is_postgres_url(raw) else "desktop_sqlite"


def _enable_sqlite_pragmas(eng) -> None:
    """WAL so desktop sqlite can have concurrent readers. SQLite FK pragma stays
    default OFF — historical desktop databases and tests insert orphan FKs;
    Postgres enforces FKs natively.
    """

    @event.listens_for(eng, "connect")
    def _sqlite_connect(dbapi_conn, _connection_record) -> None:  # noqa: ARG001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def connect_engine(url: str):
    """Create and ping an engine. Postgres URLs fail closed (no SQLite fallback)."""
    normalized = normalize_database_url(url)
    connect_args = {"check_same_thread": False} if normalized.startswith("sqlite") else {}
    eng = None
    try:
        eng = create_engine(normalized, connect_args=connect_args, pool_pre_ping=True)
        if normalized.startswith("sqlite"):
            _enable_sqlite_pragmas(eng)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        if eng is not None:
            eng.dispose()
        safe = normalized.split("@")[-1] if "@" in normalized else normalized
        print(f"[ZECT DB] Could not connect to {safe}: {exc}")
        if is_postgres_url(normalized):
            raise RuntimeError(
                "PostgreSQL DATABASE_URL is set but the database is not usable "
                "(driver missing or server unreachable). "
                "Server/production mode does not fall back to SQLite."
            ) from exc
        raise
    safe = normalized.split("@")[-1] if "@" in normalized else normalized
    print(f"[ZECT DB] Connected to: {safe}")
    return eng, normalized


DATABASE_URL = os.getenv("DATABASE_URL", _default_db)
engine, DATABASE_URL = connect_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_missing_columns(bind=None):
    """Add any columns that exist in models but are missing from the database.

    SQLAlchemy's create_all only creates new tables — it never alters existing
    ones.  This helper inspects every mapped table and issues ALTER TABLE for
    any columns the database is missing so desktop SQLite upgrades stay
    seamless without requiring Alembic on first packaged run.
    """
    bind = bind or engine
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # create_all will handle brand-new tables
        db_columns = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in db_columns:
                continue
            # Build a portable column type string
            col_type = col.type.compile(bind.dialect)
            nullable = "NULL" if col.nullable else "NOT NULL"
            default = ""
            if col.default is not None and col.default.is_scalar:
                val = col.default.arg
                default = f" DEFAULT '{val}'" if isinstance(val, str) else f" DEFAULT {val}"
            ddl = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type} {nullable}{default}"
            try:
                with bind.begin() as conn:
                    conn.execute(text(ddl))
                print(f"[ZECT DB] Added column {table.name}.{col.name}")
            except Exception as exc:
                # Column may already exist (race condition) or type mismatch — log and continue
                print(f"[ZECT DB] Could not add {table.name}.{col.name}: {exc}")


def _migrate_cloned_voices(bind=None):
    """Chatterbox multi-voice: drop per-user UNIQUE, backfill new columns."""
    bind = bind or engine
    inspector = inspect(bind)
    if "cloned_voices" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("cloned_voices")}
    try:
        with bind.begin() as conn:
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
                if bind.dialect.name == "sqlite":
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
        if bind.dialect.name == "sqlite":
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
                with bind.begin() as conn:
                    conn.execute(text("ALTER TABLE cloned_voices RENAME TO cloned_voices_old"))
                # Recreate from current model metadata
                from app.models import ClonedVoice  # noqa: F401

                ClonedVoice.__table__.create(bind=bind)
                with bind.begin() as conn:
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


def _alembic_backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def apply_alembic(
    url: str,
    revision: str = "heads",
    *,
    required: bool,
    direction: str = "upgrade",
) -> str:
    """Run Alembic against ``url``. server_postgres must set required=True."""
    try:
        from alembic.config import Config
        from alembic import command
    except ImportError:
        if required:
            raise RuntimeError(
                "Alembic is required for server_postgres. Install alembic>=1.13 "
                "(packaged requirements.txt and Poetry both list it)."
            ) from None
        print("[ZECT DB] Alembic not installed; desktop_sqlite uses create_all + additive columns")
        return "alembic_unavailable"

    backend_root = _alembic_backend_root()
    ini = backend_root / "alembic.ini"
    if not ini.is_file():
        if required:
            raise RuntimeError(f"alembic.ini missing at {ini}")
        return "alembic_ini_missing"

    cfg = Config(str(ini))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    prev = os.getcwd()
    os.chdir(str(backend_root))
    try:
        if direction == "downgrade":
            command.downgrade(cfg, revision)
        else:
            command.upgrade(cfg, revision)
    except Exception:
        if required:
            raise
        print("[ZECT DB] Desktop Alembic optional skip (create_all remains canonical)")
        return "alembic_failed"
    finally:
        os.chdir(prev)
    return "alembic_ok"


def backup_sqlite_database(dest: Path, bind=None, source_url: str | None = None) -> Path:
    """File-copy backup for desktop_sqlite after WAL checkpoint. Not for Postgres."""
    url = source_url if source_url is not None else DATABASE_URL
    if is_postgres_url(url):
        raise RuntimeError("server_postgres backup uses pg_dump, not sqlite file copy")
    bind = bind or engine
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with bind.connect() as conn:
        conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
        conn.commit()
    parsed = make_url(url)
    db_path = parsed.database
    if not db_path or db_path == ":memory:":
        raise RuntimeError("sqlite backup requires a filesystem database")
    shutil.copy2(db_path, dest)
    return dest


def init_db(bind=None, *, url: str | None = None) -> None:
    """Apply the schema lifecycle for the active deployment mode.

    desktop_sqlite: create_all + additive columns (supported packaged/local store).
    server_postgres: alembic upgrade heads only — never create_all, never SQLite fallback.
    """
    bind = bind or engine
    url = DATABASE_URL if url is None else url
    mode = database_mode(url)
    import app.models  # noqa: F401

    try:
        if mode == "server_postgres":
            apply_alembic(url, "heads", required=True)
            inspector = inspect(bind)
            if "users" not in inspector.get_table_names():
                raise RuntimeError(
                    "PostgreSQL Alembic upgrade completed but users table is missing."
                )
            print("[ZECT DB] server_postgres schema via Alembic upgrade heads")
            return

        Base.metadata.create_all(bind=bind)
        _add_missing_columns(bind)
        _migrate_cloned_voices(bind)
        # Alembic is the server_postgres boot path. Do not run it against the
        # live desktop sqlite file: the process engine pool plus a second
        # Alembic connection deadlocks SQLite (packaged sidecar would hang).
        print("[ZECT DB] desktop_sqlite tables created/verified (create_all + additive)")
    except Exception as exc:
        print(f"[ZECT DB] Error during init_db: {exc}")
        if mode == "server_postgres":
            raise
        print(
            "[ZECT DB] The app will start but some features may not work until the database is fixed."
        )
