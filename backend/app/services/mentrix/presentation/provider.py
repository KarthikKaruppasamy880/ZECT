"""ZECT PresentationProvider ABC — Presenton stays an adapter, not a domain import."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class PresentationGenerateRequest:
    content: str
    n_slides: int = 6
    template: str = "general"
    ui_template_choice: str = ""
    custom_id: str = ""
    instructions: str = ""
    filename: str = ""
    user_id: str = "anon"
    audience_id: str = "general"
    sensitivity_hint: str = ""
    context_items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PresentationStatus:
    configured: bool
    reachable: bool
    lifecycle: str
    provider: str
    hint: str = ""
    blocked_external: bool = False
    block_code: str = ""
    base_url: str = ""
    zinnia_ready: bool = False
    canonical_template_id: str = "zinnia-executive-v1"
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PresentationProvider(Protocol):
    name: str

    def status(self, *, user_id: str = "anon") -> PresentationStatus: ...

    def list_engine_templates(self) -> dict[str, Any]: ...

    def generate(self, req: PresentationGenerateRequest) -> dict[str, Any]: ...
