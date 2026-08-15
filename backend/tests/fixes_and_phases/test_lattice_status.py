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
    @patch("app.domains.repository.lattice.get_lattice_status")
    @patch("app.domains.repository.lattice.get_graph")
    @patch("app.domains.repository.lattice.get_structural_blueprint")
    def test_status_not_indexed(self, mock_bp, mock_graph, mock_status, authed_client):
        mock_graph.return_value = None
        mock_bp.return_value = None
        mock_status.return_value = {
            "state": "NOT_INDEXED",
            "indexed": False,
            "reason": "graph_missing",
            "action": "index_repository",
            "action_label": "Index repository",
        }

        r = authed_client.get("/api/lattice/status?project_key=missing-key")
        assert r.status_code == 200
        data = r.json()
        assert data["indexed"] is False
        assert data["state"] == "NOT_INDEXED"
        assert data["project_key"] == "missing-key"
        assert data["has_blueprint"] is False

    @patch("app.domains.repository.lattice.get_lattice_status")
    @patch("app.domains.repository.lattice.get_graph")
    @patch("app.domains.repository.lattice.get_structural_blueprint")
    def test_status_indexed(self, mock_bp, mock_graph, mock_status, authed_client):
        mock_graph.return_value = MagicMock(
            files_indexed=10,
            symbols=50,
            nodes=[1, 2, 3],
            edges=[1],
            languages={"python": 5},
        )
        mock_bp.return_value = {"updated_at": "2026-01-01T00:00:00+00:00", "stats": {}}
        mock_status.return_value = {
            "state": "READY",
            "indexed": True,
            "reason": "graph_ready",
            "action": "view_intelligence",
            "action_label": "View intelligence",
        }

        r = authed_client.get("/api/lattice/status?project_key=zinnia-zoas")
        assert r.status_code == 200
        data = r.json()
        assert data["indexed"] is True
        assert data["state"] == "READY"
        assert data["has_blueprint"] is True
        assert data["graph_stats"]["files_indexed"] == 10


def test_lattice_status_canonical_states():
    from app.services.lattice.indexer import get_lattice_status

    empty = get_lattice_status("")
    assert empty["state"] == "NOT_APPLICABLE"
    missing = get_lattice_status("no-such-project-key-zect-v2")
    assert missing["state"] in {"NOT_INDEXED", "NOT_CONFIGURED"}
    assert missing["indexed"] is False
