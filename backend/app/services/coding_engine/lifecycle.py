"""Mentrix Coding Agent production lifecycle.

Requirement → PLAN → approval → isolated worktree → edit → tests → diagnose →
Ultra Review → commit → push/PR. Does not auto-merge. Sibling PASS+FAIL ⇒ BLOCKED.
Cancel/resume skips already-recorded commit SHAs so retries cannot duplicate them.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.infrastructure.allowed_paths import path_under_allowed_roots
from app.services.coding_engine.mentrix_agent_tools import execute_tool, resolve_workspace
from app.services.mentrix.companion_scope import aggregate_sibling_status, redact_secrets

CHECKPOINT = ".zect/coding-agent-checkpoint.json"
_MISSION_ID_RE = re.compile(r"^[0-9a-fA-F-]{8,64}$")

_LOCK = threading.Lock()
_MISSIONS: dict[str, dict[str, Any]] = {}


def missions_dir() -> Path:
    override = (os.getenv("ZECT_CODING_MISSIONS_DIR") or "").strip()
    if override:
        return Path(override)
    user = (os.getenv("ZECT_USER_DATA") or "").strip()
    if user:
        return Path(user) / "data" / "coding_missions"
    if (os.getenv("ZECT_PYTEST") or "").strip() or os.getenv("PYTEST_CURRENT_TEST"):
        current = (os.getenv("PYTEST_CURRENT_TEST") or "session").split(" ")[0]
        safe = re.sub(r"[^0-9a-zA-Z._-]+", "_", current)[:80] or "session"
        return Path(tempfile.gettempdir()) / "zect-pytest-coding-missions" / safe
    return Path(__file__).resolve().parents[3] / "data" / "coding_missions"


def reset_mission_cache() -> None:
    """Simulate a backend process restart (in-memory map is empty)."""
    with _LOCK:
        _MISSIONS.clear()


def _safe_mission_id(mission_id: str) -> str:
    mid = (mission_id or "").strip()
    if not _MISSION_ID_RE.fullmatch(mid):
        raise KeyError("mission_not_found")
    return mid


def _persistable(mission: dict[str, Any]) -> dict[str, Any]:
    """JSON snapshot of internal mission state.

    Do not round-trip through ``redact_secrets`` here: that rewrites patch
    bodies and test paths, so resume/repair after restart would re-apply ``***``.
    API responses still go through ``_public`` + companion redaction.
    """
    return json.loads(json.dumps(mission, default=str))


def _save_mission(mission: dict[str, Any]) -> None:
    mid = _safe_mission_id(str(mission.get("id") or ""))
    dest = missions_dir()
    try:
        dest.mkdir(parents=True, exist_ok=True)
        payload = _persistable(mission)
        (dest / f"{mid}.json").write_text(json.dumps(payload), encoding="utf-8")
        mission.pop("persist_error", None)
    except (OSError, TypeError, ValueError):
        mission["persist_error"] = "persist_failed"


def _load_mission_from_disk(mission_id: str) -> dict[str, Any] | None:
    mid = _safe_mission_id(mission_id)
    path = missions_dir() / f"{mid}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("mission_corrupt") from exc
    if not isinstance(data, dict) or str(data.get("id") or "") != mid:
        raise ValueError("mission_corrupt")
    return data


def _lookup(mission_id: str) -> dict[str, Any]:
    mid = _safe_mission_id(mission_id)
    with _LOCK:
        cached = _MISSIONS.get(mid)
        if cached:
            return cached
    loaded = _load_mission_from_disk(mid)
    with _LOCK:
        cached = _MISSIONS.get(mid)
        if cached:
            return cached
        if not loaded:
            raise KeyError("mission_not_found")
        _MISSIONS[mid] = loaded
        return loaded


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(cwd: Path, args: list[str], timeout: int = 60) -> dict[str, Any]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip()[:1500],
    }


def _head(cwd: Path) -> str:
    return _git(cwd, ["rev-parse", "HEAD"]).get("stdout") or ""


def _public(mission: dict[str, Any]) -> dict[str, Any]:
    repos = []
    for r in mission.get("repos") or []:
        repos.append(
            {
                "repository_id": r.get("repository_id"),
                "label": r.get("label"),
                "worktree_path": r.get("worktree_path"),
                "branch": r.get("branch"),
                "head_sha": r.get("head_sha"),
                "test_ok": r.get("test_ok"),
                "test_status": r.get("test_status"),
                "files": list(r.get("files") or []),
                "commands": list(r.get("commands") or []),
                "blocker": r.get("blocker") or "",
                "committed_shas": list(r.get("committed_shas") or []),
                "diff": str(r.get("diff") or "")[:8000],
                "push": r.get("push") or {},
                "pr": r.get("pr") or {},
            }
        )
    sibling = mission.get("sibling") or {}
    return {
        "id": mission["id"],
        "goal": mission.get("goal"),
        "phase": mission.get("phase"),
        "status": mission.get("status"),
        "plan": mission.get("plan"),
        "plan_approved": bool(mission.get("plan_approved")),
        "git_approved": bool(mission.get("git_approved")),
        "repos": repos,
        "files": [f for r in repos for f in (r.get("files") or [])],
        "commands": [c for r in repos for c in (r.get("commands") or [])],
        "tests": {str(r.get("repository_id")): r.get("test_status") for r in repos},
        "blockers": [r.get("blocker") for r in repos if r.get("blocker")]
        + ([sibling.get("blocker")] if sibling.get("blocked") else []),
        "approvals": {
            "plan": bool(mission.get("plan_approved")),
            "git": bool(mission.get("git_approved")),
        },
        "review": mission.get("review") or {},
        "pr": next((r.get("pr") for r in repos if (r.get("pr") or {}).get("url")), {}) or {},
        "ci": mission.get("ci") or {},
        "correlation_id": mission.get("correlation_id") or "",
        "work_item_id": mission.get("work_item_id"),
        "project_id": mission.get("project_id"),
        "sibling": sibling,
        "ready_to_merge": mission.get("phase") == "ready_to_merge",
        "companion_edits_code": False,
        "no_auto_merge": True,
        "persistence": "durable_json",
        "updated_at": mission.get("updated_at"),
        "events": list(mission.get("events") or [])[-40:],
        "evidence": list(mission.get("events") or [])[-40:],
    }


def get_mission(mission_id: str) -> dict[str, Any]:
    return _public(_lookup(mission_id))


def _emit(mission: dict[str, Any], event: str, message: str, **data: Any) -> None:
    mission.setdefault("events", []).append(
        {"event": event, "message": message, "data": data, "at": _now()}
    )
    mission["updated_at"] = _now()
    _save_mission(mission)
    try:
        from app.infrastructure.observability import emit_event
        from app.security.redact import redact_mapping

        fail = ""
        if event in ("cancelled",):
            fail = "cancelled"
        elif event in ("blocked",):
            fail = "blocked"
        emit_event(
            operation="coding_agent",
            stage=event,
            message=message,
            run_id=str(mission.get("id") or ""),
            correlation_id=str(mission.get("correlation_id") or ""),
            work_item_id=mission.get("work_item_id"),
            project_id=mission.get("project_id"),
            failure_class=fail,
            extra=redact_mapping(data) if data else {},
        )
    except Exception:
        pass


def _write_checkpoint(repo: dict[str, Any]) -> None:
    wt = Path(repo.get("worktree_path") or "")
    if not wt:
        return
    path = wt / CHECKPOINT
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "committed_shas": list(repo.get("committed_shas") or []),
        "phase": repo.get("slice_phase") or "",
        "head_sha": repo.get("head_sha") or "",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_checkpoint(wt: Path) -> dict[str, Any]:
    path = wt / CHECKPOINT
    if not path.is_file():
        return {"committed_shas": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"committed_shas": []}
    except json.JSONDecodeError:
        return {"committed_shas": []}


def _ensure_zect_ignored(worktree: Path) -> None:
    gi = worktree / ".gitignore"
    try:
        text = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    except OSError:
        return
    if ".zect/" in text.splitlines() or text.endswith(".zect/\n") or ".zect/\n" in text:
        return
    suffix = "" if not text or text.endswith("\n") else "\n"
    try:
        gi.write_text(text + suffix + ".zect/\n", encoding="utf-8")
    except OSError:
        return


def isolate_worktree(source: str | Path, *, branch: str, dest: str | Path) -> dict[str, Any]:
    """Create an isolated git worktree; leave the main checkout untouched."""
    main = resolve_workspace(str(source))
    dest_p = Path(dest)
    dest_p.parent.mkdir(parents=True, exist_ok=True)
    before = _head(main)
    if dest_p.exists() and (dest_p / ".git").exists():
        ck = _load_checkpoint(dest_p)
        return {
            "ok": True,
            "reused": True,
            "worktree_path": str(dest_p.resolve()),
            "branch": branch,
            "head_sha": _head(dest_p),
            "main_head_sha": before,
            "main_unchanged": True,
            "committed_shas": list(ck.get("committed_shas") or []),
        }
    add = _git(main, ["worktree", "add", "-B", branch, str(dest_p), "HEAD"])
    if not add["ok"]:
        return {"ok": False, "error": add.get("stderr") or add.get("stdout") or "worktree_add_failed"}
    _ensure_zect_ignored(dest_p)
    after = _head(main)
    return {
        "ok": True,
        "reused": False,
        "worktree_path": str(dest_p.resolve()),
        "branch": branch,
        "head_sha": _head(dest_p),
        "main_head_sha": after,
        "main_unchanged": after == before,
        "committed_shas": [],
    }


def run_repo_tests(worktree: Path) -> dict[str, Any]:
    tests_dir = worktree / "tests"
    has_pytest = tests_dir.is_dir() and any(tests_dir.glob("test_*.py"))
    if not has_pytest:
        return {"ok": True, "status": "skipped", "kind": "none", "detail": "no tests/"}
    import sys

    root = resolve_workspace(str(worktree))
    out = execute_tool(
        "run_command",
        {
            "command": (
                f'"{sys.executable}" -m pytest -q --tb=short --noconftest '
                f"--rootdir=. -o addopts= -o testpaths=tests -p no:cacheprovider tests"
            ),
            "timeout": 90,
        },
        workspace=root,
        auto_approve_edits=True,
    )
    ok = bool(out.get("ok"))
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "kind": "pytest",
        "exit_code": out.get("exit_code"),
        "stdout": (out.get("stdout") or "")[-1200:],
        "stderr": (out.get("stderr") or "")[-600:],
        "command": out.get("command"),
    }


def scan_worktree_security(worktree: Path) -> list[dict[str, Any]]:
    """Fail closed on eval() and obvious hardcoded secrets in the isolated tree."""
    findings: list[dict[str, Any]] = []
    skip = {".git", "node_modules", "__pycache__", ".venv", ".zect"}
    secret_re = re.compile(r"(sk-live-|AKIA[0-9A-Z]{16}|api_key\s*=\s*['\"][^'\"]{8,}['\"])", re.I)
    eval_re = re.compile(r"\beval\s*\(")
    for dirpath, dirnames, filenames in os.walk(worktree):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if not fn.endswith((".py", ".js", ".ts", ".tsx", ".env")):
                continue
            fp = Path(dirpath) / fn
            if ".git" in fp.parts or "tests" in fp.parts:
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = str(fp.relative_to(worktree)).replace("\\", "/")
            if eval_re.search(text):
                findings.append(
                    {"severity": "critical", "category": "security", "message": f"eval() remains in {rel}"}
                )
            if secret_re.search(text) and fn != "package-lock.json":
                findings.append(
                    {
                        "severity": "critical",
                        "category": "secrets",
                        "message": f"possible hardcoded secret in {rel}",
                    }
                )
    return findings


def _added_from_diff(diff: str) -> str:
    """Review added lines only — deleted secret hunks must not block a fix."""
    added: list[str] = []
    for line in (diff or "").splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    return "\n".join(added)


def _blocking_review_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Critical always blocks. High blocks only for security categories, not style nits."""
    blocking: list[dict[str, Any]] = []
    security_cats = {"security", "secrets", "vulnerabilities", "vulnerability", "injection"}
    for f in findings:
        sev = str(f.get("severity") or "").lower()
        cat = str(f.get("category") or "").lower()
        if sev == "critical":
            blocking.append(f)
        elif sev == "high" and cat in security_cats:
            blocking.append(f)
    return blocking


def review_diff(diff: str) -> dict[str, Any]:
    """Mentrix Ultra Review of a unified diff. Offline heuristics still count as review, not skip."""
    blob = redact_secrets(_added_from_diff(diff) or diff or "")[:20000]
    from app.services.phases.review_phase_svc import run_ultra_review

    out = run_ultra_review(
        blob or "# empty diff\n",
        language="diff",
        goal="Mentrix Coding Agent production review: secrets, injection, path jail, no auto-merge.",
    )
    findings = [f for f in (out.get("findings") or []) if isinstance(f, dict)]
    blocking = _blocking_review_findings(findings)
    return {
        "passed": bool(out.get("passed")) and not blocking,
        "score": out.get("score") or out.get("quality_score"),
        "critical_findings": len(blocking),
        "offline": bool(out.get("offline")),
        "model": out.get("model"),
        "findings": [
            {
                "severity": f.get("severity"),
                "category": f.get("category"),
                "message": str(f.get("message") or f.get("description") or f.get("title") or "")[:400],
            }
            for f in findings[:20]
        ],
        "summary": str(out.get("summary") or "")[:600],
    }


def _apply_patches(worktree: Path, patches: list[dict[str, Any]]) -> dict[str, Any]:
    root = resolve_workspace(str(worktree))
    files: list[str] = []
    commands: list[str] = []
    for patch in patches or []:
        path = str(patch.get("path") or "").strip()
        if not path:
            continue
        if patch.get("content") is not None:
            out = execute_tool(
                "write_file",
                {"path": path, "content": str(patch.get("content"))},
                workspace=root,
                auto_approve_edits=True,
            )
        else:
            old = str(patch.get("old_text") or patch.get("old") or "")
            new = str(patch.get("new_text") or patch.get("new") or "")
            out = execute_tool(
                "apply_patch",
                {"path": path, "old_text": old, "new_text": new},
                workspace=root,
                auto_approve_edits=True,
            )
            if not out.get("ok") and out.get("error") == "old_text_not_found":
                existing = execute_tool("read_file", {"path": path}, workspace=root, auto_approve_edits=True)
                if new and new in str(existing.get("content") or ""):
                    files.append(path.replace("\\", "/"))
                    continue
        if out.get("ok") and out.get("path"):
            files.append(out["path"])
        elif not out.get("ok"):
            return {"ok": False, "error": out.get("error") or "patch_failed", "path": path, "files": files}
        if patch.get("command"):
            cmd = str(patch["command"])
            commands.append(cmd)
            execute_tool("run_command", {"command": cmd}, workspace=root, auto_approve_edits=True)
    return {"ok": True, "files": files, "commands": commands}


def _collect_diff(worktree: Path) -> str:
    out = _git(worktree, ["diff", "HEAD"])
    return str(out.get("stdout") or "")[:12000]


def _commit_if_needed(repo: dict[str, Any], message: str) -> dict[str, Any]:
    wt = Path(repo["worktree_path"])
    _ensure_zect_ignored(wt)
    porcelain = _git(wt, ["status", "--porcelain"])
    dirty = [
        ln
        for ln in (porcelain.get("stdout") or "").splitlines()
        if ln.strip() and ".zect/" not in ln.replace("\\", "/")
    ]
    if not dirty:
        sha = _head(wt)
        return {"ok": True, "skipped": "clean", "sha": sha, "duplicate": sha in (repo.get("committed_shas") or [])}
    # Never commit the same tree twice after a recorded SHA for this slice.
    current = _head(wt)
    if current and current in (repo.get("committed_shas") or []) and not (porcelain.get("stdout") or "").strip():
        return {"ok": True, "skipped": "already_committed", "sha": current, "duplicate": True}
    _git(wt, ["config", "user.email", "mentrix-coding-agent@zect.local"])
    _git(wt, ["config", "user.name", "Mentrix Coding Agent"])
    _git(wt, ["add", "-A"])
    commit = _git(wt, ["commit", "-m", message])
    sha = _head(wt)
    if not commit["ok"] and "nothing to commit" in (commit.get("stdout") or "").lower() + (
        commit.get("stderr") or ""
    ).lower():
        return {"ok": True, "skipped": "nothing_to_commit", "sha": sha, "duplicate": True}
    if not commit["ok"]:
        return {"ok": False, "error": commit.get("stderr") or commit.get("stdout") or "commit_failed"}
    if sha in (repo.get("committed_shas") or []):
        return {"ok": True, "skipped": "duplicate_sha", "sha": sha, "duplicate": True}
    repo.setdefault("committed_shas", []).append(sha)
    repo["head_sha"] = sha
    _write_checkpoint(repo)
    return {"ok": True, "sha": sha, "duplicate": False}


def _push_or_block(repo: dict[str, Any]) -> dict[str, Any]:
    wt = Path(repo["worktree_path"])
    origin = _git(wt, ["remote", "get-url", "origin"])
    url = (origin.get("stdout") or "").strip()
    if not origin.get("ok") or not url:
        return {
            "ok": True,
            "skipped": "no_origin",
            "blocked_external": False,
            "pr": {"note": "No origin remote; local commit only. Not a GitHub PASS."},
        }
    dry = (os.getenv("MENTRIX_PR_DRY_RUN") or "").strip().lower() in ("1", "true", "yes")
    token = (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or "").strip()
    is_github = "github.com" in url.lower()
    if is_github and (dry or not token):
        return {
            "ok": False,
            "blocked_external": True,
            "error": "BLOCKED_EXTERNAL",
            "detail": "Live GitHub push/PR not used (dry-run or token unset). Local commits remain.",
        }
    branch = str(repo.get("branch") or "HEAD")
    push = _git(wt, ["push", "-u", "origin", branch], timeout=90)
    if not push["ok"]:
        if is_github:
            return {"ok": False, "blocked_external": True, "error": "BLOCKED_EXTERNAL", "detail": push.get("stderr")}
        return {"ok": False, "error": push.get("stderr") or "push_failed"}
    pr: dict[str, Any] = {"pushed": True, "branch": branch, "head_sha": repo.get("head_sha")}
    if is_github and token and not dry:
        pr["url"] = ""  # URL filled by caller if gh available; never invent
        pr["note"] = "GitHub push succeeded; create PR via gh/API when configured."
    return {"ok": True, "blocked_external": False, "push": pr, "pr": pr}


def start_mission(
    *,
    goal: str,
    roots: list[dict[str, Any]],
    plan: str = "",
    patches_by_repo: dict[str, list[dict[str, Any]]] | None = None,
    work_item_id: int | None = None,
    project_id: int | None = None,
    workspace_parent: str = "",
) -> dict[str, Any]:
    if not (goal or "").strip():
        raise ValueError("goal_required")
    if not roots:
        raise ValueError("authorized_roots_required")
    mid = str(uuid.uuid4())
    from app.infrastructure.observability import current_correlation, new_id

    correlation_id = current_correlation() or new_id()
    plan_text = (plan or "").strip() or (
        f"# PLAN\n\nGoal: {goal.strip()}\n\n"
        f"Affected roots: {', '.join(str(r.get('label') or r.get('id')) for r in roots)}\n\n"
        "1. Isolate a worktree/branch per authorized root.\n"
        "2. Apply the change, run tests, do not hide sibling failures.\n"
        "3. Ultra Review the diff. Commit only after git approval.\n"
        "4. Push/PR only when the remote is available — never auto-merge.\n"
    )
    parent = Path(workspace_parent) if workspace_parent else Path(tempfile_parent(roots[0]))
    mission = {
        "id": mid,
        "goal": goal.strip(),
        "correlation_id": correlation_id,
        "phase": "awaiting_plan_approval",
        "status": "awaiting_plan_approval",
        "plan": plan_text,
        "plan_approved": False,
        "git_approved": False,
        "project_id": project_id,
        "work_item_id": work_item_id,
        "patches_by_repo": patches_by_repo or {},
        "workspace_parent": str(parent),
        "repos": [
            {
                "repository_id": r.get("id") or r.get("repository_id"),
                "label": r.get("label") or r.get("repo_name") or str(r.get("id")),
                "source_path": str(path_under_allowed_roots(str(r.get("path") or r.get("local_path") or ""))),
                "files": [],
                "commands": [],
                "committed_shas": [],
            }
            for r in roots
        ],
        "events": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    with _LOCK:
        _MISSIONS[mid] = mission
    _emit(mission, "plan", "PLAN ready — approve before isolated worktrees or edits.")
    return _public(mission)


def tempfile_parent(root: dict[str, Any]) -> Path:
    src = Path(str(root.get("path") or root.get("local_path") or "")).resolve()
    return src.parent / "zect-coding-worktrees"


def approve_plan(mission_id: str) -> dict[str, Any]:
    mission = _lookup(mission_id)
    if mission.get("status") == "cancelled":
        raise ValueError("mission_cancelled")
    mission["plan_approved"] = True
    mission["phase"] = "isolating"
    mission["status"] = "running"
    _emit(mission, "plan_approved", "PLAN approved. Isolating worktrees.")
    parent = Path(mission["workspace_parent"])
    parent.mkdir(parents=True, exist_ok=True)
    for repo in mission["repos"]:
        branch = f"zect-ca-{mission_id[:8]}-r{repo.get('repository_id')}"
        dest = parent / f"{repo.get('label')}-{mission_id[:8]}"
        iso = isolate_worktree(repo["source_path"], branch=branch, dest=dest)
        if not iso.get("ok"):
            repo["blocker"] = iso.get("error") or "worktree_failed"
            mission["phase"] = "blocked"
            mission["status"] = "blocked"
            _emit(mission, "blocked", f"Worktree failed for {repo.get('label')}", error=repo["blocker"])
            return _public(mission)
        repo["worktree_path"] = iso["worktree_path"]
        repo["branch"] = iso.get("branch") or branch
        repo["head_sha"] = iso.get("head_sha")
        repo["committed_shas"] = list(iso.get("committed_shas") or [])
        repo["main_unchanged"] = iso.get("main_unchanged")
        _write_checkpoint(repo)

    mission["phase"] = "editing"
    _emit(mission, "isolating", "Worktrees ready.")
    return _run_edit_test_review(mission)


def _stringify_patch_map(patches: dict[str, Any] | None) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = {}
    for key, value in (patches or {}).items():
        out[str(key)] = list(value or [])
    return out


def _patches_for_repo(patches_map: dict[str, Any], repo: dict[str, Any]) -> list[Any]:
    rid = repo.get("repository_id")
    for key in (str(rid), rid):
        got = patches_map.get(key) if isinstance(patches_map, dict) else None
        if got:
            return list(got)
    return []


def _run_edit_test_review(mission: dict[str, Any]) -> dict[str, Any]:
    patches_map = _stringify_patch_map(mission.get("patches_by_repo") if isinstance(mission.get("patches_by_repo"), dict) else {})
    diffs: list[str] = []
    per_repo_status: list[dict[str, Any]] = []
    for repo in mission["repos"]:
        if mission.get("status") == "cancelled":
            return _public(mission)
        patches = _patches_for_repo(patches_map, repo)
        wt = Path(repo["worktree_path"])
        applied = _apply_patches(wt, patches)
        if not applied.get("ok"):
            repo["blocker"] = applied.get("error") or "edit_failed"
            repo["test_ok"] = False
            repo["test_status"] = "fail"
            mission["phase"] = "blocked"
            mission["status"] = "blocked"
            _emit(mission, "blocked", f"Edit failed on {repo.get('label')}", error=repo["blocker"])
            return _public(mission)
        repo["files"] = list(applied.get("files") or [])
        repo["commands"] = list(applied.get("commands") or [])
        tests = run_repo_tests(wt)
        repo["test_ok"] = bool(tests.get("ok"))
        repo["test_status"] = tests.get("status")
        repo["test"] = tests
        if tests.get("command"):
            repo.setdefault("commands", []).append(tests["command"])
        if not tests.get("ok"):
            repo["blocker"] = f"tests_{tests.get('status')}"
        else:
            repo["blocker"] = ""
        diff = _collect_diff(wt)
        if diff:
            repo["diff"] = diff
        diffs.append(diff or str(repo.get("diff") or ""))
        per_repo_status.append(
            {
                "repository_id": repo.get("repository_id"),
                "label": repo.get("label"),
                "status": "pass" if tests.get("ok") else "fail",
            }
        )
        _emit(
            mission,
            "tests",
            f"{repo.get('label')}: {tests.get('status')}",
            repository_id=repo.get("repository_id"),
            ok=tests.get("ok"),
        )

    sibling = aggregate_sibling_status(per_repo_status)
    mission["sibling"] = sibling
    if sibling.get("blocked"):
        mission["phase"] = "blocked"
        mission["status"] = "blocked"
        mission["sibling"]["blocker"] = "sibling_failure"
        _emit(mission, "blocked", "PASS + FAIL ⇒ aggregate BLOCKED. Repair the failing sibling before READY.")
        return _public(mission)

    combined = "\n\n".join(d for d in diffs if d) or "# no unstaged diff (may already be committed)\n"
    review = review_diff(combined)
    local_findings: list[dict[str, Any]] = []
    for repo in mission["repos"]:
        local_findings.extend(scan_worktree_security(Path(repo["worktree_path"])))
    if local_findings:
        review = dict(review)
        review["passed"] = False
        review["critical_findings"] = int(review.get("critical_findings") or 0) + len(local_findings)
        review["findings"] = list(review.get("findings") or []) + local_findings
    mission["review"] = review
    if int(review.get("critical_findings") or 0) > 0:
        mission["phase"] = "blocked"
        mission["status"] = "blocked"
        _emit(mission, "blocked", "Ultra Review / security Critical/High — not READY_TO_MERGE.")
        return _public(mission)

    mission["phase"] = "awaiting_git_approval"
    mission["status"] = "awaiting_git_approval"
    _emit(mission, "review", "Ultra Review passed. Git commit/push requires explicit approval.")
    return _public(mission)


def approve_git(mission_id: str, *, commit: bool = True, push: bool = True) -> dict[str, Any]:
    mission = _lookup(mission_id)
    if mission.get("status") == "cancelled":
        raise ValueError("mission_cancelled")
    if mission.get("phase") == "blocked":
        raise ValueError("mission_blocked")
    if not mission.get("plan_approved"):
        raise ValueError("plan_not_approved")
    if mission.get("phase") not in ("awaiting_git_approval", "ready_to_merge", "pushing"):
        raise ValueError(f"unexpected_phase:{mission.get('phase')}")
    mission["git_approved"] = True
    mission["phase"] = "committing"
    _emit(mission, "git_approved", "Git approval recorded.")
    try:
        from app.infrastructure.observability import emit_privileged

        emit_privileged(
            action="coding_mission_git_approve",
            resource_type="coding_mission",
            resource_name=str(mission_id),
            details={"phase": mission.get("phase")},
        )
    except Exception:
        pass
    if commit:
        for repo in mission["repos"]:
            result = _commit_if_needed(repo, f"zect coding-agent: {mission.get('goal', '')[:72]}")
            repo["last_commit"] = result
            if result.get("duplicate"):
                _emit(mission, "commit", f"{repo.get('label')}: skipped duplicate commit", sha=result.get("sha"))
            elif not result.get("ok"):
                mission["phase"] = "blocked"
                mission["status"] = "blocked"
                repo["blocker"] = result.get("error")
                return _public(mission)
            else:
                _emit(mission, "commit", f"{repo.get('label')} @{result.get('sha', '')[:8]}")
    if push:
        mission["phase"] = "pushing"
        any_ext = False
        for repo in mission["repos"]:
            result = _push_or_block(repo)
            repo["push"] = result
            repo["pr"] = result.get("pr") or {}
            if result.get("blocked_external"):
                any_ext = True
                _emit(mission, "blocked_external", f"{repo.get('label')}: {result.get('detail') or 'BLOCKED_EXTERNAL'}")
            elif not result.get("ok"):
                mission["phase"] = "blocked"
                mission["status"] = "blocked"
                repo["blocker"] = result.get("error")
                return _public(mission)
        if any_ext:
            mission["ci"] = {"status": "BLOCKED_EXTERNAL", "detail": "GitHub push/PR not completed"}
        else:
            mission["ci"] = {"status": "local_push", "detail": "Pushed to origin (no auto-merge)"}
    mission["phase"] = "ready_to_merge"
    mission["status"] = "ready_to_merge"
    _emit(mission, "ready_to_merge", "READY_TO_MERGE locally. Human merge only — no auto-merge.")
    return _public(mission)


def cancel_mission(mission_id: str) -> dict[str, Any]:
    mission = _lookup(mission_id)
    mission["status"] = "cancelled"
    mission["phase"] = "cancelled"
    _emit(mission, "cancelled", "Mission cancelled. Worktrees and recorded commits preserved.")
    try:
        from app.infrastructure.observability import emit_privileged

        emit_privileged(
            action="coding_mission_cancel",
            resource_type="coding_mission",
            resource_name=str(mission_id),
            details={"phase": mission.get("phase"), "status": "cancelled"},
        )
    except Exception:
        pass
    for repo in mission.get("repos") or []:
        if repo.get("worktree_path"):
            _write_checkpoint(repo)
    return _public(mission)


def resume_mission(mission_id: str) -> dict[str, Any]:
    mission = _lookup(mission_id)
    if mission.get("phase") == "ready_to_merge":
        _save_mission(mission)
        return _public(mission)
    mission["status"] = "running"
    if not mission.get("plan_approved"):
        mission["phase"] = "awaiting_plan_approval"
        _save_mission(mission)
        return _public(mission)
    if not all(r.get("worktree_path") for r in mission["repos"]):
        return approve_plan(mission_id)
    _emit(mission, "resume", "Resuming from checkpoint. Duplicate commits skipped.")
    return _run_edit_test_review(mission)


def retry_mission(mission_id: str) -> dict[str, Any]:
    return resume_mission(mission_id)


def repair_and_retry(mission_id: str, patches_by_repo: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    mission = _lookup(mission_id)
    merged = _stringify_patch_map(mission.get("patches_by_repo") if isinstance(mission.get("patches_by_repo"), dict) else {})
    merged.update(_stringify_patch_map(patches_by_repo))
    mission["patches_by_repo"] = merged
    mission["status"] = "running"
    mission["sibling"] = {}
    mission["review"] = {}
    for repo in mission.get("repos") or []:
        repo["blocker"] = ""
    _emit(mission, "repair", "Applying sibling repair patches.")
    return _run_edit_test_review(mission)
