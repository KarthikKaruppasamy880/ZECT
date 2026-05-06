"""Code Review API endpoints for ZECT.

Provides AI-powered code review for PRs and code snippets,
identifying bugs, vulnerabilities, performance issues, and more.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import github_service
from app.review_service import review_pr_diff, review_code_snippet

# Import for inline PR review
try:
    from app.github_service import post_pr_review_comment, get_pr_review_comments
except ImportError:
    post_pr_review_comment = None
    get_pr_review_comments = None

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


# ---------------------------------------------------------------------------
# Inline PR Review Endpoints
# ---------------------------------------------------------------------------

class PostCommentRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int
    body: str
    commit_sha: str | None = None
    path: str | None = None
    line: int | None = None


class PostReviewRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int
    auto_comment: bool = True  # If True, post review findings as inline comments


@router.post("/pr/inline")
def review_pr_and_post_comments(req: PostReviewRequest):
    """Review a PR and post findings as inline comments on GitHub.

    ZECT reviews actual PRs and posts inline comments directly on GitHub,
    not just reviewing pasted snippets.
    """
    # First, run the review
    review_req = ReviewPRRequest(owner=req.owner, repo=req.repo, pr_number=req.pr_number)
    try:
        review_result = review_pull_request(review_req)
    except HTTPException:
        raise

    if not req.auto_comment:
        return review_result

    # Post findings as comments on the PR
    posted_comments = []

    # Post summary as a general comment
    summary_body = f"## ZECT AI Code Review\n\n"
    summary_body += f"**Quality Score: {review_result.quality_score}/100**\n\n"
    summary_body += f"{review_result.summary}\n\n"
    summary_body += f"**Issues Found:** {review_result.total_issues}\n\n"

    if review_result.strengths:
        summary_body += "### Strengths\n"
        for s in review_result.strengths:
            summary_body += f"- {s}\n"
        summary_body += "\n"

    if review_result.recommendations:
        summary_body += "### Recommendations\n"
        for r in review_result.recommendations:
            summary_body += f"- {r}\n"

    try:
        if post_pr_review_comment:
            comment = post_pr_review_comment(
                owner=req.owner, repo=req.repo, pr_number=req.pr_number,
                body=summary_body,
            )
            posted_comments.append(comment)
    except Exception as e:
        posted_comments.append({"error": str(e), "type": "summary"})

    # Post inline comments for each finding that has a file/line
    for finding in review_result.findings:
        if finding.get("file") and finding.get("line"):
            severity_icon = {"critical": "\U0001f6d1", "high": "\u26a0\ufe0f", "medium": "\U0001f4a1", "low": "\u2139\ufe0f"}.get(
                finding.get("severity", "").lower(), "\U0001f4a1"
            )
            comment_body = f"{severity_icon} **{finding.get('severity', 'Info').upper()}: {finding.get('title', 'Issue')}**\n\n"
            comment_body += f"{finding.get('description', '')}\n\n"
            if finding.get("suggestion"):
                comment_body += f"**Suggestion:** {finding['suggestion']}\n"
            if finding.get("code_snippet"):
                comment_body += f"\n```suggestion\n{finding['code_snippet']}\n```\n"

            try:
                if post_pr_review_comment:
                    # Get the latest commit SHA for inline comments
                    pr_data = github_service.get_pull(req.owner, req.repo, req.pr_number)
                    # Use head SHA from the PR
                    from app.github_service import get_github
                    gh = get_github()
                    repo_obj = gh.get_repo(f"{req.owner}/{req.repo}")
                    pr_obj = repo_obj.get_pull(req.pr_number)
                    head_sha = pr_obj.head.sha

                    comment = post_pr_review_comment(
                        owner=req.owner, repo=req.repo, pr_number=req.pr_number,
                        body=comment_body,
                        commit_sha=head_sha,
                        path=finding["file"],
                        line=finding["line"],
                    )
                    posted_comments.append(comment)
            except Exception as e:
                posted_comments.append({"error": str(e), "file": finding.get("file"), "type": "inline"})

    return {
        "review": review_result.model_dump(),
        "posted_comments": posted_comments,
        "total_comments_posted": len([c for c in posted_comments if "error" not in c]),
    }


@router.post("/pr/comment")
def post_review_comment(req: PostCommentRequest):
    """Post a single comment on a PR (inline or general)."""
    if not post_pr_review_comment:
        raise HTTPException(status_code=503, detail="PR comment feature not available")
    try:
        result = post_pr_review_comment(
            owner=req.owner, repo=req.repo, pr_number=req.pr_number,
            body=req.body, commit_sha=req.commit_sha,
            path=req.path, line=req.line,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to post comment: {e}")


@router.get("/pr/{owner}/{repo}/{pr_number}/comments")
def get_review_comments(owner: str, repo: str, pr_number: int):
    """Get all review comments on a PR."""
    if not get_pr_review_comments:
        raise HTTPException(status_code=503, detail="PR comments feature not available")
    try:
        return get_pr_review_comments(owner, repo, pr_number)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to get comments: {e}")
