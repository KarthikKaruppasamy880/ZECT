"""E1 geometry layer — missing boxes must not become full-slide covers."""

from app.services.mentrix.presentation.geometry import (
    WIDESCREEN_CX,
    boxes_overlap,
    geometry_to_percent,
    geometry_valid,
    within_slide,
)


def test_geometry_valid_and_percent():
    assert geometry_valid(None) is False
    assert geometry_valid({"cx": 0, "cy": 10}) is False
    geo = {"x": 914400, "y": 0, "cx": 914400, "cy": 100}
    pct = geometry_to_percent(geo, WIDESCREEN_CX, 1000)
    assert pct is not None
    assert abs(pct["left"] - 10.0) < 0.01
    assert geometry_to_percent({"cx": 0, "cy": 1}, WIDESCREEN_CX, 1000) is None


def test_overlap_and_bounds():
    a = {"x": 0, "y": 0, "cx": 100_000, "cy": 100_000}
    b = {"x": 200_000, "y": 0, "cx": 100_000, "cy": 100_000}
    assert boxes_overlap(a, b) is False
    assert boxes_overlap(a, {"x": 50_000, "y": 0, "cx": 100_000, "cy": 100_000}) is True
    assert within_slide(a, 1_000_000, 1_000_000) is True
    assert within_slide({"x": 0, "y": 0, "cx": 9_000_000, "cy": 9_000_000}, 1000, 1000) is False


def test_compose_child_geometry():
    from app.services.mentrix.presentation.geometry import compose_child_geometry

    parent = {"x": 100, "y": 200, "cx": 1000, "cy": 800}
    child = {"x": 10, "y": 20, "cx": 50, "cy": 60}
    out = compose_child_geometry(parent, child)
    assert out is not None
    assert out["x"] == 110
    assert out["y"] == 220
    assert out["cx"] == 50
    assert compose_child_geometry(None, {"cx": 0, "cy": 1}) is None

