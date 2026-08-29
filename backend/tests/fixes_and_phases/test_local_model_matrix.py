"""Local/cloud model support matrix tests for Mentrix closeout."""

from __future__ import annotations

from app.services.local_model_matrix import build_local_model_matrix


def test_local_model_matrix_structure():
    m = build_local_model_matrix()
    names = {s["surface"] for s in m["surfaces"]}
    assert names >= {
        "Ask",
        "Plan",
        "Companion",
        "Agent/Coding",
        "ForgeLoop",
        "Ultra Review",
        "Blueprint",
        "Embeddings",
    }
    assert m["claim_fully_local"] is False
    for s in m["surfaces"]:
        assert s["status"] in ("VERIFIED", "PARTIAL", "CLOUD_ONLY", "BLOCKED")
