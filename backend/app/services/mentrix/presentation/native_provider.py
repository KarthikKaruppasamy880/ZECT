"""Experimental ZECT-native presentation provider (S4 renderer)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.blocks import ensure_visual_blocks, visual_inventory
from app.services.mentrix.presentation.document import document_from_plan
from app.services.mentrix.presentation.generation_job import (
    enforce_slide_count_contract,
    new_generation_job,
    trace_slide_count,
)
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
            hint="Native generate uses ZECT LayoutComposer + PptxExporter. Set ZECT_PRESENTATION_PROVIDER=zect_native.",
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
        from app.services.mentrix.presentation.generation_progress import complete_job, create_job, set_stage

        job = new_generation_job(requested_slide_count=req.n_slides, run_id=req.run_id or "")
        progress = create_job(
            job_id=job["generation_job_id"],
            requested_slide_count=job["requested_slide_count"],
            user_id=req.user_id or "anon",
        )
        set_stage(job["generation_job_id"], "UNDERSTANDING", label="Understanding request")
        trace_slide_count(job, stage="planner_input", component="native_provider", count=req.n_slides)
        set_stage(job["generation_job_id"], "STORY_PLANNING", label="Planning story")
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
        if definition:
            from app.services.mentrix.presentation.template_semantics import enrich_definition_semantics

            definition = enrich_definition_semantics(definition)
        source = tmpl.source_pptx_path(canon, user_id=req.user_id) if canon else None
        used_master = bool(source and Path(source).is_file())
        plan = planned["plan"]
        plan["requested_slide_count"] = int(job["requested_slide_count"])
        plan["generation_job_id"] = job["generation_job_id"]
        trace_slide_count(job, stage="plan_built", component="planner", count=len(plan.get("slides") or []))
        asset_ids = [str(a).strip() for a in list(req.asset_ids or []) if str(a).strip()]
        for slide in list(plan.get("slides") or []):
            ensure_visual_blocks(slide, asset_ids=asset_ids)
        set_stage(job["generation_job_id"], "LAYOUT_PLANNING", label="Selecting layouts")
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
        set_stage(job["generation_job_id"], "QUALITY_CHECK", label="Quality inspection")
        plan, quality = repair_until_pass(
            plan,
            definition,
            prompt=req.content,
            context_items=list(req.context_items or []),
            degraded=degraded,
        )
        plan, slide_violations = enforce_slide_count_contract(plan, job=job)
        if slide_violations:
            quality["slide_count_violations"] = slide_violations
            quality["status"] = "FAIL"
            quality["final_quality_status"] = "FAIL"
        set_stage(job["generation_job_id"], "FINAL_QUALITY_CHECK", label="Finalizing")
        trace_slide_count(job, stage="post_repair", component="quality_repair", count=len(plan.get("slides") or []))

        def _render_and_inspect(current_plan: dict[str, Any]) -> tuple[bytes, dict[str, Any], dict[str, Any], int]:
            t_render = time.perf_counter()
            set_stage(job["generation_job_id"], "VISUAL_COMPOSITION", label="Composing slides")
            rendered = render_plan_to_pptx(
                current_plan,
                template_path=source if used_master else None,
                definition=definition,
                user_id=req.user_id or "anon",
            )
            render_ms = int((time.perf_counter() - t_render) * 1000)
            from app.services.mentrix.presentation.final_pptx_inspector import (
                inspect_and_repair_pptx,
                merge_inspector_into_quality,
            )
            from app.services.mentrix.presentation.document import document_from_pptx_bytes
            from app.services.mentrix.presentation.quality_critic import critique_document

            repaired, inspector = inspect_and_repair_pptx(rendered, definition=definition)
            merged = merge_inspector_into_quality(dict(quality), inspector)
            doc = document_from_pptx_bytes(repaired, path="")
            critic = critique_document(doc, prompt=req.content)
            merged["document_critic"] = critic
            if critic.get("deck_status") == "FAIL" or critic.get("export_blocked"):
                merged["status"] = "FAIL"
                merged["final_quality_status"] = "FAIL"
            return repaired, merged, inspector, render_ms

        def _post_render_plan_repair(current_plan: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
            from app.services.mentrix.presentation.content_capacity import dedupe_semantic_blocks
            from app.services.mentrix.presentation.layout_composer import compose_plan

            hard = set(report.get("hard_findings") or [])
            doc_critic = report.get("document_critic") if isinstance(report.get("document_critic"), dict) else {}
            if int(doc_critic.get("rendered_overlap_count") or 0) > 0:
                hard.add("rendered_overlap")
            for slide in list(current_plan.get("slides") or []):
                exclude = list(slide.get("_layout_exclude") or [])
                name = str(slide.get("master_layout_name") or "")
                if name and name not in exclude:
                    exclude.append(name)
                slide["_layout_exclude"] = exclude
                dedupe_semantic_blocks(slide)
                if "rendered_overlap" in hard or "text_shape_collision" in hard:
                    slide["blocks"] = [
                        b
                        for b in list(slide.get("blocks") or [])
                        if str(b.get("kind") or "") not in {"text", "quote", "metric"}
                    ]
            return compose_plan(current_plan, definition, prompt=req.content)

        try:
            data, quality, inspector, render_ms = _render_and_inspect(plan)
            post_render_attempts = 0
            while post_render_attempts < 2 and (
                inspector.get("status") == "FAIL"
                or str(quality.get("final_quality_status") or "") == "FAIL"
            ):
                post_render_attempts += 1
                plan = _post_render_plan_repair(plan, quality)
                data, quality, inspector, render_ms = _render_and_inspect(plan)
                quality["post_render_repair_attempts"] = post_render_attempts
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
        layout_hard = bool(quality.get("layout_hard_fail"))
        critic_fail = str(quality.get("final_quality_status") or quality.get("status") or "") == "FAIL"
        export_blocked = bool(layout_hard or inspector.get("status") == "FAIL" or critic_fail)
        generation_blocked = bool(export_blocked)
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
        outcome = "NEEDS_REVIEW" if generation_blocked else "COMPLETE"
        complete_job(job["generation_job_id"], outcome=outcome, path=str(dest), quality=quality)
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
            "lifecycle": tmpl.LIFECYCLE_NEEDS_REVIEW if generation_blocked else tmpl.LIFECYCLE_READY,
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
            "generation_blocked": generation_blocked,
            "generation_job": job,
            "generation_progress": progress,
            "requested_slide_count": job["requested_slide_count"],
            "generation_job_id": job["generation_job_id"],
            "slide_count_trace": job.get("trace") or [],
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
