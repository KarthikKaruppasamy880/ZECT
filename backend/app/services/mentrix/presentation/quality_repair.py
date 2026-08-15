"""Bounded render → critic → repair → recompose loop for native Present."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.presentation.grounding import scrub_plan
from app.services.mentrix.presentation.layout_composer import compose_plan
from app.services.mentrix.presentation.quality_critic import critique_plan
from app.services.mentrix.presentation.quality_policy import MAX_BULLET_CHARS, MAX_BULLETS, MAX_REPAIR_ATTEMPTS, MAX_TITLE_CHARS


def _drop_kinds(slide: dict[str, Any], kinds: set[str]) -> None:
    slide["blocks"] = [b for b in list(slide.get("blocks") or []) if str(b.get("kind") or "") not in kinds]
    if str(slide.get("visual_intent") or "") in kinds:
        slide["visual_intent"] = "none"


def _shorten_slide(slide: dict[str, Any]) -> None:
    title = str(slide.get("title") or "")
    if len(title) > MAX_TITLE_CHARS:
        slide["title"] = title[: MAX_TITLE_CHARS - 1].rsplit(" ", 1)[0] or title[:MAX_TITLE_CHARS]
    blocks = list(slide.get("content_blocks") or [])
    kept = []
    for block in blocks[:MAX_BULLETS]:
        text = str(block.get("text") or "").strip()
        if len(text) > MAX_BULLET_CHARS:
            text = text[: MAX_BULLET_CHARS - 1].rsplit(" ", 1)[0] or text[:MAX_BULLET_CHARS]
        block["text"] = text
        if text:
            kept.append(block)
    slide["content_blocks"] = kept
    for block in list(slide.get("blocks") or []):
        content = block.get("content") if isinstance(block.get("content"), dict) else None
        if content and "text" in content:
            text = str(content.get("text") or "")
            if len(text) > MAX_BULLET_CHARS:
                content["text"] = text[: MAX_BULLET_CHARS - 1].rsplit(" ", 1)[0] or text[:MAX_BULLET_CHARS]


def _table_to_bullets(slide: dict[str, Any]) -> None:
    extra: list[dict[str, Any]] = list(slide.get("content_blocks") or [])
    for block in list(slide.get("blocks") or []):
        if str(block.get("kind") or "") != "table":
            continue
        content = block.get("content") if isinstance(block.get("content"), dict) else {}
        for row in list(content.get("rows") or []):
            if not isinstance(row, list):
                continue
            line = " — ".join(str(c).strip() for c in row if str(c).strip() and str(c).strip().lower() not in {"watch", "owner"})
            if line:
                extra.append({"kind": "bullet", "text": line[:MAX_BULLET_CHARS]})
    slide["content_blocks"] = extra[:MAX_BULLETS]
    _drop_kinds(slide, {"table"})
    slide["content_intent"] = "BULLETS"
    slide["layout"] = "title_body"


def _split_slide(slide: dict[str, Any]) -> dict[str, Any] | None:
    blocks = list(slide.get("content_blocks") or [])
    if len(blocks) < 5:
        return None
    mid = max(3, len(blocks) // 2)
    slide["content_blocks"] = blocks[:mid]
    clone = dict(slide)
    clone["content_blocks"] = blocks[mid:]
    clone["title"] = (str(slide.get("title") or "Continued") + " (continued)")[:MAX_TITLE_CHARS]
    clone["blocks"] = [b for b in list(slide.get("blocks") or []) if str(b.get("kind") or "") in {"text", "bullet"}]
    clone["visual_intent"] = "none"
    clone.pop("master_layout_name", None)
    clone.pop("composed_regions", None)
    return clone


def apply_repairs(plan: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    slides = list(plan.get("slides") or [])
    extra: list[dict[str, Any]] = []
    for slide, row in zip(slides, list(report.get("slides") or [])):
        repairs = set(row.get("repairs") or [])
        findings = set(row.get("findings") or [])
        if "table_to_bullets" in repairs or "placeholder_table" in findings or "inappropriate_table" in findings:
            _table_to_bullets(slide)
        if "drop_image" in repairs:
            _drop_kinds(slide, {"image"})
        if "drop_chart" in repairs:
            _drop_kinds(slide, {"chart"})
        if "shorten_text" in repairs or "shorten_or_split" in repairs or "cramped" in findings:
            _shorten_slide(slide)
        if "shorten_or_split" in repairs and len(list(slide.get("content_blocks") or [])) > MAX_BULLETS:
            follow = _split_slide(slide)
            if follow:
                extra.append(follow)
        if "change_layout" in repairs or "title_body_spacing" in repairs or "reposition" in repairs:
            slide.pop("master_layout_name", None)
            slide.pop("composed_regions", None)
        if "enlarge_content" in repairs:
            regions = slide.get("composed_regions") if isinstance(slide.get("composed_regions"), dict) else {}
            body = regions.get("body") if isinstance(regions.get("body"), dict) else None
            if body:
                body["cy"] = int(body.get("cy") or 1) + 200000
    if extra:
        slides.extend(extra)
        plan["slides"] = slides
        plan["n_slides"] = len(slides)
    return plan


def repair_until_pass(
    plan: dict[str, Any],
    definition: dict[str, Any] | None,
    *,
    prompt: str = "",
    context_items: list[dict[str, Any]] | None = None,
    degraded: bool = False,
    max_attempts: int = MAX_REPAIR_ATTEMPTS,
) -> tuple[dict[str, Any], dict[str, Any]]:
    scrubbed = scrub_plan(plan, prompt=prompt, context_items=context_items)
    compose_plan(plan, definition, prompt=prompt)
    report = critique_plan(plan, definition, prompt=prompt, context_items=context_items)
    attempts = 0
    while report.get("status") == "REPAIRABLE" and attempts < max_attempts:
        attempts += 1
        apply_repairs(plan, report)
        scrub_plan(plan, prompt=prompt, context_items=context_items)
        compose_plan(plan, definition, prompt=prompt)
        report = critique_plan(plan, definition, prompt=prompt, context_items=context_items)
    report["repair_attempts"] = attempts
    remaining = int(report.get("ungrounded_fact_count") or 0)
    hard = (
        report["overlap_count"]
        or report["out_of_bounds_count"]
        or report["table_appropriateness"] == "fail"
        or remaining
    )
    if report.get("status") == "REPAIRABLE":
        report["status"] = "FAIL" if hard else "PASS"
    layout_hard = bool(report.get("overlap_count") or report.get("out_of_bounds_count"))
    if report.get("status") == "FAIL" and degraded and not layout_hard:
        report["status"] = "PASS"
        report["degraded_override"] = True
    report["final_quality_status"] = report["status"]
    report["scrubbed_fact_count"] = scrubbed
    plan["quality"] = report
    plan["repair_attempts"] = attempts
    return plan, report
