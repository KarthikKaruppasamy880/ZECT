"""S4 native PPTX renderer — experimental; Presenton stays default."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.provider import PresentationGenerateRequest
from app.services.mentrix.presentation.renderer import render_plan_to_pptx, validate_generated_pptx
from app.services.mentrix.presentation.service import PresentationService
from app.services.pptx_parse import parse_pptx_bytes
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes


def test_native_generate_writes_valid_pptx_without_presenton(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_PRESENTATION_PROVIDER", "zect_native")
    monkeypatch.setattr(
        "app.services.mentrix.presentation.native_provider.default_pptx_save_dir",
        lambda: tmp_path,
    )
    imported = tmpl.import_canonical_master(
        "zinnia-executive-v1",
        make_master_pptx_bytes(),
        name="Zinnia Executive",
        filename="exec.pptx",
    )
    assert imported["native_ready"] is True
    with patch("app.services.presenton_client.generate_presentation") as gen:
        with patch("app.services.phases.llm_phase._chat", return_value={"ok": False, "error": "offline", "content": ""}):
            out = PresentationService().generate(
                PresentationGenerateRequest(
                    content="Q3 delivery status for leadership",
                    n_slides=4,
                    ui_template_choice="zinnia-executive-v1",
                    audience_id="executive",
                    filename="zect-native-s4.pptx",
                    user_id="u1",
                )
            )
        gen.assert_not_called()
    assert out["ok"] is True, out.get("error") or out.get("hint") or out
    assert out["provider"] == "zect_native"
    assert out["zinnia_verified"] is True
    path = Path(out["path"])
    assert path.is_file()
    data = path.read_bytes()
    validate_generated_pptx(data, n_slides=4)
    slides = parse_pptx_bytes(data)
    assert len(slides) == 4
    assert any((s.get("text") or s.get("notes")) for s in slides)


def test_native_zinnia_without_definition_is_not_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_PRESENTATION_PROVIDER", "zect_native")
    monkeypatch.delenv("ZINNIA_PRESENTON_TEMPLATE_ID", raising=False)
    with patch("app.services.presenton_client.generate_presentation") as gen:
        with patch(
            "app.services.phases.llm_phase._chat",
            return_value={"ok": False, "error": "offline", "content": ""},
        ):
            out = PresentationService().generate(
                PresentationGenerateRequest(
                    content="Status",
                    n_slides=4,
                    ui_template_choice="zinnia-executive-v1",
                    user_id="u1",
                )
            )
        gen.assert_not_called()
    assert out["ok"] is False
    assert out["http_status"] == 409
    assert out["zinnia_verified"] is False
    assert out["lifecycle"] == tmpl.LIFECYCLE_TEMPLATE_NOT_READY


def test_render_plan_round_trip_notes(tmp_path):
    plan = {
        "slides": [
            {
                "index": 0,
                "title": "Status",
                "content_blocks": [{"kind": "bullet", "text": "On track"}],
                "layout_intent": "title_body",
                "notes_intent": "Say we are on track this week.",
                "visual_intent": "none",
            },
            {
                "index": 1,
                "title": "Ask",
                "content_blocks": [{"kind": "bullet", "text": "Approve owners"}],
                "layout_intent": "closing",
                "notes_intent": "Ask for a decision on owners.",
                "visual_intent": "none",
            },
            {
                "index": 2,
                "title": "Risks",
                "content_blocks": [{"kind": "bullet", "text": "Staffing"}],
                "layout_intent": "title_body",
                "notes_intent": "Cover staffing risk.",
                "visual_intent": "none",
            },
        ]
    }
    data = render_plan_to_pptx(plan)
    slides = parse_pptx_bytes(data)
    assert len(slides) == 3
    assert "on track" in (slides[0].get("notes") or "").lower()


def test_corrupt_master_does_not_claim_zinnia_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_PRESENTATION_PROVIDER", "zect_native")
    monkeypatch.setattr(
        "app.services.mentrix.presentation.native_provider.default_pptx_save_dir",
        lambda: tmp_path,
    )
    imported = tmpl.import_canonical_master(
        "zinnia-executive-v1",
        make_master_pptx_bytes(),
        name="Zinnia Executive",
        filename="exec.pptx",
    )
    assert imported["native_ready"] is True
    master = tmpl.source_pptx_path("zinnia-executive-v1", user_id="u1")
    assert master is not None
    master.write_bytes(b"PK\x03\x04not-a-real-pptx")
    with patch("app.services.phases.llm_phase._chat", return_value={"ok": False, "error": "offline", "content": ""}):
        out = PresentationService().generate(
            PresentationGenerateRequest(
                content="Q3 delivery status",
                n_slides=4,
                ui_template_choice="zinnia-executive-v1",
                user_id="u1",
            )
        )
    assert out["ok"] is False
    assert out["zinnia_verified"] is False
    assert out["http_status"] == 502
