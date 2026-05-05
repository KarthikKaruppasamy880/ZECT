"""Ultrareview — Multi-agent deep code review with security scanning."""

import os
import json
import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import ReviewSession, ReviewFinding, Repo
from app.token_tracker import log_tokens
from openai import OpenAI, APIError

router = APIRouter(prefix="/api/ultrareview", tags=["ultrareview"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    return OpenAI(api_key=key)


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


class FindingOut(BaseModel):
    category: str
    severity: str
    title: str
    description: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    suggestion: str | None = None
    fixed_code: str | None = None
    cwe_id: str | None = None
    owasp_category: str | None = None


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

REVIEW_SYSTEM_PROMPT = """You are ZECT Ultrareview — an elite multi-agent code review engine.
Analyze the code for:
1. **Security vulnerabilities** (injection, XSS, CSRF, auth bypass, secrets exposure, SSRF)
2. **Bugs** (null refs, race conditions, off-by-one, logic errors, unhandled edge cases)
3. **Performance** (N+1 queries, memory leaks, unnecessary re-renders, blocking I/O)
4. **Code quality** (duplication, dead code, naming, complexity, SOLID violations)
5. **Architecture** (coupling, separation of concerns, scalability, testability)
6. **Best practices** (error handling, logging, input validation, documentation)

For each finding, provide:
- category: bug | security | performance | style | architecture | best_practice
- severity: critical | high | medium | low | info
- title: concise title
- description: detailed explanation
- file_path: if applicable
- line_start / line_end: if applicable
- code_snippet: the problematic code
- suggestion: how to fix it
- fixed_code: corrected code
- cwe_id: CWE ID for security findings (e.g. CWE-79)
- owasp_category: OWASP category if applicable (e.g. A03:2021-Injection)

Also provide:
- overall_score: 0-100 quality score
- review_summary: 2-3 sentence summary

Return valid JSON:
{
  "overall_score": 85,
  "review_summary": "...",
  "findings": [...]
}"""


def _parse_review(content: str) -> dict:
    """Parse the LLM response into structured review data."""
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        return {"overall_score": 0, "review_summary": "Failed to parse review response.", "findings": []}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/snippet", response_model=ReviewResult)
def review_snippet(req: SnippetReviewRequest, db: Session = Depends(get_db)):
    """Review a code snippet with multi-agent deep analysis."""
    client = _get_client()
    start = time.time()

    session = ReviewSession(
        review_type="snippet",
        status="running",
        model_used=req.model,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        resp = client.chat.completions.create(
            model=req.model,
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": f"Language: {req.language}\n\nCode:\n```{req.language}\n{req.code[:8000]}\n```"},
            ],
            max_tokens=4000,
            temperature=0.1,
        )
        content = resp.choices[0].message.content or "{}"
        tokens = resp.usage.total_tokens if resp.usage else 0
        prompt_t = resp.usage.prompt_tokens if resp.usage else 0
        completion_t = resp.usage.completion_tokens if resp.usage else 0
        cost = (prompt_t / 1000 * 0.00015) + (completion_t / 1000 * 0.0006)

        data = _parse_review(content)
        findings_data = data.get("findings", [])
        duration = int(time.time() - start)

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        db_findings = []
        for f in findings_data:
            sev = f.get("severity", "info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            finding = ReviewFinding(
                review_session_id=session.id,
                category=f.get("category", "style"),
                severity=sev,
                title=f.get("title", ""),
                description=f.get("description", ""),
                file_path=f.get("file_path"),
                line_start=f.get("line_start"),
                line_end=f.get("line_end"),
                code_snippet=f.get("code_snippet"),
                suggestion=f.get("suggestion"),
                fixed_code=f.get("fixed_code"),
                cwe_id=f.get("cwe_id"),
                owasp_category=f.get("owasp_category"),
            )
            db.add(finding)
            db_findings.append(finding)

        session.status = "completed"
        session.overall_score = data.get("overall_score", 0)
        session.review_summary = data.get("review_summary", "")
        session.total_findings = len(findings_data)
        session.critical_count = severity_counts["critical"]
        session.high_count = severity_counts["high"]
        session.medium_count = severity_counts["medium"]
        session.low_count = severity_counts["low"]
        session.info_count = severity_counts["info"]
        session.tokens_used = tokens
        session.cost_usd = round(cost, 6)
        session.duration_seconds = duration
        session.completed_at = datetime.now(timezone.utc)
        db.commit()

        log_tokens(
            action="ultrareview_snippet",
            feature="ultrareview",
            model=req.model,
            prompt_tokens=prompt_t,
            completion_tokens=completion_t,
            total_tokens=tokens,
        )

        return ReviewResult(
            session_id=session.id,
            status="completed",
            overall_score=session.overall_score,
            review_summary=session.review_summary,
            total_findings=session.total_findings,
            critical_count=session.critical_count,
            high_count=session.high_count,
            medium_count=session.medium_count,
            low_count=session.low_count,
            info_count=session.info_count,
            findings=[
                FindingOut(
                    category=f.category,
                    severity=f.severity,
                    title=f.title,
                    description=f.description or "",
                    file_path=f.file_path,
                    line_start=f.line_start,
                    line_end=f.line_end,
                    code_snippet=f.code_snippet,
                    suggestion=f.suggestion,
                    fixed_code=f.fixed_code,
                    cwe_id=f.cwe_id,
                    owasp_category=f.owasp_category,
                )
                for f in db_findings
            ],
            tokens_used=tokens,
            cost_usd=round(cost, 6),
            duration_seconds=duration,
            model_used=req.model,
        )
    except APIError as e:
        session.status = "failed"
        db.commit()
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")


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
    """Get a review session with all findings."""
    session = db.query(ReviewSession).filter(ReviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    findings = db.query(ReviewFinding).filter(ReviewFinding.review_session_id == session_id).all()
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
        findings=[
            FindingOut(
                category=f.category,
                severity=f.severity,
                title=f.title,
                description=f.description or "",
                file_path=f.file_path,
                line_start=f.line_start,
                line_end=f.line_end,
                code_snippet=f.code_snippet,
                suggestion=f.suggestion,
                fixed_code=f.fixed_code,
                cwe_id=f.cwe_id,
                owasp_category=f.owasp_category,
            )
            for f in findings
        ],
        tokens_used=session.tokens_used,
        cost_usd=session.cost_usd,
        duration_seconds=session.duration_seconds,
        model_used=session.model_used,
    )
