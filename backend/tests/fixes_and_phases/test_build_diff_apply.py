"""Unit tests for Phase 2 — diff-based review before Build writes to disk.

Covers: diff computed when the target file already exists (both build_phase.py's
HTTP endpoint and build_phase_svc.py's internal path), write_to_repo's existing
behavior is unchanged (no regression), and the new /apply endpoint's path-safety
check and audit logging.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.models import Repo


def _fake_completed(file_path="auth.py", code="def login():\n    return True\n"):
    return {
        "content": f"FILE_PATH: {file_path}\nLANGUAGE: python\nEXPLANATION: ok\n```python\n{code}```",
        "tokens_used": 5, "prompt_tokens": 3, "completion_tokens": 2,
        "finish_reason": "stop", "structure_ok": True,
    }


class TestGenerateCoreComputesDiff:
    def test_diff_present_when_file_already_exists(self, tmp_path, monkeypatch):
        from app.services.phases import build_phase_svc

        (tmp_path / "auth.py").write_text("def login():\n    return False\n", encoding="utf-8")
        repo = Mock(spec=Repo, id=1, local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "app.services.build_intel.retriever.search",
            lambda db, repo_id, query, top_k=6, user_id=None: [],
        )
        monkeypatch.setattr("app.routers.llm._build_repo_context", lambda db, repo_id, max_chars=4000: "")
        monkeypatch.setattr("app.services.context_store.load", lambda db, user_id, page, keys=None: {})
        monkeypatch.setattr(
            "app.services.quality.truncation.complete_with_continuations",
            lambda client, messages, **kw: _fake_completed(),
        )
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        class Req:
            plan_step = "fix login"
            project_context = None
            tech_stack = ""
            repo_id = 1
            file_path = "auth.py"
            write_to_repo = False

        result = build_phase_svc._generate_core(Req(), db=db, workspace="")

        assert result["file_existed"] is True
        assert result["diff"] is not None
        assert result["diff"]["stats"]["additions"] >= 1 or result["diff"]["stats"]["deletions"] >= 1
        # write_to_repo was False — file on disk must be untouched
        assert (tmp_path / "auth.py").read_text() == "def login():\n    return False\n"

    def test_no_diff_when_file_is_new(self, tmp_path, monkeypatch):
        from app.services.phases import build_phase_svc

        repo = Mock(spec=Repo, id=1, local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "app.services.build_intel.retriever.search",
            lambda db, repo_id, query, top_k=6, user_id=None: [],
        )
        monkeypatch.setattr("app.routers.llm._build_repo_context", lambda db, repo_id, max_chars=4000: "")
        monkeypatch.setattr("app.services.context_store.load", lambda db, user_id, page, keys=None: {})
        monkeypatch.setattr(
            "app.services.quality.truncation.complete_with_continuations",
            lambda client, messages, **kw: _fake_completed(file_path="new_file.py"),
        )
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        class Req:
            plan_step = "add feature"
            project_context = None
            tech_stack = ""
            repo_id = 1
            file_path = "new_file.py"
            write_to_repo = False

        result = build_phase_svc._generate_core(Req(), db=db, workspace="")

        assert result["file_existed"] is False
        assert result["diff"] is None

    def test_write_to_repo_still_writes_regardless_of_diff(self, tmp_path, monkeypatch):
        """Confirms Phase 2 is purely additive — write_to_repo's existing
        behavior (used by agent_mode.py's automated orchestrator) is unchanged."""
        from app.services.phases import build_phase_svc

        (tmp_path / "auth.py").write_text("old content\n", encoding="utf-8")
        repo = Mock(spec=Repo, id=1, local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "app.services.build_intel.retriever.search",
            lambda db, repo_id, query, top_k=6, user_id=None: [],
        )
        monkeypatch.setattr("app.routers.llm._build_repo_context", lambda db, repo_id, max_chars=4000: "")
        monkeypatch.setattr("app.services.context_store.load", lambda db, user_id, page, keys=None: {})
        monkeypatch.setattr(
            "app.services.quality.truncation.complete_with_continuations",
            lambda client, messages, **kw: _fake_completed(code="def login():\n    return True\n"),
        )
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        class Req:
            plan_step = "fix login"
            project_context = None
            tech_stack = ""
            repo_id = 1
            file_path = "auth.py"
            write_to_repo = True

        result = build_phase_svc._generate_core(Req(), db=db, workspace="")

        assert result["file_existed"] is True  # diff still computed
        assert result["diff"] is not None
        assert "auth.py" in result["files_written"]
        assert "def login():\n    return True" in (tmp_path / "auth.py").read_text()


class TestApplyEndpoint:
    """apply_generated_code — the review-then-write path."""

    def test_writes_file_and_logs_audit(self, tmp_path, monkeypatch):
        from app.routers.build_phase import ApplyRequest, apply_generated_code

        repo = Mock(spec=Repo, id=1, clone_status="cloned", local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo

        audit_calls = []
        monkeypatch.setattr(
            "app.routers.build_phase.log_audit",
            lambda **kw: audit_calls.append(kw),
        )

        current_user = Mock(user_id=42)
        req = ApplyRequest(repo_id=1, file_path="src/new.py", code="print('hi')\n")

        result = apply_generated_code(req, current_user=current_user, db=db)

        assert result.written is True
        assert (tmp_path / "src" / "new.py").read_text() == "print('hi')\n"
        assert audit_calls[0]["action"] == "build_apply"
        assert audit_calls[0]["user_id"] == 42

    def test_rejects_path_traversal(self, tmp_path):
        from app.routers.build_phase import ApplyRequest, apply_generated_code
        from fastapi import HTTPException

        repo = Mock(spec=Repo, id=1, clone_status="cloned", local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo
        current_user = Mock(user_id=1)

        req = ApplyRequest(repo_id=1, file_path="../../etc/passwd", code="malicious")

        with pytest.raises(HTTPException) as exc_info:
            apply_generated_code(req, current_user=current_user, db=db)
        assert exc_info.value.status_code == 400
        assert "escapes" in exc_info.value.detail

    def test_rejects_uncloned_repo(self, tmp_path):
        from app.routers.build_phase import ApplyRequest, apply_generated_code
        from fastapi import HTTPException

        repo = Mock(spec=Repo, id=1, clone_status="not_cloned", local_path=None)
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo
        current_user = Mock(user_id=1)

        req = ApplyRequest(repo_id=1, file_path="x.py", code="x = 1")

        with pytest.raises(HTTPException) as exc_info:
            apply_generated_code(req, current_user=current_user, db=db)
        assert exc_info.value.status_code == 400

    def test_allows_legitimate_nested_path(self, tmp_path, monkeypatch):
        from app.routers.build_phase import ApplyRequest, apply_generated_code

        repo = Mock(spec=Repo, id=1, clone_status="cloned", local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo
        monkeypatch.setattr("app.routers.build_phase.log_audit", lambda **kw: None)
        current_user = Mock(user_id=1)

        req = ApplyRequest(repo_id=1, file_path="a/b/c/deep.py", code="x = 1\n")
        result = apply_generated_code(req, current_user=current_user, db=db)

        assert result.written is True
        assert (tmp_path / "a" / "b" / "c" / "deep.py").read_text() == "x = 1\n"
