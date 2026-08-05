"""Ultrareview — review history (list/detail) over ReviewSession/ReviewFinding.

/snippet used to duplicate review_service.py's LLM-calling logic a third time
(confirmed: same 6-category JSON schema as code_review.py's REVIEW_SYSTEM_PROMPT
and review_phase.py's now-retired duplicate) — it now delegates to the same
canonical review_code_snippet(), which persists through _persist_review_session
(the exact ReviewSession/ReviewFinding models this router already queries for
history). One engine, three entry points (PR/snippet/repo via code_review.py,
generic fix-prompt via review_phase.py, history browsing here), zero duplicate
LLM prompts.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.budget import enforce_token_budget
from app.infrastructure.database import get_db
from app.models import ReviewSession, ReviewFinding
from app.domains.pr_review.finding_schema import ReviewFindingSpec, normalize_from_db
from app.domains.pr_review.post_approval import (
    approve_post,
    build_fix_goal_from_findings,
    get_approval,
    post_findings_to_github,
    require_approval,
)

router = APIRouter(prefix="/api/ultrareview", tags=["ultrareview"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SnippetReviewRequest(BaseModel):
    code: str
    language: str = "typescript"
    review_type: str = "snippet"  # snippet, full_repo
    model: str = "gpt-4o-mini"


class PRReviewRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int
    model: str = "gpt-4o-mini"


# FindingOut = canonical Upgrade.md shape (Phase 4 Stage A)
FindingOut = ReviewFindingSpec


class ReviewResult(BaseModel):
    session_id: int
    status: str
    overall_score: float
    review_summary: str
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    findings: list[FindingOut]
    tokens_used: int
    cost_usd: float
    duration_seconds: int
    model_used: str


class ReviewListItem(BaseModel):
    id: int
    review_type: str
    status: str
    overall_score: float
    total_findings: int
    critical_count: int
    high_count: int
    tokens_used: int
    model_used: str
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_review_result(session: ReviewSession, findings: list[ReviewFinding]) -> ReviewResult:
    """Session + findings rows -> API response. Shared by /snippet and
    GET /{session_id} so there's one serialization path, not two."""
    return ReviewResult(
        session_id=session.id,
        status=session.status,
        overall_score=session.overall_score,
        review_summary=session.review_summary or "",
        total_findings=session.total_findings,
        critical_count=session.critical_count,
        high_count=session.high_count,
        medium_count=session.medium_count,
        low_count=session.low_count,
        info_count=session.info_count,
        findings=[normalize_from_db(f) for f in findings],
        tokens_used=session.tokens_used,
        cost_usd=session.cost_usd,
        duration_seconds=session.duration_seconds,
        model_used=session.model_used,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/snippet", response_model=ReviewResult)
def review_snippet(
    req: SnippetReviewRequest,
    current_user: CurrentUser = Depends(enforce_token_budget),
    db: Session = Depends(get_db),
):
    """Review a code snippet — delegates to the canonical review engine
    (review_service.review_code_snippet), which persists to ReviewSession/
    ReviewFinding itself; this just re-fetches that session for the response."""
    from app.review_service import review_code_snippet

    try:
        result = review_code_snippet(code=req.code, language=req.language, user_id=current_user.user_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    session_id = result.get("review_session_id")
    if session_id is None:
        raise HTTPException(status_code=500, detail="Review completed but could not be persisted to history.")

    session = db.query(ReviewSession).filter(ReviewSession.id == session_id).first()
    findings = db.query(ReviewFinding).filter(ReviewFinding.review_session_id == session_id).all()
    return _build_review_result(session, findings)


@router.get("", response_model=list[ReviewListItem])
@router.get("/", response_model=list[ReviewListItem])
def list_reviews(limit: int = 20, db: Session = Depends(get_db)):
    """List recent review sessions."""
    sessions = db.query(ReviewSession).order_by(ReviewSession.created_at.desc()).limit(limit).all()
    return [
        ReviewListItem(
            id=s.id,
            review_type=s.review_type,
            status=s.status,
            overall_score=s.overall_score,
            total_findings=s.total_findings,
            critical_count=s.critical_count,
            high_count=s.high_count,
            tokens_used=s.tokens_used,
            model_used=s.model_used,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=ReviewResult)
def get_review(session_id: int, db: Session = Depends(get_db)):
    """Get a review session with all findings — populated by PR, snippet,
    and full-repo reviews alike now, not just this router's old /snippet."""
    session = db.query(ReviewSession).filter(ReviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    findings = db.query(ReviewFinding).filter(ReviewFinding.review_session_id == session_id).all()
    return _build_review_result(session, findings)


class ApprovePostRequest(BaseModel):
    finding_ids: list[int]
    owner: str | None = None
    repo: str | None = None
    pr_number: int | None = None


class PostGithubRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int


class StartFixRunRequest(BaseModel):
    workspace: str
    project_key: str = ""
    project_id: int | None = None
    repo_id: int | None = None
    owner: str | None = None
    repo: str | None = None
    pr_number: int | None = None


@router.post("/{session_id}/approve-post")
def approve_findings_for_post(
    session_id: int,
    req: ApprovePostRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Stage D — human must approve selected findings before GitHub post or fix run."""
    session = db.query(ReviewSession).filter(ReviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    rows = (
        db.query(ReviewFinding)
        .filter(ReviewFinding.review_session_id == session_id, ReviewFinding.id.in_(req.finding_ids))
        .all()
    )
    if not rows:
        raise HTTPException(status_code=400, detail="No matching findings for this session")
    try:
        rec = approve_post(
            session_id,
            [r.id for r in rows],
            approved_by=getattr(user, "email", None),
            owner=req.owner,
            repo=req.repo,
            pr_number=req.pr_number or session.pr_number,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "approved", **rec, "finding_count": len(rows)}


@router.get("/{session_id}/approval")
def get_post_approval(session_id: int, _user: CurrentUser = Depends(get_current_user)):
    rec = get_approval(session_id)
    if not rec:
        return {"approved": False, "session_id": session_id}
    return {"approved": True, "session_id": session_id, **rec}


@router.post("/{session_id}/post-github")
def post_approved_findings(
    session_id: int,
    req: PostGithubRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Post only approved findings — reuses github_service.post_pr_review_comment."""
    try:
        rec = require_approval(session_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    session = db.query(ReviewSession).filter(ReviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    rows = (
        db.query(ReviewFinding)
        .filter(ReviewFinding.review_session_id == session_id, ReviewFinding.id.in_(rec["finding_ids"]))
        .all()
    )
    findings = [
        {
            "title": r.title,
            "severity": r.severity,
            "description": r.description,
            "file": r.file_path,
            "line": r.line_start,
            "suggestion": r.suggestion,
            "code_snippet": r.code_snippet,
        }
        for r in rows
    ]
    posted = post_findings_to_github(
        owner=req.owner,
        repo=req.repo,
        pr_number=req.pr_number,
        findings=findings,
        summary=session.review_summary or "",
        quality_score=session.overall_score,
    )
    return {
        "status": "posted",
        "session_id": session_id,
        "posted_count": len(posted),
        "posted_comments": posted,
        "approved_by": rec.get("approved_by") or getattr(user, "email", None),
    }


@router.post("/{session_id}/start-fix-run")
def start_fix_run_from_findings(
    session_id: int,
    req: StartFixRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Start existing Mentrix bugfix run from approved findings (coding-engine bridge via worker)."""
    try:
        rec = require_approval(session_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    if not (req.workspace or "").strip():
        raise HTTPException(status_code=400, detail="workspace is required")

    session = db.query(ReviewSession).filter(ReviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    rows = (
        db.query(ReviewFinding)
        .filter(ReviewFinding.review_session_id == session_id, ReviewFinding.id.in_(rec["finding_ids"]))
        .all()
    )
    if not rows:
        raise HTTPException(status_code=400, detail="No approved findings to fix")

    goal = build_fix_goal_from_findings(
        rows,
        repo=req.repo or (f"{req.owner}/{req.repo}" if req.owner and req.repo else None),
        pr_number=req.pr_number or session.pr_number,
    )

    # Reuse Mentrix start_run internals — no new orchestrator
    import json
    from app.models import MentrixRun
    from app.workers.mentrix_worker import run_mentrix_in_background
    from app.domains.audit.audit_trail import log_audit

    run = MentrixRun(
        project_id=req.project_id,
        mode="bugfix",
        goal=goal,
        status="running",
        current_agent="orchestrator",
        events_json="[]",
        gates_json="{}",
        result_json=json.dumps(
            {
                "context": {
                    "project_key": req.project_key or "",
                    "workspace": req.workspace or "",
                    "repo_id": req.repo_id,
                    "review_session_id": session_id,
                    "approved_finding_ids": rec["finding_ids"],
                }
            }
        ),
        next_step="",
        created_by=getattr(user, "email", "") or "",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        log_audit(
            db,
            action="ultrareview_start_fix_run",
            resource_type="mentrix_run",
            resource_id=run.id,
            resource_name=goal[:120],
            details=json.dumps({"session_id": session_id, "finding_ids": rec["finding_ids"]}),
            user_id=getattr(user, "id", None) if isinstance(getattr(user, "id", None), int) else None,
        )
    except Exception:
        pass

    background_tasks.add_task(
        run_mentrix_in_background,
        run.id,
        goal=goal,
        mode="bugfix",
        project_key=req.project_key,
        project_id=req.project_id,
        created_by=getattr(user, "email", None),
        workspace=req.workspace,
        source_lang=None,
        target_lang=None,
        repo_id=req.repo_id,
    )
    return {
        "status": "started",
        "session_id": session_id,
        "mentrix_run_id": run.id,
        "mode": "bugfix",
        "finding_count": len(rows),
        "goal_preview": goal[:500],
    }
