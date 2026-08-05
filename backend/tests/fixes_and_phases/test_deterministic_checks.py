"""Phase 4 Stage C — deterministic finding collectors."""
from app.domains.pr_review.deterministic_checks import (
    HARDCODED_CREDENTIAL_RE,
    collect_deterministic_findings,
)


def test_hardcoded_credential_regex_requires_assignment():
    assert HARDCODED_CREDENTIAL_RE.search('api_key = "sk-live"')
    assert not HARDCODED_CREDENTIAL_RE.search("Generated without OPENAI_API_KEY — replace")


def test_collect_snippet_secrets_and_todo():
    code = 'password = "hunter2"\n# TODO finish\n'
    findings = collect_deterministic_findings(code=code, language="python", file_path="x.py")
    titles = {f["title"] for f in findings}
    assert "Possible hardcoded credential" in titles
    assert "Incomplete implementation marker" in titles
    assert all(f["source"] == "deterministic" for f in findings)


def test_collect_pr_patch_added_lines():
    files = [
        {
            "filename": "cfg.py",
            "status": "modified",
            "patch": "@@ -1,1 +1,2 @@\n keep\n+api_key = 'x'\n",
        }
    ]
    findings = collect_deterministic_findings(files=files)
    assert any(f["file"] == "cfg.py" and f.get("line") == 2 for f in findings)


def test_collect_without_db_skips_rules():
    findings = collect_deterministic_findings(code="print(1)\n", db=None)
    assert isinstance(findings, list)
