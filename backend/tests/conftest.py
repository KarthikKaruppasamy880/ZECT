"""Shared fixtures for ZECT backend tests."""

import os
import pytest
from fastapi.testclient import TestClient

# Force SQLite for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_zect.db")
os.environ.setdefault("AUTH_EMAIL", "test@test.com")
os.environ.setdefault("AUTH_PASSWORD", "test1234")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-ci")

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """FastAPI test client shared across the test session."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_token(client: TestClient):
    """Get a valid JWT token for authenticated endpoints."""
    resp = client.post("/api/auth/login", json={
        "email": "test@test.com",
        "password": "test1234",
    })
    if resp.status_code == 200:
        return resp.json().get("token", "")
    return ""


@pytest.fixture(scope="session")
def auth_headers(auth_token: str):
    """Authorization headers dict."""
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}
