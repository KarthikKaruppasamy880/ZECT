"""Register all domain routers on the FastAPI app.

Domain modules own business logic and route handlers; this package is the
public HTTP surface entrypoint required by the Phase 1 target layout.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.domains.project import projects, analytics, export_share, token_controls, generated_outputs, settings
from app.domains.permissions import auth, permissions, secrets_manager
from app.domains.pr_review import github, code_review
from app.domains.agent_run import (
    llm,
    build_phase,
    review_phase,
    deploy_phase,
    model_selection,
    orchestration,
    context_management,
    ultrareview,
    agent_mode,
)
from app.domains.agent_run import mentrix as mentrix_router
from app.domains.audit import audit_trail
from app.domains.integration import (
    jira_integration,
    slack_integration,
    confluence_integration,
    datadog_integration,
    email_integration,
    mcp,
    ci_monitor,
    ci_remediation,
)
from app.domains.workspace import app_runner, autofix, rules_engine, sandbox, diff_viewer
from app.domains.repository import (
    repo_analysis,
    file_explorer,
    git_ops,
    code_index,
    knowledge_base,
    repo_clone,
    repo_browser,
    build_intel,
    file_watcher,
)
from app.domains.repository import lattice as lattice_router
from app.domains.personal_agent import (
    memory,
    dream_engine,
    data_layer,
    data_flywheel,
    transfer,
    skills_engine,
    conversations,
    playbooks,
    scheduler,
    session_insights,
    persistent_sessions,
    user_sessions,
)
from app.domains.voice import realtime, voice_clone


def register_routers(app: FastAPI) -> None:
    app.include_router(projects.router)
    app.include_router(github.router)
    app.include_router(settings.router)
    app.include_router(analytics.router)
    app.include_router(repo_analysis.router)
    app.include_router(auth.router)
    app.include_router(llm.router)
    app.include_router(code_review.router)
    app.include_router(code_review.code_review_alias)
    app.include_router(build_phase.router)
    app.include_router(review_phase.router)
    app.include_router(deploy_phase.router)
    app.include_router(token_controls.router)
    app.include_router(model_selection.router)
    app.include_router(orchestration.router)
    app.include_router(context_management.router)

    app.include_router(audit_trail.router)
    app.include_router(ultrareview.router)
    app.include_router(jira_integration.router)
    app.include_router(slack_integration.router)
    app.include_router(rules_engine.router)
    app.include_router(export_share.router)
    app.include_router(user_sessions.router)
    app.include_router(generated_outputs.router)
    app.include_router(mcp.router)
    app.include_router(app_runner.router)
    app.include_router(file_explorer.router)
    app.include_router(git_ops.router)
    app.include_router(ci_monitor.router)
    app.include_router(autofix.router)

    app.include_router(memory.router)
    app.include_router(dream_engine.router)
    app.include_router(data_layer.router)
    app.include_router(data_flywheel.router)
    app.include_router(permissions.router)
    app.include_router(transfer.router)
    app.include_router(skills_engine.router)

    app.include_router(conversations.router)
    app.include_router(knowledge_base.router)
    app.include_router(playbooks.router)
    app.include_router(scheduler.router)
    app.include_router(secrets_manager.router)
    app.include_router(code_index.router)
    app.include_router(session_insights.router)

    app.include_router(repo_clone.router)
    app.include_router(repo_browser.router)
    app.include_router(build_intel.router)

    app.include_router(agent_mode.router)
    app.include_router(persistent_sessions.router)
    app.include_router(ci_remediation.router)
    app.include_router(sandbox.router)
    app.include_router(realtime.router)
    app.include_router(file_watcher.router)
    app.include_router(diff_viewer.router)

    app.include_router(lattice_router.router)
    app.include_router(mentrix_router.router)
    app.include_router(voice_clone.router)
    app.include_router(confluence_integration.router)
    app.include_router(datadog_integration.router)
    app.include_router(email_integration.router)
