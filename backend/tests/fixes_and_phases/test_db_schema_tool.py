"""The db_schema coding-agent tool -- governed, read-only DB schema lookup
available to every role (not just via an @mention). See Phase E of
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md.
"""

from __future__ import annotations

from app.services.coding_engine.mentrix_agent_tools import execute_tool, resolve_workspace
from app.services.coding_engine.mentrix_lead import ROLE_CODER, ROLE_EXPLORE, ROLE_TOOL_ALLOWLISTS


def _write_model(ws):
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "models.py").write_text(
        (
            "from sqlalchemy import Column, Integer, String\n"
            "from app.db import Base\n\n"
            "class User(Base):\n"
            '    __tablename__ = "users"\n'
            "    id = Column(Integer, primary_key=True)\n"
            "    email = Column(String, nullable=False)\n"
        ),
        encoding="utf-8",
    )


class TestDbSchemaTool:
    def test_no_table_arg_lists_every_table(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "repo"
        _write_model(ws)
        root = resolve_workspace(str(ws))

        out = execute_tool("db_schema", {}, workspace=root)
        assert out["ok"] is True
        assert {"table_name": "users", "model_class": "User"} in out["tables"]

    def test_table_arg_returns_one_tables_columns(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "repo"
        _write_model(ws)
        root = resolve_workspace(str(ws))

        out = execute_tool("db_schema", {"table": "users"}, workspace=root)
        assert out["ok"] is True
        assert out["table"]["table_name"] == "users"
        assert {"name": "email", "type": "String"} in out["table"]["columns"]

    def test_unknown_table_reports_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZECT_WORKSPACE_ROOT", str(tmp_path))
        ws = tmp_path / "repo"
        _write_model(ws)
        root = resolve_workspace(str(ws))

        out = execute_tool("db_schema", {"table": "nonexistent"}, workspace=root)
        assert out["ok"] is False

    def test_present_on_every_role_allowlist(self):
        for role in (ROLE_EXPLORE, ROLE_CODER):
            assert "db_schema" in ROLE_TOOL_ALLOWLISTS[role]
