"""Jira/Slack config tokens were stored plaintext in columns literally named
*_encrypted — configure_jira/configure_slack assigned the raw request value
with no _encrypt() call at all. Verifies both now actually encrypt on write
(nothing in the codebase reads these back — real Jira/Slack calls go through
the MCP hub's env/MCPServerConfig path — so this only checks storage, not a
round-trip decrypt).
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.infrastructure.database import Base
from app.models import JiraConfig, SlackConfig
from app.domains.integration.jira_integration import JiraConfigCreate, configure_jira
from app.domains.integration.slack_integration import SlackConfigCreate, configure_slack


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestJiraTokenEncrypted:
    def test_configure_jira_stores_ciphertext_not_plaintext(self, monkeypatch):
        monkeypatch.setenv("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcy0h")
        monkeypatch.setenv("ENV", "development")
        db = _session()

        configure_jira(
            JiraConfigCreate(base_url="https://acme.atlassian.net", email="bot@acme.com", api_token="super-secret-token"),
            db=db,
        )

        config = db.query(JiraConfig).first()
        assert config.api_token_encrypted != "super-secret-token"
        assert "super-secret-token" not in config.api_token_encrypted

    def test_reconfigure_re_encrypts_on_update_path(self, monkeypatch):
        monkeypatch.setenv("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcy0h")
        monkeypatch.setenv("ENV", "development")
        db = _session()
        configure_jira(JiraConfigCreate(base_url="https://a.atlassian.net", email="a@a.com", api_token="token-1"), db=db)
        first_ciphertext = db.query(JiraConfig).first().api_token_encrypted

        configure_jira(JiraConfigCreate(base_url="https://a.atlassian.net", email="a@a.com", api_token="token-2"), db=db)

        config = db.query(JiraConfig).first()
        assert config.api_token_encrypted != first_ciphertext
        assert "token-2" not in config.api_token_encrypted


class TestSlackTokenEncrypted:
    def test_configure_slack_stores_ciphertext_not_plaintext(self, monkeypatch):
        monkeypatch.setenv("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcy0h")
        monkeypatch.setenv("ENV", "development")
        db = _session()

        configure_slack(SlackConfigCreate(bot_token="xoxb-super-secret"), db=db)

        config = db.query(SlackConfig).first()
        assert config.bot_token_encrypted != "xoxb-super-secret"
        assert "xoxb-super-secret" not in config.bot_token_encrypted
