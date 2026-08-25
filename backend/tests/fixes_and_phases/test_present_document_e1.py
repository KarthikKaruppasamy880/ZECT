"""E1 PresentationDocument schema + E9 critique_document."""

from app.services.mentrix.presentation.document import SCHEMA_VERSION, document_from_pptx_bytes
from app.services.mentrix.presentation.quality_critic import critique_document
from app.services.mentrix.presentation.renderer import render_plan_to_pptx


def test_document_from_pptx_is_presentation_document_v2(tmp_path):
    dest = tmp_path / "doc.pptx"
    dest.write_bytes(
        render_plan_to_pptx(
            {
                "slides": [
                    {
                        "title": "Q3 delivery",
                        "content_blocks": [{"kind": "bullet", "text": "On track"}],
                        "notes_intent": "Say the status first",
                        "layout_intent": "title_body",
                    }
                ]
            }
        )
    )
    doc = document_from_pptx_bytes(dest.read_bytes(), path=str(dest), provider="zect_native")
    assert doc["kind"] == "PresentationDocument"
    assert doc["schema_version"] == SCHEMA_VERSION == 2
    assert int(doc["slide_cx"]) > 0
    assert int(doc["slide_cy"]) > 0
    assert len(doc["slides"]) == 1


def test_critique_document_reports_overlap():
    out = critique_document(
        {
            "schema_version": 2,
            "kind": "PresentationDocument",
            "path": "deck.pptx",
            "slide_cx": 9144000,
            "slide_cy": 5143500,
            "slides": [
                {
                    "text": "Q3 delivery status",
                    "notes": "Status then owners",
                    "blocks": [
                        {"kind": "chart", "geometry": {"x": 0, "y": 0, "cx": 200, "cy": 200}},
                        {"kind": "table", "geometry": {"x": 50, "y": 0, "cx": 200, "cy": 200}},
                    ],
                }
            ],
        }
    )
    assert "final_quality_status" in out
    assert out["schema_version"] == 2
    assert out["document_overlap_count"] >= 1
