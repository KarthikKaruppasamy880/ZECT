"""Mentrix Coding Agent production lifecycle.

Requirement → PLAN → approval → isolated worktree → edit → tests → diagnose →
Ultra Review → commit → push/PR. Does not auto-merge. Sibling PASS+FAIL ⇒ BLOCKED.
Cancel/resume skips already-recorded commit SHAs so retries cannot duplicate them.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
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

# Process-local set of mission_ids with a live approve_plan/resume_mission
# thread executing right now, in THIS process. Deliberately not persisted:
# after a backend restart nothing is running until something resumes it,
# which is the truthful signal mission_execution_state() needs.
_RUNNING_LOCK = threading.Lock()
_RUNNING_MISSIONS: set[str] = set()


def _mark_running(mission_id: str) -> None:
    with _RUNNING_LOCK:
        _RUNNING_MISSIONS.add(mission_id)


def _mark_stopped(mission_id: str) -> None:
    with _RUNNING_LOCK:
        _RUNNING_MISSIONS.discard(mission_id)


def is_mission_running(mission_id: str) -> bool:
    with _RUNNING_LOCK:
        return mission_id in _RUNNING_MISSIONS


def mission_execution_state(mission: dict[str, Any]) -> str:
    """Truthful "is this mission actually executing right now" signal --
    distinct from its last-saved phase. A mission can sit at a mid-flight
    phase like "editing" with no live thread anywhere (backend restarted, or
    the executing thread died) and that must read as "recoverable", not
    "running", so History never lies about a stuck process.
    """
    mid = str(mission.get("id") or "")
    if is_mission_running(mid):
        return "running"
    phase = mission.get("phase")
    if phase == "blocked":
        return "blocked"
    if phase == "cancelled":
        return "stopped"
    if phase in ("ready_to_merge", "awaiting_git_approval"):
        return "completed"
    if phase == "awaiting_plan_approval":
        return "stopped"
    # isolating / editing / committing / pushing with nothing live executing
    # it right now: mid-flight but not actually running -- recoverable via
    # resume_mission()/retry_mission(), not silently shown as "running".
    return "recoverable"


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


_EVENT_TO_AGENT = (
    ("explore_", "explore"),
    ("diagnose_", "debugger"),
    ("browser_verify_", "tester"),
    ("native_implement", "coder"),
    ("evidence_verify_", "reviewer"),
    ("review", "reviewer"),
)


def _agents_involved(mission: dict[str, Any]) -> list[str]:
    """Derive which Mentrix Lead roles actually touched this mission from its
    own event names, rather than a separately-tracked field -- one source of
    truth (the event stream), consistent everywhere a mission is read."""
    seen: list[str] = []
    for ev in mission.get("events") or []:
        name = str(ev.get("event") or "")
        for prefix, agent in _EVENT_TO_AGENT:
            if name.startswith(prefix) and agent not in seen:
                seen.append(agent)
                break
    return seen


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
                "patches_applied": r.get("patches_applied"),
                "test_stdout": (
                    str(r.get("test_stdout") or (r.get("test") or {}).get("stdout") or "")[-800:]
                    if not r.get("test_ok")
                    else ""
                ),
                "test_stderr": (
                    str((r.get("test") or {}).get("stderr") or "")[-400:] if not r.get("test_ok") else ""
                ),
                "files": list(r.get("files") or []),
                "commands": list(r.get("commands") or []),
                "blocker": r.get("blocker") or "",
                "auto_repair_attempts": r.get("auto_repair_attempts") or 0,
                "committed_shas": list(r.get("committed_shas") or []),
                "diff": str(r.get("diff") or "")[:8000],
                "push": r.get("push") or {},
                "pr": r.get("pr") or {},
                "native_build": r.get("native_build") or {},
                "browser_verification": r.get("browser_verification") or {},
                "explore_findings": r.get("explore_findings") or "",
                "evidence_verification": r.get("evidence_verification") or {},
            }
        )
    sibling = mission.get("sibling") or {}
    return {
        "id": mission["id"],
        "goal": mission.get("goal"),
        "mode": mission.get("mode") or "",
        "source": mission.get("source") or "coding_agent",
        "agents": _agents_involved(mission),
        "started_at": mission.get("created_at"),
        "phase": mission.get("phase"),
        "status": mission.get("status"),
        "plan": mission.get("plan"),
        "plan_hash": mission.get("plan_hash") or "",
        "plan_approved_hash": mission.get("plan_approved_hash") or "",
        "plan_approved": bool(mission.get("plan_approved")),
        "git_approved": bool(mission.get("git_approved")),
        "context_used": mission.get("context_used"),
        "primary_repository_id": mission.get("primary_repository_id"),
        # CP-06: structured VALID/INVALID/STALE + findings from the last
        # approve-plan attempt, so the UI can show *why* Approve & Build is
        # blocked instead of just a generic 409.
        "plan_validation": mission.get("plan_validation"),
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
        "propose_if_empty": bool(mission.get("propose_if_empty")),
        "sibling": sibling,
        "ready_to_merge": mission.get("phase") == "ready_to_merge",
        "companion_edits_code": False,
        "native_implement": mission.get("native_implement") or [],
        "no_auto_merge": True,
        "persistence": "durable_json",
        "execution_state": mission_execution_state(mission),
        "updated_at": mission.get("updated_at"),
        "events": list(mission.get("events") or [])[-40:],
        "evidence": list(mission.get("events") or [])[-40:],
    }


def get_mission(mission_id: str) -> dict[str, Any]:
    return _public(_lookup(mission_id))


def get_mission_events(mission_id: str, *, after: int = 0) -> list[dict[str, Any]]:
    """CP-09 -- the full (unlike _public()'s last-40 slice), cursor-filtered
    event list the Mission/EventStream SSE endpoint sends. `after` is the
    `seq` of the last event a client already has -- 0 gets everything, so
    a client with no prior cursor (fresh tab, post-refresh, post-restart)
    replays this Mission's entire recorded history from disk rather than
    only whatever fits in a last-N slice.
    """
    mission = _lookup(mission_id)
    events = mission.get("events") or []
    return [e for e in events if int(e.get("seq") or 0) > after]


def list_missions(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Project the canonical durable Mission store as a history list --
    reads the same JSON files _lookup()/_load_mission_from_disk() use, so
    History is never a second store: it is the Mission/Event persistence
    itself, just enumerated. Survives navigation and backend restart because
    the underlying files do.
    """
    directory = missions_dir()
    if not directory.is_dir():
        return []
    entries: list[tuple[float, dict[str, Any]]] = []
    for path in directory.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or not data.get("id"):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        entries.append((mtime, data))
    entries.sort(key=lambda pair: pair[0], reverse=True)
    window = entries[offset : offset + max(0, limit)]
    return [_public(data) for _, data in window]


def _next_event_seq(mission: dict[str, Any]) -> int:
    seq = int(mission.get("_event_seq") or 0) + 1
    mission["_event_seq"] = seq
    return seq


def _emit(mission: dict[str, Any], event: str, message: str, **data: Any) -> None:
    if (mission.get("status") == "cancelled" or mission.get("phase") == "cancelled") and event != "cancelled":
        return
    # Copy scalars only — never share the live kwargs dict with redact/telemetry
    # (that dict is also stored on the mission and JSON-persisted).
    extra: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            extra[key] = value
        else:
            extra[key] = str(value)[:200]
    # CP-09: `seq` is the canonical, monotonic ordinal the Mission/
    # EventStream SSE endpoint cursors on (?after=<seq>) -- every event a
    # Mission ever records, from this function or from
    # _bridge_native_events() below, shares this one counter so a client
    # reconnecting after a tab switch/refresh/backend restart can resume
    # from exactly where it left off without re-deriving position from
    # list length (which would break once events get pruned/rotated).
    mission.setdefault("events", []).append(
        {"event": event, "message": message, "data": extra, "at": _now(), "seq": _next_event_seq(mission)}
    )
    mission["updated_at"] = _now()
    _save_mission(mission)
    try:
        from app.infrastructure.observability import emit_event

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
            work_item_id=mission.get("work_item_id") if isinstance(mission.get("work_item_id"), int) else None,
            project_id=mission.get("project_id") if isinstance(mission.get("project_id"), int) else None,
            failure_class=fail,
            extra=dict(extra),
        )
    except Exception:
        pass


def _bridge_native_events(
    mission: dict[str, Any], run_id: str, *, role: str = "", repository_id: Any = None
) -> None:
    """CP-09 -- the fine-grained per-tool-call activity (files read,
    commands run, individual model routing/token/cost calls) happens on
    MentrixNativeCodingRuntime's OWN in-memory run; lifecycle.py's mission
    previously only ever recorded the coarse summary _emit() calls
    sprinkled around each role invocation, so a backend restart mid-build
    silently lost every read_file/write_file/run_command/model_call the
    native loop actually did, and the Developer Agent pane's activity feed
    could never show them at all. Bridges that run's full event list into
    the Mission's own durable, JSON-persisted event log -- the ONE
    canonical activity store the live feed and History both read from --
    in a single batch/save rather than replaying _emit() per tool call
    (which would trigger one redundant disk write per event).
    """
    if not run_id or (mission.get("status") == "cancelled" or mission.get("phase") == "cancelled"):
        return
    try:
        from app.adapters.coding_runtime import get_mentrix_native_runtime

        run = get_mentrix_native_runtime().get_run(run_id)
    except Exception:  # noqa: BLE001 -- bridging must never fail a build
        return
    events = list(run.get("events") or [])
    if not events:
        return
    appended: list[dict[str, Any]] = []
    for e in events:
        appended.append(
            {
                "event": str(e.get("event") or ""),
                "message": str(e.get("message") or ""),
                "data": e.get("data") or {},
                "at": str(e.get("timestamp") or _now()),
                "seq": _next_event_seq(mission),
                "phase": str(e.get("phase") or ""),
                "role": str(e.get("agent_id") or role or ""),
                "tool": str(e.get("tool") or ""),
                "repository_id": repository_id,
                "provider": str(e.get("provider") or ""),
                "model": str(e.get("model") or ""),
                "routing_reason": str(e.get("routing_reason") or ""),
                "input_tokens": int(e.get("input_tokens") or 0),
                "output_tokens": int(e.get("output_tokens") or 0),
                "cached_tokens": int(e.get("cached_tokens") or 0),
                "estimated_cost": float(e.get("estimated_cost") or 0.0),
                "duration_ms": e.get("duration_ms"),
                "status": str(e.get("status") or ""),
                "evidence_refs": list(e.get("evidence_refs") or []),
                "source_run_id": run_id,
            }
        )
    mission.setdefault("events", []).extend(appended)
    mission["updated_at"] = _now()
    _save_mission(mission)


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
    # Same policy as plan storage (.zect/ is agent scratch, never the user's
    # commit) -- kept in one place rather than reimplemented here.
    from app.services.coding_engine.plan_store import ensure_zect_ignored

    ensure_zect_ignored(worktree)


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


def _locate_pytest(worktree: Path) -> tuple[Path, Path] | None:
    """Prefer nested ZOAS tests over missing repo-root tests/."""
    pairs = [
        (worktree, worktree / "tests"),
        (worktree / "zinnia-modern" / "backend", worktree / "zinnia-modern" / "backend" / "tests"),
        (worktree / "backend", worktree / "backend" / "tests"),
    ]
    for cwd, tests_dir in pairs:
        if tests_dir.is_dir() and any(tests_dir.glob("test_*.py")):
            return cwd.resolve(), tests_dir.resolve()
    return None


def _run_pytest_only(worktree: Path) -> dict[str, Any]:
    located = _locate_pytest(worktree)
    if not located:
        return {"ok": True, "status": "skipped", "kind": "none", "detail": "no tests/"}
    cwd, tests_dir = located
    import sys

    root = resolve_workspace(str(cwd))
    cfg_path = ""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".ini", delete=False, encoding="utf-8") as cfg:
            cfg.write("[pytest]\naddopts =\npythonpath = .\n")
            cfg_path = cfg.name
        child_env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST")}
        child_env["PYTHONPATH"] = str(root)
        child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        child_env["PYTEST_ADDOPTS"] = ""
        child_env["PYTHONDONTWRITEBYTECODE"] = "1"
        argv = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "--noconftest",
            f"--confcutdir={root}",
            f"--rootdir={root}",
            "-c",
            cfg_path,
            "--import-mode=prepend",
            "-p",
            "no:cacheprovider",
            str(tests_dir),
        ]
        completed = subprocess.run(
            argv,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=90,
            env=child_env,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "status": "fail",
            "kind": "pytest",
            "exit_code": None,
            "stdout": "",
            "stderr": "timeout",
            "command": "pytest",
        }
    finally:
        if cfg_path:
            try:
                os.unlink(cfg_path)
            except OSError:
                pass
    ok = completed.returncode == 0
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "kind": "pytest",
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "")[-1200:],
        "stderr": (completed.stderr or "")[-600:],
        "command": " ".join(argv),
    }


def _run_js_suite(worktree: Path) -> dict[str, Any]:
    """Run package.json test / Playwright when those files exist. Skip if neither exists."""
    root = Path(worktree)
    pkg = root / "package.json"
    has_pw = any(
        (root / name).is_file()
        for name in ("playwright.config.ts", "playwright.config.js", "playwright.config.mts")
    )
    if not pkg.is_file() and not has_pw:
        return {"ok": True, "status": "skipped", "kind": "none", "detail": "no package.json/playwright"}
    cmd = ""
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        scripts = data.get("scripts") if isinstance(data, dict) else {}
        scripts = scripts if isinstance(scripts, dict) else {}
        if "test" in scripts:
            cmd = "npm test --silent"
        elif "test:e2e" in scripts:
            cmd = "npm run test:e2e --silent"
    if not cmd and has_pw:
        cmd = "npx --yes playwright test --reporter=line"
    if not cmd:
        return {"ok": True, "status": "skipped", "kind": "none", "detail": "no test script"}
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=180,
            shell=True,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "status": "fail",
            "kind": "js",
            "detail": "timeout",
            "command": cmd,
            "stdout": "",
            "stderr": "timeout",
        }
    ok = completed.returncode == 0
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "kind": "playwright" if "playwright" in cmd else "npm",
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "")[-1200:],
        "stderr": (completed.stderr or "")[-600:],
        "command": cmd,
    }


def run_repo_tests(worktree: Path) -> dict[str, Any]:
    py = _run_pytest_only(worktree)
    js = _run_js_suite(worktree)
    if js.get("kind") == "none":
        return py
    if py.get("kind") == "none":
        return js
    ok = bool(py.get("ok")) and bool(js.get("ok"))
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "kind": f"{py.get('kind')}+{js.get('kind')}",
        "detail": f"{py.get('status')}; {js.get('status')}",
        "stdout": ((py.get("stdout") or "") + "\n" + (js.get("stdout") or ""))[-2000:],
        "stderr": ((py.get("stderr") or "") + "\n" + (js.get("stderr") or ""))[-1200:],
        "command": f"{py.get('command') or ''} ; {js.get('command') or ''}",
        "recipes": [py, js],
    }


def _pyproject_has_section(pyproject: Path, section: str) -> bool:
    if not pyproject.is_file():
        return False
    try:
        text = pyproject.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return f"[{section}]" in text


def _run_py_lint(worktree: Path) -> dict[str, Any]:
    """Only runs when the repo itself declares ruff config AND ruff is on
    PATH -- a repo with neither is not blocked by a gate it never opted into."""
    root = Path(worktree)
    configured = (
        (root / "ruff.toml").is_file()
        or (root / ".ruff.toml").is_file()
        or _pyproject_has_section(root / "pyproject.toml", "tool.ruff")
    )
    if not configured or not shutil.which("ruff"):
        return {"ok": True, "status": "skipped", "kind": "none", "detail": "no ruff config/binary"}
    try:
        completed = subprocess.run(
            ["ruff", "check", "."], cwd=str(root), capture_output=True, text=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "status": "fail",
            "kind": "ruff",
            "detail": "timeout",
            "command": "ruff check .",
            "stdout": "",
            "stderr": "timeout",
        }
    ok = completed.returncode == 0
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "kind": "ruff",
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "")[-1200:],
        "stderr": (completed.stderr or "")[-600:],
        "command": "ruff check .",
    }


def _run_py_typecheck(worktree: Path) -> dict[str, Any]:
    root = Path(worktree)
    configured = (
        (root / "mypy.ini").is_file()
        or (root / ".mypy.ini").is_file()
        or _pyproject_has_section(root / "pyproject.toml", "tool.mypy")
    )
    if not configured or not shutil.which("mypy"):
        return {"ok": True, "status": "skipped", "kind": "none", "detail": "no mypy config/binary"}
    try:
        completed = subprocess.run(
            ["mypy", "."], cwd=str(root), capture_output=True, text=True, timeout=90
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "status": "fail",
            "kind": "mypy",
            "detail": "timeout",
            "command": "mypy .",
            "stdout": "",
            "stderr": "timeout",
        }
    ok = completed.returncode == 0
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "kind": "mypy",
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "")[-1200:],
        "stderr": (completed.stderr or "")[-600:],
        "command": "mypy .",
    }


def _run_js_script_gate(worktree: Path, script_name: str, kind: str) -> dict[str, Any]:
    """Run a package.json script iff the repo itself declares it -- so "lint"/
    "typecheck"/"build" mean whatever tooling the repo already wired up
    (eslint, tsc, next build, vite build, ...) instead of us guessing a
    command that may not match the project."""
    root = Path(worktree)
    pkg = root / "package.json"
    if not pkg.is_file():
        return {"ok": True, "status": "skipped", "kind": "none", "detail": "no package.json"}
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    scripts = data.get("scripts") if isinstance(data, dict) else {}
    scripts = scripts if isinstance(scripts, dict) else {}
    if script_name not in scripts:
        return {"ok": True, "status": "skipped", "kind": "none", "detail": f"no {script_name} script"}
    cmd = f"npm run {script_name} --silent"
    try:
        completed = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=180, shell=True)
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "status": "fail",
            "kind": kind,
            "detail": "timeout",
            "command": cmd,
            "stdout": "",
            "stderr": "timeout",
        }
    ok = completed.returncode == 0
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "kind": kind,
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "")[-1200:],
        "stderr": (completed.stderr or "")[-600:],
        "command": cmd,
    }


def run_repo_quality_gates(worktree: Path) -> dict[str, Any]:
    """Deterministic lint/typecheck/build checks, run alongside (before)
    run_repo_tests. Each individual gate is skipped -- not failed -- when the
    repo has no matching config/script, so this never blocks a repo on
    tooling it never opted into. See Phase D of
    ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md: previously
    lint/typecheck/build were left entirely to the Coder/Debugger role's own
    discretion via generic run_command, with no orchestrated pass/fail gate.
    """
    steps = [
        _run_py_lint(worktree),
        _run_py_typecheck(worktree),
        _run_js_script_gate(worktree, "lint", "eslint"),
        _run_js_script_gate(worktree, "typecheck", "tsc"),
        _run_js_script_gate(worktree, "build", "build"),
    ]
    ran = [s for s in steps if s.get("kind") != "none"]
    if not ran:
        return {"ok": True, "status": "skipped", "kind": "none", "detail": "no lint/typecheck/build configured"}
    failed = [s for s in ran if not s.get("ok")]
    ok = not failed
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "kind": "+".join(str(s.get("kind")) for s in ran),
        "detail": "; ".join(f"{s.get('kind')}:{s.get('status')}" for s in ran),
        "stdout": "\n".join((s.get("stdout") or "") for s in (failed or ran))[-2000:],
        "stderr": "\n".join((s.get("stderr") or "") for s in (failed or ran))[-1200:],
        "command": " ; ".join(str(s.get("command") or "") for s in ran if s.get("command")),
        "recipes": steps,
    }


def _run_quality_and_tests(worktree: Path) -> dict[str, Any]:
    """The gate a repo's change must clear: lint/typecheck/build (when
    configured) MUST pass before tests are even attempted, mirroring ordinary
    CI ordering and avoiding a wasted test run against code that doesn't
    build. Returns the same shape as run_repo_tests (ok/status/kind/stdout/
    stderr/command) so existing callers of run_repo_tests need no changes --
    a quality-gate failure is reported through the identical fields a test
    failure would use, and the auto-repair loop treats both uniformly.
    """
    quality = run_repo_quality_gates(worktree)
    if not quality.get("ok"):
        return quality
    tests = run_repo_tests(worktree)
    if quality.get("kind") != "none":
        tests = dict(tests)
        tests["quality"] = quality
    return tests


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


def _apply_patches(mission: dict[str, Any], repo: dict[str, Any], worktree: Path, patches: list[dict[str, Any]]) -> dict[str, Any]:
    root = resolve_workspace(str(worktree))
    files: list[str] = []
    commands: list[str] = []
    # CP-07: a Mission with no work_item_id never went through ASK/PLAN and
    # has no FILE_IMPACTS.json to check against -- same scope boundary
    # CP-06's _plan_validation_gate already uses, preserved here rather
    # than newly gating Missions built from hand-supplied patches (e.g.
    # test_coding_agent_production.py's Missions A-G). Any Mission that
    # DOES carry a work_item_id is fail-closed from here on.
    work_item_id = mission.get("work_item_id")
    for patch in patches or []:
        path = str(patch.get("path") or "").strip()
        if not path:
            continue
        tool_name = "write_file" if patch.get("content") is not None else "apply_patch"
        if work_item_id:
            from app.services.coding_engine import agent_write_policy

            decision = agent_write_policy.evaluate_write(
                work_item_id=work_item_id,
                repo_id=repo.get("repository_id"),
                tool_name=tool_name,
                path=path,
                workspace=root,
            )
            if not decision.allowed:
                _emit(
                    mission,
                    "agent_write_blocked",
                    f"{repo.get('label')}: write to {path} refused ({decision.reason})",
                    repository_id=repo.get("repository_id"),
                    path=path,
                    reason=decision.reason,
                    detail=decision.detail,
                )
                return {"ok": False, "error": f"write_blocked:{decision.reason}", "path": path, "files": files}
            _emit(
                mission,
                "agent_write_allowed",
                f"{repo.get('label')}: write to {path} authorized ({decision.matched_action})",
                repository_id=repo.get("repository_id"),
                path=path,
            )
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
            expected = str(patch.get("content") or patch.get("new_text") or patch.get("new") or "")
            if expected:
                check = execute_tool("read_file", {"path": path}, workspace=root, auto_approve_edits=True)
                if expected not in str(check.get("content") or ""):
                    return {"ok": False, "error": "patch_not_visible", "path": path, "files": files}
        elif not out.get("ok"):
            return {"ok": False, "error": out.get("error") or "patch_failed", "path": path, "files": files}
        if patch.get("command"):
            cmd = str(patch["command"])
            commands.append(cmd)
            # CP-09A: this call's result used to be discarded entirely --
            # a command needing approval (or one that simply failed) ran
            # (or silently didn't) with the patch still reported "ok".
            # command_governance classifies every command; anything
            # outside READ_ONLY/BUILD/TEST/APP_RUNNER needs_approval and
            # must block the mission with a visible reason, same as a
            # blocked write_file/apply_patch above -- never a silent no-op.
            from app.services.coding_engine.command_governance import classify_command

            category = classify_command(cmd)
            cmd_out = execute_tool("run_command", {"command": cmd}, workspace=root, auto_approve_edits=True)
            if cmd_out.get("needs_approval"):
                _emit(
                    mission,
                    "tool_blocked",
                    f"{repo.get('label')}: command requires approval ({category}): {cmd[:160]}",
                    repository_id=repo.get("repository_id"),
                    category=category,
                    command=cmd[:400],
                )
                return {
                    "ok": False,
                    "error": f"command_blocked:{category}",
                    "path": path,
                    "files": files,
                    "commands": commands,
                }
            if not cmd_out.get("ok"):
                _emit(
                    mission,
                    "tool_failed",
                    f"{repo.get('label')}: command failed ({cmd_out.get('error')}): {cmd[:160]}",
                    repository_id=repo.get("repository_id"),
                    category=category,
                )
                return {
                    "ok": False,
                    "error": cmd_out.get("error") or "command_failed",
                    "path": path,
                    "files": files,
                    "commands": commands,
                }
            _emit(
                mission,
                "command_completed",
                f"{repo.get('label')}: {cmd[:160]}",
                repository_id=repo.get("repository_id"),
                category=category,
            )
    return {"ok": True, "files": files, "commands": commands}


def _collect_diff(worktree: Path) -> str:
    out = _git(worktree, ["diff", "HEAD"])
    return str(out.get("stdout") or "")[:12000]


def verify_mission_evidence(mission: dict[str, Any], repo: dict[str, Any], worktree: Path) -> dict[str, Any]:
    """Independently re-check this repo's claims against the actual worktree/git
    state and the mission's own event timeline, instead of trusting self-reported
    flags. Critical findings block the mission (see caller); warnings are recorded
    but never block -- ``diff_text`` is truncated at 12000 chars by ``_collect_diff``,
    so a legitimately large change can look "missing" from it without being wrong.
    """
    findings: list[dict[str, Any]] = []

    claimed_files = list(repo.get("files") or [])
    for path in claimed_files:
        if not (worktree / path).exists():
            findings.append({"severity": "critical", "code": "claimed_file_missing", "detail": path})

    diff_text = str(repo.get("diff") or "")
    if len(diff_text) < 12000:
        for path in claimed_files:
            marker = path.replace("\\", "/")
            if marker and marker not in diff_text.replace("\\", "/") and (worktree / path).exists():
                findings.append({"severity": "warning", "code": "claimed_file_not_in_diff", "detail": path})

    current_head = _head(worktree)
    committed = list(repo.get("committed_shas") or [])
    expected_head = committed[-1] if committed else str(repo.get("head_sha") or "")
    if expected_head and current_head and current_head != expected_head:
        findings.append(
            {
                "severity": "critical",
                "code": "worktree_sha_drift",
                "detail": f"expected {expected_head[:12]}, found {current_head[:12]}",
            }
        )

    browser = repo.get("browser_verification") or {}
    if browser.get("ran") and browser.get("verified"):
        events = mission.get("events") or []
        has_evidence = any(
            e.get("event") == "browser_verify_result"
            and (e.get("data") or {}).get("repository_id") == repo.get("repository_id")
            and bool((e.get("data") or {}).get("ok"))
            for e in events
        )
        if not has_evidence:
            findings.append(
                {
                    "severity": "critical",
                    "code": "browser_verification_unevidenced",
                    "detail": "verified=True has no matching browser_verify_result event in the mission timeline",
                }
            )

    critical = [f for f in findings if f.get("severity") == "critical"]
    return {"ok": not critical, "findings": findings}


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
    propose_if_empty: bool = False,
    mode: str = "",
    source: str = "",
    primary_repository_id: int | None = None,
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
        "mode": mode.strip(),
        "source": source.strip() or "coding_agent",
        "correlation_id": correlation_id,
        "phase": "awaiting_plan_approval",
        "status": "awaiting_plan_approval",
        "plan": plan_text,
        "plan_hash": hashlib.sha256(plan_text.encode("utf-8")).hexdigest(),
        "plan_approved": False,
        "plan_approved_hash": "",
        "git_approved": False,
        "project_id": project_id,
        "work_item_id": work_item_id,
        # The WorkItem's own sticky repository_id, when known -- the single
        # authoritative "which repo is primary" fact for this Mission, so
        # patch proposal/application (propose_patches.py) doesn't have to
        # guess from roots[0] ordering (finding A2 / CP-01). Falls back to
        # the first authorized root only when no WorkItem binding exists.
        "primary_repository_id": primary_repository_id
        or (roots[0].get("id") or roots[0].get("repository_id") if roots else None),
        "patches_by_repo": _stringify_patch_map(patches_by_repo),
        "propose_if_empty": bool(propose_if_empty),
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
    mid = _safe_mission_id(mission_id)
    _mark_running(mid)
    try:
        return _approve_plan_impl(mid)
    finally:
        _mark_stopped(mid)


def approve_plan_in_background(mission_id: str) -> dict[str, Any]:
    """Kick off approve_plan() on a daemon thread and return immediately with
    the mission's current (pre-execution) state, for callers that must not
    block the HTTP response on a multi-minute mission run (see
    domains/agent_run/agent_mode.py). The mission is marked running before
    the thread starts, so a caller that polls get_mission() right away still
    observes "running", not a race where it briefly looks idle.
    """
    mid = _safe_mission_id(mission_id)
    _mark_running(mid)

    def _run() -> None:
        try:
            _approve_plan_impl(mid)
        finally:
            _mark_stopped(mid)

    threading.Thread(target=_run, daemon=True).start()
    return get_mission(mid)


def _plan_validation_gate(mission: dict[str, Any]) -> "plan_validator.PlanValidationResult | None":
    """Returns None when this Mission is out of scope for CP-06 (no
    work_item_id, or that WorkItem never produced a grounded-plan machine
    contract) -- lifecycle.py is deliberately DB-decoupled everywhere else,
    so this opens a short-lived session only for this one lookup and fails
    OPEN (returns None, preserving prior behavior) on any unexpected error
    rather than blocking a Mission that has nothing to do with the
    grounded ASK/PLAN pipeline this gate targets."""
    wi_id = mission.get("work_item_id")
    if not wi_id:
        return None
    try:
        import json as _json

        from app.domains.work_items import service as wi_svc
        from app.infrastructure.database import SessionLocal
        from app.services.work_items import plan_generator, plan_validator
        from app.services.work_items.artifact_store import ArtifactStore, plan_hash_bytes
        from app.services.work_items.context_package import ContextPackage
        from app.services.work_items.multi_repo_context import repo_binding

        db = SessionLocal()
        try:
            wi = wi_svc.get_work_item(db, int(wi_id))
            store = ArtifactStore(wi.id)
            sidecar = store.read_json("FILE_IMPACTS.json", default=None) or None
            if not sidecar:
                return None
            plan_text = str(mission.get("plan") or "")
            current_hash = plan_hash_bytes(plan_text) if plan_text.strip() else ""
            repo_local_path = str(repo_binding(db, wi.repository_id).get("local_path") or "") if wi.repository_id else ""
            architecture = (
                plan_generator.detect_repo_architecture(repo_local_path)
                if repo_local_path
                else plan_generator.RepoArchitecture(primary_language="unknown", build_system="unknown")
            )
            context_package = None
            raw = (wi.context_snapshot_json or "").strip()
            if raw and raw != "{}":
                data = _json.loads(raw)
                if data:
                    context_package = ContextPackage.from_dict(data)
            return plan_validator.validate_plan_for_approval(
                work_item_id=wi.id,
                primary_repo_id=wi.repository_id,
                base_commit_sha=wi.base_commit_sha or "",
                recorded_plan_hash=wi.plan_hash or "",
                plan_text=plan_text,
                current_plan_hash=current_hash,
                sidecar=sidecar,
                context_package=context_package,
                repo_root=repo_local_path or ".",
                architecture=architecture,
            )
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        return None


def _approve_plan_impl(mission_id: str) -> dict[str, Any]:
    mission = _lookup(mission_id)
    if mission.get("status") == "cancelled":
        raise ValueError("mission_cancelled")

    # CP-06: this is the actual "Approve & Build" button's call path (the
    # Developer Workspace UI hits POST /api/coding-agent/missions/{id}/
    # approve-plan, never developer_service.py's WorkItem-level
    # approve_plan) -- so the hard pre-approval gate belongs here, not
    # there. Only enforced when this Mission is tied to a WorkItem that
    # actually went through the grounded ASK/PLAN pipeline (has a
    # FILE_IMPACTS.json machine contract); a Mission created directly
    # without a work_item_id, or one whose WorkItem never called
    # developer plan(), was never part of that flow and keeps its
    # pre-CP-06 behavior (silent re-hash on drift) unchanged.
    gate = _plan_validation_gate(mission)
    if gate is not None and not gate.ok:
        detail = "; ".join(f"{f.rule}: {f.detail}" for f in gate.findings) or gate.status
        _emit(mission, "plan_validation_failed", f"PLAN failed validation ({gate.status}): {detail}")
        mission["plan_validation"] = gate.to_dict()
        raise ValueError(f"plan_validation_failed:{gate.status}")
    if gate is not None:
        mission["plan_validation"] = gate.to_dict()

    existing = _stringify_patch_map(mission.get("patches_by_repo"))
    has_patches = any(existing.get(str(k)) for k in existing)
    if mission.get("propose_if_empty") and not has_patches:
        from app.services.coding_engine.propose_patches import propose_from_plan

        try:
            proposed = propose_from_plan(mission)
        except ValueError as exc:
            if str(exc) == "llm_offline":
                raise ValueError("llm_offline") from exc
            proposed = {}
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"propose_patches_failed:{exc}") from exc
        mission["patches_by_repo"] = _stringify_patch_map(proposed)
        n = sum(len(v) for v in (proposed or {}).values())
        _emit(mission, "patches_proposed", f"Proposed {n} patch(es) from PLAN + ContextPack.")
        if n == 0:
            mission["native_implement_pending"] = True
            _emit(
                mission,
                "native_implement",
                "No JSON patches from PLAN — Mentrix native implementer will edit isolated worktrees.",
            )
    current_plan_hash = hashlib.sha256(str(mission.get("plan") or "").encode("utf-8")).hexdigest()
    if current_plan_hash != mission.get("plan_hash"):
        _emit(mission, "plan_hash_drift", "PLAN text changed since it was recorded — re-hashing at approval time.")
        mission["plan_hash"] = current_plan_hash
    mission["plan_approved"] = True
    mission["plan_approved_hash"] = current_plan_hash
    mission["phase"] = "isolating"
    mission["status"] = "running"
    _emit(mission, "plan_approved", f"PLAN approved @{current_plan_hash[:12]}. Isolating worktrees.")
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

    if mission.get("status") == "cancelled" or mission.get("phase") == "cancelled":
        return _public(mission)

    mission["phase"] = "editing"
    _emit(mission, "isolating", "Worktrees ready.")
    if mission.get("native_implement_pending"):
        _run_native_implementer(mission)
    return _run_edit_test_review(mission)


def _run_native_implementer(mission: dict[str, Any]) -> None:
    """Run Mentrix native tool loop inside isolated worktrees (same engine as HISTORY chat).

    Each repo gets a bounded Explore pass (read-only role, see
    mentrix_lead.run_explore_phase) before the Coder role is allowed to
    touch any file, so edits are grounded in what actually exists rather
    than the model's first guess.
    """
    from app.services.coding_engine.mentrix_lead import ROLE_CODER, ROLE_TOOL_ALLOWLISTS, run_explore_phase
    from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build
    from app.services.coding_engine.skill_router import select_skill

    skill = select_skill(ROLE_CODER)
    _emit(mission, "skill_selected", f"Coder role: {skill.skill_name or 'no skill matched'}", **skill.to_event_data())
    base_goal = skill.goal_prefix() + str(mission.get("goal") or "")
    approved_plan = str(mission.get("plan") or "")
    results: list[dict[str, Any]] = []
    for repo in mission["repos"]:
        wt = str(repo.get("worktree_path") or "").strip()
        if not wt:
            continue
        _emit(
            mission,
            "explore_start",
            f"{repo.get('label')}: Explore role investigating repo before edits",
            repository_id=repo.get("repository_id"),
        )
        findings = run_explore_phase(mission, repo, Path(wt))
        repo["explore_findings"] = findings
        _emit(
            mission,
            "explore_result",
            f"{repo.get('label')}: Explore findings ready ({len(findings)} char(s))",
            repository_id=repo.get("repository_id"),
        )
        goal = base_goal
        if findings:
            goal = f"{base_goal}\n\nEXPLORE FINDINGS:\n{findings}"
        out = run_mentrix_native_build(
            goal=goal,
            workspace=wt,
            expected_files=list(repo.get("expected_files") or []),
            project_id=mission.get("project_id"),
            timeout_s=float(os.getenv("MENTRIX_CODING_AGENT_MISSION_TIMEOUT", "240")),
            max_steps=int(os.getenv("MENTRIX_CODING_AGENT_MISSION_MAX_STEPS", "48")),
            role=ROLE_CODER,
            allowed_tools=ROLE_TOOL_ALLOWLISTS[ROLE_CODER],
            mission_id=mission.get("id"),
            repo_id=repo.get("repository_id"),
            work_item_id=mission.get("work_item_id"),
            approved_plan=approved_plan,
        )
        _bridge_native_events(mission, str(out.get("run_id") or ""), role=ROLE_CODER, repository_id=repo.get("repository_id"))
        results.append(out)
        repo["native_build"] = {
            "ok": out.get("ok"),
            "status": out.get("status"),
            "files_written": list(out.get("files_written") or []),
            "run_id": out.get("run_id"),
        }
        if out.get("context_used"):
            mission["context_used"] = out["context_used"]
        written = list(out.get("files_written") or [])
        if written:
            files = list(repo.get("files") or [])
            for path in written:
                if path not in files:
                    files.append(path)
            repo["files"] = files
        _emit(
            mission,
            "native_implement",
            f"{repo.get('label')}: native implementer {out.get('status') or 'done'} "
            f"({len(written)} file(s))",
            repository_id=repo.get("repository_id"),
            ok=out.get("ok"),
        )
    mission["native_implement"] = results


def _stringify_patch_map(patches: dict[str, Any] | None) -> dict[str, list[Any]]:
    raw: Any = patches
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    out: dict[str, list[Any]] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        if isinstance(value, list):
            items = value
        elif isinstance(value, dict):
            items = [value]
        else:
            items = []
        out[str(key)] = copy.deepcopy(list(items))
    return out


def _patches_for_repo(patches_map: dict[str, Any], repo: dict[str, Any]) -> list[Any]:
    rid = repo.get("repository_id")
    keys: list[Any] = [str(rid), rid]
    try:
        keys.append(int(str(rid).strip()))
    except (TypeError, ValueError):
        pass
    seen: set[str] = set()
    for key in keys:
        marker = f"{type(key).__name__}:{key}"
        if marker in seen or not isinstance(patches_map, dict):
            continue
        seen.add(marker)
        if key not in patches_map:
            continue
        got = patches_map.get(key)
        if isinstance(got, list):
            return copy.deepcopy(got)
        if isinstance(got, dict):
            return [copy.deepcopy(got)]
    return []


def _diagnose_and_repair_repo(
    mission: dict[str, Any], repo: dict[str, Any], wt: Path, tests: dict[str, Any]
) -> dict[str, Any]:
    """On a failing check (lint, typecheck, build, or tests -- see
    _run_quality_and_tests), feed the failure output back into the same
    native agent loop used for real edits (not a second implementation) to
    diagnose and patch, then rerun. Bounded by
    MENTRIX_CODING_AGENT_AUTO_REPAIR_MAX so a persistently-broken repo still
    reaches ``blocked`` rather than looping forever or getting silently
    reported as complete.
    """
    from app.services.coding_engine.mentrix_lead import ROLE_DEBUGGER, ROLE_TOOL_ALLOWLISTS
    from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build
    from app.services.coding_engine.skill_router import select_skill

    skill = select_skill(ROLE_DEBUGGER, signals={"test_failed": True})
    _emit(mission, "skill_selected", f"Debugger role: {skill.skill_name or 'no skill matched'}", **skill.to_event_data())

    max_attempts = int(os.getenv("MENTRIX_CODING_AGENT_AUTO_REPAIR_MAX", "2"))
    attempts = int(repo.get("auto_repair_attempts") or 0)
    current = tests
    while not current.get("ok") and attempts < max_attempts:
        attempts += 1
        failed_kind = str(current.get("kind") or "check")
        diagnostic_goal = skill.goal_prefix() + (
            f"The previous change caused this check ({failed_kind}) to fail:\n\n"
            f"{(current.get('stdout') or '').strip()}\n{(current.get('stderr') or '').strip()}\n\n"
            "Diagnose the root cause and patch the affected source file(s) so "
            "lint/typecheck/build and tests all pass. Do not modify test files "
            "unless the test itself is provably wrong -- explain why in a "
            "comment if you do."
        )
        _emit(
            mission,
            "diagnose_attempt",
            f"{repo.get('label')}: Debugger role auto-repair attempt {attempts}/{max_attempts} after test failure",
            repository_id=repo.get("repository_id"),
            attempt=attempts,
        )
        out = run_mentrix_native_build(
            goal=diagnostic_goal,
            workspace=str(wt),
            project_id=mission.get("project_id"),
            timeout_s=float(os.getenv("MENTRIX_CODING_AGENT_MISSION_TIMEOUT", "240")),
            max_steps=int(os.getenv("MENTRIX_CODING_AGENT_MISSION_MAX_STEPS", "48")),
            role=ROLE_DEBUGGER,
            allowed_tools=ROLE_TOOL_ALLOWLISTS[ROLE_DEBUGGER],
            mission_id=mission.get("id"),
            repo_id=repo.get("repository_id"),
            work_item_id=mission.get("work_item_id"),
            approved_plan=str(mission.get("plan") or ""),
        )
        _bridge_native_events(mission, str(out.get("run_id") or ""), role=ROLE_DEBUGGER, repository_id=repo.get("repository_id"))
        if out.get("context_used"):
            mission["context_used"] = out["context_used"]
        written = list(out.get("files_written") or [])
        if written:
            files = list(repo.get("files") or [])
            for path in written:
                if path not in files:
                    files.append(path)
            repo["files"] = files
        current = _run_quality_and_tests(wt)
        _emit(
            mission,
            "diagnose_result",
            f"{repo.get('label')}: repair attempt {attempts} -> {current.get('status')} "
            f"({len(written)} file(s) touched)",
            repository_id=repo.get("repository_id"),
            ok=current.get("ok"),
            files_written=written,
        )
    repo["auto_repair_attempts"] = attempts
    return current


def _run_app_and_browser_verification(
    mission: dict[str, Any], repo: dict[str, Any], wt: Path
) -> dict[str, Any]:
    """Once unit tests pass, ask the SAME native agent loop -- now with the
    start_app/health_check/browser_* tools available -- to start this repo's
    real application and verify the change in a real browser. Not a
    hard-scripted sequence: the model decides whether/how to start the app,
    what to click, and whether a browser-observed failure needs a code fix,
    then reruns verification itself, bounded the same way as
    _diagnose_and_repair_repo. If runtime_discovery finds no runnable app
    here, this is a no-op (not every repo has a browsable UI) rather than a
    failure.
    """
    from app.services.coding_engine.mentrix_lead import ROLE_TESTER, ROLE_TOOL_ALLOWLISTS
    from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build
    from app.services.coding_engine.skill_router import select_skill
    from app.services.workspace.runtime_discovery import discover_runtime_recipes

    discovered = discover_runtime_recipes(str(wt))
    if not discovered.get("recipes"):
        return {"ran": False, "reason": "no_runnable_app_detected"}

    skill = select_skill(ROLE_TESTER, signals={"browser_acceptance": True})
    _emit(mission, "skill_selected", f"Tester role: {skill.skill_name or 'no skill matched'}", **skill.to_event_data())

    max_attempts = int(os.getenv("MENTRIX_CODING_AGENT_BROWSER_VERIFY_MAX", "2"))
    attempt = 0
    verified = False
    summary = ""
    while attempt < max_attempts and not verified:
        attempt += 1
        goal = skill.goal_prefix() + (
            "The unit tests pass. Now verify the change actually works at runtime: "
            "call start_app (with no command, so the real project start command is "
            "discovered -- if it returns needs_recipe_choice, pick the most relevant "
            "candidate and call start_app again with that recipe_id), then health_check "
            "the port it reports, then use the browser_* tools to navigate to it and "
            "confirm the change is visible/working with no new console errors or failed "
            "network requests. If you find a real problem, fix the affected source "
            "file(s), call restart_app, and verify again. When finished (including if "
            "you determine this workspace has nothing browser-verifiable), call stop_app "
            "and state clearly what you verified or could not verify."
        )
        _emit(
            mission,
            "browser_verify_attempt",
            f"{repo.get('label')}: Tester role app/browser verification attempt {attempt}/{max_attempts}",
            repository_id=repo.get("repository_id"),
            attempt=attempt,
        )
        out = run_mentrix_native_build(
            goal=goal,
            workspace=str(wt),
            project_id=mission.get("project_id"),
            timeout_s=float(os.getenv("MENTRIX_CODING_AGENT_MISSION_TIMEOUT", "240")),
            max_steps=int(os.getenv("MENTRIX_CODING_AGENT_MISSION_MAX_STEPS", "48")),
            role=ROLE_TESTER,
            allowed_tools=ROLE_TOOL_ALLOWLISTS[ROLE_TESTER],
            mission_id=mission.get("id"),
            repo_id=repo.get("repository_id"),
            work_item_id=mission.get("work_item_id"),
            approved_plan=str(mission.get("plan") or ""),
        )
        _bridge_native_events(mission, str(out.get("run_id") or ""), role=ROLE_TESTER, repository_id=repo.get("repository_id"))
        if out.get("context_used"):
            mission["context_used"] = out["context_used"]
        summary = str(out.get("summary") or out.get("status") or "")
        written = list(out.get("files_written") or [])
        if written:
            files = list(repo.get("files") or [])
            for path in written:
                if path not in files:
                    files.append(path)
            repo["files"] = files

        retest = _run_quality_and_tests(wt)
        if not retest.get("ok"):
            retest = _diagnose_and_repair_repo(mission, repo, wt, retest)
        # "verified" requires BOTH: the agent's own browser-verification turn
        # reported success (out.get("ok") -- it may have run out of steps,
        # found the app unreachable, etc, distinct from unit-test status),
        # AND the unit tests still pass (in case a "fix" broke something).
        verified = bool(out.get("ok")) and bool(retest.get("ok"))
        _emit(
            mission,
            "browser_verify_result",
            f"{repo.get('label')}: attempt {attempt} -> {'verified' if verified else 'not verified'} "
            f"({len(written)} file(s) touched)",
            repository_id=repo.get("repository_id"),
            ok=verified,
            files_written=written,
        )

    try:
        from app.domains.workspace.app_runner import stop_owned_processes_in_workspace

        stop_owned_processes_in_workspace(str(wt))
    except Exception:  # noqa: BLE001
        pass

    return {"ran": True, "verified": verified, "attempts": attempt, "summary": summary[:500]}


def _run_edit_test_review(mission: dict[str, Any]) -> dict[str, Any]:
    patches_map = _stringify_patch_map(mission.get("patches_by_repo"))
    diffs: list[str] = []
    per_repo_status: list[dict[str, Any]] = []
    for repo in mission["repos"]:
        if mission.get("status") == "cancelled":
            return _public(mission)
        patches = _patches_for_repo(patches_map, repo)
        repo["patches_applied"] = len(patches)
        wt = Path(repo["worktree_path"])
        applied = _apply_patches(mission, repo, wt, patches)
        if not applied.get("ok"):
            repo["blocker"] = applied.get("error") or "edit_failed"
            repo["test_ok"] = False
            repo["test_status"] = "fail"
            mission["phase"] = "blocked"
            mission["status"] = "blocked"
            _emit(mission, "blocked", f"Edit failed on {repo.get('label')}", error=repo["blocker"])
            return _public(mission)
        # Merge, don't overwrite -- the native implementer (Explore/Coder,
        # taken when there are no JSON patches) may have already recorded
        # files_written on this repo before this function ever ran.
        files = list(repo.get("files") or [])
        for path in applied.get("files") or []:
            if path not in files:
                files.append(path)
        repo["files"] = files
        repo["commands"] = list(applied.get("commands") or [])
        tests = _run_quality_and_tests(wt)
        if not tests.get("ok"):
            tests = _diagnose_and_repair_repo(mission, repo, wt, tests)
        repo["test_ok"] = bool(tests.get("ok"))
        repo["test_status"] = tests.get("status")
        repo["test"] = tests
        repo["test_stdout"] = tests.get("stdout")
        if tests.get("command"):
            repo.setdefault("commands", []).append(tests["command"])
        if not tests.get("ok"):
            attempts = repo.get("auto_repair_attempts") or 0
            repo["blocker"] = f"tests_{tests.get('status')}_after_{attempts}_repair_attempt(s)"
        else:
            repo["blocker"] = ""
            verify = _run_app_and_browser_verification(mission, repo, wt)
            repo["browser_verification"] = verify
            if verify.get("ran") and not verify.get("verified"):
                repo["test_ok"] = False
                repo["test_status"] = "fail"
                attempts = verify.get("attempts") or 0
                repo["blocker"] = f"browser_verification_failed_after_{attempts}_attempt(s)"
        diff = _collect_diff(wt)
        if diff:
            repo["diff"] = diff
        diffs.append(diff or str(repo.get("diff") or ""))
        # Use repo["test_ok"], not the local `tests` dict -- browser
        # verification (above) can flip a passing unit-test result to
        # failed, and the aggregate/sibling gate below must see that.
        per_repo_status.append(
            {
                "repository_id": repo.get("repository_id"),
                "label": repo.get("label"),
                "status": "pass" if repo.get("test_ok") else "fail",
            }
        )
        _emit(
            mission,
            "tests",
            f"{repo.get('label')}: {repo.get('test_status')}",
            repository_id=repo.get("repository_id"),
            ok=repo.get("test_ok"),
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

    evidence_blocked = False
    for repo in mission["repos"]:
        wt = Path(repo["worktree_path"])
        verification = verify_mission_evidence(mission, repo, wt)
        repo["evidence_verification"] = verification
        _emit(
            mission,
            "evidence_verify_result",
            f"{repo.get('label')}: {'verified' if verification.get('ok') else 'evidence mismatch'} "
            f"({len(verification.get('findings') or [])} finding(s))",
            repository_id=repo.get("repository_id"),
            ok=verification.get("ok"),
        )
        if not verification.get("ok"):
            evidence_blocked = True
            codes = ",".join(f["code"] for f in verification["findings"] if f.get("severity") == "critical")
            repo["blocker"] = f"evidence_verification_failed:{codes}"
    if evidence_blocked:
        mission["phase"] = "blocked"
        mission["status"] = "blocked"
        _emit(mission, "blocked", "EvidenceVerifier found unevidenced/inconsistent claims — not READY_TO_MERGE.")
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
    mid = _safe_mission_id(mission_id)
    _mark_stopped(mid)
    mission = _lookup(mid)
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
    mid = _safe_mission_id(mission_id)
    _mark_running(mid)
    try:
        return _resume_mission_impl(mid)
    finally:
        _mark_stopped(mid)


def resume_mission_in_background(mission_id: str) -> dict[str, Any]:
    """Background-thread twin of approve_plan_in_background(), for a
    "recoverable" mission (mid-flight phase, no live thread -- e.g. after a
    backend restart) that a caller wants to genuinely resume rather than
    just re-inspect."""
    mid = _safe_mission_id(mission_id)
    _mark_running(mid)

    def _run() -> None:
        try:
            _resume_mission_impl(mid)
        finally:
            _mark_stopped(mid)

    threading.Thread(target=_run, daemon=True).start()
    return get_mission(mid)


def _resume_mission_impl(mission_id: str) -> dict[str, Any]:
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
        return _approve_plan_impl(mission_id)
    _emit(mission, "resume", "Resuming from checkpoint. Duplicate commits skipped.")
    return _run_edit_test_review(mission)


def retry_mission(mission_id: str) -> dict[str, Any]:
    return resume_mission(mission_id)


def repair_and_retry(mission_id: str, patches_by_repo: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    mission = _lookup(mission_id)
    merged = _stringify_patch_map(mission.get("patches_by_repo"))
    merged.update(_stringify_patch_map(patches_by_repo))
    mission["patches_by_repo"] = merged
    mission["status"] = "running"
    mission["sibling"] = {}
    mission["review"] = {}
    for repo in mission.get("repos") or []:
        repo["blocker"] = ""
    _emit(mission, "repair", "Applying sibling repair patches.")
    return _run_edit_test_review(mission)
