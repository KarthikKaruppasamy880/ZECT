"""G1–G4 Graphify/Lattice spine: incremental ingest, tests, CODEOWNERS, cross-repo evidence."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from app.services.lattice.cross_repo import CrossRepoEdgeError, make_cross_repo_edge
from app.services.lattice.graphify_snapshot import graphify_snapshot
from app.services.lattice.indexer import ingest_path, query_graph


def _git_init(root: Path) -> None:
    subprocess.check_call(["git", "init", "-b", "main"], cwd=root, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "zect@example.com"], cwd=root)
    subprocess.check_call(["git", "config", "user.name", "ZECT"], cwd=root)


def test_ingest_test_nodes_codeowners_and_pollution_skip():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pkg").mkdir()
        (root / "pkg" / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests" / "test_app.py").write_text("def test_run():\n    assert True\n", encoding="utf-8")
        (root / "vendor").mkdir()
        (root / "vendor" / "lib.py").write_text("SECRET = 1\n", encoding="utf-8")
        (root / ".env").write_text("X=1\n", encoding="utf-8")
        (root / "CODEOWNERS").write_text("* @zect-owners\n", encoding="utf-8")
        g = ingest_path(str(root), project_key="g2-fixture", force=True)
        assert g.files_indexed >= 2
        tests = [n for n in g.nodes if n.kind == "test"]
        assert tests, "expected test nodes"
        assert not any(n.path.replace("\\\\", "/").startswith("vendor/") for n in g.nodes)
        owned = [n for n in g.nodes if n.kind == "file" and n.group == "@zect-owners"]
        assert owned


def test_incremental_skip_when_sha_unchanged():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
        _git_init(root)
        subprocess.check_call(["git", "add", "."], cwd=root, stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "commit", "-m", "init"], cwd=root, stdout=subprocess.DEVNULL)
        first = ingest_path(str(root), project_key="inc-fix", force=True)
        assert first.incremental is False
        assert first.commit_sha
        second = ingest_path(str(root), project_key="inc-fix", force=False)
        assert second.incremental is True
        assert second.commit_sha == first.commit_sha


def test_parse_failure_isolated():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "ok.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
        (root / "bad.py").write_text("def broken(\n", encoding="utf-8")
        g = ingest_path(str(root), project_key="parse-fix", force=True)
        assert g.files_indexed >= 1
        assert any("bad.py" in e for e in g.errors)


def test_cross_repo_requires_evidence_rejects_name_similarity():
    with pytest.raises(CrossRepoEdgeError):
        make_cross_repo_edge(
            source_repo="a",
            source_sha="aaa",
            target_repo="b",
            target_sha="bbb",
            edge_type="import",
            evidence="",
        )
    with pytest.raises(CrossRepoEdgeError):
        make_cross_repo_edge(
            source_repo="zoas",
            source_sha="aaa",
            target_repo="zaf",
            target_sha="bbb",
            edge_type="configured",
            evidence="name_similarity",
        )
    edge = make_cross_repo_edge(
        source_repo="zoas",
        source_sha="abc123",
        target_repo="zaf",
        target_sha="def456",
        edge_type="api_contract",
        evidence="openapi: /policies shared schema PolicyId",
        confidence=0.9,
    )
    assert edge["source_repo"] == "zoas"
    assert edge["type"] == "api_contract"


def test_graphify_snapshot_adapter_uses_lattice():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "m.py").write_text("def m():\n    return 0\n", encoding="utf-8")
        ingest_path(str(root), project_key="snap-fix", force=True)
        snap = graphify_snapshot("snap-fix")
        assert snap["kind"] == "GraphifySnapshot"
        assert snap["adapter"] == "lattice"
        assert snap["ux_label"] == "Lattice"
        assert snap["state"] in {
            "READY",
            "STALE",
            "NOT_INDEXED",
            "INDEXING",
            "ERROR",
            "NOT_CONFIGURED",
            "NOT_APPLICABLE",
        }
        hits = query_graph("snap-fix", "m")
        assert hits


def test_lattice_query_does_not_grant_write_permission():
    from app.services.mentrix.permission_broker import TOOL_ACTIONS

    assert TOOL_ACTIONS["lattice_query"] == "companion_lattice_query"
    assert "write" not in TOOL_ACTIONS["lattice_query"]
    assert TOOL_ACTIONS["lattice_query"] != TOOL_ACTIONS["git_push"]
    assert TOOL_ACTIONS["lattice_query"] != TOOL_ACTIONS["coding_agent_start"]


def test_contract_files_exist_no_second_store():
    root = Path(__file__).resolve().parents[2]
    assert (root / "ZECT_GRAPHIFY_LATTICE_CONTRACT.md").is_file()
    assert (root / "ZECT_GRAPHIFY_LATTICE_ACCEPTANCE.md").is_file()
    snap = (root / "backend" / "app" / "services" / "lattice" / "graphify_snapshot.py").read_text(
        encoding="utf-8"
    )
    assert "pgvector" not in snap.lower()
    assert "chroma" not in snap.lower()
    assert "faiss" not in snap.lower()
