"""Phase 4 Stage D — approval gate for GitHub posting + fix-run goal builder.

In-memory approval records avoid SQLite migration risk. Process restart clears
pending approvals (safe: human must re-approve before post).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
# session_id -> {finding_ids: list[int], approved_at: str, approved_by: str|None, owner, repo, pr_number}
_APPROVALS: dict[int, dict[str, Any]] = {}


def approve_post(
    session_id: int,
    finding_ids: list[int],
    *,
    approved_by: str | None = None,
    owner: str | None = None,
    repo: str | None = None,
    pr_number: int | None = None,
) -> dict[str, Any]:
    if not finding_ids:
        raise ValueError("finding_ids required — select at least one finding to approve for post/fix")
    record = {
        "finding_ids": sorted({int(i) for i in finding_ids}),
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approved_by": approved_by,
        "owner": owner,
        "repo": repo,
        "pr_number": pr_number,
    }
    with _lock:
        _APPROVALS[session_id] = record
    return {"session_id": session_id, **record}


def get_approval(session_id: int) -> dict[str, Any] | None:
    with _lock:
        rec = _APPROVALS.get(session_id)
        return dict(rec) if rec else None


def require_approval(session_id: int) -> dict[str, Any]:
    rec = get_approval(session_id)
    if not rec:
        raise PermissionError(
            "Post/fix-run requires approval first "
            "(POST /api/ultrareview/{session_id}/approve-post)"
        )
    return rec


def clear_approval(session_id: int) -> None:
    with _lock:
        _APPROVALS.pop(session_id, None)


def build_fix_goal_from_findings(findings: list[Any], *, repo: str | None = None, pr_number: int | None = None) -> str:
    """Reuse CodeReview fix-prompt style for Mentrix bugfix goal."""
    lines = [
        "# ZECT Code Review — Accepted findings fix run",
        "",
    ]
    if repo:
        lines.append(f"**Repository:** {repo}")
    if pr_number:
        lines.append(f"**PR:** #{pr_number}")
    lines.append("Fix the following accepted review findings. Do not invent unrelated changes.")
    lines.append("")
    for i, f in enumerate(findings, start=1):
        title = getattr(f, "title", None) or (f.get("title") if isinstance(f, dict) else "Issue")
        sev = getattr(f, "severity", None) or (f.get("severity") if isinstance(f, dict) else "info")
        path = getattr(f, "file_path", None) or getattr(f, "file", None)
        if path is None and isinstance(f, dict):
            path = f.get("file_path") or f.get("file")
        line = getattr(f, "line_start", None) or getattr(f, "start_line", None)
        if line is None and isinstance(f, dict):
            line = f.get("line_start") or f.get("start_line") or f.get("line")
        desc = getattr(f, "description", None) or getattr(f, "explanation", None)
        if desc is None and isinstance(f, dict):
            desc = f.get("description") or f.get("explanation") or ""
        sug = getattr(f, "suggestion", None) or getattr(f, "suggested_fix", None)
        if sug is None and isinstance(f, dict):
            sug = f.get("suggestion") or f.get("suggested_fix")
        lines.append(f"## {i}. [{sev}] {title}")
        if path:
            lines.append(f"- File: `{path}`" + (f":{line}" if line else ""))
        if desc:
            lines.append(f"- Detail: {desc}")
        if sug:
            lines.append(f"- Suggestion: {sug}")
        lines.append("")
    return "\n".join(lines).strip()


def post_findings_to_github(
    *,
    owner: str,
    repo: str,
    pr_number: int,
    findings: list[dict[str, Any]],
    summary: str = "",
    quality_score: float | int | None = None,
) -> list[dict[str, Any]]:
    """Reuse github_service.post_pr_review_comment — no parallel poster."""
    from app.github_service import post_pr_review_comment, get_github

    posted: list[dict[str, Any]] = []
    summary_body = "## ZECT AI Code Review (approved findings)\n\n"
    if quality_score is not None:
        summary_body += f"**Quality Score: {quality_score}/100**\n\n"
    if summary:
        summary_body += f"{summary}\n\n"
    summary_body += f"**Approved issues posted:** {len(findings)}\n"
    try:
        posted.append(
            post_pr_review_comment(owner=owner, repo=repo, pr_number=pr_number, body=summary_body)
            or {"ok": True, "type": "summary"}
        )
    except Exception as e:
        posted.append({"error": str(e), "type": "summary"})

    head_sha = None
    try:
        gh = get_github()
        pr_obj = gh.get_repo(f"{owner}/{repo}").get_pull(pr_number)
        head_sha = pr_obj.head.sha
    except Exception:
        head_sha = None

    for finding in findings:
        path = finding.get("file") or finding.get("file_path")
        line = finding.get("line") or finding.get("line_start") or finding.get("start_line")
        if not path or not line:
            continue
        sev = (finding.get("severity") or "info").lower()
        icon = {"critical": "\U0001f6d1", "high": "\u26a0\ufe0f", "medium": "\U0001f4a1", "low": "\u2139\ufe0f"}.get(
            sev, "\U0001f4a1"
        )
        body = f"{icon} **{sev.upper()}: {finding.get('title', 'Issue')}**\n\n"
        body += f"{finding.get('description') or finding.get('explanation') or ''}\n\n"
        if finding.get("suggestion") or finding.get("suggested_fix"):
            body += f"**Suggestion:** {finding.get('suggestion') or finding.get('suggested_fix')}\n"
        try:
            posted.append(
                post_pr_review_comment(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    body=body,
                    commit_sha=head_sha,
                    path=path,
                    line=int(line),
                )
                or {"ok": True, "file": path, "line": line}
            )
        except Exception as e:
            posted.append({"error": str(e), "file": path, "type": "inline"})
    return posted
