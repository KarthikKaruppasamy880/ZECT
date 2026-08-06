"""Unit tests for Mentrix batched Build helpers + incomplete expected list."""

from __future__ import annotations

from app.services.forge_loop.batch_build import (
    MENTRIX_BUILD_BATCH_SIZE,
    attach_files_expected,
    chunk_files,
    collect_files_expected,
    normalize_file_paths,
)
from app.services.quality.incomplete_files import check_incomplete_files


def test_normalize_skips_placeholders():
    assert normalize_file_paths(["a.py", "(new files)", "a.py", " b.py "]) == ["a.py", "b.py"]


def test_collect_files_expected_prefers_top_level():
    plan = {
        "files_expected": ["src/a.py", "src/b.py"],
        "steps": [{"files": ["ignored.py"]}],
    }
    assert collect_files_expected(plan) == ["src/a.py", "src/b.py"]


def test_collect_files_expected_from_steps():
    plan = {
        "steps": [
            {"files": ["one.py", "(skip)"]},
            {"files": ["two.py"]},
        ]
    }
    assert collect_files_expected(plan) == ["one.py", "two.py"]


def test_chunk_files_respects_batch_size(monkeypatch):
    monkeypatch.setenv("MENTRIX_BUILD_BATCH_SIZE", "2")
    # Re-import size via chunk default arg — pass size explicitly
    assert chunk_files(["a", "b", "c", "d", "e"], 2) == [["a", "b"], ["c", "d"], ["e"]]
    assert chunk_files([], 2) == []
    assert MENTRIX_BUILD_BATCH_SIZE >= 1


def test_attach_files_expected_merges():
    plan = attach_files_expected({"steps": [{"files": ["a.py"]}]}, ["b.py", "a.py"])
    assert plan["files_expected"] == ["a.py", "b.py"]


def test_incomplete_blocks_missing_expected():
    out = check_incomplete_files(
        files_expected=["a.py", "b.py"],
        files_written=["a.py"],
        file_contents={"a.py": "print(1)\n"},
    )
    assert out["ok"] is False
    assert any("missing_files" in b for b in out["blockers"])


def test_incomplete_ok_when_all_written():
    out = check_incomplete_files(
        files_expected=["a.py"],
        files_written=["a.py"],
        file_contents={"a.py": "print(1)\n"},
    )
    assert out["ok"] is True
