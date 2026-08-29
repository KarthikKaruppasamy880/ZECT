"""Lint runner unit tests (no FastAPI / SQLAlchemy import)."""

from app.services.quality.lint_runner import run_lint


def test_lint_skip_without_workspace():
    out = run_lint("")
    assert out["skipped"] is True
    assert "ok" in out


def test_lint_python_compile(tmp_path):
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    out = run_lint(str(tmp_path))
    assert out["skipped"] is False or out["ok"] is True
    if not out["skipped"]:
        assert out["ok"] is True
