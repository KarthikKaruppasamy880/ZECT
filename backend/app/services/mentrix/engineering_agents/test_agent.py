"""Mentrix Test Agent — independent verification worker (deterministic tools first)."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.mentrix.engineering_agents.roles import ROLE_TESTER
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.checkpoints import record_checkpoint


class MentrixTestAgent:
    """Produce TEST_RESULTS.json; never hide failures; never READY_TO_SHIP."""

    role = ROLE_TESTER

    def __init__(self, work_item_id: int, *, repo_root: Path | None = None) -> None:
        self.work_item_id = work_item_id
        self.store = ArtifactStore(work_item_id)
        self.repo_root = repo_root or Path(__file__).resolve().parents[5]

    def determine_suites(self, *, changed_files: list[str] | None = None) -> list[str]:
        suites = ["unit"]
        files = changed_files or []
        blob = " ".join(files).lower()
        if "frontend" in blob or blob.endswith((".tsx", ".ts")):
            suites.extend(["frontend", "typecheck"])
        if "api" in blob or "router" in blob:
            suites.append("api")
        if "migration" in blob or "alembic" in blob:
            suites.append("migration")
        return list(dict.fromkeys(suites))

    def run(
        self,
        *,
        suites: list[str] | None = None,
        pytest_args: list[str] | None = None,
        inject_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run deterministic verification. inject_result used by unit tests to avoid heavy CI."""
        record_checkpoint(self.store, checkpoint_type="op_start", operation_id="test_agent")
        chosen = suites or self.determine_suites()
        if inject_result is not None:
            result = dict(inject_result)
            result.setdefault("suites", chosen)
            result.setdefault("at", datetime.now(timezone.utc).isoformat())
            result.setdefault("role", self.role)
            result["route_back_to_coder"] = not bool(result.get("ok"))
            result["may_ready_to_ship"] = False
            self.store.write_json("TEST_RESULTS.json", result)
            record_checkpoint(
                self.store,
                checkpoint_type="verification",
                operation_id="test_agent",
                payload={"ok": result.get("ok"), "failed": result.get("failed")},
            )
            return result

        # Deterministic default: run a bounded pytest subset when args provided
        cmd = [sys.executable, "-m", "pytest", "-q", "--tb=no"]
        if pytest_args:
            cmd.extend(pytest_args)
        else:
            # Soft smoke — do not claim full suite without args
            result = {
                "ok": False,
                "passed": 0,
                "failed": 0,
                "skipped": True,
                "unverified": True,
                "reason": "no_pytest_args_unverified",
                "suites": chosen,
                "at": datetime.now(timezone.utc).isoformat(),
                "role": self.role,
                "route_back_to_coder": False,
                "may_ready_to_ship": False,
                "commands": [],
            }
            self.store.write_json("TEST_RESULTS.json", result)
            record_checkpoint(
                self.store,
                checkpoint_type="verification",
                operation_id="test_agent",
                payload={"ok": False, "unverified": True},
            )
            return result

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.repo_root / "backend"),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            ok = proc.returncode == 0
            result = {
                "ok": ok,
                "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-2000:],
                "stderr_tail": (proc.stderr or "")[-1000:],
                "suites": chosen,
                "commands": [" ".join(cmd)],
                "at": datetime.now(timezone.utc).isoformat(),
                "role": self.role,
                "route_back_to_coder": not ok,
                "may_ready_to_ship": False,
                "failed": 0 if ok else 1,
                "passed": 1 if ok else 0,
            }
        except Exception as exc:  # noqa: BLE001
            result = {
                "ok": False,
                "error": str(exc)[:500],
                "suites": chosen,
                "at": datetime.now(timezone.utc).isoformat(),
                "role": self.role,
                "route_back_to_coder": True,
                "may_ready_to_ship": False,
                "failed": 1,
                "passed": 0,
            }

        self.store.write_json("TEST_RESULTS.json", result)
        record_checkpoint(
            self.store,
            checkpoint_type="verification" if result.get("ok") else "failure",
            operation_id="test_agent",
            payload={"ok": result.get("ok")},
        )
        return result
