"""System Health aggregation — Operations surface (P2)."""

from __future__ import annotations

import os
from typing import Any


def build_system_health(db: Any = None) -> dict[str, Any]:
    """Fail-soft readiness snapshot; never returns secrets."""
    components: list[dict[str, Any]] = []

    components.append({"id": "api", "name": "API", "status": "ok", "detail": "healthz"})

    auth_mode = (os.getenv("ZECT_AUTH_MODE") or "local").strip()
    components.append(
        {
            "id": "auth",
            "name": "Auth",
            "status": "ok" if auth_mode else "degraded",
            "detail": f"mode={auth_mode}",
        }
    )

    coding = (os.getenv("ZECT_CODING_ENGINE") or "mentrix_native").strip()
    components.append(
        {
            "id": "coding_engine",
            "name": "Coding Agent",
            "status": "ok",
            "detail": f"engine={coding}",
        }
    )

    try:
        from app.adapters.llm.openai_compat import (
            mentrix_local_llm_configured,
            openai_compat_available,
            mentrix_llm_chat_model,
        )

        local_ok = mentrix_local_llm_configured()
        cloud_ok = openai_compat_available()
        components.append(
            {
                "id": "model_gateway",
                "name": "Model Gateway",
                "status": "ok" if (local_ok or cloud_ok) else "degraded",
                "detail": {
                    "local": local_ok,
                    "cloud": cloud_ok,
                    "model": mentrix_llm_chat_model(),
                },
            }
        )
    except Exception as exc:  # noqa: BLE001
        components.append(
            {"id": "model_gateway", "name": "Model Gateway", "status": "unknown", "detail": str(exc)[:200]}
        )

    jira = bool((os.getenv("JIRA_BASE_URL") or os.getenv("JIRA_URL") or "").strip())
    components.append(
        {
            "id": "jira",
            "name": "Jira adapter",
            "status": "ok" if jira else "not_configured",
            "detail": "configured" if jira else "set JIRA_* for live ingest",
        }
    )

    camunda = bool((os.getenv("ZECT_CAMUNDA_BASE_URL") or os.getenv("CAMUNDA_BASE_URL") or "").strip())
    components.append(
        {
            "id": "camunda",
            "name": "Camunda / Mentrix Process",
            "status": "ok" if camunda else "not_configured",
            "detail": "configured" if camunda else "set ZECT_CAMUNDA_BASE_URL for live ingest",
        }
    )

    lattice_on = (os.getenv("LATTICE_ENABLED") or "true").strip().lower() in ("1", "true", "yes", "on")
    components.append(
        {
            "id": "lattice",
            "name": "Lattice",
            "status": "ok" if lattice_on else "disabled",
            "detail": f"LATTICE_ENABLED={lattice_on}",
        }
    )

    wi_count = None
    if db is not None:
        try:
            from app.models import WorkItem

            wi_count = db.query(WorkItem).count()
        except Exception:  # noqa: BLE001
            wi_count = None
    components.append(
        {
            "id": "work_items",
            "name": "WorkItems",
            "status": "ok",
            "detail": {"count": wi_count},
        }
    )

    try:
        from app.services.desktop_readiness import build_desktop_readiness

        desk = build_desktop_readiness()
        components.append(
            {
                "id": "desktop",
                "name": "Desktop / Computer Mode",
                "status": "ok" if desk.get("electron_main_present") else "degraded",
                "detail": {
                    "electron": desk.get("electron_main_present"),
                    "computer": desk.get("computer_module_present"),
                    "bridge_queue": desk.get("bridge_queue_present"),
                },
            }
        )
    except Exception as exc:  # noqa: BLE001
        components.append(
            {"id": "desktop", "name": "Desktop / Computer Mode", "status": "unknown", "detail": str(exc)[:200]}
        )

    try:
        from app.services.skills_fs import list_filesystem_skills

        fs_n = len(list_filesystem_skills(limit=20))
        components.append(
            {
                "id": "skills_fs",
                "name": "Skills filesystem",
                "status": "ok" if fs_n else "not_configured",
                "detail": {"pack_count": fs_n},
            }
        )
    except Exception as exc:  # noqa: BLE001
        components.append(
            {"id": "skills_fs", "name": "Skills filesystem", "status": "unknown", "detail": str(exc)[:200]}
        )

    worst = "ok"
    for c in components:
        st = c.get("status")
        if st in ("error", "failed"):
            worst = "error"
            break
        if st in ("degraded", "not_configured", "disabled", "unknown") and worst == "ok":
            worst = "degraded"

    return {
        "status": worst,
        "product": "ZECT",
        "agent": "Mentrix",
        "components": components,
    }
