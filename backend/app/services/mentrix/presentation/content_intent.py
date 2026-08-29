"""Semantic slide content selection. Tables/charts/images require real structure, not keywords."""

from __future__ import annotations

import re
from typing import Any

SLIDE_INTENTS = (
    "TEXT",
    "BULLETS",
    "METRICS",
    "IMAGE",
    "CHART",
    "TABLE",
    "COMPARISON",
    "TIMELINE",
    "PROCESS",
    "ARCHITECTURE",
    "DIAGRAM",
)

_GENERIC_TABLE_HEADERS = {
    ("workstream", "status", "owner"),
    ("item", "status", "owner"),
    ("stream", "rag", "owner"),
}
_PLACEHOLDER_CELLS = frozenset({"watch", "owner", "n/a", "—", "-", "status", "a", "b", "c"})


def _lines(slide: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for block in list(slide.get("content_blocks") or []):
        text = str(block.get("text") or "").strip()
        if text:
            out.append(text)
    for block in list(slide.get("blocks") or []):
        if str(block.get("kind") or "") in {"text", "bullet", "body"}:
            text = str((block.get("content") or {}).get("text") or block.get("text") or "").strip()
            if text:
                out.append(text)
    return out


def parse_delimited_table(lines: list[str]) -> tuple[list[str], list[list[str]]] | None:
    """Return headers+rows only when lines look like a real table (3+ consistent columns)."""
    rows: list[list[str]] = []
    for line in lines:
        if "|" in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]
        elif "\t" in line:
            cells = [c.strip() for c in line.split("\t") if c.strip()]
        else:
            continue
        if len(cells) >= 3:
            rows.append(cells)
    if len(rows) < 2:
        return None
    width = len(rows[0])
    if width < 3 or any(len(r) != width for r in rows):
        return None
    return rows[0], rows[1:]


def table_from_blocks(slide: dict[str, Any]) -> tuple[list[str], list[list[str]]] | None:
    for block in list(slide.get("blocks") or []):
        if str(block.get("kind") or "") != "table":
            continue
        content = block.get("content") if isinstance(block.get("content"), dict) else {}
        headers = [str(h).strip() for h in list(content.get("headers") or []) if str(h).strip()]
        rows = [list(r) for r in list(content.get("rows") or []) if isinstance(r, list)]
        if len(headers) >= 2 and len(rows) >= 2:
            return headers, rows
    return None


def is_placeholder_table(headers: list[str], rows: list[list[str]]) -> bool:
    key = tuple(h.strip().lower() for h in headers[:3])
    if key in _GENERIC_TABLE_HEADERS:
        generic = 0
        total = 0
        for row in rows:
            for cell in row[1:]:
                total += 1
                if str(cell).strip().lower() in _PLACEHOLDER_CELLS:
                    generic += 1
        if total and generic / total >= 0.5:
            return True
    return False


def has_tabular_data(slide: dict[str, Any]) -> bool:
    parsed = table_from_blocks(slide) or parse_delimited_table(_lines(slide))
    if not parsed:
        return False
    headers, rows = parsed
    if is_placeholder_table(headers, rows):
        return False
    return True


def has_quantitative_series(slide: dict[str, Any]) -> bool:
    """True only when there is a comparable numeric series, not a lone 'Q3' token."""
    for block in list(slide.get("blocks") or []):
        if str(block.get("kind") or "") != "chart":
            continue
        content = block.get("content") if isinstance(block.get("content"), dict) else {}
        cats = list(content.get("categories") or [])
        series = list(content.get("series") or [])
        if len(cats) >= 2 and series:
            return True
    numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", " ".join(_lines(slide)))
    return len(numbers) >= 3


def user_requested_example_visual(prompt: str, slide: dict[str, Any]) -> bool:
    blob = f"{prompt} {slide.get('title') or ''} {slide.get('key_message') or ''}".lower()
    return any(w in blob for w in ("example chart", "illustrative", "sample data", "generated example"))


def choose_slide_intent(
    slide: dict[str, Any],
    *,
    purpose: str = "",
    asset_ids: list[str] | None = None,
    prompt: str = "",
) -> str:
    purpose = (purpose or str(slide.get("purpose") or "")).lower()
    existing = str(slide.get("visual_intent") or "none").lower()
    assets = [a for a in (asset_ids or []) if a]
    if purpose in {"architecture"}:
        return "ARCHITECTURE"
    if purpose in {"process", "flow"}:
        return "PROCESS"
    if has_tabular_data(slide):
        return "TABLE"
    if existing == "table" and not has_tabular_data(slide):
        return "BULLETS"
    if existing == "chart" or purpose == "status":
        if has_quantitative_series(slide) or user_requested_example_visual(prompt, slide):
            return "CHART"
        if purpose == "status":
            return "METRICS"
    if purpose == "figure":
        return "IMAGE"
    if existing == "image":
        blob = f"{prompt} {slide.get('title') or ''} {slide.get('key_message') or ''}".lower()
        if assets or user_requested_example_visual(prompt, slide) or any(
            w in blob for w in ("image", "photo", "figure", "screenshot", "caption")
        ):
            return "IMAGE"
        return "BULLETS"
    if purpose == "comparison":
        return "COMPARISON"
    if purpose in {"decision", "cta"}:
        return "BULLETS"
    if purpose == "opening":
        return "TEXT"
    if existing == "diagram":
        return "DIAGRAM"
    if existing == "quote":
        return "TEXT"
    if existing in {"metric", "metrics"}:
        return "METRICS"
    lines = _lines(slide)
    if len(lines) >= 2:
        return "BULLETS"
    return "TEXT"


def intent_to_visual(intent: str) -> str:
    return {
        "TABLE": "table",
        "CHART": "chart",
        "IMAGE": "image",
        "METRICS": "metric",
        "ARCHITECTURE": "diagram",
        "PROCESS": "diagram",
        "DIAGRAM": "diagram",
        "COMPARISON": "none",
        "TIMELINE": "none",
        "TEXT": "none",
        "BULLETS": "none",
    }.get(intent, "none")


def intent_to_layout(intent: str) -> str:
    return {
        "TABLE": "table",
        "CHART": "chart_commentary",
        "IMAGE": "text_image",
        "METRICS": "metrics",
        "ARCHITECTURE": "diagram",
        "PROCESS": "diagram",
        "DIAGRAM": "diagram",
        "COMPARISON": "two_column",
        "TIMELINE": "title_body",
        "TEXT": "title_body",
        "BULLETS": "title_body",
    }.get(intent, "title_body")
