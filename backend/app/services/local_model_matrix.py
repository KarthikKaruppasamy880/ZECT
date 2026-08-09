"""Local/cloud model support matrix for Mentrix closeout (no secrets)."""

from __future__ import annotations

import os
from typing import Any


def _local_gateway() -> bool:
    try:
        from app.adapters.llm.openai_compat import mentrix_local_llm_configured

        return bool(mentrix_local_llm_configured())
    except Exception:  # noqa: BLE001
        return bool((os.getenv("ZECT_LLM_BASE_URL") or "").strip())


def _cloud_openai() -> bool:
    return bool((os.getenv("OPENAI_API_KEY") or "").strip())


def _anthropic() -> bool:
    return bool((os.getenv("ANTHROPIC_API_KEY") or "").strip())


def build_local_model_matrix() -> dict[str, Any]:
    """Classify each Mentrix surface: VERIFIED | PARTIAL | CLOUD_ONLY | BLOCKED.

    VERIFIED = local gateway configured AND code path uses openai_compat with policy.
    PARTIAL = code supports local but untested live OR policy gap.
    CLOUD_ONLY = implementation hard-requires cloud API.
    BLOCKED = cannot run without missing credentials for its only path.
    """
    local = _local_gateway()
    cloud = _cloud_openai()
    anthropic = _anthropic()
    policy = (os.getenv("ZECT_MODEL_FALLBACK_POLICY") or "never").strip().lower()

    def status_for(*, supports_local: bool, cloud_only: bool, live_local: bool) -> str:
        if cloud_only:
            return "CLOUD_ONLY" if cloud or anthropic else "BLOCKED"
        if supports_local and live_local:
            return "VERIFIED"
        if supports_local and not live_local:
            return "PARTIAL" if cloud else "BLOCKED"
        return "BLOCKED"

    rows = [
        {
            "surface": "Ask",
            "path": "developer_service.ask → llm_phase → openai_compat",
            "status": status_for(supports_local=True, cloud_only=False, live_local=local),
            "notes": f"fallback_policy={policy}",
        },
        {
            "surface": "Plan",
            "path": "developer_service.plan → llm_phase → openai_compat",
            "status": status_for(supports_local=True, cloud_only=False, live_local=local),
            "notes": f"fallback_policy={policy}",
        },
        {
            "surface": "Companion",
            "path": "companion.py → openai_compat",
            "status": "PARTIAL" if (local or cloud) else "BLOCKED",
            "notes": "Uses gateway but does not enforce resolve_model_route / fallback_policy",
        },
        {
            "surface": "Agent/Coding",
            "path": "coding_engine_mentrix → openai_compat; ForgeLoop mentrix_native",
            "status": status_for(supports_local=True, cloud_only=False, live_local=local),
            "notes": "Deterministic smoke path available; policy gate uneven vs llm_phase",
        },
        {
            "surface": "ForgeLoop",
            "path": "Ask/Plan via llm_phase; Build via Anthropic/OpenAI or mentrix_native",
            "status": "PARTIAL" if (local or cloud or anthropic) else "BLOCKED",
            "notes": "Ask/Plan local-capable; Build often cloud unless mentrix_native",
        },
        {
            "surface": "Ultra Review",
            "path": "review_service.py (gpt-4o-mini / OPENAI_API_KEY); lanes merge offline",
            "status": "CLOUD_ONLY" if cloud else "PARTIAL",
            "notes": "LLM review CLOUD_ONLY when key present; three-lane merger does not call LLM; offline heuristics if no key",
        },
        {
            "surface": "Blueprint",
            "path": "llm_phase.run_enhance_blueprint → openai_compat",
            "status": status_for(supports_local=True, cloud_only=False, live_local=local),
            "notes": f"fallback_policy={policy}",
        },
        {
            "surface": "Embeddings",
            "path": "build_intel/embeddings.py → OpenAI embeddings",
            "status": "CLOUD_ONLY" if cloud else "BLOCKED",
            "notes": "No local embedding gateway in product path",
        },
    ]

    return {
        "local_gateway_configured": local,
        "cloud_openai_configured": cloud,
        "anthropic_configured": anthropic,
        "fallback_policy": policy,
        "claim_fully_local": False,
        "surfaces": rows,
    }
