"""PresentationService — selects Presenton (default) or experimental native provider."""

from __future__ import annotations

import os
from typing import Any

from app.adapters.presentation.presenton_provider import PresentonProvider
from app.services.mentrix.presentation.native_provider import ZectNativePresentationProvider
from app.services.mentrix.presentation.provider import (
    PresentationGenerateRequest,
    PresentationProvider,
    PresentationStatus,
)

DEFAULT_PROVIDER = "presenton"


def configured_provider_name() -> str:
    raw = (os.getenv("ZECT_PRESENTATION_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if raw in {"zect_native", "native"}:
        return "zect_native"
    return DEFAULT_PROVIDER


def get_provider() -> PresentationProvider:
    if configured_provider_name() == "zect_native":
        return ZectNativePresentationProvider()
    return PresentonProvider()


class PresentationService:
    def __init__(self, provider: PresentationProvider | None = None) -> None:
        self._provider = provider or get_provider()

    @property
    def provider_name(self) -> str:
        return getattr(self._provider, "name", configured_provider_name())

    def status(self, *, user_id: str = "anon") -> dict[str, Any]:
        st: PresentationStatus = self._provider.status(user_id=user_id)
        return {
            "configured": st.configured,
            "reachable": st.reachable,
            "base_url": st.base_url,
            "hint": st.hint,
            "blocked_external": st.blocked_external,
            "block_code": st.block_code,
            "lifecycle": st.lifecycle,
            "zinnia_ready": st.zinnia_ready,
            "canonical_template_id": st.canonical_template_id,
            "provider": st.provider,
        }

    def list_engine_templates(self) -> dict[str, Any]:
        return self._provider.list_engine_templates()

    def plan(self, req: PresentationGenerateRequest) -> dict[str, Any]:
        from app.services.mentrix.presentation.planner import build_presentation_plan

        ui = (req.ui_template_choice or req.template or "").strip()
        return build_presentation_plan(
            prompt=req.content,
            n_slides=req.n_slides,
            template_id=ui,
            audience_id=req.audience_id or "general",
            sensitivity_hint=req.sensitivity_hint or None,
            context_items=list(req.context_items or []),
        )

    def generate(self, req: PresentationGenerateRequest) -> dict[str, Any]:
        from app.services.mentrix.presentation.sensitivity import classify_deck_material

        if self.provider_name == "presenton":
            blob = req.content or ""
            for item in req.context_items or []:
                if isinstance(item, dict):
                    blob += "\n" + str(item.get("content") or "")
            sens = classify_deck_material(blob, hint=req.sensitivity_hint or None)
            if sens.get("forbid_external_retrieval"):
                return {
                    "ok": False,
                    "error": "restricted_external_provider",
                    "hint": "RESTRICTED/CONFIDENTIAL decks cannot be sent to an external presentation engine",
                    "http_status": 403,
                    "lifecycle": "GENERATION_FAILED",
                    "provider": self.provider_name,
                    "zinnia_verified": False,
                    "blocked_external": True,
                    "block_code": "restricted_external_provider",
                    "sensitivity": sens.get("sensitivity"),
                }
        out = self._provider.generate(req)
        out.setdefault("provider", self.provider_name)
        path = str(out.get("path") or "").strip()
        if out.get("ok") and path:
            try:
                from pathlib import Path

                from app.services.mentrix.presentation.final_pptx_inspector import (
                    inspect_and_repair_pptx,
                    merge_inspector_into_quality,
                )

                pptx = Path(path)
                if pptx.is_file():
                    data, inspector = inspect_and_repair_pptx(pptx.read_bytes())
                    pptx.write_bytes(data)
                    quality = merge_inspector_into_quality(dict(out.get("quality") or {}), inspector)
                    out["quality"] = quality
                    out["inspector"] = inspector
                    out["overlap_count"] = quality.get("overlap_count")
                    out["final_quality_status"] = quality.get("final_quality_status") or inspector.get("status")
                    out["export_blocked"] = bool(quality.get("layout_hard_fail") or inspector.get("status") == "FAIL")
                    out["bytes"] = len(data)
            except Exception as exc:  # noqa: BLE001 — inspector must not 500 generate
                out.setdefault("inspector_error", str(exc)[:200])
        return out
