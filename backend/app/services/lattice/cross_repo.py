"""Evidence-backed cross-repo Graphify edges. Never connect from name similarity."""

from __future__ import annotations

from typing import Any

ALLOWED_EDGE_TYPES = frozenset(
    {
        "package_dependency",
        "api_contract",
        "import",
        "schema",
        "test_fixture",
        "configured",
    }
)


class CrossRepoEdgeError(ValueError):
    pass


def make_cross_repo_edge(
    *,
    source_repo: str,
    source_sha: str,
    target_repo: str,
    target_sha: str,
    edge_type: str,
    evidence: str,
    confidence: float = 0.7,
) -> dict[str, Any]:
    src = (source_repo or "").strip()
    dst = (target_repo or "").strip()
    ev = (evidence or "").strip()
    kind = (edge_type or "").strip()
    if not src or not dst:
        raise CrossRepoEdgeError("source_repo and target_repo are required")
    if src.lower() == dst.lower():
        raise CrossRepoEdgeError("cross-repo edge requires distinct repos")
    if not ev:
        raise CrossRepoEdgeError("evidence is required")
    if ev.lower() in {"name", "name_similarity", "similar_name", "same_name"}:
        raise CrossRepoEdgeError("never connect repos from name similarity")
    if kind not in ALLOWED_EDGE_TYPES:
        raise CrossRepoEdgeError(f"unsupported edge type: {kind}")
    src_sha = (source_sha or "").strip()
    dst_sha = (target_sha or "").strip()
    if not src_sha or not dst_sha:
        raise CrossRepoEdgeError("source_sha and target_sha are required")
    conf = float(confidence)
    if conf < 0 or conf > 1:
        raise CrossRepoEdgeError("confidence must be 0..1")
    return {
        "source_repo": src,
        "source_sha": src_sha,
        "target_repo": dst,
        "target_sha": dst_sha,
        "type": kind,
        "evidence": ev,
        "confidence": conf,
    }
