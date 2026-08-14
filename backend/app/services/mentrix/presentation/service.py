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

    def generate(self, req: PresentationGenerateRequest) -> dict[str, Any]:
        out = self._provider.generate(req)
        out.setdefault("provider", self.provider_name)
        return out
