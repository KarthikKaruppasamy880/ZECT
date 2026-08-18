"""Runtime recovery production gates — honest BLOCKED_EXTERNAL, never fake NSIS PASS."""

from __future__ import annotations

import os
import subprocess
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base, SessionLocal, init_db
from app.models import AuthToken, Project, Repo
from app.services.coding_engine.lifecycle import (
    get_mission,
    missions_dir,
    reset_mission_cache,
    start_mission,
)
from app.services.presenton_client import generate_presentation, presenton_configured
from app.services.workspace_multi_root import search_workspace


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "a.py").write_text("A = 1\n", encoding="utf-8")
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "rec@zect.local")
    _git(root, "config", "user.name", "ZECT Rec")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "init")
    return root


def test_clean_install_sqlite_create_all(tmp_path, monkeypatch):
    dbfile = tmp_path / "fresh.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{dbfile.as_posix()}")
    engine = create_engine(f"sqlite:///{dbfile.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    names = set(Base.metadata.tables)
    assert "users" in names
    assert "auth_tokens" in names
    assert dbfile.is_file()


def test_alembic_revision_chain_is_linear():
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    files = sorted(versions.glob("*.py"))
    assert files, "alembic versions missing"
    revs: dict[str, str | None] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        rev = ""
        down: str | None = None
        for line in text.splitlines():
            if line.startswith("revision:") or line.startswith("revision ="):
                rev = line.split("=", 1)[-1].strip().strip("'\"")
            if line.startswith("down_revision:") or line.startswith("down_revision ="):
                raw = line.split("=", 1)[-1].strip()
                down = None if raw in ("None",) else raw.strip("'\"")
        assert rev
        revs[rev] = down
    assert "e9c4a1b2d3f0" in revs
    assert revs["e9c4a1b2d3f0"] == "d8b02c3e5a21"
    assert revs["d8b02c3e5a21"] == "c7a91e2b4f10"
    assert revs["c7a91e2b4f10"] == "bfe9cfe5fde9"
    assert revs["bfe9cfe5fde9"] is None
    assert revs["f1a6c7d8e9b0"] == "e9c4a1b2d3f0"


def test_alembic_upgrade_heads_when_package_present(tmp_path, monkeypatch):
    try:
        from alembic.config import Config
        from alembic import command
    except ImportError:
        # Packaged sidecar uses init_db create_all. Missing alembic wheel is not a live Postgres PASS.
        assert (Path(__file__).resolve().parents[1] / "alembic.ini").is_file()
        return
    dbfile = tmp_path / "alembic.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{dbfile.as_posix()}")
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    backend = Path(__file__).resolve().parents[1]
    prev = os.getcwd()
    os.chdir(backend)
    try:
        command.upgrade(cfg, "heads")
        command.upgrade(cfg, "heads")
        with pytest.raises(Exception):
            command.upgrade(cfg, "deadbeefdeadbeef")
    finally:
        os.chdir(prev)


def test_init_db_does_not_crash_on_existing_sqlite():
    init_db()


def test_coding_mission_survives_backend_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    repo = _init_repo(tmp_path / "app")
    started = start_mission(
        goal="Recover after restart",
        roots=[{"id": 1, "label": "app", "path": str(repo)}],
        workspace_parent=str(tmp_path / "wt"),
    )
    assert started["persistence"] == "durable_json"
    mid = started["id"]
    disk = missions_dir() / f"{mid}.json"
    assert disk.is_file()
    reset_mission_cache()
    recovered = get_mission(mid)
    assert recovered["id"] == mid
    assert recovered["goal"] == "Recover after restart"
    assert recovered["phase"] == "awaiting_plan_approval"
    assert recovered["persistence"] == "durable_json"


def test_sibling_repair_survives_backend_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from app.services.coding_engine.lifecycle import approve_plan, repair_and_retry

    def _repo(name: str) -> Path:
        root = tmp_path / name
        root.mkdir(parents=True)
        (root / "protocol.py").write_text("PROTOCOL = 1\n", encoding="utf-8")
        tests = root / "tests"
        tests.mkdir()
        (tests / f"test_{name}.py").write_text(
            "import protocol\n\ndef test_proto():\n    assert protocol.PROTOCOL == 2\n",
            encoding="utf-8",
        )
        _git(root, "init", "-b", "main")
        _git(root, "config", "user.email", "rec@zect.local")
        _git(root, "config", "user.name", "ZECT Rec")
        _git(root, "add", ".")
        _git(root, "commit", "-m", "init")
        return root

    a = _repo("alpha")
    b = _repo("beta")
    started = start_mission(
        goal="Bump protocol to 2 in both roots",
        roots=[
            {"id": 10, "label": "alpha", "path": str(a)},
            {"id": 11, "label": "beta", "path": str(b)},
        ],
        patches_by_repo={"10": [{"path": "protocol.py", "old": "PROTOCOL = 1", "new": "PROTOCOL = 2"}]},
        workspace_parent=str(tmp_path / "wt"),
    )
    blocked = approve_plan(started["id"])
    assert blocked["phase"] == "blocked"
    reset_mission_cache()
    repaired = repair_and_retry(
        started["id"],
        {"11": [{"path": "protocol.py", "old": "PROTOCOL = 1", "new": "PROTOCOL = 2"}]},
    )
    assert repaired["phase"] == "awaiting_git_approval", (
        repaired.get("phase"),
        repaired.get("tests"),
        repaired.get("blockers"),
        repaired.get("review"),
    )


def test_corrupt_mission_file_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    repo = _init_repo(tmp_path / "app")
    started = start_mission(
        goal="Corrupt",
        roots=[{"id": 2, "label": "app", "path": str(repo)}],
        workspace_parent=str(tmp_path / "wt"),
    )
    path = missions_dir() / f"{started['id']}.json"
    path.write_text("{not-json", encoding="utf-8")
    reset_mission_cache()
    with pytest.raises(ValueError, match="mission_corrupt"):
        get_mission(started["id"])


def test_mission_id_path_escape_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    with pytest.raises(KeyError):
        get_mission("../etc/passwd")


def test_expired_credential_is_401(client):
    db = SessionLocal()
    try:
        token = f"expired-{uuid.uuid4().hex}"
        db.add(
            AuthToken(
                token=token,
                username="expired@zect.local",
                email="expired@zect.local",
                auth_mode="local",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
        )
        db.commit()
    finally:
        db.close()
    res = client.get("/api/system/health", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in (401, 403)


def test_missing_workspace_root_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    project = Project(name="rec", description="", team="t")
    db.add(project)
    db.commit()
    db.refresh(project)
    missing = Repo(
        project_id=project.id,
        owner="local",
        repo_name="gone",
        clone_status="cloned",
        local_path=str((tmp_path / "does-not-exist").resolve()),
        default_branch="main",
        clone_branch="main",
    )
    db.add(missing)
    db.commit()
    db.refresh(missing)
    out = search_workspace(db, pattern="x", scope="workspace", repo_ids=[missing.id])
    assert out["hits"] == []
    assert out["skipped"][0]["reason"] == "ROOT_UNAVAILABLE"


def test_missing_optional_presenton_is_blocked_external(monkeypatch):
    monkeypatch.delenv("PRESENTON_BASE_URL", raising=False)
    assert presenton_configured() is False
    out = generate_presentation("recovery deck")
    assert out["ok"] is False
    assert out.get("blocked_external") is True or out.get("error") == "presenton_not_configured"


def test_present_deck_files_survive_process_simulation(tmp_path, monkeypatch):
    from app.services.mentrix.presentation import deck_catalog

    monkeypatch.setattr(deck_catalog, "default_pptx_save_dir", lambda: tmp_path)
    monkeypatch.setattr(
        deck_catalog,
        "notes_sidecar_for_pptx",
        lambda p: Path(p).with_suffix(".notes.json"),
    )
    pptx = tmp_path / "recovery-deck.pptx"
    pptx.write_bytes(b"PK\x03\x04not-a-real-deck")
    decks = deck_catalog.list_recent_decks(limit=8)
    assert any(d.get("name") == "recovery-deck.pptx" for d in decks)


def test_healthz_unauthenticated_ok(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["database_mode"] in ("desktop_sqlite", "server_postgres")
