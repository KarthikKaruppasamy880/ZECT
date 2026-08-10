"""MentrixDeveloperService — ASK / PLAN / AGENT orchestration (P0)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.work_items import service as wi_svc
from app.domains.work_items.events import append_event
from app.domains.work_items.status import (
    STATUS_EXECUTING,
    STATUS_IMPLEMENTED,
    STATUS_NEEDS_HUMAN_DECISION,
    STATUS_PLAN_APPROVED,
    STATUS_PLANNED,
    STATUS_READY_TO_SHIP,
    STATUS_VERIFYING,
)
from app.models import MentrixRun, WorkItem
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.checkpoints import load_execution_state, record_checkpoint
from app.services.work_items.context_engine import MentrixContextEngine
from app.services.work_items.evidence_verifier import EvidenceVerifier
from app.services.work_items.fallback_policy import resolve_model_route
from app.services.work_items.project_intelligence import ProjectIntelligenceService
from app.services.work_items.telemetry import TelemetryTimer, build_telemetry


class MentrixDeveloperService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.context_engine = MentrixContextEngine()
        self.pi = ProjectIntelligenceService()
        self.verifier = EvidenceVerifier()

    def _store(self, work_item_id: int) -> ArtifactStore:
        return ArtifactStore(work_item_id)

    def _ensure_work_item(
        self,
        *,
        work_item_id: int | None,
        title: str,
        project_id: int | None,
        repository_id: int | None,
        repository_ref: str,
        base_commit_sha: str,
        actor: str,
    ) -> WorkItem:
        if work_item_id:
            return wi_svc.get_work_item(self.db, work_item_id)
        return wi_svc.create_work_item(
            self.db,
            title=title[:200],
            description=title,
            project_id=project_id,
            repository_id=repository_id,
            repository_ref=repository_ref,
            base_commit_sha=base_commit_sha,
            created_by=actor,
        )

    def _build_pack(self, wi: WorkItem, goal: str) -> dict[str, Any]:
        project_key = ""
        try:
            if wi.project_id and self.db is not None:
                from app.models import Project

                p = self.db.query(Project).filter(Project.id == wi.project_id).first()
                project_key = (getattr(p, "name", None) or getattr(p, "key", None) or "") if p else ""
        except Exception:  # noqa: BLE001
            project_key = ""
        snap = self.pi.snapshot(
            project_id=wi.project_id,
            project_key=str(project_key or ""),
            repository_id=wi.repository_id,
            db=self.db,
            query=goal,
        )
        pack = self.context_engine.build(
            work_item_id=wi.id,
            repository_id=wi.repository_id,
            repository_ref=wi.repository_ref or "",
            base_commit_sha=wi.base_commit_sha or "",
            goal=goal,
            knowledge_hits=snap.knowledge,
            memory_hits=snap.memory,
            lattice_hits=list((snap.lattice or {}).get("hits") or []),
            blueprint_snippet=str((snap.blueprint or {}).get("snippet") or ""),
        )
        return {"pack": pack.to_dict(), "pi": snap.to_dict()}

    def ask(
        self,
        *,
        question: str,
        work_item_id: int | None = None,
        project_id: int | None = None,
        repository_id: int | None = None,
        repository_ref: str = "",
        base_commit_sha: str = "",
        actor: str = "",
    ) -> dict[str, Any]:
        wi = self._ensure_work_item(
            work_item_id=work_item_id,
            title=f"Ask: {question[:80]}",
            project_id=project_id,
            repository_id=repository_id,
            repository_ref=repository_ref,
            base_commit_sha=base_commit_sha,
            actor=actor,
        )
        built = self._build_pack(wi, question)
        timer = TelemetryTimer()
        from app.adapters.llm.openai_compat import (
            mentrix_llm_chat_model,
            mentrix_local_llm_configured,
            openai_compat_available,
        )
        from app.services.phases import llm_phase

        route = resolve_model_route(
            local_configured=mentrix_local_llm_configured(),
            cloud_configured=bool((__import__("os").getenv("OPENAI_API_KEY") or "").strip()),
            local_model=mentrix_llm_chat_model(),
        )
        if route.blocked and route.provider == "none":
            # Still allow offline clarifying answer via llm_phase offline path
            pass
        result = llm_phase.run_ask(
            question,
            repo_context=MentrixContextEngine()
            .build(
                work_item_id=wi.id,
                repository_id=wi.repository_id,
                repository_ref=wi.repository_ref or "",
                base_commit_sha=wi.base_commit_sha or "",
                goal=question,
                knowledge_hits=built["pi"].get("knowledge") or [],
                memory_hits=built["pi"].get("memory") or [],
                lattice_hits=(built["pi"].get("lattice") or {}).get("hits") or [],
                blueprint_snippet=str((built["pi"].get("blueprint") or {}).get("snippet") or ""),
            )
            .text_blob(),
            repo_id=wi.repository_id,
            db=self.db,
        )
        tel = build_telemetry(
            requested_provider="local" if mentrix_local_llm_configured() else "cloud",
            requested_model=mentrix_llm_chat_model(),
            actual_provider=route.provider if not result.get("offline") else "offline",
            actual_model=str(result.get("model") or ""),
            fallback_used=route.fallback_used,
            fallback_reason=route.fallback_reason,
            latency_ms=timer.latency_ms(),
            work_item_id=wi.id,
            operation_id="ask",
        )
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="ask",
            payload={"question": question[:500], "telemetry": tel},
            commit=True,
        )
        return {
            "work_item_id": wi.id,
            "answer": result.get("answer"),
            "context_pack": built["pack"],
            "project_intelligence": built["pi"],
            "telemetry": tel,
            "result": result,
        }

    def plan(
        self,
        *,
        goal: str,
        work_item_id: int | None = None,
        project_id: int | None = None,
        repository_id: int | None = None,
        repository_ref: str = "",
        base_commit_sha: str = "",
        constraints: str = "",
        actor: str = "",
    ) -> dict[str, Any]:
        wi = self._ensure_work_item(
            work_item_id=work_item_id,
            title=f"Plan: {goal[:80]}",
            project_id=project_id,
            repository_id=repository_id,
            repository_ref=repository_ref,
            base_commit_sha=base_commit_sha,
            actor=actor,
        )
        store = self._store(wi.id)
        record_checkpoint(store, checkpoint_type="op_start", operation_id="plan")
        built = self._build_pack(wi, goal)
        from app.services.phases import llm_phase

        result = llm_phase.run_plan(
            goal,
            repo_context=MentrixContextEngine()
            .build(
                work_item_id=wi.id,
                repository_id=wi.repository_id,
                repository_ref=wi.repository_ref or "",
                base_commit_sha=wi.base_commit_sha or "",
                goal=goal,
                knowledge_hits=built["pi"].get("knowledge") or [],
                memory_hits=built["pi"].get("memory") or [],
                lattice_hits=(built["pi"].get("lattice") or {}).get("hits") or [],
                blueprint_snippet=str((built["pi"].get("blueprint") or {}).get("snippet") or ""),
            )
            .text_blob(),
            constraints=constraints,
            repo_id=wi.repository_id,
            db=self.db,
            upgrade=True,
        )
        plan_text = str(result.get("plan") or "")
        written = store.write_plan(plan_text)
        new_hash = written["plan_hash"]
        material_change = bool(wi.approved_plan_hash and wi.approved_plan_hash != new_hash)
        wi.plan_version = int(wi.plan_version or 0) + 1
        wi.plan_hash = new_hash
        if material_change:
            wi.approved_plan_hash = None
            wi.status = STATUS_NEEDS_HUMAN_DECISION
            append_event(
                self.db,
                work_item_id=wi.id,
                event_type="plan_reapproval_required",
                payload={"plan_hash": new_hash, "previous_approved": True},
            )
        else:
            wi.status = STATUS_PLANNED
        # Dual-write MentrixRun compatibility mirror
        run = MentrixRun(
            project_id=wi.project_id,
            mode="plan",
            goal=goal,
            status="completed",
            result_json=json.dumps({"plan": plan_text, "work_item_id": wi.id}, default=str),
            created_by=actor,
        )
        self.db.add(run)
        self.db.flush()
        wi.mentrix_run_id = run.id
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="plan_written",
            payload={
                "plan_hash": new_hash,
                "plan_version": wi.plan_version,
                "artifact_path": written["path"],
                "mentrix_run_id": run.id,
            },
        )
        self.db.commit()
        self.db.refresh(wi)
        record_checkpoint(store, checkpoint_type="completion", operation_id="plan", payload={"plan_hash": new_hash})
        return {
            "work_item_id": wi.id,
            "plan": plan_text,
            "plan_hash": new_hash,
            "plan_version": wi.plan_version,
            "status": wi.status,
            "reapproval_required": material_change,
            "artifact_path": written["path"],
            "context_pack": built["pack"],
            "project_intelligence": built["pi"],
            "mentrix_run_id": run.id,
        }

    def approve_plan(self, *, work_item_id: int, actor: str = "") -> dict[str, Any]:
        wi = wi_svc.get_work_item(self.db, work_item_id)
        store = self._store(wi.id)
        plan = store.read_plan()
        if not plan.strip():
            raise HTTPException(status_code=400, detail="plan_missing")
        h = store.plan_hash()
        wi.plan_hash = h
        wi.approved_plan_hash = h
        wi.status = STATUS_PLAN_APPROVED
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="plan_approved",
            payload={"approved_plan_hash": h, "actor": actor},
        )
        self.db.commit()
        self.db.refresh(wi)
        record_checkpoint(store, checkpoint_type="completion", operation_id="approve_plan", payload={"hash": h})
        return wi_svc.serialize_work_item(wi)

    def start_agent(
        self,
        *,
        work_item_id: int,
        goal: str = "",
        workspace: str = "",
        actor: str = "",
        deterministic: bool = False,
    ) -> dict[str, Any]:
        import os
        from pathlib import Path

        wi = wi_svc.get_work_item(self.db, work_item_id)
        if wi.status not in (STATUS_PLAN_APPROVED, STATUS_EXECUTING, STATUS_NEEDS_HUMAN_DECISION):
            # Allow EXECUTING resume; require approve unless deterministic e2e helper
            if wi.approved_plan_hash != wi.plan_hash or not wi.approved_plan_hash:
                raise HTTPException(status_code=409, detail="plan_not_approved")
        store = self._store(wi.id)
        record_checkpoint(store, checkpoint_type="op_start", operation_id="agent")
        ws = (workspace or wi.worktree_path or "").strip()
        if not ws:
            # default worktree under artifact store
            ws = str(store.root / "worktree")
            Path(ws).mkdir(parents=True, exist_ok=True)
        wi.worktree_path = ws
        wi.status = STATUS_EXECUTING
        agent_goal = goal or store.read_plan()[:1500] or wi.title
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="agent_started",
            payload={"workspace": ws, "goal": agent_goal[:500], "actor": actor},
        )
        self.db.commit()

        use_det = deterministic or (os.getenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE") or "").strip() in (
            "1",
            "true",
            "yes",
        )
        files_written: list[str] = []
        events_tail: list[Any] = []
        run_id = ""
        engine = "mentrix_native"

        if use_det:
            from app.services.coding_engine.mentrix_agent_tools import execute_tool, resolve_workspace

            root = resolve_workspace(ws)
            # real read/edit/run/diff path (same tools Coding Agent uses)
            execute_tool("list_dir", {"path": "."}, workspace=root)
            w = execute_tool(
                "write_file",
                {"path": "mentrix_p0_agent_marker.py", "content": "# mentrix p0\nprint('ok')\n"},
                workspace=root,
            )
            r = execute_tool("read_file", {"path": "mentrix_p0_agent_marker.py"}, workspace=root)
            cmd = execute_tool("run_command", {"command": "python mentrix_p0_agent_marker.py"}, workspace=root)
            files_written = ["mentrix_p0_agent_marker.py"] if w.get("ok") else []
            events_tail = [
                {"event": "tool", "name": "write_file", "ok": w.get("ok"), "file_diff": w.get("file_diff")},
                {"event": "tool", "name": "read_file", "ok": r.get("ok")},
                {"event": "tool", "name": "run_command", "ok": cmd.get("ok"), "exit": cmd.get("exit_code")},
            ]
            run_id = f"deterministic-{wi.id}"
            record_checkpoint(
                store,
                checkpoint_type="file_change",
                operation_id="agent",
                payload={"files": files_written},
                worktree_path=ws,
                base_commit_sha=wi.base_commit_sha or "",
                current_commit_sha=wi.current_commit_sha or wi.base_commit_sha or "",
            )
            record_checkpoint(
                store,
                checkpoint_type="command_execution",
                operation_id="agent",
                payload={"command": "python mentrix_p0_agent_marker.py", "result": cmd},
            )
        else:
            from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build

            native = run_mentrix_native_build(
                goal=agent_goal,
                workspace=ws,
                expected_files=["mentrix_p0_agent_marker.py"],
                project_id=wi.project_id,
            )
            files_written = list(native.get("files_written") or [])
            events_tail = list(native.get("events_tail") or [])
            run_id = str(native.get("run_id") or "")
            engine = str(native.get("engine") or "mentrix_native")
            record_checkpoint(
                store,
                checkpoint_type="file_change",
                operation_id="agent",
                payload={"files": files_written, "native": native.get("ok")},
                worktree_path=ws,
                base_commit_sha=wi.base_commit_sha or "",
                current_commit_sha=wi.current_commit_sha or "",
            )

        wi.status = STATUS_IMPLEMENTED if files_written else STATUS_EXECUTING
        wi.current_commit_sha = wi.current_commit_sha or wi.base_commit_sha or ""
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="agent_completed_slice",
            payload={"run_id": run_id, "files_written": files_written, "engine": engine},
        )
        self.db.commit()
        self.db.refresh(wi)
        return {
            "work_item_id": wi.id,
            "status": wi.status,
            "run_id": run_id,
            "files_written": files_written,
            "events_tail": events_tail,
            "engine": engine,
            "worktree_path": ws,
        }

    def continue_agent(self, *, work_item_id: int, goal: str = "", actor: str = "") -> dict[str, Any]:
        return self.start_agent(work_item_id=work_item_id, goal=goal, actor=actor)

    def cancel_agent(self, *, work_item_id: int, actor: str = "") -> dict[str, Any]:
        wi = wi_svc.transition_status(
            self.db,
            work_item_id,
            "CANCELLED",
            reason="agent_cancelled",
            actor=actor,
        )
        store = self._store(work_item_id)
        record_checkpoint(store, checkpoint_type="blocking", operation_id="cancel", payload={"actor": actor})
        return wi_svc.serialize_work_item(wi)

    def resume(self, *, work_item_id: int, actor: str = "") -> dict[str, Any]:
        wi = wi_svc.get_work_item(self.db, work_item_id)
        store = self._store(wi.id)
        state = load_execution_state(store)
        wi.worktree_path = state.get("worktree_path") or wi.worktree_path
        wi.base_commit_sha = state.get("base_commit_sha") or wi.base_commit_sha
        wi.current_commit_sha = state.get("current_commit_sha") or wi.current_commit_sha
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="resume",
            payload={"state": state, "actor": actor},
        )
        self.db.commit()
        self.db.refresh(wi)
        return {
            "work_item": wi_svc.serialize_work_item(wi),
            "execution_state": state,
            "resume_operation": state.get("resume_operation"),
        }

    def verify_and_ready_to_ship(
        self,
        *,
        work_item_id: int,
        mandatory_operation_ids: list[str],
        requirement_ids: list[str],
        acceptance_ids: list[str],
        evidence: list[dict[str, Any]],
        actor: str = "EvidenceVerifier",
    ) -> dict[str, Any]:
        wi = wi_svc.get_work_item(self.db, work_item_id)
        store = self._store(wi.id)
        wi.status = STATUS_VERIFYING
        self.db.commit()
        record_checkpoint(store, checkpoint_type="verification", operation_id="verify")
        result = self.verifier.verify(
            mandatory_operation_ids=mandatory_operation_ids,
            requirement_ids=requirement_ids,
            acceptance_ids=acceptance_ids,
            evidence=evidence,
        )
        store.write_json(
            "EVIDENCE.json",
            {"evidence": evidence, "verification": result.to_dict()},
        )
        close_loop_result: dict[str, Any] | None = None
        if result.ready_to_ship:
            wi = wi_svc.transition_status(
                self.db,
                work_item_id,
                STATUS_READY_TO_SHIP,
                reason="evidence_verified",
                allow_gate=True,
                actor=actor,
            )
            record_checkpoint(store, checkpoint_type="completion", operation_id="ready_to_ship")
            # OP-040: optional external close (dry_run by default — no live Jira/Camunda)
            try:
                from app.services.work_items.close_loop import close_external_loop

                close_loop_result = close_external_loop(
                    self.db,
                    work_item_id=wi.id,
                    dry_run=True,
                )
            except Exception as exc:  # noqa: BLE001
                close_loop_result = {"ok": False, "error": str(exc)[:300]}
        else:
            append_event(
                self.db,
                work_item_id=wi.id,
                event_type="verification_failed",
                payload=result.to_dict(),
                commit=True,
            )
            record_checkpoint(
                store,
                checkpoint_type="failure",
                operation_id="verify",
                payload=result.to_dict(),
            )
        out: dict[str, Any] = {
            "work_item": wi_svc.serialize_work_item(wi),
            "verification": result.to_dict(),
        }
        if close_loop_result is not None:
            out["close_loop"] = close_loop_result
        return out
