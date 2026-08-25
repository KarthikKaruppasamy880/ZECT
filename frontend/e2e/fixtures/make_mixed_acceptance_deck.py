"""Build a >=7-slide mixed-element deck for Present product acceptance (native renderer)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / "backend" / ".env", override=False)


def main() -> int:
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Documents" / "zect-mixed-acceptance.pptx"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.environ["ZECT_PRESENT_ASSET_ROOT"] = str(dest.parent / ".zect-mixed-assets")

    from app.services.mentrix.presentation.asset_resolver import example_png_bytes, store_image
    from app.services.mentrix.presentation.blocks import example_chart_block, example_table_block, normalize_block
    from app.services.mentrix.presentation.document import document_from_plan
    from app.services.mentrix.presentation.plan import validate_plan
    from app.services.mentrix.presentation.renderer import render_plan_to_pptx
    from app.services.pptx_paths import notes_sidecar_for_pptx, write_notes_sidecar

    meta = store_image(example_png_bytes(label="MixedAcceptance"), user_id="anon", filename="mixed.png")
    image = normalize_block(
        {
            "kind": "image",
            "content": {"asset_id": meta["asset_id"], "alt": "Architecture figure", "caption": "Figure"},
            "provenance": {"source": "example", "generated": True},
        },
        slide_index=2,
        ordinal=0,
    )
    diagram = normalize_block(
        {
            "kind": "diagram",
            "content": {
                "nodes": ["LLM", "RAG", "GraphRAG", "ZECT Lattice"],
                "edges": [["LLM", "RAG"], ["RAG", "GraphRAG"], ["GraphRAG", "ZECT Lattice"]],
            },
            "provenance": {"source": "example", "generated": True},
        },
        slide_index=5,
        ordinal=0,
    )
    slides = [
        {
            "title": "Executive overview",
            "content_blocks": [{"kind": "bullet", "text": "LLM and RAG in ZECT"}],
            "notes_intent": "Open with the executive summary.",
            "layout_intent": "title_body",
        },
        {
            "title": "Context",
            "content_blocks": [{"kind": "bullet", "text": "Why Graphify matters"}],
            "notes_intent": "Set context for leadership.",
            "layout_intent": "title_body",
        },
        {
            "title": "Architecture figure",
            "content_blocks": [{"kind": "bullet", "text": "Reference diagram"}],
            "blocks": [image],
            "visual_intent": "image",
            "layout_intent": "text_image",
            "notes_intent": "Describe the figure.",
        },
        {
            "title": "Metrics",
            "content_blocks": [{"kind": "bullet", "text": "Illustrative trend"}],
            "blocks": [example_chart_block(3, 0, title="Delivery trend (example data)")],
            "visual_intent": "chart",
            "layout_intent": "chart_commentary",
            "notes_intent": "Walk the chart values.",
        },
        {
            "title": "Comparison table",
            "content_blocks": [{"kind": "bullet", "text": "Approach comparison"}],
            "blocks": [example_table_block(4, 0)],
            "visual_intent": "table",
            "layout_intent": "table",
            "notes_intent": "Compare rows.",
        },
        {
            "title": "GraphRAG path",
            "content_blocks": [{"kind": "bullet", "text": "Nodes and edges"}],
            "blocks": [diagram],
            "visual_intent": "diagram",
            "layout_intent": "title_body",
            "notes_intent": "Explain the diagram.",
        },
        {
            "title": "Roadmap",
            "content_blocks": [
                {"kind": "bullet", "text": "Phase 1 — document canvas"},
                {"kind": "bullet", "text": "Phase 2 — export fidelity"},
                {"kind": "bullet", "text": "Phase 3 — Presenter Intelligence"},
            ],
            "notes_intent": "Close with roadmap.",
            "layout_intent": "title_body",
        },
        {
            "title": "Ask",
            "content_blocks": [{"kind": "bullet", "text": "Decisions needed this week"}],
            "notes_intent": "Leadership ask.",
            "layout_intent": "title_body",
        },
    ]
    plan = validate_plan(
        {
            "objective": "ZECT mixed acceptance deck",
            "audience_id": "executive",
            "narrative": "LLM RAG GraphRAG ZECT",
            "n_slides": len(slides),
            "slides": slides,
        },
        n_slides=len(slides),
        template_id="zinnia-executive-v1",
        audience_id="executive",
    )
    from app.services.mentrix.presentation import template_registry as tmpl

    master = tmpl.source_pptx_path("zinnia-executive-v1")
    if master is None or not master.is_file():
        raise FileNotFoundError("zinnia-executive-v1 master missing for mixed acceptance deck")
    definition_path = master.parent.parent / "definitions" / "zinnia-executive-v1.json"
    definition = json.loads(definition_path.read_text(encoding="utf-8")) if definition_path.is_file() else None
    dest.write_bytes(render_plan_to_pptx(plan, user_id="anon", template_path=master, definition=definition))
    doc = document_from_plan(plan, path=str(dest), provider="zect_native")
    write_notes_sidecar(notes_sidecar_for_pptx(dest), json.dumps(doc, indent=2))
    print(dest)
    print(f"slides={len(slides)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
