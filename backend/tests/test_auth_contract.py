"""Characterizing tests for auth contract (Mentrix Phase 0 preflight)."""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def auth_env(monkeypatch):
    monkeypatch.setenv("ZECT_USERNAME", "test@zect.local")
    monkeypatch.setenv("ZECT_PASSWORD", "test-pass-1234")
    monkeypatch.setenv("ZECT_AUTH_MODE", "local")
    monkeypatch.setenv("ZECT_AUTH_ENFORCE", "true")


def test_login_requires_username_password(client: TestClient, auth_env):
    bad = client.post("/api/auth/login", json={"email": "x", "password": "y"})
    # Either validation error or 401 — must not succeed with wrong shape silently as 200 with token
    assert bad.status_code in (401, 422)


def test_login_success_and_verify(client: TestClient, auth_env):
    resp = client.post(
        "/api/auth/login",
        json={"username": "test@zect.local", "password": "test-pass-1234"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "token" in data
    assert data.get("username")

    verify = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {data['token']}"})
    if verify.status_code == 401:
        # Fallback query-param verify for transition
        verify = client.get(f"/api/auth/verify?token={data['token']}")
    assert verify.status_code == 200
    assert verify.json().get("valid") is True


def test_me_requires_auth(client: TestClient, auth_env):
    resp = client.get("/api/auth/me")
    assert resp.status_code in (401, 404)  # 404 only if route not yet mounted before Phase 0


def test_healthz_open(client: TestClient):
    assert client.get("/healthz").status_code == 200
