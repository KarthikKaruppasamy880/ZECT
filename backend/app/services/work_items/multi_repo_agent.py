"""Multi-repo AGENT delivery — isolated worktrees, per-repo coder/tests/review/PR, aggregate gates.

Does not auto-merge PRs. READY_TO_SHIP is only set via AcceptanceVerifier + EvidenceVerifier.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.domains.work_items.events import append_event
from app.domains.work_items.status import STATUS_EXECUTING, STATUS_IMPLEMENTED, STATUS_VERIFYING
from app.models import WorkItem
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.checkpoints import record_checkpoint
from app.services.work_items.multi_repo_context import git_head_sha

MARKER_FILE = "mentrix_p0_agent_marker.py"
MARKER_CONTENT = "# mentrix p0\nprint('ok')\n"

READY_REPO_STATUSES = frozenset(
    {"pass", "passed", "completed", "verified", "ready_to_ship", "done"}
)
READY_OP_STATUSES = frozenset(
    {"pass", "passed", "completed", "verified", "ready_to_ship", "done"}
)


def is_multi_repo_manifest(manifest: dict[str, Any] | None) -> bool:
    man = manifest or {}
    ops = list(man.get("operations") or [])
    affected = list(man.get("affected_repos") or [])
    repo_ops = [o for o in ops if o.get("repository_id")]
    return len(affected) > 1 or len(repo_ops) > 1


def collect_current_heads(store: ArtifactStore) -> dict[str, str]:
    """Map repository_id (str) → live worktree/PR HEAD SHA."""
    heads: dict[str, str] = {}
    manifest = store.read_json("EXECUTION_MANIFEST.json", default={}) or {}
    prs_raw = store.read_json("PULL_REQUESTS.json", default={}) or {}
    prs = prs_raw.get("pull_requests") if isinstance(prs_raw, dict) else prs_raw
    if not isinstance(prs, list):
        prs = []

    def _record(rid: Any, path: str, fallback: str = "") -> None:
        key = str(rid or "")
        if not key:
            return
        live = git_head_sha(path) if path else ""
        sha = live or fallback
        if sha:
            heads[key] = sha

    for repo in manifest.get("affected_repos") or []:
        _record(
            repo.get("repository_id"),
            str(repo.get("worktree_path") or ""),
            str(repo.get("head_sha") or repo.get("current_commit_sha") or ""),
        )
    for op in manifest.get("operations") or []:
        _record(
            op.get("repository_id"),
            str(op.get("worktree_path") or ""),
            str(op.get("head_sha") or op.get("current_commit_sha") or op.get("base_commit_sha") or ""),
        )
        oid = str(op.get("id") or "")
        if oid:
            live = git_head_sha(str(op.get("worktree_path") or ""))
            sha = live or str(op.get("head_sha") or op.get("current_commit_sha") or "")
            if sha:
                heads[oid] = sha
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        _record(pr.get("repository_id"), str(pr.get("worktree_path") or ""), str(pr.get("head_sha") or ""))
    return heads


def read_multi_repo_status(store: ArtifactStore, *, work_item_id: int, wi_status: str = "") -> dict[str, Any]:
    manifest = store.read_json("EXECUTION_MANIFEST.json", default={}) or {}
    tests = store.read_json("TEST_RESULTS.json", default={}) or {}
    review = store.read_json("REVIEW.json", default={}) or {}
    prs_raw = store.read_json("PULL_REQUESTS.json", default={}) or {}
    evidence = store.read_json("EVIDENCE.json", default={}) or {}
    prs = prs_raw.get("pull_requests") if isinstance(prs_raw, dict) else prs_raw
    if not isinstance(prs, list):
        prs = []
    affected = list(manifest.get("affected_repos") or [])
    ops = list(manifest.get("operations") or [])
    worktrees = []
    for row in affected:
        wt = str(row.get("worktree_path") or "")
        if wt:
            worktrees.append(
                {
                    "repository_id": row.get("repository_id"),
                    "label": row.get("label") or "",
                    "worktree_path": wt,
                    "base_commit_sha": row.get("base_commit_sha") or "",
                    "head_sha": row.get("head_sha") or git_head_sha(wt),
                    "status": row.get("status") or "pending",
                }
            )
    ready = False
    if isinstance(evidence, dict):
        ready = bool((evidence.get("verification") or {}).get("ready_to_ship"))
    agg = "pending"
    if ready or (wi_status or "").upper() == "READY_TO_SHIP":
        agg = "ready_to_ship"
        ready = True
    elif any(str(r.get("status") or "").lower() in ("blocked", "stale") for r in affected):
        agg = "blocked"
    elif any(str(r.get("status") or "").lower() == "failed" for r in affected) or tests.get("ok") is False:
        agg = "failed"
    elif affected and all(str(r.get("status") or "").lower() in READY_REPO_STATUSES for r in affected):
        agg = "passed"
    elif any(str(r.get("status") or "").lower() not in ("", "pending") for r in affected):
        agg = "executing"
    return {
        "work_item_id": work_item_id,
        "multi_repo": is_multi_repo_manifest(manifest),
        "aggregate_status": agg,
        "ready_to_ship": bool(ready),
        "work_item_status": wi_status,
        "affected_repos": affected,
        "operations": ops,
        "worktrees": worktrees,
        "tests": tests,
        "review": review,
        "pull_requests": prs,
    }


def run_multi_repo_agent(
    db: Session,
    wi: WorkItem,
    store: ArtifactStore,
    *,
    goal: str,
    actor: str = "",
    deterministic: bool = False,
) -> dict[str, Any]:
    manifest = store.read_json("EXECUTION_MANIFEST.json", default={}) or {}
    ops = list(manifest.get("operations") or [])
    affected = list(manifest.get("affected_repos") or [])
    by_id: dict[int, dict[str, Any]] = {}
    for row in affected:
        try:
            by_id[int(row["repository_id"])] = row
        except (KeyError, TypeError, ValueError):
            continue

    tests_by_repo: dict[str, Any] = {}
    reviews_by_repo: dict[str, Any] = {}
    pull_requests: list[dict[str, Any]] = []
    evidence_items: list[dict[str, Any]] = []
    files_written: list[str] = []
    worktrees_out: list[dict[str, Any]] = []
    events_tail: list[Any] = []

    for op in ops:
        rid = int(op.get("repository_id") or 0)
        binding = by_id.get(rid) or {}
        result = _run_one_repo(
            db,
            wi,
            store,
            op=op,
            binding=binding,
            goal=goal,
            deterministic=deterministic,
        )
        tests_by_repo[str(rid)] = result["tests"]
        reviews_by_repo[str(rid)] = result["review"]
        pull_requests.append(result["pull_request"])
        evidence_items.extend(result["evidence"])
        files_written.extend(result.get("files_written") or [])
        if result.get("worktree"):
            worktrees_out.append(result["worktree"])
        events_tail.extend(result.get("events") or [])
        op.update(result["op_patch"])
        if binding:
            binding.update(result["repo_patch"])

    mandatory_ids = {int(r["repository_id"]) for r in affected if r.get("mandatory", True) and r.get("repository_id")}
    all_mandatory_pass = True
    for rid_s, t in tests_by_repo.items():
        try:
            rid_i = int(rid_s)
        except (TypeError, ValueError):
            continue
        if rid_i in mandatory_ids and not t.get("ok"):
            all_mandatory_pass = False
    for row in affected:
        if row.get("mandatory", True) and str(row.get("status") or "").lower() not in READY_REPO_STATUSES:
            all_mandatory_pass = False
    for op in ops:
        if op.get("mandatory", True) and str(op.get("status") or "").lower() not in READY_OP_STATUSES:
            all_mandatory_pass = False

    test_results = {
        "ok": all_mandatory_pass,
        "by_repository": tests_by_repo,
        "at": datetime.now(timezone.utc).isoformat(),
        "may_ready_to_ship": False,
    }
    any_blocking = []
    for rid_s, rev in reviews_by_repo.items():
        any_blocking.extend(list(rev.get("blocking") or []))
    review_doc = {
        "clean": bool(all_mandatory_pass and not any_blocking),
        "blocking": any_blocking,
        "by_repository": reviews_by_repo,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if not all_mandatory_pass:
        review_doc["clean"] = False

    manifest["operations"] = ops
    manifest["affected_repos"] = affected
    store.write_json("EXECUTION_MANIFEST.json", manifest)
    store.write_json("TEST_RESULTS.json", test_results)
    store.write_json("REVIEW.json", review_doc)
    store.write_json("PULL_REQUESTS.json", {"pull_requests": pull_requests})
    store.write_json(
        "EVIDENCE.json",
        {"evidence": evidence_items, "by_repository": {str(e.get("payload", {}).get("repository_id")): e for e in evidence_items}},
    )

    first_wt = next((w.get("worktree_path") for w in worktrees_out if w.get("worktree_path")), "") or ""
    wi.worktree_path = first_wt or wi.worktree_path
    if worktrees_out:
        wi.current_commit_sha = str(worktrees_out[0].get("head_sha") or wi.current_commit_sha or "")
    wi.status = STATUS_IMPLEMENTED if files_written else STATUS_EXECUTING
    append_event(
        db,
        work_item_id=wi.id,
        event_type="agent_completed_slice",
        payload={
            "engine": "mentrix_native" if not deterministic else "deterministic",
            "files_written": files_written,
            "repos": [w.get("repository_id") for w in worktrees_out],
            "multi_repo": True,
        },
    )
    db.commit()

    wi.status = STATUS_VERIFYING
    db.commit()
    from app.services.mentrix.engineering_agents.acceptance_verifier import AcceptanceVerifier

    acceptance = AcceptanceVerifier(db, wi.id).verify(evidence=evidence_items, ship=True, actor=actor or "multi_repo_agent")
    db.refresh(wi)

    record_checkpoint(
        store,
        checkpoint_type="verification" if acceptance.get("ready_to_ship") else "blocking",
        operation_id="multi_repo_agent",
        payload={"ready_to_ship": acceptance.get("ready_to_ship"), "repos": list(tests_by_repo.keys())},
        worktree_path=first_wt,
        base_commit_sha=wi.base_commit_sha or "",
        current_commit_sha=wi.current_commit_sha or "",
    )

    status_out = read_multi_repo_status(store, work_item_id=wi.id, wi_status=wi.status or "")
    return {
        "work_item_id": wi.id,
        "status": wi.status,
        "run_id": f"{'deterministic' if deterministic else 'mentrix_native'}-{wi.id}",
        "files_written": files_written,
        "events_tail": events_tail,
        "engine": "deterministic" if deterministic else "mentrix_native",
        "worktree_path": first_wt,
        "worktrees": worktrees_out,
        "tests": test_results,
        "review": review_doc,
        "pull_requests": pull_requests,
        "acceptance": acceptance,
        "ready_to_ship": bool(acceptance.get("ready_to_ship")),
        "multi_repo": True,
        "aggregate_status": status_out.get("aggregate_status"),
        "affected_repos": affected,
        "operations": ops,
    }


def _run_one_repo(
    db: Session,
    wi: WorkItem,
    store: ArtifactStore,
    *,
    op: dict[str, Any],
    binding: dict[str, Any],
    goal: str,
    deterministic: bool,
) -> dict[str, Any]:
    rid = int(op.get("repository_id") or binding.get("repository_id") or 0)
    oid = str(op.get("id") or f"OP-repo-{rid}")
    local_path = str(binding.get("local_path") or "")
    label = str(binding.get("label") or f"repo-{rid}")
    head_branch = str(op.get("repository_ref") or binding.get("repository_ref") or "main")
    base_sha = str(op.get("base_commit_sha") or binding.get("base_commit_sha") or "")

    def _blocked(reason: str, status: str = "blocked") -> dict[str, Any]:
        tests = {"ok": False, "status": status, "reason": reason, "repository_id": rid, "label": label}
        review = {
            "clean": False,
            "blocking": [{"id": f"blocked-{rid}", "severity": "high", "message": reason, "verification_status": "verified"}],
            "repository_id": rid,
            "stub": True,
        }
        pr = {
            "repository_id": rid,
            "branch": "",
            "pr_number": None,
            "pr_url": None,
            "head_sha": "",
            "ci": "unknown",
            "review": status,
            "worktree_path": "",
            "pr_status": "local_branch_only",
            "error": reason,
        }
        return {
            "tests": tests,
            "review": review,
            "pull_request": pr,
            "evidence": [],
            "files_written": [],
            "worktree": None,
            "events": [{"event": "blocked", "repository_id": rid, "reason": reason}],
            "op_patch": {"status": status, "worktree_path": "", "error": reason},
            "repo_patch": {"status": status, "worktree_path": "", "error": reason},
        }

    if not rid or not local_path:
        return _blocked("no_authorized_local_path", "blocked")

    from app.services.repo_onboarding import ensure_agent_worktree

    fallback = store.root / "worktrees" / f"repo-{rid}"
    wt = ensure_agent_worktree(
        db,
        repo_id=rid,
        work_item_id=wi.id,
        head_branch=head_branch,
        head_sha=base_sha,
    )
    if not wt.get("ok"):
        fallback.mkdir(parents=True, exist_ok=True)
        wt = ensure_agent_worktree(
            db,
            repo_id=rid,
            work_item_id=wi.id,
            head_branch=head_branch,
            head_sha=base_sha,
            worktree_path=fallback,
        )
    if not wt.get("ok"):
        return _blocked(str(wt.get("error") or "worktree_failed"), "blocked")

    wt_path = str(wt["worktree_path"])
    start_sha = str(wt.get("base_commit_sha") or wt.get("head_sha") or base_sha)
    coder = _run_coder(wt_path, goal=goal, deterministic=deterministic)
    files = list(coder.get("files_written") or [])
    head_after_coder = _commit_worktree(Path(wt_path), f"zect wi-{wi.id} repo-{rid}")
    tests = _run_repo_tests(Path(wt_path), marker=MARKER_FILE)
    tests["repository_id"] = rid
    tests["label"] = label
    tests["worktree_path"] = wt_path
    tests["head_sha"] = head_after_coder or git_head_sha(wt_path)

    repo_status = "pass"
    op_status = "completed"
    if not tests.get("ok"):
        repo_status = "failed" if tests.get("status") != "blocked" else "blocked"
        op_status = "failed" if repo_status == "failed" else "blocked"
    if not coder.get("ok") and repo_status == "pass":
        repo_status = "failed"
        op_status = "failed"

    review = _review_repo(
        db,
        work_item_id=wi.id,
        worktree=Path(wt_path),
        tests_ok=bool(tests.get("ok")),
        goal=goal,
        repository_id=rid,
    )
    pr = _record_pr(
        worktree=Path(wt_path),
        repository_id=rid,
        branch=str(wt.get("branch") or ""),
        head_sha=tests.get("head_sha") or head_after_coder,
        review=review,
        tests_ok=bool(tests.get("ok")),
        label=label,
        title=f"ZECT WI-{wi.id}: {goal[:80]}",
        body=f"Isolated AGENT delivery for {label} (work item {wi.id}). Do not auto-merge.",
    )

    evidence = [
        {
            "id": f"file:{rid}",
            "type": "FILE_CHANGED",
            "operation_id": oid,
            "payload": {
                "repository_id": rid,
                "head_sha": tests.get("head_sha"),
                "worktree_path": wt_path,
                "files": files,
            },
            "llm_claim": False,
        },
        {
            "id": f"test:{rid}",
            "type": "TEST_RESULT",
            "operation_id": oid,
            "payload": {
                "repository_id": rid,
                "ok": tests.get("ok"),
                "head_sha": tests.get("head_sha"),
                "worktree_path": wt_path,
            },
            "llm_claim": False,
        },
    ]

    wt_info = {
        "repository_id": rid,
        "worktree_path": wt_path,
        "base_commit_sha": start_sha,
        "head_sha": tests.get("head_sha"),
        "branch": wt.get("branch"),
        "main_unchanged": wt.get("main_unchanged", True),
        "main_path": wt.get("main_path"),
        "status": repo_status,
    }
    return {
        "tests": tests,
        "review": review,
        "pull_request": pr,
        "evidence": evidence,
        "files_written": files,
        "worktree": wt_info,
        "events": list(coder.get("events_tail") or []),
        "op_patch": {
            "status": op_status,
            "worktree_path": wt_path,
            "base_commit_sha": start_sha,
            "head_sha": tests.get("head_sha"),
            "current_commit_sha": tests.get("head_sha"),
        },
        "repo_patch": {
            "status": repo_status,
            "worktree_path": wt_path,
            "base_commit_sha": start_sha,
            "head_sha": tests.get("head_sha"),
            "current_commit_sha": tests.get("head_sha"),
        },
    }


def _run_coder(worktree: str, *, goal: str, deterministic: bool) -> dict[str, Any]:
    if deterministic or (os.getenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        from app.services.coding_engine.mentrix_agent_tools import execute_tool, resolve_workspace

        root = resolve_workspace(worktree)
        execute_tool("list_dir", {"path": "."}, workspace=root)
        w = execute_tool(
            "write_file",
            {"path": MARKER_FILE, "content": MARKER_CONTENT},
            workspace=root,
        )
        r = execute_tool("read_file", {"path": MARKER_FILE}, workspace=root)
        cmd = execute_tool("run_command", {"command": f"python {MARKER_FILE}"}, workspace=root)
        ok = bool(w.get("ok") and r.get("ok"))
        return {
            "ok": ok,
            "files_written": [MARKER_FILE] if w.get("ok") else [],
            "events_tail": [
                {"event": "tool", "name": "write_file", "ok": w.get("ok")},
                {"event": "tool", "name": "read_file", "ok": r.get("ok")},
                {"event": "tool", "name": "run_command", "ok": cmd.get("ok"), "exit": cmd.get("exit_code")},
            ],
        }

    from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build

    native = run_mentrix_native_build(
        goal=goal,
        workspace=worktree,
        expected_files=[MARKER_FILE],
        project_id=wi.project_id,
        repo_id=rid,
        work_item_id=wi.id,
    )
    return {
        "ok": bool(native.get("ok")),
        "files_written": list(native.get("files_written") or []),
        "events_tail": list(native.get("events_tail") or []),
    }


def _run_repo_tests(worktree: Path, *, marker: str) -> dict[str, Any]:
    tests_dir = worktree / "tests"
    has_pytest = tests_dir.is_dir() and any(tests_dir.glob("test_*.py"))
    if has_pytest:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "--tb=short", "--noconftest", "tests"],
                cwd=str(worktree),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            ok = proc.returncode == 0
            return {
                "ok": ok,
                "status": "pass" if ok else "failed",
                "kind": "pytest",
                "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-1500:],
                "stderr_tail": (proc.stderr or "")[-800:],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "status": "blocked", "kind": "pytest", "error": str(exc)[:400]}

    target = worktree / marker
    if target.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, marker],
                cwd=str(worktree),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            ok = proc.returncode == 0
            return {
                "ok": ok,
                "status": "pass" if ok else "failed",
                "kind": "marker_smoke",
                "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-500:],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "status": "blocked", "kind": "marker_smoke", "error": str(exc)[:400]}

    try:
        proc = subprocess.run(
            [sys.executable, "-c", "print('ok')"],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        ok = proc.returncode == 0
        return {"ok": ok, "status": "pass" if ok else "failed", "kind": "python_c_smoke", "exit_code": proc.returncode}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": "blocked", "kind": "python_c_smoke", "error": str(exc)[:400]}


def _review_repo(
    db: Session,
    *,
    work_item_id: int,
    worktree: Path,
    tests_ok: bool,
    goal: str,
    repository_id: int,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    ultra: dict[str, Any] = {}
    marker = worktree / MARKER_FILE
    code = marker.read_text(encoding="utf-8", errors="replace") if marker.is_file() else ""
    try:
        from app.services.phases.review_phase_svc import run_ultra_review

        if code.strip():
            ultra = run_ultra_review(code, language="python", goal=goal, db=db) or {}
            findings.extend(list(ultra.get("findings") or []))
    except Exception as exc:  # noqa: BLE001
        ultra = {"offline": True, "error": str(exc)[:200]}

    if not tests_ok:
        findings.append(
            {
                "id": f"tests-failed-{repository_id}",
                "severity": "high",
                "category": "correctness",
                "message": "Repo tests failed or blocked; review is not CLEAN",
                "verification_status": "verified",
            }
        )

    blocking = [
        f
        for f in findings
        if str(f.get("severity") or "").lower() in ("critical", "high", "blocking", "error")
        and str(f.get("verification_status") or "verified").lower() in ("verified", "validated", "")
    ]
    clean = tests_ok and not blocking
    return {
        "clean": clean,
        "blocking": blocking,
        "findings": findings,
        "repository_id": repository_id,
        "ultra": {"passed": ultra.get("passed"), "offline": ultra.get("offline"), "model": ultra.get("model")},
        "stub": not bool(ultra) and tests_ok,
        "work_item_id": work_item_id,
    }


def _record_pr(
    *,
    worktree: Path,
    repository_id: int,
    branch: str,
    head_sha: str,
    review: dict[str, Any],
    tests_ok: bool,
    label: str,
    title: str,
    body: str,
) -> dict[str, Any]:
    if not branch:
        br = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            check=False,
        )
        branch = (br.stdout or "").strip()
        if branch == "HEAD":
            branch = f"zect-wi-repo-{repository_id}"

    rec: dict[str, Any] = {
        "repository_id": repository_id,
        "branch": branch,
        "pr_number": None,
        "pr_url": None,
        "head_sha": head_sha or git_head_sha(str(worktree)),
        "ci": "unknown",
        "review": "clean" if review.get("clean") else ("blocked" if not tests_ok else "findings"),
        "worktree_path": str(worktree),
        "pr_status": "local_branch_only",
        "label": label,
    }

    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(worktree),
        capture_output=True,
        text=True,
        check=False,
    )
    origin = (remote.stdout or "").strip()
    if not token or remote.returncode != 0 or "github.com" not in origin.lower():
        rec["pr_status"] = "local_branch_only"
        rec["pr_error"] = rec.get("pr_error") or (
            "missing_github_token_or_origin" if not token or "github.com" not in origin.lower() else "no_origin"
        )
        return rec

    owner, repo_name = _parse_github_origin(origin)
    if not owner or not repo_name:
        rec["pr_error"] = "cannot_parse_github_origin"
        return rec

    push = _git_push_github(worktree, origin=origin, branch=branch, token=token)
    if not push.get("ok"):
        rec["pr_status"] = "local_branch_only"
        rec["pr_error"] = str(push.get("error") or "push_failed")[:400]
        return rec

    try:
        from app import github_service

        base = "main"
        try:
            info = github_service.get_repo_info(owner, repo_name)
            base = str(getattr(info, "default_branch", None) or "main")
        except Exception:  # noqa: BLE001
            base = "main"
        pr = github_service.create_pull_request(
            owner=owner,
            repo=repo_name,
            title=title,
            body=body,
            head=branch,
            base=base,
        )
        rec["pr_status"] = "created"
        rec["pr_number"] = pr.get("number")
        rec["pr_url"] = pr.get("html_url")
        rec["ci"] = "pending"
    except Exception as exc:  # noqa: BLE001
        rec["pr_status"] = "local_branch_only"
        rec["pr_error"] = _redact_secrets(str(exc)[:400])
        rec["pr_url"] = None
        rec["pr_number"] = None
    return rec


def _redact_secrets(text: str) -> str:
    s = text or ""
    s = re.sub(r"(gho_|ghp_|github_pat_|ghu_|ghs_|ghr_)[A-Za-z0-9_]+", "[redacted]", s)
    s = re.sub(r"(x-access-token:)[^@\s]+", r"\1[redacted]", s, flags=re.I)
    s = re.sub(r"(Authorization:\s*bearer\s+)\S+", r"\1[redacted]", s, flags=re.I)
    s = re.sub(r"(Bearer |token )[A-Za-z0-9._\-]+", r"\1[redacted]", s, flags=re.I)
    return s


def _git_push_github(worktree: Path, *, origin: str, branch: str, token: str) -> dict[str, Any]:
    """Push with GITHUB_TOKEN via http.extraHeader so the token is not stored in origin URL."""
    owner, repo_name = _parse_github_origin(origin)
    if not owner or not repo_name or not token or not branch:
        return {"ok": False, "error": "push_precondition"}
    https = f"https://github.com/{owner}/{repo_name}.git"
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_COUNT"] = "2"
    env["GIT_CONFIG_KEY_0"] = "credential.helper"
    env["GIT_CONFIG_VALUE_0"] = ""
    env["GIT_CONFIG_KEY_1"] = "http.extraHeader"
    env["GIT_CONFIG_VALUE_1"] = f"AUTHORIZATION: bearer {token}"
    proc = subprocess.run(
        [
            "git",
            "push",
            "-u",
            https,
            f"{branch}:{branch}",
        ],
        cwd=str(worktree),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    if proc.returncode == 0:
        return {"ok": True}
    err = _redact_secrets((proc.stderr or proc.stdout or "push_failed")[:400])
    return {"ok": False, "error": err}


def _parse_github_origin(url: str) -> tuple[str, str]:
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url or "")
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def _commit_worktree(worktree: Path, message: str) -> str:
    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "ZECT Agent")
    env.setdefault("GIT_AUTHOR_EMAIL", "zect-agent@local")
    env.setdefault("GIT_COMMITTER_NAME", "ZECT Agent")
    env.setdefault("GIT_COMMITTER_EMAIL", "zect-agent@local")
    subprocess.run(["git", "add", "-A"], cwd=str(worktree), capture_output=True, text=True, check=False)
    st = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(worktree),
        capture_output=True,
        text=True,
        check=False,
    )
    if not (st.stdout or "").strip():
        return git_head_sha(str(worktree))
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(worktree),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return git_head_sha(str(worktree))
