"""Unit tests for Phase 3 (multi-file coordinated generation) and Phase 4
(rule-violation pre-check + verify-and-fix, reusing rules_engine.py and
autofix.py's existing, real implementations)."""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models import Repo
from app.routers.build_phase import (
    MAX_MULTI_FILE_TARGETS,
    ApplyFileEntry,
    ApplyMultiRequest,
    MultiFileBuildRequest,
    VerifyAndFixRequest,
    _parse_multi_file_response,
    apply_multi_file,
    generate_multi_file,
    verify_and_fix,
)


MULTI_FILE_SAMPLE = """Some preamble the model might add.
===FILE: src/auth.py===
LANGUAGE: python
EXPLANATION: Login endpoint
```python
def login():
    return True
```
===END FILE===
===FILE: src/auth_test.py===
LANGUAGE: python
EXPLANATION: Test for login
```python
def test_login():
    assert login()
```
===END FILE===
"""


class TestParseMultiFileResponse:
    def test_parses_two_files_in_order(self):
        parsed = _parse_multi_file_response(MULTI_FILE_SAMPLE)
        assert len(parsed) == 2
        assert parsed[0]["file_path"] == "src/auth.py"
        assert parsed[1]["file_path"] == "src/auth_test.py"

    def test_extracts_language_explanation_and_code(self):
        parsed = _parse_multi_file_response(MULTI_FILE_SAMPLE)
        assert parsed[0]["language"] == "python"
        assert parsed[0]["explanation"] == "Login endpoint"
        assert "def login():" in parsed[0]["generated_code"]
        assert "```" not in parsed[0]["generated_code"]

    def test_empty_content_returns_no_files(self):
        assert _parse_multi_file_response("") == []
        assert _parse_multi_file_response("no markers here at all") == []

    def test_single_file_block_parses_correctly(self):
        content = "===FILE: only.py===\nLANGUAGE: python\nEXPLANATION: x\n```python\npass\n```\n===END FILE==="
        parsed = _parse_multi_file_response(content)
        assert len(parsed) == 1
        assert parsed[0]["file_path"] == "only.py"


class TestGenerateMultiFile:
    def test_rejects_empty_target_files(self):
        from fastapi import HTTPException

        req = MultiFileBuildRequest(plan_step="x", target_files=[])
        with pytest.raises(HTTPException) as exc:
            generate_multi_file(req, current_user=Mock(user_id=1), db=Mock(spec=Session))
        assert exc.value.status_code == 400

    def test_rejects_too_many_target_files(self):
        from fastapi import HTTPException

        req = MultiFileBuildRequest(
            plan_step="x", target_files=[f"f{i}.py" for i in range(MAX_MULTI_FILE_TARGETS + 1)]
        )
        with pytest.raises(HTTPException) as exc:
            generate_multi_file(req, current_user=Mock(user_id=1), db=Mock(spec=Session))
        assert exc.value.status_code == 400

    def test_generates_and_diffs_multiple_files(self, tmp_path, monkeypatch):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "auth.py").write_text("def login():\n    return False\n", encoding="utf-8")

        repo = Mock(spec=Repo, id=1, clone_status="cloned", local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "app.services.build_intel.retriever.search",
            lambda db, repo_id, query, top_k=4, user_id=None: [],
        )
        monkeypatch.setattr("app.routers.llm._build_repo_context", lambda db, repo_id, max_chars=4000: "")
        monkeypatch.setattr(
            "app.services.quality.truncation.complete_with_continuations",
            lambda client, messages, **kw: {
                "content": MULTI_FILE_SAMPLE, "tokens_used": 20, "prompt_tokens": 15, "completion_tokens": 5,
                "finish_reason": "stop", "structure_ok": True,
            },
        )
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)
        # db.query(Repo)/db.query(Rule) share the same mock chain here (Mock
        # ignores call args) — .first() is set above for the Repo lookup,
        # .all() below is for evaluate_rules' Rule query (no active rules).
        db.query().filter().all.return_value = []

        req = MultiFileBuildRequest(plan_step="fix login", target_files=["src/auth.py", "src/auth_test.py"], repo_id=1)
        result = generate_multi_file(req, current_user=Mock(user_id=1), db=db)

        assert len(result.files) == 2
        assert result.files[0].file_path == "src/auth.py"
        assert result.files[0].file_existed is True
        assert result.files[0].diff is not None
        assert result.files[1].file_path == "src/auth_test.py"
        assert result.files[1].file_existed is False
        assert result.files[1].diff is None


class TestApplyMultiFile:
    def test_writes_all_files_and_commits_once(self, tmp_path, monkeypatch):
        repo = Mock(spec=Repo, id=1, clone_status="cloned", local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo
        monkeypatch.setattr("app.routers.build_phase.log_audit", lambda **kw: None)

        commit_calls = []
        monkeypatch.setattr(
            "app.routers.git_ops.git_commit",
            lambda req: (commit_calls.append(req), {"status": "committed", "message": "ok"})[1],
        )

        req = ApplyMultiRequest(
            repo_id=1,
            files=[
                ApplyFileEntry(file_path="a.py", code="a = 1\n"),
                ApplyFileEntry(file_path="b.py", code="b = 2\n"),
            ],
            commit_message="feat: add a and b",
        )
        result = apply_multi_file(req, current_user=Mock(user_id=7), db=db)

        assert set(result.written) == {"a.py", "b.py"}
        assert (tmp_path / "a.py").read_text() == "a = 1\n"
        assert (tmp_path / "b.py").read_text() == "b = 2\n"
        assert result.committed is True
        assert commit_calls[0].files == ["a.py", "b.py"]

    def test_rejects_empty_files_list(self):
        from fastapi import HTTPException

        req = ApplyMultiRequest(repo_id=1, files=[])
        with pytest.raises(HTTPException) as exc:
            apply_multi_file(req, current_user=Mock(user_id=1), db=Mock(spec=Session))
        assert exc.value.status_code == 400

    def test_path_traversal_in_batch_rejected(self, tmp_path):
        from fastapi import HTTPException

        repo = Mock(spec=Repo, id=1, clone_status="cloned", local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo

        req = ApplyMultiRequest(repo_id=1, files=[ApplyFileEntry(file_path="../../etc/passwd", code="x")])
        with pytest.raises(HTTPException) as exc:
            apply_multi_file(req, current_user=Mock(user_id=1), db=db)
        assert exc.value.status_code == 400


class TestVerifyAndFix:
    """Thin wrapper over autofix.run_and_fix — confirms it's actually called
    with the repo's real local_path as cwd, not a new loop reimplemented here."""

    def test_rejects_uncloned_repo(self):
        from fastapi import HTTPException

        repo = Mock(spec=Repo, clone_status="not_cloned", local_path=None)
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo

        req = VerifyAndFixRequest(repo_id=1, test_command="pytest")
        with pytest.raises(HTTPException) as exc:
            verify_and_fix(req, current_user=Mock(user_id=1), db=db)
        assert exc.value.status_code == 400

    def test_delegates_to_autofix_run_and_fix_with_repo_cwd(self, tmp_path, monkeypatch):
        repo = Mock(spec=Repo, clone_status="cloned", local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo
        monkeypatch.setattr("app.routers.build_phase.log_audit", lambda **kw: None)

        captured = {}

        def fake_run_and_fix(req):
            captured["command"] = req.command
            captured["cwd"] = req.cwd
            captured["max_retries"] = req.max_retries
            from app.routers.autofix import AutoFixResponse
            return AutoFixResponse(success=True, total_attempts=1, steps=[], final_output="ok", tokens_used=0)

        monkeypatch.setattr("app.routers.autofix.run_and_fix", fake_run_and_fix)

        req = VerifyAndFixRequest(repo_id=1, test_command="pytest -x", max_retries=2)
        result = verify_and_fix(req, current_user=Mock(user_id=1), db=db)

        assert captured["command"] == "pytest -x"
        assert captured["cwd"] == str(tmp_path)
        assert captured["max_retries"] == 2
        assert result.success is True
