"""Phase 2 Stage A — coding engine factory, health, worktree provisioner."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.adapters.coding_runtime import (
    MockCodingRuntime,
    coding_engine_health,
    get_coding_runtime,
    selected_coding_engine,
)
from app.adapters.coding_engine_remote import CodingEngineConfigError, RemoteCodingEngine
from app.services.coding_engine.workspace import dispose_worktree, provision_worktree


def _init_git_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@zect.local"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT Test"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


def test_factory_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("ZECT_CODING_ENGINE", raising=False)
    from app.adapters.coding_runtime import reset_coding_runtime_for_tests

    reset_coding_runtime_for_tests()
    assert selected_coding_engine() == "mock"
    rt = get_coding_runtime()
    assert isinstance(rt, MockCodingRuntime)
    health = coding_engine_health()
    assert health["provider"] == "mock"
    assert health["ready"] is True


def test_factory_remote_requires_config(monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "remote")
    monkeypatch.delenv("ZECT_CODING_ENGINE_URL", raising=False)
    monkeypatch.delenv("ZECT_CODING_ENGINE_API_KEY", raising=False)
    from app.adapters.coding_runtime import reset_coding_runtime_for_tests

    reset_coding_runtime_for_tests()
    with pytest.raises(CodingEngineConfigError):
        get_coding_runtime()
    health = coding_engine_health()
    assert health["provider"] == "remote"
    assert health["ready"] is False


def test_remote_health_ok_with_mocked_http(monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "remote")
    monkeypatch.setenv("ZECT_CODING_ENGINE_URL", "http://engine.test")
    monkeypatch.setenv("ZECT_CODING_ENGINE_API_KEY", "secret-key")

    class _Resp:
        status_code = 200
        text = '{"version":"1.2.3"}'

        def json(self):
            return {"version": "1.2.3", "status": "ok"}

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None):
            assert "secret-key" in (headers or {}).get("X-Session-API-Key", "")
            assert url.rstrip("/").endswith("health") or "health" in url
            return _Resp()

    monkeypatch.setattr("app.adapters.coding_engine_remote.httpx.Client", _Client)
    engine = RemoteCodingEngine.from_env()
    health = engine.health()
    assert health["provider"] == "remote"
    assert health["ready"] is True
    assert health["version"] == "1.2.3"
    assert "secret" not in str(health).lower()


def test_provision_and_dispose_worktree(tmp_path, monkeypatch):
    repo = _init_git_repo(tmp_path / "repo")
    engine_root = tmp_path / "engine-ws"
    engine_root.mkdir()
    monkeypatch.setenv("ZECT_ENGINE_WORKSPACE_ROOT", str(engine_root))
    # Ensure allowlist includes both
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))

    ws = provision_worktree(repo_path=str(repo), run_id="abc-123")
    assert Path(ws.path).is_dir()
    assert (Path(ws.path) / "README.md").is_file()
    assert ws.branch.startswith("zect/run-")
    # Make a local change so dispose captures a patch
    (Path(ws.path) / "README.md").write_text("hello\nchanged\n", encoding="utf-8")

    result = dispose_worktree(
        workspace_id=ws.workspace_id,
        repo_path=ws.repo_path,
        workspace_path=ws.path,
        preserve_artifacts=True,
    )
    assert result["removed"] is True
    assert result["artifact_patch"]
    assert Path(result["artifact_patch"]).is_file()
    assert not Path(ws.path).exists()


def test_coding_engine_health_endpoint(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ZECT_CODING_ENGINE", "mock")
    from app.adapters.coding_runtime import reset_coding_runtime_for_tests

    reset_coding_runtime_for_tests()
    resp = client.get("/api/coding-engine/health", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "mock"
    assert body["ready"] is True
    assert body["selected"] == "mock"
    # Branding: public payload uses only mock|remote
    assert "openhands" not in resp.text.lower()


def test_coding_engine_workspace_api(client, auth_headers, tmp_path, monkeypatch):
    repo = _init_git_repo(tmp_path / "api-repo")
    engine_root = tmp_path / "api-engine"
    engine_root.mkdir()
    monkeypatch.setenv("ZECT_ENGINE_WORKSPACE_ROOT", str(engine_root))
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))

    created = client.post(
        "/api/coding-engine/workspaces",
        headers=auth_headers,
        json={"repo_path": str(repo), "run_id": "api1"},
    )
    assert created.status_code == 200, created.text
    data = created.json()
    assert data["isolation"] == "worktree"
    assert data["provider"] in ("mock", "remote")
    assert Path(data["path"]).is_dir()

    disposed = client.post(
        "/api/coding-engine/workspaces/dispose",
        headers=auth_headers,
        json={
            "workspace_id": data["workspace_id"],
            "repo_path": data["repo_path"],
            "workspace_path": data["path"],
        },
    )
    assert disposed.status_code == 200, disposed.text
    assert disposed.json()["removed"] is True
