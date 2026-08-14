"""S6: native generate must not depend on Voicebox/TTS."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.provider import PresentationGenerateRequest
from app.services.mentrix.presentation.service import PresentationService
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes

NATIVE = Path(__file__).resolve().parents[2] / "app" / "services" / "mentrix" / "presentation" / "native_provider.py"


def test_native_generate_does_not_call_voicebox(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_PRESENTATION_PROVIDER", "zect_native")
    monkeypatch.setattr(
        "app.services.mentrix.presentation.native_provider.default_pptx_save_dir",
        lambda: tmp_path,
    )
    tmpl.import_canonical_master(
        "zinnia-executive-v1",
        make_master_pptx_bytes(),
        name="Zinnia Executive",
        filename="exec.pptx",
    )
    with patch("app.services.phases.llm_phase._chat", return_value={"ok": False, "error": "offline", "content": ""}):
        out = PresentationService().generate(
            PresentationGenerateRequest(
                content="Delivery status",
                n_slides=3,
                ui_template_choice="zinnia-executive-v1",
                filename="s6.pptx",
                user_id="u1",
            )
        )
    assert out["ok"] is True
    assert Path(out["path"]).is_file()
    assert out["zinnia_verified"] is True
    text = NATIVE.read_text(encoding="utf-8")
    assert "voicebox" not in text.lower()
    assert "chatterbox" not in text.lower()
    assert "speakMentrix" not in text
