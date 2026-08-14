"""Editable PPTX charts via python-pptx. Only column/bar/line/pie/donut."""

from __future__ import annotations

from typing import Any

from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Emu

from app.services.mentrix.presentation.blocks import CHART_TYPES

_XL = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "line": XL_CHART_TYPE.LINE,
    "pie": XL_CHART_TYPE.PIE,
    "donut": XL_CHART_TYPE.DOUGHNUT,
}


def chart_data_from_block(block: dict[str, Any]) -> CategoryChartData | None:
    content = block.get("content") if isinstance(block.get("content"), dict) else {}
    categories = [str(c) for c in list(content.get("categories") or []) if str(c).strip()]
    series = [s for s in list(content.get("series") or []) if isinstance(s, dict)]
    if len(categories) < 2 or not series:
        return None
    data = CategoryChartData()
    data.categories = categories
    width = len(categories)
    for spec in series[:6]:
        values = list(spec.get("values") or [])[:width]
        if len(values) != width:
            return None
        data.add_series(str(spec.get("name") or "Series")[:80], tuple(float(v) for v in values))
    return data


def add_chart(slide, block: dict[str, Any], geometry: dict[str, int]) -> bool:
    content = block.get("content") if isinstance(block.get("content"), dict) else {}
    chart_type = str(content.get("chart_type") or "column").lower()
    if chart_type not in CHART_TYPES:
        chart_type = "column"
    data = chart_data_from_block(block)
    if data is None:
        return False
    x, y, cx, cy = (Emu(int(geometry[k])) for k in ("x", "y", "cx", "cy"))
    chart = slide.shapes.add_chart(_XL[chart_type], x, y, cx, cy, data).chart
    title = str(content.get("title") or "").strip()[:160]
    if title:
        chart.has_title = True
        chart.chart_title.text_frame.text = title
    chart.has_legend = bool(content.get("legend", True))
    return True


def replace_chart_data(slide, block: dict[str, Any]) -> bool:
    data = chart_data_from_block(block)
    if data is None:
        return False
    for shape in slide.shapes:
        if not getattr(shape, "has_chart", False):
            continue
        shape.chart.replace_data(data)
        title = str((block.get("content") or {}).get("title") or "").strip()[:160]
        if title:
            try:
                shape.chart.has_title = True
                shape.chart.chart_title.text_frame.text = title
            except Exception:
                pass
        return True
    return False
