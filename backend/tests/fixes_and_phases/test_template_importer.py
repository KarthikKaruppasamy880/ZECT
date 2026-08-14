"""Secure PPTX importer — zip bombs, traversal, symlink, theme/master parse."""

from __future__ import annotations

import io
import zipfile

import pytest

from app.services.mentrix.presentation.template_definition import load_definition, native_ready, public_definition
from app.services.mentrix.presentation.template_importer import UnsafePptxError, import_pptx_bytes, inspect_pptx_archive
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes


def test_import_master_pptx_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    out = import_pptx_bytes(
        make_master_pptx_bytes(),
        zect_id="zinnia-executive-v1",
        scope="ZINNIA",
        name="Zinnia Executive",
        source_filename="exec.pptx",
    )
    assert out["ok"] is True
    row = out["definition"]
    assert row["ready"] is True
    assert row["theme"]["fonts"]["major"] == "Calibri"
    assert row["theme"]["colors"]["accent1"] == "FF7500"
    assert any(lay["name"] == "Title and Content" for lay in row["layouts"])
    assert native_ready("zinnia-executive-v1") is True
    pub = public_definition(load_definition("zinnia-executive-v1") or {})
    assert pub["provider_uuid_hidden"] is True
    assert "presenton-master" not in str(pub)


def test_reject_non_zip(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    with pytest.raises(UnsafePptxError, match="not_a_pptx_zip"):
        import_pptx_bytes(b"not-a-zip", zect_id="user-x", scope="USER")


def test_reject_zip_slip(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.xml", "<x/>")
    with pytest.raises(UnsafePptxError, match="zip_path_traversal"):
        inspect_pptx_archive(buf.getvalue())


def test_reject_zip_bomb_ratio(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("ppt/presentation.xml", b"x")
        zf.filelist[-1].file_size = 90 * 1024 * 1024
        zf.filelist[-1].compress_size = 1
    with pytest.raises(UnsafePptxError, match="zip_member_too_large|zip_bomb"):
        inspect_pptx_archive(buf.getvalue())


def test_reject_symlink_attr(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("ppt/presentation.xml")
        info.external_attr = 0xA0000000
        zf.writestr(info, b"<p/>")
    with pytest.raises(UnsafePptxError, match="zip_symlink_rejected"):
        inspect_pptx_archive(buf.getvalue())
