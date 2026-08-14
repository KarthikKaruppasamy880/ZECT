"""Presenton adapter — HTTP engine only. Domain code must not import presenton_client."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.provider import PresentationGenerateRequest, PresentationStatus
from app.services.presenton_client import (
    generate_presentation,
    list_templates,
    presenton_base_url,
    presenton_configured,
    resolve_presenton_template_id,
)


class PresentonProvider:
    name = "presenton"

    def status(self, *, user_id: str = "anon") -> PresentationStatus:
        configured = presenton_configured()
        reachable = False
        hint = ""
        blocked_external = False
        block_code = ""
        listed: dict[str, Any] = {}
        if configured:
            listed = list_templates()
            reachable = bool(listed.get("reachable"))
            hint = str(listed.get("hint") or "")
            blocked_external = bool(listed.get("blocked_external"))
            block_code = str(listed.get("block_code") or "")
            if reachable:
                tmpl.maybe_bind_from_provider_templates(list(listed.get("templates") or []))
        else:
            hint = "Set PRESENTON_BASE_URL (e.g. http://127.0.0.1:5000) and run Presenton Docker"
            blocked_external = True
            block_code = "presenton_not_configured"
        lifecycle = tmpl.provider_lifecycle(
            configured=configured,
            reachable=reachable,
            template_id="zinnia-executive-v1",
            user_id=user_id,
        )
        mapped = tmpl.get_provider_mapping("zinnia-executive-v1")
        zinnia_ready = tmpl.is_verified_provider_id(str((mapped or {}).get("provider_template_id") or ""))
        return PresentationStatus(
            configured=configured,
            reachable=reachable,
            lifecycle=lifecycle,
            provider=self.name,
            hint=hint,
            blocked_external=blocked_external,
            block_code=block_code,
            base_url=presenton_base_url() or "",
            zinnia_ready=zinnia_ready,
        )

    def list_engine_templates(self) -> dict[str, Any]:
        return list_templates()

    def generate(self, req: PresentationGenerateRequest) -> dict[str, Any]:
        ui_choice = (req.ui_template_choice or req.template or "general").strip() or "general"
        custom = (req.custom_id or "").strip() or None
        resolved = resolve_presenton_template_id(ui_choice, custom_id=custom, user_id=req.user_id)
        if str(resolved.get("lifecycle") or "") == tmpl.LIFECYCLE_TEMPLATE_NOT_READY:
            return {
                "ok": False,
                "error": "template_not_ready",
                "hint": resolved.get("note") or "Register a provider mapping in the ZECT template registry",
                "http_status": 409,
                "template_sent": None,
                "ui_template_choice": resolved.get("ui_choice") or ui_choice,
                "canonical_id": resolved.get("canonical_id"),
                "zinnia_verified": False,
                "lifecycle": tmpl.LIFECYCLE_TEMPLATE_NOT_READY,
                "mapping_source": resolved.get("mapping_source"),
                "blocked_external": bool(resolved.get("blocked_external")),
                "block_code": "template_not_ready",
                "provider": self.name,
            }
        template_id = str(resolved.get("template_id") or "general").strip() or "general"
        out = generate_presentation(
            req.content,
            n_slides=req.n_slides,
            template=template_id,
            instructions=req.instructions or None,
            filename=req.filename or None,
        )
        out["provider"] = self.name
        out["ui_template_choice"] = resolved.get("ui_choice") or ui_choice
        out["canonical_id"] = resolved.get("canonical_id")
        out["template_sent"] = out.get("template_sent") or template_id
        out["resolve_note"] = resolved.get("note")
        out["mapping_source"] = resolved.get("mapping_source")
        zinnia_ui = str(out["ui_template_choice"]).startswith("zinnia-") or str(
            resolved.get("canonical_id") or ""
        ).startswith("zinnia-")
        out["zinnia_verified"] = (
            bool(resolved.get("zinnia_verified"))
            and str(out["template_sent"]) == str(resolved.get("template_id"))
            and str(resolved.get("mapping_source") or "") in ("registry", "custom")
        )
        if zinnia_ui and str(out["template_sent"]) in ("modern", "general", "standard", "swift"):
            out["zinnia_verified"] = False
            out["zinnia_note"] = (
                "Zinnia template is not mapped in the ZECT registry — TEMPLATE_NOT_READY "
                "(admin/setup must register a real provider master; do not use env as the user path)"
            )
        elif zinnia_ui and out["zinnia_verified"]:
            out["zinnia_note"] = f"Zinnia verified via registry ({resolved.get('note')})"
        lifecycle = str(resolved.get("lifecycle") or "")
        if not out.get("ok") or not out.get("path"):
            lifecycle = tmpl.LIFECYCLE_GENERATION_FAILED
            out["ok"] = False
            out["error"] = out.get("error") or "missing_pptx_output"
            out["http_status"] = 502
        out["lifecycle"] = lifecycle or tmpl.provider_lifecycle(
            configured=True,
            reachable=True,
            template_id=ui_choice,
            user_id=req.user_id,
            generation_failed=not out.get("ok"),
        )
        return out
