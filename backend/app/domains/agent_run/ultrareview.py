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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.infrastructure.auth.deps import CurrentUser
from app.infrastructure.budget import enforce_token_budget
from app.infrastructure.database import get_db
from app.domains.pr_review.finding_schema import ReviewFindingSpec, normalize_from_db

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
