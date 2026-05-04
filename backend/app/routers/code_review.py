"""Code Review API endpoints for ZECT.

Provides AI-powered code review for PRs and code snippets,
identifying bugs, vulnerabilities, performance issues, and more.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import github_service
from app.review_service import review_pr_diff, review_code_snippet

router = APIRouter(prefix="/api/review", tags=["code-review"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ReviewPRRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int


class ReviewSnippetRequest(BaseModel):
    code: str
    language: str = "unknown"


class ReviewFinding(BaseModel):
    severity: str
    category: str
    title: str
    description: str
    file: str | None = None
    line: int | None = None
    suggestion: str | None = None
    code_snippet: str | None = None


class ReviewCategories(BaseModel):
    bugs: int = 0
    vulnerabilities: int = 0
    performance: int = 0
    code_quality: int = 0
    architecture: int = 0
    best_practices: int = 0


class ReviewResponse(BaseModel):
    summary: str
    quality_score: int
    total_issues: int
    categories: dict
    findings: list[dict]
    strengths: list[str]
    recommendations: list[str]
    tokens_used: int
    model: str
    pr_number: int | None = None
    repo: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/pr", response_model=ReviewResponse)
def review_pull_request(req: ReviewPRRequest):
    """Run AI code review on a GitHub Pull Request.

    Fetches the PR diff from GitHub and analyses it for bugs,
    vulnerabilities, code quality issues, and structural problems.
    """
    try:
        pr = github_service.get_pull(req.owner, req.repo, req.pr_number)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch PR: {e}")

    try:
        files_raw = github_service.get_pull_files(req.owner, req.repo, req.pr_number)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch PR files: {e}")

    files = [
        {
            "filename": f.filename,
            "status": f.status,
            "additions": f.additions,
            "deletions": f.deletions,
            "patch": f.patch,
        }
        for f in files_raw
    ]

    try:
        result = review_pr_diff(
            owner=req.owner,
            repo=req.repo,
            pr_number=req.pr_number,
            pr_title=pr.title,
            pr_body=pr.body,
            files=files,
        )
        return ReviewResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/snippet", response_model=ReviewResponse)
def review_snippet(req: ReviewSnippetRequest):
    """Run AI code review on a standalone code snippet."""
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="Code snippet cannot be empty.")

    try:
        result = review_code_snippet(code=req.code, language=req.language)
        return ReviewResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
