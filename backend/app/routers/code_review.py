"""Code Review API endpoints for ZECT.

Provides AI-powered code review for PRs, code snippets, and full repositories,
identifying bugs, vulnerabilities, performance issues, and more.
Includes auto-fix loop, GitHub webhook auto-trigger, and Rules Engine integration.
"""

import hashlib
import hmac
import json
import re
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app import github_service
from app.review_service import review_pr_diff, review_code_snippet, review_repo_files
from app.database import SessionLocal
from app.models import Rule

# Import for inline PR review
try:
    from app.github_service import post_pr_review_comment, get_pr_review_comments
except ImportError:
    post_pr_review_comment = None
    get_pr_review_comments = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["code-review"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


class ReviewRepoRequest(BaseModel):
    owner: str
    repo: str
    branch: str | None = None
    file_patterns: list[str] | None = None  # e.g. ["*.py", "src/**/*.ts"]


class AutoFixLoopRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int
    max_iterations: int = 3
    auto_comment: bool = True  # post fix suggestions as PR comments


class WebhookConfigRequest(BaseModel):
    owner: str
    repo: str
    enabled: bool = True
    auto_review: bool = True
    auto_comment: bool = True
    webhook_secret: str = ""  # optional shared secret for signature verification


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
    branch: str | None = None
    files_scanned: int | None = None
    total_lines: int | None = None
    scanned_files: list[str] | None = None


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


# ---------------------------------------------------------------------------
# Full Repository Scan
# ---------------------------------------------------------------------------

@router.post("/repo", response_model=ReviewResponse)
def review_full_repo(req: ReviewRepoRequest):
    """Scan an entire GitHub repository and run AI code review on all source files.

    Unlike PR review (which only checks changed files), this scans ALL source files
    in the repo — useful for new repos, legacy repos, and full security audits.
    """
    try:
        result = review_repo_files(
            owner=req.owner,
            repo=req.repo,
            branch=req.branch,
            file_patterns=req.file_patterns,
        )
        return ReviewResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repo scan failed: {e}")


# ---------------------------------------------------------------------------
# Auto-Fix Loop: Review → Generate Fixes → Re-review
# ---------------------------------------------------------------------------

@router.post("/auto-fix-loop")
def auto_fix_loop(req: AutoFixLoopRequest):
    """Run the auto-fix loop: review PR → generate fix suggestions → post to PR.

    Flow:
    1. Run AI code review on the PR
    2. For each finding, generate a specific fix suggestion
    3. Post fix suggestions as inline comments on the PR
    4. Return the review + all suggested fixes
    
    The 'max_iterations' parameter controls how many review passes to run
    (each pass focuses on remaining unfixed issues from the previous pass).
    """
    all_iterations: list[dict] = []
    total_tokens = 0
    total_fixes_posted = 0

    for iteration in range(1, req.max_iterations + 1):
        # Step 1: Run review
        review_req = ReviewPRRequest(owner=req.owner, repo=req.repo, pr_number=req.pr_number)
        try:
            review_result = review_pull_request(review_req)
        except HTTPException:
            raise

        total_tokens += review_result.tokens_used

        # If no issues found, we're done
        if review_result.total_issues == 0:
            all_iterations.append({
                "iteration": iteration,
                "action": "clean",
                "total_issues": 0,
                "quality_score": review_result.quality_score,
                "message": "No issues found — code is clean.",
            })
            break

        # Step 2: Generate fix prompt for each finding
        fix_suggestions: list[dict] = []
        for finding in review_result.findings:
            fix = {
                "severity": finding.get("severity", "info"),
                "category": finding.get("category", ""),
                "title": finding.get("title", ""),
                "file": finding.get("file"),
                "line": finding.get("line"),
                "description": finding.get("description", ""),
                "suggestion": finding.get("suggestion", ""),
                "code_snippet": finding.get("code_snippet", ""),
            }
            fix_suggestions.append(fix)

        # Step 3: Post as inline comments if enabled
        posted_count = 0
        if req.auto_comment and post_pr_review_comment:
            # Post summary
            summary = f"## ZECT Auto-Fix Loop — Iteration {iteration}\n\n"
            summary += f"**Quality Score:** {review_result.quality_score}/100\n"
            summary += f"**Issues Found:** {review_result.total_issues}\n\n"
            summary += "### Fix Suggestions\n\n"
            for i, fix in enumerate(fix_suggestions, 1):
                sev_icon = {"critical": "\U0001f6d1", "high": "\u26a0\ufe0f", "medium": "\U0001f4a1", "low": "\u2139\ufe0f"}.get(
                    fix["severity"], "\U0001f4a1"
                )
                summary += f"{i}. {sev_icon} **{fix['title']}**"
                if fix["file"]:
                    summary += f" (`{fix['file']}"
                    if fix["line"]:
                        summary += f":{fix['line']}"
                    summary += "`)"
                summary += f"\n   - {fix['suggestion']}\n\n" if fix["suggestion"] else "\n"

            try:
                post_pr_review_comment(
                    owner=req.owner, repo=req.repo, pr_number=req.pr_number,
                    body=summary,
                )
                posted_count += 1
            except Exception as e:
                logger.warning("Failed to post auto-fix summary: %s", e)

            # Post inline fixes for findings with file/line
            for fix in fix_suggestions:
                if fix["file"] and fix["line"] and fix["suggestion"]:
                    body = f"**ZECT Auto-Fix:** {fix['suggestion']}"
                    if fix["code_snippet"]:
                        body += f"\n\n```suggestion\n{fix['code_snippet']}\n```"
                    try:
                        pr_data = github_service.get_pull(req.owner, req.repo, req.pr_number)
                        from app.github_service import get_github
                        gh = get_github()
                        repo_obj = gh.get_repo(f"{req.owner}/{req.repo}")
                        pr_obj = repo_obj.get_pull(req.pr_number)
                        head_sha = pr_obj.head.sha
                        post_pr_review_comment(
                            owner=req.owner, repo=req.repo, pr_number=req.pr_number,
                            body=body, commit_sha=head_sha,
                            path=fix["file"], line=fix["line"],
                        )
                        posted_count += 1
                    except Exception as e:
                        logger.warning("Failed to post inline fix for %s:%s — %s", fix["file"], fix["line"], e)

        total_fixes_posted += posted_count

        all_iterations.append({
            "iteration": iteration,
            "action": "review_and_fix",
            "total_issues": review_result.total_issues,
            "quality_score": review_result.quality_score,
            "fixes_posted": posted_count,
            "findings": fix_suggestions,
        })

        # If quality is high enough, stop early
        if review_result.quality_score >= 90 and review_result.total_issues <= 2:
            break

    return {
        "owner": req.owner,
        "repo": req.repo,
        "pr_number": req.pr_number,
        "total_iterations": len(all_iterations),
        "total_tokens_used": total_tokens,
        "total_fixes_posted": total_fixes_posted,
        "final_quality_score": all_iterations[-1]["quality_score"] if all_iterations else 0,
        "iterations": all_iterations,
    }


# ---------------------------------------------------------------------------
# GitHub Webhook — Auto-trigger review on new PRs
# ---------------------------------------------------------------------------

# In-memory webhook config store (persists per server restart)
# Production would use the database, but this keeps it simple
_webhook_configs: dict[str, dict] = {}


@router.post("/webhook/configure")
def configure_webhook(req: WebhookConfigRequest):
    """Configure auto-review webhook for a repository.

    When enabled, any incoming GitHub webhook events for pull_request
    (opened/synchronize) will auto-trigger a ZECT code review.
    
    If disabled via this endpoint or via Rules Engine, the auto-review
    stops — this is the kill switch.
    """
    key = f"{req.owner}/{req.repo}"
    _webhook_configs[key] = {
        "owner": req.owner,
        "repo": req.repo,
        "enabled": req.enabled,
        "auto_review": req.auto_review,
        "auto_comment": req.auto_comment,
        "webhook_secret": req.webhook_secret,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"status": "configured", "config": _webhook_configs[key]}


@router.get("/webhook/configure/{owner}/{repo}")
def get_webhook_config(owner: str, repo: str):
    """Get the current webhook configuration for a repository."""
    key = f"{owner}/{repo}"
    if key not in _webhook_configs:
        return {
            "owner": owner,
            "repo": repo,
            "enabled": False,
            "auto_review": False,
            "auto_comment": False,
            "webhook_secret": "",
        }
    return _webhook_configs[key]


@router.get("/webhook/configs")
def list_webhook_configs():
    """List all configured webhook repositories."""
    return list(_webhook_configs.values())


@router.post("/webhook/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive GitHub webhook events and auto-trigger code review.

    Supports pull_request events (opened, synchronize, reopened).
    Checks Rules Engine for auto_review_enabled kill switch.
    If a rule with type='review' and action='block' is active, auto-review is skipped.
    """
    body = await request.body()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type != "pull_request":
        return {"status": "ignored", "reason": f"Event type '{event_type}' not handled"}

    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "reason": f"PR action '{action}' not handled"}

    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    repo_full = payload.get("repository", {}).get("full_name", "")

    if not pr_number or not repo_full:
        raise HTTPException(status_code=400, detail="Missing PR number or repository info")

    parts = repo_full.split("/")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid repository format")

    owner, repo_name = parts[0], parts[1]
    key = f"{owner}/{repo_name}"

    # Check webhook config — kill switch
    config = _webhook_configs.get(key, {})
    if not config.get("enabled", False) or not config.get("auto_review", False):
        return {"status": "skipped", "reason": "Auto-review not enabled for this repo"}

    # Verify signature if secret is configured
    secret = config.get("webhook_secret", "")
    if secret:
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

    # Check Rules Engine kill switch
    block_rules = db.query(Rule).filter(
        Rule.is_active == True,
        Rule.rule_type == "review",
        Rule.action == "block",
    ).all()

    for rule in block_rules:
        # Check if rule applies to this repo
        try:
            if re.search(rule.condition, repo_full, re.IGNORECASE):
                return {
                    "status": "blocked",
                    "reason": f"Rule '{rule.name}' blocks auto-review for this repo",
                    "rule_id": rule.id,
                }
        except re.error:
            pass

    # Run the review
    try:
        review_req = ReviewPRRequest(owner=owner, repo=repo_name, pr_number=pr_number)
        review_result = review_pull_request(review_req)

        posted_comments = []
        if config.get("auto_comment", False) and post_pr_review_comment:
            # Post summary
            summary = f"## ZECT Auto-Review\n\n"
            summary += f"**Triggered by:** PR #{pr_number} {action}\n"
            summary += f"**Quality Score:** {review_result.quality_score}/100\n"
            summary += f"**Issues Found:** {review_result.total_issues}\n\n"
            summary += f"{review_result.summary}\n\n"

            if review_result.findings:
                summary += "### Findings\n\n"
                for f in review_result.findings[:10]:  # Limit to top 10
                    sev_icon = {"critical": "\U0001f6d1", "high": "\u26a0\ufe0f", "medium": "\U0001f4a1", "low": "\u2139\ufe0f"}.get(
                        f.get("severity", ""), "\U0001f4a1"
                    )
                    summary += f"- {sev_icon} **{f.get('title', '')}**"
                    if f.get("file"):
                        summary += f" (`{f['file']}`)"
                    summary += "\n"

            try:
                comment = post_pr_review_comment(
                    owner=owner, repo=repo_name, pr_number=pr_number,
                    body=summary,
                )
                posted_comments.append(comment)
            except Exception as e:
                posted_comments.append({"error": str(e)})

        return {
            "status": "reviewed",
            "pr_number": pr_number,
            "repo": repo_full,
            "quality_score": review_result.quality_score,
            "total_issues": review_result.total_issues,
            "comments_posted": len([c for c in posted_comments if "error" not in c]),
        }

    except Exception as e:
        logger.error("Auto-review failed for PR #%s on %s: %s", pr_number, repo_full, e)
        return {"status": "error", "reason": str(e)}


# ---------------------------------------------------------------------------
# Rules Engine Integration — Evaluate code against active rules
# ---------------------------------------------------------------------------

@router.post("/evaluate-rules")
def evaluate_review_rules(req: ReviewPRRequest, db: Session = Depends(get_db)):
    """Run code review AND evaluate findings against active Rules Engine rules.

    This combines AI code review with regex-based rule evaluation:
    1. First runs AI code review on the PR
    2. Then evaluates all active 'review' rules against the PR diff
    3. Merges results — rule matches become additional findings

    Rules with action='block' will set a 'blocked' flag in the response,
    indicating the PR should not be merged.
    """
    # Step 1: Run AI review
    try:
        review_result = review_pull_request(req)
    except HTTPException:
        raise

    # Step 2: Get PR diff for rule evaluation
    try:
        files_raw = github_service.get_pull_files(req.owner, req.repo, req.pr_number)
        diff_text = "\n".join(f.patch or "" for f in files_raw)
    except Exception:
        diff_text = ""

    # Step 3: Evaluate active review rules
    review_rules = db.query(Rule).filter(
        Rule.is_active == True,
        Rule.rule_type == "review",
    ).all()

    rule_findings: list[dict] = []
    is_blocked = False

    for rule in review_rules:
        try:
            if re.search(rule.condition, diff_text, re.MULTILINE | re.IGNORECASE):
                rule_findings.append({
                    "severity": rule.severity,
                    "category": "best_practices",
                    "title": f"Rule: {rule.name}",
                    "description": rule.description or f"Custom rule '{rule.name}' matched",
                    "file": None,
                    "line": None,
                    "suggestion": f"Action: {rule.action}",
                    "code_snippet": None,
                    "rule_id": rule.id,
                    "rule_action": rule.action,
                })
                if rule.action == "block":
                    is_blocked = True
        except re.error:
            pass

    # Merge findings
    all_findings = list(review_result.findings) + rule_findings

    return {
        "review": review_result.model_dump(),
        "rule_findings": rule_findings,
        "total_rule_matches": len(rule_findings),
        "merged_findings": all_findings,
        "merged_total_issues": review_result.total_issues + len(rule_findings),
        "is_blocked": is_blocked,
        "blocked_by_rules": [rf["title"] for rf in rule_findings if rf.get("rule_action") == "block"],
    }
