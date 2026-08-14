"""Experimental ZECT-native presentation provider (S4 renderer)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.planner import build_presentation_plan
from app.services.mentrix.presentation.provider import PresentationGenerateRequest, PresentationStatus
from app.services.mentrix.presentation.renderer import (
    is_fallback_template_id,
    render_plan_to_pptx,
    write_pptx,
    _safe_filename,
)
from app.services.mentrix.presentation.template_definition import load_definition, list_ready_ids, native_ready
from app.services.mentrix.presentation.template_importer import UnsafePptxError
from app.services.pptx_paths import default_pptx_save_dir


class ZectNativePresentationProvider:
    name = "zect_native"

    def status(self, *, user_id: str = "anon") -> PresentationStatus:
        zinnia_ready = native_ready("zinnia-executive-v1")
        lifecycle = tmpl.LIFECYCLE_READY if zinnia_ready else tmpl.LIFECYCLE_TEMPLATE_NOT_READY
        return PresentationStatus(
            configured=True,
            reachable=True,
            lifecycle=lifecycle,
            provider=self.name,
            hint="Native generate is experimental. Set ZECT_PRESENTATION_PROVIDER=zect_native. Presenton remains default.",
            blocked_external=False,
            zinnia_ready=zinnia_ready,
        )

    def list_engine_templates(self) -> dict[str, Any]:
        ids = list_ready_ids()
        return {
            "ok": True,
            "source": "zect_native",
            "templates": [{"id": i, "name": i} for i in ids],
            "reachable": True,
            "configured": True,
        }

    def generate(self, req: PresentationGenerateRequest) -> dict[str, Any]:
        ui = (req.ui_template_choice or req.template or "").strip()
        canon = tmpl.canonical_id(ui) or ui
        planned = build_presentation_plan(
            prompt=req.content,
            n_slides=req.n_slides,
            template_id=canon,
            audience_id=req.audience_id or "general",
            sensitivity_hint=req.sensitivity_hint or None,
            context_items=list(req.context_items or []),
        )
        if not planned.get("ok"):
            return {
                "ok": False,
                "error": planned.get("error") or "plan_failed",
                "hint": planned.get("detail") or "",
                "http_status": 403 if planned.get("block_code") == "sensitivity_blocked" else 502,
                "lifecycle": tmpl.LIFECYCLE_GENERATION_FAILED,
                "provider": self.name,
                "ui_template_choice": ui,
                "canonical_id": canon,
                "zinnia_verified": False,
                "template_sent": None,
                "blocked_external": bool(planned.get("blocked_external")),
                "block_code": planned.get("block_code") or planned.get("error") or "",
            }
        owned = canon.startswith("zinnia-") or canon.startswith("org-") or canon.startswith("user-")
        if owned and not native_ready(canon):
            return {
                "ok": False,
                "error": "template_not_ready",
                "hint": "Import a ZECT TemplateDefinition master before native generate. Never silent modern.",
                "http_status": 409,
                "lifecycle": tmpl.LIFECYCLE_TEMPLATE_NOT_READY,
                "provider": self.name,
                "ui_template_choice": ui,
                "canonical_id": canon,
                "zinnia_verified": False,
                "template_sent": None,
                "blocked_external": False,
                "block_code": "template_not_ready",
            }
        definition = load_definition(canon) if canon else None
        source = tmpl.source_pptx_path(canon, user_id=req.user_id) if canon else None
        used_master = bool(source and Path(source).is_file() and definition and definition.get("ready"))
        try:
            data = render_plan_to_pptx(
                planned["plan"],
                template_path=source if used_master else None,
                definition=definition,
            )
        except UnsafePptxError as exc:
            return {
                "ok": False,
                "error": "native_pptx_invalid",
                "detail": str(exc),
                "http_status": 502,
                "lifecycle": tmpl.LIFECYCLE_GENERATION_FAILED,
                "provider": self.name,
                "zinnia_verified": False,
                "block_code": "native_pptx_invalid",
            }
        dest_dir = default_pptx_save_dir()
        dest = dest_dir / _safe_filename(req.filename or planned["plan"].get("objective") or "zect-native-deck")
        if dest.exists():
            dest = dest_dir / _safe_filename(f"{dest.stem}-{req.user_id or 'anon'}{dest.suffix}")
        write_pptx(data, dest)
        zinnia_ui = canon.startswith("zinnia-")
        zinnia_verified = bool(zinnia_ui and used_master and not is_fallback_template_id(canon))
        if zinnia_ui and is_fallback_template_id(canon):
            zinnia_verified = False
        return {
            "ok": True,
            "path": str(dest),
            "bytes": len(data),
            "provider": self.name,
            "experimental": True,
            "ui_template_choice": ui,
            "canonical_id": canon,
            "template_sent": canon if used_master else None,
            "zinnia_verified": zinnia_verified,
            "zinnia_note": (
                f"Zinnia verified via native TemplateDefinition ({canon})"
                if zinnia_verified
                else ("Zinnia TemplateDefinition not applied" if zinnia_ui else "")
            ),
            "lifecycle": tmpl.LIFECYCLE_READY,
            "planner_source": planned["plan"].get("planner_source"),
            "n_slides": planned["plan"].get("n_slides"),
            "charts_images_tables": "partial",
            "blocked_external": False,
            "telemetry": {"provider": self.name, "opt_in": True, "used_master": used_master},
        }
