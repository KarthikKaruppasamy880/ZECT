"""Run ZOAS-in-ZECT workflow steps via API (ask, plan, mentrix bugfix, approve, PR)."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.getenv("ZECT_API", "http://127.0.0.1:8000")
USER = os.getenv("ZECT_USERNAME", "karthik.karuppasamy@zinnia.com")
PASSWORD = os.getenv("ZECT_PASSWORD", "Karthik@1234")
WORKSPACE = r"C:\Users\karuppk\zect-workspaces\zinnia\zoas"
PROJECT_KEY = "zinnia-zoas"
ARTIFACTS = os.path.join(os.path.dirname(__file__), "..", "artifacts", "zoas-workflow")


def req(method: str, path: str, token: str | None = None, body: dict | None = None, timeout: int = 120):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> {e.code}: {detail}") from e


def login() -> str:
    out = req("POST", "/api/auth/login", body={"username": USER, "password": PASSWORD})
    return out["token"]


def save(name: str, content: str):
    os.makedirs(ARTIFACTS, exist_ok=True)
    path = os.path.join(ARTIFACTS, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"saved {path}")


def main():
    token = login()
    print("logged in")

    bp = req("POST", "/api/lattice/blueprint/prompt", token, {"project_key": PROJECT_KEY}, timeout=120)
    ctx = bp.get("prompt", "")[:6000]
    save("blueprint_prompt.md", bp.get("prompt", ""))

    q = req(
        "POST",
        "/api/lattice/query",
        token,
        {"project_key": PROJECT_KEY, "q": "auth", "limit": 10},
    )
    save("lattice_query_auth.json", json.dumps(q, indent=2))
    print(f"lattice query hits: {len(q.get('hits') or [])}")

    ask = req(
        "POST",
        "/api/llm/ask",
        token,
        {
            "question": (
                "Where is authentication and security handled in ZOAS (zinnia-modern)? "
                "Summarize navigation for Workspace, Labs, and API testing flows."
            ),
            "repo_context": ctx,
        },
        timeout=180,
    )
    save("ask_answer.md", ask.get("answer", ""))
    print(f"ask tokens: {ask.get('tokens_used')}")

    plan = req(
        "POST",
        "/api/llm/plan",
        token,
        {
            "project_description": (
                "Improve ZOAS unauthenticated API error handling: consistent JSON error "
                "responses and frontend redirect to login when session expires."
            ),
            "repo_context": ctx + "\n\nAsk triage:\n" + ask.get("answer", "")[:2500],
            "constraints": "Minimal diff; preserve auth flow; run pytest in zinnia-modern/backend/tests.",
        },
        timeout=180,
    )
    save("fix_plan.md", plan.get("plan", ""))
    print(f"plan tokens: {plan.get('tokens_used')}")

    goal = (
        "Bugfix ZOAS (zinnia/zoas): run pytest in zinnia-modern/backend/tests and fix any "
        "failing tests related to auth error responses. Plan:\n"
        + plan.get("plan", "")[:3000]
    )
    run = req(
        "POST",
        "/api/mentrix/runs",
        token,
        {
            "goal": goal,
            "mode": "bugfix",
            "project_key": PROJECT_KEY,
            "workspace": WORKSPACE,
        },
        timeout=120,
    )
    run_id = run["id"]
    print(f"mentrix run id={run_id} status={run.get('status')}")

    deadline = time.time() + 900
    final = run
    while time.time() < deadline:
        time.sleep(5)
        final = req("GET", f"/api/mentrix/runs/{run_id}", token, timeout=60)
        status = final.get("status", "")
        print(f"  status={status} agent={final.get('current_agent')}")
        if status in ("completed", "failed", "approved", "needs_human", "error"):
            break

    save("mentrix_run.json", json.dumps(final, indent=2))
    gates = final.get("gates") or {}
    print(f"gates: {json.dumps(gates)[:500]}")

    approved = req(
        "POST",
        f"/api/mentrix/runs/{run_id}/approve",
        token,
        {"acknowledge_issues": True, "acknowledge_reason": "ZOAS workflow eval — sandbox may skip DB deps"},
        timeout=60,
    )
    save("mentrix_approve.json", json.dumps(approved, indent=2))
    print(f"approved status={approved.get('status')}")

    pr = req(
        "POST",
        f"/api/mentrix/runs/{run_id}/create-pr",
        token,
        {
            "title": "fix(zoas): auth error handling improvements",
            "repo_path": WORKSPACE,
            "owner": "zinnia",
            "repo_name": "zoas",
            "dry_run": True,
        },
        timeout=120,
    )
    save("mentrix_pr.json", json.dumps(pr, indent=2))
    print(f"pr dry_run url={pr.get('pr_url') or pr.get('url')}")
    print("done")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
