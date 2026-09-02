"""Governed, read-only DB schema/ORM/migration inventory -- static analysis
of SQLAlchemy model classes and Alembic migration files, no live database
connection or credentials. Closes the "governed DB schema/ORM/migration
intelligence... doesn't exist at all" gap from
ZECT_DEVELOPER_V4_RECONCILIATION_AND_EXECUTION_PLAN.md Phase E.
"""

from __future__ import annotations

from app.services.quality.db_schema_eval import inventory_db_schema


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestSqlAlchemyModelDetection:
    def test_detects_tablename_and_columns(self, tmp_path):
        _write(
            tmp_path / "models.py",
            (
                "from sqlalchemy import Column, Integer, String\n"
                "from app.db import Base\n\n"
                "class User(Base):\n"
                '    __tablename__ = "users"\n'
                "    id = Column(Integer, primary_key=True)\n"
                "    email = Column(String, nullable=False)\n"
            ),
        )
        out = inventory_db_schema(workspace=str(tmp_path))
        assert out["count"] == 1
        table = out["tables"][0]
        assert table["table_name"] == "users"
        assert table["model_class"] == "User"
        assert {"name": "id", "type": "Integer"} in table["columns"]
        assert {"name": "email", "type": "String"} in table["columns"]

    def test_detects_multiple_models_in_one_file(self, tmp_path):
        _write(
            tmp_path / "models.py",
            (
                "from sqlalchemy import Column, Integer\n"
                "from app.db import Base\n\n"
                "class A(Base):\n"
                '    __tablename__ = "a"\n'
                "    id = Column(Integer, primary_key=True)\n\n"
                "class B(Base):\n"
                '    __tablename__ = "b"\n'
                "    id = Column(Integer, primary_key=True)\n"
            ),
        )
        out = inventory_db_schema(workspace=str(tmp_path))
        assert out["count"] == 2
        assert {t["table_name"] for t in out["tables"]} == {"a", "b"}

    def test_ignores_non_orm_classes(self, tmp_path):
        _write(
            tmp_path / "plain.py",
            "class NotAModel:\n    def __init__(self):\n        self.x = 1\n",
        )
        out = inventory_db_schema(workspace=str(tmp_path))
        assert out["count"] == 0

    def test_falls_back_to_lowercased_class_name_when_no_tablename(self, tmp_path):
        _write(
            tmp_path / "models.py",
            (
                "from sqlalchemy import Column, Integer\n"
                "from app.db import Base\n\n"
                "class Widget(Base):\n"
                "    id = Column(Integer, primary_key=True)\n"
            ),
        )
        out = inventory_db_schema(workspace=str(tmp_path))
        assert out["tables"][0]["table_name"] == "widget"

    def test_skips_unparseable_python_file_without_crashing(self, tmp_path):
        _write(tmp_path / "broken.py", "class Broken(Base:\n    this is not python\n")
        _write(
            tmp_path / "models.py",
            (
                "from sqlalchemy import Column, Integer\n"
                "from app.db import Base\n\n"
                "class Ok(Base):\n"
                '    __tablename__ = "ok"\n'
                "    id = Column(Integer, primary_key=True)\n"
            ),
        )
        out = inventory_db_schema(workspace=str(tmp_path))
        assert out["count"] == 1
        assert out["tables"][0]["table_name"] == "ok"

    def test_no_workspace_or_missing_dir_returns_empty_not_an_error(self, tmp_path):
        out = inventory_db_schema(workspace=str(tmp_path / "does-not-exist"))
        assert out == {"tables": [], "migrations": [], "sources": [], "count": 0}
        assert inventory_db_schema(workspace="") == {"tables": [], "migrations": [], "sources": [], "count": 0}

    def test_no_orm_at_all_reports_empty_not_a_guess(self, tmp_path):
        _write(tmp_path / "app.js", "console.log('a node app, not python');\n")
        out = inventory_db_schema(workspace=str(tmp_path))
        assert out["count"] == 0
        assert out["tables"] == []


class TestAlembicMigrationDetection:
    def test_detects_revision_and_down_revision(self, tmp_path):
        _write(
            tmp_path / "alembic" / "versions" / "abc123_add_widget.py",
            (
                '"""Add widget table\n\nRevision ID: abc123\nRevises: 000000\n"""\n\n'
                'revision: str = "abc123"\n'
                'down_revision = "000000"\n\n'
                "def upgrade() -> None:\n    pass\n"
            ),
        )
        out = inventory_db_schema(workspace=str(tmp_path))
        assert len(out["migrations"]) == 1
        m = out["migrations"][0]
        assert m["revision"] == "abc123"
        assert m["down_revision"] == "000000"
        assert "Add widget table" in m["message"]

    def test_no_alembic_dir_reports_no_migrations(self, tmp_path):
        out = inventory_db_schema(workspace=str(tmp_path))
        assert out["migrations"] == []
