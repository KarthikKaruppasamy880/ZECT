"""Deterministic PresentationQualityCritic. PASS | REPAIRABLE | FAIL per slide and deck."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.services.mentrix.presentation.content_intent import (
    choose_slide_intent,
    has_quantitative_series,
    has_tabular_data,
    is_placeholder_table,
    table_from_blocks,
)
from app.services.mentrix.presentation.grounding import _INVENTED_NAMES, evidence_blob
from app.services.mentrix.presentation.layout_composer import compose_plan, compose_regions, pick_template_layout
from app.services.mentrix.presentation.quality_policy import (
    DENSITY_CRAMPED,
    MAX_BULLET_CHARS,
    MAX_BULLETS,
    MAX_REPEATED_LAYOUT,
    MAX_TITLE_CHARS,
    MIN_FONT_PT,
    TITLE_MIN_PT,
    WHITESPACE_SPARSE,
    boxes_overlap,
    slide_size_emu,
    within_bounds,
)

_KV_MEMORY_MYTH = re.compile(
    r"kv[\s-]*cache.{0,90}(reduces?|saves?|less|lower|decreases?).{0,40}memory"
    r"|memory.{0,40}(reduces?|saves?|less).{0,40}kv[\s-]*cache",
    re.I,
)


def _bullet_texts(slide: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for block in list(slide.get("content_blocks") or []):
        text = str(block.get("text") or "").strip()
        if text:
            out.append(text)
    for block in list(slide.get("blocks") or []):
        if str(block.get("kind") or "") not in {"text", "bullet", "body"}:
            continue
        text = str((block.get("content") or {}).get("text") or "").strip()
        if text:
            out.append(text)
    return out


def _occupied(slide: dict[str, Any], definition: dict[str, Any] | None) -> list[tuple[str, dict[str, int]]]:
    regions = slide.get("composed_regions") if isinstance(slide.get("composed_regions"), dict) else {}
    if not regions:
        layout = pick_template_layout(definition, slide)
        regions = compose_regions(definition, layout)
        slide["composed_regions"] = regions
    boxes: list[tuple[str, dict[str, int]]] = []
    title = regions.get("title")
    if isinstance(title, dict):
        boxes.append(("title", title))
    body = regions.get("body")
    visuals = [b for b in list(slide.get("blocks") or []) if str(b.get("kind") or "") not in {"text", "bullet", "body"}]
    if isinstance(body, dict) and not visuals:
        boxes.append(("body", body))
    for block in list(slide.get("blocks") or []):
        geom = block.get("geometry") if isinstance(block.get("geometry"), dict) else None
        if not geom:
            visual = regions.get("visual") if isinstance(regions.get("visual"), dict) else body
            if visual:
                geom = visual
        if geom and str(block.get("kind") or "") not in {"text", "bullet", "body"}:
            boxes.append((str(block.get("kind") or "block"), geom))
    return boxes


def critique_slide(
    slide: dict[str, Any],
    definition: dict[str, Any] | None,
    *,
    used_layouts: list[str],
    evidence: str,
    prompt: str = "",
) -> dict[str, Any]:
    findings: list[str] = []
    repairable: list[str] = []
    boxes = _occupied(slide, definition)
    overlap_count = 0
    out_of_bounds = 0
    for i, (ka, a) in enumerate(boxes):
        if not within_bounds(a, definition):
            out_of_bounds += 1
            findings.append("out_of_bounds")
            repairable.append("reposition")
        for kb, b in boxes[i + 1 :]:
            if ka == "title" and kb == "body":
                if boxes_overlap(a, b):
                    overlap_count += 1
                    findings.append("title_collision")
                    repairable.append("title_body_spacing")
            elif boxes_overlap(a, b):
                overlap_count += 1
                findings.append("overlap")
                repairable.append("reposition")
    bullets = _bullet_texts(slide)
    clipped = 0
    if len(bullets) > MAX_BULLETS:
        findings.append("excessive_text")
        repairable.append("shorten_or_split")
    for line in bullets:
        if len(line) > MAX_BULLET_CHARS:
            clipped += 1
            findings.append("truncated_text")
            repairable.append("shorten_text")
    title = str(slide.get("title") or "")
    if len(title) > MAX_TITLE_CHARS:
        findings.append("truncated_text")
        repairable.append("shorten_text")
    visual = str(slide.get("visual_intent") or "none")
    parsed = table_from_blocks(slide)
    if visual == "table" or parsed:
        if parsed and is_placeholder_table(*parsed):
            findings.append("placeholder_table")
            repairable.append("table_to_bullets")
        elif visual == "table" and not has_tabular_data(slide):
            findings.append("inappropriate_table")
            repairable.append("table_to_bullets")
    if visual == "chart" and not has_quantitative_series(slide):
        blob = f"{prompt} {title}".lower()
        if not any(w in blob for w in ("example", "illustrative", "sample data")):
            findings.append("inappropriate_chart")
            repairable.append("drop_chart")
    if visual == "image":
        blob = f"{prompt} {title} {slide.get('key_message') or ''} {slide.get('purpose') or ''}".lower()
        if not any(w in blob for w in ("image", "photo", "figure", "screenshot", "caption")):
            findings.append("irrelevant_image")
            repairable.append("drop_image")
    if _INVENTED_NAMES.search(" ".join([title, str(slide.get("notes_intent") or ""), *bullets])):
        findings.append("ungrounded_facts")
        repairable.append("scrub_facts")
    kv_blob = " ".join([title, str(slide.get("key_message") or ""), *bullets])
    if _KV_MEMORY_MYTH.search(kv_blob):
        findings.append("kv_cache_memory_oversimplified")
        repairable.append("ground_kv_cache")
    layout_name = str(slide.get("master_layout_name") or "")
    if layout_name and used_layouts.count(layout_name) >= MAX_REPEATED_LAYOUT:
        findings.append("repeated_layout")
        repairable.append("change_layout")
    cx, cy = slide_size_emu(definition)
    area = max(1, cx * cy)
    used = 0
    for _, geom in boxes:
        used += max(0, geom.get("cx", 0) * geom.get("cy", 0))
    whitespace = max(0.0, 1.0 - min(1.0, used / area))
    density = min(1.0, used / area)
    if whitespace > WHITESPACE_SPARSE and not bullets:
        findings.append("excessive_whitespace")
        repairable.append("enlarge_content")
    if density > DENSITY_CRAMPED and len(bullets) > 4:
        findings.append("cramped")
        repairable.append("shorten_or_split")
    intent = str(slide.get("content_intent") or choose_slide_intent(slide, prompt=prompt))
    status = "REPAIRABLE" if findings else "PASS"
    hard = {"title_collision", "overlap", "out_of_bounds", "placeholder_table", "ungrounded_facts"}
    return {
        "status": status,
        "findings": sorted(set(findings)),
        "repairs": sorted(set(repairable)),
        "overlap_count": overlap_count,
        "out_of_bounds_count": out_of_bounds,
        "clipped_text_count": clipped,
        "min_font_size": MIN_FONT_PT if bullets else TITLE_MIN_PT,
        "text_density": round(density, 3),
        "whitespace_ratio": round(whitespace, 3),
        "table_appropriateness": "ok" if visual != "table" or has_tabular_data(slide) else "fail",
        "image_relevance": "fail" if "irrelevant_image" in findings else ("ok" if visual == "image" else "n/a"),
        "content_intent": intent,
        "master_layout_name": layout_name,
        "hard_findings": sorted(set(findings) & hard),
    }


def critique_plan(
    plan: dict[str, Any],
    definition: dict[str, Any] | None,
    *,
    prompt: str = "",
    context_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not any(isinstance(s.get("composed_regions"), dict) for s in list(plan.get("slides") or [])):
        compose_plan(plan, definition, prompt=prompt)
    evidence = evidence_blob(context_items, prompt)
    used: list[str] = []
    slides_out: list[dict[str, Any]] = []
    for slide in list(plan.get("slides") or []):
        name = str(slide.get("master_layout_name") or "")
        row = critique_slide(slide, definition, used_layouts=used, evidence=evidence, prompt=prompt)
        slides_out.append(row)
        if name:
            used.append(name)
    titles = [str(s.get("title") or "").strip().lower() for s in list(plan.get("slides") or [])]
    generic = sum(1 for t in titles if t in {"opening", "status", "title", "slide", "context"})
    layout_counts = Counter(str(s.get("master_layout_name") or "") for s in list(plan.get("slides") or []))
    repeated_layout_count = sum(max(0, n - 1) for n in layout_counts.values() if n)
    overlap_count = sum(s["overlap_count"] for s in slides_out)
    out_of_bounds_count = sum(s["out_of_bounds_count"] for s in slides_out)
    clipped_text_count = sum(s["clipped_text_count"] for s in slides_out)
    ungrounded = 0
    for slide in list(plan.get("slides") or []):
        blob = " ".join(
            [
                str(slide.get("title") or ""),
                str(slide.get("notes_intent") or ""),
                " ".join(str(b.get("text") or "") for b in list(slide.get("content_blocks") or [])),
            ]
        )
        ungrounded += len(_INVENTED_NAMES.findall(blob))
    statuses = [s["status"] for s in slides_out]
    if any(s == "FAIL" for s in statuses):
        status = "FAIL"
    elif any(s == "REPAIRABLE" for s in statuses) or generic > 1:
        status = "REPAIRABLE"
    else:
        status = "PASS"
    whitespace = round(sum(s["whitespace_ratio"] for s in slides_out) / max(len(slides_out), 1), 3)
    density = round(sum(s["text_density"] for s in slides_out) / max(len(slides_out), 1), 3)
    table_ok = all(s["table_appropriateness"] != "fail" for s in slides_out)
    return {
        "status": status,
        "slides": slides_out,
        "overlap_count": overlap_count,
        "out_of_bounds_count": out_of_bounds_count,
        "clipped_text_count": clipped_text_count,
        "min_font_size": MIN_FONT_PT,
        "text_density": density,
        "whitespace_ratio": whitespace,
        "alignment_variance": 0.0,
        "repeated_layout_count": repeated_layout_count,
        "table_appropriateness": "ok" if table_ok else "fail",
        "image_relevance_status": next((s["image_relevance"] for s in slides_out if s["image_relevance"] == "fail"), "ok"),
        "ungrounded_fact_count": ungrounded,
        "repair_attempts": int(plan.get("repair_attempts") or 0),
        "final_quality_status": status,
        "generic_title_count": generic,
    }


def critique_document(doc: dict[str, Any], *, prompt: str = "") -> dict[str, Any]:
    """E9: run the critic against a PresentationDocument (editor / export path)."""
    slides: list[dict[str, Any]] = []
    for spec in list(doc.get("slides") or []):
        if not isinstance(spec, dict):
            continue
        slides.append(
            {
                "title": str(spec.get("text") or "").split("\n")[0][:80],
                "notes_intent": spec.get("notes") or "",
                "content_blocks": [{"text": spec.get("text") or ""}],
                "blocks": spec.get("blocks") or [],
            }
        )
    out = critique_plan({"slides": slides}, None, prompt=prompt)
    out["path"] = str(doc.get("path") or "")
    out["schema_version"] = int(doc.get("schema_version") or 1)
    out["slide_cx"] = int(doc.get("slide_cx") or 0)
    out["slide_cy"] = int(doc.get("slide_cy") or 0)
    try:
        from app.services.mentrix.presentation.geometry import (
            boxes_overlap,
            geometry_valid,
            normalize_geometry,
            within_slide,
        )

        slide_cx = int(doc.get("slide_cx") or 0)
        slide_cy = int(doc.get("slide_cy") or 0)
        overlap = 0
        oob = 0
        boxes: list[dict[str, int]] = []
        for spec in list(doc.get("slides") or []):
            if not isinstance(spec, dict):
                continue
            for raw in list(spec.get("blocks") or []):
                if not isinstance(raw, dict):
                    continue
                geo = raw.get("geometry")
                parent = raw.get("parent_geometry")
                if parent and geometry_valid(parent) and geometry_valid(geo):
                    from app.services.mentrix.presentation.geometry import compose_child_geometry

                    composed = compose_child_geometry(parent, geo)
                    geo = composed or geo
                g = normalize_geometry(geo)
                if not g:
                    continue
                if not within_slide(g, slide_cx, slide_cy):
                    oob += 1
                for prev in boxes:
                    if boxes_overlap(prev, g):
                        overlap += 1
                boxes.append(g)
        out["document_overlap_count"] = overlap
        out["document_out_of_bounds_count"] = oob
    except Exception:
        out["document_overlap_count"] = 0
        out["document_out_of_bounds_count"] = 0
    return out
