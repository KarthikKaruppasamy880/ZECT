"""Render a native visual PPTX (chart + table + image) for headed S6.5 editor proof."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / "backend" / ".env", override=False)


def main() -> int:
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "zect-s65-visual.pptx")
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.environ["ZECT_PRESENT_ASSET_ROOT"] = str(dest.parent / ".zect-s65-assets")

    from app.services.mentrix.presentation.asset_resolver import example_png_bytes, store_image
    from app.services.mentrix.presentation.blocks import example_chart_block, example_table_block, normalize_block
    from app.services.mentrix.presentation.document import document_from_plan
    from app.services.mentrix.presentation.plan import validate_plan
    from app.services.mentrix.presentation.renderer import render_plan_to_pptx
    from app.services.pptx_paths import notes_sidecar_for_pptx, write_notes_sidecar

    meta = store_image(example_png_bytes(label="S65"), user_id="anon", filename="s65.png")
    image = normalize_block(
        {
            "kind": "image",
            "content": {"asset_id": meta["asset_id"], "alt": "S6.5 figure", "caption": "Example image"},
            "provenance": {"source": "example", "generated": True},
        },
        slide_index=1,
        ordinal=0,
    )
    raw = {
        "objective": "S6.5 visual editor proof",
        "audience_id": "executive",
        "narrative": "Figure, chart, table",
        "n_slides": 4,
        "slides": [
            {
                "title": "Status snapshot",
                "content_blocks": [{"kind": "bullet", "text": "Delivery is on track"}],
                "notes_intent": "Open with status.",
                "layout_intent": "title_body",
            },
            {
                "title": "Figure",
                "content_blocks": [{"kind": "bullet", "text": "Authorized figure"}],
                "blocks": [image],
                "visual_intent": "image",
                "layout_intent": "text_image",
                "notes_intent": "Describe the figure.",
            },
            {
                "title": "Metrics",
                "content_blocks": [{"kind": "bullet", "text": "Illustrative trend"}],
                "blocks": [example_chart_block(2, 0, title="Illustrative trend (example data)")],
                "visual_intent": "chart",
                "layout_intent": "chart_commentary",
                "notes_intent": "This chart is example data.",
            },
            {
                "title": "Workstreams",
                "content_blocks": [{"kind": "bullet", "text": "Status table"}],
                "blocks": [example_table_block(3, 0)],
                "visual_intent": "table",
                "layout_intent": "table",
                "notes_intent": "Walk the table.",
            },
        ],
    }
    plan = validate_plan(raw, n_slides=4, template_id="", audience_id="executive")
    dest.write_bytes(render_plan_to_pptx(plan, user_id="anon"))
    try:
        doc = document_from_plan(plan, path=str(dest), provider="zect_native")
        write_notes_sidecar(notes_sidecar_for_pptx(dest), __import__("json").dumps(doc, indent=2))
    except (PermissionError, OSError, ValueError):
        sidecar = dest.with_name(f"{dest.stem}.notes.json")
        sidecar.write_text(__import__("json").dumps(document_from_plan(plan, path=str(dest), provider="zect_native"), indent=2), encoding="utf-8")
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
