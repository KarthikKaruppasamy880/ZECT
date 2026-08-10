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
from app.services.mentrix.untrusted_content import sanitize_for_prompt, tag_untrusted

router = APIRouter(prefix="/api/learning", tags=["zect-learning"])

PBL_REPO = "https://github.com/practical-tutorials/project-based-learning"
PBL_RAW_README = (
    "https://raw.githubusercontent.com/practical-tutorials/project-based-learning/master/README.md"
)
PBL_LICENSE = "MIT"
PBL_ATTRIBUTION = "practical-tutorials/project-based-learning (MIT) — tutorial links remain external"

MODES = ("GUIDED", "PAIR", "DEMO", "AUTONOMOUS")


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
    resource_id: int
    mode: str = "GUIDED"
    title: str = ""
    work_item_id: Optional[int] = None


class ProgressIn(BaseModel):
    event: str  # started | milestone | test_passed | user_confirmed | completed
    milestone: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class MentorAskIn(BaseModel):
    question: str
    project_id: Optional[int] = None
    mode: str = "GUIDED"


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
    res = db.query(LearningResource).filter(LearningResource.id == body.resource_id).first()
    if not res:
        raise HTTPException(404, "resource_not_found")
    proj = LearningProject(
        user_id=getattr(current_user, "user_id", None),
        resource_id=res.id,
        title=(body.title or res.title)[:300],
        mode=mode,
        status="active",
        skills_json=res.skills_json,
        work_item_id=body.work_item_id,
        progress_json=json.dumps({"started": True, "milestones_done": []}),
        evidence_json=json.dumps([{"event": "started", "at": datetime.now(timezone.utc).isoformat()}]),
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return serialize_project(proj)


@router.get("/projects")
@require_authentication
def my_projects(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = getattr(current_user, "user_id", None)
    q = db.query(LearningProject)
    if uid:
        q = q.filter(LearningProject.user_id == uid)
    rows = q.order_by(LearningProject.id.desc()).limit(100).all()
    return {"projects": [serialize_project(p) for p in rows]}


@router.post("/projects/{project_id}/progress")
@require_authentication
def update_progress(
    project_id: int,
    body: ProgressIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    uid = getattr(current_user, "user_id", None)
    q = db.query(LearningProject).filter(LearningProject.id == project_id)
    if uid is not None:
        q = q.filter(LearningProject.user_id == uid)
    proj = q.first()
    if not proj:
        raise HTTPException(404, "project_not_found")
    progress = _jload(proj.progress_json, {})
    evidence = _jload(proj.evidence_json, [])
    # user_confirmed is evidence only — does not grant verified skills / completion
    verified_event = body.event in ("test_passed", "milestone", "completed")
    ev = {
        "event": body.event,
        "milestone": body.milestone,
        "evidence": body.evidence,
        "at": datetime.now(timezone.utc).isoformat(),
        "verified": verified_event,
    }
    evidence.append(ev)
    if body.event == "milestone" and body.milestone:
        done = list(progress.get("milestones_done") or [])
        if body.milestone not in done:
            done.append(body.milestone)
        progress["milestones_done"] = done
    if body.event == "user_confirmed":
        progress["user_confirmed"] = True
    if body.event == "completed":
        proj.status = "completed"
        proj.completed_at = datetime.now(timezone.utc)
        progress["completed"] = True
    proj.progress_json = json.dumps(progress)
    proj.evidence_json = json.dumps(evidence[-50:])
    db.commit()
    db.refresh(proj)
    return serialize_project(proj)


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
    project = None
    resource = None
    if body.project_id:
        uid = getattr(current_user, "user_id", None)
        pq = db.query(LearningProject).filter(LearningProject.id == body.project_id)
        if uid is not None:
            pq = pq.filter(LearningProject.user_id == uid)
        project = pq.first()
        if body.project_id and not project:
            raise HTTPException(404, "project_not_found")
        if project and project.resource_id:
            resource = db.query(LearningResource).filter(LearningResource.id == project.resource_id).first()

    # External catalog text is untrusted
    catalog_ctx = ""
    if resource:
        catalog_ctx = sanitize_for_prompt(
            f"Title: {resource.title}\nURL: {resource.source_url}\nSummary: {resource.summary}",
            source="learning_catalog",
        )

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

    return {
        "ok": True,
        "answer": answer,
        "route": route,
        "catalog_context": tag_untrusted(catalog_ctx, source="learning_catalog") if catalog_ctx else None,
        "project": serialize_project(project) if project else None,
        "resource": serialize_resource(resource) if resource else None,
    }


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
