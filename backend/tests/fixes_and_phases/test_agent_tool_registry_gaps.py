"""Tool registry gaps closed for Phase D: glob_files, git_log, git_branch.

Previously the Coder/Debugger/Explore/Tester roles could only find files by
grepping content (search_code) or listing one directory at a time
(list_dir) -- there was no way to find files by name/path pattern, and no
way to see commit history or branch state without shelling out via
run_command (which is unaudited/free-form, unlike the other typed git_*
tools). See ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase D:
"Tool registry gaps: glob/... for repo tools; git log/branch/... for git
tools." All three are read-only and added to _READ_ONLY_TOOLS, so every
role (Explore/Coder/Tester/Debugger) gets them automatically.
"""

from __future__ import annotations

import subprocess

from app.services.coding_engine.mentrix_agent_tools import execute_tool, resolve_workspace
from app.services.coding_engine.mentrix_lead import ROLE_TOOL_ALLOWLISTS, ROLE_CODER, ROLE_EXPLORE


def _init_repo(root, files):
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "zect-tools@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT Tools"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


class TestGlobFiles:
    def test_finds_files_matching_pattern(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "repo"
        ws.mkdir()
        (ws / "a.py").write_text("x = 1\n", encoding="utf-8")
        (ws / "sub").mkdir()
        (ws / "sub" / "b.py").write_text("y = 2\n", encoding="utf-8")
        (ws / "c.txt").write_text("not python\n", encoding="utf-8")
        root = resolve_workspace(str(ws))

        out = execute_tool("glob_files", {"pattern": "**/*.py"}, workspace=root)
        assert out["ok"] is True
        assert set(out["paths"]) == {"a.py", "sub/b.py"}

    def test_requires_pattern(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "repo"
        ws.mkdir()
        root = resolve_workspace(str(ws))
        out = execute_tool("glob_files", {}, workspace=root)
        assert out["ok"] is False

    def test_excludes_noise_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "repo"
        ws.mkdir()
        (ws / "node_modules").mkdir()
        (ws / "node_modules" / "dep.js").write_text("x\n", encoding="utf-8")
        (ws / "app.js").write_text("y\n", encoding="utf-8")
        root = resolve_workspace(str(ws))

        out = execute_tool("glob_files", {"pattern": "**/*.js"}, workspace=root)
        assert out["ok"] is True
        assert out["paths"] == ["app.js"]

    def test_cannot_escape_workspace_via_parent_segments(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "repo"
        ws.mkdir()
        (tmp_path / "outside.py").write_text("secret\n", encoding="utf-8")
        root = resolve_workspace(str(ws))

        out = execute_tool("glob_files", {"pattern": "../*.py"}, workspace=root)
        assert out["ok"] is True
        assert out["paths"] == []


class TestGitLog:
    def test_returns_commit_history(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        repo = _init_repo(tmp_path / "repo", {"a.py": "x = 1\n"})
        root = resolve_workspace(str(repo))

        out = execute_tool("git_log", {}, workspace=root)
        assert out["ok"] is True
        assert "init" in out["log"]

    def test_respects_max_count(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        repo = _init_repo(tmp_path / "repo", {"a.py": "x = 1\n"})
        for i in range(3):
            (repo / "a.py").write_text(f"x = {i}\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"change {i}"], cwd=repo, check=True, capture_output=True)
        root = resolve_workspace(str(repo))

        out = execute_tool("git_log", {"max_count": 2}, workspace=root)
        assert out["ok"] is True
        assert len(out["log"].splitlines()) == 2


class TestGitBranch:
    def test_reports_current_branch(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        repo = _init_repo(tmp_path / "repo", {"a.py": "x = 1\n"})
        root = resolve_workspace(str(repo))

        out = execute_tool("git_branch", {}, workspace=root)
        assert out["ok"] is True
        assert out["current"] == "main"
        assert "main" in out["branches"]

    def test_lists_new_branch(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        repo = _init_repo(tmp_path / "repo", {"a.py": "x = 1\n"})
        subprocess.run(["git", "branch", "feature-x"], cwd=repo, check=True, capture_output=True)
        root = resolve_workspace(str(repo))

        out = execute_tool("git_branch", {}, workspace=root)
        assert out["ok"] is True
        assert "feature-x" in out["branches"]


class TestNewToolsAreOnEveryRoleAllowlist:
    def test_present_on_explore_and_coder(self):
        for tool in ("glob_files", "git_log", "git_branch"):
            assert tool in ROLE_TOOL_ALLOWLISTS[ROLE_EXPLORE]
            assert tool in ROLE_TOOL_ALLOWLISTS[ROLE_CODER]
