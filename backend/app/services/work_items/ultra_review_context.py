"""Ultra Review consumes WorkItem ContextPack + typed evidence (no second engine)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domains.work_items import service as wi_svc
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.context_engine import MentrixContextEngine
from app.services.work_items.project_intelligence import ProjectIntelligenceService


def build_ultrareview_work_item_context(
    db: Session,
    *,
    work_item_id: int,
    query: str = "",
) -> dict[str, Any]:
    """Assemble review inputs from WorkItem + PI + ContextPack + ArtifactStore evidence."""
    wi = wi_svc.get_work_item(db, work_item_id)
    goal = (query or wi.title or "").strip()
    pi = ProjectIntelligenceService().snapshot(
        project_id=wi.project_id,
        repository_id=wi.repository_id,
        db=db,
        query=goal,
    )
    pack = MentrixContextEngine().build(
        work_item_id=wi.id,
        repository_id=wi.repository_id,
        repository_ref=wi.repository_ref or "",
        base_commit_sha=wi.base_commit_sha or "",
        goal=goal,
        knowledge_hits=pi.knowledge,
        memory_hits=pi.memory,
        blueprint_snippet=str((pi.blueprint or {}).get("snippet") or ""),
    )
    store = ArtifactStore(wi.id)
    evidence_doc: dict[str, Any] = {}
    try:
        evidence_doc = store.read_json("EVIDENCE.json") or {}
    except Exception:  # noqa: BLE001
        evidence_doc = {}
    plan = ""
    try:
        plan = store.read_plan() or ""
    except Exception:  # noqa: BLE001
        plan = ""

    return {
        "work_item": wi_svc.serialize_work_item(wi),
        "context_pack": pack.to_dict(),
        "project_intelligence": pi.to_dict(),
        "plan_excerpt": plan[:4000],
        "evidence": evidence_doc.get("evidence") or [],
        "verification": evidence_doc.get("verification") or {},
        "review_prompt_prefix": (
            f"WorkItem #{wi.id} [{wi.status}] {wi.title}\n"
            f"Repo={wi.repository_id}:{wi.repository_ref}@{wi.base_commit_sha}\n"
            f"Use ContextPack provenance; do not invent files.\n"
        ),
        "engine": "review_service",  # canonical Ultra Review engine — no parallel
    }
