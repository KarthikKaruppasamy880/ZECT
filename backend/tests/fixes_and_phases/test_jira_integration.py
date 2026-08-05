"""jira_integration.py's create_ticket used to always fabricate a local
ticket key (f"{project_key}-{count+1}") and never call Jira's real REST
API. This verifies it now creates a real issue via the MCP jira adapter
(app.services.mcp.hub.execute_tool) when Jira is reachable, and falls back
to the local placeholder — clearly labeled as such — when it isn't.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.models import JiraConfig
from app.routers import jira_integration
from app.routers.jira_integration import JiraTicketCreate, create_ticket


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _configured_db():
    db = _session()
    config = JiraConfig(
        base_url="https://acme.atlassian.net",
        email="bot@acme.com",
        api_token_encrypted="token",
        default_project_key="SEC",
        is_active=True,
    )
    db.add(config)
    db.commit()
    return db


class TestCreateRealIssue:
    def test_real_jira_success_returns_key_and_url(self, monkeypatch):
        db = _configured_db()
        monkeypatch.setattr(
            "app.services.mcp.hub.execute_tool",
            lambda db, server_id, tool_name, arguments: {"status": "success", "result": {"key": "SEC-7"}},
        )

        req = JiraTicketCreate(project_key="SEC", summary="Anomaly detected", issue_type="Bug")
        result = create_ticket(req, db=db)

        assert result.ticket_key == "SEC-7"
        assert result.ticket_url == "https://acme.atlassian.net/browse/SEC-7"
        assert result.ticket_status == "To Do"

    def test_jira_not_configured_falls_back_to_local_placeholder(self, monkeypatch):
        db = _configured_db()
        monkeypatch.setattr(
            "app.services.mcp.hub.execute_tool",
            lambda db, server_id, tool_name, arguments: {
                "status": "error",
                "result": {"message": "not configured"},
            },
        )

        req = JiraTicketCreate(project_key="SEC", summary="Anomaly detected", issue_type="Bug")
        result = create_ticket(req, db=db)

        assert result.ticket_key == "SEC-1"
        assert "local placeholder" in result.ticket_status.lower()

    def test_jira_call_raising_falls_back_to_local_placeholder(self, monkeypatch):
        db = _configured_db()
        monkeypatch.setattr(
            "app.services.mcp.hub.execute_tool",
            lambda db, server_id, tool_name, arguments: (_ for _ in ()).throw(RuntimeError("network down")),
        )

        req = JiraTicketCreate(project_key="SEC", summary="x", issue_type="Task")
        result = create_ticket(req, db=db)

        assert "local placeholder" in result.ticket_status.lower()

    def test_missing_config_still_raises_400(self):
        db = _session()
        req = JiraTicketCreate(project_key="SEC", summary="x")

        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            create_ticket(req, db=db)
        assert exc_info.value.status_code == 400
