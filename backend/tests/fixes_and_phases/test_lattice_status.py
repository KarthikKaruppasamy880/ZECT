"""Lattice status endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def authed_client(client, monkeypatch):
    monkeypatch.setenv("ZECT_AUTH_ENFORCE", "false")
    user = CurrentUser(
        user_id=1,
        username="admin@zect.local",
        email="admin@zect.local",
        auth_mode="local",
        token="test-token",
        role="admin",
    )

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    yield client
    app.dependency_overrides.clear()


class TestLatticeStatus:
    @patch("app.routers.lattice.get_graph")
    @patch("app.routers.lattice.get_structural_blueprint")
    def test_status_not_indexed(self, mock_bp, mock_graph, authed_client):
        mock_graph.return_value = None
        mock_bp.return_value = None

        r = authed_client.get("/api/lattice/status?project_key=missing-key")
        assert r.status_code == 200
        data = r.json()
        assert data["indexed"] is False
        assert data["project_key"] == "missing-key"
        assert data["has_blueprint"] is False

    @patch("app.routers.lattice.get_graph")
    @patch("app.routers.lattice.get_structural_blueprint")
    def test_status_indexed(self, mock_bp, mock_graph, authed_client):
        mock_graph.return_value = MagicMock(
            files_indexed=10,
            symbols=50,
            nodes=[1, 2, 3],
            edges=[1],
            languages={"python": 5},
        )
        mock_bp.return_value = {"updated_at": "2026-01-01T00:00:00+00:00", "stats": {}}

        r = authed_client.get("/api/lattice/status?project_key=zinnia-zoas")
        assert r.status_code == 200
        data = r.json()
        assert data["indexed"] is True
        assert data["has_blueprint"] is True
        assert data["graph_stats"]["files_indexed"] == 10
