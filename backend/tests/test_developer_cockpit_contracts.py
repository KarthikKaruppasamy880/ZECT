"""Unit tests for plan store, runtime discovery, and ship handoff contracts."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.coding_engine.plan_store import list_plans, load_plan, save_plan
from app.services.coding_engine.ship_handoff import find_open_handoff, register_handoff
from app.services.workspace.runtime_discovery import discover_runtime_recipes, resolve_recipe


def test_save_and_reload_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_PLAN_ROOT", str(tmp_path))
    out = save_plan(work_item_or_run="wi-9", title="fix login", markdown="## Steps\n1. Reproduce")
    assert out["ok"] is True
    loaded = load_plan(out["id"])
    assert "Reproduce" in loaded["markdown"]
    assert any(p["id"] == out["id"] for p in list_plans())


def test_runtime_discovery_zoas_nested(tmp_path):
    zm = tmp_path / "zinnia-modern"
    (zm / "frontend").mkdir(parents=True)
    (zm / "backend" / "tests").mkdir(parents=True)
    (zm / "package.json").write_text(json.dumps({"scripts": {"start:all": "echo all"}}), encoding="utf-8")
    (zm / "frontend" / "package.json").write_text(json.dumps({"scripts": {"dev": "next dev"}}), encoding="utf-8")
    (zm / "backend" / "main.py").write_text("app = None\n", encoding="utf-8")
    (zm / "backend" / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    out = discover_runtime_recipes(str(tmp_path))
    ids = {r["id"] for r in out["recipes"]}
    assert "zoas-full" in ids
    assert "zoas-frontend" in ids
    assert "zoas-backend" in ids
    assert "zoas-tests" in ids
    full = resolve_recipe(str(tmp_path), "zoas-full")
    assert full["ok"] is True
    assert full["command"] == "npm run start:all"
    assert Path(full["cwd"]).name == "zinnia-modern"


def test_runtime_discovery_rejects_injection(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "npm run dev; rm -rf /"}}),
        encoding="utf-8",
    )
    out = discover_runtime_recipes(str(tmp_path))
    # command we emit is `npm run dev`, not the script body — still must not include rm
    for row in out["recipes"]:
        assert "rm " not in row["command"]
        assert ".." not in row["cwdRel"]


def test_ship_handoff_rejects_duplicate(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_SHIP_HANDOFF_PATH", str(tmp_path / "h.json"))
    first = register_handoff(work_item_id=3, coding_mission_id="m1", delivery_run_id=11)
    assert first["ok"] is True
    dup = register_handoff(work_item_id=3, coding_mission_id="m1", delivery_run_id=12)
    assert dup["ok"] is False
    assert dup["error"] == "duplicate_delivery_run"
    assert find_open_handoff(3, "m1")["delivery_run_id"] == 11


def test_locate_nested_zoas_pytest(tmp_path):
    from app.services.coding_engine.lifecycle import _locate_pytest

    backend_tests = tmp_path / "zinnia-modern" / "backend" / "tests"
    backend_tests.mkdir(parents=True)
    (backend_tests / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    located = _locate_pytest(tmp_path)
    assert located is not None
    cwd, tests_dir = located
    assert cwd.name == "backend"
    assert tests_dir.name == "tests"
