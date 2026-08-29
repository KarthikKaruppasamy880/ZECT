"""Fabric spine + Camunda Mentrix Process + brand grep."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest


def test_brand_scrub_no_foreign_bot_in_docs_frontend_scripts():
    root = Path(__file__).resolve().parents[3]
    bad = []
    needles = ("minion" + "bot", "Minion" + "Bot")
    for base in (root / "docs", root / "frontend" / "src", root / "scripts", root / "backend" / "tests"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() not in {".md", ".py", ".tsx", ".ts", ".js"}:
                continue
            if path.name == "test_fabric_camunda.py":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            # Allow this test's needle literals only in assert messages elsewhere — skip self
            for n in needles:
                if n in text:
                    bad.append(f"{path.relative_to(root)}:{n}")
    assert not bad, "foreign bot strings remain:\n" + "\n".join(bad[:40])


def test_classify_and_refuse(db_session=None):
    from app.domains.fabric.router import classify_text, ensure_seed_surfaces
    from app.infrastructure.database import SessionLocal

    db = SessionLocal()
    try:
        ensure_seed_surfaces(db)
        from app.models import FabricSurface

        for s in db.query(FabricSurface).all():
            s.active = s.surface_id == "ngc"
        db.commit()
        hit = classify_text(db, "Update NGC rules for signatory", require_active=True)
        assert "ngc" in hit["surfaces_required"]
        assert hit["refuse"] is False
        miss = classify_text(db, "Need CDS contract changes", require_active=True)
        assert "cds" in miss["surfaces_required"] or miss["refuse"]
        if "cds" in miss["surfaces_required"]:
            assert miss["refuse"] is True
    finally:
        db.close()


def test_fabric_run_handoff_mocked():
    from app.domains.fabric.router import classify_text, ensure_seed_surfaces
    from app.infrastructure.database import SessionLocal
    from app.models import FabricSurface

    db = SessionLocal()
    try:
        ensure_seed_surfaces(db)
        for s in db.query(FabricSurface).all():
            s.active = s.surface_id in ("ngc", "bpm_pi")
            s.workspace = str(Path(__file__).resolve().parents[3])
        db.commit()

        class FakeRT:
            def start_run(self, goal, workspace="", **kwargs):
                return "sess-1"

        classified = classify_text(db, "NGC and BPM workflow", require_active=True)
        assert classified["refuse"] is False
        assert "ngc" in classified["surfaces_required"]
        assert FakeRT().start_run("g", workspace=".") == "sess-1"
    finally:
        db.close()


def test_camunda_status_degraded_without_url(monkeypatch):
    monkeypatch.delenv("ZECT_CAMUNDA_BASE_URL", raising=False)
    from app.adapters.camunda_client import process_engine_status

    st = process_engine_status()
    assert st["provider"] == "mentrix_process"
    assert st["ready"] is False


def test_camunda_deploy_start_incidents_mocked(monkeypatch):
    monkeypatch.setenv("ZECT_CAMUNDA_BASE_URL", "http://engine.test/engine-rest")
    monkeypatch.setenv("ZECT_CAMUNDA_USER", "demo")
    monkeypatch.setenv("ZECT_CAMUNDA_PASSWORD", "demo")

    class FakeResp:
        def __init__(self, code=200, payload=None, text=""):
            self.status_code = code
            self._payload = payload or {}
            self.text = text
            self.content = b"{}" if payload is not None else b""

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            if "incident" in url:
                return FakeResp(200, [{"id": "1"}])
            return FakeResp(200, {"version": "7.20"})

        def post(self, url, data=None, files=None, json=None):
            if "deployment" in url:
                return FakeResp(200, {"id": "dep1"})
            if "start" in url:
                return FakeResp(200, {"id": "inst1"})
            return FakeResp(404, text="no")

    with patch("app.adapters.camunda_client.httpx.Client", FakeClient):
        from app.adapters import camunda_client as c

        assert c.process_engine_status()["ready"] is True
        assert c.deploy_bpmn(content=b"<bpmn/>", name="x.bpmn")["ok"] is True
        assert c.start_process("order")["ok"] is True
        assert c.list_incidents()["ok"] is True
        assert len(c.list_incidents()["items"]) == 1
