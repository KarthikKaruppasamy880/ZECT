"""Deploy -> CI/CD trigger. Previously /api/deploy/{checklist,runbook} only
ever generated advice text; nothing in ZECT actually deployed anything, which
meant the Permissions Protocol's deploy_.* -> require_approval rule had
nothing to enforce against (dead config, per the Phase F audit). This is the
first real deploy action: a GitHub Actions workflow_dispatch, gated by that
same rule."""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.agent_run.deploy_phase import DeployTriggerRequest, trigger_workflow

CURRENT_USER = Mock(user_id=7, email="dev@zinnia.com")


class TestTriggerWorkflow:
    def test_dispatches_immediately_when_policy_allows(self, monkeypatch):
        monkeypatch.setattr(
            "app.domains.permissions.permissions.check_permission",
            lambda data, db: {"result": "granted", "permission_level": "allow", "audit_id": 1},
        )
        monkeypatch.setattr(
            "app.github_service.trigger_workflow_dispatch",
            lambda owner, repo, workflow_file, ref, inputs: {"dispatched": True, "message": "Dispatched deploy.yml on main"},
        )
        monkeypatch.setattr("app.domains.audit.audit_trail.log_audit", lambda **kw: None)

        req = DeployTriggerRequest(owner="acme", repo="widgets", workflow_file="deploy.yml", ref="main", environment="staging")
        result = trigger_workflow(req, current_user=CURRENT_USER, db=Mock(spec=Session))

        assert result.status == "dispatched"
        assert "Dispatched" in result.message

    def test_returns_pending_approval_when_policy_requires_it(self, monkeypatch):
        monkeypatch.setattr(
            "app.domains.permissions.permissions.check_permission",
            lambda data, db: {"result": "pending_approval", "permission_level": "require_approval", "audit_id": 42},
        )

        req = DeployTriggerRequest(owner="acme", repo="widgets", workflow_file="deploy.yml", environment="production")
        result = trigger_workflow(req, current_user=CURRENT_USER, db=Mock(spec=Session))

        assert result.status == "pending_approval"
        assert result.audit_id == 42
        assert "audits/42/approve" in result.message

    def test_denied_by_policy_raises_403(self, monkeypatch):
        monkeypatch.setattr(
            "app.domains.permissions.permissions.check_permission",
            lambda data, db: {"result": "denied", "permission_level": "never", "audit_id": 1},
        )

        req = DeployTriggerRequest(owner="acme", repo="widgets", workflow_file="deploy.yml")
        with pytest.raises(HTTPException) as exc:
            trigger_workflow(req, current_user=CURRENT_USER, db=Mock(spec=Session))
        assert exc.value.status_code == 403

    def test_retry_with_unapproved_audit_id_is_rejected(self):
        db = Mock(spec=Session)
        db.query().filter().first.return_value = None

        req = DeployTriggerRequest(owner="acme", repo="widgets", workflow_file="deploy.yml", audit_id=999)
        with pytest.raises(HTTPException) as exc:
            trigger_workflow(req, current_user=CURRENT_USER, db=db)
        assert exc.value.status_code == 403

    def test_retry_with_granted_audit_id_dispatches(self, monkeypatch):
        granted_audit = Mock(action="deploy_production", result="granted")
        db = Mock(spec=Session)
        db.query().filter().first.return_value = granted_audit

        monkeypatch.setattr(
            "app.github_service.trigger_workflow_dispatch",
            lambda owner, repo, workflow_file, ref, inputs: {"dispatched": True, "message": "Dispatched deploy.yml on main"},
        )
        monkeypatch.setattr("app.domains.audit.audit_trail.log_audit", lambda **kw: None)

        req = DeployTriggerRequest(
            owner="acme", repo="widgets", workflow_file="deploy.yml", environment="production", audit_id=42
        )
        result = trigger_workflow(req, current_user=CURRENT_USER, db=db)

        assert result.status == "dispatched"

    def test_wrong_action_on_audit_is_rejected(self):
        mismatched_audit = Mock(action="deploy_staging", result="granted")
        db = Mock(spec=Session)
        db.query().filter().first.return_value = mismatched_audit

        req = DeployTriggerRequest(
            owner="acme", repo="widgets", workflow_file="deploy.yml", environment="production", audit_id=42
        )
        with pytest.raises(HTTPException) as exc:
            trigger_workflow(req, current_user=CURRENT_USER, db=db)
        assert exc.value.status_code == 403

    def test_github_dispatch_failure_returns_502(self, monkeypatch):
        monkeypatch.setattr(
            "app.domains.permissions.permissions.check_permission",
            lambda data, db: {"result": "granted", "permission_level": "allow", "audit_id": 1},
        )

        def boom(owner, repo, workflow_file, ref, inputs):
            raise RuntimeError("workflow not found")

        monkeypatch.setattr("app.github_service.trigger_workflow_dispatch", boom)

        req = DeployTriggerRequest(owner="acme", repo="widgets", workflow_file="nope.yml")
        with pytest.raises(HTTPException) as exc:
            trigger_workflow(req, current_user=CURRENT_USER, db=Mock(spec=Session))
        assert exc.value.status_code == 502


class TestTriggerWorkflowDispatchService:
    def test_raises_on_falsy_dispatch_result(self, monkeypatch):
        from app import github_service

        mock_workflow = Mock()
        mock_workflow.create_dispatch.return_value = False
        mock_repo = Mock()
        mock_repo.get_workflow.return_value = mock_workflow
        mock_gh = Mock()
        mock_gh.get_repo.return_value = mock_repo

        monkeypatch.setattr(github_service, "get_github", lambda: mock_gh)

        with pytest.raises(Exception):
            github_service.trigger_workflow_dispatch("acme", "widgets", "deploy.yml", "main", {})

    def test_success_returns_dispatched_dict(self, monkeypatch):
        from app import github_service

        mock_workflow = Mock()
        mock_workflow.create_dispatch.return_value = True
        mock_repo = Mock()
        mock_repo.get_workflow.return_value = mock_workflow
        mock_gh = Mock()
        mock_gh.get_repo.return_value = mock_repo

        monkeypatch.setattr(github_service, "get_github", lambda: mock_gh)

        result = github_service.trigger_workflow_dispatch("acme", "widgets", "deploy.yml", "main", {"env": "prod"})

        assert result["dispatched"] is True
        mock_workflow.create_dispatch.assert_called_once_with("main", {"env": "prod"})
