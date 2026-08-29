"""Compose skills / memory / Lattice / Blueprint context for Mentrix Coding Agent."""

from __future__ import annotations

from typing import Any


def compose_context_pack(
    *,
    goal: str,
    project_id: int | None = None,
    skill_id: int | None = None,
    project_key: str | None = None,
    db: Any = None,
    max_chars: int = 3500,
) -> dict[str, Any]:
    """Token-capped ContextPack. Graphify is ingest-only; retrieve via Lattice."""
    bits: list[str] = []
    meta: dict[str, Any] = {
        "knowledge": False,
        "lattice_hits": 0,
        "lattice_indexed": False,
        "blueprint": False,
        "project_key": (project_key or "").strip() or None,
    }
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
                    meta["knowledge"] = True
            except Exception:  # noqa: BLE001
                pass

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
                    meta["project_key"] = pk
                    hits = hybrid_retrieve(db, goal[:400], project_key=pk, top_k=4) if pk else []
                    lines = []
                    for h in hits or []:
                        path = h.get("path") or h.get("file_path") or h.get("source") or ""
                        snippet = (h.get("content") or h.get("text") or "")[:280]
                        if snippet:
                            lines.append(f"- {path}: {snippet}")
                    meta["lattice_hits"] = len(lines)
                    meta["lattice_indexed"] = bool(pk) and bool(hits is not None)
                    if lines:
                        bits.append("Lattice facts:\n" + "\n".join(lines)[:900])
            except Exception:  # noqa: BLE001
                pass

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
                    meta["blueprint"] = True
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
        text = text[: max_chars - 20] + "\n…(truncated)"
    meta["text"] = text
    return meta


_ASK_STOP = frozenset(
    {
        "what", "which", "where", "when", "this", "that", "with", "from",
        "file", "files", "does", "define", "defines", "token",
    }
)
_SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}


def _workspace_grep_items(workspace: Any, goal: str, *, repository_id: str = "") -> list[Any]:
    """Same authorized-local-grep the Ask/Plan pipeline uses
    (developer_service.py's _workspace_file_items), adapted for the Agent
    path's already-resolved filesystem workspace Path instead of a DB Repo
    row's local_path -- the caller (coding_engine_mentrix.start_run) has
    already validated/jailed `workspace` via resolve_workspace(), so this
    does not re-check path_under_allowed_roots."""
    import os
    import re
    from pathlib import Path

    from app.services.work_items.context_engine import ProvenanceItem

    root = Path(workspace)
    if not root.is_dir():
        return []
    tokens = [t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", goal or "") if t.lower() not in _ASK_STOP]
    tokens = sorted(set(tokens), key=len, reverse=True)[:5]
    if not tokens:
        return []
    regexes = [re.compile(re.escape(t), re.IGNORECASE) for t in tokens]
    items: list[Any] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            fpath = Path(dirpath) / name
            try:
                if fpath.stat().st_size > 400_000:
                    continue
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = str(fpath.relative_to(root)).replace("\\", "/")
            for i, line in enumerate(text.splitlines(), 1):
                if any(rx.search(line) for rx in regexes):
                    items.append(
                        ProvenanceItem(
                            source_type="workspace_file",
                            source_id=f"{rel}:{i}",
                            content=f"{rel}:{i}: {line.strip()[:240]}",
                            repository=repository_id,
                            freshness="current",
                            verification_state="file_search",
                            selection_reason="authorized_local_grep",
                            retrieval_score=1.0,
                        )
                    )
                    if len(items) >= 12:
                        return items
                    break
    return items


def compose_rich_agent_context_pack(
    *,
    goal: str,
    workspace: str = "",
    project_id: int | None = None,
    project_key: str | None = None,
    repository_id: str | int | None = None,
    work_item_id: int | None = None,
    db: Any = None,
    max_chars: int = 6000,
) -> dict[str, Any]:
    """The SAME provenance-aware Project Intelligence pipeline Ask/Plan use
    (ProjectIntelligenceService + MentrixContextEngine) -- not the thinner,
    independently-implemented compose_coding_agent_context below -- so the
    Coder/Tester/Debugger roles see the same Lattice/knowledge/blueprint
    context a human already reviewed via Ask/Plan for this repository, not
    a separately-assembled approximation of it. See
    ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phases C and D.

    Same shape as compose_context_pack() (knowledge/lattice_hits/
    lattice_indexed/blueprint/text) so a Mission's "Context Used" can be
    rendered with the exact same component Ask/Plan already use, not a
    second display concept -- see mentrix_lead.py / coding_engine_mentrix.py
    callers, which persist this dict on the run/mission for that purpose.

    Returns an empty-but-well-shaped dict (never raises) if Project
    Intelligence is unavailable -- callers fall back to
    compose_coding_agent_context, so a build is never blocked on this.
    """
    meta: dict[str, Any] = {
        "knowledge": False,
        "lattice_hits": 0,
        "lattice_indexed": False,
        "blueprint": False,
        "project_key": (project_key or "").strip() or None,
        "text": "",
    }
    own_session = False
    if db is None:
        try:
            from app.infrastructure.database import SessionLocal

            db = SessionLocal()
            own_session = True
        except Exception:  # noqa: BLE001
            return meta
    try:
        from app.services.work_items.context_engine import MentrixContextEngine
        from app.services.work_items.project_intelligence import ProjectIntelligenceService

        rid: int | None = None
        if repository_id is not None:
            try:
                rid = int(repository_id)
            except (TypeError, ValueError):
                rid = None

        snap = ProjectIntelligenceService().snapshot(
            project_id=project_id,
            project_key=project_key or "",
            repository_id=rid,
            db=db,
            query=goal,
        )
        file_items = _workspace_grep_items(workspace, goal, repository_id=str(rid or "")) if workspace else []
        pack = MentrixContextEngine().build(
            work_item_id=work_item_id,
            repository_id=rid,
            goal=goal,
            knowledge_hits=snap.knowledge,
            memory_hits=snap.memory,
            lattice_hits=list((snap.lattice or {}).get("hits") or []),
            blueprint_snippet=str((snap.blueprint or {}).get("snippet") or ""),
            extra_items=file_items,
        )
        text = pack.text_blob()
        if len(text) > max_chars:
            text = text[: max_chars - 20] + "\n…(truncated)"
        lattice_hits = list((snap.lattice or {}).get("hits") or [])
        meta.update(
            {
                "knowledge": bool(snap.knowledge),
                "lattice_hits": len(lattice_hits),
                "lattice_indexed": str((snap.lattice or {}).get("status") or "") == "READY",
                "blueprint": bool((snap.blueprint or {}).get("snippet")),
                "text": text,
            }
        )
        return meta
    except Exception:  # noqa: BLE001
        return meta
    finally:
        if own_session:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass


def compose_rich_agent_context(**kwargs: Any) -> str:
    """Text-only view of compose_rich_agent_context_pack(), for callers that
    only need the prompt text (see coding_engine_mentrix.py's start_run)."""
    return str(compose_rich_agent_context_pack(**kwargs).get("text") or "")


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
    pack = compose_context_pack(
        goal=goal,
        project_id=project_id,
        skill_id=skill_id,
        project_key=project_key,
        db=db,
        max_chars=max_chars,
    )
    return str(pack.get("text") or "")
