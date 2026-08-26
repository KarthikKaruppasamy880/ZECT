"""Learning Studio — catalog/lesson/quiz grounded in indexed Lattice + Knowledge Base content.

Distinct from the ZECT Learning coding-tutor system (learning.py) — this is
a retrieval + presentation layer over content already indexed for this
project, not a programming curriculum. Never fabricates content: every
catalog/lesson/quiz item carries source_refs into a real Lattice node or
Knowledge Base entry, and lesson/quiz generation is hard-gated on the
Lattice index being READY (see ZECT_LEARNING_STUDIO_EXECUTION_PLAN.md).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.database import get_db
from app.models import KnowledgeEntry
from app.services.lattice.indexer import explain, get_lattice_status, query_graph

router = APIRouter(prefix="/api/learning-studio", tags=["learning-studio"])


def _topic_id(kind: str, ref: str) -> str:
    return f"{kind}:{ref}"


@router.get("/status")
def studio_status(
    project_key: str = "",
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    return get_lattice_status(project_key)


@router.get("/catalog")
def get_catalog(
    project_key: str = "",
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    status = get_lattice_status(project_key)
    topics: list[dict[str, Any]] = []
    if status.get("state") != "READY":
        # Never invent a syllabus when the index isn't ready — the caller
        # must show a re-index prompt instead of catalog content.
        return {"status": status, "topics": topics}

    for node in query_graph(project_key, "", limit=200, kinds=["module", "class"]):
        topics.append({
            "topic_id": _topic_id("lattice", node["id"]),
            "title": node.get("title") or node.get("name") or node.get("path"),
            "kind": node.get("kind", "module"),
            "source_refs": [{
                "type": "lattice",
                "id": node["id"],
                "path": node.get("path"),
                "title": node.get("name"),
            }],
        })

    entries = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.is_active == True)  # noqa: E712
        .order_by(KnowledgeEntry.updated_at.desc())
        .limit(100)
        .all()
    )
    for e in entries:
        topics.append({
            "topic_id": _topic_id("knowledge", str(e.id)),
            "title": e.title,
            "kind": "knowledge",
            "source_refs": [{"type": "knowledge", "id": str(e.id), "title": e.title}],
        })

    return {"status": status, "topics": topics}


@router.get("/lesson/{topic_id}")
def get_lesson(
    topic_id: str,
    project_key: str = "",
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    status = get_lattice_status(project_key)
    if status.get("state") != "READY":
        raise HTTPException(status_code=409, detail={"reason": "not_ready", "status": status})

    kind, _, ref = topic_id.partition(":")
    if kind == "lattice":
        result = explain(project_key, node_ref=ref)
        return {
            "topic_id": topic_id,
            "body": result.get("summary", ""),
            "neighbors": result.get("neighbors", {}),
            "source_refs": [{"type": "lattice", "id": ref}],
        }
    if kind == "knowledge":
        try:
            entry_id = int(ref)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid knowledge topic id") from None
        entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
        if not entry or not entry.is_active:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")
        return {
            "topic_id": topic_id,
            "body": entry.content,
            "source_refs": [{"type": "knowledge", "id": str(entry.id), "title": entry.title}],
        }
    raise HTTPException(status_code=400, detail=f"Unknown topic kind: {kind}")


@router.post("/quiz/{topic_id}/generate")
def generate_quiz(
    topic_id: str,
    project_key: str = "",
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    lesson = get_lesson(topic_id, project_key=project_key, db=db, current_user=current_user)
    body = (lesson.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=422, detail="Lesson has no grounded content to quiz from")

    # Deterministic, content-derived questions only — every question cites
    # the same source_ref the lesson itself was built from. No LLM call, no
    # possibility of an ungrounded claim.
    source_ref = lesson["source_refs"][0]
    topic_ref = topic_id.split(":", 1)[-1]
    questions: list[dict[str, Any]] = []
    for n in (lesson.get("neighbors") or {}).get("nodes", [])[:3]:
        name = n.get("name")
        if not name:
            continue
        questions.append({
            "question": f"What is {name}'s relationship to {topic_ref}?",
            "answer": name,
            "source_ref": source_ref,
        })
    if not questions:
        questions.append({
            "question": f"Summarize the indexed content behind topic '{topic_id}'.",
            "answer": body[:280],
            "source_ref": source_ref,
        })
    return {"topic_id": topic_id, "questions": questions}
