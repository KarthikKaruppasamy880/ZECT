"""Blank deck PresentationDocument — real editable blocks, not an empty parse shell."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from app.services.mentrix.presentation.geometry import WIDESCREEN_CX, WIDESCREEN_CY
from app.services.pptx_paths import notes_sidecar_for_pptx, write_notes_sidecar

BlankLayout = Literal[
    "blank",
    "title_slide",
    "title_content",
    "section",
    "two_column",
    "comparison",
    "picture_text",
]

# Zinnia Present theme tokens (editor + export baseline)
ZECT_BLANK_THEME = {
    "accent": "#FF7500",
    "secondary": "#00628B",
    "text": "#1A1A1A",
    "muted": "#44546A",
    "background": "#FFFFFF",
}


def _accent_bar(slide_index: int, cx: int, cy: int) -> dict[str, Any]:
    return {
        "id": f"blk_{slide_index}_accent",
        "kind": "shape",
        "slide_index": slide_index,
        "geometry": {"x": 0, "y": 0, "cx": int(cx * 0.012), "cy": cy},
        "content": {"shape": "rect", "fill": ZECT_BLANK_THEME["accent"], "locked": False},
        "provenance": {"source": "blank", "generated": True},
    }


def _text_block(
    slide_index: int,
    *,
    block_id: str,
    role: str,
    text: str,
    x_ratio: float,
    y_ratio: float,
    w_ratio: float,
    h_ratio: float,
    font_size_pt: int,
    color: str,
    bold: bool = False,
    cx: int = WIDESCREEN_CX,
    cy: int = WIDESCREEN_CY,
) -> dict[str, Any]:
    return {
        "id": f"blk_{slide_index}_{block_id}",
        "kind": "text",
        "slide_index": slide_index,
        "geometry": {
            "x": int(cx * x_ratio),
            "y": int(cy * y_ratio),
            "cx": int(cx * w_ratio),
            "cy": int(cy * h_ratio),
        },
        "content": {
            "text": text,
            "role": role,
            "font_size_pt": font_size_pt,
            "color": color,
            "align": "left",
            **({"bold": True} if bold else {}),
        },
        "provenance": {"source": "blank", "generated": True},
    }


def blank_slide_blocks(
    *,
    slide_index: int = 0,
    layout: BlankLayout = "title_slide",
    cx: int = WIDESCREEN_CX,
    cy: int = WIDESCREEN_CY,
) -> list[dict[str, Any]]:
    """Layout-aware starter blocks — no instructional fixture copy in the PPTX."""
    accent = _accent_bar(slide_index, cx, cy)
    if layout == "blank":
        return [accent]
    if layout == "section":
        return [
            accent,
            _text_block(
                slide_index,
                block_id="section_title",
                role="title",
                text="Section title",
                x_ratio=0.08,
                y_ratio=0.38,
                w_ratio=0.84,
                h_ratio=0.18,
                font_size_pt=44,
                color=ZECT_BLANK_THEME["text"],
                bold=True,
                cx=cx,
                cy=cy,
            ),
        ]
    if layout == "title_content":
        return [
            accent,
            _text_block(
                slide_index,
                block_id="title",
                role="title",
                text="Untitled presentation",
                x_ratio=0.08,
                y_ratio=0.1,
                w_ratio=0.84,
                h_ratio=0.12,
                font_size_pt=36,
                color=ZECT_BLANK_THEME["text"],
                bold=True,
                cx=cx,
                cy=cy,
            ),
            _text_block(
                slide_index,
                block_id="body",
                role="body",
                text="",
                x_ratio=0.08,
                y_ratio=0.28,
                w_ratio=0.84,
                h_ratio=0.58,
                font_size_pt=18,
                color=ZECT_BLANK_THEME["text"],
                cx=cx,
                cy=cy,
            ),
        ]
    if layout == "picture_text":
        return [
            accent,
            _text_block(
                slide_index,
                block_id="title",
                role="title",
                text="Untitled presentation",
                x_ratio=0.08,
                y_ratio=0.07,
                w_ratio=0.84,
                h_ratio=0.1,
                font_size_pt=32,
                color=ZECT_BLANK_THEME["text"],
                bold=True,
                cx=cx,
                cy=cy,
            ),
            _text_block(
                slide_index,
                block_id="body",
                role="body",
                text="",
                x_ratio=0.08,
                y_ratio=0.22,
                w_ratio=0.44,
                h_ratio=0.68,
                font_size_pt=16,
                color=ZECT_BLANK_THEME["text"],
                cx=cx,
                cy=cy,
            ),
            {
                "id": f"blk_{slide_index}_picture",
                "kind": "image",
                "slide_index": slide_index,
                "geometry": {
                    "x": int(cx * 0.56),
                    "y": int(cy * 0.22),
                    "cx": int(cx * 0.36),
                    "cy": int(cy * 0.55),
                },
                "content": {
                    "alt": "Picture placeholder",
                    "fit": "contain",
                    "caption": "Insert picture",
                },
                "provenance": {"source": "blank", "generated": True},
            },
        ]
    if layout in {"two_column", "comparison"}:
        return [
            accent,
            _text_block(
                slide_index,
                block_id="title",
                role="title",
                text="Untitled presentation",
                x_ratio=0.08,
                y_ratio=0.08,
                w_ratio=0.84,
                h_ratio=0.1,
                font_size_pt=32,
                color=ZECT_BLANK_THEME["text"],
                bold=True,
                cx=cx,
                cy=cy,
            ),
            _text_block(
                slide_index,
                block_id="left",
                role="body",
                text="",
                x_ratio=0.08,
                y_ratio=0.24,
                w_ratio=0.4,
                h_ratio=0.62,
                font_size_pt=16,
                color=ZECT_BLANK_THEME["text"],
                cx=cx,
                cy=cy,
            ),
            _text_block(
                slide_index,
                block_id="right",
                role="body",
                text="",
                x_ratio=0.52,
                y_ratio=0.24,
                w_ratio=0.4,
                h_ratio=0.62,
                font_size_pt=16,
                color=ZECT_BLANK_THEME["text"],
                cx=cx,
                cy=cy,
            ),
        ]
    # Default: clean title slide (title + optional subtitle, no help bullets)
    return [
        accent,
        _text_block(
            slide_index,
            block_id="title",
            role="title",
            text="Untitled presentation",
            x_ratio=0.08,
            y_ratio=0.14,
            w_ratio=0.84,
            h_ratio=0.14,
            font_size_pt=40,
            color=ZECT_BLANK_THEME["text"],
            bold=True,
            cx=cx,
            cy=cy,
        ),
        _text_block(
            slide_index,
            block_id="subtitle",
            role="subtitle",
            text="",
            x_ratio=0.08,
            y_ratio=0.32,
            w_ratio=0.84,
            h_ratio=0.08,
            font_size_pt=20,
            color=ZECT_BLANK_THEME["muted"],
            cx=cx,
            cy=cy,
        ),
    ]


def blank_slide_document(*, slide_index: int = 0, layout: BlankLayout = "title_slide") -> dict[str, Any]:
    blocks = blank_slide_blocks(slide_index=slide_index, layout=layout)
    text = " ".join(
        str(b.get("content", {}).get("text") or "").strip()
        for b in blocks
        if b.get("kind") == "text"
    )
    return {
        "index": slide_index,
        "notes": "",
        "text": text[:4000],
        "layout_intent": layout,
        "background": {"fill": ZECT_BLANK_THEME["background"], "source": "blank"},
        "theme": dict(ZECT_BLANK_THEME),
        "blocks": blocks,
    }


def write_blank_sidecar(pptx: Path, *, layout: BlankLayout = "title_slide") -> Path:
    """Persist PresentationDocument blocks beside the blank PPTX."""
    sidecar = notes_sidecar_for_pptx(pptx)
    payload = {
        "version": 2,
        "kind": "presentation_document",
        "theme": dict(ZECT_BLANK_THEME),
        "slides": [blank_slide_document(slide_index=0, layout=layout)],
    }
    write_notes_sidecar(sidecar, json.dumps(payload, indent=2))
    return sidecar


__all__ = [
    "BlankLayout",
    "ZECT_BLANK_THEME",
    "blank_slide_blocks",
    "blank_slide_document",
    "write_blank_sidecar",
]
