"""MentrixContextEngine — bounded ContextPack with full provenance.

Lattice / Graphify hits are evidence for PLAN and impact analysis only.
Graph evidence never grants edit, git write, or coding-agent permission.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


PROVENANCE_KEYS = (
    "source_type",
    "source_id",
    "repository",
    "commit_sha",
    "retrieval_score",
    "freshness",
    "verification_state",
    "token_count",
    "selection_reason",
)


@dataclass
class ProvenanceItem:
    source_type: str
    source_id: str
    content: str
    repository: str = ""
    commit_sha: str = ""
    retrieval_score: float = 0.0
    freshness: str = "unknown"
    verification_state: str = "unverified"
    token_count: int = 0
    selection_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # ensure all provenance keys present
        for k in PROVENANCE_KEYS:
            d.setdefault(k, "" if k not in ("retrieval_score", "token_count") else 0)
        return d


@dataclass
class ContextPack:
    work_item_id: int | None = None
    repository_id: int | None = None
    repository_ref: str = ""
    base_commit_sha: str = ""
    items: list[ProvenanceItem] = field(default_factory=list)
    token_budget: int = 8000
    token_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_item_id": self.work_item_id,
            "repository_id": self.repository_id,
            "repository_ref": self.repository_ref,
            "base_commit_sha": self.base_commit_sha,
            "token_budget": self.token_budget,
            "token_used": self.token_used,
            "items": [i.to_dict() for i in self.items],
        }

    def text_blob(self, *, max_chars: int = 12000) -> str:
        parts: list[str] = []
        for it in self.items:
            parts.append(f"[{it.source_type}:{it.source_id}] {it.content}")
        blob = "\n\n".join(parts)
        return blob[:max_chars]


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


class MentrixContextEngine:
    """Build bounded ContextPack with provenance on every item."""

    def __init__(self, *, token_budget: int = 8000) -> None:
        self.token_budget = token_budget

    def build(
        self,
        *,
        work_item_id: int | None = None,
        repository_id: int | None = None,
        repository_ref: str = "",
        base_commit_sha: str = "",
        goal: str = "",
        knowledge_hits: list[dict[str, Any]] | None = None,
        memory_hits: list[dict[str, Any]] | None = None,
        lattice_hits: list[dict[str, Any]] | None = None,
        blueprint_snippet: str = "",
        extra_items: list[ProvenanceItem] | None = None,
    ) -> ContextPack:
        pack = ContextPack(
            work_item_id=work_item_id,
            repository_id=repository_id,
            repository_ref=repository_ref or "",
            base_commit_sha=base_commit_sha or "",
            token_budget=self.token_budget,
        )
        used = 0

        def _add(item: ProvenanceItem) -> None:
            nonlocal used
            tc = item.token_count or _estimate_tokens(item.content)
            item.token_count = tc
            if used + tc > self.token_budget:
                return
            pack.items.append(item)
            used += tc

        if goal:
            _add(
                ProvenanceItem(
                    source_type="goal",
                    source_id="user_goal",
                    content=goal[:2000],
                    repository=str(repository_id or ""),
                    commit_sha=base_commit_sha or "",
                    selection_reason="primary_goal",
                    verification_state="user_provided",
                    freshness="current",
                )
            )

        if blueprint_snippet:
            _add(
                ProvenanceItem(
                    source_type="blueprint",
                    source_id="structural",
                    content=blueprint_snippet[:4000],
                    repository=str(repository_id or ""),
                    commit_sha=base_commit_sha or "",
                    selection_reason="project_intelligence",
                    freshness="indexed",
                )
            )

        for i, hit in enumerate(knowledge_hits or []):
            content = str(hit.get("content") or hit.get("text") or "")[:2000]
            if not content:
                continue
            _add(
                ProvenanceItem(
                    source_type="knowledge",
                    source_id=str(hit.get("id") or f"kb-{i}"),
                    content=content,
                    repository=str(hit.get("repository") or repository_id or ""),
                    commit_sha=str(hit.get("commit_sha") or base_commit_sha or ""),
                    retrieval_score=float(hit.get("score") or 0.0),
                    freshness=str(hit.get("freshness") or "unknown"),
                    verification_state=str(hit.get("verification_state") or "curated"),
                    selection_reason="knowledge_retrieve",
                )
            )

        for i, hit in enumerate(memory_hits or []):
            content = str(hit.get("content") or hit.get("text") or "")[:1500]
            if not content:
                continue
            _add(
                ProvenanceItem(
                    source_type="memory",
                    source_id=str(hit.get("id") or f"mem-{i}"),
                    content=content,
                    repository=str(hit.get("repository") or repository_id or ""),
                    commit_sha=str(hit.get("commit_sha") or ""),
                    retrieval_score=float(hit.get("score") or 0.0),
                    freshness=str(hit.get("freshness") or "learned"),
                    verification_state=str(hit.get("verification_state") or "unverified"),
                    selection_reason="memory_retrieve",
                )
            )

        for i, hit in enumerate(lattice_hits or []):
            content = str(hit.get("content") or hit.get("text") or hit.get("summary") or "")[:1500]
            if not content:
                continue
            _add(
                ProvenanceItem(
                    source_type="lattice",
                    source_id=str(hit.get("id") or f"lat-{i}"),
                    content=content,
                    repository=str(hit.get("repository") or repository_id or ""),
                    commit_sha=str(hit.get("commit_sha") or base_commit_sha or ""),
                    retrieval_score=float(hit.get("score") or 0.0),
                    freshness=str(hit.get("freshness") or "indexed"),
                    verification_state=str(hit.get("verification_state") or "structural"),
                    selection_reason="lattice_query",
                )
            )

        for item in extra_items or []:
            # Never inject stale/replaced document/web versions into ContextPack.
            if str(getattr(item, "freshness", "") or "").lower() == "stale":
                continue
            if getattr(item, "source_type", "") in ("document", "web") and str(
                getattr(item, "freshness", "") or ""
            ).lower() not in ("current",):
                continue
            _add(item)

        pack.token_used = used
        return pack
