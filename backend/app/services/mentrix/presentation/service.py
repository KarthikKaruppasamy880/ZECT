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
        from app.infrastructure.observability import (
            begin_operation,
            emit_event,
            emit_privileged,
            is_cancelled,
            new_id,
        )
        import time as _time

        run_id = (req.run_id or "").strip() or new_id()
        req.run_id = run_id
        t0 = _time.perf_counter()
        begin_operation(
            run_id,
            kind="present_generate",
            extra={"provider": self.provider_name, "fast_basic": bool(req.fast_basic)},
        )
        from app.services.mentrix.presentation.sensitivity import classify_deck_material

        if self.provider_name == "presenton":
            blob = req.content or ""
            for item in req.context_items or []:
                if isinstance(item, dict):
                    blob += "\n" + str(item.get("content") or "")
            sens = classify_deck_material(blob, hint=req.sensitivity_hint or None)
            if sens.get("forbid_external_retrieval"):
                out = {
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
                    "run_id": run_id,
                }
                emit_event(
                    operation="present_generate",
                    stage="blocked",
                    run_id=run_id,
                    failure_class="restricted_external_provider",
                    duration_ms=int((_time.perf_counter() - t0) * 1000),
                    model_route=self.provider_name,
                )
                emit_privileged(
                    action="present_generate_blocked",
                    resource_type="presentation",
                    details={"block_code": "restricted_external_provider", "provider": self.provider_name},
                )
                return out
        if is_cancelled(run_id):
            out = {
                "ok": False,
                "error": "generation_cancelled",
                "http_status": 409,
                "lifecycle": "GENERATION_CANCELLED",
                "provider": self.provider_name,
                "block_code": "generation_cancelled",
                "run_id": run_id,
            }
            emit_event(
                operation="present_generate",
                stage="cancelled",
                run_id=run_id,
                failure_class="cancelled",
                duration_ms=int((_time.perf_counter() - t0) * 1000),
            )
            return out
        out = self._provider.generate(req)
        out.setdefault("provider", self.provider_name)
        out["run_id"] = run_id
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
        duration_ms = int((_time.perf_counter() - t0) * 1000)
        fail = "" if out.get("ok") else (out.get("block_code") or out.get("error") or "present_failed")
        emit_event(
            operation="present_generate",
            stage="complete" if out.get("ok") else "failed",
            run_id=run_id,
            failure_class=fail,
            duration_ms=duration_ms,
            model_route=str(out.get("provider") or self.provider_name),
            extra={
                "planner_mode": out.get("planner_mode") or "",
                "degraded": bool(out.get("degraded")),
            },
        )
        emit_privileged(
            action="present_generate",
            resource_type="presentation",
            details={
                "ok": bool(out.get("ok")),
                "block_code": fail,
                "provider": out.get("provider") or self.provider_name,
            },
        )
        return out
