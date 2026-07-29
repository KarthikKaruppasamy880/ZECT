import os
from github import Github, GithubException
from app.schemas import (
    GitHubRepoInfo, GitHubPR, GitHubPRFile,
    GitHubCommit, GitHubWorkflowRun,
)

_gh: Github | None = None


def get_github() -> Github:
    global _gh
    token = os.getenv("GITHUB_TOKEN", "")
    if _gh is None and token:
        _gh = Github(token)
    elif _gh is None:
        _gh = Github()  # unauthenticated (60 req/hr)
    return _gh


def list_org_repos(org: str, limit: int = 30) -> list[GitHubRepoInfo]:
    gh = get_github()
    try:
        organization = gh.get_organization(org)
        repos = organization.get_repos(sort="updated", direction="desc")
    except GithubException:
        user = gh.get_user(org)
        repos = user.get_repos(sort="updated", direction="desc")

    result: list[GitHubRepoInfo] = []
    for repo in repos[:limit]:
        result.append(GitHubRepoInfo(
            full_name=repo.full_name,
            name=repo.name,
            owner=repo.owner.login,
            description=repo.description,
            language=repo.language,
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            open_issues=repo.open_issues_count,
            default_branch=repo.default_branch,
            updated_at=repo.updated_at.isoformat() if repo.updated_at else "",
            html_url=repo.html_url,
            private=repo.private,
        ))
    return result


def get_repo_info(owner: str, repo_name: str) -> GitHubRepoInfo:
    gh = get_github()
    repo = gh.get_repo(f"{owner}/{repo_name}")
    return GitHubRepoInfo(
        full_name=repo.full_name,
        name=repo.name,
        owner=repo.owner.login,
        description=repo.description,
        language=repo.language,
        stars=repo.stargazers_count,
        forks=repo.forks_count,
        open_issues=repo.open_issues_count,
        default_branch=repo.default_branch,
        updated_at=repo.updated_at.isoformat() if repo.updated_at else "",
        html_url=repo.html_url,
        private=repo.private,
    )


def list_pulls(owner: str, repo_name: str, state: str = "all", limit: int = 20) -> list[GitHubPR]:
    gh = get_github()
    repo = gh.get_repo(f"{owner}/{repo_name}")
    pulls = repo.get_pulls(state=state, sort="updated", direction="desc")
    result: list[GitHubPR] = []
    for pr in pulls[:limit]:
        result.append(GitHubPR(
            number=pr.number,
            title=pr.title,
            state=pr.state if not pr.merged else "merged",
            author=pr.user.login if pr.user else "unknown",
            created_at=pr.created_at.isoformat() if pr.created_at else "",
            updated_at=pr.updated_at.isoformat() if pr.updated_at else "",
            merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
            additions=pr.additions,
            deletions=pr.deletions,
            changed_files=pr.changed_files,
            html_url=pr.html_url,
            head_branch=pr.head.ref,
            base_branch=pr.base.ref,
            body=pr.body,
        ))
    return result


def get_pull(owner: str, repo_name: str, number: int) -> GitHubPR:
    gh = get_github()
    repo = gh.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(number)
    return GitHubPR(
        number=pr.number,
        title=pr.title,
        state=pr.state if not pr.merged else "merged",
        author=pr.user.login if pr.user else "unknown",
        created_at=pr.created_at.isoformat() if pr.created_at else "",
        updated_at=pr.updated_at.isoformat() if pr.updated_at else "",
        merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
        additions=pr.additions,
        deletions=pr.deletions,
        changed_files=pr.changed_files,
        html_url=pr.html_url,
        head_branch=pr.head.ref,
        base_branch=pr.base.ref,
        body=pr.body,
    )


def get_pull_files(owner: str, repo_name: str, number: int) -> list[GitHubPRFile]:
    gh = get_github()
    repo = gh.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(number)
    files = pr.get_files()
    result: list[GitHubPRFile] = []
    for f in files:
        result.append(GitHubPRFile(
            filename=f.filename,
            status=f.status,
            additions=f.additions,
            deletions=f.deletions,
            changes=f.changes,
            patch=f.patch,
        ))
    return result


def list_commits(owner: str, repo_name: str, limit: int = 20) -> list[GitHubCommit]:
    gh = get_github()
    repo = gh.get_repo(f"{owner}/{repo_name}")
    commits = repo.get_commits()
    result: list[GitHubCommit] = []
    for c in commits[:limit]:
        result.append(GitHubCommit(
            sha=c.sha,
            message=c.commit.message,
            author=c.commit.author.name if c.commit.author else "unknown",
            date=c.commit.author.date.isoformat() if c.commit.author and c.commit.author.date else "",
            html_url=c.html_url,
            additions=c.stats.additions if c.stats else 0,
            deletions=c.stats.deletions if c.stats else 0,
            files_changed=c.stats.total if c.stats else 0,
        ))
    return result


def _get_github() -> Github:
    """Internal accessor for raw Github client (used by CI monitor etc.)."""
    return get_github()


def create_pull_request(owner: str, repo: str, title: str, body: str, head: str, base: str) -> dict:
    """Create a pull request on GitHub."""
    gh = get_github()
    repo_obj = gh.get_repo(f"{owner}/{repo}")
    pr = repo_obj.create_pull(title=title, body=body, head=head, base=base)
    return {
        "number": pr.number,
        "html_url": pr.html_url,
        "title": pr.title,
        "state": pr.state,
    }


def _sast_name_patterns() -> list[str]:
    import fnmatch
    import os

    raw = os.getenv("MENTRIX_SAST_CHECK_NAMES", "Semgrep*,semgrep*,*semgrep*")
    return [p.strip() for p in raw.split(",") if p.strip()]


def sast_required() -> bool:
    import os

    return os.getenv("MENTRIX_SAST_REQUIRED", "").lower() in ("1", "true", "yes")


def list_check_runs(owner: str, repo: str, ref: str) -> list[dict]:
    """List GitHub Check Runs for a commit SHA or branch ref."""
    gh = get_github()
    repo_obj = gh.get_repo(f"{owner}/{repo}")
    runs = repo_obj.get_commit(ref).get_check_runs()
    out: list[dict] = []
    for c in runs:
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "conclusion": c.conclusion,
                "html_url": getattr(c, "html_url", None),
                "app": getattr(getattr(c, "app", None), "slug", None)
                or getattr(getattr(c, "app", None), "name", None),
            }
        )
    return out


def sast_checks_ok(owner: str, repo: str, ref: str) -> dict:
    """Evaluate Semgrep / SAST check runs (scanSuccessful ≈ conclusion success)."""
    import fnmatch

    patterns = _sast_name_patterns()
    try:
        checks = list_check_runs(owner, repo, ref)
    except Exception as e:
        return {
            "ok": False,
            "required": sast_required(),
            "matched": [],
            "error": str(e)[:300],
            "note": "Failed to list GitHub check runs",
        }

    matched = []
    for c in checks:
        name = c.get("name") or ""
        app = str(c.get("app") or "")
        if any(fnmatch.fnmatch(name, p) or fnmatch.fnmatch(app, p) for p in patterns):
            matched.append(c)
        elif "semgrep" in name.lower() or "semgrep" in app.lower():
            matched.append(c)

    if not matched:
        return {
            "ok": False if sast_required() else True,
            "required": sast_required(),
            "matched": [],
            "note": "No Semgrep/SAST check runs found for this ref",
        }

    # Prefer completed success (Semgrep Cloud scanSuccessful)
    successes = [c for c in matched if c.get("conclusion") == "success"]
    pending = [c for c in matched if c.get("status") != "completed"]
    failures = [
        c
        for c in matched
        if c.get("status") == "completed" and c.get("conclusion") not in ("success", "neutral", "skipped")
    ]
    ok = bool(successes) and not failures and not pending
    if pending and not failures:
        ok = False
    return {
        "ok": ok,
        "required": sast_required(),
        "matched": matched,
        "pending": len(pending) > 0,
        "note": "Semgrep check success" if ok else "SAST not green yet",
    }


def create_check_run(
    owner: str,
    repo: str,
    name: str,
    head_sha: str,
    conclusion: str,
    title: str,
    summary: str,
    details_url: str | None = None,
) -> dict:
    """Create a GitHub Check Run for Mentrix / ZECT review status."""
    gh = get_github()
    repo_obj = gh.get_repo(f"{owner}/{repo}")
    output = {"title": title, "summary": summary}
    kwargs: dict = {
        "name": name,
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": output,
    }
    if details_url:
        kwargs["details_url"] = details_url
    check = repo_obj.create_check_run(**kwargs)
    return {
        "id": check.id,
        "name": check.name,
        "conclusion": check.conclusion,
        "html_url": getattr(check, "html_url", None),
    }


def post_pr_review_comment(owner: str, repo: str, pr_number: int, body: str, commit_sha: str | None = None, path: str | None = None, line: int | None = None) -> dict:
    """Post a review comment on a PR (inline or general)."""
    gh = get_github()
    repo_obj = gh.get_repo(f"{owner}/{repo}")
    pr = repo_obj.get_pull(pr_number)

    if path and line and commit_sha:
        # Inline comment on a specific file/line
        commit = repo_obj.get_commit(commit_sha)
        comment = pr.create_review_comment(body=body, commit=commit, path=path, line=line)
        return {"id": comment.id, "body": comment.body, "path": path, "line": line, "type": "inline"}
    else:
        # General PR comment
        comment = pr.create_issue_comment(body=body)
        return {"id": comment.id, "body": comment.body, "type": "general"}


def get_pr_review_comments(owner: str, repo: str, pr_number: int) -> list[dict]:
    """Get all review comments on a PR."""
    gh = get_github()
    repo_obj = gh.get_repo(f"{owner}/{repo}")
    pr = repo_obj.get_pull(pr_number)

    comments = []
    # Get general comments
    for c in pr.get_issue_comments():
        comments.append({
            "id": c.id,
            "body": c.body,
            "author": c.user.login if c.user else "unknown",
            "created_at": c.created_at.isoformat() if c.created_at else "",
            "type": "general",
        })
    # Get inline review comments
    for c in pr.get_review_comments():
        comments.append({
            "id": c.id,
            "body": c.body,
            "author": c.user.login if c.user else "unknown",
            "path": c.path,
            "line": c.line,
            "created_at": c.created_at.isoformat() if c.created_at else "",
            "type": "inline",
        })
    return comments


def list_workflow_runs(owner: str, repo_name: str, limit: int = 10) -> list[GitHubWorkflowRun]:
    gh = get_github()
    repo = gh.get_repo(f"{owner}/{repo_name}")
    try:
        runs = repo.get_workflow_runs()
        result: list[GitHubWorkflowRun] = []
        for run in runs[:limit]:
            result.append(GitHubWorkflowRun(
                id=run.id,
                name=run.name or "",
                status=run.status or "",
                conclusion=run.conclusion,
                head_branch=run.head_branch or "",
                event=run.event or "",
                created_at=run.created_at.isoformat() if run.created_at else "",
                updated_at=run.updated_at.isoformat() if run.updated_at else "",
                html_url=run.html_url or "",
            ))
        return result
    except GithubException:
        return []


def trigger_workflow_dispatch(
    owner: str, repo_name: str, workflow_file: str, ref: str = "main", inputs: dict | None = None
) -> dict:
    """Fire a real workflow_dispatch run — the actual CI/CD trigger; nothing
    else in this module does more than read Actions status."""
    gh = get_github()
    repo = gh.get_repo(f"{owner}/{repo_name}")
    workflow = repo.get_workflow(workflow_file)
    ok = workflow.create_dispatch(ref, inputs or {})
    if not ok:
        raise GithubException(502, f"workflow_dispatch rejected for {workflow_file}@{ref}", None)
    return {
        "dispatched": True,
        "workflow": workflow_file,
        "ref": ref,
        "message": f"Dispatched {workflow_file} on {ref}",
    }
