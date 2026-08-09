"""Model call telemetry with fallback_* fields."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ModelTelemetry:
    requested_provider: str = ""
    requested_model: str = ""
    actual_provider: str = ""
    actual_model: str = ""
    fallback_used: bool = False
    fallback_reason: str = ""
    latency_ms: int = 0
    work_item_id: int | None = None
    agent_run_id: str | None = None
    operation_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class TelemetryTimer:
    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    def latency_ms(self) -> int:
        return int((time.perf_counter() - self._t0) * 1000)


def build_telemetry(
    *,
    requested_provider: str,
    requested_model: str,
    actual_provider: str,
    actual_model: str,
    fallback_used: bool = False,
    fallback_reason: str = "",
    latency_ms: int = 0,
    work_item_id: int | None = None,
    agent_run_id: str | None = None,
    operation_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return ModelTelemetry(
        requested_provider=requested_provider,
        requested_model=requested_model,
        actual_provider=actual_provider,
        actual_model=actual_model,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        latency_ms=latency_ms,
        work_item_id=work_item_id,
        agent_run_id=agent_run_id,
        operation_id=operation_id,
        extra=extra or {},
    ).to_dict()
