"""Experimental ZECT-native presentation provider. Generate lands in S3–S4."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.provider import PresentationGenerateRequest, PresentationStatus
from app.services.mentrix.presentation.template_definition import list_ready_ids, native_ready


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
            hint="Native generate is experimental and not implemented until S4",
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
        ready = native_ready(canon) if canon else False
        return {
            "ok": False,
            "error": "native_generate_not_implemented",
            "hint": "S2 imported TemplateDefinition only. Native PPTX generate is S3–S4.",
            "http_status": 501,
            "lifecycle": tmpl.LIFECYCLE_TEMPLATE_NOT_READY if not ready else tmpl.LIFECYCLE_GENERATION_FAILED,
            "provider": self.name,
            "ui_template_choice": ui,
            "canonical_id": canon,
            "zinnia_verified": False,
            "template_sent": None,
            "blocked_external": False,
            "block_code": "native_generate_not_implemented",
        }
