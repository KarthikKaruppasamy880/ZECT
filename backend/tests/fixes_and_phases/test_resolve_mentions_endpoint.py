"""POST /api/coding-agent/context/resolve-mentions -- end to end through the
real FastAPI app, not just the resolver function in isolation."""

from __future__ import annotations


def test_resolve_mentions_returns_a_bounded_pack_with_provenance(client, auth_headers, tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    resp = client.post(
        "/api/coding-agent/context/resolve-mentions",
        headers=auth_headers,
        json={"text": "check @file:calc.py please", "workspace": str(tmp_path)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    items = body["pack"]["items"]
    assert any(i["source_type"] == "mention:file" for i in items)
    assert body["pack"]["token_used"] > 0


def test_resolve_mentions_rejects_workspace_outside_allowed_roots(client, auth_headers):
    resp = client.post(
        "/api/coding-agent/context/resolve-mentions",
        headers=auth_headers,
        json={"text": "@diff", "workspace": "C:/Windows/System32"},
    )
    assert resp.status_code == 403


def test_resolve_mentions_requires_auth(client, tmp_path):
    resp = client.post(
        "/api/coding-agent/context/resolve-mentions",
        json={"text": "@diff", "workspace": str(tmp_path)},
    )
    assert resp.status_code == 401
