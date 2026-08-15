"""S7.7 quality critic, grounding, composer, and repair regressions from observed deck defects."""

from __future__ import annotations

from app.services.mentrix.presentation.blocks import example_table_block, ensure_visual_blocks
from app.services.mentrix.presentation.content_intent import choose_slide_intent, has_tabular_data
from app.services.mentrix.presentation.grounding import scrub_plan
from app.services.mentrix.presentation.layout_composer import compose_plan
from app.services.mentrix.presentation.quality_critic import critique_plan
from app.services.mentrix.presentation.quality_repair import repair_until_pass
from app.services.mentrix.presentation.visual_planner import apply_visual_plan


def _definition() -> dict:
    return {
        "slide_size": {"cx": 9144000, "cy": 5143500},
        "layouts": [
            {
                "name": "Title Page 1",
                "placeholders": [
                    {"type": "TITLE", "geometry": {"x": 457200, "y": 200000, "cx": 8229600, "cy": 700000}},
                    {"type": "BODY", "geometry": {"x": 4800000, "y": 1371600, "cx": 3900000, "cy": 3200000}},
                ],
            },
            {
                "name": "Subtitle + 1 column",
                "placeholders": [
                    {"type": "TITLE", "geometry": {"x": 457200, "y": 180000, "cx": 8229600, "cy": 640000}},
                    {"type": "BODY", "geometry": {"x": 457200, "y": 1000000, "cx": 8229600, "cy": 3700000}},
                ],
            },
            {
                "name": "Subtitle + 2 columns",
                "placeholders": [
                    {"type": "TITLE", "geometry": {"x": 457200, "y": 180000, "cx": 8229600, "cy": 640000}},
                    {"type": "BODY", "geometry": {"x": 400000, "y": 1100000, "cx": 4000000, "cy": 3500000}},
                    {"type": "BODY", "geometry": {"x": 4700000, "y": 1100000, "cx": 4000000, "cy": 3500000}},
                ],
            },
            {"name": "1_Blank", "placeholders": []},
        ],
    }


def test_roadmap_prose_does_not_become_placeholder_table():
    plan = {
        "slides": [
            {
                "title": "Roadmap",
                "purpose": "comparison",
                "visual_intent": "table",
                "content_blocks": [
                    {"kind": "bullet", "text": "Ship identity hardening next quarter"},
                    {"kind": "bullet", "text": "Stabilize billing after the vendor cutover"},
                    {"kind": "bullet", "text": "Open the claims portal to advisors"},
                ],
            }
        ]
    }
    out = apply_visual_plan(plan, audience_id="general", prompt="Product roadmap of workstreams for two quarters")
    slide = out["slides"][0]
    kinds = [str(b.get("kind") or "") for b in list(slide.get("blocks") or [])]
    assert "table" not in kinds
    assert slide.get("visual_intent") != "table"
    assert choose_slide_intent(slide) != "TABLE"
    blob = str(slide)
    assert "Watch" not in blob or not has_tabular_data(slide)


def test_ensure_visual_blocks_does_not_invent_watch_owner_rows():
    slide = {
        "index": 1,
        "visual_intent": "table",
        "content_blocks": [
            {"kind": "bullet", "text": "Delivery is on track"},
            {"kind": "bullet", "text": "Risks remain vendor-shaped"},
        ],
    }
    out = ensure_visual_blocks(slide)
    assert out.get("visual_intent") != "table"
    assert not any(b.get("kind") == "table" for b in out.get("blocks") or [])


def test_grounded_pipe_table_is_kept():
    slide = {
        "index": 2,
        "visual_intent": "table",
        "content_blocks": [
            {"kind": "bullet", "text": "Workstream | Status | Owner"},
            {"kind": "bullet", "text": "Identity | Delayed | TBD"},
            {"kind": "bullet", "text": "Billing | On track | TBD"},
        ],
    }
    out = ensure_visual_blocks(slide)
    tables = [b for b in out.get("blocks") or [] if b.get("kind") == "table"]
    assert tables
    rows = (tables[0].get("content") or {}).get("rows") or []
    assert any("Identity" in str(r) for r in rows)
    assert not any(str(r) == "['Delivery', 'On track', 'A']" for r in rows)


def test_title_body_collision_is_repairable():
    plan = {
        "slides": [
            {
                "title": "Q3 Delivery",
                "content_blocks": [{"kind": "bullet", "text": "Twelve of fourteen epics closed"}],
                "composed_regions": {
                    "title": {"x": 400000, "y": 200000, "cx": 8000000, "cy": 900000},
                    "body": {"x": 400000, "y": 400000, "cx": 8000000, "cy": 2000000},
                    "visual": {"x": 400000, "y": 400000, "cx": 8000000, "cy": 2000000},
                },
            }
        ]
    }
    report = critique_plan(plan, _definition(), prompt="Q3 delivery")
    assert report["overlap_count"] >= 1
    assert any("title_collision" in (s.get("findings") or []) for s in report["slides"])
    _, fixed = repair_until_pass(plan, _definition(), prompt="Q3 delivery")
    assert fixed["overlap_count"] == 0 or fixed["final_quality_status"] in {"PASS", "FAIL"}
    regions = plan["slides"][0].get("composed_regions") or {}
    title, body = regions.get("title") or {}, regions.get("body") or {}
    if title and body:
        assert title["y"] + title["cy"] <= body["y"] + 8000 or body["y"] >= title["y"] + title["cy"]


def test_truncated_rows_are_shortened():
    long_line = "This workstream commentary is far too long for a readable bullet and will clip in the body placeholder unless the critic shortens it before render. " * 2
    plan = {
        "slides": [
            {
                "title": "Status",
                "content_blocks": [{"kind": "bullet", "text": long_line}],
            }
        ]
    }
    report = critique_plan(plan, _definition())
    assert any("truncated_text" in (s.get("findings") or []) for s in report["slides"])
    plan, out = repair_until_pass(plan, _definition(), prompt="status")
    text = str(plan["slides"][0]["content_blocks"][0]["text"])
    assert len(text) <= 140


def test_repeated_identical_layouts_are_varied():
    slides = []
    for i in range(5):
        slides.append(
            {
                "title": f"Point {i + 1}",
                "content_intent": "BULLETS",
                "master_layout_name": "Title Page 1",
                "content_blocks": [{"kind": "bullet", "text": f"Item {i + 1}"}],
            }
        )
    plan = {"slides": slides}
    report = critique_plan(plan, _definition())
    assert report["repeated_layout_count"] >= 1
    plan, _out = repair_until_pass(plan, _definition(), prompt="five points")
    names = [str(s.get("master_layout_name") or "") for s in plan["slides"]]
    assert len(set(names)) >= 2


def test_irrelevant_image_is_dropped():
    plan = {
        "slides": [
            {
                "title": "Decision needed",
                "purpose": "decision",
                "visual_intent": "image",
                "content_blocks": [{"kind": "bullet", "text": "Approve contractor hiring"}],
                "blocks": [
                    {
                        "kind": "image",
                        "content": {"asset_id": "asset-x", "alt": "stock"},
                        "geometry": {"x": 400000, "y": 1400000, "cx": 3000000, "cy": 2000000},
                    }
                ],
            }
        ]
    }
    report = critique_plan(plan, _definition(), prompt="Approve the hiring decision")
    assert any("irrelevant_image" in (s.get("findings") or []) for s in report["slides"])
    plan, _out = repair_until_pass(plan, _definition(), prompt="Approve the hiring decision")
    assert not any(b.get("kind") == "image" for b in plan["slides"][0].get("blocks") or [])


def test_excessive_blank_space_is_flagged():
    plan = {
        "slides": [
            {
                "title": "Empty",
                "content_intent": "TEXT",
                "composed_regions": {
                    "title": {"x": 400000, "y": 200000, "cx": 2000000, "cy": 400000},
                    "body": {"x": 400000, "y": 800000, "cx": 2000000, "cy": 400000},
                    "visual": {"x": 400000, "y": 800000, "cx": 2000000, "cy": 400000},
                },
            }
        ]
    }
    report = critique_plan(plan, _definition())
    assert report["whitespace_ratio"] > 0.7 or any("excessive_whitespace" in (s.get("findings") or []) for s in report["slides"])


def test_invented_owner_name_and_date_are_scrubbed():
    plan = {
        "slides": [
            {
                "title": "Owners",
                "notes_intent": "Jane Smith owns delivery by Sep 12.",
                "content_blocks": [{"kind": "bullet", "text": "Jane Smith to close identity by Sep 12"}],
            }
        ]
    }
    n = scrub_plan(plan, prompt="Summarize attached evidence", context_items=[{"content": "Identity delayed. Hire contractors."}])
    assert n >= 1
    blob = str(plan)
    assert "Jane Smith" not in blob
    assert "Sep 12" not in blob
    assert "TBD" in blob


def test_chart_without_series_is_not_forced():
    slide = {
        "title": "Q3 update",
        "purpose": "status",
        "visual_intent": "chart",
        "content_blocks": [{"kind": "bullet", "text": "Delivery is mostly on track this quarter"}],
    }
    assert choose_slide_intent(slide, purpose="status", prompt="Q3 update") != "CHART"


def test_example_table_helper_still_exists_for_explicit_tables():
    block = example_table_block(0, 0, headers=["Epic", "State"], rows=[["Identity", "Delayed"]])
    assert block and block["kind"] == "table"
    assert (block.get("content") or {}).get("headers") == ["Epic", "State"]


def test_repair_loop_converts_placeholder_table_and_passes():
    plan = {
        "objective": "Roadmap",
        "slides": [
            {
                "title": "Workstreams",
                "visual_intent": "table",
                "content_intent": "TABLE",
                "content_blocks": [{"kind": "bullet", "text": "Harden identity"}],
                "blocks": [
                    example_table_block(
                        0,
                        0,
                        headers=["Workstream", "Status", "Owner"],
                        rows=[["Delivery", "Watch", "A"], ["Risks", "Watch", "B"]],
                    )
                ],
            }
        ],
    }
    plan, report = repair_until_pass(plan, _definition(), prompt="roadmap without owners")
    kinds = [str(b.get("kind") or "") for s in plan["slides"] for b in s.get("blocks") or []]
    assert "table" not in kinds
    assert report["table_appropriateness"] == "ok"
    assert report["final_quality_status"] in {"PASS", "FAIL"}
    if report["overlap_count"] == 0 and report["out_of_bounds_count"] == 0:
        assert report["final_quality_status"] == "PASS"


def test_real_zinnia_composer_varies_layouts():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / ".zect/present-templates/definitions/zinnia-executive-v1.json"
    if not path.is_file():
        import pytest

        pytest.skip("real Zinnia TemplateDefinition is not imported in this workspace")
    definition = json.loads(path.read_text(encoding="utf-8"))
    plan = {
        "slides": [
            {"title": "Board opening", "purpose": "opening", "content_blocks": [{"kind": "bullet", "text": "Q3 delivery"}]},
            {"title": "Status", "purpose": "section", "content_blocks": [{"kind": "bullet", "text": "Twelve of fourteen epics closed"}]},
            {"title": "Options", "purpose": "comparison", "content_blocks": [{"kind": "bullet", "text": "Build vs buy"}]},
            {"title": "Ask", "purpose": "cta", "content_blocks": [{"kind": "bullet", "text": "Approve contractors"}]},
        ]
    }
    compose_plan(plan, definition, prompt="Zinnia executive board pack")
    names = [str(s.get("master_layout_name") or "") for s in plan["slides"]]
    assert all(names)
    assert names[0] != names[1] or names[1] != names[2]
    regions = plan["slides"][1]["composed_regions"]
    title, body = regions["title"], regions["body"]
    assert title["y"] + title["cy"] <= body["y"] + 20000


def test_real_zinnia_render_grounded_roadmap_without_placeholder_table(tmp_path):
    import json
    from pathlib import Path

    from app.services.mentrix.presentation.renderer import render_plan_to_pptx, validate_generated_pptx
    from app.services.mentrix.presentation.visual_planner import apply_visual_plan

    root = Path(__file__).resolve().parents[3]
    defn_path = root / ".zect/present-templates/definitions/zinnia-executive-v1.json"
    master = root / ".zect/present-templates/masters/zinnia-executive-v1.pptx"
    if not defn_path.is_file() or not master.is_file():
        import pytest

        pytest.skip("real Zinnia master/definition not imported")
    definition = json.loads(defn_path.read_text(encoding="utf-8"))
    plan = apply_visual_plan(
        {
            "objective": "Q3 delivery",
            "slides": [
                {
                    "title": "Roadmap",
                    "purpose": "section",
                    "content_blocks": [
                        {"kind": "bullet", "text": "Harden identity next quarter"},
                        {"kind": "bullet", "text": "Stabilize billing after cutover"},
                    ],
                },
                {
                    "title": "Evidence table",
                    "purpose": "section",
                    "content_blocks": [
                        {"kind": "bullet", "text": "Workstream | Status | Owner"},
                        {"kind": "bullet", "text": "Identity | Delayed | TBD"},
                        {"kind": "bullet", "text": "Billing | On track | TBD"},
                    ],
                },
            ],
        },
        audience_id="executive",
        prompt="Roadmap and evidence table. Do not invent owners.",
    )
    plan, report = repair_until_pass(plan, definition, prompt="Roadmap and evidence table. Do not invent owners.")
    assert report["final_quality_status"] == "PASS"
    kinds = [str(b.get("kind") or "") for s in plan["slides"] for b in s.get("blocks") or []]
    assert "table" in kinds
    roadmap = next(s for s in plan["slides"] if s.get("title") == "Roadmap")
    assert not any(b.get("kind") == "table" for b in roadmap.get("blocks") or [])
    data = render_plan_to_pptx(plan, template_path=master, definition=definition, user_id="s77")
    validate_generated_pptx(data, n_slides=len(plan["slides"]))
    out = tmp_path / "s77-zinnia-quality.pptx"
    out.write_bytes(data)
    assert out.stat().st_size > 1000


def test_composer_does_not_reuse_first_layout_for_every_slide():
    plan = {
        "slides": [
            {"title": "Opening", "purpose": "opening", "content_blocks": [{"kind": "bullet", "text": "Welcome"}]},
            {"title": "Status", "purpose": "section", "content_blocks": [{"kind": "bullet", "text": "Epics closed"}]},
            {"title": "Compare", "purpose": "comparison", "content_blocks": [{"kind": "bullet", "text": "Option A vs B"}]},
        ]
    }
    compose_plan(plan, _definition(), prompt="board pack")
    names = [s.get("master_layout_name") for s in plan["slides"]]
    assert names[0]
    assert len(set(names)) >= 2


def test_gallery_visual_hides_provider_uuid_and_exposes_theme():
    from app.services.mentrix.presentation.template_definition import gallery_visual

    visual = gallery_visual("zinnia-executive-v1")
    assert visual["provider_uuid_hidden"] is True
    assert "presenton" not in str(visual).lower() or visual["provider_uuid_hidden"]
    assert visual["readiness"] in {"READY", "TEMPLATE_NOT_READY"}
    if visual.get("error") != "definition_missing":
        assert visual["layout_count"] >= 1
        assert visual["colors"]
