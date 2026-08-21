"""Presenter intelligence + builtin template delete."""

import json

from app.services.mentrix.presentation.presenter_intelligence import grounded_slide_script, narrate_slides
from app.services.mentrix.presentation.template_registry import delete_uploaded_template, delete_unmapped_uploads


def test_grounded_script_does_not_invent_numbers():
    script = grounded_slide_script(
        {"notes": "Status is green.", "text": "Q3", "visuals": ["chart"]},
        deck_context="ZOAS delivery",
        slide_index=0,
        slide_count=2,
    )
    assert "Slide 1 of 2" in script
    assert "invent" in script.lower() or "chart" in script.lower()
    assert "42%" not in script


def test_narrate_slides_word_budget():
    long_notes = "word " * 400
    out = narrate_slides([{"index": 0, "notes": long_notes, "text": "", "visuals": []}])
    assert out["ok"] is True
    assert out["slides"][0]["word_count"] <= 220


def test_cannot_delete_org_builtin(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    out = delete_uploaded_template("u1", "org-standard")
    assert out["ok"] is False
    assert out["error"] == "cannot_delete_builtin"


def test_delete_unmapped_skips_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    # empty registry — still ok
    out = delete_unmapped_uploads("u1")
    assert out["ok"] is True
    assert out["count"] == 0


def test_delete_unmapped_uploads_only(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    user_dir = tmp_path / "user-u1"
    user_dir.mkdir()
    (user_dir / "registry.json").write_text(
            json.dumps(
            {
                "templates": [
                    {"id": "user-dead", "native_ready": False, "path": str(tmp_path / "gone.pptx")},
                    {"id": "user-ok", "native_ready": True},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = delete_unmapped_uploads("u1")
    assert out["ok"] is True
    assert "user-dead" in out["deleted"]
    assert "user-ok" not in out["deleted"]
