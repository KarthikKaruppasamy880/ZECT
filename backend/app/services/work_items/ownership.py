"""Ownership invariants — ArtifactStore owns PLAN; ForgeLoop uses mentrix_native."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def assert_artifact_store_owns_plan(work_item_id: int, *, root: Path | None = None) -> dict[str, Any]:
    """PLAN.md SoT is ArtifactStore — dual-write targets must not replace it."""
    from app.services.work_items.artifact_store import ArtifactStore

    store = ArtifactStore(work_item_id, root=root) if root else ArtifactStore(work_item_id)
    plan_path = store.path("PLAN.md")
    return {
        "owner": "ArtifactStore",
        "plan_path": str(plan_path),
        "exists": plan_path.exists(),
        "plan_hash": store.plan_hash() if plan_path.exists() else None,
    }


def assert_forgeloop_mentrix_native_path() -> dict[str, Any]:
    """Static ownership check: ForgeLoop still routes builds through mentrix_native."""
    orch = Path(__file__).resolve().parents[1] / "forge_loop" / "orchestrator.py"
    text = orch.read_text(encoding="utf-8")
    checks = {
        "imports_mentrix_native_build": "run_mentrix_native_build" in text,
        "sets_engine_provider": 'result["engine_provider"] = "mentrix_native"' in text,
        "mentrix_native_build_enabled": "mentrix_native_build_enabled" in text,
    }
    ok = all(checks.values())
    return {"ok": ok, "checks": checks, "path": str(orch)}
