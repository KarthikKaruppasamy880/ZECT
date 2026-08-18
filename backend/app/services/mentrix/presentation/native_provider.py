"""Experimental ZECT-native presentation provider (S4 renderer)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.blocks import ensure_visual_blocks, visual_inventory
from app.services.mentrix.presentation.document import document_from_plan
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


def _unique_pptx_path(dest_dir: Path, name: str) -> Path:
    dest = dest_dir / _safe_filename(name)
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    for n in range(1, 1000):
        candidate = dest_dir / _safe_filename(f"{stem}-{n}{suffix}")
        if not candidate.exists():
            return candidate
    raise UnsafePptxError("pptx_dest_collision")


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
        import time

        t0 = time.perf_counter()
        if req.run_id:
            from app.infrastructure.observability import is_cancelled

            if is_cancelled(req.run_id):
                return {
                    "ok": False,
                    "error": "generation_cancelled",
                    "http_status": 409,
                    "lifecycle": "GENERATION_CANCELLED",
                    "provider": self.name,
                    "block_code": "generation_cancelled",
                    "run_id": req.run_id,
                }
        planned = build_presentation_plan(
            prompt=req.content,
            n_slides=req.n_slides,
            template_id=canon,
            audience_id=req.audience_id or "general",
            sensitivity_hint=req.sensitivity_hint or None,
            context_items=list(req.context_items or []),
            require_llm=bool(req.require_llm) and not bool(req.fast_basic),
            asset_ids=list(req.asset_ids or []),
            fast_basic=bool(req.fast_basic),
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
                "planner_mode": planned.get("planner_mode") or "",
                "fallback": bool(planned.get("fallback")),
                "fallback_reason": planned.get("fallback_reason") or planned.get("detail") or "",
                "degraded": bool(planned.get("degraded")),
                "model": planned.get("model") or "",
                "latency": planned.get("latency") or {},
            }
        definition = load_definition(canon) if canon else None
        source = tmpl.source_pptx_path(canon, user_id=req.user_id) if canon else None
        used_master = bool(source and Path(source).is_file() and definition and definition.get("ready"))
        plan = planned["plan"]
        asset_ids = [str(a).strip() for a in list(req.asset_ids or []) if str(a).strip()]
        for slide in list(plan.get("slides") or []):
            ensure_visual_blocks(slide, asset_ids=asset_ids)
        from app.services.mentrix.presentation.quality_repair import repair_until_pass

        degraded = bool(planned.get("degraded"))
        if req.run_id:
            from app.infrastructure.observability import is_cancelled

            if is_cancelled(req.run_id):
                return {
                    "ok": False,
                    "error": "generation_cancelled",
                    "http_status": 409,
                    "lifecycle": "GENERATION_CANCELLED",
                    "provider": self.name,
                    "block_code": "generation_cancelled",
                    "run_id": req.run_id,
                    "planner_mode": planned.get("planner_mode") or "",
                }
        plan, quality = repair_until_pass(
            plan,
            definition,
            prompt=req.content,
            context_items=list(req.context_items or []),
            degraded=degraded,
        )
        # Always render a reviewable PPTX. Critic FAIL is reported on the deck;
        # inspector collisions/clipping/broken rels are hard *export* blockers.
        try:
            t_render = time.perf_counter()
            data = render_plan_to_pptx(
                plan,
                template_path=source if used_master else None,
                definition=definition,
                user_id=req.user_id or "anon",
            )
            render_ms = int((time.perf_counter() - t_render) * 1000)
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
        except Exception as exc:  # noqa: BLE001 — python-pptx / OS failures must not 500 the API
            return {
                "ok": False,
                "error": "native_render_failed",
                "detail": str(exc)[:200],
                "http_status": 502,
                "lifecycle": tmpl.LIFECYCLE_GENERATION_FAILED,
                "provider": self.name,
                "zinnia_verified": False,
                "block_code": "native_render_failed",
            }
        from app.services.mentrix.presentation.final_pptx_inspector import (
            inspect_and_repair_pptx,
            merge_inspector_into_quality,
        )

        data, inspector = inspect_and_repair_pptx(data, definition=definition)
        quality = merge_inspector_into_quality(quality, inspector)
        layout_hard = bool(quality.get("layout_hard_fail"))
        export_blocked = bool(layout_hard or inspector.get("status") == "FAIL")
        dest_dir = default_pptx_save_dir()
        dest = _unique_pptx_path(
            dest_dir,
            req.filename or planned["plan"].get("objective") or "zect-native-deck",
        )
        write_pptx(data, dest)
        try:
            from app.services.pptx_paths import notes_sidecar_for_pptx, write_notes_sidecar

            doc = document_from_plan(plan, path=str(dest), provider=self.name)
            write_notes_sidecar(notes_sidecar_for_pptx(dest), json.dumps(doc, indent=2))
        except (PermissionError, OSError, ValueError, TypeError):
            pass
        inventory = visual_inventory(plan)
        visual_status = (
            "present"
            if inventory.get("chart") and inventory.get("image") and inventory.get("table")
            else "partial"
        )
        zinnia_ui = canon.startswith("zinnia-")
        zinnia_verified = bool(zinnia_ui and used_master and not is_fallback_template_id(canon))
        if zinnia_ui and is_fallback_template_id(canon):
            zinnia_verified = False
        latency = dict(planned.get("latency") or {})
        latency["render_ms"] = render_ms
        latency["total_generate_ms"] = int((time.perf_counter() - t0) * 1000)
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
            "planner_mode": planned.get("planner_mode") or planned["plan"].get("planner_mode") or "LLM",
            "fallback": bool(planned.get("fallback")),
            "fallback_reason": planned.get("fallback_reason") or "",
            "degraded": bool(planned.get("degraded")),
            "model": planned.get("model") or "",
            "n_slides": planned["plan"].get("n_slides"),
            "charts_images_tables": visual_status,
            "visual_inventory": inventory,
            "quality": quality,
            "overlap_count": quality.get("overlap_count"),
            "out_of_bounds_count": quality.get("out_of_bounds_count"),
            "clipped_text_count": quality.get("clipped_text_count"),
            "whitespace_ratio": quality.get("whitespace_ratio"),
            "repeated_layout_count": quality.get("repeated_layout_count"),
            "ungrounded_fact_count": quality.get("ungrounded_fact_count"),
            "repair_attempts": quality.get("repair_attempts"),
            "final_quality_status": quality.get("final_quality_status"),
            "export_blocked": export_blocked,
            "inspector": inspector,
            "blocked_external": False,
            "latency": latency,
            "telemetry": {
                "provider": self.name,
                "opt_in": True,
                "used_master": used_master,
                "visuals": inventory,
                "planner_mode": planned.get("planner_mode"),
                "model": planned.get("model") or "",
                "llm": planned.get("telemetry") or {},
                "latency": latency,
                "quality": quality,
            },
        }
