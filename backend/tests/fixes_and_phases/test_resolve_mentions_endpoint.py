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


def test_resolve_mentions_rejects_workspace_outside_allowed_roots(client, auth_headers, monkeypatch):
    # Not a Windows-specific literal like "C:/Windows/System32": on POSIX,
    # "C:" isn't a drive marker, so that string resolves relative to the
    # CWD and can land right back inside an allowed root (this broke CI on
    # Linux while passing locally on Windows). Use the same proven,
    # platform-portable "clearly nowhere real" path as
    # test_app_runner_security.py's equivalent test.
    monkeypatch.delenv("ZECT_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("MENTRIX_WORKSPACE", raising=False)
    resp = client.post(
        "/api/coding-agent/context/resolve-mentions",
        headers=auth_headers,
        json={"text": "@diff", "workspace": "/__zect_not_allowed__/outside"},
    )
    assert resp.status_code == 403


def test_resolve_mentions_requires_auth(client, tmp_path):
    resp = client.post(
        "/api/coding-agent/context/resolve-mentions",
        json={"text": "@diff", "workspace": str(tmp_path)},
    )
    assert resp.status_code == 401
