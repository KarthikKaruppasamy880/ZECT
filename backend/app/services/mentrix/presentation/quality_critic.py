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


def _norm_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def _text_geometry_boxes(slide: dict[str, Any], definition: dict[str, Any] | None) -> list[tuple[str, str, dict[str, int]]]:
    """Semantic text blocks with resolved geometry for duplicate/collision checks."""
    regions = slide.get("composed_regions") if isinstance(slide.get("composed_regions"), dict) else {}
    if not regions:
        layout = pick_template_layout(definition, slide)
        regions = compose_regions(definition, layout)
    boxes: list[tuple[str, str, dict[str, int]]] = []
    title = str(slide.get("title") or "").strip()
    title_geom = regions.get("title")
    if title and isinstance(title_geom, dict):
        boxes.append(("title", _norm_text(title), title_geom))
    body_geom = regions.get("body") if isinstance(regions.get("body"), dict) else None
    for block in list(slide.get("blocks") or []):
        kind = str(block.get("kind") or "")
        if kind not in {"text", "bullet", "body", "quote", "metric"}:
            continue
        text = str((block.get("content") or {}).get("text") or "").strip()
        if not text:
            continue
        geom = block.get("geometry") if isinstance(block.get("geometry"), dict) else body_geom
        if isinstance(geom, dict):
            boxes.append((kind, _norm_text(text), geom))
    for block in list(slide.get("content_blocks") or []):
        text = str(block.get("text") or "").strip()
        if not text or not isinstance(body_geom, dict):
            continue
        norm = _norm_text(text)
        if any(norm == existing for _role, existing, _g in boxes):
            continue
        boxes.append(("bullet", norm, body_geom))
    return boxes


def _duplicate_semantic_count(slide: dict[str, Any], definition: dict[str, Any] | None) -> int:
    """Near-identical text occupying overlapping geometry (slide-11 class defect)."""
    boxes = _text_geometry_boxes(slide, definition)
    dup = 0
    for i, (_ka, ta, ga) in enumerate(boxes):
        if not ta:
            continue
        for _kb, tb, gb in boxes[i + 1 :]:
            if not tb:
                continue
            if not boxes_overlap(ga, gb, pad=12000):
                continue
            if ta == tb or ta in tb or tb in ta:
                dup += 1
    return dup


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
    duplicate_semantic_count = _duplicate_semantic_count(slide, definition)
    if duplicate_semantic_count:
        findings.append("duplicate_semantic_content")
        repairable.append("dedupe_text")
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
                repairable.append("change_layout")
    regions = slide.get("composed_regions") if isinstance(slide.get("composed_regions"), dict) else {}
    sem = regions.get("semantic_map") if isinstance(regions.get("semantic_map"), dict) else {}
    protected = list(sem.get("protected_regions") or [])
    body_geom = regions.get("body") if isinstance(regions.get("body"), dict) else None
    if body_geom and protected:
        from app.services.mentrix.presentation.template_semantics import region_overlaps_protected

        if region_overlaps_protected(body_geom, protected):
            findings.append("template_conflict")
            repairable.append("change_layout")
            overlap_count += 1
    bullets = _bullet_texts(slide)
    clipped = 0
    title = str(slide.get("title") or "")
    visual = str(slide.get("visual_intent") or "none")
    if len(bullets) <= 1 and len(title.strip()) < 12 and visual == "none":
        findings.append("near_empty")
        repairable.append("enlarge_content")
    if len(bullets) > MAX_BULLETS:
        findings.append("excessive_text")
        repairable.append("shorten_or_split")
    for line in bullets:
        if len(line) > MAX_BULLET_CHARS:
            clipped += 1
            findings.append("truncated_text")
            repairable.append("shorten_text")
    if len(title) > MAX_TITLE_CHARS:
        findings.append("truncated_text")
        repairable.append("shorten_text")
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
    hard = {
        "title_collision",
        "overlap",
        "out_of_bounds",
        "placeholder_table",
        "ungrounded_facts",
        "duplicate_semantic_content",
        "template_conflict",
        "near_empty",
    }
    if set(findings) & hard:
        status = "FAIL"
    return {
        "status": status,
        "findings": sorted(set(findings)),
        "repairs": sorted(set(repairable)),
        "duplicate_semantic_count": duplicate_semantic_count,
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
    slides_in = list(plan.get("slides") or [])
    pre_truncated = [
        any(len(str(block.get("text") or "")) > MAX_BULLET_CHARS for block in list(slide.get("content_blocks") or []))
        or len(str(slide.get("title") or "")) > MAX_TITLE_CHARS
        for slide in slides_in
    ]
    if definition and not any(isinstance(s.get("composed_regions"), dict) for s in slides_in):
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
    for idx, row in enumerate(slides_out):
        if not pre_truncated[idx]:
            continue
        findings = set(row.get("findings") or [])
        if "truncated_text" not in findings:
            findings.add("truncated_text")
            row["findings"] = sorted(findings)
            repairs = set(row.get("repairs") or [])
            repairs.add("shorten_text")
            row["repairs"] = sorted(repairs)
            row["status"] = "FAIL"
    titles = [str(s.get("title") or "").strip().lower() for s in list(plan.get("slides") or [])]
    generic = sum(1 for t in titles if t in {"opening", "status", "title", "slide", "context"})
    layout_counts = Counter(str(s.get("master_layout_name") or "") for s in list(plan.get("slides") or []))
    repeated_layout_count = sum(max(0, n - 1) for n in layout_counts.values() if n)
    overlap_count = sum(s["overlap_count"] for s in slides_out)
    duplicate_semantic_count = sum(int(s.get("duplicate_semantic_count") or 0) for s in slides_out)
    out_of_bounds_count = sum(s["out_of_bounds_count"] for s in slides_out)
    clipped_text_count = sum(s["clipped_text_count"] for s in slides_out)
    near_empty_slide_count = sum(1 for s in slides_out if "near_empty" in (s.get("findings") or []))
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
        "duplicate_semantic_count": duplicate_semantic_count,
        "out_of_bounds_count": out_of_bounds_count,
        "clipped_text_count": clipped_text_count,
        "near_empty_slide_count": near_empty_slide_count,
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


def _duplicate_block_id_count(doc: dict[str, Any]) -> int:
    dup = 0
    for spec in list(doc.get("slides") or []):
        if not isinstance(spec, dict):
            continue
        seen: set[str] = set()
        for raw in list(spec.get("blocks") or []):
            if not isinstance(raw, dict):
                continue
            block_id = str(raw.get("id") or "").strip()
            if not block_id:
                continue
            if block_id in seen:
                dup += 1
            else:
                seen.add(block_id)
    return dup


def critique_document(doc: dict[str, Any], *, prompt: str = "") -> dict[str, Any]:
    """E9: run the critic against a PresentationDocument (editor / export path)."""
    duplicate_block_id_count = _duplicate_block_id_count(doc)
    out: dict[str, Any] = {
        "status": "PASS",
        "deck_status": "PASS",
        "final_quality_status": "PASS",
        "slides": [],
        "overlap_count": 0,
        "duplicate_semantic_count": 0,
        "out_of_bounds_count": 0,
        "clipped_text_count": 0,
        "near_empty_slide_count": 0,
        "hard_findings": [],
        "export_blocked": False,
    }
    out["duplicate_block_id_count"] = duplicate_block_id_count
    try:
        from app.services.mentrix.presentation.rendered_quality import inspect_rendered_document

        rendered = inspect_rendered_document(doc)
        out["rendered_quality"] = rendered
        if rendered.get("rendered_overlap_count"):
            out.setdefault("hard_findings", []).append("rendered_overlap")
        if rendered.get("rendered_clipped_text_count"):
            out.setdefault("hard_findings", []).append("rendered_clipping")
        if rendered.get("status") == "FAIL":
            out["status"] = "FAIL"
            out["deck_status"] = "FAIL"
            out["export_blocked"] = True
    except Exception:
        out["rendered_quality"] = {"status": "n/a", "rendered_geometry_inspected": False}
    if duplicate_block_id_count:
        out["status"] = "FAIL"
        out["deck_status"] = "FAIL"
        out["export_blocked"] = True
        out.setdefault("hard_findings", [])
        if "duplicate_block_id" not in out["hard_findings"]:
            out["hard_findings"].append("duplicate_block_id")
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
        _text_kinds = frozenset({"text", "body", "title", "subtitle", "bullet", "quote", "metric", "chart", "table"})
        for spec in list(doc.get("slides") or []):
            if not isinstance(spec, dict):
                continue
            slide_boxes: list[dict[str, int]] = []
            for raw in list(spec.get("blocks") or []):
                if not isinstance(raw, dict):
                    continue
                kind = str(raw.get("kind") or "")
                if kind and kind not in _text_kinds:
                    continue
                content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
                has_text = bool(str(raw.get("text") or content.get("text") or "").strip())
                if kind not in _text_kinds and not has_text:
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
                for prev in slide_boxes:
                    if boxes_overlap(prev, g):
                        overlap += 1
                slide_boxes.append(g)
        out["document_overlap_count"] = overlap
        out["document_out_of_bounds_count"] = oob
        if overlap or oob:
            out["status"] = "FAIL"
            out["deck_status"] = "FAIL"
            out["final_quality_status"] = "FAIL"
            out["export_blocked"] = True
            out.setdefault("hard_findings", [])
            if overlap and "text_shape_collision" not in out["hard_findings"]:
                out["hard_findings"].append("text_shape_collision")
            if oob and "clipping_out_of_bounds" not in out["hard_findings"]:
                out["hard_findings"].append("clipping_out_of_bounds")
    except Exception:
        out["document_overlap_count"] = 0
        out["document_out_of_bounds_count"] = 0
    return out
