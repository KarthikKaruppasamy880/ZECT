"""Compose skills / memory / Lattice / Blueprint context for Mentrix Coding Agent."""

from __future__ import annotations

from typing import Any


def compose_coding_agent_context(
    *,
    goal: str,
    project_id: int | None = None,
    skill_id: int | None = None,
    project_key: str | None = None,
    db: Any = None,
    max_chars: int = 3500,
) -> str:
    """Return extra system-context text (may be empty). Safe if DB/services missing."""
    bits: list[str] = []
    own_session = False
    if db is None:
        try:
            from app.infrastructure.database import SessionLocal

            db = SessionLocal()
            own_session = True
        except Exception:  # noqa: BLE001
            db = None

    try:
        if db is not None:
            try:
                from app.services.mentrix.companion import build_agent_context

                ctx = build_agent_context(
                    db,
                    skill_id=skill_id,
                    project_id=project_id,
                    query=goal or "",
                )
                if (ctx or "").strip():
                    bits.append(ctx.strip()[:2200])
            except Exception:  # noqa: BLE001
                pass

            # Lattice hybrid retrieve (token-capped)
            try:
                from app.services.rag.retriever import hybrid_retrieve

                pk = (project_key or "").strip() or None
                if pk or project_id is not None:
                    if not pk and project_id is not None:
                        try:
                            from app.models import Project

                            proj = db.query(Project).filter(Project.id == int(project_id)).first()
                            pk = (getattr(proj, "key", None) or getattr(proj, "slug", None) or "") or None
                        except Exception:  # noqa: BLE001
                            pk = None
                    hits = hybrid_retrieve(db, goal[:400], project_key=pk, top_k=4) if pk else []
                    lines = []
                    for h in hits or []:
                        path = h.get("path") or h.get("file_path") or h.get("source") or ""
                        snippet = (h.get("content") or h.get("text") or "")[:280]
                        if snippet:
                            lines.append(f"- {path}: {snippet}")
                    if lines:
                        bits.append("Lattice facts:\n" + "\n".join(lines)[:900])
            except Exception:  # noqa: BLE001
                pass

            # Latest blueprint text if available
            try:
                from app.models import GeneratedOutput

                q = db.query(GeneratedOutput).filter(
                    GeneratedOutput.output_type.in_(("blueprint", "code")),
                    GeneratedOutput.feature.in_(("blueprint", "enhance_blueprint", "blueprint_phase")),
                )
                row = q.order_by(GeneratedOutput.id.desc()).first()
                body = ""
                if row is not None:
                    body = (getattr(row, "output_content", None) or "")[:800]
                if body.strip():
                    bits.append("Blueprint (target architecture):\n" + body.strip())
            except Exception:  # noqa: BLE001
                pass
    finally:
        if own_session and db is not None:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass

    text = "\n\n".join(bits).strip()
    if len(text) > max_chars:
        return text[: max_chars - 20] + "\n…(truncated)"
    return text
