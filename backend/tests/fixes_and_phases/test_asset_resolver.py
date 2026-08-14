"""S6.5 AssetResolver — MIME, bombs, SVG, URLs, ownership."""

from __future__ import annotations

import pytest

from app.services.mentrix.presentation.asset_resolver import (
    UnsafeImageError,
    example_png_bytes,
    load_image,
    store_example_image,
    store_image,
)


def test_store_and_load_png(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path))
    meta = store_image(example_png_bytes(), user_id="u1", filename="ok.png", mime="image/png")
    assert meta["ok"] is True
    assert meta["asset_id"]
    loaded = load_image(meta["asset_id"], user_id="u1")
    assert loaded["bytes"][:8] == b"\x89PNG\r\n\x1a\n"


def test_svg_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path))
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
    with pytest.raises(UnsafeImageError, match="svg_or_active"):
        store_image(svg, user_id="u1", filename="x.svg", mime="image/svg+xml")


def test_url_filename_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path))
    with pytest.raises(UnsafeImageError, match="image_url_rejected"):
        store_image(example_png_bytes(), user_id="u1", filename="https://evil.example/x.png")


def test_html_polyglot_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path))
    with pytest.raises(UnsafeImageError):
        store_image(b"<!DOCTYPE html><html><script>alert(1)</script>", user_id="u1", filename="x.png", mime="image/png")


def test_too_large_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path))
    with pytest.raises(UnsafeImageError, match="image_too_large"):
        store_image(b"\x89PNG\r\n\x1a\n" + b"A" * (9 * 1024 * 1024), user_id="u1", filename="big.png")


def test_cross_user_denied(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path))
    meta = store_example_image(user_id="owner", label="secret")
    with pytest.raises(FileNotFoundError):
        load_image(meta["asset_id"], user_id="other")
