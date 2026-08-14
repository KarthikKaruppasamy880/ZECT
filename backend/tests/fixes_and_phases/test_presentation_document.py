"""S5 PresentationDocument + OOXML notes/text round-trip."""

from __future__ import annotations

from app.services.mentrix.presentation.document import document_from_pptx_bytes
from app.services.mentrix.presentation.document_io import apply_document_to_pptx
from app.services.mentrix.presentation.renderer import render_plan_to_pptx
from app.services.pptx_parse import parse_pptx_bytes


def test_document_round_trip_notes_and_text(tmp_path):
    plan = {
        "slides": [
            {
                "index": 0,
                "title": "One",
                "content_blocks": [{"kind": "bullet", "text": "Alpha"}],
                "notes_intent": "Notes one",
                "layout_intent": "title_body",
            },
            {
                "index": 1,
                "title": "Two",
                "content_blocks": [{"kind": "bullet", "text": "Beta"}],
                "notes_intent": "Notes two",
                "layout_intent": "title_body",
            },
            {
                "index": 2,
                "title": "Three",
                "content_blocks": [{"kind": "bullet", "text": "Gamma"}],
                "notes_intent": "Notes three",
                "layout_intent": "title_body",
            },
        ]
    }
    dest = tmp_path / "doc.pptx"
    dest.write_bytes(render_plan_to_pptx(plan))
    doc = document_from_pptx_bytes(dest.read_bytes(), path=str(dest), provider="zect_native")
    assert len(doc["slides"]) == 3
    doc["slides"][0]["notes"] = "Updated native notes"
    doc["slides"][0]["text"] = "Updated title\nUpdated body"
    out = apply_document_to_pptx(dest, doc["slides"])
    assert out["ok"] is True
    assert out["ooxml_roundtrip"] is True
    slides = parse_pptx_bytes(dest.read_bytes())
    assert "updated native notes" in (slides[0].get("notes") or "").lower()
    blob = f"{slides[0].get('text') or ''} {slides[0].get('notes') or ''}".lower()
    assert "updated" in blob
