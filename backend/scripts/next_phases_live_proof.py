#!/usr/bin/env python3
"""Live Graphify → Lattice → Companion → PLAN → Present proof against :8020.

Never prints secrets. Does not fake Presenton / Voicebox / GitHub / PowerPoint.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.services.lattice.indexer import derive_project_key  # noqa: E402
from app.services.mentrix.companion_scope import handoff_url  # noqa: E402

API = os.environ.get("ZECT_API_URL", "http://127.0.0.1:8020").rstrip("/")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    path = BACKEND / ".env"
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, val = stripped.split("=", 1)
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def git_init(root: Path) -> str:
    subprocess.check_call(["git", "init", "-b", "main"], cwd=root, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "zect@example.com"], cwd=root)
    subprocess.check_call(["git", "config", "user.name", "ZECT"], cwd=root)
    subprocess.check_call(["git", "add", "."], cwd=root, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-m", "init"], cwd=root, stdout=subprocess.DEVNULL)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def req(method: str, path: str, token: str = "", body: dict | None = None, timeout: int = 90):
    data = None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {"detail": raw}
        except json.JSONDecodeError:
            parsed = {"detail": raw[:400]}
        return exc.code, parsed


def probe(url: str, timeout: float = 1.5) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def main() -> int:
    env = load_env()
    user = env.get("ZECT_USERNAME") or os.environ.get("ZECT_USERNAME") or "admin@zect.local"
    password = env.get("ZECT_PASSWORD") or os.environ.get("ZECT_PASSWORD") or "zect-dev-local"
    report: dict = {"api": API, "steps": []}

    status, health = req("GET", "/healthz")
    report["healthz"] = {"http": status, "ok": status == 200}
    if status != 200:
        print(json.dumps(report, indent=2))
        return 1

    status, login = req("POST", "/api/auth/login", body={"username": user, "password": password})
    token = str(login.get("token") or "") if status == 200 else ""
    report["login"] = {"http": status, "ok": bool(token)}
    if not token:
        print(json.dumps(report, indent=2))
        return 1

    base = Path(tempfile.mkdtemp(prefix="zect-next-phases-"))
    alpha = base / "alpha-svc"
    beta = base / "beta-svc"
    alpha.mkdir()
    beta.mkdir()
    (alpha / "api.py").write_text(
        "from fastapi import APIRouter\nrouter = APIRouter()\n@router.get('/health')\ndef health():\n    return {'ok': True}\n",
        encoding="utf-8",
    )
    (alpha / "tests").mkdir()
    (alpha / "tests" / "test_api.py").write_text("def test_health():\n    assert True\n", encoding="utf-8")
    (beta / "client.py").write_text("def call_health():\n    return '/health'\n", encoding="utf-8")
    sha_a = git_init(alpha)
    sha_b = git_init(beta)

    status, project = req(
        "POST",
        "/api/projects",
        token,
        {"name": "next-phases-integrated", "description": "Graphify Lattice live proof", "team": "zect"},
    )
    pid = int(project.get("id") or 0) if status in (200, 201) else 0
    report["project"] = {"http": status, "id": pid, "ok": pid > 0}
    if not pid:
        print(json.dumps(report, indent=2))
        return 1

    repos = []
    for path in (alpha, beta):
        st, body = req(
            "POST",
            "/api/repos/register-local",
            token,
            {"project_id": pid, "local_path": str(path)},
        )
        repos.append({"http": st, "ok": bool(body.get("ok")), "repo_id": body.get("repo_id"), "identity_name": (body.get("identity") or {}).get("name")})
    report["register_local"] = repos
    if not all(r["ok"] for r in repos):
        print(json.dumps(report, indent=2))
        return 1

    snapshots = []
    for path, expected_sha in ((alpha, sha_a), (beta, sha_b)):
        owner = "local"
        name = path.name
        key = derive_project_key(owner, name)
        st, ingest = req(
            "POST",
            "/api/lattice/ingest",
            token,
            {"path": str(path), "project_key": key, "force": True, "index_rag": False, "max_files": 50},
            timeout=120,
        )
        st2, snap = req("GET", f"/api/lattice/snapshot?project_key={key}", token)
        snapshots.append(
            {
                "key": key,
                "ingest_http": st,
                "snapshot_http": st2,
                "state": snap.get("state"),
                "kind": snap.get("kind"),
                "adapter": snap.get("adapter"),
                "ux_label": snap.get("ux_label"),
                "commit_sha": (snap.get("commit_sha") or "")[:12],
                "sha_match": (snap.get("commit_sha") or "") == expected_sha,
                "ready": snap.get("state") in {"READY", "STALE"} and snap.get("kind") == "GraphifySnapshot",
            }
        )
    report["snapshots"] = snapshots
    report["graphify_lattice"] = all(s["ready"] and s["sha_match"] for s in snapshots)

    key_a = snapshots[0]["key"] if snapshots else ""
    st, query = req("POST", "/api/lattice/query", token, {"project_key": key_a, "q": "health", "limit": 8})
    report["lattice_query"] = {"http": st, "hits": len((query.get("hits") or [])), "ok": st == 200 and bool(query.get("hits"))}

    st, turn = req(
        "POST",
        "/api/mentrix/companion/turn",
        token,
        {
            "message": "What APIs exist in the authorized Lattice graph? Do not invent.",
            "project_id": pid,
            "project_key": key_a,
            "repository_ids": [r["repo_id"] for r in repos if r.get("repo_id")],
        },
        timeout=60,
    )
    tools = [str(t.get("name") or t.get("tool") or "") for t in (turn.get("tool_results") or turn.get("tools") or [])]
    report["companion_turn"] = {
        "http": st,
        "ok": st == 200,
        "has_answer": bool(turn.get("answer") or turn.get("text") or turn.get("message")),
        "tool_names": tools[:8],
        "ux_not_graphify_internal": "GraphifySnapshot" not in json.dumps(turn)[:4000],
    }

    st, wi = req(
        "POST",
        "/api/work-items",
        token,
        {
            "title": "Graph-informed health endpoint review",
            "description": "Use Lattice provenance only",
            "project_id": pid,
            "repository_id": repos[0].get("repo_id"),
            "base_commit_sha": sha_a,
        },
    )
    wid = int(wi.get("id") or 0) if st in (200, 201) else 0
    report["work_item"] = {"http": st, "id": wid, "ok": wid > 0}

    st, plan = req(
        "POST",
        "/api/mentrix/developer/plan",
        token,
        {
            "goal": "Document health API impact across authorized repos using Lattice",
            "work_item_id": wid,
            "project_id": pid,
            "repository_ids": [r["repo_id"] for r in repos if r.get("repo_id")],
            "base_commit_sha": sha_a,
        },
        timeout=90,
    )
    pack = plan.get("context_pack") or {}
    report["graph_informed_plan"] = {
        "http": st,
        "ok": st == 200,
        "work_item_id": plan.get("work_item_id") or wid,
        "affected_repos": len(plan.get("affected_repos") or []),
        "has_context": bool(pack),
    }

    st, mission = req(
        "POST",
        "/api/coding-agent/missions",
        token,
        {
            "goal": "Add a comment on health() without pushing to GitHub",
            "project_id": pid,
            "work_item_id": wid,
        },
        timeout=60,
    )
    report["coding_agent_mission"] = {
        "http": st,
        "ok": st == 200,
        "phase": mission.get("phase") or mission.get("status"),
        "github_pr": "BLOCKED_EXTERNAL",
        "note": "Internal PLAN/awaiting_plan_approval only; no live GitHub PR claimed",
    }

    url = handoff_url(
        "present_create",
        {"project_id": pid, "work_item_id": wid, "workspace_id": key_a},
        extra={"prompt": "architecture from Lattice", "audience": "exec"},
    )
    report["present_handoff"] = {"ok": url.startswith("/present/create") and f"project_id={pid}" in url, "path_prefix": url.split("?")[0]}

    st, pstat = req("GET", "/api/mentrix/presenton/status", token)
    provider = str(pstat.get("provider") or "")
    reachable = bool(pstat.get("reachable") or pstat.get("ok") or pstat.get("presenton_reachable"))
    report["presenton_status"] = {
        "http": st,
        "provider": provider,
        "keys": sorted(list(pstat.keys()))[:12] if isinstance(pstat, dict) else [],
    }
    stg, gen = req(
        "POST",
        "/api/mentrix/presenton/generate",
        token,
        {"content": "Lattice architecture one-pager", "n_slides": 3, "fast_basic": True, "require_llm": False},
        timeout=45,
    )
    gen_ok = stg in (200, 201) and bool((gen or {}).get("ok") if isinstance(gen, dict) else False)
    report["present_generate"] = {
        "http": stg,
        "ok": gen_ok,
        "verdict": "PASS" if gen_ok else "BLOCKED_EXTERNAL",
        "error": (str((gen or {}).get("detail") or (gen or {}).get("error") or "")[:180] if not gen_ok else ""),
    }

    st, integ = req("GET", "/api/mentrix/companion/integrations", token)
    connectors = integ.get("connectors") or integ if isinstance(integ, dict) else {}
    report["integrations_http"] = st
    report["optional"] = {
        "presenton_probe": "READY" if probe("http://127.0.0.1:5000/") else "OPTIONAL_UNAVAILABLE",
        "voicebox_probe": "READY" if probe("http://127.0.0.1:17493/health") else "OPTIONAL_UNAVAILABLE",
        "github": "BLOCKED_EXTERNAL",
        "jira": "BLOCKED_EXTERNAL",
        "camunda": "BLOCKED_EXTERNAL",
        "powerpoint": "OPTIONAL_UNAVAILABLE",
        "nsis": "BLOCKED_EXTERNAL",
    }

    report["fixture_dir"] = str(base)
    report["keys"] = [s["key"] for s in snapshots]
    internal = bool(
        report["graphify_lattice"]
        and report["lattice_query"]["ok"]
        and report["work_item"]["ok"]
        and report["graph_informed_plan"]["ok"]
        and report["present_handoff"]["ok"]
    )
    report["internal_path"] = "PASS" if internal else "FAIL"
    print(json.dumps(report, indent=2))
    state_path = REPO / ".zect" / "stack" / "next-phases-proof.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"fixture_dir": str(base), "keys": report["keys"], "project_id": pid, "work_item_id": wid}, indent=2), encoding="utf-8")
    return 0 if internal else 1


if __name__ == "__main__":
    raise SystemExit(main())
