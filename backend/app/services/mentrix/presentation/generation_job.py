"""Generation job contract — immutable requested_slide_count with boundary tracing."""

from __future__ import annotations

import uuid
from typing import Any

from app.services.mentrix.presentation.plan import clamp_slide_count, normalize_slide


def new_generation_job(*, requested_slide_count: int, run_id: str = "") -> dict[str, Any]:
    count = clamp_slide_count(requested_slide_count)
    job_id = (run_id or "").strip() or str(uuid.uuid4())
    return {
        "generation_job_id": job_id,
        "requested_slide_count": count,
        "trace": [{"stage": "request", "component": "api", "count": count}],
    }


def trace_slide_count(job: dict[str, Any] | None, *, stage: str, component: str, count: int, detail: str = "") -> None:
    if not job:
        return
    row: dict[str, Any] = {"stage": stage, "component": component, "count": int(count)}
    if detail:
        row["detail"] = detail[:240]
    job.setdefault("trace", []).append(row)


def enforce_slide_count_contract(plan: dict[str, Any], *, job: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[str]]:
    """Hard-cap plan slides to requested_slide_count. Never expand beyond user contract."""
    requested = clamp_slide_count(plan.get("requested_slide_count") or plan.get("n_slides") or 6)
    violations: list[str] = []
    slides = list(plan.get("slides") or [])
    actual = len(slides)
    if actual > requested:
        violations.append(f"plan_slides={actual}>requested={requested}")
        slides = slides[:requested]
    while len(slides) < requested:
        idx = len(slides)
        slides.append(normalize_slide({"title": f"Slide {idx + 1}"}, index=idx))
    for idx, slide in enumerate(slides):
        slide["index"] = idx
    plan["slides"] = slides
    plan["n_slides"] = requested
    plan["requested_slide_count"] = requested
    trace_slide_count(job, stage="enforce", component="generation_job", count=len(slides), detail=",".join(violations))
    return plan, violations


def assert_pptx_slide_count(*, expected: int, actual: int, job: dict[str, Any] | None = None) -> None:
    from app.services.mentrix.presentation.template_importer import UnsafePptxError

    if int(actual) != int(expected):
        trace_slide_count(
            job,
            stage="pptx_validate",
            component="renderer",
            count=actual,
            detail=f"expected={expected}",
        )
        raise UnsafePptxError(f"slide_count_mismatch:expected={expected},actual={actual}")


__all__ = [
    "assert_pptx_slide_count",
    "enforce_slide_count_contract",
    "new_generation_job",
    "trace_slide_count",
]
