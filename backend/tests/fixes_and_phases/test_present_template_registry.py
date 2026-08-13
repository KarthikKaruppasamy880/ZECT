"""Presentation template registry + API smoke."""

from __future__ import annotations

from io import BytesIO

from fastapi import UploadFile

from app.services.mentrix.presentation import template_registry as tmpl


def test_list_includes_zinnia(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    out = tmpl.list_templates("u1")
    assert out["ok"] is True
    ids = {t["id"] for t in out["zinnia"]}
    assert "zinnia-exec" in ids
    assert out["my_templates"] == []


def test_register_and_preview_user_pptx(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))

    async def _run():
        upload = UploadFile(filename="master.pptx", file=BytesIO(b"PK\x03\x04fake-pptx"))
        reg = await tmpl.register_user_pptx("u1", upload, name="My Master")
        assert reg["ok"] is True
        tid = reg["template"]["id"]
        listed = tmpl.list_templates("u1")
        assert any(t["id"] == tid for t in listed["my_templates"])
        prev = tmpl.preview_template("u1", tid)
        assert prev["ok"] is True
        assert prev["provider_uuid_hidden"] is True
        # Isolation: other user cannot see
        other = tmpl.list_templates("u2")
        assert other["my_templates"] == []

    import asyncio

    asyncio.run(_run())
