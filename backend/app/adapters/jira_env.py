"""Jira env names — runner uses JIRA_USERNAME; ZECT historically used JIRA_EMAIL."""

from __future__ import annotations

import os


def jira_base_url() -> str:
    return (os.getenv("JIRA_BASE_URL") or os.getenv("MCP_JIRA_URL") or "").strip()


def jira_email() -> str:
    """Atlassian account email. JIRA_USERNAME is the runner alias."""
    return (os.getenv("JIRA_EMAIL") or os.getenv("JIRA_USERNAME") or "").strip()


def jira_api_token() -> str:
    return (os.getenv("JIRA_API_TOKEN") or "").strip()


def jira_configured() -> bool:
    return bool(jira_base_url() and jira_email() and jira_api_token())
