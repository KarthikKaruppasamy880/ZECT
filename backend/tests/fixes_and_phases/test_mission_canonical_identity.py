"""Phase B (canonical Mission identity): WorkItem.coding_mission_id is set
when a coding_engine.lifecycle Mission is created for it, so the WorkItem
always has one authoritative pointer to "its" Mission -- see
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase B. The Mission
store itself is JSON-file-backed (not a SQL table), so this is a plain
string column, not a real foreign key.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from app.domains.work_items.service import serialize_work_item
from app.infrastructure.database import SessionLocal
from app.models import WorkItem


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "readme.txt").write_text("marker\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "zect-ca@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT CA"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    return tmp_path


@pytest.fixture()
def work_item():
    db = SessionLocal()
    try:
        wi = WorkItem(title="Phase B identity test", source="user")
        db.add(wi)
        db.commit()
        db.refresh(wi)
        wid = wi.id
    finally:
        db.close()
    yield wid
    db = SessionLocal()
    try:
        row = db.query(WorkItem).filter(WorkItem.id == wid).first()
        if row is not None:
            db.delete(row)
            db.commit()
    finally:
        db.close()


def test_create_mission_with_work_item_id_sets_the_canonical_pointer(ws, authed_client, work_item):
    repo = _init_repo(ws / "identity")
    created = authed_client.post(
        "/api/coding-agent/missions",
        json={
            "goal": "Add a helper",
            "roots": [{"id": 1, "label": "identity", "path": str(repo)}],
            "work_item_id": work_item,
        },
    )
    assert created.status_code == 200, created.text
    mission_id = created.json()["id"]

    db = SessionLocal()
    try:
        wi = db.query(WorkItem).filter(WorkItem.id == work_item).first()
        assert wi.coding_mission_id == mission_id
        assert serialize_work_item(wi)["coding_mission_id"] == mission_id
    finally:
        db.close()


def test_create_mission_without_work_item_id_touches_no_work_item(ws, authed_client):
    repo = _init_repo(ws / "no-identity")
    created = authed_client.post(
        "/api/coding-agent/missions",
        json={"goal": "Add a helper", "roots": [{"id": 1, "label": "no-identity", "path": str(repo)}]},
    )
    assert created.status_code == 200, created.text
    # No work_item_id was supplied -- nothing to assert on a WorkItem row,
    # this just proves the new code path doesn't blow up when it's absent.


def test_create_mission_with_unknown_work_item_id_does_not_error(ws, authed_client):
    repo = _init_repo(ws / "unknown-identity")
    created = authed_client.post(
        "/api/coding-agent/missions",
        json={
            "goal": "Add a helper",
            "roots": [{"id": 1, "label": "unknown-identity", "path": str(repo)}],
            "work_item_id": 999_999_999,
        },
    )
    assert created.status_code == 200, created.text
