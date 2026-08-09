"""ProjectIntelligenceService — live Lattice/Blueprint/KB/Memory/Skills/Playbooks (P1)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ProjectIntelligenceSnapshot:
    lattice: dict[str, Any] = field(default_factory=dict)
    blueprint: dict[str, Any] = field(default_factory=dict)
    knowledge: list[dict[str, Any]] = field(default_factory=list)
    memory: list[dict[str, Any]] = field(default_factory=list)
    related_work: list[dict[str, Any]] = field(default_factory=list)
    skill_selection: list[dict[str, Any]] = field(default_factory=list)
    playbook_selection: list[dict[str, Any]] = field(default_factory=list)
    freshness: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        assert "knowledge" in d and "memory" in d
        assert d["knowledge"] is not d["memory"]
        return d


class ProjectIntelligenceService:
    """Assemble Project Intelligence snapshot for MentrixDeveloperService."""

    def snapshot(
        self,
        *,
        project_id: int | None = None,
        project_key: str = "",
        repository_id: int | None = None,
        db: Any = None,
        related_work: list[dict[str, Any]] | None = None,
        query: str = "",
        user_id: int | None = None,
    ) -> ProjectIntelligenceSnapshot:
        lattice: dict[str, Any] = {"status": "unavailable", "hits": []}
        blueprint: dict[str, Any] = {"snippet": "", "freshness": "unknown"}
        knowledge: list[dict[str, Any]] = []
        memory: list[dict[str, Any]] = []
        skills: list[dict[str, Any]] = []
        playbooks: list[dict[str, Any]] = []
        related = list(related_work or [])

        # Lattice
        try:
            if project_key:
                try:
                    from app.services.lattice.indexer import get_lattice_status  # type: ignore

                    lattice = {"status": "ok", "detail": get_lattice_status(project_key), "hits": []}
                except Exception:  # noqa: BLE001
                    lattice = {"status": "ok", "project_key": project_key, "hits": [], "freshness": "ephemeral"}
        except Exception:  # noqa: BLE001
            lattice = {"status": "unavailable", "hits": []}

        # Blueprint
        try:
            if db is not None and project_key:
                from app.models import LatticeStructuralBlueprint

                row = (
                    db.query(LatticeStructuralBlueprint)
                    .filter(LatticeStructuralBlueprint.project_key == project_key)
                    .first()
                )
                if row:
                    blueprint = {
                        "snippet": (
                            f"blueprint:{project_key} commit={getattr(row, 'indexed_commit_sha', '')} "
                            f"status={getattr(row, 'status', '')}"
                        )[:2000],
                        "freshness": getattr(row, "status", "unknown"),
                        "indexed_commit_sha": getattr(row, "indexed_commit_sha", ""),
                        "workspace_path": getattr(row, "workspace_path", ""),
                    }
        except Exception:  # noqa: BLE001
            pass

        # Knowledge (curated truth)
        try:
            if db is not None:
                from app.domains.repository.knowledge_base import retrieve_knowledge_for_context

                block, meta = retrieve_knowledge_for_context(
                    db,
                    query=query or project_key or "project",
                    project_id=project_id,
                    limit=5,
                )
                if block:
                    knowledge.append(
                        {
                            "id": "kb-context",
                            "content": str(block)[:3000],
                            "score": 1.0,
                            "freshness": "curated",
                            "verification_state": "curated",
                            "meta": meta or {},
                        }
                    )
        except Exception:  # noqa: BLE001
            pass

        # Memory (learned — separate store)
        try:
            if db is not None:
                from app.models import TypedMemoryRecord
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)
                q = db.query(TypedMemoryRecord)
                if project_id is not None:
                    q = q.filter(TypedMemoryRecord.project_id == project_id)
                if user_id is not None:
                    q = q.filter(TypedMemoryRecord.user_id == user_id)
                rows = (
                    q.filter(
                        (TypedMemoryRecord.expires_at == None)  # noqa: E711
                        | (TypedMemoryRecord.expires_at > now)
                    )
                    .order_by(TypedMemoryRecord.created_at.desc())
                    .limit(8)
                    .all()
                )
                for r in rows:
                    memory.append(
                        {
                            "id": f"mem-{r.id}",
                            "content": f"[{r.memory_type}] {r.title}: {r.content}"[:1500],
                            "score": 0.5,
                            "freshness": "learned",
                            "verification_state": "unverified",
                        }
                    )
        except Exception:  # noqa: BLE001
            pass

        # Related work
        try:
            if db is not None and not related:
                from app.models import WorkItem

                q = db.query(WorkItem).order_by(WorkItem.id.desc())
                if project_id is not None:
                    q = q.filter(WorkItem.project_id == project_id)
                if repository_id is not None:
                    q = q.filter(WorkItem.repository_id == repository_id)
                for w in q.limit(10).all():
                    related.append(
                        {
                            "id": w.id,
                            "title": w.title,
                            "status": w.status,
                            "source": w.source,
                            "external_id": w.external_id,
                        }
                    )
        except Exception:  # noqa: BLE001
            pass

        # Skills selection (may be empty if none)
        try:
            if db is not None:
                from app.models import SkillDefinition

                rows = db.query(SkillDefinition).limit(10).all()
                for s in rows:
                    skills.append(
                        {
                            "id": getattr(s, "id", None),
                            "name": getattr(s, "name", "") or getattr(s, "skill_key", ""),
                            "reason": "available_skill",
                        }
                    )
        except Exception:  # noqa: BLE001
            pass

        # Playbooks
        try:
            if db is not None:
                try:
                    from app.models import Playbook

                    rows = db.query(Playbook).limit(10).all()
                    for p in rows:
                        playbooks.append(
                            {
                                "id": getattr(p, "id", None),
                                "name": getattr(p, "name", ""),
                                "reason": "available_playbook",
                            }
                        )
                except Exception:  # noqa: BLE001
                    playbooks = []
        except Exception:  # noqa: BLE001
            pass

        freshness = {
            "lattice": lattice.get("status", "unknown"),
            "blueprint": blueprint.get("freshness", "unknown"),
            "knowledge": "present" if knowledge else "empty",
            "memory": "present" if memory else "empty",
            "skills": "present" if skills else "empty",
            "playbooks": "present" if playbooks else "empty",
            "related_work": "present" if related else "empty",
        }

        return ProjectIntelligenceSnapshot(
            lattice=lattice,
            blueprint=blueprint,
            knowledge=knowledge,
            memory=memory,
            related_work=related,
            skill_selection=skills,
            playbook_selection=playbooks,
            freshness=freshness,
        )
