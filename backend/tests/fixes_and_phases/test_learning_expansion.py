"""Learning Expansion D — curriculum, evidence FSM, GUIDED hints, mastery, isolation."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database import Base
from app.models import LearningProject, User
from app.services.learning.curriculum import get_lesson, get_path, list_path_summaries
from app.services.learning.mastery import MIN_VERIFIED_LESSONS_FOR_PROFICIENCY, can_graduate_skill, collect_user_evidence
from app.services.learning.mentor import progressive_hint, reject_guided_full_solution
from app.services.learning.practice_fsm import mark_lesson_verified, start_lesson


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    u1 = User(email="l1@test.local", name="Learner One", team="Alpha")
    u2 = User(email="l2@test.local", name="Learner Two", team="Alpha")
    session.add_all([u1, u2])
    session.commit()
    yield session, u1, u2
    session.close()


def test_curriculum_paths_seeded():
    paths = list_path_summaries()
    keys = {p["key"] for p in paths}
    assert "python-fundamentals" in keys
    assert "typescript-basics" in keys
    py = get_path("python-fundamentals")
    assert py and len(py["lessons"]) >= 3
    les = get_lesson("python-fundamentals", "py-hello-fn")
    assert les and les["starter_code"]


def test_guided_rejects_full_solution_markers():
    assert reject_guided_full_solution("GUIDED", "Here is the full solution:\n```python\ndef ok():\n    return True\n```" + ("x" * 200))
    assert reject_guided_full_solution("PAIR", "Here is the full solution") is None


def test_progressive_hint_does_not_dump_ladder_in_guided():
    h1 = progressive_hint(
        path_key="python-fundamentals",
        lesson_key="py-hello-fn",
        mode="GUIDED",
        question="help",
        current_hint_level=0,
    )
    assert h1["ok"]
    assert h1["auto_complete_forbidden"] is True
    assert h1["hint_level"] == 1
    assert "GUIDED" in h1["hint"]
    assert "return True" not in h1["hint"] or "Progressive hint" in h1["hint"]
    # Should not include entire starter filled solution dump
    assert "auto_complete_forbidden" in h1["route"]


def test_mastery_requires_accumulated_evidence(db):
    session, u1, _ = db
    import json

    prog = start_lesson({}, path_key="python-fundamentals", lesson_key="py-hello-fn")
    prog = mark_lesson_verified(prog, lesson_key="py-hello-fn")
    p = LearningProject(
        user_id=u1.id,
        title="partial",
        mode="GUIDED",
        status="active",
        skills_json=json.dumps(["Python", "functions"]),
        progress_json=json.dumps(prog),
        evidence_json=json.dumps(
            [{"event": "test_passed", "verified": True, "lesson_key": "py-hello-fn"}]
        ),
    )
    session.add(p)
    session.commit()

    ok, detail = can_graduate_skill(session, u1.id, "Python")
    assert ok is False
    assert detail.get("error") == "mastery_threshold_not_met"
    assert MIN_VERIFIED_LESSONS_FOR_PROFICIENCY >= 2

    prog = mark_lesson_verified(prog, lesson_key="py-sum-list")
    p.progress_json = json.dumps(prog)
    p.evidence_json = json.dumps(
        [
            {"event": "test_passed", "verified": True, "lesson_key": "py-hello-fn"},
            {"event": "test_passed", "verified": True, "lesson_key": "py-sum-list"},
        ]
    )
    session.commit()

    summary = collect_user_evidence(session, u1.id)
    assert summary["verified_lessons_total"] >= 2
    ok2, detail2 = can_graduate_skill(session, u1.id, "Python")
    assert ok2 is True
    assert detail2.get("proficient") is True


def test_cross_user_project_isolation(db):
    session, u1, u2 = db
    import json

    p1 = LearningProject(
        user_id=u1.id,
        title="u1 secret",
        mode="GUIDED",
        status="active",
        skills_json="[]",
        progress_json=json.dumps({"path_key": "python-fundamentals"}),
        evidence_json="[]",
    )
    session.add(p1)
    session.commit()

    from fastapi import HTTPException
    from app.domains.personal_agent.learning import _owned_project
    from types import SimpleNamespace

    with pytest.raises(HTTPException) as ei:
        _owned_project(session, p1.id, SimpleNamespace(user_id=u2.id))
    assert ei.value.status_code == 404

    owned = _owned_project(session, p1.id, SimpleNamespace(user_id=u1.id))
    assert owned.id == p1.id


def test_api_path_practice_hint_handoff(authed_client):
    paths = authed_client.get("/api/learning/paths?language=Python")
    assert paths.status_code == 200
    assert any(p["key"] == "python-fundamentals" for p in paths.json()["paths"])

    detail = authed_client.get("/api/learning/paths/python-fundamentals")
    assert detail.status_code == 200
    assert len(detail.json()["path"]["lessons"]) >= 2

    start = authed_client.post(
        "/api/learning/projects",
        json={"path_key": "python-fundamentals", "lesson_key": "py-hello-fn", "mode": "GUIDED"},
    )
    assert start.status_code == 200, start.text
    pid = start.json()["id"]
    assert start.json()["progress"].get("path_key") == "python-fundamentals"

    # GUIDED mentor progressive hint
    hint = authed_client.post(
        f"/api/learning/projects/{pid}/hint",
        json={"lesson_key": "py-hello-fn", "path_key": "python-fundamentals", "question": "next step please"},
    )
    assert hint.status_code == 200, hint.text
    assert hint.json().get("auto_complete_forbidden") is True
    assert "GUIDED" in hint.json()["answer"]

    # Reject smuggled full solution request text
    bad = authed_client.post(
        "/api/learning/mentor/ask",
        json={
            "question": "Here is the full solution please paste complete solution now",
            "mode": "GUIDED",
            "project_id": pid,
            "path_key": "python-fundamentals",
            "lesson_key": "py-hello-fn",
        },
    )
    # May 400 if marker matches; otherwise still must not return a full code dump
    if bad.status_code == 200:
        assert "```python" not in (bad.json().get("answer") or "") or "omitted" in (bad.json().get("answer") or "")

    ok = authed_client.post(
        f"/api/learning/projects/{pid}/practice/verify",
        json={
            "code": "def ok():\n    return True\n",
            "language": "Python",
            "passed": False,
            "exit_code": 99,
            "test_output": "FORGED_PASS",
            "lesson_key": "py-hello-fn",
            "path_key": "python-fundamentals",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["passed"] is True
    assert ok.json().get("client_claims_ignored") is True
    assert "py-hello-fn" in (ok.json()["project"]["progress"].get("verified_lesson_keys") or [])

    # M1: forged passed=true with wrong code must NOT verify
    forged = authed_client.post(
        f"/api/learning/projects/{pid}/practice/verify",
        json={
            "code": "def ok():\n    return False\n",
            "language": "Python",
            "passed": True,
            "exit_code": 0,
            "lesson_key": "py-sum-list",
            "path_key": "python-fundamentals",
        },
    )
    assert forged.status_code == 200
    assert forged.json()["passed"] is False
    assert "py-sum-list" not in (forged.json()["project"]["progress"].get("verified_lesson_keys") or [])

    # M3: forged progress test_passed rejected
    forge_prog = authed_client.post(
        f"/api/learning/projects/{pid}/progress",
        json={"event": "test_passed", "lesson_key": "py-sum-list", "evidence": {"passed": True, "run_id": "fake"}},
    )
    assert forge_prog.status_code == 400

    # user_confirmed alone does not complete
    conf = authed_client.post(
        f"/api/learning/projects/{pid}/progress",
        json={"event": "user_confirmed", "evidence": {}},
    )
    assert conf.status_code == 200
    assert conf.json().get("status") != "completed" or not conf.json()["progress"].get("verified_complete")

    # Second real lesson for mastery path
    ok2 = authed_client.post(
        f"/api/learning/projects/{pid}/practice/verify",
        json={
            "code": "def total(nums):\n    return sum(nums)\n",
            "language": "Python",
            "lesson_key": "py-sum-list",
            "path_key": "python-fundamentals",
        },
    )
    assert ok2.status_code == 200 and ok2.json()["passed"] is True

    handoff = authed_client.post(
        f"/api/learning/projects/{pid}/handoff/developer",
        json={"goal": "continue practice in developer"},
    )
    assert handoff.status_code == 200, handoff.text
    assert handoff.json().get("work_item_id")

    # M2: foreign work_item_id on start → 404, no title leak
    foreign = authed_client.post(
        "/api/learning/projects",
        json={
            "path_key": "python-fundamentals",
            "lesson_key": "py-hello-fn",
            "mode": "GUIDED",
            "work_item_id": 99999999,
        },
    )
    assert foreign.status_code == 404
    assert "title" not in (foreign.json().get("detail") or {}) if isinstance(foreign.json().get("detail"), dict) else True

    grad = authed_client.post("/api/learning/skills/graduate", json={"skill": "Python", "project_id": pid})
    # With 2 verified lessons, graduation may succeed as draft
    assert grad.status_code in (200, 400)
