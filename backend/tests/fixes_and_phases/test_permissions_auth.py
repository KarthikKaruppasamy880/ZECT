"""Phase 5 Stage A — permission endpoints require authentication."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_rules_requires_auth():
    res = client.get("/api/permissions/rules")
    assert res.status_code in (401, 403)


def test_check_permission_requires_auth():
    res = client.post("/api/permissions/check", json={"action": "read_file"})
    assert res.status_code in (401, 403)


def test_list_audits_requires_auth():
    res = client.get("/api/permissions/audits")
    assert res.status_code in (401, 403)


def test_pending_audits_requires_auth():
    res = client.get("/api/permissions/audits/pending")
    assert res.status_code in (401, 403)
