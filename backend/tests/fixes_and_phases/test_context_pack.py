from unittest.mock import MagicMock, patch

from app.domains.agent_run.llm import _looks_like_path_only
from app.services.coding_engine.agent_context import compose_coding_agent_context, compose_context_pack
from app.services.coding_engine.propose_patches import _parse_json
from app.services.mentrix.presentation.blocks import CHART_TYPES


def test_looks_like_path_only():
    assert _looks_like_path_only(r"C:\Users\karuppk\zect-workspaces\zinnia\zoas")
    assert _looks_like_path_only("/home/zect/zoas")
    assert not _looks_like_path_only("README.md\n## Hello")
    assert not _looks_like_path_only("")


def test_compose_context_pack_includes_lattice_when_indexed():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    with patch("app.services.mentrix.companion.build_agent_context", return_value="KB: auth uses JWT"):
        with patch(
            "app.services.rag.retriever.hybrid_retrieve",
            return_value=[{"path": "auth.py", "content": "def login():"}],
        ):
            pack = compose_context_pack(goal="login", project_id=1, project_key="zinnia/zoas", db=db)
    assert pack["knowledge"] is True
    assert pack["lattice_hits"] == 1
    assert "Lattice facts" in pack["text"]
    assert "auth.py" in pack["text"]
    assert compose_coding_agent_context(goal="x", db=None) == ""


def test_parse_proposed_patches_json():
    data = _parse_json('```json\n{"patches_by_repo": {"1": [{"path": "a.py", "old": "x", "new": "y"}]}}\n```')
    assert data["patches_by_repo"]["1"][0]["path"] == "a.py"


def test_chart_types_include_radar_area_stacked():
    assert {"radar", "area", "stacked"} <= set(CHART_TYPES)
