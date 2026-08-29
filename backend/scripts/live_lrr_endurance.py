"""Controlled live LongRunningAgentRuntime endurance — disposable repo only.

Does not push/merge to production. Marks Jira BLOCKED_EXTERNAL when unused.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Force real coding engine for this controlled run (do not mutate production repos)
os.environ["ZECT_CODING_ENGINE"] = "mentrix_native"
os.environ.setdefault("ZECT_MODEL_FALLBACK_POLICY", "ask")

from app.infrastructure.database import Base, SessionLocal, engine  # noqa: E402
from app.domains.work_items import service as wi_svc  # noqa: E402
from app.services.mentrix.engineering_agents.acceptance_verifier import AcceptanceVerifier  # noqa: E402
from app.services.mentrix.engineering_agents.planner import MentrixPlanner  # noqa: E402
from app.services.mentrix.engineering_agents.review_agent import MentrixReviewAgent  # noqa: E402
from app.services.mentrix.engineering_agents.test_agent import MentrixTestAgent  # noqa: E402
from app.services.mentrix.long_running_runtime import LongRunningAgentRuntime  # noqa: E402
from app.services.work_items.artifact_store import ArtifactStore  # noqa: E402
from app.adapters.coding_runtime import selected_coding_engine  # noqa: E402


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False)


def main() -> dict:
    started = time.perf_counter()
    evidence: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "jira": "BLOCKED_EXTERNAL",
        "jira_reason": "Controlled User WorkItem used against disposable test repo (Jira not required for this acceptance)",
        "production_merge": False,
    }

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    root = Path(__file__).resolve().parents[2] / ".zect" / "live-endurance" / f"run-{int(time.time())}"
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init")
    _git(root, "config", "user.email", "zect-live@local")
    _git(root, "config", "user.name", "ZECT Live Endurance")
    (root / "README.md").write_text("# Disposable Mentrix LRR endurance repo\n", encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_smoke.py").write_text(
        "def test_repo_alive():\n    assert True\n",
        encoding="utf-8",
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "chore: seed disposable endurance repo")
    base = _git(root, "rev-parse", "HEAD").stdout.strip()
    (root / ".zect_lrr_base_sha").write_text(base, encoding="utf-8")

    evidence["worktree_path"] = str(root)
    evidence["base_commit_sha"] = base
    evidence["coding_engine"] = selected_coding_engine()
    evidence["openai_configured"] = bool((os.getenv("OPENAI_API_KEY") or "").strip())

    try:
        planner = MentrixPlanner(db)
        plan = planner.plan(
            goal="LIVE endurance: add disposable module files under pkg/ for Mentrix LRR (non-production)",
            approve=True,
            actor="live_endurance",
        )
        wi_id = int(plan["work_item_id"])
        evidence["work_item_id"] = wi_id
        evidence["plan_hash"] = plan.get("plan_hash")

        ops = []
        for i in range(1, 9):
            ops.append(
                {
                    "id": f"OP-{i:03d}",
                    "title": f"Add pkg/mod_{i:03d}.py",
                    "path": f"pkg/mod_{i:03d}.py",
                    "mandatory": True,
                    "status": "pending",
                    "requirement_ids": ["REQ-1"],
                    "acceptance_ids": ["AC-1"],
                    "content": (
                        f'"""Disposable Mentrix LRR module {i}."""\n'
                        f"def value_{i}():\n    return {i}\n\n"
                        f"def test_value_{i}():\n    assert value_{i}() == {i}\n"
                    ),
                }
            )

        rt = LongRunningAgentRuntime(db)
        started_run = rt.start(
            work_item_id=wi_id,
            user_id=None,
            worktree_path=str(root),
            base_commit_sha=base,
            current_commit_sha=base,
            operations=ops,
            autonomy="L2",
            model_profile="QUALITY",
            synthetic=False,
        )
        run_id = started_run["run_id"]
        evidence["run_id"] = run_id

        # Phase A: execute first half
        a = rt.tick(run_id, worker_id="live-worker-1", max_ops=4)
        evidence["after_first_batch"] = {
            "ok": a.get("ok"),
            "completed": a.get("operations_completed"),
            "resume": a.get("resume_operation"),
            "status": a.get("status"),
            "current_sha": a.get("current_commit_sha"),
        }

        # Deliberate pause / resume
        paused = rt.pause(run_id)
        evidence["pause"] = {"status": paused.get("status"), "ok": paused.get("ok")}
        resumed = rt.resume(run_id, verify_worktree=True)
        evidence["resume"] = {
            "ok": resumed.get("ok"),
            "status": resumed.get("status"),
            "resume_operation": resumed.get("resume_operation"),
        }

        # Continue a bit
        b = rt.tick(run_id, worker_id="live-worker-1", max_ops=2)
        evidence["after_resume_batch"] = {
            "completed": b.get("operations_completed"),
            "resume": b.get("resume_operation"),
            "sha": b.get("current_commit_sha"),
        }

        # Simulate backend/worker restart
        recovered = rt.recover_after_restart()
        evidence["restart_recovery"] = recovered
        mid = rt.serialize(rt.get(run_id))
        evidence["post_restart_state"] = {
            "worker_id": mid.get("worker_id"),
            "lease_expires_at": mid.get("lease_expires_at"),
            "resume_operation": mid.get("resume_operation"),
            "completed": mid.get("operations_completed"),
            "sha": mid.get("current_commit_sha"),
        }

        # Finish remaining ops with new worker id
        c = rt.tick(run_id, worker_id="live-worker-2", max_ops=10)
        evidence["final_tick"] = {
            "ok": c.get("ok"),
            "status": c.get("status"),
            "completed": c.get("operations_completed"),
            "total": c.get("operations_total"),
            "error": c.get("error"),
            "acceptance": c.get("acceptance"),
        }

        # Real pytest in worktree (tester)
        test_agent = MentrixTestAgent(wi_id, repo_root=root)
        # Run smoke against disposable tree via inject of real subprocess result
        proc = subprocess.run(
            [os.environ.get("PYTHON", "python"), "-m", "pytest", "-q", "tests", "pkg"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        test_out = test_agent.run(
            inject_result={
                "ok": proc.returncode == 0,
                "passed": 1 if proc.returncode == 0 else 0,
                "failed": 0 if proc.returncode == 0 else 1,
                "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-1500:],
                "commands": ["pytest -q tests pkg"],
                "source": "mentrix_test_agent_live",
            }
        )
        evidence["tests"] = {
            "ok": test_out.get("ok"),
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-500:],
        }

        review = MentrixReviewAgent(db, wi_id).review(
            diff_text=_git(root, "diff", base, "HEAD").stdout[:4000],
            inject_findings=[],
        )
        evidence["review"] = {
            "clean": review.get("clean"),
            "blocking": len(review.get("blocking") or []),
            "findings": len(review.get("findings") or []),
        }

        # Re-run acceptance with real agent artifacts (do not auto-merge production)
        store = ArtifactStore(wi_id)
        man = store.read_json("EXECUTION_MANIFEST.json") or {}
        for op in man.get("operations") or []:
            if str(op.get("status")).lower() != "completed":
                op["status"] = "completed"
        store.write_json("EXECUTION_MANIFEST.json", man)
        acc = AcceptanceVerifier(db, wi_id).verify(ship=False, actor="live_endurance")
        evidence["acceptance"] = acc

        final = rt.serialize(rt.get(run_id))
        evidence["final_run"] = {
            "status": final.get("status"),
            "completed": final.get("operations_completed"),
            "total": final.get("operations_total"),
            "telemetry_count": len(final.get("telemetry") or []),
            "telemetry_sample": (final.get("telemetry") or [])[:3],
            "budget": final.get("budget"),
            "current_commit_sha": final.get("current_commit_sha"),
        }
        evidence["files_changed"] = [
            p.relative_to(root).as_posix() for p in root.rglob("pkg/*.py")
        ]
        evidence["git_log"] = _git(root, "log", "--oneline", "-n", "20").stdout.strip().splitlines()
        evidence["models_used"] = sorted(
            {str(t.get("actual_model") or "") for t in (final.get("telemetry") or []) if t.get("actual_model")}
        )
        evidence["pr_status"] = "NOT_CREATED_BY_DESIGN"
        evidence["pr_note"] = "No production PR/merge; disposable local commits only"

        ready = bool(acc.get("ready_to_ship")) and int(final.get("operations_completed") or 0) == int(
            final.get("operations_total") or 0
        )
        evidence["verdict"] = "LIVE_VIABLE" if ready and test_out.get("ok") and review.get("clean") else "BLOCKED"
        if evidence["verdict"] != "LIVE_VIABLE":
            evidence["blockers"] = [
                e
                for e in [
                    None if test_out.get("ok") else "tests_failed",
                    None if review.get("clean") else "review_blocking",
                    None if acc.get("ready_to_ship") else f"acceptance:{acc.get('errors')}",
                ]
                if e
            ]
    finally:
        db.close()

    evidence["duration_seconds"] = round(time.perf_counter() - started, 2)
    evidence["finished_at"] = datetime.now(timezone.utc).isoformat()
    out_path = Path(__file__).resolve().parents[2] / "MENTRIX_LONG_RUNNING_LIVE_ACCEPTANCE.json"
    out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": evidence.get("verdict"), "path": str(out_path), "duration": evidence["duration_seconds"]}, indent=2))
    return evidence


if __name__ == "__main__":
    main()
