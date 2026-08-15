"""Grounding / anti-hallucination for native Present. Do not invent people, dates, or KPIs."""

from __future__ import annotations

import re
from typing import Any

SOURCE_GROUNDED = "SOURCE_GROUNDED"
USER_PROVIDED = "USER_PROVIDED"
PROJECT_GROUNDED = "PROJECT_GROUNDED"
GENERATED_EXAMPLE = "GENERATED_EXAMPLE"
UNKNOWN = "UNKNOWN"

_INVENTED_NAMES = re.compile(
    r"\b(John Doe|Jane Smith|Emily Johnson|John Smith|Alice Johnson|Bob Martinez)\b",
    re.I,
)
_OWNER_LABEL = re.compile(r"\b(owner(?:ship)?|assigned to)\s*[:\-]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")
_DATE_FACT = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.I,
)


def evidence_blob(context_items: list[dict[str, Any]] | None, prompt: str = "") -> str:
    parts = [prompt or ""]
    for item in list(context_items or []):
        if isinstance(item, dict):
            parts.append(str(item.get("content") or item.get("excerpt") or ""))
    return "\n".join(parts)


def classify_fact(text: str, *, evidence: str) -> str:
    value = (text or "").strip()
    if not value:
        return UNKNOWN
    hay = (evidence or "").lower()
    if value.lower() in hay:
        return SOURCE_GROUNDED
    if _INVENTED_NAMES.search(value):
        return GENERATED_EXAMPLE
    return UNKNOWN


def _scrub_text(text: str, *, evidence: str) -> tuple[str, int]:
    raw = text or ""
    count = 0
    if _INVENTED_NAMES.search(raw):
        raw = _INVENTED_NAMES.sub("TBD", raw)
        count += 1

    def _date(match: re.Match[str]) -> str:
        nonlocal count
        token = match.group(0)
        if token.lower() in evidence.lower():
            return token
        count += 1
        return "TBD"

    raw = _DATE_FACT.sub(_date, raw)
    return raw, count


def scrub_slide(slide: dict[str, Any], *, evidence: str) -> int:
    """Replace ungrounded person names/dates. Returns ungrounded_fact_count."""
    n = 0
    for key in ("title", "key_message", "notes_intent"):
        cleaned, extra = _scrub_text(str(slide.get(key) or ""), evidence=evidence)
        slide[key] = cleaned
        n += extra
    for block in list(slide.get("content_blocks") or []):
        cleaned, extra = _scrub_text(str(block.get("text") or ""), evidence=evidence)
        block["text"] = cleaned
        n += extra
    for block in list(slide.get("blocks") or []):
        content = block.get("content") if isinstance(block.get("content"), dict) else None
        if not content:
            continue
        if "text" in content:
            cleaned, extra = _scrub_text(str(content.get("text") or ""), evidence=evidence)
            content["text"] = cleaned
            n += extra
        if str(block.get("kind") or "") == "table":
            headers = [str(h) for h in list(content.get("headers") or [])]
            rows = list(content.get("rows") or [])
            new_rows = []
            for row in rows:
                if not isinstance(row, list):
                    continue
                cells = []
                for cell in row:
                    cleaned, extra = _scrub_text(str(cell), evidence=evidence)
                    n += extra
                    cells.append(cleaned)
                new_rows.append(cells)
            content["headers"] = headers
            content["rows"] = new_rows
            from app.services.mentrix.presentation.content_intent import is_placeholder_table

            if is_placeholder_table(headers, new_rows):
                block["kind"] = "text"
                block["content"] = {
                    "text": " ".join(" — ".join(str(c) for c in row) for row in new_rows[:6]),
                    "role": "body",
                }
                n += 1
    return n


def scrub_plan(plan: dict[str, Any], *, prompt: str = "", context_items: list[dict[str, Any]] | None = None) -> int:
    evidence = evidence_blob(context_items, prompt)
    total = 0
    for slide in list(plan.get("slides") or []):
        total += scrub_slide(slide, evidence=evidence)
    plan["ungrounded_fact_count"] = total
    return total
