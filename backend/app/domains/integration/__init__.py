"""Integration domain routers."""

from app.domains.integration import jira_integration
from app.domains.integration import slack_integration
from app.domains.integration import confluence_integration
from app.domains.integration import datadog_integration
from app.domains.integration import email_integration
from app.domains.integration import mcp
from app.domains.integration import ci_monitor
from app.domains.integration import ci_remediation

__all__ = ['jira_integration', 'slack_integration', 'confluence_integration', 'datadog_integration', 'email_integration', 'mcp', 'ci_monitor', 'ci_remediation']
