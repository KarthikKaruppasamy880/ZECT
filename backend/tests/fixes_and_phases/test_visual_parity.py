"""S6.5 visual-content parity: blocks, charts, tables, images, overflow, no Presenton."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.services.mentrix.presentation import template_registry as tmpl
from app.services.mentrix.presentation.asset_resolver import example_png_bytes, store_image
from app.services.mentrix.presentation.blocks import example_chart_block, example_table_block, normalize_block
from app.services.mentrix.presentation.document import inspect_pptx_visuals
from app.services.mentrix.presentation.document_io import apply_document_to_pptx
from app.services.mentrix.presentation.plan import validate_plan
from app.services.mentrix.presentation.provider import PresentationGenerateRequest
from app.services.mentrix.presentation.renderer import render_plan_to_pptx, validate_generated_pptx
from app.services.mentrix.presentation.service import PresentationService
from app.services.pptx_parse import parse_pptx_bytes
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes


def _visual_plan(*, image_asset: str = "") -> dict:
    image = normalize_block(
        {
            "kind": "image",
            "content": {"asset_id": image_asset, "alt": "Example figure", "caption": "Example image"},
            "provenance": {"source": "upload" if image_asset else "example", "generated": not bool(image_asset)},
        },
        slide_index=1,
        ordinal=0,
    )
    return {
        "objective": "Visual parity brief",
        "audience_id": "executive",
        "narrative": "Status then metrics",
        "n_slides": 4,
        "slides": [
            {
                "title": "Title",
                "content_blocks": [{"kind": "bullet", "text": "Opening"}],
                "layout_intent": "title",
                "notes_intent": "Welcome the room.",
                "visual_intent": "none",
            },
            {
                "title": "Figure",
                "content_blocks": [{"kind": "bullet", "text": "Authorized figure"}],
                "blocks": [image],
                "layout_intent": "text_image",
                "visual_intent": "image",
                "notes_intent": "Describe the figure.",
            },
            {
                "title": "Metrics",
                "content_blocks": [{"kind": "bullet", "text": "Trend is illustrative"}],
                "blocks": [example_chart_block(2, 0)],
                "layout_intent": "chart_commentary",
                "visual_intent": "chart",
                "notes_intent": "Call the example trend, not a forecast.",
            },
            {
                "title": "Workstreams",
                "content_blocks": [{"kind": "bullet", "text": "Status table"}],
                "blocks": [example_table_block(3, 0)],
                "layout_intent": "table",
                "visual_intent": "table",
                "notes_intent": "Walk the table left to right.",
            },
        ],
    }


def test_plan_normalizes_typed_blocks():
    plan = validate_plan(_visual_plan(), n_slides=4, template_id="zinnia-executive-v1", audience_id="executive")
    kinds = {b["kind"] for s in plan["slides"] for b in s.get("blocks") or []}
    assert "chart" in kinds
    assert "table" in kinds
    assert "image" in kinds


def test_render_chart_table_image_into_pptx(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path / "assets"))
    meta = store_image(example_png_bytes(label="parity"), user_id="u1", filename="fig.png")
    plan = validate_plan(
        _visual_plan(image_asset=meta["asset_id"]),
        n_slides=4,
        template_id="",
        audience_id="executive",
    )
    data = render_plan_to_pptx(plan, user_id="u1")
    validate_generated_pptx(data, n_slides=4)
    visuals = inspect_pptx_visuals(data)
    assert visuals["has_chart"] is True
    assert visuals["has_image"] is True
    assert visuals["has_table"] is True
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = [i.filename.replace("\\", "/") for i in zf.infolist()]
    assert any(n.startswith("ppt/charts/") for n in names)
    assert any(n.startswith("ppt/media/") for n in names)
    slides = parse_pptx_bytes(data)
    blob = " ".join(f"{s.get('text') or ''} {s.get('notes') or ''}" for s in slides).lower()
    assert "workstream" in blob or "example" in blob or "illustrative" in blob
    dest = tmp_path / "visual.pptx"
    dest.write_bytes(data)
    for block in plan["slides"][2].get("blocks") or []:
        if block.get("kind") == "chart":
            block["content"]["title"] = "Updated example chart"
    doc_slides = [
        {
            "index": i,
            "text": s["title"],
            "notes": s.get("notes_intent") or "",
            "blocks": s.get("blocks") or [],
        }
        for i, s in enumerate(plan["slides"])
    ]
    out = apply_document_to_pptx(dest, doc_slides, user_id="u1")
    assert out["ok"] is True
    again = inspect_pptx_visuals(dest.read_bytes())
    assert again["has_chart"] is True
    assert again["has_image"] is True


def test_table_too_large_is_truncated_not_silent(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path / "assets"))
    rows = [[f"r{i}", "x"] for i in range(30)]
    block = normalize_block(
        {"kind": "table", "content": {"headers": ["A", "B"], "rows": rows}},
        slide_index=0,
        ordinal=0,
    )
    assert block is not None
    errors = " ".join(block["validation"]["errors"])
    assert "table_too_large" in errors or "table_truncated" in errors
    assert len(block["content"]["rows"]) <= 12


def test_image_url_block_rejected():
    block = normalize_block(
        {"kind": "image", "content": {"url": "https://evil.example/x.png", "asset_id": ""}},
        slide_index=0,
        ordinal=0,
    )
    assert block is not None
    assert "image_url_rejected" in block["validation"]["errors"]
    assert block["validation"]["ok"] is False


def test_native_visual_generate_zero_presenton(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PRESENT_TEMPLATE_ROOT", str(tmp_path / "templates"))
    monkeypatch.setenv("ZECT_PRESENT_ASSET_ROOT", str(tmp_path / "assets"))
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
    meta = store_image(example_png_bytes(), user_id="u1", filename="fig.png")
    with patch("app.services.presenton_client.generate_presentation") as gen:
        with patch("app.services.phases.llm_phase._chat", return_value={"ok": False, "error": "offline", "content": ""}):
            out = PresentationService().generate(
                PresentationGenerateRequest(
                    content="Executive update with metrics chart, status table, and an image figure",
                    n_slides=6,
                    ui_template_choice="zinnia-executive-v1",
                    filename="s65.pptx",
                    user_id="u1",
                    asset_ids=[meta["asset_id"]],
                )
            )
        gen.assert_not_called()
    assert out["ok"] is True
    assert out["zinnia_verified"] is True
    data = Path(out["path"]).read_bytes()
    visuals = inspect_pptx_visuals(data)
    assert visuals["has_chart"] is True
    assert visuals["has_table"] is True
    assert visuals["has_image"] is True
    inventory = out.get("visual_inventory") or {}
    assert inventory.get("chart", 0) >= 1
    assert inventory.get("table", 0) >= 1
