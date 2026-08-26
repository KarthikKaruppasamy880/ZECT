"""Layout content capacity contracts — measured from composed regions, not naive char counts."""

from __future__ import annotations

from typing import Any

from pptx.util import Inches

from app.services.mentrix.presentation.quality_policy import (
    MAX_BULLET_CHARS,
    MAX_BULLETS,
    MAX_TITLE_CHARS,
    MIN_READABLE_CY,
    boxes_overlap,
)

_TEXT_KINDS = frozenset({"text", "bullet", "body", "title", "subtitle", "quote", "metric"})


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def measure_layout_capacity(regions: dict[str, Any] | None) -> dict[str, int]:
    """Estimate readable capacity from title/body region geometry (EMU)."""
    title = (regions or {}).get("title") if isinstance((regions or {}).get("title"), dict) else {}
    body = (regions or {}).get("body") if isinstance((regions or {}).get("body"), dict) else {}
    title_cx = max(1, int(title.get("cx") or Inches(9)))
    title_cy = max(1, int(title.get("cy") or Inches(0.85)))
    body_cx = max(1, int(body.get("cx") or Inches(9)))
    body_cy = max(1, int(body.get("cy") or Inches(4.5)))
    # Heuristic: ~1 char per 90k EMU width at 12pt; line height ~MIN_READABLE_CY
    max_title_chars = max(24, min(MAX_TITLE_CHARS, int(title_cx / 90_000)))
    max_bullets = max(2, min(MAX_BULLETS, int(body_cy / max(MIN_READABLE_CY, int(Inches(0.35))))))
    max_bullet_chars = max(48, min(MAX_BULLET_CHARS, int(body_cx / 75_000)))
    title_lines = max(1, min(3, int(title_cy / max(MIN_READABLE_CY, int(Inches(0.28))))))
    return {
        "max_title_chars": max_title_chars,
        "max_title_lines": title_lines,
        "max_bullets": max_bullets,
        "max_bullet_chars": max_bullet_chars,
        "body_cy": body_cy,
        "title_cy": title_cy,
    }


def apply_content_budget(slide: dict[str, Any], regions: dict[str, Any] | None) -> dict[str, int]:
    """Trim slide content to layout capacity before composition/render."""
    cap = measure_layout_capacity(regions)
    title = str(slide.get("title") or "")
    if len(title) > cap["max_title_chars"]:
        slide["title"] = title[: cap["max_title_chars"] - 1].rsplit(" ", 1)[0] or title[: cap["max_title_chars"]]
    kept: list[dict[str, Any]] = []
    for block in list(slide.get("content_blocks") or [])[: cap["max_bullets"]]:
        text = str(block.get("text") or "").strip()
        if len(text) > cap["max_bullet_chars"]:
            text = text[: cap["max_bullet_chars"] - 1].rsplit(" ", 1)[0] or text[: cap["max_bullet_chars"]]
        if text:
            row = dict(block)
            row["text"] = text
            kept.append(row)
    slide["content_blocks"] = kept
    for block in list(slide.get("blocks") or []):
        if str(block.get("kind") or "") not in _TEXT_KINDS:
            continue
        content = block.get("content") if isinstance(block.get("content"), dict) else {}
        text = str(content.get("text") or "").strip()
        if len(text) > cap["max_bullet_chars"]:
            content["text"] = text[: cap["max_bullet_chars"] - 1].rsplit(" ", 1)[0] or text[: cap["max_bullet_chars"]]
            block["content"] = content
    slide["content_capacity"] = cap
    return cap


def dedupe_semantic_blocks(slide: dict[str, Any]) -> int:
    """Remove duplicate title/body/closing text at compose time (slide-11 class defect)."""
    regions = slide.get("composed_regions") if isinstance(slide.get("composed_regions"), dict) else {}
    title_geom = regions.get("title") if isinstance(regions.get("title"), dict) else None
    body_geom = regions.get("body") if isinstance(regions.get("body"), dict) else None
    title_text = _norm(str(slide.get("title") or ""))
    removed = 0
    signatures: list[tuple[str, dict[str, int]]] = []
    kept_blocks: list[dict[str, Any]] = []
    for block in list(slide.get("blocks") or []):
        kind = str(block.get("kind") or "")
        if kind not in _TEXT_KINDS:
            kept_blocks.append(block)
            continue
        content = block.get("content") if isinstance(block.get("content"), dict) else {}
        text = _norm(str(content.get("text") or ""))
        if not text:
            kept_blocks.append(block)
            continue
        geom = block.get("geometry") if isinstance(block.get("geometry"), dict) else None
        if geom is None:
            role = str(content.get("role") or "").lower()
            geom = title_geom if role in {"title", "subtitle"} else body_geom
        if not isinstance(geom, dict):
            kept_blocks.append(block)
            continue
        is_dup = False
        for prev_text, prev_geom in signatures:
            if not boxes_overlap(geom, prev_geom, pad=12_000):
                continue
            if prev_text == text or prev_text in text or text in prev_text:
                is_dup = True
                break
        if title_text and title_geom and boxes_overlap(geom, title_geom, pad=12_000):
            if text == title_text or (text in title_text and len(text) >= len(title_text) - 4):
                is_dup = True
        if is_dup:
            removed += 1
            continue
        signatures.append((text, geom))
        kept_blocks.append(block)
    slide["blocks"] = kept_blocks
    seen_bullets: set[str] = set()
    kept_cb: list[dict[str, Any]] = []
    for block in list(slide.get("content_blocks") or []):
        text = _norm(str(block.get("text") or ""))
        if not text:
            continue
        if text in seen_bullets:
            removed += 1
            continue
        if title_text and text == title_text:
            removed += 1
            continue
        if any(text == prev_text for prev_text, _g in signatures):
            removed += 1
            continue
        seen_bullets.add(text)
        kept_cb.append(block)
    slide["content_blocks"] = kept_cb
    if removed:
        slide["dedupe_removed"] = int(slide.get("dedupe_removed") or 0) + removed
    return removed
