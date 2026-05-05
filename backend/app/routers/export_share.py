"""Export/Share — Export plans, blueprints, reviews as PDF or Markdown."""

import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import ExportJob, GeneratedOutput, ReviewSession

router = APIRouter(prefix="/api/export", tags=["export"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    content_type: str  # blueprint, plan, review, code, deploy_checklist, custom
    export_type: str = "markdown"  # markdown, pdf
    source_id: int | None = None  # generated_output or review_session ID
    title: str = ""
    custom_content: str = ""  # for custom exports


class ExportJobOut(BaseModel):
    id: int
    export_type: str
    content_type: str
    title: str
    status: str
    file_size_bytes: int
    created_at: str
    completed_at: str | None


class ExportResult(BaseModel):
    job_id: int
    export_type: str
    content: str  # markdown content or file path for PDF
    title: str
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=ExportResult)
@router.post("/", response_model=ExportResult)
def create_export(req: ExportRequest, db: Session = Depends(get_db)):
    """Create an export job — generates Markdown (PDF support planned)."""
    content = ""
    title = req.title

    if req.custom_content:
        content = req.custom_content
        title = title or "Custom Export"
    elif req.source_id and req.content_type in ("blueprint", "plan", "code", "deploy_checklist"):
        output = db.query(GeneratedOutput).filter(GeneratedOutput.id == req.source_id).first()
        if not output:
            raise HTTPException(status_code=404, detail="Source output not found")
        title = title or output.title or f"{output.output_type} Export"
        content = _format_output_as_markdown(output)
    elif req.source_id and req.content_type == "review":
        session = db.query(ReviewSession).filter(ReviewSession.id == req.source_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Review session not found")
        title = title or f"Code Review #{session.id}"
        content = _format_review_as_markdown(session, db)
    else:
        raise HTTPException(status_code=400, detail="Provide source_id or custom_content")

    job = ExportJob(
        export_type=req.export_type,
        content_type=req.content_type,
        title=title,
        status="completed",
        file_size_bytes=len(content.encode()),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return ExportResult(
        job_id=job.id,
        export_type=req.export_type,
        content=content,
        title=title,
        status="completed",
    )


@router.get("", response_model=list[ExportJobOut])
@router.get("/", response_model=list[ExportJobOut])
def list_exports(limit: int = 20, db: Session = Depends(get_db)):
    """List recent export jobs."""
    jobs = db.query(ExportJob).order_by(ExportJob.created_at.desc()).limit(limit).all()
    return [
        ExportJobOut(
            id=j.id,
            export_type=j.export_type,
            content_type=j.content_type,
            title=j.title or "",
            status=j.status,
            file_size_bytes=j.file_size_bytes,
            created_at=j.created_at.isoformat() if j.created_at else "",
            completed_at=j.completed_at.isoformat() if j.completed_at else None,
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=ExportJobOut)
def get_export(job_id: int, db: Session = Depends(get_db)):
    """Get export job details."""
    job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return ExportJobOut(
        id=job.id,
        export_type=job.export_type,
        content_type=job.content_type,
        title=job.title or "",
        status=job.status,
        file_size_bytes=job.file_size_bytes,
        created_at=job.created_at.isoformat() if job.created_at else "",
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_output_as_markdown(output: GeneratedOutput) -> str:
    lines = [
        f"# {output.title or output.output_type}",
        "",
        f"**Type:** {output.output_type}",
        f"**Feature:** {output.feature}",
        f"**Model:** {output.model_used}",
        f"**Tokens:** {output.tokens_used}",
        f"**Generated:** {output.created_at.isoformat() if output.created_at else 'N/A'}",
        "",
        "---",
        "",
    ]
    if output.prompt_used:
        lines += ["## Prompt", "", output.prompt_used, "", "---", ""]
    if output.output_content:
        lang = output.language or ""
        lines += ["## Output", "", f"```{lang}", output.output_content, "```", ""]
    return "\n".join(lines)


def _format_review_as_markdown(session: ReviewSession, db: Session) -> str:
    from app.models import ReviewFinding
    findings = db.query(ReviewFinding).filter(ReviewFinding.review_session_id == session.id).all()

    lines = [
        f"# Code Review Report",
        "",
        f"**Score:** {session.overall_score}/100",
        f"**Status:** {session.status}",
        f"**Model:** {session.model_used}",
        f"**Findings:** {session.total_findings} (Critical: {session.critical_count}, High: {session.high_count}, Medium: {session.medium_count}, Low: {session.low_count})",
        f"**Tokens:** {session.tokens_used}",
        "",
        "## Summary",
        "",
        session.review_summary or "No summary available.",
        "",
        "---",
        "",
        "## Findings",
        "",
    ]
    for i, f in enumerate(findings, 1):
        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}.get(f.severity, "")
        lines += [
            f"### {i}. {severity_emoji} [{f.severity.upper()}] {f.title}",
            "",
            f"**Category:** {f.category}",
        ]
        if f.file_path:
            lines.append(f"**File:** `{f.file_path}`")
        if f.line_start:
            lines.append(f"**Lines:** {f.line_start}-{f.line_end or f.line_start}")
        lines += ["", f.description or "", ""]
        if f.code_snippet:
            lines += ["**Code:**", f"```", f.code_snippet, "```", ""]
        if f.suggestion:
            lines += ["**Suggestion:**", f.suggestion, ""]
        if f.fixed_code:
            lines += ["**Fix:**", "```", f.fixed_code, "```", ""]
        if f.cwe_id:
            lines.append(f"**CWE:** {f.cwe_id}")
        if f.owasp_category:
            lines.append(f"**OWASP:** {f.owasp_category}")
        lines += ["", "---", ""]

    return "\n".join(lines)
