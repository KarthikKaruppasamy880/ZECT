"""CI/CD Monitor API — poll GitHub Actions, detect failures, suggest AI fixes.

Closes the "CI/CD Monitoring" gap vs Devin: ZECT can now monitor CI
pipelines and suggest AI-powered fixes for failures.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/ci", tags=["ci-monitor"])


# ── Models ────────────────────────────────────────────────────────────────

class CIRunSummary(BaseModel):
    id: int
    name: str
    status: str  # queued, in_progress, completed
    conclusion: str | None  # success, failure, cancelled, skipped, etc.
    branch: str
    commit_sha: str
    commit_message: str
    html_url: str
    created_at: str
    updated_at: str
    run_number: int


class CIJobDetail(BaseModel):
    id: int
    name: str
    status: str
    conclusion: str | None
    started_at: str | None
    completed_at: str | None
    steps: list[dict]


class CIFixSuggestion(BaseModel):
    error_summary: str
    root_cause: str
    suggested_fix: str
    fix_code: str | None = None
    confidence: str  # high, medium, low
    file_path: str | None = None


class AnalyzeFailureRequest(BaseModel):
    owner: str
    repo: str
    run_id: int


class MonitorRequest(BaseModel):
    owner: str
    repo: str
    branch: str | None = None
    poll_interval: int = 30  # seconds


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/runs/{owner}/{repo}", response_model=list[CIRunSummary])
def list_ci_runs(owner: str, repo: str, branch: str | None = None, limit: int = 10):
    """List recent CI/CD workflow runs."""
    try:
        from app import github_service
        runs = github_service.list_workflow_runs(owner, repo, limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot fetch CI runs: {e}")

    results = []
    for run in runs:
        if branch and run.head_branch != branch:
            continue
        results.append(CIRunSummary(
            id=run.id,
            name=run.name,
            status=run.status,
            conclusion=run.conclusion,
            branch=run.head_branch,
            commit_sha=run.head_sha[:7],
            commit_message=getattr(run, "display_title", run.name),
            html_url=run.html_url,
            created_at=str(run.created_at),
            updated_at=str(run.updated_at),
            run_number=run.run_number,
        ))
    return results


@router.get("/runs/{owner}/{repo}/{run_id}/jobs")
def get_ci_jobs(owner: str, repo: str, run_id: int):
    """Get jobs for a specific CI run."""
    try:
        from app import github_service
        g = github_service._get_github()
        repo_obj = g.get_repo(f"{owner}/{repo}")
        run = repo_obj.get_workflow_run(run_id)
        jobs = run.jobs()

        result = []
        for job in jobs:
            steps = []
            for step in job.steps:
                steps.append({
                    "name": step.name,
                    "status": step.status,
                    "conclusion": step.conclusion,
                    "number": step.number,
                })
            result.append({
                "id": job.id,
                "name": job.name,
                "status": job.status,
                "conclusion": job.conclusion,
                "started_at": str(job.started_at) if job.started_at else None,
                "completed_at": str(job.completed_at) if job.completed_at else None,
                "steps": steps,
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot fetch CI jobs: {e}")


@router.get("/runs/{owner}/{repo}/{run_id}/logs")
def get_ci_logs(owner: str, repo: str, run_id: int):
    """Get logs for a CI run (useful for diagnosing failures)."""
    try:
        from app import github_service
        g = github_service._get_github()
        repo_obj = g.get_repo(f"{owner}/{repo}")
        run = repo_obj.get_workflow_run(run_id)
        jobs = run.jobs()

        logs = []
        for job in jobs:
            if job.conclusion == "failure":
                job_log = {
                    "job_name": job.name,
                    "conclusion": job.conclusion,
                    "failed_steps": [],
                }
                for step in job.steps:
                    if step.conclusion == "failure":
                        job_log["failed_steps"].append({
                            "name": step.name,
                            "number": step.number,
                            "conclusion": step.conclusion,
                        })
                logs.append(job_log)

        return {"run_id": run_id, "status": run.status, "conclusion": run.conclusion, "failed_jobs": logs}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot fetch CI logs: {e}")


@router.post("/analyze-failure", response_model=list[CIFixSuggestion])
def analyze_ci_failure(req: AnalyzeFailureRequest):
    """Analyze a CI failure and suggest AI-powered fixes."""
    # First get the failure details
    try:
        logs = get_ci_logs(req.owner, req.repo, req.run_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot fetch failure info: {e}")

    if not logs.get("failed_jobs"):
        return []

    # Build error context for AI
    error_context = f"CI Run #{req.run_id} for {req.owner}/{req.repo}\n"
    error_context += f"Status: {logs['conclusion']}\n\n"
    for job in logs["failed_jobs"]:
        error_context += f"Failed Job: {job['job_name']}\n"
        for step in job["failed_steps"]:
            error_context += f"  Failed Step: {step['name']}\n"

    # Use AI to analyze
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        # Return basic analysis without AI
        suggestions = []
        for job in logs["failed_jobs"]:
            for step in job["failed_steps"]:
                suggestions.append(CIFixSuggestion(
                    error_summary=f"Step '{step['name']}' failed in job '{job['job_name']}'",
                    root_cause="Requires manual investigation — configure OpenAI API key for AI analysis",
                    suggested_fix="Check the CI logs on GitHub for detailed error messages",
                    confidence="low",
                ))
        return suggestions

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are a CI/CD expert. Analyze the following CI failure and provide fix suggestions. "
                    "For each issue found, provide:\n"
                    "1. error_summary: Brief description of the error\n"
                    "2. root_cause: What caused it\n"
                    "3. suggested_fix: How to fix it\n"
                    "4. fix_code: Code snippet if applicable (or null)\n"
                    "5. confidence: high/medium/low\n"
                    "6. file_path: Affected file if known (or null)\n\n"
                    "Return a JSON array of objects."
                )},
                {"role": "user", "content": error_context},
            ],
            max_tokens=2000,
            temperature=0.2,
        )

        import json
        content = resp.choices[0].message.content or "[]"
        if "```" in content:
            parts = content.split("```")
            content = parts[1]
            if content.startswith("json"):
                content = content[4:]
        fixes = json.loads(content.strip())

        from app.token_tracker import log_tokens
        log_tokens(
            action="ci_analyze_failure",
            feature="ci_monitor",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=resp.usage.total_tokens if resp.usage else 0,
        )

        return [CIFixSuggestion(**f) for f in fixes]
    except Exception as e:
        return [CIFixSuggestion(
            error_summary="AI analysis failed",
            root_cause=str(e),
            suggested_fix="Check CI logs manually on GitHub",
            confidence="low",
        )]


@router.get("/status/{owner}/{repo}")
def ci_status_badge(owner: str, repo: str, branch: str = "main"):
    """Get a quick CI status summary for the repo/branch."""
    try:
        runs = list_ci_runs(owner, repo, branch=branch, limit=5)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    if not runs:
        return {"status": "unknown", "message": "No CI runs found", "branch": branch}

    latest = runs[0]
    return {
        "status": latest.conclusion or latest.status,
        "run_id": latest.id,
        "run_number": latest.run_number,
        "branch": branch,
        "commit": latest.commit_sha,
        "url": latest.html_url,
        "updated_at": latest.updated_at,
    }
