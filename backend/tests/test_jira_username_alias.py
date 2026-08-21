from app.adapters.jira_env import jira_configured, jira_email


def test_jira_username_aliases_email(monkeypatch):
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.setenv("JIRA_USERNAME", "ops@zinnia.example")
    monkeypatch.setenv("JIRA_BASE_URL", "https://zinnia.atlassian.net")
    monkeypatch.setenv("JIRA_API_TOKEN", "dummy-not-a-secret")
    assert jira_email() == "ops@zinnia.example"
    assert jira_configured() is True


def test_jira_email_wins_over_username(monkeypatch):
    monkeypatch.setenv("JIRA_EMAIL", "direct@zinnia.example")
    monkeypatch.setenv("JIRA_USERNAME", "ops@zinnia.example")
    assert jira_email() == "direct@zinnia.example"
