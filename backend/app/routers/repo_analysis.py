"""Repo analysis and blueprint generation endpoints.

Fetches repository structure, README, dependencies, and architecture
from GitHub, then synthesizes a single copy-paste prompt for AI tools.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Setting, TokenLog
from app import github_service
from app.token_tracker import log_tokens as _persist_tokens, get_usage_summary
from github import GithubException
import json
import os
import time

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _log_tokens(action: str, tokens: int):
    """Log token usage to the database."""
    _persist_tokens(
        action=action,
        feature="repo_analysis" if "analysis" in action else "blueprint" if "blueprint" in action else "doc_gen",
        model="github-api",
        total_tokens=tokens,
    )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RepoAnalysisRequest(BaseModel):
    owner: str
    repo: str


class MultiRepoAnalysisRequest(BaseModel):
    repos: list[RepoAnalysisRequest]


class RepoAnalysisResult(BaseModel):
    owner: str
    repo: str
    full_name: str
    description: str | None
    language: str | None
    default_branch: str
    stars: int
    forks: int
    open_issues: int
    tree: list[str]
    readme_content: str | None
    dependencies: dict[str, list[str]]
    architecture_notes: list[str]


class BlueprintResult(BaseModel):
    prompt: str
    token_estimate: int
    repos_analyzed: int


class TokenLogEntry(BaseModel):
    action: str
    tokens: int
    ts: float


class TokenUsage(BaseModel):
    total_tokens: int
    log: list[TokenLogEntry]


class ApiKeyConfig(BaseModel):
    github_token: str


class ApiKeyStatus(BaseModel):
    configured: bool
    scopes: list[str]
    rate_limit_remaining: int
    rate_limit_total: int


# ---------------------------------------------------------------------------
# Helper – analyse a single repo via GitHub API
# ---------------------------------------------------------------------------

def _analyze_repo(owner: str, repo: str) -> RepoAnalysisResult:
    gh = github_service.get_github()
    try:
        r = gh.get_repo(f"{owner}/{repo}")
    except GithubException as e:
        if e.status == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Repository '{owner}/{repo}' not found. Check the owner/repo name. For private repos, configure a GitHub token in Settings.",
            )
        if e.status == 403:
            raise HTTPException(
                status_code=403,
                detail="GitHub API rate limit exceeded. Configure a GitHub Personal Access Token in Settings to increase the limit.",
            )
        raise HTTPException(status_code=e.status, detail=str(e.data))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to GitHub API: {str(e)}. Check your network connection and try again.",
        )

    # Fetch top-level tree (limit depth to 2 for speed)
    tree_items: list[str] = []
    try:
        tree = r.get_git_tree(r.default_branch, recursive=True)
        for item in tree.tree[:300]:  # cap for large repos
            tree_items.append(item.path)
    except GithubException:
        pass

    # Fetch README
    readme: str | None = None
    try:
        content = r.get_readme()
        readme = content.decoded_content.decode("utf-8", errors="replace")[:8000]
    except GithubException:
        pass

    # Detect dependencies from well-known files
    deps: dict[str, list[str]] = {}
    dep_files = {
        "package.json": "npm",
        "requirements.txt": "pip",
        "pyproject.toml": "poetry/pip",
        "Cargo.toml": "cargo",
        "go.mod": "go",
        "Gemfile": "bundler",
        "pom.xml": "maven",
        "build.gradle": "gradle",
    }
    for fname, mgr in dep_files.items():
        if fname in tree_items:
            try:
                fc = r.get_contents(fname)
                if not isinstance(fc, list):
                    raw = fc.decoded_content.decode("utf-8", errors="replace")
                    if mgr == "npm":
                        try:
                            pkg = json.loads(raw)
                            all_deps = list((pkg.get("dependencies") or {}).keys()) + list((pkg.get("devDependencies") or {}).keys())
                            deps[mgr] = all_deps[:50]
                        except json.JSONDecodeError:
                            deps[mgr] = [f"(parse error in {fname})"]
                    else:
                        lines = [l.strip() for l in raw[:4000].split("\n") if l.strip() and not l.strip().startswith("#")]
                        deps[mgr] = lines[:50]
            except GithubException:
                pass

    # Architecture notes (inferred from tree)
    arch_notes: list[str] = []
    if any("src/" in p for p in tree_items):
        arch_notes.append("Source code in src/ directory")
    if any("app/" in p for p in tree_items):
        arch_notes.append("Application code in app/ directory")
    if any("test" in p.lower() for p in tree_items):
        arch_notes.append("Test files detected")
    if any("docker" in p.lower() for p in tree_items):
        arch_notes.append("Docker configuration present")
    if any(".github/workflows" in p for p in tree_items):
        arch_notes.append("GitHub Actions CI/CD workflows configured")
    if any("api" in p.lower() for p in tree_items[:50]):
        arch_notes.append("API layer detected")
    if r.language:
        arch_notes.append(f"Primary language: {r.language}")

    _log_tokens("repo_analysis", len(tree_items) + (len(readme) // 4 if readme else 0))

    return RepoAnalysisResult(
        owner=owner,
        repo=repo,
        full_name=r.full_name,
        description=r.description,
        language=r.language,
        default_branch=r.default_branch,
        stars=r.stargazers_count,
        forks=r.forks_count,
        open_issues=r.open_issues_count,
        tree=tree_items,
        readme_content=readme,
        dependencies=deps,
        architecture_notes=arch_notes,
    )


def _build_prompt(analyses: list[RepoAnalysisResult]) -> str:
    """Synthesise a single vibe-coding prompt from analysis results.

    Generates a conversational, outcome-focused prompt (not a technical spec)
    that can be pasted into any AI coding tool to recreate/extend the project.
    """
    sections: list[str] = []

    # Conversational intro
    if len(analyses) == 1:
        a = analyses[0]
        desc = a.description or "a software project"
        lang = f" built with {a.language}" if a.language else ""
        sections.append(
            f"I want to build a project like {a.full_name} — {desc}{lang}. "
            f"Here is everything you need to know about the original repository "
            f"so you can recreate it from scratch with the same architecture, "
            f"patterns, and quality."
        )
    else:
        names = ", ".join(a.full_name for a in analyses)
        sections.append(
            f"I want to build a project that combines patterns from these "
            f"repositories: {names}. Below is a detailed analysis of each repo. "
            f"Use this context to create a unified project that incorporates "
            f"the best architecture and patterns from all of them."
        )
    sections.append("")

    for a in analyses:
        sections.append(f"## Repository: {a.full_name}")
        if a.description:
            sections.append(f"**Description:** {a.description}")
        if a.language:
            sections.append(f"**Primary Language:** {a.language}")
        sections.append(f"**Default Branch:** {a.default_branch}")
        sections.append(f"**Stars:** {a.stars} | **Forks:** {a.forks}")
        sections.append("")

        # Architecture
        if a.architecture_notes:
            sections.append("### Architecture Notes")
            for n in a.architecture_notes:
                sections.append(f"- {n}")
            sections.append("")

        # Dependencies
        if a.dependencies:
            sections.append("### Dependencies")
            for mgr, pkgs in a.dependencies.items():
                sections.append(f"**{mgr}:** {', '.join(pkgs[:20])}")
            sections.append("")

        # File structure (top 80)
        sections.append("### File Structure")
        sections.append("```")
        for path in a.tree[:80]:
            sections.append(path)
        if len(a.tree) > 80:
            sections.append(f"... and {len(a.tree) - 80} more files")
        sections.append("```")
        sections.append("")

        # README excerpt
        if a.readme_content:
            sections.append("### README (excerpt)")
            sections.append("```markdown")
            sections.append(a.readme_content[:4000])
            sections.append("```")
            sections.append("")

    sections.append("---")
    sections.append("")
    sections.append("## What I Need You To Do")
    sections.append("")
    sections.append("Using the repository analysis above:")
    sections.append("1. Recreate the full project structure following the file layout shown")
    sections.append("2. Install all listed dependencies using the correct package manager")
    sections.append("3. Implement the core architecture as described in the architecture notes")
    sections.append("4. Follow the patterns and conventions visible in the file structure")
    sections.append("5. Ensure the project builds, lints cleanly, and all tests pass")
    sections.append("6. Match the README description, goals, and feature set")
    sections.append("7. Use production-quality code — proper error handling, types, and documentation")
    sections.append("")
    sections.append("Start with the project scaffold, then implement each module. Ask me if anything is unclear.")

    return "\n".join(sections)


def _build_focused_prompt(analysis: RepoAnalysisResult, focus_area: str, goal: str) -> str:
    """Build a prompt focused on a specific area of a repository."""
    sections: list[str] = []

    # Filter tree items related to the focus area
    focus_lower = focus_area.lower()
    relevant_files = [
        p for p in analysis.tree
        if any(kw in p.lower() for kw in focus_lower.split())
    ]

    sections.append(
        f"I want to {goal} the **{focus_area}** part of the {analysis.full_name} repository. "
        f"Here is the relevant context from the repo so you can help me."
    )
    sections.append("")
    sections.append(f"## Repository: {analysis.full_name}")
    if analysis.description:
        sections.append(f"**Description:** {analysis.description}")
    if analysis.language:
        sections.append(f"**Primary Language:** {analysis.language}")
    sections.append("")

    # Architecture notes
    if analysis.architecture_notes:
        sections.append("### Architecture Context")
        for n in analysis.architecture_notes:
            sections.append(f"- {n}")
        sections.append("")

    # Relevant files
    if relevant_files:
        sections.append(f"### Files Related to \"{focus_area}\"")
        sections.append("```")
        for path in relevant_files[:50]:
            sections.append(path)
        sections.append("```")
        sections.append("")

    # Full tree for context
    sections.append("### Full File Structure (for context)")
    sections.append("```")
    for path in analysis.tree[:60]:
        sections.append(path)
    if len(analysis.tree) > 60:
        sections.append(f"... and {len(analysis.tree) - 60} more files")
    sections.append("```")
    sections.append("")

    # Dependencies
    if analysis.dependencies:
        sections.append("### Dependencies")
        for mgr, pkgs in analysis.dependencies.items():
            sections.append(f"**{mgr}:** {', '.join(pkgs[:20])}")
        sections.append("")

    # README excerpt
    if analysis.readme_content:
        sections.append("### README (excerpt)")
        sections.append("```markdown")
        sections.append(analysis.readme_content[:3000])
        sections.append("```")
        sections.append("")

    sections.append("---")
    sections.append("")
    sections.append(f"## Focus: {focus_area}")
    sections.append("")
    sections.append(f"My goal is to **{goal}** the {focus_area} functionality from this repo.")
    sections.append("Please:")
    sections.append(f"1. Explain how the {focus_area} is implemented in this codebase")
    sections.append("2. Identify the key files and patterns used")
    sections.append("3. Provide a step-by-step plan to implement this in my project")
    sections.append("4. Include any gotchas, edge cases, or best practices to follow")
    sections.append("")
    sections.append("Be specific and reference the actual file structure shown above.")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/repo", response_model=RepoAnalysisResult)
def analyze_single_repo(req: RepoAnalysisRequest):
    """Analyze a single GitHub repository."""
    return _analyze_repo(req.owner, req.repo)


@router.post("/multi-repo", response_model=list[RepoAnalysisResult])
def analyze_multiple_repos(req: MultiRepoAnalysisRequest):
    """Analyze multiple GitHub repositories."""
    results = []
    for r in req.repos:
        results.append(_analyze_repo(r.owner, r.repo))
    return results


@router.post("/blueprint", response_model=BlueprintResult)
def generate_blueprint(req: MultiRepoAnalysisRequest):
    """Analyze repos and generate a single synthetic prompt for AI tools."""
    analyses = [_analyze_repo(r.owner, r.repo) for r in req.repos]
    prompt = _build_prompt(analyses)
    token_est = len(prompt) // 4  # rough token estimate
    _log_tokens("blueprint_generation", token_est)
    return BlueprintResult(
        prompt=prompt,
        token_estimate=token_est,
        repos_analyzed=len(analyses),
    )


class FocusedBlueprintRequest(BaseModel):
    owner: str
    repo: str
    focus_area: str  # e.g. "authentication", "API layer", "database schema"
    goal: str = "understand and replicate"  # what the user wants to do


class FocusedBlueprintResult(BaseModel):
    prompt: str
    token_estimate: int
    focus_area: str
    repo_name: str


@router.post("/blueprint/focused", response_model=FocusedBlueprintResult)
def generate_focused_blueprint(req: FocusedBlueprintRequest):
    """Generate a prompt focused on a specific area of a repository.

    Unlike the standard blueprint which covers the full repo,
    focused mode scopes the output to a particular feature or layer
    (e.g. 'authentication', 'API routes', 'database schema').
    """
    analysis = _analyze_repo(req.owner, req.repo)
    prompt = _build_focused_prompt(analysis, req.focus_area, req.goal)
    token_est = len(prompt) // 4
    _log_tokens("focused_blueprint", token_est)
    return FocusedBlueprintResult(
        prompt=prompt,
        token_estimate=token_est,
        focus_area=req.focus_area,
        repo_name=analysis.full_name,
    )


@router.get("/tokens", response_model=TokenUsage)
def get_token_usage(db: Session = Depends(get_db)):
    """Get token usage log from the database."""
    logs = db.query(TokenLog).order_by(TokenLog.created_at.desc()).limit(100).all()
    total = sum(l.total_tokens for l in logs)
    log_entries = [
        {"action": l.action, "tokens": l.total_tokens, "ts": l.created_at.timestamp() if l.created_at else 0}
        for l in logs
    ]
    return TokenUsage(total_tokens=total, log=log_entries)


@router.post("/api-key", response_model=ApiKeyStatus)
def configure_api_key(config: ApiKeyConfig):
    """Configure GitHub API token at runtime."""
    from github import Github
    try:
        gh = Github(config.github_token)
        user = gh.get_user()
        _ = user.login  # force auth check
        rate = gh.get_rate_limit().core
        # Update the global github instance
        github_service._gh = gh
        # Persist to environment
        os.environ["GITHUB_TOKEN"] = config.github_token
        return ApiKeyStatus(
            configured=True,
            scopes=list(gh.oauth_scopes or []),
            rate_limit_remaining=rate.remaining,
            rate_limit_total=rate.limit,
        )
    except GithubException as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e.data}")


class DocGenRequest(BaseModel):
    owner: str
    repo: str
    sections: list[str] = ["overview", "architecture", "api", "setup", "testing", "deployment"]


class DocSection(BaseModel):
    title: str
    content: str


class DocGenResult(BaseModel):
    repo_name: str
    sections: list[DocSection]
    total_tokens: int


@router.post("/docs/generate", response_model=DocGenResult)
def generate_documentation(req: DocGenRequest):
    """Generate granular documentation for a repository."""
    analysis = _analyze_repo(req.owner, req.repo)

    doc_sections: list[DocSection] = []
    for section_key in req.sections:
        title, content = _generate_doc_section(section_key, analysis)
        doc_sections.append(DocSection(title=title, content=content))

    total = sum(len(s.content) // 4 for s in doc_sections)
    _log_tokens("doc_generation", total)

    return DocGenResult(
        repo_name=analysis.full_name,
        sections=doc_sections,
        total_tokens=total,
    )


def _generate_doc_section(key: str, analysis: RepoAnalysisResult) -> tuple[str, str]:
    """Generate a documentation section from repo analysis data."""
    if key == "overview":
        lines = [f"# {analysis.full_name}", ""]
        lines.append(analysis.description or "No description available.")
        lines.append("")
        if analysis.language:
            lines.append(f"**Primary Language:** {analysis.language}")
        lines.append(f"**Default Branch:** {analysis.default_branch}")
        lines.append(f"**Stars:** {analysis.stars} | **Forks:** {analysis.forks} | **Open Issues:** {analysis.open_issues}")
        return "Overview", "\n".join(lines)

    elif key == "architecture":
        lines = ["# Architecture", ""]
        if analysis.architecture_notes:
            for note in analysis.architecture_notes:
                lines.append(f"- {note}")
        else:
            lines.append("No architecture notes detected from file structure.")
        lines.append("")
        lines.append("## Key Directories")
        dirs = sorted(set(p.split("/")[0] for p in analysis.tree if "/" in p))[:20]
        for d in dirs:
            count = sum(1 for p in analysis.tree if p.startswith(d + "/"))
            lines.append(f"- `{d}/` ({count} files)")
        return "Architecture", "\n".join(lines)

    elif key == "api":
        lines = ["# API Reference", ""]
        api_files = [p for p in analysis.tree if any(kw in p.lower() for kw in ["route", "api", "endpoint", "controller", "handler", "view"])]
        if api_files:
            lines.append("## Detected API Files")
            for f in api_files[:30]:
                lines.append(f"- `{f}`")
        else:
            lines.append("No API files detected. Check routes/controllers manually.")
        return "API Reference", "\n".join(lines)

    elif key == "setup":
        lines = ["# Setup Guide", ""]
        lines.append("## Prerequisites")
        if analysis.dependencies:
            for mgr in analysis.dependencies:
                lines.append(f"- {mgr} package manager")
        lines.append("")
        lines.append("## Installation")
        lines.append("```bash")
        lines.append(f"git clone https://github.com/{analysis.full_name}.git")
        lines.append(f"cd {analysis.repo}")
        if "npm" in analysis.dependencies:
            lines.append("npm install")
        if "pip" in analysis.dependencies:
            lines.append("pip install -r requirements.txt")
        if "poetry/pip" in analysis.dependencies:
            lines.append("poetry install")
        if "cargo" in analysis.dependencies:
            lines.append("cargo build")
        if "go" in analysis.dependencies:
            lines.append("go mod download")
        lines.append("```")
        return "Setup Guide", "\n".join(lines)

    elif key == "testing":
        lines = ["# Testing", ""]
        test_files = [p for p in analysis.tree if "test" in p.lower() or "spec" in p.lower()]
        if test_files:
            lines.append(f"## Test Files ({len(test_files)} detected)")
            for f in test_files[:20]:
                lines.append(f"- `{f}`")
        else:
            lines.append("No test files detected.")
        lines.append("")
        lines.append("## Running Tests")
        lines.append("```bash")
        if "npm" in analysis.dependencies:
            lines.append("npm test")
        if "pip" in analysis.dependencies or "poetry/pip" in analysis.dependencies:
            lines.append("pytest")
        if "cargo" in analysis.dependencies:
            lines.append("cargo test")
        if "go" in analysis.dependencies:
            lines.append("go test ./...")
        lines.append("```")
        return "Testing", "\n".join(lines)

    elif key == "deployment":
        lines = ["# Deployment", ""]
        has_docker = any("docker" in p.lower() for p in analysis.tree)
        has_ci = any(".github/workflows" in p for p in analysis.tree)
        if has_docker:
            lines.append("## Docker")
            docker_files = [p for p in analysis.tree if "docker" in p.lower()]
            for f in docker_files:
                lines.append(f"- `{f}`")
        if has_ci:
            lines.append("## CI/CD")
            ci_files = [p for p in analysis.tree if ".github/workflows" in p]
            for f in ci_files:
                lines.append(f"- `{f}`")
        if not has_docker and not has_ci:
            lines.append("No Docker or CI/CD configuration detected.")
        return "Deployment", "\n".join(lines)

    else:
        return key.title(), f"Documentation section '{key}' — content would be generated from repo analysis."


@router.get("/api-key/status", response_model=ApiKeyStatus)
def get_api_key_status():
    """Check current GitHub API key status."""
    gh = github_service.get_github()
    try:
        rate = gh.get_rate_limit().core
        token = os.getenv("GITHUB_TOKEN", "")
        return ApiKeyStatus(
            configured=bool(token),
            scopes=list(gh.oauth_scopes or []) if token else [],
            rate_limit_remaining=rate.remaining,
            rate_limit_total=rate.limit,
        )
    except GithubException:
        return ApiKeyStatus(
            configured=False,
            scopes=[],
            rate_limit_remaining=0,
            rate_limit_total=60,
        )
