"""Mentrix Planner — internal planning worker (no production edits, no READY_TO_SHIP)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.services.mentrix.engineering_agents.roles import ROLE_PLANNER, planner_may_write_path, role_may_declare_ready_to_ship
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.checkpoints import record_checkpoint
from app.services.work_items.developer_service import MentrixDeveloperService
from app.services.work_items.telemetry import TelemetryTimer, build_telemetry


class MentrixPlanner:
    """Analyze requirements → ArtifactStore PLAN/REQUIREMENTS/ACCEPTANCE/RISKS/MANIFEST."""

    role = ROLE_PLANNER

    def __init__(self, db: Session) -> None:
        self.db = db
        self.dev = MentrixDeveloperService(db)

    def plan(
        self,
        *,
        goal: str,
        work_item_id: int | None = None,
        project_id: int | None = None,
        repository_id: int | None = None,
        actor: str = "mentrix_planner",
        approve: bool = False,
    ) -> dict[str, Any]:
        if role_may_declare_ready_to_ship(self.role):
            # Defensive: planner must never be allowed to ship
            raise RuntimeError("planner_role_misconfigured")

        timer = TelemetryTimer()
        out = self.dev.plan(
            goal=goal,
            work_item_id=work_item_id,
            project_id=project_id,
            repository_id=repository_id,
            actor=actor,
        )
        wi_id = int(out["work_item_id"])
        store = ArtifactStore(wi_id)
        plan_text = str(out.get("plan") or "")

        # Structured companion artifacts (ArtifactStore only — never production code)
        reqs = [
            {"id": "REQ-1", "text": goal[:500], "operations": ["OP-1"], "verification": ["unit"], "acceptance": ["AC-1"]},
        ]
        acs = [{"id": "AC-1", "text": f"Goal satisfied with evidence: {goal[:200]}", "requirement_ids": ["REQ-1"]}]
        risks = [{"id": "RISK-1", "text": "Scope creep / incomplete verification", "mitigation": "budgets + EvidenceVerifier"}]
        manifest = {
            "work_item_id": wi_id,
            "operations": [
                {
                    "id": "OP-1",
                    "title": "Implement planned change",
                    "requirement_ids": ["REQ-1"],
                    "acceptance_ids": ["AC-1"],
                    "mandatory": True,
                    "status": "pending",
                }
            ],
            "mandatory_operation_ids": ["OP-1"],
            "requirement_ids": ["REQ-1"],
            "acceptance_ids": ["AC-1"],
            "planner_role": self.role,
            "may_edit_production_code": False,
            "may_ready_to_ship": False,
        }

        for name, content in (
            ("REQUIREMENTS.md", "# Requirements\n\n" + "\n".join(f"- {r['id']}: {r['text']}" for r in reqs)),
            ("ACCEPTANCE.md", "# Acceptance\n\n" + "\n".join(f"- {a['id']}: {a['text']}" for a in acs)),
            ("RISKS.md", "# Risks\n\n" + "\n".join(f"- {r['id']}: {r['text']} ({r['mitigation']})" for r in risks)),
        ):
            path = str(store.path(name))
            if not planner_may_write_path(path):
                raise PermissionError(f"planner_forbidden_write:{path}")
            store.write_text(name, content)

        store.write_json("EXECUTION_MANIFEST.json", manifest)
        state = store.read_json("EXECUTION_STATE.json", default={}) or {}
        state["requirements"] = reqs
        state["acceptance"] = acs
        state["risks"] = risks
        state["phase"] = "planned"
        state["planner"] = self.role
        store.write_json("EXECUTION_STATE.json", state)
        record_checkpoint(store, checkpoint_type="completion", operation_id="planner", payload={"work_item_id": wi_id})

        from app.adapters.llm.openai_compat import mentrix_llm_chat_model, mentrix_local_llm_configured
        from app.services.work_items.fallback_policy import resolve_model_route
        import os

        route = resolve_model_route(
            local_configured=mentrix_local_llm_configured(),
            cloud_configured=bool((os.getenv("OPENAI_API_KEY") or "").strip()),
            local_model=mentrix_llm_chat_model(),
        )
        tel = build_telemetry(
            requested_provider="local" if mentrix_local_llm_configured() else "cloud",
            requested_model=mentrix_llm_chat_model(),
            actual_provider=route.provider,
            actual_model=route.model or mentrix_llm_chat_model(),
            fallback_used=route.fallback_used,
            fallback_reason=route.fallback_reason,
            latency_ms=timer.latency_ms(),
            work_item_id=wi_id,
            operation_id="planner",
        )

        approved = False
        if approve:
            self.dev.approve_plan(work_item_id=wi_id, actor=actor)
            approved = True

        return {
            "ok": True,
            "role": self.role,
            "work_item_id": wi_id,
            "plan": plan_text,
            "plan_hash": out.get("plan_hash") or store.plan_hash(),
            "manifest": manifest,
            "artifacts": ["PLAN.md", "REQUIREMENTS.md", "ACCEPTANCE.md", "RISKS.md", "EXECUTION_MANIFEST.json"],
            "may_edit_production_code": False,
            "may_ready_to_ship": False,
            "approved": approved,
            "telemetry": tel,
            "needs_approval": not approved,
        }

    def refuse_production_edit(self, path: str) -> dict[str, Any]:
        return {
            "ok": False,
            "role": self.role,
            "error": "planner_cannot_edit_production_code",
            "path": path,
            "allowed": planner_may_write_path(path),
        }

    def refuse_ready_to_ship(self) -> dict[str, Any]:
        return {
            "ok": False,
            "role": self.role,
            "error": "planner_cannot_ready_to_ship",
            "may_ready_to_ship": False,
        }
