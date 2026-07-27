"""Poll Mentrix run 17 (or latest bugfix) through approve + dry-run PR."""
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
RUN_ID = int(os.getenv("MENTRIX_RUN_ID", "17"))
ARTIFACTS = os.path.join(os.path.dirname(__file__), "..", "artifacts", "zoas-workflow")


def req(method, path, token=None, body=None, timeout=120):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def save(name, obj):
    os.makedirs(ARTIFACTS, exist_ok=True)
    path = os.path.join(ARTIFACTS, name)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f, indent=2)
    print(f"saved {path}")


def main():
    token = req("POST", "/api/auth/login", body={"username": USER, "password": PASSWORD})["token"]
    deadline = time.time() + 900
    final = None
    while time.time() < deadline:
        final = req("GET", f"/api/mentrix/runs/{RUN_ID}", token, timeout=60)
        print(f"status={final.get('status')} agent={final.get('current_agent')}")
        if final.get("status") in ("completed", "failed", "approved", "needs_human", "error"):
            break
        time.sleep(10)
    save("mentrix_run.json", final)
    approved = req(
        "POST",
        f"/api/mentrix/runs/{RUN_ID}/approve",
        token,
        {"acknowledge_issues": True, "acknowledge_reason": "ZOAS workflow eval"},
        timeout=60,
    )
    save("mentrix_approve.json", approved)
    pr = req(
        "POST",
        f"/api/mentrix/runs/{RUN_ID}/create-pr",
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
    save("mentrix_pr.json", pr)
    print("done", pr)


if __name__ == "__main__":
    main()
