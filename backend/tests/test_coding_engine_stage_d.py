"""Phase 2 Stage D — isolation harden (Docker optional; worktree default)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.coding_engine.isolation import (
    DEFAULT_SANDBOX_IMAGE,
    resolve_isolation,
    restricted_sandbox_env,
)
from app.services.coding_engine.workspace import (
    WorkspaceError,
    dispose_isolated_workspace,
    provision_isolated_workspace,
)


def _init_git_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@zect.local"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT Test"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


def test_restricted_sandbox_env_filters_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    monkeypatch.setenv("ZECT_CODING_ENGINE_API_KEY", "engine-secret")
    monkeypatch.setenv("PATH", "/usr/bin")
    env = restricted_sandbox_env({"ZECT_RUN_ID": "r1", "OPENAI_API_KEY": "nope"})
    assert env.get("ZECT_RUN_ID") == "r1"
    assert "OPENAI_API_KEY" not in env
    assert "ZECT_CODING_ENGINE_API_KEY" not in env
    assert "sk-secret" not in str(env)


def test_resolve_isolation_defaults_worktree(monkeypatch):
    monkeypatch.delenv("ZECT_CODING_ENGINE_ISOLATION", raising=False)
    monkeypatch.setattr(
        "app.services.coding_engine.isolation.docker_available",
        lambda: False,
    )
    plan = resolve_isolation()
    assert plan["isolation"] == "worktree"
    assert plan["docker_available"] is False


def test_resolve_isolation_docker_falls_back(monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE_ISOLATION", "docker")
    monkeypatch.delenv("ZECT_CODING_ENGINE_ISOLATION_STRICT", raising=False)
    monkeypatch.setattr(
        "app.services.coding_engine.isolation.docker_available",
        lambda: False,
    )
    plan = resolve_isolation()
    assert plan["isolation"] == "worktree"
    assert plan["detail"] == "docker_unavailable_fallback_worktree"


def test_resolve_isolation_docker_strict_unavailable(monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE_ISOLATION", "docker")
    monkeypatch.setenv("ZECT_CODING_ENGINE_ISOLATION_STRICT", "1")
    monkeypatch.setattr(
        "app.services.coding_engine.isolation.docker_available",
        lambda: False,
    )
    plan = resolve_isolation()
    assert plan["isolation"] == "unavailable"


def test_provision_isolated_worktree_without_docker(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE_ISOLATION", "docker")
    monkeypatch.delenv("ZECT_CODING_ENGINE_ISOLATION_STRICT", raising=False)
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_ENGINE_WORKSPACE_ROOT", str(tmp_path / "engine"))
    (tmp_path / "engine").mkdir()
    monkeypatch.setattr(
        "app.services.coding_engine.isolation.docker_available",
        lambda: False,
    )
    repo = _init_git_repo(tmp_path / "repo")
    ws = provision_isolated_workspace(repo_path=str(repo), run_id="d1")
    assert ws.isolation == "worktree"
    assert ws.container_id is None
    assert "fallback" in (ws.isolation_note or "")
    disposed = dispose_isolated_workspace(
        workspace_id=ws.workspace_id,
        repo_path=ws.repo_path,
        workspace_path=ws.path,
    )
    assert disposed["removed"] is True


def test_provision_isolated_strict_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE_ISOLATION", "docker")
    monkeypatch.setenv("ZECT_CODING_ENGINE_ISOLATION_STRICT", "1")
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "app.services.coding_engine.isolation.docker_available",
        lambda: False,
    )
    repo = _init_git_repo(tmp_path / "repo")
    with pytest.raises(WorkspaceError):
        provision_isolated_workspace(repo_path=str(repo), run_id="strict1")


def test_provision_isolated_with_mocked_docker(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE_ISOLATION", "docker")
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_ENGINE_WORKSPACE_ROOT", str(tmp_path / "engine"))
    (tmp_path / "engine").mkdir()
    monkeypatch.setattr(
        "app.services.coding_engine.isolation.docker_available",
        lambda: True,
    )

    box = MagicMock()
    box.container_id = "cid123"
    box.image = DEFAULT_SANDBOX_IMAGE
    monkeypatch.setattr(
        "app.services.coding_engine.docker_sandbox.start_workspace_sandbox",
        lambda **kwargs: box,
    )
    stopped = {"ok": False}

    def _stop(cid):
        stopped["ok"] = cid == "cid123"
        return True

    monkeypatch.setattr(
        "app.services.coding_engine.docker_sandbox.stop_workspace_sandbox",
        _stop,
    )

    repo = _init_git_repo(tmp_path / "repo")
    ws = provision_isolated_workspace(repo_path=str(repo), run_id="dock1")
    assert ws.isolation == "docker"
    assert ws.container_id == "cid123"
    dispose_isolated_workspace(
        workspace_id=ws.workspace_id,
        repo_path=ws.repo_path,
        workspace_path=ws.path,
        container_id=ws.container_id,
    )
    assert stopped["ok"] is True


def test_health_includes_isolation(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mock")
    monkeypatch.setenv("ZECT_CODING_ENGINE_ISOLATION", "worktree")
    monkeypatch.setattr(
        "app.services.coding_engine.isolation.docker_available",
        lambda: False,
    )
    resp = client.get("/api/coding-engine/health", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["isolation"] == "worktree"
    assert body["docker_available"] is False
    assert "openhands" not in resp.text.lower()
