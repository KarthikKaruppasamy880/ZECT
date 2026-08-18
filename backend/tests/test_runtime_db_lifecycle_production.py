"""Production database lifecycle — two supported modes, never silent SQLite fallback.

desktop_sqlite is the intentional packaged/local store (create_all + additive columns).
server_postgres must use Alembic and fail closed. Live Postgres is BLOCKED_EXTERNAL
unless ZECT_TEST_POSTGRES_URL is set — skip ≠ PASS.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import (
    Base,
    apply_alembic,
    backup_sqlite_database,
    connect_engine,
    database_mode,
    init_db,
    is_postgres_url,
    normalize_database_url,
)

LIVE_PG = (os.getenv("ZECT_TEST_POSTGRES_URL") or "").strip()


def test_modes_are_explicit():
    assert database_mode("sqlite:///./zect.db") == "desktop_sqlite"
    assert database_mode("sqlite:///C:/Users/x/zect.db") == "desktop_sqlite"
    assert database_mode("postgresql://u:p@localhost:5432/zect_db") == "server_postgres"
    assert database_mode("postgresql+psycopg://u:p@localhost:5432/zect_db") == "server_postgres"
    assert is_postgres_url("postgres://u:p@h/db") is True
    assert is_postgres_url("sqlite:///x") is False
    assert normalize_database_url("postgresql://u:p@h/db").startswith("postgresql+psycopg://")


def test_postgres_unreachable_does_not_fallback_sqlite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="does not fall back to SQLite"):
        connect_engine("postgresql+psycopg://zect:zect@127.0.0.1:1/zect_missing")
    assert not (tmp_path / "zect.db").exists()
    assert not list(tmp_path.glob("*.db"))


def test_desktop_sqlite_schema_create_persist_restart(tmp_path):
    dbfile = tmp_path / "desktop.db"
    url = f"sqlite:///{dbfile.as_posix()}"
    eng, normalized = connect_engine(url)
    assert normalized == url
    init_db(bind=eng, url=url)
    names = set(inspect(eng).get_table_names())
    assert "users" in names
    assert "auth_tokens" in names
    Session = sessionmaker(bind=eng)
    db = Session()
    try:
        from app.models import User

        db.add(User(email="persist@zect.local", name="Persist"))
        db.commit()
    finally:
        db.close()
    eng.dispose()
    eng2, _ = connect_engine(url)
    init_db(bind=eng2, url=url)
    db2 = sessionmaker(bind=eng2)()
    try:
        from app.models import User

        row = db2.query(User).filter(User.email == "persist@zect.local").one()
        assert row.name == "Persist"
    finally:
        db2.close()
        eng2.dispose()


def test_desktop_init_db_does_not_run_alembic_on_live_file(tmp_path):
    """Boot must not open a second Alembic connection to the live sqlite file."""
    dbfile = tmp_path / "boot.db"
    url = f"sqlite:///{dbfile.as_posix()}"
    eng, _ = connect_engine(url)
    init_db(bind=eng, url=url)
    names = set(inspect(eng).get_table_names())
    assert "users" in names
    assert "alembic_version" not in names
    eng.dispose()


def test_desktop_sqlite_additive_upgrade_from_older_schema(tmp_path):
    dbfile = tmp_path / "old.db"
    url = f"sqlite:///{dbfile.as_posix()}"
    eng = create_engine(url, connect_args={"check_same_thread": False})
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL)"))
    init_db(bind=eng, url=url)
    cols = {c["name"] for c in inspect(eng).get_columns("users")}
    assert "name" in cols
    assert "role" in cols
    eng.dispose()


def test_alembic_revision_chain_includes_catchup():
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    revs: dict[str, str | None] = {}
    for path in sorted(versions.glob("*.py")):
        text_blob = path.read_text(encoding="utf-8")
        rev = ""
        down: str | None = None
        for line in text_blob.splitlines():
            if line.startswith("revision:") or line.startswith("revision ="):
                rev = line.split("=", 1)[-1].strip().strip("'\"")
            if line.startswith("down_revision:") or line.startswith("down_revision ="):
                raw = line.split("=", 1)[-1].strip()
                down = None if raw in ("None",) else raw.strip("'\"")
        assert rev
        revs[rev] = down
    assert revs["bfe9cfe5fde9"] is None
    assert revs["c7a91e2b4f10"] == "bfe9cfe5fde9"
    assert revs["d8b02c3e5a21"] == "c7a91e2b4f10"
    assert revs["e9c4a1b2d3f0"] == "d8b02c3e5a21"
    assert revs["f1a6c7d8e9b0"] == "e9c4a1b2d3f0"


def test_alembic_upgrade_heads_twice_unknown_revision_and_rollback(tmp_path, monkeypatch):
    dbfile = tmp_path / "alembic-lifecycle.db"
    url = f"sqlite:///{dbfile.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    assert apply_alembic(url, "heads", required=True) == "alembic_ok"
    assert apply_alembic(url, "heads", required=True) == "alembic_ok"
    eng, _ = connect_engine(url)
    assert "users" in inspect(eng).get_table_names()
    Session = sessionmaker(bind=eng)
    db = Session()
    try:
        from app.models import User

        db.add(User(email="mig@zect.local", name="Mig"))
        db.commit()
    finally:
        db.close()
    with pytest.raises(Exception):
        apply_alembic(url, "deadbeefdeadbeef", required=True)
    assert apply_alembic(url, "-1", required=True, direction="downgrade") == "alembic_ok"
    assert apply_alembic(url, "heads", required=True) == "alembic_ok"
    db2 = sessionmaker(bind=eng)()
    try:
        from app.models import User

        assert db2.query(User).filter(User.email == "mig@zect.local").one().name == "Mig"
    finally:
        db2.close()
        eng.dispose()


def test_sqlite_backup_and_wal_concurrent_access(tmp_path):
    dbfile = tmp_path / "wal.db"
    url = f"sqlite:///{dbfile.as_posix()}"
    eng, _ = connect_engine(url)
    init_db(bind=eng, url=url)
    Session = sessionmaker(bind=eng)
    db = Session()
    try:
        from app.models import User

        db.add(User(email="wal@zect.local", name="Wal"))
        db.commit()
    finally:
        db.close()
    dest = tmp_path / "backup.db"
    backup_sqlite_database(dest, bind=eng, source_url=url)
    assert dest.is_file() and dest.stat().st_size > 0
    eng_b = create_engine(f"sqlite:///{dest.as_posix()}", connect_args={"check_same_thread": False})
    names = inspect(eng_b).get_table_names()
    assert "users" in names
    eng_b.dispose()

    eng2, _ = connect_engine(url)
    db_w = sessionmaker(bind=eng)()
    db_r = sessionmaker(bind=eng2)()
    try:
        from app.models import User

        db_w.add(User(email="wal2@zect.local", name="Wal2"))
        db_w.commit()
        assert db_r.query(User).filter(User.email == "wal2@zect.local").one().name == "Wal2"
    finally:
        db_w.close()
        db_r.close()
        eng.dispose()
        eng2.dispose()


def test_postgres_backup_helper_refuses_file_copy():
    with pytest.raises(RuntimeError, match="pg_dump"):
        backup_sqlite_database(
            Path("nope.db"),
            source_url="postgresql+psycopg://u:p@localhost:5432/zect_db",
        )


def test_server_postgres_init_db_uses_alembic_not_create_all(monkeypatch):
    from app.infrastructure import database as dbmod

    calls: list[str] = []
    monkeypatch.setattr(dbmod, "apply_alembic", lambda *a, **k: calls.append("alembic") or "alembic_ok")
    monkeypatch.setattr(dbmod.Base.metadata, "create_all", lambda **kw: calls.append("create_all"))
    insp = MagicMock()
    insp.get_table_names.return_value = ["users"]
    monkeypatch.setattr(dbmod, "inspect", lambda _bind: insp)
    dbmod.init_db(bind=MagicMock(), url="postgresql+psycopg://u:p@localhost:5432/zect_db")
    assert calls == ["alembic"]


def test_server_postgres_init_db_missing_users_fails_closed(monkeypatch):
    from app.infrastructure import database as dbmod

    monkeypatch.setattr(dbmod, "apply_alembic", lambda *a, **k: "alembic_ok")
    insp = MagicMock()
    insp.get_table_names.return_value = []
    monkeypatch.setattr(dbmod, "inspect", lambda _bind: insp)
    with pytest.raises(RuntimeError, match="users table is missing"):
        dbmod.init_db(bind=MagicMock(), url="postgresql://u:p@localhost:5432/zect_db")


def test_server_postgres_init_db_alembic_failure_reraises(monkeypatch):
    from app.infrastructure import database as dbmod

    def _boom(*_a, **_k):
        raise RuntimeError("Alembic is required for server_postgres")

    monkeypatch.setattr(dbmod, "apply_alembic", _boom)
    with pytest.raises(RuntimeError, match="Alembic is required"):
        dbmod.init_db(bind=MagicMock(), url="postgresql+psycopg://u:p@localhost:5432/zect_db")


def test_desktop_init_db_start_anyway_on_schema_error(tmp_path, monkeypatch):
    from app.infrastructure import database as dbmod

    dbfile = tmp_path / "soft.db"
    url = f"sqlite:///{dbfile.as_posix()}"
    eng, _ = connect_engine(url)
    monkeypatch.setattr(dbmod.Base.metadata, "create_all", lambda **kw: (_ for _ in ()).throw(RuntimeError("disk full")))
    dbmod.init_db(bind=eng, url=url)
    eng.dispose()


def test_healthz_exposes_database_mode_not_url(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["database_mode"] == "desktop_sqlite"
    assert body["database_dialect"] == "sqlite"
    assert body["database_lifecycle"] == "create_all_additive"
    blob = res.text.lower()
    assert "postgresql://" not in blob
    assert "password" not in blob


def test_packaged_sidecar_defaults_sqlite():
    entry = (
        Path(__file__).resolve().parents[2]
        / "electron"
        / "resources"
        / "backend"
        / "zect_api_entry.py"
    )
    text_blob = entry.read_text(encoding="utf-8")
    assert "sqlite:///" in text_blob
    assert "ZECT_USER_DATA" in text_blob
    assert "setdefault" in text_blob and "DATABASE_URL" in text_blob


@pytest.mark.skipif(not LIVE_PG, reason="BLOCKED_EXTERNAL: ZECT_TEST_POSTGRES_URL unset")
def test_live_postgres_alembic_upgrade_heads_persist_restart():
    eng, url = connect_engine(LIVE_PG)
    assert database_mode(url) == "server_postgres"
    init_db(bind=eng, url=url)
    names = set(inspect(eng).get_table_names())
    assert "users" in names
    assert "alembic_version" in names
    Session = sessionmaker(bind=eng)
    db = Session()
    try:
        from app.models import User

        email = "live-pg-lifecycle@zect.local"
        existing = db.query(User).filter(User.email == email).first()
        if existing is None:
            db.add(User(email=email, name="LivePg"))
            db.commit()
    finally:
        db.close()
    eng.dispose()
    eng2, _ = connect_engine(LIVE_PG)
    init_db(bind=eng2, url=LIVE_PG)
    db2 = sessionmaker(bind=eng2)()
    try:
        from app.models import User

        assert db2.query(User).filter(User.email == "live-pg-lifecycle@zect.local").one().name == "LivePg"
    finally:
        db2.close()
        eng2.dispose()
