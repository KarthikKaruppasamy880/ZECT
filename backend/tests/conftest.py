"""Shared fixtures for ZECT backend tests."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_zect.db"
os.environ["ZECT_USERNAME"] = "test@zect.local"
os.environ["ZECT_PASSWORD"] = "test-pass-1234"
os.environ["ZECT_AUTH_MODE"] = "local"
os.environ["ZECT_AUTH_ENFORCE"] = "true"
os.environ.setdefault("OPENAI_API_KEY", "")

from app.main import app  # noqa: E402
from app.infrastructure.database import init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    init_db()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_token(client: TestClient):
    resp = client.post(
        "/api/auth/login",
        json={"username": "test@zect.local", "password": "test-pass-1234"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest.fixture(scope="session")
def auth_headers(auth_token: str):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="session")
def authed_client(client: TestClient, auth_headers: dict):
    """Client wrapper that injects Authorization on every request."""

    class _Authed:
        def request(self, method, url, **kwargs):
            headers = dict(kwargs.pop("headers", None) or {})
            headers.update(auth_headers)
            return client.request(method, url, headers=headers, **kwargs)

        def get(self, url, **kwargs):
            return self.request("GET", url, **kwargs)

        def post(self, url, **kwargs):
            return self.request("POST", url, **kwargs)

        def put(self, url, **kwargs):
            return self.request("PUT", url, **kwargs)

        def delete(self, url, **kwargs):
            return self.request("DELETE", url, **kwargs)

        def patch(self, url, **kwargs):
            return self.request("PATCH", url, **kwargs)

    return _Authed()
