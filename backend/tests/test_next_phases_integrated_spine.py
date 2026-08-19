"""Integrated Graphify → Lattice → Companion Present evidence. No second RAG. No fake Presenton."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from app.services.lattice.cross_repo import CrossRepoEdgeError, make_cross_repo_edge
from app.services.lattice.graphify_snapshot import graphify_snapshot
from app.services.lattice.indexer import ingest_path, query_graph
from app.services.mentrix.companion_scope import handoff_url
from app.services.mentrix.permission_broker import TOOL_ACTIONS


def _git_init(root: Path) -> str:
    subprocess.check_call(["git", "init", "-b", "main"], cwd=root, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "zect@example.com"], cwd=root)
    subprocess.check_call(["git", "config", "user.name", "ZECT"], cwd=root)
    subprocess.check_call(["git", "add", "."], cwd=root, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-m", "init"], cwd=root, stdout=subprocess.DEVNULL)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    return sha


def test_graphify_ingest_lattice_ready_at_sha_and_present_handoff():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "svc").mkdir()
        (root / "svc" / "api.py").write_text(
            "from fastapi import APIRouter\nrouter = APIRouter()\n@router.get('/health')\ndef health():\n    return {'ok': True}\n",
            encoding="utf-8",
        )
        (root / "tests").mkdir()
        (root / "tests" / "test_api.py").write_text("def test_health():\n    assert True\n", encoding="utf-8")
        sha = _git_init(root)
        graph = ingest_path(str(root), project_key="integrated-spine", force=True)
        assert graph.commit_sha == sha
        snap = graphify_snapshot("integrated-spine")
        assert snap["kind"] == "GraphifySnapshot"
        assert snap["adapter"] == "lattice"
        assert snap["ux_label"] == "Lattice"
        assert snap["commit_sha"] == sha
        assert snap["state"] in {"READY", "STALE"}
        hits = query_graph("integrated-spine", "health")
        assert hits
        url = handoff_url(
            "present_create",
            {"project_id": 7, "work_item_id": 3, "workspace_id": "integrated-spine"},
            extra={"prompt": "architecture from Lattice", "audience": "exec"},
        )
        assert url.startswith("/present/create")
        assert "project_id=7" in url
        assert "work_item_id=3" in url
        assert "prompt=" in url


def test_name_similarity_still_rejected_and_lattice_is_not_write():
    try:
        make_cross_repo_edge(
            source_repo="zoas",
            source_sha="aaa",
            target_repo="zaf",
            target_sha="bbb",
            edge_type="configured",
            evidence="name_similarity",
        )
        raise AssertionError("name similarity must fail")
    except CrossRepoEdgeError:
        pass
    assert TOOL_ACTIONS["lattice_query"] == "companion_lattice_query"
    assert TOOL_ACTIONS["lattice_query"] != TOOL_ACTIONS["git_push"]
