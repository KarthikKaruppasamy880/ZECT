"""S6 re-prove on native opt-in: Zinnia + user template, no Presenton calls."""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from starlette.datastructures import Headers, UploadFile

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.provider import PresentationGenerateRequest
from app.services.mentrix.presentation.renderer import validate_generated_pptx
from app.services.mentrix.presentation.service import PresentationService
from app.services.pptx_parse import parse_pptx_bytes
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes


def _native_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path / "templates"))
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path / "assets"))
    monkeypatch.setenv("ZECT_PRESENTATION_PROVIDER", "zect_native")
    monkeypatch.setattr(
        "app.services.mentrix.presentation.native_provider.default_pptx_save_dir",
        lambda: tmp_path,
    )


def test_s6_zinnia_native_generate_editor_roundtrip_no_presenton(tmp_path, monkeypatch):
    _native_env(tmp_path, monkeypatch)
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
                    filename="s6-zinnia.pptx",
                    user_id="u-s6",
                )
            )
        gen.assert_not_called()
    assert out["ok"] is True
    assert out["provider"] == "zect_native"
    assert out["zinnia_verified"] is True
    path = Path(out["path"])
    data = path.read_bytes()
    validate_generated_pptx(data, n_slides=4)
    from app.services.mentrix.presentation.document import document_from_pptx_bytes
    from app.services.mentrix.presentation.document_io import apply_document_to_pptx

    doc = document_from_pptx_bytes(data, path=str(path), provider="zect_native")
    doc["slides"][0]["notes"] = "S6 native notes: owners this week."
    doc["slides"][0]["text"] = "Status\nOn track"
    applied = apply_document_to_pptx(path, doc["slides"], user_id="u-s6")
    assert applied["ooxml_roundtrip"] is True
    slides = parse_pptx_bytes(path.read_bytes())
    assert "owners this week" in (slides[0].get("notes") or "").lower()


def test_s6_user_template_native_generate_no_presenton(tmp_path, monkeypatch):
    _native_env(tmp_path, monkeypatch)

    async def _register():
        upload = UploadFile(
            filename="user.pptx",
            file=BytesIO(make_master_pptx_bytes()),
            headers=Headers({"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}),
        )
        return await tmpl.register_user_pptx("u-s6", upload, name="User Exec", scope="USER")

    row = asyncio.run(_register())
    assert row.get("ok") is True
    tid = row["template"]["id"]
    assert str(tid).startswith("user-")
    with patch("app.services.presenton_client.generate_presentation") as gen:
        with patch("app.services.phases.llm_phase._chat", return_value={"ok": False, "error": "offline", "content": ""}):
            out = PresentationService().generate(
                PresentationGenerateRequest(
                    content="User template status brief",
                    n_slides=3,
                    ui_template_choice=tid,
                    filename="s6-user.pptx",
                    user_id="u-s6",
                )
            )
        gen.assert_not_called()
    assert out["ok"] is True, out
    assert out["provider"] == "zect_native"
    assert out["zinnia_verified"] is False
    path = Path(out["path"])
    assert path.is_file()
    validate_generated_pptx(path.read_bytes(), n_slides=3)
    assert parse_pptx_bytes(path.read_bytes())
