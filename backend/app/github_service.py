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
            files_changed=len(c.files) if c.files else 0,
        ))
    return result


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
