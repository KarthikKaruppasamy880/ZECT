"""Canonical provider-neutral presentation blocks (S6.5).

Kinds: text | image | chart | table | metric | quote | diagram.
Each block has stable id, slide, layout intent, geometry, content, provenance, validation.
"""

from __future__ import annotations

from typing import Any

BLOCK_KINDS = frozenset({"text", "bullet", "body", "image", "chart", "table", "metric", "quote", "diagram"})
TEXT_KINDS = frozenset({"text", "bullet", "body"})
VISUAL_KINDS = frozenset({"image", "chart", "table", "metric", "quote", "diagram"})
CHART_TYPES = frozenset({"column", "bar", "line", "pie", "donut"})
FIT_MODES = frozenset({"contain", "cover", "stretch"})
PROVENANCE_SOURCES = frozenset({"example", "generated", "evidence", "upload", "document", "project", "web"})
MAX_BLOCKS_PER_SLIDE = 16
MAX_TABLE_ROWS = 24
MAX_TABLE_COLS = 8
RENDER_TABLE_ROWS = 12
MAX_CHART_POINTS = 24
MAX_SERIES = 6


def _str(value: Any, *, limit: int) -> str:
    return str(value or "").strip()[:limit]


def stable_id(slide_index: int, kind: str, ordinal: int) -> str:
    return f"blk_{int(slide_index)}_{_str(kind, limit=16) or 'text'}_{int(ordinal)}"


def _provenance(raw: Any, *, default_source: str = "generated") -> dict[str, Any]:
    row = raw if isinstance(raw, dict) else {}
    source = _str(row.get("source") or default_source, limit=24).lower() or default_source
    if source not in PROVENANCE_SOURCES:
        source = default_source
    return {
        "source": source,
        "source_id": _str(row.get("source_id"), limit=120),
        "generated": bool(row.get("generated")) or source in {"example", "generated"},
        "untrusted": bool(row.get("untrusted", source in {"evidence", "document", "web"})),
        "note": _str(row.get("note"), limit=240),
    }


def _validation(errors: list[str]) -> dict[str, Any]:
    clean = [e for e in errors if e]
    return {"ok": not clean, "errors": clean}


def _geometry(raw: Any) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[str, int] = {}
    for key in ("x", "y", "cx", "cy"):
        try:
            out[key] = int(raw.get(key))
        except (TypeError, ValueError):
            return None
    if out["cx"] <= 0 or out["cy"] <= 0:
        return None
    return out


def _text_content(row: dict[str, Any]) -> dict[str, Any]:
    text = _str(row.get("text") or (row.get("content") if isinstance(row.get("content"), str) else ""), limit=800)
    nested = row.get("content") if isinstance(row.get("content"), dict) else {}
    if not text:
        text = _str(nested.get("text"), limit=800)
    return {"text": text, "role": _str(nested.get("role") or row.get("role") or "body", limit=24) or "body"}


def _image_content(row: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    nested = row.get("content") if isinstance(row.get("content"), dict) else {}
    asset_id = _str(row.get("asset_id") or nested.get("asset_id"), limit=80)
    url = _str(row.get("url") or nested.get("url"), limit=500)
    errors: list[str] = []
    if url:
        errors.append("image_url_rejected")
    fit = _str(nested.get("fit") or row.get("fit") or "contain", limit=16).lower() or "contain"
    if fit not in FIT_MODES:
        fit = "contain"
    content = {
        "asset_id": asset_id,
        "alt": _str(nested.get("alt") or row.get("alt") or "Slide image", limit=200),
        "caption": _str(nested.get("caption") or row.get("caption"), limit=200),
        "fit": fit,
    }
    if not asset_id:
        errors.append("image_asset_required")
    return content, errors


def _floats(values: Any, *, limit: int) -> list[float]:
    out: list[float] = []
    if not isinstance(values, (list, tuple)):
        return out
    for item in values[:limit]:
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            continue
    return out


def _chart_content(row: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    nested = row.get("content") if isinstance(row.get("content"), dict) else row
    chart_type = _str(nested.get("chart_type") or nested.get("type") or "column", limit=16).lower() or "column"
    if chart_type not in CHART_TYPES:
        chart_type = "column"
    categories = [_str(c, limit=80) for c in list(nested.get("categories") or [])[:MAX_CHART_POINTS] if _str(c, limit=80)]
    series_in = nested.get("series") if isinstance(nested.get("series"), list) else []
    series: list[dict[str, Any]] = []
    for i, spec in enumerate(series_in[:MAX_SERIES]):
        if not isinstance(spec, dict):
            continue
        values = _floats(spec.get("values"), limit=MAX_CHART_POINTS)
        name = _str(spec.get("name") or f"Series {i + 1}", limit=80) or f"Series {i + 1}"
        if values:
            series.append({"name": name, "values": values})
    errors: list[str] = []
    if len(categories) < 2 or not series:
        errors.append("chart_data_required")
    else:
        width = len(categories)
        for spec in series:
            if len(spec["values"]) != width:
                errors.append("chart_series_length_mismatch")
                break
    return {
        "chart_type": chart_type,
        "title": _str(nested.get("title") or row.get("title") or "Chart", limit=160) or "Chart",
        "categories": categories,
        "series": series,
        "legend": bool(nested.get("legend", True)),
        "x_axis": _str(nested.get("x_axis") or nested.get("xlabel"), limit=80),
        "y_axis": _str(nested.get("y_axis") or nested.get("ylabel"), limit=80),
    }, errors


def _table_content(row: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    nested = row.get("content") if isinstance(row.get("content"), dict) else row
    headers = [_str(h, limit=80) for h in list(nested.get("headers") or [])[:MAX_TABLE_COLS] if _str(h, limit=80)]
    rows_in = nested.get("rows") if isinstance(nested.get("rows"), list) else []
    rows: list[list[str]] = []
    errors: list[str] = []
    for raw_row in rows_in[:MAX_TABLE_ROWS]:
        if isinstance(raw_row, list):
            rows.append([_str(c, limit=120) for c in raw_row[:MAX_TABLE_COLS]])
        elif isinstance(raw_row, str) and raw_row.strip():
            rows.append([raw_row.strip()[:120]])
    if not headers and rows:
        width = max(len(r) for r in rows)
        headers = [f"Col {i + 1}" for i in range(width)]
    width = len(headers)
    if width < 1 or len(rows) < 1:
        errors.append("table_data_required")
    if len(rows_in) > MAX_TABLE_ROWS or (rows and max(len(r) for r in rows) > MAX_TABLE_COLS):
        errors.append("table_too_large")
    if len(rows) > RENDER_TABLE_ROWS:
        extra = len(rows) - RENDER_TABLE_ROWS
        errors.append(f"table_truncated:{extra}")
        rows = rows[:RENDER_TABLE_ROWS]
    for i, r in enumerate(rows):
        if len(r) < width:
            rows[i] = r + [""] * (width - len(r))
        elif len(r) > width:
            rows[i] = r[:width]
    return {"headers": headers, "rows": rows, "title": _str(nested.get("title"), limit=160)}, errors


def _metric_content(row: dict[str, Any]) -> dict[str, Any]:
    nested = row.get("content") if isinstance(row.get("content"), dict) else row
    return {
        "label": _str(nested.get("label") or row.get("text") or "Metric", limit=80) or "Metric",
        "value": _str(nested.get("value") or nested.get("text"), limit=40) or "—",
        "unit": _str(nested.get("unit"), limit=24),
        "delta": _str(nested.get("delta"), limit=40),
    }


def _quote_content(row: dict[str, Any]) -> dict[str, Any]:
    nested = row.get("content") if isinstance(row.get("content"), dict) else {}
    text = _str(nested.get("text") or row.get("text"), limit=400)
    return {"text": text or "Key message", "attribution": _str(nested.get("attribution") or row.get("attribution"), limit=80)}


def _diagram_content(row: dict[str, Any]) -> dict[str, Any]:
    nested = row.get("content") if isinstance(row.get("content"), dict) else {}
    nodes_in = nested.get("nodes") if isinstance(nested.get("nodes"), list) else []
    nodes = [_str(n if not isinstance(n, dict) else n.get("label"), limit=60) for n in nodes_in[:8]]
    nodes = [n for n in nodes if n]
    if not nodes:
        nodes = ["Context", "Status", "Ask"]
    return {"diagram_type": _str(nested.get("diagram_type") or "boxes", limit=24) or "boxes", "nodes": nodes}


def normalize_block(raw: Any, *, slide_index: int, ordinal: int) -> dict[str, Any] | None:
    if isinstance(raw, str) and raw.strip():
        raw = {"kind": "text", "text": raw.strip()}
    if not isinstance(raw, dict):
        return None
    kind = _str(raw.get("kind") or "text", limit=24).lower() or "text"
    if kind not in BLOCK_KINDS:
        kind = "text"
    errors: list[str] = []
    if kind in TEXT_KINDS:
        content = _text_content(raw)
        if not content["text"]:
            return None
        kind = "text"
    elif kind == "image":
        content, errors = _image_content(raw)
    elif kind == "chart":
        content, errors = _chart_content(raw)
    elif kind == "table":
        content, errors = _table_content(raw)
    elif kind == "metric":
        content = _metric_content(raw)
    elif kind == "quote":
        content = _quote_content(raw)
    else:
        content = _diagram_content(raw)
    incoming_val = raw.get("validation") if isinstance(raw.get("validation"), dict) else {}
    extra = [_str(e, limit=80) for e in list(incoming_val.get("errors") or [])[:8]]
    block_id = _str(raw.get("id"), limit=64) or stable_id(slide_index, kind, ordinal)
    layout_intent = _str(raw.get("layout_intent"), limit=32)
    return {
        "id": block_id,
        "kind": kind,
        "slide_index": int(slide_index),
        "layout_intent": layout_intent,
        "geometry": _geometry(raw.get("geometry")),
        "content": content,
        "provenance": _provenance(raw.get("provenance"), default_source="example" if kind in VISUAL_KINDS else "generated"),
        "validation": _validation(errors + extra),
    }


def normalize_blocks(raw: Any, *, slide_index: int) -> list[dict[str, Any]]:
    items = raw if isinstance(raw, list) else []
    out: list[dict[str, Any]] = []
    for item in items[:MAX_BLOCKS_PER_SLIDE]:
        block = normalize_block(item, slide_index=slide_index, ordinal=len(out))
        if block:
            out.append(block)
    return out


def text_lines(blocks: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for block in blocks:
        if block.get("kind") not in TEXT_KINDS:
            continue
        text = _str((block.get("content") or {}).get("text"), limit=800)
        if text:
            lines.append(text)
    return lines


def example_chart_block(
    slide_index: int,
    ordinal: int,
    *,
    title: str = "Illustrative trend (example data)",
    chart_type: str = "column",
) -> dict[str, Any]:
    kind = chart_type if chart_type in CHART_TYPES else "column"
    return normalize_block(
        {
            "kind": "chart",
            "content": {
                "chart_type": kind,
                "title": title,
                "categories": ["Q1", "Q2", "Q3", "Q4"],
                "series": [{"name": "Example", "values": [12, 18, 15, 22]}],
            },
            "provenance": {"source": "example", "generated": True, "note": "Not factual — example data"},
        },
        slide_index=slide_index,
        ordinal=ordinal,
    )


def example_table_block(
    slide_index: int,
    ordinal: int,
    *,
    headers: list[str] | None = None,
    rows: list[list[str]] | None = None,
    title: str = "Status (example)",
) -> dict[str, Any]:
    hdrs = [str(h)[:40] for h in (headers or ["Workstream", "Status", "Owner"])][:6] or ["Workstream", "Status", "Owner"]
    body = [list(r)[: len(hdrs)] for r in (rows or []) if isinstance(r, list)][:8]
    if not body:
        body = [["Delivery", "On track", "A"], ["Risks", "Watch", "B"], ["Ask", "This week", "C"]]
    return normalize_block(
        {
            "kind": "table",
            "content": {"title": title, "headers": hdrs, "rows": body},
            "provenance": {"source": "example", "generated": True, "note": "Not factual — example table"},
        },
        slide_index=slide_index,
        ordinal=ordinal,
    )


def example_metric_block(slide_index: int, ordinal: int, *, label: str, value: str) -> dict[str, Any]:
    return normalize_block(
        {
            "kind": "metric",
            "content": {"label": label, "value": value},
            "provenance": {"source": "example", "generated": True, "note": "Not factual — example metric"},
        },
        slide_index=slide_index,
        ordinal=ordinal,
    )


def example_quote_block(slide_index: int, ordinal: int, *, text: str) -> dict[str, Any]:
    return normalize_block(
        {"kind": "quote", "content": {"text": text}, "provenance": {"source": "generated"}},
        slide_index=slide_index,
        ordinal=ordinal,
    )


def example_diagram_block(
    slide_index: int,
    ordinal: int,
    *,
    nodes: list[str] | None = None,
    diagram_type: str = "flow",
) -> dict[str, Any]:
    labels = [str(n).strip()[:60] for n in (nodes or []) if str(n).strip()][:6]
    if len(labels) < 2:
        labels = ["Context", "Status", "Decisions"]
    return normalize_block(
        {
            "kind": "diagram",
            "content": {"diagram_type": diagram_type or "flow", "nodes": labels},
            "provenance": {"source": "generated", "generated": True, "note": "Conceptual — not a measured system map"},
        },
        slide_index=slide_index,
        ordinal=ordinal,
    )


def _has_valid_kind(blocks: list[dict[str, Any]], kind: str) -> bool:
    for block in blocks:
        if str(block.get("kind") or "") != kind:
            continue
        if (block.get("validation") or {}).get("ok", True):
            return True
    return False


def ensure_visual_blocks(slide: dict[str, Any], *, asset_ids: list[str] | None = None) -> dict[str, Any]:
    """Attach typed blocks for visual_intent. Never invent factual numbers (example provenance)."""
    blocks = list(slide.get("blocks") or [])
    intent = str(slide.get("visual_intent") or "none").lower()
    index = int(slide.get("index") or 0)
    assets = [a for a in (asset_ids or []) if a]
    if intent == "chart" and not _has_valid_kind(blocks, "chart"):
        blocks = [b for b in blocks if str(b.get("kind") or "") != "chart"]
        chart_type = str(slide.get("chart_type") or "column")
        blocks.append(example_chart_block(index, len(blocks), chart_type=chart_type))
    if intent == "table":
        from app.services.mentrix.presentation.content_intent import (
            is_placeholder_table,
            parse_delimited_table,
            table_from_blocks,
        )

        parsed = table_from_blocks(slide) or parse_delimited_table(
            [str(b.get("text") or "").strip() for b in list(slide.get("content_blocks") or []) if str(b.get("text") or "").strip()]
        )
        if _has_valid_kind(blocks, "table"):
            pass
        elif parsed and not is_placeholder_table(*parsed):
            headers, rows = parsed
            blocks.append(
                example_table_block(index, len(blocks), headers=headers, rows=rows, title="Status")
            )
        else:
            slide["visual_intent"] = "none"
            intent = "none"
            blocks = [b for b in blocks if str(b.get("kind") or "") != "table"]
    if intent == "image" and not _has_valid_kind(blocks, "image"):
        blocks = [b for b in blocks if str(b.get("kind") or "") != "image"]
        asset = assets[0] if assets else ""
        block = normalize_block(
            {
                "kind": "image",
                "content": {"asset_id": asset, "alt": "Slide image"},
                "provenance": {"source": "upload" if asset else "example", "generated": not bool(asset)},
            },
            slide_index=index,
            ordinal=len(blocks),
        )
        if block:
            blocks.append(block)
    if intent == "quote" and not _has_valid_kind(blocks, "quote"):
        blocks = [b for b in blocks if str(b.get("kind") or "") != "quote"]
        blocks.append(example_quote_block(index, len(blocks), text=str(slide.get("notes_intent") or "Lead with the decision.")[:400]))
    if intent == "metric" and not _has_valid_kind(blocks, "metric"):
        blocks = [b for b in blocks if str(b.get("kind") or "") != "metric"]
        blocks.append(example_metric_block(index, len(blocks), label="Example KPI", value="n/a"))
    if intent == "diagram" and not _has_valid_kind(blocks, "diagram"):
        blocks = [b for b in blocks if str(b.get("kind") or "") != "diagram"]
        nodes = [
            str(b.get("text") or "").strip()
            for b in list(slide.get("content_blocks") or [])
            if str(b.get("text") or "").strip()
        ]
        dtype = str(slide.get("visual_choice") or slide.get("diagram_type") or "flow")
        if dtype not in {"flow", "architecture", "process", "sequence", "boxes"}:
            dtype = "flow"
        blocks.append(example_diagram_block(index, len(blocks), nodes=nodes, diagram_type=dtype))
    if intent == "image" and assets:
        for block in blocks:
            if block.get("kind") == "image" and not str((block.get("content") or {}).get("asset_id") or "").strip():
                block["content"]["asset_id"] = assets[0]
                block["provenance"] = {"source": "upload", "generated": False, "untrusted": False, "note": "", "source_id": ""}
                block["validation"] = {"ok": True, "errors": []}
    slide["blocks"] = [b for b in blocks if b]
    return slide


def visual_inventory(plan: dict[str, Any]) -> dict[str, int]:
    counts = {k: 0 for k in ("text", "image", "chart", "table", "metric", "quote", "diagram")}
    for slide in list(plan.get("slides") or []):
        for block in list(slide.get("blocks") or []):
            kind = str(block.get("kind") or "")
            if kind in counts:
                counts[kind] += 1
            elif kind in TEXT_KINDS:
                counts["text"] += 1
    return counts
