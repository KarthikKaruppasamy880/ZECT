"""Phases 9–13 batch — Learning practice, model gateway, isolation, packaging honesty."""

from __future__ import annotations

import pytest

from app.core.scopes import PERSONAL_DEFAULT_SCOPE, PROJECT_SHARED, SCOPES, USER_PRIVATE
from app.infrastructure.database import SessionLocal
from app.services.model_gateway import MODEL_PROFILES, build_gateway_audit, resolve_profile_route
from app.services.desktop_readiness import build_desktop_readiness


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_scopes_enum_complete():
    assert USER_PRIVATE in SCOPES
    assert PROJECT_SHARED in SCOPES
    assert PERSONAL_DEFAULT_SCOPE == USER_PRIVATE
    assert set(SCOPES) == {
        "USER_PRIVATE",
        "TEAM_SHARED",
        "PROJECT_SHARED",
        "ORG_SHARED",
        "SYSTEM",
    }


def test_model_profiles_complete_and_restricted_never_cloud(monkeypatch):
    assert set(MODEL_PROFILES) == {"FAST", "QUALITY", "MAX", "LOCAL", "RESTRICTED", "CUSTOM"}
    monkeypatch.delenv("ZECT_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("MENTRIX_LLM_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    r = resolve_profile_route("RESTRICTED")
    assert r["allow_cloud"] is False
    assert r["blocked"] is True or r["provider"] in ("local", "none")
    assert r["fallback_used"] is False


def test_model_readiness_includes_profiles(authed_client):
    r = authed_client.get("/api/system/model-readiness")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "profiles" in body
    assert set(body["model_profiles"]) == set(MODEL_PROFILES)
    assert "gateway_audit" in body
    assert "requested_model" in body["route"] or "provider" in body["route"]


def test_gateway_audit_no_silent_duplicate_ok():
    audit = build_gateway_audit()
    assert "profiles" in audit
    assert "duplicate_config_warning" in audit


def test_learning_languages_and_practice_verify(authed_client, db):
    from app.domains.personal_agent.learning import sync_pbl_catalog
    from app.models import LearningResource

    langs = authed_client.get("/api/learning/languages")
    assert langs.status_code == 200
    body = langs.json()
    assert "Python" in body["languages"]
    assert "GUIDED" in body["modes"]
    assert body["scope"] == "USER_PRIVATE"

    sync_pbl_catalog(
        db,
        markdown="## Python\n- [Py Path](https://example.com/py) — `pytest`\n",
    )
    res = db.query(LearningResource).filter(LearningResource.language.ilike("%Python%")).first()
    assert res is not None

    start = authed_client.post(
        "/api/learning/projects",
        json={"resource_id": res.id, "mode": "GUIDED", "title": "Py practice"},
    )
    assert start.status_code == 200, start.text
    pid = start.json()["id"]

    # LLM claim alone cannot verify
    bad = authed_client.post(
        f"/api/learning/projects/{pid}/progress",
        json={
            "event": "test_passed",
            "evidence": {"items": [{"id": "x", "type": "TEST_RESULT", "llm_claim": True, "operation_id": "OP-LEARN-TEST"}]},
        },
    )
    assert bad.status_code == 400

    fail = authed_client.post(
        f"/api/learning/projects/{pid}/practice/verify",
        json={"code": "def ok():\n    return True\n", "language": "Python", "passed": False, "exit_code": 1},
    )
    assert fail.status_code == 200
    assert fail.json()["passed"] is False

    ok = authed_client.post(
        f"/api/learning/projects/{pid}/practice/verify",
        json={
            "code": "def ok():\n    return True\n",
            "language": "Python",
            "passed": True,
            "exit_code": 0,
            "test_output": "PASS",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["passed"] is True
    proj = ok.json()["project"]
    assert any(e.get("verified") for e in proj.get("evidence") or [])

    # user_confirmed does not complete
    conf = authed_client.post(
        f"/api/learning/projects/{pid}/progress",
        json={"event": "user_confirmed", "evidence": {}},
    )
    assert conf.status_code == 200
    assert conf.json()["status"] != "completed" or not conf.json()["progress"].get("verified_complete")


def test_conversations_require_auth_and_isolate(client, authed_client, auth_headers, db):
    anon = client.get("/api/conversations")
    assert anon.status_code in (401, 403)

    created = authed_client.post("/api/conversations", json={"title": "mine", "mode": "ask"})
    assert created.status_code == 200, created.text
    cid = created.json()["id"]
    assert created.json().get("scope") == "USER_PRIVATE"

    listed = authed_client.get("/api/conversations")
    assert listed.status_code == 200
    ids = [i["id"] for i in listed.json()["items"]]
    assert cid in ids

    # Forge foreign row and ensure it is not listed / not readable
    from app.models import Conversation

    foreign = Conversation(title="other-user", mode="ask", user_id=999999)
    db.add(foreign)
    db.commit()
    db.refresh(foreign)

    listed2 = authed_client.get("/api/conversations")
    ids2 = [i["id"] for i in listed2.json()["items"]]
    assert foreign.id not in ids2

    leak = authed_client.get(f"/api/conversations/{foreign.id}")
    assert leak.status_code == 404


def test_memory_preferences_cross_user_forbidden(authed_client):
    r = authed_client.get("/api/memory/preferences/999999")
    assert r.status_code in (403, 404)


def test_desktop_packaging_honest_partial():
    d = build_desktop_readiness()
    assert d["packaging"]["status"] == "PARTIAL"
    assert d["packaging"]["backend_bundled"] is False
    assert d["service_lifecycle_present"] is True
    assert d["windows_install_doc_present"] is True
