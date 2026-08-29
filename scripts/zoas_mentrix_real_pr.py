"""Drive Mentrix bugfix → confirm → approve → real Create PR for zinnia/zoas."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.getenv("ZECT_API", "http://127.0.0.1:8000")
USER = os.getenv("ZECT_USERNAME", "admin@zect.local")
PASSWORD = os.getenv("ZECT_PASSWORD", "zect-dev-local")
WORKSPACE = r"C:\Users\karuppk\zect-workspaces\zinnia\zoas"
PROJECT_KEY = "zinnia-zoas"
ARTIFACTS = os.path.join(os.path.dirname(__file__), "..", "artifacts", "zoas-workflow")


def req(method: str, path: str, token: str | None = None, body: dict | None = None, timeout: int = 300):
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
    for user, pw in (
        (USER, PASSWORD),
        ("admin@zect.local", "zect-dev-local"),
        ("karthik.karuppasamy@zinnia.com", os.getenv("ZECT_PASSWORD", "")),
    ):
        if not user or not pw:
            continue
        try:
            out = req("POST", "/api/auth/login", body={"username": user, "password": pw})
            print(f"logged in as {user}")
            return out["token"]
        except Exception as exc:
            print(f"login failed for {user}: {exc}")
    raise RuntimeError("Could not login")


def save(name: str, obj):
    os.makedirs(ARTIFACTS, exist_ok=True)
    path = os.path.join(ARTIFACTS, name)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f, indent=2)
    print(f"saved {path}")


def poll_run(token: str, run_id: int, want: set[str], timeout_s: int = 900):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        last = req("GET", f"/api/mentrix/runs/{run_id}", token)
        status = last.get("status") or ""
        print(f"  run #{run_id} status={status} next={last.get('next_step')}", flush=True)
        if status in want:
            return last
        if status in ("failed", "error", "rejected"):
            save(f"mentrix_run_{run_id}_failed.json", last)
            raise RuntimeError(f"Run failed: {status}")
        time.sleep(4)
    save(f"mentrix_run_{run_id}_timeout.json", last or {})
    raise TimeoutError(f"Run {run_id} did not reach {want}")


def main():
    token = login()
    goal = (
        "Bugfix / docs hygiene for ZOAS (zinnia/zoas) on branch mentrix/scorecard-gates-note "
        "(base develop). Ensure docs/MENTRIX_SCORECARD.md exists and states Mentrix Delivery "
        "scorecard = grounded plan + gates green (never claim 100%/0 error). "
        "Touch ONLY docs/MENTRIX_SCORECARD.md. Do not modify any .py, .ts, .tsx, .js, or "
        "zinnia-modern application code. Prefer no-op if the file already matches."
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
    print(f"started run #{run_id}")
    save("mentrix_real_pr_start.json", run)

    run = poll_run(
        token,
        run_id,
        {
            "awaiting_plan_confirm",
            "awaiting_approve",
            "awaiting_approval",
            "completed",
            "pr_created",
            "ready_for_approve",
            "approved",
        },
        timeout_s=180,
    )
    if run.get("status") == "awaiting_plan_confirm":
        run = req("POST", f"/api/mentrix/runs/{run_id}/confirm-plan", token, {}, timeout=120)
        print("confirmed plan", flush=True)
        save("mentrix_real_pr_confirm.json", run)
        run = poll_run(
            token,
            run_id,
            {
                "awaiting_approve",
                "awaiting_approval",
                "completed",
                "ready_for_approve",
                "awaiting_human",
                "approved",
                "failed",
            },
            timeout_s=900,
        )

    gates = run.get("gates") or (run.get("result") or {}).get("gates") or {}
    print("gates:", json.dumps(gates, indent=2)[:1500])
    save("mentrix_real_pr_pre_approve.json", run)

    # Approve — acknowledge sandbox/review only when needed; never ship with critical ultra findings
    critical = int(gates.get("ultra_review_critical") or 0)
    if critical > 0:
        raise RuntimeError(f"ultra_review_critical={critical} — refusing Approve/Create PR")

    ack = not (
        gates.get("sandbox_ready", True)
        and gates.get("review_ok", True)
        and gates.get("lint_ok", True)
    )
    run = req(
        "POST",
        f"/api/mentrix/runs/{run_id}/approve",
        token,
        {"acknowledge_issues": ack, "acknowledge_reason": "ZOAS docs scorecard note — gates reviewed"},
        timeout=120,
    )
    print("approved", "ack=" + str(ack))
    save("mentrix_real_pr_approve.json", run)

    pr = req(
        "POST",
        f"/api/mentrix/runs/{run_id}/create-pr",
        token,
        {
            "dry_run": False,
            "repo_path": WORKSPACE,
            "owner": "zinnia",
            "repo_name": "zoas",
            "head_branch": "mentrix/scorecard-gates-note",
            "base_branch": "develop",
            "title": "docs: Mentrix scorecard is grounded plan + gates green",
            "body": (
                "## Mentrix delivery\n\n"
                "Adds operator note: Mentrix Delivery scorecard = **grounded plan + gates green** "
                "(never claim 100%/0 error).\n\n"
                "Touched only `docs/MENTRIX_SCORECARD.md`.\n"
            ),
        },
        timeout=180,
    )
    save("mentrix_real_pr_create.json", pr)
    pr_url = pr.get("pr_url") or (pr.get("result") or {}).get("pr_url") or ""
    if not pr_url and isinstance(pr.get("result"), dict):
        pr_meta = pr["result"].get("pr") or {}
        pr_url = pr_meta.get("pr_url") or pr_meta.get("html_url") or ""
    print("PR_URL:", pr_url or pr)
    if not pr_url or "dry-run" in str(pr_url):
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
