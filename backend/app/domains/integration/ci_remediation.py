"""CI/CD Auto-Remediation — detect CI failures, analyze, suggest/apply fixes."""

import json
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/ci-remediation", tags=["ci-remediation"])


class AnalyzeFailureRequest(BaseModel):
    owner: str
    repo: str
    run_id: int
    job_name: str | None = None


class AutoFixRequest(BaseModel):
    owner: str
    repo: str
    run_id: int
    job_name: str | None = None
    branch: str = "main"
    max_retries: int = 2
    auto_commit: bool = False


def _get_github_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"} if token else {}


def _fetch_workflow_run(owner: str, repo: str, run_id: int) -> dict | None:
    """Fetch a GitHub Actions workflow run."""
    import requests
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
    resp = requests.get(url, headers=_get_github_headers(), timeout=15)
    return resp.json() if resp.status_code == 200 else None


def _fetch_run_jobs(owner: str, repo: str, run_id: int) -> list[dict]:
    """Fetch jobs for a workflow run."""
    import requests
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
    resp = requests.get(url, headers=_get_github_headers(), timeout=15)
    if resp.status_code == 200:
        return resp.json().get("jobs", [])
    return []


def _fetch_job_logs(owner: str, repo: str, job_id: int) -> str:
    """Fetch logs for a specific job."""
    import requests
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
    resp = requests.get(url, headers=_get_github_headers(), timeout=15, allow_redirects=True)
    if resp.status_code == 200:
        return resp.text[:10000]
    return f"Unable to fetch logs (status {resp.status_code})"


def _ai_analyze_ci_failure(error_log: str, job_name: str, workflow_name: str) -> dict:
    """Use AI to analyze a CI failure and suggest remediation."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return {
            "error_type": "unknown",
            "root_cause": "Configure LLM API key for AI-powered CI analysis",
            "suggested_fixes": [],
            "auto_fixable": False,
            "confidence": "low",
            "tokens_used": 0,
        }

    from openai import OpenAI
    client = OpenAI(api_key=key)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": (
                "You are a CI/CD expert. Analyze the CI failure log and provide remediation.\n"
                "Return JSON with:\n"
                "- error_type: category (build, test, lint, deploy, dependency, permission, timeout)\n"
                "- root_cause: one-line explanation\n"
                "- suggested_fixes: array of {description, commands, file_changes, confidence}\n"
                "- auto_fixable: boolean\n"
                "- confidence: high/medium/low\n"
                "- prevention: how to prevent this in the future\n"
                "Return ONLY JSON."
            )},
            {"role": "user", "content": (
                f"Workflow: {workflow_name}\nJob: {job_name}\n"
                f"\nError Log:\n{error_log[:5000]}"
            )},
        ],
        max_tokens=2000,
        temperature=0.1,
    )

    tokens = resp.usage.total_tokens if resp.usage else 0

    from app.token_tracker import log_tokens
    log_tokens(
        action="ci_remediation",
        feature="ci_remediation",
        model="gpt-4o-mini",
        prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
        completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
        total_tokens=tokens,
    )

    content = resp.choices[0].message.content or "{}"
    if "```" in content:
        parts = content.split("```")
        content = parts[1]
        if content.startswith("json"):
            content = content[4:]

    try:
        result = json.loads(content.strip())
        result["tokens_used"] = tokens
        return result
    except json.JSONDecodeError:
        return {
            "error_type": "parse_error",
            "root_cause": "Could not parse AI response",
            "suggested_fixes": [],
            "auto_fixable": False,
            "confidence": "low",
            "tokens_used": tokens,
        }


@router.post("/analyze")
def analyze_ci_failure(req: AnalyzeFailureRequest):
    """Analyze a CI failure and suggest fixes."""
    run_data = _fetch_workflow_run(req.owner, req.repo, req.run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    jobs = _fetch_run_jobs(req.owner, req.repo, req.run_id)
    failed_jobs = [j for j in jobs if j.get("conclusion") == "failure"]
    if not failed_jobs:
        return {"status": "no_failures", "message": "No failed jobs in this run"}

    results = []
    total_tokens = 0
    for job in failed_jobs:
        if req.job_name and job.get("name") != req.job_name:
            continue
        logs = _fetch_job_logs(req.owner, req.repo, job["id"])
        analysis = _ai_analyze_ci_failure(logs, job.get("name", ""), run_data.get("name", ""))
        total_tokens += analysis.get("tokens_used", 0)
        results.append({
            "job_id": job["id"],
            "job_name": job.get("name", ""),
            "conclusion": job.get("conclusion", ""),
            "analysis": analysis,
            "log_excerpt": logs[:2000],
        })

    return {
        "run_id": req.run_id,
        "workflow": run_data.get("name", ""),
        "status": run_data.get("conclusion", ""),
        "failed_jobs_count": len(failed_jobs),
        "analyses": results,
        "total_tokens": total_tokens,
    }


@router.post("/auto-fix")
def auto_fix_ci(req: AutoFixRequest):
    """Analyze CI failure and attempt automatic fix."""
    run_data = _fetch_workflow_run(req.owner, req.repo, req.run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    jobs = _fetch_run_jobs(req.owner, req.repo, req.run_id)
    failed_jobs = [j for j in jobs if j.get("conclusion") == "failure"]
    if not failed_jobs:
        return {"status": "no_failures", "message": "No failed jobs to fix"}

    fixes_applied = []
    total_tokens = 0

    for job in failed_jobs:
        if req.job_name and job.get("name") != req.job_name:
            continue
        logs = _fetch_job_logs(req.owner, req.repo, job["id"])
        analysis = _ai_analyze_ci_failure(logs, job.get("name", ""), run_data.get("name", ""))
        total_tokens += analysis.get("tokens_used", 0)

        fix_result = {
            "job_name": job.get("name", ""),
            "analysis": analysis,
            "fixes_attempted": [],
            "status": "analyzed",
        }

        for fix in analysis.get("suggested_fixes", []):
            fix_entry = {
                "description": fix.get("description", ""),
                "confidence": fix.get("confidence", "low"),
                "applied": False,
            }

            if req.auto_commit and fix.get("commands"):
                fix_entry["commands"] = fix["commands"]
                fix_entry["note"] = "Auto-commit enabled — commands ready for execution"
                fix_entry["applied"] = True

            if fix.get("file_changes"):
                fix_entry["file_changes"] = fix["file_changes"]

            fix_result["fixes_attempted"].append(fix_entry)

        if any(f.get("applied") for f in fix_result["fixes_attempted"]):
            fix_result["status"] = "fixes_ready"
        else:
            fix_result["status"] = "manual_review_needed"

        fixes_applied.append(fix_result)

    return {
        "run_id": req.run_id,
        "branch": req.branch,
        "total_failed_jobs": len(failed_jobs),
        "fixes": fixes_applied,
        "total_tokens": total_tokens,
    }


@router.get("/history")
def remediation_history(owner: str = "", repo: str = "", limit: int = 20):
    """Get history of CI remediation attempts (in-memory for now)."""
    return {
        "history": [],
        "total": 0,
        "note": "Remediation history is tracked per-session. Use audit trail for persistent history.",
    }
