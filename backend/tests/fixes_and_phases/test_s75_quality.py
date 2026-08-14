"""S7.5 quality closure — LLM planner labeling, VisualPlanner, require_llm."""

from __future__ import annotations

from unittest.mock import patch

from app.services.mentrix.presentation.native_provider import ZectNativePresentationProvider
from app.services.mentrix.presentation.planner import build_presentation_plan, _coerce_llm_plan
from app.services.mentrix.presentation.provider import PresentationGenerateRequest
from app.services.mentrix.presentation.service import PresentationService
from app.services.mentrix.presentation.visual_planner import apply_visual_plan
from tests.fixes_and_phases.pptx_fixtures import make_master_pptx_bytes
from app.services.mentrix.presentation import template_registry as tmpl


def test_public_plan_requests_automatic_gateway_policy():
    captured: list[dict] = []

    def _fake(messages, **kwargs):
        captured.append(kwargs)
        return {"ok": False, "error": "offline", "content": "", "telemetry": {}}

    with patch("app.services.phases.llm_phase._chat", side_effect=_fake):
        out = build_presentation_plan(
            prompt="Q3 delivery status for leadership",
            n_slides=5,
            audience_id="executive",
        )
    assert captured
    assert captured[0].get("policy") == "automatic"
    assert out["ok"] is True
    assert out["fallback"] is True
    assert out["planner_mode"] == "HEURISTIC_FALLBACK"
    assert out["plan"]["planner_mode"] == "HEURISTIC_FALLBACK"
    assert out.get("degraded") is True


def test_coerce_nested_narrative_arc_into_slides():
    parsed = _coerce_llm_plan(
        {
            "objective": "Q3 update",
            "audience_id": "executive",
            "n_slides": 4,
            "narrative": {
                "arc": {
                    "opening": {"title": "Q3 Delivery Status Overview", "content_blocks": [{"kind": "text", "text": "Progress"}]},
                    "sections": [{"title": "Risks", "content_blocks": [{"kind": "text", "text": "Vendor delay"}]}],
                    "decision": {"title": "Hire contractors", "content_blocks": [{"kind": "text", "text": "Ask"}]},
                    "cta": {"title": "Owners", "content_blocks": [{"kind": "text", "text": "Sep 1"}]},
                }
            },
        }
    )
    assert isinstance(parsed["narrative"], str)
    assert len(parsed["slides"]) == 4
    assert parsed["slides"][0]["title"] == "Q3 Delivery Status Overview"
    with patch("app.services.phases.llm_phase._chat", return_value={"ok": False, "error": "offline", "content": ""}):
        out = build_presentation_plan(
            prompt="Q3 delivery status",
            n_slides=4,
            audience_id="executive",
            require_llm=True,
        )
    assert out["ok"] is False
    assert out["error"] == "llm_planner_required"
    assert out["planner_mode"] == "HEURISTIC_FALLBACK"


def test_visual_planner_gives_architecture_a_diagram():
    plan = {
        "slides": [
            {"title": "Opening", "content_blocks": [{"kind": "bullet", "text": "Scope"}], "visual_intent": "none"},
            {
                "title": "Services",
                "content_blocks": [
                    {"kind": "bullet", "text": "API"},
                    {"kind": "bullet", "text": "Store"},
                    {"kind": "bullet", "text": "Workers"},
                ],
                "visual_intent": "none",
            },
            {"title": "Close", "content_blocks": [{"kind": "bullet", "text": "Ask"}], "visual_intent": "none"},
        ]
    }
    out = apply_visual_plan(plan, audience_id="technical")
    kinds = [s.get("visual_intent") for s in out["slides"]]
    assert "diagram" in kinds
    diag = next(s for s in out["slides"] if s.get("visual_intent") == "diagram")
    assert any(b.get("kind") == "diagram" for b in diag.get("blocks") or [])


def test_fast_basic_skips_gateway_and_labels_degraded():
    with patch("app.services.phases.llm_phase._chat") as chat:
        out = build_presentation_plan(
            prompt="Q3 delivery status for leadership",
            n_slides=5,
            audience_id="executive",
            fast_basic=True,
        )
        chat.assert_not_called()
    assert out["ok"] is True
    assert out["planner_mode"] == "HEURISTIC_FALLBACK"
    assert out["degraded"] is True
    assert out["fallback_reason"] == "fast_basic"


def test_restricted_still_blocks_before_llm():
    with patch("app.services.phases.llm_phase._chat") as chat:
        out = build_presentation_plan(
            prompt="RESTRICTED payroll SSNs for the board",
            n_slides=4,
            audience_id="executive",
            sensitivity_hint="RESTRICTED",
        )
        chat.assert_not_called()
    assert out["ok"] is False
    assert out["error"] == "sensitivity_blocked"


def test_invalid_llm_chart_is_replaced_with_example():
    from app.services.mentrix.presentation.blocks import ensure_visual_blocks, normalize_block

    bad = normalize_block({"kind": "chart", "content": {"chart_type": "line"}}, slide_index=1, ordinal=0)
    assert bad and not (bad.get("validation") or {}).get("ok")
    slide = {
        "index": 1,
        "visual_intent": "chart",
        "chart_type": "line",
        "blocks": [bad],
        "content_blocks": [{"kind": "bullet", "text": "KPI trend"}],
    }
    out = ensure_visual_blocks(slide)
    charts = [b for b in out["blocks"] if b.get("kind") == "chart"]
    assert len(charts) == 1
    assert (charts[0].get("validation") or {}).get("ok") is True
    assert (charts[0].get("content") or {}).get("categories")


def test_native_generate_labels_heuristic_and_skips_presenton(tmp_path, monkeypatch):
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
    with patch("app.services.presenton_client.generate_presentation") as gen:
        with patch("app.services.phases.llm_phase._chat", return_value={"ok": False, "error": "offline", "content": ""}):
            out = PresentationService(provider=ZectNativePresentationProvider()).generate(
                PresentationGenerateRequest(
                    content="Technical architecture of the claims API",
                    n_slides=5,
                    ui_template_choice="zinnia-executive-v1",
                    audience_id="technical",
                    filename="s75.pptx",
                    user_id="u-s75",
                )
            )
        gen.assert_not_called()
    assert out["ok"] is True
    assert out["planner_mode"] == "HEURISTIC_FALLBACK"
    assert out["degraded"] is True
    assert out["visual_inventory"].get("diagram", 0) >= 1
