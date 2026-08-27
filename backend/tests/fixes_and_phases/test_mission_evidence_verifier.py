"""EvidenceVerifier for the real Approve & Build mission flow.

Closes a reconciliation gap: a pre-existing EvidenceVerifier class was real
code but wired only to a separate WorkItem/automation-loop subsystem, never
called from coding_engine/lifecycle.py. The golden-fixture acceptance flow
names "EvidenceVerifier" as an explicit step between Ultra Review and
awaiting_git_approval, so this had to independently re-check the mission's
own claims against the actual worktree/git state and event timeline --
not just trust self-reported flags -- and actually gate the phase transition
on failure, the same way Ultra Review already does."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.coding_engine.lifecycle import approve_plan, start_mission, verify_mission_evidence


def _init_repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "zect-ca@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ZECT CA"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


def _head(root: Path) -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("ZECT_CODING_MISSIONS_DIR", str(tmp_path / "missions"))
    monkeypatch.setenv("MENTRIX_PR_DRY_RUN", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


class TestVerifyMissionEvidenceUnit:
    """Direct checks against real filesystem/git state -- no mocking."""

    def test_happy_path_no_findings(self, tmp_path):
        repo_root = _init_repo(tmp_path / "r1", {"calc.py": "def add(a, b):\n    return a + b\n"})
        head = _head(repo_root)
        (repo_root / "calc.py").write_text("def add(a, b):\n    return a + b  # patched\n", encoding="utf-8")
        repo = {
            "repository_id": 1,
            "files": ["calc.py"],
            "diff": "diff --git a/calc.py b/calc.py\n+    return a + b  # patched\n",
            "head_sha": head,
            "committed_shas": [],
            "browser_verification": {},
        }
        out = verify_mission_evidence({"events": []}, repo, repo_root)
        assert out["ok"] is True
        assert out["findings"] == []

    def test_claimed_file_missing_is_critical(self, tmp_path):
        repo_root = _init_repo(tmp_path / "r2", {"calc.py": "x = 1\n"})
        repo = {
            "repository_id": 1,
            "files": ["never_written.py"],
            "diff": "",
            "head_sha": _head(repo_root),
            "committed_shas": [],
            "browser_verification": {},
        }
        out = verify_mission_evidence({"events": []}, repo, repo_root)
        assert out["ok"] is False
        codes = [f["code"] for f in out["findings"]]
        assert "claimed_file_missing" in codes
        assert all(f["severity"] == "critical" for f in out["findings"] if f["code"] == "claimed_file_missing")

    def test_worktree_sha_drift_is_critical(self, tmp_path):
        repo_root = _init_repo(tmp_path / "r3", {"calc.py": "x = 1\n"})
        stale_head = _head(repo_root)
        # Something external advances HEAD after the mission recorded head_sha.
        (repo_root / "other.py").write_text("y = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "external change"], cwd=repo_root, check=True, capture_output=True)
        repo = {
            "repository_id": 1,
            "files": [],
            "diff": "",
            "head_sha": stale_head,
            "committed_shas": [],
            "browser_verification": {},
        }
        out = verify_mission_evidence({"events": []}, repo, repo_root)
        assert out["ok"] is False
        assert any(f["code"] == "worktree_sha_drift" for f in out["findings"])

    def test_browser_verified_without_timeline_evidence_is_critical(self, tmp_path):
        repo_root = _init_repo(tmp_path / "r4", {"calc.py": "x = 1\n"})
        repo = {
            "repository_id": 7,
            "files": [],
            "diff": "",
            "head_sha": _head(repo_root),
            "committed_shas": [],
            "browser_verification": {"ran": True, "verified": True},
        }
        out = verify_mission_evidence({"events": []}, repo, repo_root)
        assert out["ok"] is False
        assert any(f["code"] == "browser_verification_unevidenced" for f in out["findings"])

    def test_browser_verified_with_matching_event_passes(self, tmp_path):
        repo_root = _init_repo(tmp_path / "r5", {"calc.py": "x = 1\n"})
        repo = {
            "repository_id": 7,
            "files": [],
            "diff": "",
            "head_sha": _head(repo_root),
            "committed_shas": [],
            "browser_verification": {"ran": True, "verified": True},
        }
        mission = {
            "events": [
                {"event": "browser_verify_result", "message": "ok", "data": {"repository_id": 7, "ok": True}}
            ]
        }
        out = verify_mission_evidence(mission, repo, repo_root)
        assert out["ok"] is True

    def test_diff_missing_claimed_file_is_warning_not_blocking(self, tmp_path):
        """_collect_diff truncates at 12000 chars -- a claimed file legitimately
        absent from a *short* diff is suspicious enough to record, but must
        never block on its own (it could be a rename/format-only change the
        diff renders differently)."""
        repo_root = _init_repo(tmp_path / "r6", {"calc.py": "x = 1\n"})
        repo = {
            "repository_id": 1,
            "files": ["calc.py"],
            "diff": "diff --git a/unrelated.py b/unrelated.py\n+z = 1\n",
            "head_sha": _head(repo_root),
            "committed_shas": [],
            "browser_verification": {},
        }
        out = verify_mission_evidence({"events": []}, repo, repo_root)
        assert out["ok"] is True
        assert any(f["code"] == "claimed_file_not_in_diff" and f["severity"] == "warning" for f in out["findings"])


class TestEvidenceVerifierWiredIntoTheRealMissionLoop:
    def test_passing_mission_reaches_awaiting_git_approval_with_evidence_recorded(self, ws):
        repo = _init_repo(
            ws / "backend",
            {
                "calc.py": "def add(a, b):\n    return a - b\n",
                "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            },
        )
        m = start_mission(
            goal="Fix add()",
            roots=[{"id": 1, "label": "backend", "path": str(repo)}],
            patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
            workspace_parent=str(ws / "wt"),
        )
        m = approve_plan(m["id"])
        assert m["phase"] == "awaiting_git_approval", m
        verification = m["repos"][0]["evidence_verification"]
        assert verification["ok"] is True
        events = [e["event"] for e in m["events"]]
        assert "evidence_verify_result" in events

    def test_evidence_failure_blocks_the_mission(self, ws):
        repo = _init_repo(
            ws / "backend",
            {
                "calc.py": "def add(a, b):\n    return a - b\n",
                "tests/test_calc.py": "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            },
        )
        m = start_mission(
            goal="Fix add()",
            roots=[{"id": 1, "label": "backend", "path": str(repo)}],
            patches_by_repo={"1": [{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]},
            workspace_parent=str(ws / "wt"),
        )
        with patch(
            "app.services.coding_engine.lifecycle.verify_mission_evidence",
            return_value={"ok": False, "findings": [{"severity": "critical", "code": "claimed_file_missing", "detail": "x"}]},
        ):
            m = approve_plan(m["id"])

        assert m["phase"] == "blocked", m
        repo_out = m["repos"][0]
        assert "evidence_verification_failed" in repo_out["blocker"]
        assert repo_out["evidence_verification"]["ok"] is False
        events = [e for e in m["events"] if e["event"] == "evidence_verify_result"]
        assert events and events[-1]["data"]["ok"] is False
        blocked_events = [e for e in m["events"] if e["event"] == "blocked"]
        assert any("EvidenceVerifier" in e["message"] for e in blocked_events)
