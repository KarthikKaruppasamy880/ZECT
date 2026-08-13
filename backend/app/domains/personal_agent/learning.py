"""ZECT Learning / Mentrix Learning Advisor — catalog + projects (no second assistant)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import require_authentication, log_audit
from app.infrastructure.database import get_db
from app.models import LearningProject, LearningResource, LearningSource, WorkItem
from app.services.learning.curriculum import (
    get_lesson,
    get_path,
    list_path_summaries,
    serialize_lesson_public,
)
from app.services.learning.handoff import graduate_skill_draft, handoff_to_developer
from app.services.learning.mastery import collect_user_evidence
from app.services.learning.mentor import progressive_hint, reject_guided_full_solution
from app.services.learning.practice_fsm import (
    mark_lesson_verified,
    record_hint,
    record_practice_attempt,
    start_lesson,
)
from app.services.learning.practice_runner import evidence_from_run, run_server_practice
from app.services.learning.work_item_access import resolve_owned_work_item
from app.services.mentrix.untrusted_content import sanitize_for_prompt, tag_untrusted
from app.services.mentrix.permission_broker import check_tool_permission

router = APIRouter(prefix="/api/learning", tags=["zect-learning"])

PBL_REPO = "https://github.com/practical-tutorials/project-based-learning"
PBL_RAW_README = (
    "https://raw.githubusercontent.com/practical-tutorials/project-based-learning/master/README.md"
)
PBL_LICENSE = "MIT"
PBL_ATTRIBUTION = "practical-tutorials/project-based-learning (MIT) — tutorial links remain external"

MODES = ("GUIDED", "PAIR", "DEMO", "AUTONOMOUS")

# Curated initial language paths (catalog filter + UI chips)
SUPPORTED_LANGUAGES = (
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C#",
    "Go",
    "Rust",
    "C",
    "C++",
)


def _jload(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def serialize_source(s: LearningSource) -> dict[str, Any]:
    return {
        "id": s.id,
        "source_type": s.source_type,
        "name": s.name,
        "repository_url": s.repository_url,
        "license": s.license,
        "attribution": s.attribution,
        "refresh_policy": s.refresh_policy,
        "enabled": bool(s.enabled),
        "last_synced_at": s.last_synced_at.isoformat() if s.last_synced_at else None,
    }


def serialize_resource(r: LearningResource) -> dict[str, Any]:
    return {
        "id": r.id,
        "learning_source_id": r.learning_source_id,
        "title": r.title,
        "source_url": r.source_url,
        "language": r.language,
        "technologies": _jload(r.technologies_json, []),
        "project_type": r.project_type,
        "difficulty": r.difficulty,
        "prerequisites": _jload(r.prerequisites_json, []),
        "skills": _jload(r.skills_json, []),
        "summary": r.summary,
        "attribution": r.attribution,
        "content_policy": r.content_policy,
        "external_license_status": r.external_license_status,
        "indexed_at": r.indexed_at.isoformat() if r.indexed_at else None,
    }


def serialize_project(p: LearningProject) -> dict[str, Any]:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "resource_id": p.resource_id,
        "title": p.title,
        "mode": p.mode,
        "status": p.status,
        "goals": _jload(p.goals_json, []),
        "milestones": _jload(p.milestones_json, []),
        "skills": _jload(p.skills_json, []),
        "repository_id": p.repository_id,
        "work_item_id": p.work_item_id,
        "progress": _jload(p.progress_json, {}),
        "evidence": _jload(p.evidence_json, []),
        "started_at": p.started_at.isoformat() if p.started_at else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
    }


def parse_pbl_readme(markdown: str) -> list[dict[str, Any]]:
    """Parse project-based-learning README into catalog metadata (links only)."""
    resources: list[dict[str, Any]] = []
    current_lang = ""
    # ## Language or ### Language sections + bullet links
    for line in (markdown or "").splitlines():
        h = re.match(r"^#{2,3}\s+(.+)$", line.strip())
        if h:
            title = h.group(1).strip()
            if title.lower() not in ("table of contents", "contents", "license", "contributing"):
                current_lang = title
            continue
        m = re.match(r"^[-*]\s+\[([^\]]+)\]\((https?://[^)]+)\)(.*)$", line.strip())
        if not m:
            continue
        title, url, rest = m.group(1).strip(), m.group(2).strip(), (m.group(3) or "").strip()
        host = urlparse(url).netloc.lower()
        # Skip same-repo anchors only
        if "github.com/practical-tutorials/project-based-learning" in url and "#" in url and url.count("/") <= 5:
            continue
        skills = [current_lang] if current_lang else []
        techs = [t.strip() for t in re.findall(r"`([^`]+)`", rest)][:8]
        resources.append(
            {
                "title": title[:300],
                "source_url": url[:1000],
                "language": current_lang[:80],
                "technologies": techs or ([current_lang] if current_lang else []),
                "project_type": "tutorial",
                "difficulty": "intermediate",
                "prerequisites": [],
                "skills": skills,
                "summary": rest[:500] or f"External tutorial ({host})",
                "attribution": PBL_ATTRIBUTION,
                "content_policy": "external_link_only",
                "external_license_status": "link_only_third_party",
            }
        )
    return resources[:500]


def ensure_pbl_source(db: Session) -> LearningSource:
    row = db.query(LearningSource).filter(LearningSource.repository_url == PBL_REPO).first()
    if row:
        return row
    row = LearningSource(
        source_type="catalog",
        name="Project Based Learning",
        repository_url=PBL_REPO,
        license=PBL_LICENSE,
        attribution=PBL_ATTRIBUTION,
        refresh_policy="manual",
        enabled=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def sync_pbl_catalog(db: Session, *, markdown: str | None = None) -> dict[str, Any]:
    source = ensure_pbl_source(db)
    text = markdown
    if text is None:
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(PBL_RAW_README)
                if r.status_code >= 400:
                    return {"ok": False, "error": f"fetch_failed:{r.status_code}", "source": serialize_source(source)}
                text = r.text
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)[:200], "source": serialize_source(source)}

    parsed = parse_pbl_readme(text or "")
    upserted = 0
    existing_by_url = {
        row.source_url: row
        for row in db.query(LearningResource)
        .filter(LearningResource.learning_source_id == source.id)
        .all()
    }
    for item in parsed:
        existing = existing_by_url.get(item["source_url"])
        if existing:
            existing.title = item["title"]
            existing.language = item["language"]
            existing.technologies_json = json.dumps(item["technologies"])
            existing.skills_json = json.dumps(item["skills"])
            existing.summary = item["summary"]
            existing.indexed_at = datetime.now(timezone.utc)
        else:
            row = LearningResource(
                learning_source_id=source.id,
                title=item["title"],
                source_url=item["source_url"],
                language=item["language"],
                technologies_json=json.dumps(item["technologies"]),
                project_type=item["project_type"],
                difficulty=item["difficulty"],
                prerequisites_json=json.dumps(item["prerequisites"]),
                skills_json=json.dumps(item["skills"]),
                summary=item["summary"],
                attribution=item["attribution"],
                content_policy=item["content_policy"],
                external_license_status=item["external_license_status"],
            )
            db.add(row)
            existing_by_url[item["source_url"]] = row
            upserted += 1
    source.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    total = db.query(LearningResource).filter(LearningResource.learning_source_id == source.id).count()
    return {
        "ok": True,
        "source": serialize_source(source),
        "parsed": len(parsed),
        "inserted": upserted,
        "total": total,
        "content_policy": "external_link_only",
    }


class StartProjectIn(BaseModel):
    resource_id: Optional[int] = None
    path_key: str = ""
    lesson_key: str = ""
    mode: str = "GUIDED"
    title: str = ""
    work_item_id: Optional[int] = None


class ProgressIn(BaseModel):
    event: str  # started | lesson_started | milestone | test_passed | user_confirmed | completed | practice_attempt | hint_used
    milestone: str = ""
    lesson_key: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class MentorAskIn(BaseModel):
    question: str
    project_id: Optional[int] = None
    mode: str = "GUIDED"
    path_key: str = ""
    lesson_key: str = ""
    study_notes: str = ""  # optional B/C untrusted notes — never system instructions


class PracticeVerifyIn(BaseModel):
    """Practice → Code → Tests path. Client passed/exit_code are ignored (M1)."""

    code: str = ""
    language: str = "Python"
    passed: bool = False  # IGNORED — client claim
    test_output: str = ""  # IGNORED — client claim
    exit_code: int = 1  # IGNORED — client claim
    lesson_key: str = ""
    path_key: str = ""


class StartLessonIn(BaseModel):
    lesson_key: str
    path_key: str = ""


class HintIn(BaseModel):
    lesson_key: str = ""
    path_key: str = ""
    question: str = ""
    study_notes: str = ""


class GraduateIn(BaseModel):
    skill: str
    project_id: Optional[int] = None


class HandoffIn(BaseModel):
    goal: str = ""


@router.get("/languages")
@require_authentication
def list_languages(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "languages": list(SUPPORTED_LANGUAGES),
        "modes": list(MODES),
        "path": [
            "Choose Language/Skill",
            "Learning Path",
            "Topic/Lesson",
            "Practice",
            "Code",
            "Run Tests",
            "Hint",
            "Retry",
            "Evidence",
            "Verified Progress",
            "Project",
            "Skills Graduation",
        ],
        "scope": "USER_PRIVATE",
        "curriculum_paths": list_path_summaries(),
    }


@router.get("/paths")
@require_authentication
def list_paths(
    language: str = "",
    current_user: CurrentUser = Depends(get_current_user),
):
    rows = list_path_summaries()
    if language:
        lang = language.strip().lower()
        rows = [r for r in rows if (r.get("language") or "").lower() == lang or lang in (r.get("language") or "").lower()]
    return {"paths": rows, "scope": "USER_PRIVATE"}


@router.get("/paths/{path_key}")
@require_authentication
def get_path_detail(path_key: str, current_user: CurrentUser = Depends(get_current_user)):
    path = get_path(path_key)
    if not path:
        raise HTTPException(404, "path_not_found")
    return {
        "path": {
            "key": path["key"],
            "language": path["language"],
            "title": path["title"],
            "difficulty": path["difficulty"],
            "skills": path["skills"],
            "attribution": path["attribution"],
            "content_policy": path["content_policy"],
            "lessons": [serialize_lesson_public({**les, "path_key": path["key"], "language": path["language"]}) for les in path["lessons"]],
        }
    }


@router.get("/sources")
@require_authentication
def list_sources(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    rows = db.query(LearningSource).order_by(LearningSource.id.asc()).all()
    return {"sources": [serialize_source(s) for s in rows]}


@router.post("/sources/pbl/sync")
@require_authentication
def sync_pbl(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    out = sync_pbl_catalog(db)
    log_audit(
        db=db,
        user_id=getattr(current_user, "user_id", None) or 0,
        action="learning_catalog_sync",
        resource_type="learning_source",
        details={"ok": out.get("ok"), "total": out.get("total")},
    )
    return out


@router.get("/resources")
@require_authentication
def search_resources(
    q: str = "",
    language: str = "",
    difficulty: str = "",
    skill: str = "",
    limit: int = Query(40, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    query = db.query(LearningResource)
    if language:
        query = query.filter(LearningResource.language.ilike(f"%{language}%"))
    if difficulty:
        query = query.filter(LearningResource.difficulty == difficulty)
    qn = (q or "").strip()
    sk = (skill or "").strip()
    if qn:
        like = f"%{qn}%"
        query = query.filter(
            (LearningResource.title.ilike(like))
            | (LearningResource.summary.ilike(like))
            | (LearningResource.skills_json.ilike(like))
            | (LearningResource.language.ilike(like))
        )
    if sk:
        query = query.filter(LearningResource.skills_json.ilike(f"%{sk}%"))
    rows = query.order_by(LearningResource.id.desc()).limit(limit).all()
    return {"resources": [serialize_resource(r) for r in rows], "content_policy": "external_link_only"}


@router.post("/projects")
@require_authentication
def start_project(
    body: StartProjectIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    mode = (body.mode or "GUIDED").upper()
    if mode not in MODES:
        raise HTTPException(400, f"mode must be one of {MODES}")

    path = get_path(body.path_key) if body.path_key else None
    res = None
    if body.resource_id:
        res = db.query(LearningResource).filter(LearningResource.id == body.resource_id).first()
        if not res:
            raise HTTPException(404, "resource_not_found")
    if not res and not path:
        raise HTTPException(400, "resource_id_or_path_key_required")

    title = (body.title or (path["title"] if path else "") or (res.title if res else "Learning"))[:300]
    skills = list(path["skills"]) if path else _jload(res.skills_json if res else "[]", [])
    first_lesson = ""
    if path and path["lessons"]:
        first_lesson = body.lesson_key or path["lessons"][0]["key"]
        if body.lesson_key and not get_lesson(path["key"], body.lesson_key):
            raise HTTPException(404, "lesson_not_found")

    # M2: never trust client work_item_id without independent ownership check
    linked_wi: int | None = None
    if body.work_item_id is not None:
        wi = resolve_owned_work_item(db, int(body.work_item_id), current_user)
        linked_wi = wi.id

    progress: dict[str, Any] = {"started": True, "milestones_done": [], "lessons": {}, "verified_lesson_keys": []}
    if path:
        progress = start_lesson(progress, path_key=path["key"], lesson_key=first_lesson)

    proj = LearningProject(
        user_id=getattr(current_user, "user_id", None),
        resource_id=res.id if res else None,
        title=title,
        mode=mode,
        status="active",
        skills_json=json.dumps(skills),
        work_item_id=linked_wi,
        milestones_json=json.dumps([les["key"] for les in path["lessons"]] if path else []),
        progress_json=json.dumps(progress),
        evidence_json=json.dumps(
            [
                {
                    "event": "started",
                    "at": datetime.now(timezone.utc).isoformat(),
                    "path_key": path["key"] if path else "",
                    "lesson_key": first_lesson,
                    "verified": False,
                    "scope": "USER_PRIVATE",
                }
            ]
        ),
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    out = serialize_project(proj)
    out["curriculum"] = {
        "path_key": path["key"] if path else "",
        "lesson_key": first_lesson,
    }
    return out


@router.get("/projects")
@require_authentication
def my_projects(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = getattr(current_user, "user_id", None)
    if uid is None:
        raise HTTPException(401, "user_required")
    rows = (
        db.query(LearningProject)
        .filter(LearningProject.user_id == uid)
        .order_by(LearningProject.id.desc())
        .limit(100)
        .all()
    )
    return {"projects": [serialize_project(p) for p in rows]}


def _verify_learning_evidence(
    body: ProgressIn,
    *,
    server_attested: bool = False,
) -> dict[str, Any]:
    """EvidenceVerifier is authority — client claims never grant verified progress (M1/M3).

    Verifying events (test_passed / milestone / completed) require server_attested=True,
    which only practice_verify (and other server runners) may set — never from HTTP body.
    """
    from app.services.work_items.evidence_verifier import EvidenceVerifier

    if body.event == "user_confirmed":
        return {"ok": True, "verified": False, "reason": "user_confirmed_not_verified"}
    if body.event in ("practice_attempt", "hint_used", "lesson_started", "started"):
        return {"ok": True, "verified": False, "reason": "attempt_or_informational"}
    if body.event not in ("test_passed", "milestone", "completed"):
        return {"ok": True, "verified": False, "reason": "informational"}

    # M3: refuse client-manufactured verification via /progress
    if not server_attested:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "client_forged_evidence_rejected",
                "verified": False,
                "hint": "Use POST /api/learning/projects/{id}/practice/verify — server runs hidden tests.",
                "event": body.event,
            },
        )

    raw = body.evidence or {}
    if not raw.get("server_controlled") or not raw.get("run_id"):
        raise HTTPException(
            status_code=400,
            detail={"error": "server_run_required", "verified": False},
        )

    items = list(raw.get("items") or [])
    if not items:
        raise HTTPException(
            status_code=400,
            detail={"error": "server_evidence_items_required", "verified": False},
        )
    # Reject items that look client-forged (missing server_controlled on payloads)
    for i in items:
        if not isinstance(i, dict):
            continue
        payload = i.get("payload") or {}
        if not payload.get("server_controlled") and not raw.get("server_controlled"):
            raise HTTPException(
                status_code=400,
                detail={"error": "server_controlled_flag_required", "verified": False},
            )

    if any(bool(i.get("llm_claim")) for i in items if isinstance(i, dict)) and not any(
        (i.get("type") in ("TEST_RESULT", "COMMAND_EXIT", "HUMAN_APPROVAL", "FILE_CHANGED"))
        and not i.get("llm_claim")
        for i in items
        if isinstance(i, dict)
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "llm_text_alone_cannot_verify_learning", "verified": False},
        )

    result = EvidenceVerifier().verify(
        mandatory_operation_ids=["OP-LEARN-TEST"]
        if body.event == "test_passed"
        else (
            ["OP-LEARN-MILESTONE"]
            if body.event == "milestone"
            else ["OP-LEARN-TEST", "OP-LEARN-COMPLETE"]
        ),
        requirement_ids=(
            ["REQ-LEARN-PASS"]
            if body.event == "test_passed"
            else (
                ["REQ-LEARN-MILESTONE"]
                if body.event == "milestone"
                else ["REQ-LEARN-PASS", "REQ-LEARN-COMPLETE"]
            )
        ),
        acceptance_ids=(
            ["AC-LEARN-PASS"]
            if body.event == "test_passed"
            else (
                ["AC-LEARN-MILESTONE"]
                if body.event == "milestone"
                else ["AC-LEARN-PASS", "AC-LEARN-COMPLETE"]
            )
        ),
        evidence=items
        if body.event != "completed"
        else items
        + [
            {
                "id": f"learn-complete-{raw.get('run_id')}",
                "type": "TEST_RESULT",
                "operation_id": "OP-LEARN-COMPLETE",
                "requirement_ids": ["REQ-LEARN-COMPLETE"],
                "acceptance_ids": ["AC-LEARN-COMPLETE"],
                "payload": {**raw, "server_controlled": True},
                "llm_claim": False,
            }
        ],
    )
    if not result.ok:
        raise HTTPException(
            status_code=400,
            detail={"error": "evidence_required", "verified": False, **result.to_dict()},
        )
    return {"ok": True, "verified": True, "server_attested": True, **result.to_dict()}


def _owned_project(db: Session, project_id: int, current_user: CurrentUser) -> LearningProject:
    uid = getattr(current_user, "user_id", None)
    if uid is None:
        # Fail closed — never skip ownership filter (defense-in-depth)
        raise HTTPException(401, "user_required")
    proj = (
        db.query(LearningProject)
        .filter(LearningProject.id == project_id, LearningProject.user_id == uid)
        .first()
    )
    if not proj:
        raise HTTPException(404, "project_not_found")
    return proj


def _apply_progress(
    *,
    project_id: int,
    body: ProgressIn,
    db: Session,
    current_user: CurrentUser,
    server_attested: bool = False,
) -> dict[str, Any]:
    proj = _owned_project(db, project_id, current_user)
    progress = _jload(proj.progress_json, {})
    evidence = _jload(proj.evidence_json, [])
    verification = _verify_learning_evidence(body, server_attested=server_attested)
    verified_event = bool(verification.get("verified"))
    lesson_key = (body.lesson_key or progress.get("current_lesson_key") or "").strip()

    if body.event == "lesson_started" and lesson_key:
        path_key = str(progress.get("path_key") or body.evidence.get("path_key") or "")
        progress = start_lesson(progress, path_key=path_key, lesson_key=lesson_key)
    if body.event == "hint_used" and lesson_key:
        progress = record_hint(progress, lesson_key=lesson_key, level=int((body.evidence or {}).get("hint_level") or 1))
    if body.event == "practice_attempt" and lesson_key:
        # Only record pass state from server-attested evidence
        attempt_passed = bool(server_attested and (body.evidence or {}).get("passed"))
        progress = record_practice_attempt(progress, lesson_key=lesson_key, passed=attempt_passed)

    # Strip client authority flags from stored evidence blob
    safe_evidence = dict(body.evidence or {})
    for k in ("passed", "exit_code", "verified", "completed", "test_passed"):
        if k in safe_evidence and not server_attested:
            safe_evidence[f"client_claim_{k}"] = safe_evidence.pop(k)

    ev = {
        "event": body.event,
        "milestone": body.milestone,
        "lesson_key": lesson_key,
        "evidence": safe_evidence if not server_attested else body.evidence,
        "at": datetime.now(timezone.utc).isoformat(),
        "verified": verified_event,
        "verification": verification,
        "scope": "USER_PRIVATE",
        "server_attested": bool(server_attested and verified_event),
    }
    evidence.append(ev)
    if body.event == "milestone" and body.milestone and verified_event:
        done = list(progress.get("milestones_done") or [])
        if body.milestone not in done:
            done.append(body.milestone)
        progress["milestones_done"] = done
    if body.event == "test_passed" and verified_event:
        progress["tests_passed"] = int(progress.get("tests_passed") or 0) + 1
        if lesson_key:
            progress = mark_lesson_verified(progress, lesson_key=lesson_key)
            done = list(progress.get("milestones_done") or [])
            if lesson_key not in done:
                done.append(lesson_key)
            progress["milestones_done"] = done
    if body.event == "user_confirmed":
        progress["user_confirmed"] = True
        # Explicitly never completes from confirmation alone
        progress["verified_complete"] = bool(progress.get("verified_complete"))
    if body.event == "completed":
        prior_verified = any(
            isinstance(x, dict) and x.get("verified") and x.get("event") == "test_passed" for x in evidence[:-1]
        )
        if not server_attested:
            raise HTTPException(
                status_code=400,
                detail={"error": "client_forged_evidence_rejected", "verified": False},
            )
        if not prior_verified and not verified_event:
            raise HTTPException(
                status_code=400,
                detail={"error": "completion_requires_verified_tests", "verified": False},
            )
        if verified_event or prior_verified:
            proj.status = "completed"
            proj.completed_at = datetime.now(timezone.utc)
            progress["completed"] = True
            progress["verified_complete"] = True
    proj.progress_json = json.dumps(progress)
    proj.evidence_json = json.dumps(evidence[-80:])
    db.commit()
    db.refresh(proj)
    out = serialize_project(proj)
    out["verification"] = verification
    return out


@router.post("/projects/{project_id}/progress")
@require_authentication
def update_progress(
    project_id: int,
    body: ProgressIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """User state only unless server-attested (M3). Verifying events must use practice/verify."""
    return _apply_progress(
        project_id=project_id,
        body=body,
        db=db,
        current_user=current_user,
        server_attested=False,
    )


@router.post("/projects/{project_id}/practice/verify")
@require_authentication
def practice_verify(
    project_id: int,
    body: PracticeVerifyIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Submission → server hidden tests → EvidenceVerifier (M1). Client passed/exit_code ignored."""
    proj = _owned_project(db, project_id, current_user)
    progress = _jload(proj.progress_json, {})
    lesson_key = (body.lesson_key or progress.get("current_lesson_key") or "").strip()
    path_key = (body.path_key or progress.get("path_key") or "").strip()
    if not lesson_key or not path_key:
        raise HTTPException(400, detail={"error": "path_and_lesson_required", "verified": False})

    uid = getattr(current_user, "user_id", None)
    # Intentionally ignore body.passed / body.exit_code / body.test_output
    _ = (body.passed, body.exit_code, body.test_output)

    run = run_server_practice(
        code=body.code or "",
        path_key=path_key,
        lesson_key=lesson_key,
        language=body.language or "Python",
        user_id=int(uid) if uid is not None else None,
        project_id=project_id,
    )
    evidence = evidence_from_run(run)
    syntax_ok = bool(run.get("syntax_ok", True))
    passed = bool(run.get("passed"))

    attempt = _apply_progress(
        project_id=project_id,
        body=ProgressIn(
            event="practice_attempt",
            lesson_key=lesson_key,
            evidence={
                "passed": passed,
                "syntax_ok": syntax_ok,
                "run_id": run.get("run_id"),
                "submission_id": run.get("submission_id"),
                "client_claims_ignored": True,
                "server_controlled": True,
            },
        ),
        db=db,
        current_user=current_user,
        server_attested=False,
    )
    if not passed:
        return {
            "ok": False,
            "passed": False,
            "syntax_ok": syntax_ok,
            "syntax_error": run.get("stderr") if not syntax_ok else "",
            "run": {
                "run_id": run.get("run_id"),
                "submission_id": run.get("submission_id"),
                "exit_code": run.get("exit_code"),
                "stderr": (run.get("stderr") or "")[:1000],
                "stdout": (run.get("stdout") or "")[:1000],
                "error": run.get("error"),
                "server_controlled": True,
            },
            "project": attempt,
            "lesson_key": lesson_key,
            "client_claims_ignored": True,
            "hint": "Fix failing tests or syntax, then retry. Ask Mentor for a GUIDED hint — not a full solution.",
        }

    verified = _apply_progress(
        project_id=project_id,
        body=ProgressIn(event="test_passed", lesson_key=lesson_key, evidence=evidence),
        db=db,
        current_user=current_user,
        server_attested=True,
    )
    return {
        "ok": True,
        "passed": True,
        "syntax_ok": True,
        "project": verified,
        "lesson_key": lesson_key,
        "run": {
            "run_id": run.get("run_id"),
            "submission_id": run.get("submission_id"),
            "exit_code": run.get("exit_code"),
            "server_controlled": True,
        },
        "client_claims_ignored": True,
    }


@router.post("/mentor/ask")
@require_authentication
def mentor_ask(
    body: MentorAskIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Mentrix Learning Advisor — GUIDED must not silently solve the whole exercise."""
    mode = (body.mode or "GUIDED").upper()
    if mode not in MODES:
        mode = "GUIDED"

    blocked = reject_guided_full_solution(mode, body.question or "")
    if blocked:
        raise HTTPException(400, detail={"error": blocked, "mode": mode})

    project = None
    resource = None
    progress: dict[str, Any] = {}
    if body.project_id:
        project = _owned_project(db, body.project_id, current_user)
        progress = _jload(project.progress_json, {})
        if project.resource_id:
            resource = db.query(LearningResource).filter(LearningResource.id == project.resource_id).first()

    path_key = (body.path_key or progress.get("path_key") or "").strip()
    lesson_key = (body.lesson_key or progress.get("current_lesson_key") or "").strip()
    hint_level = 0
    if lesson_key and progress.get("lessons"):
        hint_level = int(((progress.get("lessons") or {}).get(lesson_key) or {}).get("hint_level") or 0)

    catalog_ctx = ""
    if resource:
        catalog_ctx = sanitize_for_prompt(
            f"Title: {resource.title}\nURL: {resource.source_url}\nSummary: {resource.summary}",
            source="learning_catalog",
        )

    if path_key and lesson_key:
        hint_out = progressive_hint(
            path_key=path_key,
            lesson_key=lesson_key,
            mode=mode,
            question=body.question,
            current_hint_level=hint_level,
            study_notes=body.study_notes or "",
        )
        if not hint_out.get("ok"):
            raise HTTPException(404, hint_out.get("error") or "lesson_not_found")
        if project:
            _apply_progress(
                project_id=project.id,
                body=ProgressIn(
                    event="hint_used",
                    lesson_key=lesson_key,
                    evidence={"hint_level": hint_out.get("hint_level"), "path_key": path_key},
                ),
                db=db,
                current_user=current_user,
            )
            project = _owned_project(db, project.id, current_user)
        return {
            "ok": True,
            "answer": hint_out["hint"],
            "route": hint_out.get("route"),
            "hint_level": hint_out.get("hint_level"),
            "hint_max": hint_out.get("hint_max"),
            "auto_complete_forbidden": hint_out.get("auto_complete_forbidden"),
            "catalog_context": tag_untrusted(catalog_ctx, source="learning_catalog") if catalog_ctx else None,
            "study_notes": hint_out.get("study_notes"),
            "project": serialize_project(project) if project else None,
            "resource": serialize_resource(resource) if resource else None,
            "lesson": hint_out.get("lesson"),
        }

    # Fallback (catalog-only project without curriculum path)
    if mode == "GUIDED":
        answer = (
            "Mentrix Learning Advisor (GUIDED): I will explain concepts and ask questions, "
            "but you write the code. I will not paste a full solution unless you switch to DEMO/PAIR/AUTONOMOUS.\n\n"
            f"Question: {body.question[:800]}\n"
        )
        if resource:
            answer += f"\nOpen the external tutorial (link-only): {resource.source_url}\n"
            answer += "Hint: break the problem into one milestone; share your next 5–10 lines for feedback."
        route = {"mode": "GUIDED", "coding_agent": False, "auto_complete_forbidden": True}
    elif mode == "PAIR":
        answer = (
            "PAIR mode: we implement together via Mentrix Developer / Coding Agent with your approval on edits.\n"
            f"Focus: {body.question[:500]}"
        )
        route = {"mode": "PAIR", "coding_agent": True, "navigate": "/workspace"}
    elif mode == "DEMO":
        answer = (
            "DEMO mode: Mentrix Coding Agent may demonstrate while explaining decisions; "
            "verify with tests before marking learning progress.\n"
            f"Goal: {body.question[:500]}"
        )
        route = {"mode": "DEMO", "coding_agent": True, "navigate": "/workspace"}
    else:
        answer = (
            "AUTONOMOUS mode: Mentrix Coding Agent may execute under existing Developer policies "
            "(plan approve / evidence). Learning progress still requires verified milestones.\n"
            f"Goal: {body.question[:500]}"
        )
        route = {"mode": "AUTONOMOUS", "coding_agent": True, "navigate": "/workspace"}

    notes = None
    if body.study_notes.strip():
        notes = tag_untrusted(
            sanitize_for_prompt(body.study_notes[:2000], source="learning_study_notes", max_chars=2000),
            source="learning_study_notes",
        )

    return {
        "ok": True,
        "answer": answer,
        "route": route,
        "catalog_context": tag_untrusted(catalog_ctx, source="learning_catalog") if catalog_ctx else None,
        "study_notes": notes,
        "project": serialize_project(project) if project else None,
        "resource": serialize_resource(resource) if resource else None,
        "auto_complete_forbidden": mode == "GUIDED",
    }


@router.post("/projects/{project_id}/lessons/start")
@require_authentication
def start_lesson_endpoint(
    project_id: int,
    body: StartLessonIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    proj = _owned_project(db, project_id, current_user)
    progress = _jload(proj.progress_json, {})
    path_key = (body.path_key or progress.get("path_key") or "").strip()
    if not path_key or not get_path(path_key):
        raise HTTPException(400, "path_key_required")
    if not get_lesson(path_key, body.lesson_key):
        raise HTTPException(404, "lesson_not_found")
    return _apply_progress(
        project_id=project_id,
        body=ProgressIn(
            event="lesson_started",
            lesson_key=body.lesson_key,
            evidence={"path_key": path_key},
        ),
        db=db,
        current_user=current_user,
    )


@router.post("/projects/{project_id}/hint")
@require_authentication
def lesson_hint(
    project_id: int,
    body: HintIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    proj = _owned_project(db, project_id, current_user)
    return mentor_ask(
        MentorAskIn(
            question=body.question or " progressive hint for my next step — do not solve the whole exercise.",
            project_id=project_id,
            mode=proj.mode or "GUIDED",
            path_key=body.path_key,
            lesson_key=body.lesson_key,
            study_notes=body.study_notes,
        ),
        db=db,
        current_user=current_user,
    )


@router.get("/mastery")
@require_authentication
def mastery_summary(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = getattr(current_user, "user_id", None)
    if uid is None:
        raise HTTPException(401, "user_required")
    return collect_user_evidence(db, int(uid))


@router.post("/projects/{project_id}/handoff/developer")
@require_authentication
def handoff_developer(
    project_id: int,
    body: HandoffIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    proj = _owned_project(db, project_id, current_user)
    email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or ""
    out = handoff_to_developer(
        db, project=proj, user_email=str(email), goal=body.goal, current_user=current_user
    )
    return out


@router.post("/skills/graduate")
@require_authentication
def graduate_skill(
    body: GraduateIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Skill draft only when accumulated verified evidence meets mastery threshold."""
    uid = getattr(current_user, "user_id", None)
    if uid is None:
        raise HTTPException(401, "user_required")
    # Only hard-deny; drafts already require approval on SkillDefinition
    perm = check_tool_permission(db, "docs_draft", user_id=int(uid), user_confirmed=True)
    level = str(perm.get("permission_level") or "").lower()
    result = str(perm.get("result") or "").lower()
    if result in ("denied", "deny", "error") or level in ("never", "deny", "denied"):
        raise HTTPException(
            403,
            detail={
                "error": "permission_denied",
                "result": result or "denied",
                "permission_level": level or "never",
                "audit_id": perm.get("audit_id"),
            },
        )

    proj = None
    if body.project_id:
        proj = _owned_project(db, body.project_id, current_user)
    out = graduate_skill_draft(db, user_id=int(uid), skill=body.skill, project=proj)
    if not out.get("ok"):
        raise HTTPException(400, detail=out)
    out["permission"] = {"result": result or "granted", "permission_level": level or "allow", "approval_required": True}
    return out


@router.get("/recommend/work-item/{work_item_id}")
@require_authentication
def recommend_for_work_item(
    work_item_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Skill-gap recommendation — never blocks work unless org policy says so."""
    wi = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not wi:
        raise HTTPException(404, "work_item_not_found")
    # Authorize: creator match or admin/lead; do not leak other users' WI content
    identity = (
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or ""
    ).strip().lower()
    role = str(getattr(current_user, "role", "") or "").lower()
    created = str(wi.created_by or "").strip().lower()
    is_admin = role in ("admin", "lead", "executive")
    if created and identity and created not in (identity,) and not is_admin:
        raise HTTPException(404, "work_item_not_found")
    blob = f"{wi.title}\n{wi.description}\n{wi.requirements_json}".lower()
    # crude skill tokens
    skill_tokens = []
    for token in ("redis", "fastapi", "react", "kafka", "docker", "postgres", "kubernetes", "graphql"):
        if token in blob:
            skill_tokens.append(token)

    uid = getattr(current_user, "user_id", None)
    verified: set[str] = set()
    if uid:
        for p in db.query(LearningProject).filter(LearningProject.user_id == uid, LearningProject.status == "completed").all():
            for sk in _jload(p.skills_json, []):
                verified.add(str(sk).lower())

    missing = [s for s in skill_tokens if s not in verified and not any(s in v for v in verified)]
    recommendations = []
    for skill in missing[:5]:
        rows = (
            db.query(LearningResource)
            .filter(LearningResource.skills_json.ilike(f"%{skill}%"))
            .limit(3)
            .all()
        )
        for r in rows:
            recommendations.append(serialize_resource(r))

    return {
        "ok": True,
        "work_item_id": wi.id,
        "required_skills_guess": skill_tokens,
        "verified_skills": sorted(verified),
        "missing_skills": missing,
        "recommendations": recommendations,
        "actions": [
            "Learn First",
            "Explain While Building",
            "Pair With Mentrix",
            "Continue Agent",
        ],
        "blocks_work": False,
        "note": "Learning recommendations never block WorkItem execution unless org policy requires training.",
        # Do not attach confidential WI body to public learning retrieval
        "leak_guard": "work_item_body_not_sent_to_external_catalog",
    }
