"""approve_delivery/create_pr were pure stubs in the Companion chat/voice tool
dispatcher — saying "approve and ship it" returned {"ok": True, "queued":
True, ...} without doing anything, just telling the user to go confirm in the
Mentrix Delivery UI. This verifies they now call the same approve/create-pr
route logic the UI itself uses, against a real MentrixRun row.
"""

from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — register all models incl. MentrixRun
from app.infrastructure.database import Base
from app.models import MentrixRun
from app.services.mentrix.companion import _exec_tool


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _make_run(db, *, created_by="alice@zinnia.com", gates=None, status="awaiting_approval"):
    run = MentrixRun(
        mode="deliver",
        goal="Add a small helper function",
        status=status,
        gates_json=json.dumps(gates or {"lint_ok": True, "sandbox_ready": True, "review_ok": True}),
        result_json="{}",
        created_by=created_by,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


class TestApproveDelivery:
    def test_approves_the_most_recent_run_for_this_user(self):
        db = _session()
        run = _make_run(db)

        out = _exec_tool(db, "approve_delivery", {}, created_by="alice@zinnia.com", user_id=7)

        assert out["ok"] is True
        assert out["run_id"] == run.id
        assert out["status"] == "approved"
        db.refresh(run)
        assert run.status == "approved"
        assert run.approved_by == "alice@zinnia.com"

    def test_approves_an_explicit_run_id(self):
        db = _session()
        _make_run(db)  # an older run that should NOT be picked
        run2 = _make_run(db)

        out = _exec_tool(db, "approve_delivery", {"run_id": run2.id}, created_by="alice@zinnia.com")

        assert out["run_id"] == run2.id

    def test_no_run_returns_clear_error_not_a_crash(self):
        db = _session()

        out = _exec_tool(db, "approve_delivery", {}, created_by="nobody@zinnia.com")

        assert out["ok"] is False
        assert "start_delivery" in out["error"] or "run" in out["error"].lower()

    def test_gates_not_green_surfaces_real_error_not_fake_success(self):
        db = _session()
        _make_run(db, gates={"lint_ok": False, "sandbox_ready": True, "review_ok": True})

        out = _exec_tool(db, "approve_delivery", {}, created_by="alice@zinnia.com")

        assert out["ok"] is False
        assert "lint_ok" in out["error"]


class TestCreatePR:
    def test_create_pr_after_approve_dry_run(self, monkeypatch):
        monkeypatch.setenv("MENTRIX_PR_DRY_RUN", "true")
        db = _session()
        run = _make_run(db)
        approved = _exec_tool(db, "approve_delivery", {}, created_by="alice@zinnia.com")
        assert approved["ok"] is True

        out = _exec_tool(db, "create_pr", {"dry_run": True}, created_by="alice@zinnia.com")

        assert out["ok"] is True
        assert out["pr_url"]
        db.refresh(run)
        assert run.status == "pr_created"

    def test_create_pr_without_approve_is_blocked_not_silently_shipped(self):
        db = _session()
        _make_run(db)

        out = _exec_tool(db, "create_pr", {"dry_run": True}, created_by="alice@zinnia.com")

        assert out["ok"] is False
        assert "approve" in out["error"].lower()
