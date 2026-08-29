from __future__ import annotations

from app.domains.project.projects import is_fixture_project_name
from app.infrastructure.database import SessionLocal
from app.models import Project, WorkItem
from app.services.fixture_isolation import (
    PROVENANCE_TEST,
    audit_projects,
    cleanup_proven_test_projects,
    is_proven_test_project,
    should_hide_project,
    tag_projects_by_ids,
)


def test_fixture_project_names_are_candidates_only():
    assert is_fixture_project_name("Policy Admin Modernization")
    assert is_fixture_project_name("Phase6 Onboard")
    assert is_fixture_project_name("r36-live-abc")
    assert is_fixture_project_name("zect-r36-mss82cce-a")
    assert not is_fixture_project_name("Customer Portal")
    assert not is_fixture_project_name("ZECT")


def test_name_is_not_a_delete_or_security_rule():
    user_named = Project(name="Phase6 Onboard", provenance="user", test_run_id="")
    assert not is_proven_test_project(user_named)
    assert should_hide_project(user_named, exclude_name_candidates=True)
    assert not should_hide_project(user_named, exclude_name_candidates=False)


def test_api_hides_proven_test_not_user_projects(authed_client):
    user = authed_client.post(
        "/api/projects",
        json={"name": "ZECT Authorized", "description": "real", "provenance": "user"},
    )
    assert user.status_code == 201, user.text
    fixture = authed_client.post(
        "/api/projects",
        json={
            "name": "Phase6 Pollution",
            "description": "test",
            "provenance": "test",
            "test_run_id": "hygiene-unit",
        },
    )
    assert fixture.status_code == 201, fixture.text
    hidden = authed_client.get("/api/projects?exclude_fixtures=1&exclude_name_candidates=0")
    assert hidden.status_code == 200
    names = {p["name"] for p in hidden.json()}
    assert "ZECT Authorized" in names
    assert "Phase6 Pollution" not in names
    named_only = authed_client.get("/api/projects?exclude_fixtures=1")
    names2 = {p["name"] for p in named_only.json()}
    assert "Phase6 Pollution" not in names2


def test_cleanup_deletes_only_proven_test(authed_client):
    db = SessionLocal()
    try:
        keep = Project(name="ZOAS Keep", provenance="user", test_run_id="")
        drop = Project(name="Drop Me", provenance=PROVENANCE_TEST, test_run_id="cleanup-run")
        db.add_all([keep, drop])
        db.commit()
        db.refresh(keep)
        db.refresh(drop)
        dry = cleanup_proven_test_projects(db, dry_run=True)
        ids = {row["id"] for row in dry["would_delete"]}
        assert drop.id in ids
        assert keep.id not in ids
        live = cleanup_proven_test_projects(db, dry_run=False)
        assert drop.id in live["deleted_ids"]
        db.expire_all()
        assert db.query(Project).filter(Project.id == keep.id).first() is not None
        assert db.query(Project).filter(Project.id == drop.id).first() is None
    finally:
        db.close()


def test_tag_then_audit_and_workitem_isolation(authed_client):
    db = SessionLocal()
    try:
        cand = Project(name="Phase6 Candidate", provenance="user", test_run_id="")
        db.add(cand)
        db.commit()
        db.refresh(cand)
        audit = audit_projects(db)
        assert any(r["id"] == cand.id for r in audit["name_candidates"])
        tagged = tag_projects_by_ids(db, [cand.id], test_run_id="legacy-hygiene")
        assert tagged["ok"] is True
        wi = WorkItem(
            title="fixture work",
            source="user",
            is_test_fixture=True,
            test_run_id="hygiene-wi",
        )
        visible = WorkItem(title="real work", source="user", is_test_fixture=False)
        db.add_all([wi, visible])
        db.commit()
    finally:
        db.close()
    listed = authed_client.get("/api/work-items?limit=200")
    assert listed.status_code == 200
    titles = {w["title"] for w in listed.json().get("items") or []}
    assert "fixture work" not in titles
    included = authed_client.get("/api/work-items?limit=200&include_fixtures=true")
    titles_all = {w["title"] for w in included.json().get("items") or []}
    assert "fixture work" in titles_all
