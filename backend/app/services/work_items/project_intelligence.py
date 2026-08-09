"""ProjectIntelligenceService — P0 snapshot contract (Skills/Playbooks may be empty)."""

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
        # Knowledge and Memory must remain separate keys
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
    ) -> ProjectIntelligenceSnapshot:
        lattice: dict[str, Any] = {"status": "unavailable", "hits": []}
        blueprint: dict[str, Any] = {"snippet": "", "freshness": "unknown"}
        knowledge: list[dict[str, Any]] = []
        memory: list[dict[str, Any]] = []

        # Best-effort Lattice / Blueprint (no hard fail)
        try:
            if project_key:
                from app.services.lattice import status as lattice_status  # type: ignore

                if hasattr(lattice_status, "get_status"):
                    lattice = {"status": "ok", "detail": lattice_status.get_status(project_key)}
                else:
                    lattice = {"status": "ok", "project_key": project_key, "hits": []}
        except Exception:  # noqa: BLE001
            lattice = {"status": "unavailable", "hits": []}

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
                        "snippet": (row.summary_json if hasattr(row, "summary_json") else "")[:2000]
                        if False
                        else f"blueprint:{project_key} commit={getattr(row, 'indexed_commit_sha', '')}",
                        "freshness": getattr(row, "status", "unknown"),
                        "indexed_commit_sha": getattr(row, "indexed_commit_sha", ""),
                    }
        except Exception:  # noqa: BLE001
            pass

        try:
            if db is not None:
                from app.domains.repository import knowledge_base as kb_mod  # noqa: F401
        except Exception:  # noqa: BLE001
            pass

        freshness = {
            "lattice": lattice.get("status", "unknown"),
            "blueprint": blueprint.get("freshness", "unknown"),
            "knowledge": "empty" if not knowledge else "present",
            "memory": "empty" if not memory else "present",
            "skills": "deferred_p1",
            "playbooks": "deferred_p1",
        }

        return ProjectIntelligenceSnapshot(
            lattice=lattice,
            blueprint=blueprint,
            knowledge=knowledge,
            memory=memory,
            related_work=list(related_work or []),
            skill_selection=[],  # P1 may populate
            playbook_selection=[],  # P1 may populate
            freshness=freshness,
        )
