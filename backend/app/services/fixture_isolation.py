"""Provenance-first fixture isolation for Projects and WorkItems.

Name matching is candidate identification only. Cleanup may delete only rows
with provenance=test (or is_test_fixture) and a non-empty test_run_id.
"""

from __future__ import annotations

import os
import re
from typing import Any

from sqlalchemy.orm import Session

PROVENANCE_USER = "user"
PROVENANCE_TEST = "test"

DEMO_NAMES = frozenset(
    {
        "Policy Admin Modernization",
        "Claims Processing API",
        "Agent Portal Redesign",
        "Underwriting Rules Engine",
        "Customer Notifications Service",
        "Document Intelligence Pipeline",
    }
)
FIXTURE_NAME = re.compile(
    r"^(Phase6\b|zect-r36-|r36-live-|Repo Onboard |Onboarding Test|LIVE_E2E\b)",
    re.I,
)


def in_pytest() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("ZECT_PYTEST") == "1")


def current_test_run_id() -> str:
    current = (os.environ.get("PYTEST_CURRENT_TEST") or "").split(" ")[0].strip()
    if current:
        return current[:120]
    if os.environ.get("ZECT_PYTEST") == "1":
        return (os.environ.get("ZECT_TEST_RUN_ID") or "pytest")[:120]
    return ""


def is_fixture_project_name(name: str) -> bool:
    """Legacy name heuristic — candidates only, never a delete rule."""
    n = (name or "").strip()
    return n in DEMO_NAMES or bool(FIXTURE_NAME.search(n))


def project_provenance(project: Any) -> str:
    raw = str(getattr(project, "provenance", None) or PROVENANCE_USER).strip().lower()
    return PROVENANCE_TEST if raw == PROVENANCE_TEST else PROVENANCE_USER


def is_proven_test_project(project: Any) -> bool:
    rid = str(getattr(project, "test_run_id", None) or "").strip()
    return project_provenance(project) == PROVENANCE_TEST and bool(rid)


def is_name_candidate_project(project: Any) -> bool:
    if is_proven_test_project(project):
        return False
    return is_fixture_project_name(getattr(project, "name", "") or "")


def should_hide_project(project: Any, *, exclude_name_candidates: bool) -> bool:
    if is_proven_test_project(project):
        return True
    if exclude_name_candidates and is_name_candidate_project(project):
        return True
    return False


def is_test_work_item(item: Any) -> bool:
    if bool(getattr(item, "is_test_fixture", False)):
        return True
    rid = str(getattr(item, "test_run_id", None) or "").strip()
    return bool(rid) and project_provenance(item) == PROVENANCE_TEST


def serialize_project_hygiene(project: Any) -> dict[str, Any]:
    repos = list(getattr(project, "repos", None) or [])
    return {
        "id": getattr(project, "id", None),
        "name": getattr(project, "name", ""),
        "provenance": project_provenance(project),
        "test_run_id": str(getattr(project, "test_run_id", None) or ""),
        "repo_count": len(repos),
        "created_at": getattr(project, "created_at", None).isoformat()
        if getattr(project, "created_at", None)
        else None,
        "name_candidate": is_name_candidate_project(project),
        "proven_test": is_proven_test_project(project),
    }


def audit_projects(db: Session) -> dict[str, Any]:
    from app.models import Project

    rows = db.query(Project).order_by(Project.id.asc()).all()
    proven = [serialize_project_hygiene(p) for p in rows if is_proven_test_project(p)]
    candidates = [serialize_project_hygiene(p) for p in rows if is_name_candidate_project(p)]
    user_rows = [
        serialize_project_hygiene(p)
        for p in rows
        if not is_proven_test_project(p) and not is_name_candidate_project(p)
    ]
    return {
        "ok": True,
        "proven_test": proven,
        "name_candidates": candidates,
        "authorized": user_rows,
        "note": (
            "Name matches are candidates only. Cleanup deletes provenance=test "
            "rows with test_run_id. Tag candidates by id before deletion."
        ),
    }


def tag_projects_by_ids(
    db: Session,
    ids: list[int],
    *,
    test_run_id: str,
) -> dict[str, Any]:
    from app.models import Project

    rid = (test_run_id or "").strip()
    if not rid:
        return {"ok": False, "error": "test_run_id_required"}
    if not ids:
        return {"ok": True, "tagged": []}
    rows = db.query(Project).filter(Project.id.in_(ids)).all()
    tagged: list[dict[str, Any]] = []
    for project in rows:
        project.provenance = PROVENANCE_TEST
        project.test_run_id = rid[:120]
        tagged.append(serialize_project_hygiene(project))
    db.commit()
    return {"ok": True, "tagged": tagged}


def cleanup_proven_test_projects(db: Session, *, dry_run: bool = True) -> dict[str, Any]:
    from app.models import Project, WorkItem

    rows = db.query(Project).all()
    proven = [p for p in rows if is_proven_test_project(p)]
    planned = [serialize_project_hygiene(p) for p in proven]
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_delete": planned,
            "count": len(planned),
        }
    deleted_ids: list[int] = []
    for project in proven:
        pid = int(project.id)
        db.query(WorkItem).filter(WorkItem.project_id == pid).delete(synchronize_session=False)
        db.delete(project)
        deleted_ids.append(pid)
    db.commit()
    return {"ok": True, "dry_run": False, "deleted_ids": deleted_ids, "count": len(deleted_ids)}


def _null_optional_project_fks(db: Session, project_ids: list[int]) -> None:
    """Null nullable project_id FKs so Project delete is not blocked."""
    from app.models import Base, Project, Repo, WorkItem

    skip = {Project, Repo, WorkItem}
    id_set = set(project_ids)
    if not id_set:
        return
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if cls in skip or not hasattr(cls, "project_id"):
            continue
        col = getattr(cls, "project_id")
        cols = list(getattr(getattr(col, "property", None), "columns", []) or [])
        if cols and not bool(getattr(cols[0], "nullable", True)):
            continue
        try:
            with db.begin_nested():
                db.query(cls).filter(col.in_(id_set)).update({col: None}, synchronize_session=False)
        except Exception:  # noqa: BLE001 — table may not exist in this schema
            continue


def keep_cleanup_projects(
    db: Session,
    keep_ids: list[int],
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Operator cleanup: delete every project except explicit keep_ids. Never delete-by-name."""
    from app.models import Project, WorkItem

    keep = {int(i) for i in keep_ids if int(i) > 0}
    if not keep:
        return {"ok": False, "error": "keep_ids_required"}
    rows = db.query(Project).order_by(Project.id.asc()).all()
    would_keep = [serialize_project_hygiene(p) for p in rows if int(p.id) in keep]
    would_delete = [serialize_project_hygiene(p) for p in rows if int(p.id) not in keep]
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_keep": would_keep,
            "would_delete": would_delete,
            "count": len(would_delete),
        }
    deleted_ids: list[int] = [int(p.id) for p in rows if int(p.id) not in keep]
    if deleted_ids:
        db.query(WorkItem).filter(WorkItem.project_id.in_(deleted_ids)).delete(synchronize_session=False)
        _null_optional_project_fks(db, deleted_ids)
        for project in list(rows):
            if int(project.id) in keep:
                continue
            db.delete(project)
        db.commit()
    return {
        "ok": True,
        "dry_run": False,
        "kept_ids": sorted(keep),
        "deleted_ids": deleted_ids,
        "count": len(deleted_ids),
    }
