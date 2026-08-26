"""Exact slide-count constraint — regression for gates D/E."""

from __future__ import annotations

import pytest

from app.services.mentrix.presentation.plan import MIN_SLIDES, MAX_SLIDES, clamp_slide_count, empty_plan, validate_plan


@pytest.mark.parametrize("requested,expected", [(1, 1), (3, 3), (6, 6), (20, 20), (0, 1), (25, 20), (None, 6)])
def test_clamp_slide_count_exact(requested: int | None, expected: int) -> None:
    assert clamp_slide_count(requested) == expected


def test_min_slides_is_one() -> None:
    assert MIN_SLIDES == 1
    assert MAX_SLIDES == 20


def test_empty_plan_respects_requested_count() -> None:
    for n in (1, 3, 6, 20):
        plan = empty_plan(n_slides=n)
        assert plan["n_slides"] == n


def test_validate_plan_ignores_llm_n_slides_override() -> None:
    """LLM returning n_slides=6 must not override user requested_slide_count=3."""
    raw = {
        "objective": "Agentic AI deck",
        "n_slides": 6,
        "slides": [{"title": f"S{i}", "purpose": "body", "key_message": f"K{i}"} for i in range(6)],
    }
    plan = validate_plan(raw, n_slides=3, requested_slide_count=3, template_id="zinnia-executive-v1", audience_id="general")
    assert plan["requested_slide_count"] == 3
    assert plan["n_slides"] == 3
    assert len(plan["slides"]) == 3
    assert plan.get("llm_n_slides_ignored") == 6


def test_enforce_slide_count_contract_caps_repair_expansion() -> None:
    from app.services.mentrix.presentation.generation_job import enforce_slide_count_contract

    plan = {
        "requested_slide_count": 3,
        "n_slides": 6,
        "slides": [{"index": i, "title": f"S{i}"} for i in range(6)],
    }
    fixed, violations = enforce_slide_count_contract(plan)
    assert len(fixed["slides"]) == 3
    assert fixed["n_slides"] == 3
    assert violations


def test_validate_plan_does_not_expand_slide_count() -> None:
    raw = {
        "objective": "Test deck",
        "n_slides": 3,
        "slides": [
            {"title": "A", "purpose": "opening", "key_message": "One"},
            {"title": "B", "purpose": "body", "key_message": "Two"},
            {"title": "C", "purpose": "closing", "key_message": "Three"},
        ],
    }
    plan = validate_plan(raw, n_slides=3, template_id="zinnia-executive-v1", audience_id="general")
    assert plan["n_slides"] == 3
    assert len(plan["slides"]) == 3


def test_blank_deck_sidecar_has_editable_blocks(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pptx_paths.default_pptx_save_dir",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "app.services.pptx_paths._under_allowlist",
        lambda _p: True,
    )
    from app.services.mentrix.presentation.deck_catalog import create_blank_pptx
    from app.services.pptx_parse import parse_pptx_bytes
    from app.services.pptx_paths import notes_sidecar_for_pptx
    from app.services.mentrix.presentation.document import merge_sidecar_slides
    import json

    dest = create_blank_pptx()
    assert dest.is_file()
    sidecar = notes_sidecar_for_pptx(dest)
    assert sidecar.is_file()
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload.get("kind") == "presentation_document"
    blocks = payload["slides"][0]["blocks"]
    assert len(blocks) >= 2
    parsed = parse_pptx_bytes(dest.read_bytes())
    merged = merge_sidecar_slides(parsed, payload["slides"])
    assert len(merged[0]["blocks"]) >= 2
    kinds = {b.get("kind") for b in merged[0]["blocks"]}
    assert "text" in kinds
    assert "shape" in kinds
    sidecar_text = json.dumps(payload).lower()
    assert "add content with insert" not in sidecar_text
    assert "drag to move" not in sidecar_text
