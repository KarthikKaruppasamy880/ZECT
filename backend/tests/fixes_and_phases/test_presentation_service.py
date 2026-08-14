"""PresentationService — Presenton default; native generate is a stub that never calls Presenton."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.services.mentrix.presentation.native_provider import ZectNativePresentationProvider
from app.services.mentrix.presentation.provider import PresentationGenerateRequest
from app.services.mentrix.presentation.service import (
    DEFAULT_PROVIDER,
    PresentationService,
    configured_provider_name,
    get_provider,
)
from app.services.mentrix.presentation.template_importer import import_pptx_bytes
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes


def test_default_provider_is_presenton(monkeypatch):
    monkeypatch.delenv("ZECT_PRESENTATION_PROVIDER", raising=False)
    assert DEFAULT_PROVIDER == "presenton"
    assert configured_provider_name() == "presenton"
    assert get_provider().name == "presenton"


def test_native_env_selects_stub(monkeypatch):
    monkeypatch.setenv("ZECT_PRESENTATION_PROVIDER", "zect_native")
    assert configured_provider_name() == "zect_native"
    assert get_provider().name == "zect_native"


def test_native_generate_does_not_call_presenton(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_PRESENTATION_PROVIDER", "zect_native")
    monkeypatch.setattr(
        "app.services.mentrix.presentation.native_provider.default_pptx_save_dir",
        lambda: tmp_path,
    )
    import_pptx_bytes(
        make_master_pptx_bytes(),
        zect_id="zinnia-executive-v1",
        scope="ZINNIA",
        name="Zinnia Executive",
    )
    with patch("app.services.presenton_client.generate_presentation") as gen:
        with patch("app.services.phases.llm_phase._chat", return_value={"ok": False, "error": "offline", "content": ""}):
            out = PresentationService().generate(
                PresentationGenerateRequest(
                    content="Q3 delivery status",
                    n_slides=6,
                    ui_template_choice="zinnia-executive-v1",
                    user_id="u1",
                )
            )
        gen.assert_not_called()
    assert out["ok"] is True
    assert out["provider"] == "zect_native"
    assert Path(out["path"]).is_file()


def test_native_status_does_not_call_presenton(monkeypatch):
    monkeypatch.setenv("ZECT_PRESENTATION_PROVIDER", "zect_native")
    with patch("app.services.presenton_client.list_templates") as listed:
        st = ZectNativePresentationProvider().status(user_id="u1")
        listed.assert_not_called()
    assert st.provider == "zect_native"
    assert st.configured is True
