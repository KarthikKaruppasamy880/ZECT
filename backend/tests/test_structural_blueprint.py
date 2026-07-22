"""Structural RepoBlueprint pipeline — Lattice deep inventory."""

from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — register LatticeStructuralBlueprint
from app.database import Base
from app.services.lattice.indexer import communities, god_nodes, ingest_path
from app.services.lattice.structural_blueprint import (
    build_deep_prompt,
    build_structural_blueprint,
    get_structural_blueprint,
    persist_structural_blueprint,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _fixture_repo(root: Path) -> None:
    (root / "app").mkdir()
    (root / "requirements.txt").write_text("fastapi\nsqlalchemy\n", encoding="utf-8")
    (root / "app" / "main.py").write_text(
        """
from fastapi import FastAPI
import sqlalchemy

app = FastAPI()

class WidgetService:
    def list(self):
        return []

@app.get("/widgets")
def list_widgets():
    return WidgetService().list()
""",
        encoding="utf-8",
    )
    (root / "app" / "client.py").write_text(
        "import requests\n\ndef ping():\n    return requests.get('https://example.com')\n",
        encoding="utf-8",
    )


def test_build_persist_and_deep_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fixture_repo(root)
        key = "struct-bp-test"
        bp = build_structural_blueprint(str(root), key, max_files=100, refresh_graph=True)
        assert bp["project_key"] == key
        assert bp["stats"]["files_indexed"] >= 2
        assert bp["api_endpoints"], "expected FastAPI endpoints in blueprint"
        assert any("fastapi" in t or "python" in t for t in (bp["tech_stack"] or []))
        assert bp["functions"] or bp["classes"]
        assert bp["god_nodes"] is not None
        prompt = build_deep_prompt(bp)
        assert "API endpoints" in prompt
        assert "/widgets" in prompt or "list_widgets" in prompt or "GET" in prompt.upper() or "widgets" in prompt

        db = _session()
        persist_structural_blueprint(db, bp)
        loaded = get_structural_blueprint(db, key)
        assert loaded is not None
        assert loaded["stats"]["api_endpoints"] == bp["stats"]["api_endpoints"]
        assert len(loaded["api_endpoints"]) >= 1


def test_god_nodes_and_communities():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fixture_repo(root)
        key = "god-nodes-test"
        ingest_path(str(root), project_key=key)
        gods = god_nodes(key, limit=5)
        assert isinstance(gods, list)
        comps = communities(key, limit=5)
        assert isinstance(comps, list)
